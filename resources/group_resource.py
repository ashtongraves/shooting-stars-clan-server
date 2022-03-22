import falcon
import sqlite3
import json

class GroupResource:
  def __init__(self, conn: sqlite3.Connection):
    self.__conn = conn

  def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    results = self.__conn.execute("select id, name from groups").fetchAll()
    output = []
    for row in results:
      resultObject = {
        'id': row['id'],
        'name': row['name'],
      }
      output.append(resultObject)
    resp.text = json.dumps(output)
    return resp