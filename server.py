import os
import sqlite3

import falcon
from wsgiref.simple_server import make_server

from base_shooting_stars_resource import BaseShootingStarsResource


def create_app(conn: sqlite3.Connection, clazz):
    # falcon.App instances are callable WSGI apps
    # in larger applications the app is created in a separate file
    app = falcon.App()

    # Resources are represented by long-lived class instances
    shooting_stars_resource = clazz(conn)

    # things will handle all requests to the '/things' URL path
    app.add_route('/shooting_stars', shooting_stars_resource)
    # app.add_route('/star_miners', star_miners_resource)
    # app.add_route('/star_miners_whitelist', star_miners_resource, suffix='whitelist')
    return app


if __name__ == '__main__':
    server_conn = sqlite3.connect(os.environ['SHOOTING_STARS_DB'])
    server_conn.row_factory = sqlite3.Row
    with make_server('', 8000, create_app(server_conn, BaseShootingStarsResource)) as httpd:
        print('Serving on port 8000...')

        # Serve until process is killed
        httpd.serve_forever()