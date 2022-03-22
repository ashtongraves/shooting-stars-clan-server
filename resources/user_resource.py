import falcon
import sqlite3
import json
from hooks import hook_validate_user

class UserResource:
  def __init__(self, conn: sqlite3.Connection):
    self.__conn = conn

  def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    results = self.__conn.execute("select id, name from users").fetchAll()
    output = []
    for row in results:
      resultObject = {
        'id': row['id'],
        'name': row['name'],
      }
      output.append(resultObject)
    resp.text = json.dumps(output)
    return resp

  @falcon.before(hook_validate_user)
  def on_post(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    user = req.body.name
    self.__conn.execute("""
        insert into users (name)
        values(?)
    """, user)
    self.__conn.commit()
    return resp
  
  @falcon.before(hook_validate_user)
  def on_delete(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    user_id = int(req.body.id)
    self.__conn.execute("""
        delete from users
        where id = ?
    """, user_id)
    self.__conn.commit()
    return resp