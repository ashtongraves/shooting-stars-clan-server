import sqlite3
from pathlib import Path
from constants import VALID_LOCATIONS, VALID_WORLDS, DATABASE_PATH

def init_db(conn: sqlite3.Connection):
  conn.execute("""create table if not exists settings(
      id integer primary key autoincrement not null,
      admin_password text not null,
      server_password text not null,
      date_modified datetime default current_timestamp not null
  )""")
  conn.execute("""insert into settings(admin_password, server_password)
    values ('default', 'default')
  """)
  conn.execute("""create table if not exists users(
      id integer primary key autoincrement not null,
      name text UNIQUE not null,
      date_modified datetime default current_timestamp not null
  )""")
  conn.execute("""create table if not exists groups(
      id integer primary key autoincrement  not null,
      name text check(name in ('scout', 'whitelist')) not null,
      date_modified datetime default current_timestamp not null
  )""")
  conn.execute("""insert into groups(name)
    values
      ('scout'),
      ('whitelist')
  """)
  conn.execute("""create table if not exists group_membership(
      id integer primary key autoincrement not null,
      user_id integer not null,
      group_id integer not null,
      date_modified datetime default current_timestamp not null
  )""")
  conn.execute("""create table if not exists stars(
      location integer not null,
      world integer not null,
      minTime integer,
      maxTime integer,
      PRIMARY KEY(location, world)
  )""")
  for world in VALID_WORLDS:
    for location in VALID_LOCATIONS:
      conn.execute("insert into stars(world, location) values (?, ?)", (world, location))
  conn.commit()
  return conn

if __name__ == '__main__':
  if Path(DATABASE_PATH).exists():
    print(f'ERROR: Database already exists at {Path(DATABASE_PATH)}')
  else:
    conn = sqlite3.connect(DATABASE_PATH)
    init_db(conn)