import os, sqlite3

dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "db.db")

# Delete the old db if it exists so we start fresh with ALL correct columns
if os.path.exists(db_path):
    os.remove(db_path)
    print("Old database deleted.")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
conn.execute("PRAGMA journal_mode=WAL;")

# 1. Users Table (matches /edit_profile and /profile routes)
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        image1 BLOB,
        image2 BLOB,
        image1_format TEXT,
        image2_format TEXT
    )
''')

# 2. Messages Table (matches /send_message and /messages routes)
# Note: Renamed 'time' to 'timestamp' and added 'friend_id', 'seen', and 'reply_to'
cursor.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        user_id INTEGER, 
        friend_id INTEGER,
        message TEXT,
        file_location TEXT,
        reply_to INTEGER,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        seen INTEGER DEFAULT 0,
        file_timestamp DATETIME
    )
''')

# 3. Friends Table
cursor.execute('''
    CREATE TABLE friends (
        user_id INTEGER PRIMARY KEY,
        friends TEXT,
        incoming_request TEXT
    )
''')

conn.commit()
conn.close()
print("Database recreated successfully with all columns matching main.py!")