import os
import sqlite3
import falcon
import jwt
import bcrypt
from wsgiref.simple_server import make_server
from resources.star_resource import StarResource
from resources.user_resource import UserResource
from resources.group_resource import GroupResource
from resources.group_member_resource import GroupMemberResource
from resources.settings_resource import SettingsResource
from constants import DATABASE_PATH, PORT, ERROR_MSG_AUTHORIZATION_FAIL
from hooks import hook_validate_auth

class ValidatePassword:
  @falcon.before(hook_validate_auth)
  def process_request(self, req, resp, conn):
    if req.path != "/stars":
      # Retrieve hashed password
      cur = conn.cursor()
      cur.execute('select server_password from settings')
      password = cur.fetchall()[0]

      # Decrypt key
      encrypted_token = req.auth
      token = jwt.decode(encrypted_token, password, algorithm="HS256")

      # Verify user has permissions to the route they're trying to access
      user = token.user
      group = set()
      match req.method:
        case "GET":
          group="whitelist"
        case "PATCH":
          group = "scout"

      cur.execute("""
      select user_id
      from group_members
      inner join groups
        on group_member.group_id = groups.id
      inner join users
        on group_member.user_id = users.id
      where group.name = '?' and user.name = ?
      """, group, user)
      results = cur.fetchall()

      if len(results) <= 0:
        raise falcon.HTTPInvalidParam(title='Unauthorized', description=ERROR_MSG_AUTHORIZATION_FAIL)
    else:
      password = bcrypt.hashpw(req.auth.strip(), bcrypt.gensalt(14))
      cur = conn.cursor()
      cur.execute("""
        select id
        from settings
        where admin_password = ?
      """, password)
      results = cur.fetchall()
      if len(results) <= 0:
        raise falcon.HTTPInvalidParam(title='Unauthorized', description=ERROR_MSG_AUTHORIZATION_FAIL)


def create_server(conn: sqlite3.Connection):
    app = falcon.App()
    app = falcon.API(middleware=[ValidatePassword(conn)])

    # Create routes
    app.add_route('/stars', StarResource(conn))
    app.add_route('/users', UserResource(conn))
    app.add_route('/groups', GroupResource(conn))
    app.add_route('/group_members', GroupMemberResource(conn))
    app.add_route('/settings', SettingsResource(conn))

    return app

if __name__ == '__main__':
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    with make_server('', PORT, create_server(conn)) as httpd:
        print(f'Serving on port {PORT}...')

        # Serve until process is killed
        httpd.serve_forever()