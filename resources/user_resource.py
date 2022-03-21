import falcon
import sqlite3
import json

def __init__(self, conn: sqlite3.Connection):
    self.conn = conn

@falcon.before(hook_validate_auth)
def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200