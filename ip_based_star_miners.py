import json
import os

import falcon
from base_shooting_stars_resource import BaseShootingStarsResource, hook_validate_auth, hook_validate_data
from constants import ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT, ERROR_MSG_DATA_VALIDATION_FAIL

master_whitelist = set()
scout_whitelist = set()


def hook_validate_ip_addr(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    ip_addr = req.remote_addr
    authorization = req.auth
    if ip_addr not in scout_whitelist and ip_addr not in master_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_master_ip_addr(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    ip_addr = req.remote_addr
    if ip_addr not in master_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_whitelist_params(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    if not isinstance(params.get('uid', None), str):
        msg = ERROR_MSG_DATA_VALIDATION_FAIL
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


class IpStarMinersResource:

    def __init__(self, path_to_db: str):
        self.shooting_stars_resource = BaseShootingStarsResource(path_to_db)

    def on_get_uuid(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.text = hash(req.forwarded)
        return resp

    @falcon.before(hook_validate_master_ip_addr)
    def on_get_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps(scout_whitelist)
        return resp

    @falcon.before(hook_validate_master_ip_addr)
    @falcon.before(hook_validate_whitelist_params)
    def on_post_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        scout_whitelist.add(req.params('uid'))
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_master_ip_addr)
    @falcon.before(hook_validate_whitelist_params)
    def on_delete_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        scout_whitelist.discard(req.params('uid'))
        self.shooting_stars_resource.conn.execute("""
        DELETE
            FROM data
        WHERE
            uid = ?
        """, [req.params('uid')])
        self.shooting_stars_resource.conn.commit()
        resp.status = falcon.HTTP_200
        return resp

    @falcon.before(hook_validate_ip_addr)
    def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
        return self.shooting_stars_resource.on_post(req, resp)

    def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
        return self.shooting_stars_resource.on_get(req, resp)
