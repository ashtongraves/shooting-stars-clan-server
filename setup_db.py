import os
import sqlite3
import sys
from pathlib import Path


def create_shared_key_db(path_to_db: str, create_whitelists: bool = False) -> sqlite3.Connection:
    if Path(path_to_db).is_file():
        delete_db(path_to_db)
    conn = sqlite3.connect(path_to_db)
    conn.execute("""CREATE TABLE
        data(
            location integer,
            world integer,
            minTime integer,
            maxTime integer,
            sharedKey text
        )""")
    if create_whitelists:
        conn.execute("""CREATE TABLE
            scout_whitelist(
                password text UNIQUE ON CONFLICT IGNORE NOT NULL ON CONFLICT IGNORE
            )""")
        conn.execute("""CREATE TABLE
            master_whitelist(
                password text UNIQUE ON CONFLICT IGNORE NOT NULL ON CONFLICT IGNORE
            )""")
    conn.commit()
    return conn


def delete_db(path_to_db: str) -> None:
    if not Path(path_to_db).is_file():
        raise ValueError
    os.remove(Path(path_to_db))


if __name__ == '__main__':
    if len(sys.argv) == 2 and not Path(sys.argv[1]).exists():
        create_shared_key_db(sys.argv[1], create_whitelists=True)
    elif Path(sys.argv[1]).exists():
        print(f'ERROR: Database already exists at {Path(sys.argv[1])}')
    else:
        print('Usage: python setup_db.py [PATH_TO_DB_TO_CREATE]')
