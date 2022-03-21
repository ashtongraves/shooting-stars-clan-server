import os
import sqlite3
from pathlib import Path
from constants import VALID_LOCATIONS, VALID_WORLDS, DATABASE_PATH

def init_db(conn: sqlite3.Connection):
    conn.execute("""CREATE TABLE IF NOT EXISTS
        settings(
            id integer primary key autonicrement not null,
            admin_password text not null,
            server_password text not null,
            date_modified datetime default current_timestamp not null
        )
    )""")
    conn.execute("""INSERT INTO settings(admin_password, server_password)
        values ('default', 'default')
    """)
    conn.execute("""CREATE TABLE IF NOT EXISTS
        users(
            id integer primary key autonicrement not null,
            username text UNIQUE not null,
        )
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS
        groups(
            id integer primary key autonicrement  not null,
            name text check(name in ('scout', 'whitelist')) not null,
            date_modified datetime default current_timestamp not null
        )
    )""")
    conn.execute("""INSERT INTO groups(name)
        values
            ('scout'),
            ('whitelist')
    """)
    conn.execute("""CREATE TABLE IF NOT EXISTS
        group_membership(
            id integer primary key autoincrement not null,
            user_id integer not null,
            group_id integer not null,
            date_modified datetime default current_timestamp not null
        )
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS
        stars(
            location integer not null,
            world integer not null,
            minTime integer,
            maxTime integer,
            PRIMARY KEY(location, world)
    )""")
    conn.commit()
    return conn

if __name__ == '__main__':
    if Path(DATABASE_PATH).exists():
        print(f'ERROR: Database already exists at {Path(DATABASE_PATH)}')
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        init_db(conn)