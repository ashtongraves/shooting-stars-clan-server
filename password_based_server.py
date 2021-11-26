import os
import sqlite3
from wsgiref.simple_server import make_server

import falcon

from password_based_shooting_stars_resource import PasswordBasedShootingStarsResource


def create_app(conn: sqlite3.Connection):
    app = falcon.App()
    # Resources are represented by long-lived class instances
    shooting_stars_resource = PasswordBasedShootingStarsResource(conn)
    app.add_route('/shooting_stars', shooting_stars_resource)
    app.add_route('/audit', shooting_stars_resource, suffix='separate')
    app.add_route('/whitelist', shooting_stars_resource, suffix='whitelist')
    app.add_static_route('/portal', os.environ['STATIC_ASSETS_FOLDER'])
    return app


if __name__ == '__main__':
    server_conn = sqlite3.connect(os.environ['SM_SHOOTING_STARS_DB'])
    server_conn.row_factory = sqlite3.Row
    with make_server('', int(os.environ['SM_SHOOTING_STARS_PORT']), create_app(server_conn)) as httpd:
        print(f'Serving on port {os.environ["SM_SHOOTING_STARS_PORT"]}...')

        # Serve until process is killed
        httpd.serve_forever()
