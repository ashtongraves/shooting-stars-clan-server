import json
import re
import time
from typing import Dict

import falcon
import sqlite3

from constants import ERROR_MSG_AUTHORIZATION_FAIL, ERROR_MSG_DATA_VALIDATION_FAIL

valid_locs = set(range(14))
# Obviously this can be made to specifically grab members worlds
valid_worlds = {n for n in range(301, 581)}


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
            if data_obj.get('loc'):
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
            if loc not in valid_locs:
                raise falcon.HTTPBadRequest(title='Bad request', description=msg)
            if world not in valid_worlds:
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
    msg = ERROR_MSG_AUTHORIZATION_FAIL
    if not req.auth:
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)
    if len(req.auth) > 10 or len(req.auth) < 1:
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)
    if re.fullmatch('^[a-zA-Z]+$', req.auth) is None:
        raise falcon.HTTPBadRequest(title='Bad request', description=msg)


class BaseShootingStarsResource:

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @falcon.before(hook_validate_auth)
    def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        authorization = req.auth

        # Get all current worlds
        lowest_time = int(time.time()) - (60*60)
        highest_time = int(time.time()) + (60*150)
        rows = self.conn.execute("""
            SELECT location, world, minTime, maxTime
            FROM data
            WHERE sharedKey = ?
            AND maxTime > ? AND maxTime < ?
            ORDER BY maxTime
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

    def _insert_sighting(self, star_data: Dict[str, int], authorization: str):
        self.conn.execute("""
            INSERT INTO data
                (location, world, minTime, maxTime, sharedKey)
            VALUES (?, ?, ?, ?, ?)
        """, [star_data['location'], star_data['world'], star_data['minTime'], star_data['maxTime'], authorization])
        self.conn.commit()

    def _update_sighting(self, existing_row, star_data: Dict[str, int]):

        new_min_time = max(existing_row['minTime'], star_data['minTime'])
        new_max_time = min(existing_row['maxTime'], star_data['maxTime'])
        if new_min_time <= new_max_time:
            self.conn.execute("""
                UPDATE data
                SET minTime = ?, maxTime = ?
                WHERE ROWID = ?
            """, [new_min_time, new_max_time, existing_row['ROWID']])
            self.conn.commit()

    @falcon.before(hook_validate_auth)
    @falcon.before(hook_validate_data)
    def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200  # This is the default status
        authorization = req.auth

        # Handle the ping case
        if not req.media:
            return resp
        # For each sighting, see if we need to insert a new record or update an existing one.
        data = req.media
        for data_obj in data:
            data_obj: dict
            world = data_obj['world']
            min_time = data_obj['minTime']
            # Get most recent insert
            row = self.conn.execute("""
                SELECT ROWID, location, world, minTime, maxTime
                FROM data
                WHERE world = ? AND maxTime > ? AND sharedKey = ? ORDER BY ROWID DESC
            """, [world, min_time - 60*10, authorization]).fetchone()

            if row is None:
                self._insert_sighting(data_obj, authorization)
            else:
                self._update_sighting(row, data_obj)

        return resp
