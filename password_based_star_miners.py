import json
import sqlite3
import time

import falcon
from base_shooting_stars_resource import BaseShootingStarsResource, hook_validate_auth
from constants import ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT, ERROR_MSG_DATA_VALIDATION_FAIL

master_pw_whitelist = set()
scout_pw_whitelist = set()


def hook_validate_scout_password(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    authorization = req.auth
    if authorization not in scout_pw_whitelist and authorization not in master_pw_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_master_password(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    authorization = req.auth
    if authorization not in master_pw_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_whitelist_params(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    msg = ERROR_MSG_DATA_VALIDATION_FAIL
    try:
        data = json.loads(req.media)
    except Exception:
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)
    if not isinstance(data.get('password', None), str):
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


class PasswordStarMinersResource:

    def __init__(self, path_to_db: sqlite3.Connection):
        self.shooting_stars_resource = BaseShootingStarsResource(path_to_db)

    @falcon.before(hook_validate_master_password)
    def on_get_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps(list(scout_pw_whitelist.difference(master_pw_whitelist)))
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_post_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        data = json.loads(req.media)
        scout_pw_whitelist.add(data['password'])
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_delete_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        data = json.loads(req.media)
        if data['password'] in scout_pw_whitelist:
            self.shooting_stars_resource.conn.execute("""
            DELETE
                FROM data
            WHERE
                sharedKey = ?
            """, [data['password']])
            self.shooting_stars_resource.conn.commit()
            scout_pw_whitelist.discard(data['password'])
            resp.text = 'Successfully removed from whitelist and data cleared'
        else:
            resp.text = 'No such key found in the whitelist'
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_scout_password)
    def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
        return self.shooting_stars_resource.on_post(req, resp)

    @falcon.before(hook_validate_auth)
    def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status

        # Get all current worlds for all keys.
        lowest_time = int(time.time()) - (60*60)
        highest_time = int(time.time()) + (60*150)
        rows = self.shooting_stars_resource.conn.execute("""
            SELECT location, world, MAX(minTime) as minTime, MIN(maxTime) as maxTime
            FROM data
            WHERE
                maxTime > ? AND maxTime < ?
            GROUP BY location, world
            ORDER BY maxTime
        """, [lowest_time, highest_time]).fetchall()

        # Put data in json format
        data_blob = []
        for row in rows:
            data = {
                'location': row['location'],
                'world': row['world'],
                'minTime': row['minTime'],
                'maxTime': row['maxTime']
            }
            data_blob.append(data)
        resp.text = json.dumps(data_blob)
        return resp

    @falcon.before(hook_validate_master_password)
    def on_get_separate(self, req: falcon.request.Request, resp: falcon.response.Response):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status

        # Get all current worlds for all keys.
        lowest_time = int(time.time()) - (60*60)
        highest_time = int(time.time()) + (60*150)
        rows = self.shooting_stars_resource.conn.execute(f"""
            SELECT location, world, minTime, maxTime, sharedKey
            FROM data
            WHERE
                maxTime > ? AND maxTime < ? AND sharedKey NOT IN ({','.join('?'*len(master_pw_whitelist))})
            ORDER BY world
        """, [lowest_time, highest_time, *master_pw_whitelist]).fetchall()

        # Put data in json format
        data_blob = []
        for row in rows:
            data = {
                'location': row['location'],
                'world': row['world'],
                'minTime': row['minTime'],
                'maxTime': row['maxTime'],
                'password': row['sharedKey']
            }
            data_blob.append(data)
        resp.text = json.dumps(data_blob)
        return resp

