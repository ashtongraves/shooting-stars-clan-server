import os
import sqlite3

import falcon
import datetime
from falcon import testing

from freezegun import freeze_time

import password_based_star_miners

import setup_db
from constants import ERROR_MSG_DATA_VALIDATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
from password_based_star_miners import PasswordStarMinersResource

FROZEN_UNIX_TIME = 1635422400
FROZEN_TIME = datetime.datetime.fromtimestamp(FROZEN_UNIX_TIME, tz=datetime.timezone.utc).isoformat()
PATH_TO_TEST_DB = 'test_db.db'


def create_test_app(conn: sqlite3.Connection):
    # falcon.App instances are callable WSGI apps
    # in larger applications the app is created in a separate file
    app = falcon.App()

    # Resources are represented by long-lived class instances
    shooting_stars_resource = PasswordStarMinersResource(conn)
    password_based_star_miners.scout_pw_whitelist.add('testpw')
    password_based_star_miners.scout_pw_whitelist.add('testpw2')
    password_based_star_miners.master_pw_whitelist.add('masterpw')

    app.add_route('/shooting_stars', shooting_stars_resource)
    app.add_route('/audit', shooting_stars_resource, suffix='separate')
    app.add_route('/whitelist', shooting_stars_resource, suffix='whitelist')
    app.add_static_route('/portal', os.environ['STATIC_ASSETS_FOLDER'])
    return app, shooting_stars_resource


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
        self.conn = setup_db.create_shared_key_db(PATH_TO_TEST_DB, create_whitelists=True)
        self.conn.row_factory = sqlite3.Row
        app, self.shooting_stars_resource = create_test_app(self.conn)
        self.app = testing.TestClient(app)

    def tearDown(self) -> None:
        super(TestCase, self).tearDown()
        self.conn.close()
        del self.app
        setup_db.delete_db(PATH_TO_TEST_DB)


@freeze_time(FROZEN_TIME)
class TestPasswordShootingStarsResourceGet(TestCase):

    def test_simple(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        add_data(self.conn, test_data, 'testpw')

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
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw')

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
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'masterpw')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        assert test_data in resp.json
        assert test_data_2 in resp.json

    def test_multiple_data_points_diff_keys_same_world(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['minTime'] = FROZEN_UNIX_TIME
        test_data_2['maxTime'] = FROZEN_UNIX_TIME + 200
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'masterpw')

        resp: falcon.testing.Result = self.app.simulate_get('/shooting_stars', headers={'Authorization': 'global'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 1
        data: dict = resp.json[0]
        assert data['location'] == 10
        assert data['world'] == 302
        assert data['minTime'] == FROZEN_UNIX_TIME
        assert data['maxTime'] == FROZEN_UNIX_TIME + 100

    def test_out_of_range(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (60*60)
        }
        add_data(self.conn, test_data, 'testpw')

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
        add_data(self.conn, test_data, 'testpw')

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
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw')

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
        resp = self.app.simulate_post('/shooting_stars', json=[], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

    def test_empty_list_master_pw(self):
        resp = self.app.simulate_post('/shooting_stars', json=[], headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200

    def test_single(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'testpw'
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
        resp = self.app.simulate_post('/shooting_stars', json=data, headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 2

        row1, row2 = [dict(r) for r in rows]

        assert row1['sharedKey'] == 'testpw'
        assert row1['location'] == test_data['location']
        assert row1['world'] == test_data['world']
        assert row1['minTime'] == test_data['minTime']
        assert row1['maxTime'] == test_data['maxTime']

        assert row2['sharedKey'] == 'testpw'
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
        resp = self.app.simulate_post('/shooting_stars', json=data, headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'testpw'
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
        add_data(self.conn, test_data, 'testpw')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 600,
            'maxTime': FROZEN_UNIX_TIME + 1100
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'testpw'
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
        add_data(self.conn, test_data, 'testpw')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + (60*10) - 1,
            'maxTime': FROZEN_UNIX_TIME + (60*20)
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 1
        assert rows[0]['sharedKey'] == 'testpw'
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
        add_data(self.conn, test_data, 'testpw')
        test_data_2 = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + (60*10),
            'maxTime': FROZEN_UNIX_TIME + (60*20)
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data_2], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_200

        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 2
        row1, row2 = [dict(r) for r in rows]
        assert row1['sharedKey'] == 'testpw'
        assert row1['location'] == test_data['location']
        assert row1['world'] == test_data['world']
        assert row1['minTime'] == test_data['minTime']
        assert row1['maxTime'] == test_data['maxTime']
        assert row2['sharedKey'] == 'testpw'
        assert row2['location'] == test_data_2['location']
        assert row2['world'] == test_data_2['world']
        assert row2['minTime'] == test_data_2['minTime']
        assert row2['maxTime'] == test_data_2['maxTime']

    def test_validation_fail_no_auth(self):
        resp = self.app.simulate_post('/shooting_stars')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_not_on_either_list(self):
        resp = self.app.simulate_post('/shooting_stars', headers={'Authorization': 'testpwa'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_non_alpha_auth(self):
        password_based_star_miners.scout_pw_whitelist.add('123456')
        resp = self.app.simulate_post('/shooting_stars', headers={'Authorization': '123456'})
        password_based_star_miners.scout_pw_whitelist.remove('123456')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_alpha_numeric_auth(self):
        password_based_star_miners.scout_pw_whitelist.add('a1b2c3d4')
        resp = self.app.simulate_post('/shooting_stars', headers={'Authorization': 'a1b2c3d4'})
        password_based_star_miners.scout_pw_whitelist.remove('a1b2c3d4')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_entry_not_dict(self):
        resp = self.app.simulate_post('/shooting_stars', json=['fail'], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_second_entry_not_dict(self):
        resp = self.app.simulate_post('/shooting_stars', json=[{'test': 'pass'}, 'fail'], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_location(self):
        test_data = {
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_world(self):
        test_data = {
            'location': 10,
            'minTime': FROZEN_UNIX_TIME + 500,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_min_time(self):
        test_data = {
            'location': 10,
            'world': 302,
            'maxTime': FROZEN_UNIX_TIME + 1000
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []

    def test_validation_fail_missing_max_time(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME + 500
        }
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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
        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
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

        resp = self.app.simulate_post('/shooting_stars', json=[test_data], headers={'Authorization': 'testpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        assert self.conn.execute('''SELECT * FROM data''').fetchall() == []


@freeze_time(FROZEN_TIME)
class TestPasswordShootingStarsResourceGetSeparate(TestCase):

    def test_simple(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        add_data(self.conn, test_data, 'testpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        correct_response = test_data.copy()
        correct_response['password'] = 'testpw'
        assert resp.status == falcon.HTTP_200
        assert resp.json == [correct_response]

    def test_master_pw_data_point(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        add_data(self.conn, test_data, 'masterpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        correct_response = test_data.copy()
        correct_response['password'] = 'MASTER PASSWORD'
        assert resp.status == falcon.HTTP_200
        assert resp.json == [correct_response]

    def test_multiple_data_points(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['world'] = 304
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        correct_response_1 = test_data.copy()
        correct_response_1['password'] = 'testpw'
        correct_response_2 = test_data_2.copy()
        correct_response_2['password'] = 'testpw'
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        assert correct_response_1 in resp.json
        assert correct_response_2 in resp.json

    def test_multiple_data_points_diff_keys(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['world'] = 304
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw2')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        test_data_with_key = test_data.copy()
        test_data_with_key['password'] = 'testpw'
        test_data_with_key_2 = test_data_2.copy()
        test_data_with_key_2['password'] = 'testpw2'
        assert test_data_with_key in resp.json
        assert test_data_with_key_2 in resp.json

    def test_multiple_data_points_diff_keys_same_world(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        test_data_2 = test_data.copy()
        test_data_2['minTime'] = FROZEN_UNIX_TIME
        test_data_2['maxTime'] = FROZEN_UNIX_TIME + 200
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw2')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        test_data_with_key = test_data.copy()
        test_data_with_key['password'] = 'testpw'
        test_data_with_key_2 = test_data_2.copy()
        test_data_with_key_2['password'] = 'testpw2'
        assert test_data_with_key in resp.json
        assert test_data_with_key_2 in resp.json

    def test_out_of_range(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (60*60)
        }
        add_data(self.conn, test_data, 'testpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert resp.json == []

    def test_edge_of_range(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - (100 + (60*60)),
            'maxTime': FROZEN_UNIX_TIME - (60*60) + 1
        }
        add_data(self.conn, test_data, 'testpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 1
        data: dict = resp.json[0]
        assert data['location'] == 10
        assert data['world'] == 302
        assert data['minTime'] == FROZEN_UNIX_TIME - (100 + (60*60))
        assert data['maxTime'] == FROZEN_UNIX_TIME - (60*60) + 1

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
        add_data(self.conn, test_data, 'testpw')
        add_data(self.conn, test_data_2, 'testpw')

        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        test_data_2_with_key = test_data_2.copy()
        test_data_2_with_key['password'] = 'testpw'
        assert resp.json == [test_data_2_with_key]

    def test_validation_fail_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/audit')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}

    def test_validation_allow_non_alpha_auth(self):
        password_based_star_miners.master_pw_whitelist.add('123456')
        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': '123456'})
        password_based_star_miners.master_pw_whitelist.remove('123456')
        assert resp.status == falcon.HTTP_200

    def test_validation_allow_alpha_numeric_auth(self):
        password_based_star_miners.master_pw_whitelist.add('a1b2c3d4')
        resp: falcon.testing.Result = self.app.simulate_get('/audit', headers={'Authorization': 'a1b2c3d4'})
        password_based_star_miners.master_pw_whitelist.remove('a1b2c3d4')
        assert resp.status == falcon.HTTP_200


class TestPasswordShootingStarsResourceGetWhitelist(TestCase):

    def test_simple(self):
        resp: falcon.testing.Result = self.app.simulate_get('/whitelist', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        assert 'testpw' in resp.json
        assert 'testpw2' in resp.json

    def test_master_password_not_returned(self):
        password_based_star_miners.master_pw_whitelist.add('masterpw')
        resp: falcon.testing.Result = self.app.simulate_get('/whitelist', headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_200
        assert len(resp.json) == 2
        assert 'testpw' in resp.json
        assert 'testpw2' in resp.json
        assert 'masterpw' not in resp.json
        password_based_star_miners.master_pw_whitelist.remove('masterpw')

    def test_validation_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/whitelist')
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}

    def test_validation_incorrect_auth(self):
        resp: falcon.testing.Result = self.app.simulate_get('/whitelist', headers={'Authorization': 'badpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}


class TestPasswordShootingStarsResourcePostWhitelist(TestCase):

    def test_simple(self):
        resp: falcon.testing.Result = self.app.simulate_post('/whitelist', headers={'Authorization': 'masterpw'}, json={'password': 'testpw3'})
        assert resp.status == falcon.HTTP_200
        assert 'testpw3' in password_based_star_miners.scout_pw_whitelist
        assert 'testpw3' not in password_based_star_miners.master_pw_whitelist
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 1
        password_based_star_miners.scout_pw_whitelist.discard('testpw3')

    def test_already_existing_add(self):
        password_based_star_miners.scout_pw_whitelist.add('testpw3')
        resp: falcon.testing.Result = self.app.simulate_post('/whitelist', headers={'Authorization': 'masterpw'}, json={'password': 'testpw3'})
        assert resp.status == falcon.HTTP_200
        assert 'testpw3' in password_based_star_miners.scout_pw_whitelist
        assert 'testpw3' not in password_based_star_miners.master_pw_whitelist
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 1
        password_based_star_miners.scout_pw_whitelist.discard('testpw3')

    def test_validation_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_post('/whitelist', json={'password': 'testpw3'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 0

    def test_validation_incorrect_auth(self):
        resp: falcon.testing.Result = self.app.simulate_post('/whitelist', headers={'Authorization': 'badpw'}, json={'password': 'testpw3'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 0

    def test_validation_fail_missing_password(self):
        resp = self.app.simulate_post('/whitelist', json={}, headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 0

    def test_validation_fail_password_not_str(self):
        resp = self.app.simulate_post('/whitelist', json={"password": 1}, headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw3"''').fetchall()
        assert len(rows) == 0


class TestPasswordShootingStarsResourceDeleteWhitelist(TestCase):

    def test_simple(self):
        resp: falcon.testing.Result = self.app.simulate_delete('/whitelist', headers={'Authorization': 'masterpw'}, json={'password': 'testpw2'})

        assert resp.status == falcon.HTTP_200
        assert 'testpw2' not in password_based_star_miners.scout_pw_whitelist
        assert 'testpw' in password_based_star_miners.scout_pw_whitelist
        assert resp.text == 'Successfully removed from whitelist and data cleared'
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw2"''').fetchall()
        assert len(rows) == 0

        password_based_star_miners.scout_pw_whitelist.add('testpw2')

    def test_remove_data(self):
        test_data = {
            'location': 10,
            'world': 302,
            'minTime': FROZEN_UNIX_TIME - 100,
            'maxTime': FROZEN_UNIX_TIME + 100
        }
        add_data(self.conn, test_data, 'testpw2')
        resp: falcon.testing.Result = self.app.simulate_delete('/whitelist', headers={'Authorization': 'masterpw'}, json={'password': 'testpw2'})

        assert resp.status == falcon.HTTP_200
        assert 'testpw2' not in password_based_star_miners.scout_pw_whitelist
        assert 'testpw' in password_based_star_miners.scout_pw_whitelist
        assert resp.text == 'Successfully removed from whitelist and data cleared'
        rows = self.conn.execute('''SELECT * FROM data''').fetchall()
        assert len(rows) == 0
        rows = self.conn.execute('''SELECT password FROM scout_whitelist WHERE password = "testpw2"''').fetchall()
        assert len(rows) == 0

        password_based_star_miners.scout_pw_whitelist.add('testpw2')

    def test_not_in_whitelist(self):
        resp: falcon.testing.Result = self.app.simulate_delete('/whitelist', headers={'Authorization': 'masterpw'}, json={'password': 'testpw3'})
        assert resp.status == falcon.HTTP_200
        assert 'testpw2' in password_based_star_miners.scout_pw_whitelist
        assert 'testpw' in password_based_star_miners.scout_pw_whitelist
        assert resp.text == 'No such key found in the whitelist'

    def test_validation_no_auth(self):
        resp: falcon.testing.Result = self.app.simulate_delete('/whitelist', json={'password': 'testpw2'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}

    def test_validation_incorrect_auth(self):
        resp: falcon.testing.Result = self.app.simulate_delete('/whitelist', headers={'Authorization': 'badpw'}, json={'password': 'testpw2'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT}

    def test_validation_fail_missing_password(self):
        resp = self.app.simulate_delete('/whitelist', json={}, headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}

    def test_validation_fail_password_not_str(self):
        resp = self.app.simulate_delete('/whitelist', json={"password": 1}, headers={'Authorization': 'masterpw'})
        assert resp.status == falcon.HTTP_400
        assert resp.json == {'title': 'Bad request', 'description': ERROR_MSG_DATA_VALIDATION_FAIL}
