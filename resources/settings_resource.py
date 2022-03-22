import falcon
import sqlite3
import json
import bcrypt
from hooks import hook_validate_settings

class SettingsResource:
  def __init__(self, conn: sqlite3.Connection):
    self.__conn = conn
  
  @falcon.before(hook_validate_settings)
  def on_patch(self, req: falcon.request.Request, resp: falcon.response.Response):
    resp.status = falcon.HTTP_200
    server_password = req.body.server_password.strip()
    admin_password = req.body.admin_password.strip()
    if server_password:
      server_password = bcrypt.hashpw(server_password, bcrypt.gensalt(14))
      self.__conn.execute("""
          UPDATE settings
          SET server_password = ?
      """, server_password)
    if admin_password:
      admin_password = bcrypt.hashpw(admin_password, bcrypt.gensalt(14))
      self.__conn.execute("""
          UPDATE settings
          SET admin_password = ?
      """, admin_password)
    self.__conn.commit()
    return resp