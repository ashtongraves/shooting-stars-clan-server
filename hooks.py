import time
import falcon
import re
import os
from constants import ERROR_MSG_DATA_VALIDATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL, ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT, VALID_LOCATIONS, VALID_WORLDS, PASSWORD_ENABLED
master_pw_whitelist = set()
scout_pw_whitelist = set()

def hook_validate_data(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    """Take a cursory look at the data to see if anything looks obviously incorrect."""

    msg = ERROR_MSG_DATA_VALIDATION_FAIL
    data = req.media
    if data:
        if not isinstance(data, list):
            raise falcon.HTTPBadRequest(title='Bad request', description=msg)
        # Take a peek at each sighting passed in the body
        for data_obj in data:
            if not isinstance(data_obj, dict):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)

            # TODO: Remove this after updating the plugin to fix the breaking change
            # Supports old plugin's API
            if data_obj.get('loc') is not None:
                data_obj['location'] = data_obj['loc']

            # KISS, do not try to be clever here.
            loc = data_obj.get('location')
            world = data_obj.get('world')
            min_time = data_obj.get('minTime')
            max_time = data_obj.get('maxTime')

            # Basic existence checks.
            if loc is None or not isinstance(loc, int):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if world is None or not isinstance(world, int):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if min_time is None or not isinstance(min_time, int):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if max_time is None or not isinstance(max_time, int):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)

            # Feel free to add any other checks here.
            if loc not in VALID_LOCATIONS:
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if world not in VALID_WORLDS:
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if max_time - min_time < 120 or max_time - min_time > 60*26:
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if min_time >= max_time:
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if max_time > 60*150 + int(time.time()):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if max_time < int(time.time()):
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)


def hook_validate_auth(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    if not req.auth:
        raise falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_AUTHORIZATION_FAIL)
    if len(req.auth) < 1:
        raise falcon.HTTPBadRequest(title='Bad request', description=ERROR_MSG_AUTHORIZATION_FAIL)


def hook_validate_master_password(req: falcon.request.Request, resp: falcon.response.Response, resource, params):
    authorization = req.auth
    if authorization not in master_pw_whitelist:
        msg = ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)