from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
import os
import random
import string

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Used for sessions (keep it secure)

# Ensure the 'db.db' exists
db_path = "db.db"
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
    conn.commit()
    conn.close()

# File upload configurations
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Set upload folder


def generate_random_string(length=10):
    """Generate a random string of uppercase, lowercase characters, and digits."""
    chars = string.ascii_letters + string.digits  # Alphabets and numbers
    return ''.join(random.choices(chars, k=length))


@app.route('/')
def login_page():
    return render_template('login_page.html')


@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']

    # Store files as BLOBs in database for image1 and image2
    image1_blob = request.files['image1'].read() if 'image1' in request.files else None
    image2_blob = request.files['image2'].read() if 'image2' in request.files else None

    # Check if user already exists
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    existing_user = cursor.fetchone()

    if existing_user:
        # Check for the password
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        pwd = cursor.fetchone()
        if pwd[0] == password:
            return redirect("/chatroom")
        else:
            flash("User already exists. Please log in.", "danger")
            return redirect(url_for('login_page'))

    # If user doesn't exist, register them
    cursor.execute("INSERT INTO users (username, password, image1, image2) VALUES (?, ?, ?, ?)",
                   (username, password, sqlite3.Binary(image1_blob) if image1_blob else None, sqlite3.Binary(image2_blob) if image2_blob else None))
    conn.commit()
    conn.close()

    session['username'] = username  # Save user in session
    flash("Login successful!", "success")
    return redirect(url_for('chatroom'))



@app.route('/chatroom')
def chatroom():
    # Check if user is logged in
    if 'username' not in session:
        flash("Please log in to access the chatroom.", "warning")
        return redirect(url_for('login_page'))

    return render_template('chatroom.html', username=session['username'])


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        flash("Unauthorized access. Please log in to continue.", "danger")
        return redirect(url_for('login_page'))

    username = session['username']
    message = request.form['message']
    file = request.files.get('file')  # File received via the "send_message" endpoint

    new_file_name = None

    if file:
        # Rename and save the uploaded file
        random_suffix = generate_random_string()
        filename, ext = os.path.splitext(file.filename)
        new_file_name = f"{filename}_{random_suffix}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_file_name))

    # Save the message and file_location in the database
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (username, message, file_location) VALUES (?, ?, ?)",
                   (username, message, new_file_name))
    conn.commit()
    conn.close()
    return jsonify({"response": "gay"})


if __name__ == '__main__':
    app.run(debug=True)
