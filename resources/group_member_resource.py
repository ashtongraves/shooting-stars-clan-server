import falcon
import sqlite3
import json
from hooks import hook_validate_group_member

class GroupMemberResource:
  def __init__(self, conn: sqlite3.Connection):
    self.__conn = conn

  def on_get(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    results = self.__conn.execute("""
      select group_members.id, users.name, groups.name
      from group_members
      inner join groups
        on groups.id = group_members.group_id
      inner join users
        on users.id = group_members.user_id
    """).fetchAll()
    output = []
    for row in results:
      resultObject = {
        'id': row['id'],
        'user': row['users.name'],
        'group': row['groups.name']
      }
      output.append(resultObject)
    resp.text = json.dumps(output)
    return resp
  
  @falcon.before(hook_validate_group_member)
  def on_put(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    group_members = req.body
    self.__conn.execute("delete from group_members")
    for member in group_members:
      user_id = int(member.user_id)
      group_id = int(member.group_id)
      self.__conn.execute("""
        insert into group_members(user_id, group_id)
        values(?, ?)
      """, user_id, group_id)
    self.__conn.commit()
    return resp