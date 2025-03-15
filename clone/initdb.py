import os,sqlite3


dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "db.db")
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            image1 BLOB,
            image2 BLOB
        )
    ''')
    cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            message TEXT,
            time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            file_location TEXT
        )
    ''')
    cursor.execute('''
            CREATE TABLE friends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                friends TEXT
            )
        ''')
    conn.commit()
    conn.close()