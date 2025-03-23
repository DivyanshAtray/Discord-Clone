import os
import sqlite3

dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "db.db")

# Connect to the database (create if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Enable WAL mode for better concurrency
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA foreign_keys=ON;")  # Enable foreign key constraints

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        image1 BLOB,
        image2 BLOB
    )
''')

# Create messages table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        user_id INTEGER,
        friend_id INTEGER,
        message TEXT,
        file_location TEXT,
        reply_to INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        seen INTEGER DEFAULT 0,  -- Add seen column, default to 0 (unseen)
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (friend_id) REFERENCES users(id)
    )
''')

# Create friends table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER PRIMARY KEY,
        friends TEXT,
        incoming_request TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
''')

# Migration: Add timestamp column if it doesn't exist (for existing databases)
try:
    cursor.execute('ALTER TABLE messages ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP')
except sqlite3.OperationalError:
    # Column already exists, no action needed
    pass

conn.commit()
conn.close()

print(f"Database initialized at {db_path}")