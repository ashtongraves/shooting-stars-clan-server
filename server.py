import os
import sqlite3
import falcon
from wsgiref.simple_server import make_server
from resources.stars_resource import StarsResource
from resources.admin_resource import UserResource
from resources.admin_resource import GroupResource
from resources.admin_resource import GroupMemberResource
from resources.admin_resource import SettingsResource
from constants import PASSWORD_ENABLED, DATABASE_PATH, PORT

def create_server(conn: sqlite3.Connection):
    app = falcon.App()
    
    # Create routes
    app.add_route('/stars', StarsResource(conn))
    if PASSWORD_ENABLED:
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