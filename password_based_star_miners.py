import json
import time

import falcon
from base_shooting_stars_resource import BaseShootingStarsResource
from constants import ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT, ERROR_MSG_DATA_VALIDATION_FAIL


master_pw_whitelist = set()
scout_pw_whitelist = set()


def hook_validate_scout_password(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    authorization = req.auth
    if authorization not in scout_pw_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_master_password(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    authorization = req.auth
    if authorization not in master_pw_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_whitelist_params(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    if not isinstance(params.get('password', None), str):
        msg = ERROR_MSG_DATA_VALIDATION_FAIL
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


class PasswordStarMinersResource:

    def __init__(self, path_to_db: str):
        self.shooting_stars_resource = BaseShootingStarsResource(path_to_db)

    @falcon.before(hook_validate_master_password)
    def on_get_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps(scout_pw_whitelist)
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_post_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        scout_pw_whitelist.add(req.params('password'))
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_delete_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        scout_pw_whitelist.discard(req.params('password'))
        self.shooting_stars_resource.conn.execute("""
        DELETE
            FROM data
        WHERE
            sharedKey = ?
        """, [req.params('password')])
        self.shooting_stars_resource.conn.commit()
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_scout_password)
    def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
        return self.shooting_stars_resource.on_post(req, resp)

    def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        authorization = req.auth

        # Get all current worlds for all keys.
        lowest_time = int(time.time()) - (60*60)
        highest_time = int(time.time()) + (60*150)
        rows = self.shooting_stars_resource.conn.execute("""
            SELECT location, world, MAX(minTime), MIN(maxTime)
            FROM data
            WHERE
                maxTime > ? AND maxTime < ?
            ORDER BY maxTime
            GROUP BY location, world
        """, [authorization, lowest_time, highest_time]).fetchall()

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
