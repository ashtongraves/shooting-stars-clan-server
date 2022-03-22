import falcon
import sqlite3
import json
from hooks import hook_validate_star

class StarResource:
  def __init__(self, conn: sqlite3.Connection):
    self.__conn = conn

  def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    results = self.__conn.execute("select location, world, minTime, maxTime FROM stars WHERE maxTime >= current_timestamp").fetchAll()
    output = []
    for row in results:
      resultObject = {
        'location': row['location'],
        'world': row['world'],
        'minTime': row['minTime'],
        'maxTime': row['maxTime']
      }
      output.append(resultObject)
    resp.text = json.dumps(output)
    return resp
  
  @falcon.before(hook_validate_star)
  def on_patch(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    star = {
      'world': req.body.world,
      'location': req.body.location,
      'min_time': req.body.min_time,
      'max_time': req.body.max_time
    }

    results = self.__conn.execute("select minTime, maxTime FROM stars WHERE world = ? and location = ?", star.world, star.location).fetchAll()
    current_min_time = results[0],
    current_max_time = results[1]
    self.__conn.execute("""
        UPDATE stars
        SET minTime = ?, maxTime = ?
        WHERE world = ? and location = ?
    """, star.min_time, star.max_time, star.world, star.location)
    self.__conn.commit()
    return resp