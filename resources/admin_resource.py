import json
import sqlite3
import time
import falcon
import bcrypt
import os
from constants import ERROR_MSG_AUTHORIZATION_FAIL_SUBMIT, ERROR_MSG_DATA_VALIDATION_FAIL
from hooks import hook_validate_master_password, hook_validate_whitelist_params, hook_validate_scout_password

class AdminResource:
    def __init__(self, conn: sqlite3.Connection):
        self.__scout_pw_whitelist = set()
        self.__master_pw_whitelist = set()
        self.__conn = conn
        scout_pws = self.__conn.execute('SELECT password FROM scout_whitelist').fetchall()
        for scout in scout_pws:
            self.__scout_pw_whitelist.add(scout['password'])
        master_pws = self.__conn.execute('SELECT password FROM master_whitelist').fetchall()
        for master in master_pws:
            self.__master_pw_whitelist.add(master['password'])

    @falcon.before(hook_validate_master_password)
    def on_get_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps(list(self.__scout_pw_whitelist.difference(self.__master_pw_whitelist)))
        resp.append_header('Access-Control-Allow-Origin', '*')
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_post_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        pw = bcrypt.hashpw(req.media['password'].strip(), bcrypt.gensalt(14))
        self.__scout_pw_whitelist.add(pw)
        self.__conn.execute("""
        INSERT
            INTO scout_whitelist
        VALUES
            (?)
        """, [pw])
        self.__conn.commit()
        resp.status = falcon.HTTP_200
        resp.append_header('Access-Control-Allow-Origin', '*')
        return resp

    @falcon.before(hook_validate_master_password)
    @falcon.before(hook_validate_whitelist_params)
    def on_delete_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        pw = bcrypt.hashpw(req.media['password'].strip(), bcrypt.gensalt(14))
        if pw in self.__scout_pw_whitelist:
            self.__conn.execute("""
            DELETE
                FROM data
            WHERE
                sharedKey = ?
            """, [pw])
            self.__conn.execute("""
            DELETE
                FROM scout_whitelist
            WHERE
                password = ?
            """, [pw])
            self.__conn.commit()
            self.__scout_pw_whitelist.discard(pw)
            resp.text = 'Successfully removed from whitelist and data cleared'
        else:
            resp.text = 'No such key found in the whitelist'
        resp.status = falcon.HTTP_200
        resp.append_header('Access-Control-Allow-Origin', '*')
        return resp

    def on_options_whitelist(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.append_header('Access-Control-Allow-Origin', '*')
        resp.append_header('Access-Control-Allow-Headers', '*')
        resp.append_header('Access-Control-Allow-Methods', '*')
        return resp

    @falcon.before(hook_validate_scout_password)
    def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
        return self.__shooting_stars_resource.on_post(req, resp)

    @falcon.before(hook_validate_master_password)
    def on_get_separate(self, req: falcon.request.Request, resp: falcon.response.Response):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status

        # Get all current worlds for all keys.
        lowest_time = int(time.time()) - (60*60)
        highest_time = int(time.time()) + (60*150)
        rows = self.__conn.execute(f"""
            SELECT location, world, minTime, maxTime, sharedKey
            FROM data
            WHERE
                maxTime > ? AND maxTime < ?
            ORDER BY world
        """, [lowest_time, highest_time]).fetchall()

        # Put data in json format
        data_blob = []
        for row in rows:
            data = {
                'location': row['location'],
                'world': row['world'],
                'minTime': row['minTime'],
                'maxTime': row['maxTime'],
                'password': (row['sharedKey'] if row['sharedKey'] not in self.__master_pw_whitelist else 'MASTER PASSWORD')
            }
            data_blob.append(data)
        resp.text = json.dumps(data_blob)
        resp.append_header('Access-Control-Allow-Origin', '*')
        return resp

    def on_options_separate(self, req: falcon.request.Request, resp: falcon.response.Response):
        resp.status = falcon.HTTP_200
        resp.append_header('Access-Control-Allow-Origin', '*')
        resp.append_header('Access-Control-Allow-Headers', '*')
        resp.append_header('Access-Control-Allow-Methods', '*')
        return resp