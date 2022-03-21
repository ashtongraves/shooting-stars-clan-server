import sqlite3

import falcon
import datetime
from falcon import testing

from freezegun import freeze_time

import server

import setup_db
from resources.stars_resource import StarsResource
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
        self.app = testing.TestClient(server.create_app(self.conn, StarsResource))

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
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

    def test_single(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
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
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=data, headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 2

        row1, row2 = [dict(r) for r in rows]

        assert row1['sharedKey'] == 'global'
        assert row1['location'] == test_data['location']
        assert row1['world'] == test_data['world']
        assert row1['minTime'] == test_data['minTime']
        assert row1['maxTime'] == test_data['maxTime']

        assert row2['sharedKey'] == 'global'
        assert row2['location'] == test_data_2['location']
        assert row2['world'] == test_data_2['world']
        assert row2['minTime'] == test_data_2['minTime']
        assert row2['maxTime'] == test_data_2['maxTime']

    def test_two_same_world(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 600,
            'maxTime': FROZEN_UNIX_TIME + 1100
        }
        data = [test_data, test_data_2]
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=data, headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'global'
        assert rows[0]['location'] == test_data['location']
        assert rows[0]['world'] == test_data['world']
        assert rows[0]['minTime'] == test_data_2['minTime']
        assert rows[0]['maxTime'] == test_data['maxTime']

    def test_update_existing(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        add_data(self.conn, test_data, 'global')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 600,
            'maxTime': FROZEN_UNIX_TIME + 1100
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'global'
        assert rows[0]['location'] == test_data['location']
        assert rows[0]['world'] == test_data['world']
        assert rows[0]['minTime'] == test_data_2['minTime']
        assert rows[0]['maxTime'] == test_data['maxTime']

    def test_update_with_recent_old(self):
        # This would probably indicate fake data in either data 1 or 2 (or world reset)
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME
        }
        add_data(self.conn, test_data, 'global')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + (60*10) - 1,
            'maxTime': FROZEN_UNIX_TIME + (60*20)
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'global'
        assert rows[0]['location'] == test_data['location']
        assert rows[0]['world'] == test_data['world']
        assert rows[0]['minTime'] == test_data['minTime']
        assert rows[0]['maxTime'] == test_data['maxTime']

    def test_update_with_too_old(self):
        # This would probably indicate fake data in either data 1 or 2 (or world reset)
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME
        }
        add_data(self.conn, test_data, 'global')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + (60*10),
            'maxTime': FROZEN_UNIX_TIME + (60*20)
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 2
        row1, row2 = [dict(r) for r in rows]
        assert row1['sharedKey'] == 'global'
        assert row1['location'] == test_data['location']
        assert row1['world'] == test_data['world']
        assert row1['minTime'] == test_data['minTime']
        assert row1['maxTime'] == test_data['maxTime']
        assert row2['sharedKey'] == 'global'
        assert row2['location'] == test_data_2['location']
        assert row2['world'] == test_data_2['world']
        assert row2['minTime'] == test_data_2['minTime']
        assert row2['maxTime'] == test_data_2['maxTime']

    def test_validation_fail_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_non_alpha_auth(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', headers={'Authorization': '123456'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_alpha_numeric_auth(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', headers={'Authorization': 'a1b2c3d4'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_entry_not_dict(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=['fail'], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_second_entry_not_dict(self):
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[{'test': 'pass'}, 'fail'], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_location(self):
        test_data = {
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_world(self):
        test_data = {
            'location': 10,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_min_time(self):
        test_data = {
            'location': 10,
            'world': 302,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_max_time(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_location_not_int(self):
        test_data = {
            'location': '10',
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_world_not_int(self):
        test_data = {
            'location': 10,
            'world': '302',
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_min_time_not_int(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': f'{FROZEN_UNIX_TIME + 500}',
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_max_time_not_int(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': f'{FROZEN_UNIX_TIME + 1000}'
        }
        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_location_not_valid_negative(self):
        test_data = {
            'location': -1,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_location_not_valid_too_high(self):
        test_data = {
            'location': 14,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_world_not_valid(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_times_too_close(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME + 881,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_times_too_far(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME,
            'maxTime': FROZEN_UNIX_TIME + (60*26) + 1
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_min_greater_than_max(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME + 1000,
            'maxTime': FROZEN_UNIX_TIME
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_too_far_in_the_future(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME + 1000,
            'maxTime': FROZEN_UNIX_TIME + (60*150) + 1
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_in_the_past(self):
        test_data = {
            'location': 10,
            'world': 30,
            'minTime': FROZEN_UNIX_TIME - 500,
            'maxTime': FROZEN_UNIX_TIME - 50
        }

        resp: falcon.testing.Result = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []
