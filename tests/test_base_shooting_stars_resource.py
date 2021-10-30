import copy
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import falcon
import datetime
from falcon import testing

from freezegun import freeze_time

import server

import setup_db
from constants import ERROR_MSG_DATA_VALIDATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL

FROZEN_UNIX_TIME = 1635422400
FROZEN_TIME = datetime.datetime.fromtimestamp(FROZEN_UNIX_TIME, tz=datetime.timezone.utc).isoformat()
PATH_TO_TEST_DB = 'test_db.db'


def add_data(connection, star_data: dict, shared_key: str):
    connection.execute("""
        INSERT INTO data
            (location, world, minTime, maxTime, sharedKey)
        VALUES (?, ?, ?, ?, ?)
    """, [star_data['location'], star_data['world'], star_data['minTime'], star_data['maxTime'], shared_key])
    connection.commit()


class TestCase(testing.TestCase):
    def setUp(self):
        super(TestCase, self).setUp()
        self.conn = setup_db.create_shared_key_db(PATH_TO_TEST_DB)
        self.conn.row_factory = sqlite3.Row
        self.app = testing.TestClient(server.create_app(self.conn))

    def tearDown(self) -> None:
        super(TestCase, self).tearDown()
        self.conn.close()
        del self.app
        setup_db.delete_db(PATH_TO_TEST_DB)


@freeze_time(FROZEN_TIME)
class TestShootingStarsResourceGet(TestCase):

    def test_simple(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        add_data(self.conn, test_data, 'global')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert resp.json == [test_data]

    def test_multiple_data_points(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['world'] = 304
        add_data(self.conn, test_data, 'global')
        add_data(self.conn, test_data_2, 'global')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        assert test_data in resp.json
        assert test_data_2 in resp.json

    def test_multiple_data_points_diff_keys(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['world'] = 304
        add_data(self.conn, test_data, 'global')
        add_data(self.conn, test_data_2, 'notglobal')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 1
        assert test_data in resp.json
        assert test_data_2 not in resp.json

    def test_out_of_range(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (60*60)
        }
        add_data(self.conn, test_data, 'global')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert resp.json == []

    def test_edge_of_range(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (60*60) + 1
        }
        add_data(self.conn, test_data, 'global')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert resp.json == [test_data]

    def test_simple_with_old_data(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (50 + (60*60))
        }
        test_data_2 = {
            'location': 8,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 100,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        add_data(self.conn, test_data, 'global')
        add_data(self.conn, test_data_2, 'global')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert resp.json == [test_data_2]

    def test_validation_fail_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}

    def test_validation_fail_non_alpha_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': '123456'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}

    def test_validation_fail_alpha_numeric_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'a1b2c3d4'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}


@freeze_time(FROZEN_TIME)
class TestShootingStarsResourcePost(TestCase):

    def test_empty_list(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json='[]', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

    def test_single(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=json.dumps([test_data]), headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'global'
        assert rows[0]['location'] == test_data['location']
        assert rows[0]['world'] == test_data['world']
        assert rows[0]['minTime'] == test_data['minTime']
        assert rows[0]['maxTime'] == test_data['maxTime']

    def test_two(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        test_data_2 = {
            'location': 10,
            'world': 303,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        data = [test_data, test_data_2]
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=json.dumps(data), headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'global'
        assert rows[0]['location'] == test_data['location']
        assert rows[0]['world'] == test_data['world']
        assert rows[0]['minTime'] == test_data['minTime']
        assert rows[0]['maxTime'] == test_data['maxTime']
