from flask import Flask,render_template, request, session, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os
import random
import string,sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app)


# File upload configurations
dirname = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(dirname, "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Set upload folder


def generate_random_string(length=10):
    """Generate a random string of uppercase, lowercase characters, and digits."""
    chars = string.ascii_letters + string.digits  # Alphabets and numbers
    return ''.join(random.choices(chars, k=length))



@socketio.on("connect")
def handle_connect():
    # Handle a user connection
    print("A user connected")


@socketio.on("disconnect")
def handle_disconnect():
    # Remove a user from the connected users (if needed)
    print("A user disconnected")

@app.route('/login')
def login_page():
    return render_template('login_page.html')

@app.route('/profile',methods=['POST','GET'])
def profile():
    id = request.args.get('id', type=int)
    print(id)
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    row=cursor.fetchone()
    if row:
        formatted_messages = [
            {
                "username": row[1],
                "image1": row[3],
                "image2": row[4]
            }]
        return formatted_messages
    else:
        return None

@app.route('/messages', methods=['GET'])
def get_last_messages():
    try:
        conn = sqlite3.connect("db.db")
        cursor = conn.cursor()
        # Retrieve the value of 'x' from the 'settings' table
        cursor.execute("SELECT value FROM settings WHERE key = 'message_limit'")
        result = cursor.fetchone()

        if result is None:
            return jsonify({"error": "Setting for 'message_limit' not found"}), 404

        # Extract the number of messages to fetch
        message_limit = int(result[0])

        # Fetch the last 'message_limit' messages
        cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?", (message_limit,))
        messages = cursor.fetchall()

        # Assuming the messages table has columns like ('id', 'user', 'message', 'timestamp')
        formatted_messages = [
            {
                "id": row[0],
                "username": row[1],
                "message": row[2],
                "time": row[3],
                "file_location":row[4]
            }
            for row in messages
        ]

        return jsonify(formatted_messages)
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

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
            flash("User already exists. Please log in.","error")
            return redirect(url_for('login_page'))
    else:
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            flash("User already exists. Please log in.","error")
            return redirect(url_for('login_page'))
        else:
        # If user doesn't exist, register them
            cursor.execute("INSERT INTO users (username, password, image1, image2) VALUES (?, ?, ?, ?)",
                           (username, password, sqlite3.Binary(image1_blob) if image1_blob else None, sqlite3.Binary(image2_blob) if image2_blob else None))
            conn.commit()
            conn.close()

    session['username'] = username  # Save user in session
    flash("Login successful!", "success")
    return redirect(url_for('chatroom'))



@app.route('/')
def chatroom():
    # Check if user is logged in
    if 'username' not in session:
        flash("Please log in to access the chatroom.","error")
        return redirect(url_for('login_page'))

    return render_template('chatroom.html', username=session['username'])


@app.route('/get_username', methods=['GET'])
def get_username():
    username = session.get('username')  # Retrieve the username from the session
    if username:
        return jsonify({"username": username})
    else:
        return jsonify({"error": "No username found"}), 401


@socketio.on("send_message")
def handle_send_message(data):
    """
    Handle incoming messages from users.
    Data format (example):
    {
        "username": "user1",
        "message": "Hello, everyone!"
    }
    """

    username = data["username"]
    message = data["message"]
    print(f"{username}: {message}")

    # Broadcast the received message to all clients
    emit("broadcast_message", {"username": username, "message": message}, broadcast=True)


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        flash("Unauthorized access. Please log in to continue.", "danger")
        return redirect(url_for('login_page'))

    username = session['username']
    print(request.form)
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
    return jsonify({"status": "success"})


if __name__ == '__main__':
    socketio.run(app,debug=True,allow_unsafe_werkzeug=True)