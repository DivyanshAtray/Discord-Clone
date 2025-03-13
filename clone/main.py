from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Ensure users.db exists
db_path = "users.db"
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            image1 BLOB,
            image2 BLOB
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def login_page():
    return render_template('login_page.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    password = request.form['password']
    image1 = request.files['image1'].read() if 'image1' in request.files else None
    image2 = request.files['image2'].read() if 'image2' in request.files else None

    # Store in database
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, password, image1, image2) VALUES (?, ?, ?, ?)",
                   (username, password, image1, image2))
    conn.commit()
    conn.close()

    flash("Login successful!", "success")
    return redirect(url_for('chatroom'))

@app.route('/chatroom')
def chatroom():
    return render_template('chatroom.html')

# API to process messages
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json  # Get JSON data
    user_message = data.get("message", "")  # Extract message
    response_message = user_message[::-1]  # Reverse the text
    return jsonify({"response": response_message})  # Send JSON response

if __name__ == '__main__':
    app.run(debug=True)
