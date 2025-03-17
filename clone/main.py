from flask import Flask,render_template, request, session, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os,base64
import random
import string,sqlite3

app = Flask(__name__)
app.secret_key = "your_secret_key"
socketio = SocketIO(app)


# File upload configurations
dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "db.db")
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

@app.route('/get-friend-data', methods=['GET'])
def get_user_data():
    user_id = request.args.get('id')  # Get 'id' from query parameters
    if not user_id:
        return jsonify({"error": "No 'id' parameter provided"}), 400

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query the friends table for the specific user ID
        cursor.execute('SELECT friends, incoming_request FROM friends WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()

        if row:
            response = {
                "friends": row["friends"],
                "incoming_request": row["incoming_request"]
            }
        else:
            response = {"error": f"No user found with id {user_id}"}
        print(response)
        conn.close()
        return jsonify(response), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/request-friend')
def request_friend():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    # Get the friend ID
    friend_id = request.args.get('friendId', type=int)

    # Check for missing parameters
    if not user_id or not friend_id:
        conn.close()
        return jsonify({"error": "Missing 'id' or 'friend_id' parameter"}), 400

    # Ensure that the user isn't sending a request to themselves
    if user_id == friend_id:
        conn.close()
        return jsonify({"error": "You cannot send a friend request to yourself"}), 400

    try:
        # Check if there is already an incoming request from the same ID
        cursor.execute('SELECT incoming_request FROM friends WHERE user_id = ?', (user_id,))
        incoming_requests = cursor.fetchone()

        if incoming_requests and incoming_requests[0]:  # If there are existing incoming requests
            # Parse the delimited string into a list
            incoming_request_list = incoming_requests[0].split(',')

            # Check if the friendId is already in the incoming request list
            if str(friend_id) in incoming_request_list:
                conn.close()
                return jsonify(
                    {"error": "A friend request from this user already exists. Please wait for them to respond."}), 400

        # Check if the friend is already in the user's friends list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (user_id,))
        friends_data = cursor.fetchone()
        if friends_data and friends_data[0]:  # If there are existing friends
            # Parse the delimited string into a list
            friends_list = friends_data[0].split(',')

            if str(friend_id) in friends_list:
                conn.close()
                return jsonify({"error": "This user is already in your friends list."}), 400

        # Add the friendId to the incoming_request list
        if incoming_requests and incoming_requests[0]:
            # Append to the existing incoming_request string
            incoming_request_list.append(str(friend_id))
            updated_requests = ','.join(incoming_request_list)
            print(updated_requests)
            cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (updated_requests, user_id))
        else:
            print("new entry must be added ig")
            # Create a new incoming_request entry
            cursor.execute('INSERT INTO friends(user_id,incoming_request) VALUES(?,?)', (user_id,str(friend_id) ))

        conn.commit()
        conn.close()
        return jsonify({"status": "Friend request sent successfully."}), 200

    except Exception as e:
        conn.close()
        print(e)
        return jsonify({"error": str(e)}), 500


@app.route('/add_friend')
def add_friend():
    print("im called")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]
    print(user_id)

    # Get the friend ID (the ID of the user sending the friend request)
    friend_id = request.args.get('id', type=int)
    print(friend_id)
    # Check for missing parameters
    if not user_id or not friend_id:
        conn.close()
        return jsonify({"error": "Missing 'id' or 'friend_id' parameter"}), 400

    try:
        # Check if there is an incoming friend request from the friendId
        cursor.execute('SELECT incoming_request FROM friends WHERE user_id = ?', (user_id,))
        incoming_requests = cursor.fetchone()

        if not incoming_requests or not incoming_requests[0]:  # If there are no incoming requests
            conn.close()
            return jsonify({"error": "No friend request from this user exists."}), 400

        # Parse the incoming request list
        incoming_request_list = incoming_requests[0].split(',')
        if str(friend_id) not in incoming_request_list:
            conn.close()
            return jsonify({"error": "No friend request from this user exists."}), 400

        # Remove the friendId from the incoming request list
        incoming_request_list.remove(str(friend_id))
        updated_requests = ','.join(incoming_request_list)

        # Update the incoming_request list in the database
        cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (updated_requests, user_id))

        # Add the friendId to the current user's friends list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (user_id,))
        user_friends = cursor.fetchone()
        if user_friends and user_friends[0]:  # If there are existing friends
            user_friends_list = user_friends[0].split(',')
            if str(friend_id) not in user_friends_list:
                user_friends_list.append(str(friend_id))
                updated_user_friends = ','.join(user_friends_list)
            else:
                updated_user_friends = user_friends[0]  # No change
        else:
            updated_user_friends = str(friend_id)  # Create the new friend list if none exists

        # Update the current user's friends list
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (updated_user_friends, user_id))

        # Add the current user's ID to the friend's friends list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (friend_id,))
        friend_friends = cursor.fetchone()
        if friend_friends and friend_friends[0]:  # If the friend already has a friends list
            friend_friends_list = friend_friends[0].split(',')
            if str(user_id) not in friend_friends_list:
                friend_friends_list.append(str(user_id))
                updated_friend_friends = ','.join(friend_friends_list)
            else:
                updated_friend_friends = friend_friends[0]  # No change
        else:
            updated_friend_friends = str(user_id)  # Create the new friends list if none exists

        # Update the friend's friends list
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (updated_friend_friends, friend_id))

        # Commit the changes to the database
        conn.commit()
        conn.close()
        return jsonify({"status": "Friend added successfully!"}), 200

    except Exception as e:
        conn.close()
        print(e)
        return jsonify({"error": str(e)}), 500


@app.route('/login')
def login_page():
    return render_template('login_page.html')

@app.route('/profile',methods=['GET'])
def profile():
    id = request.args.get('id', type=int)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    row=cursor.fetchone()
    if row:
        encoded_image1 = base64.b64encode(row[3]).decode('utf-8')
        encoded_image2 = base64.b64encode(row[4]).decode('utf-8')
        formatted_messages = [
            {
                "username": row[1],
                "image1": encoded_image1,
                "image2": encoded_image2
            }]
        return jsonify(formatted_messages)
    else:
        return jsonify({"error": "ID doesn't exist or not found"}), 404


@app.route('/logout')
def logout():
    # Clear the user session
    session.pop('username', None)
    # Redirect to the login page
    return redirect(url_for('login_page'))

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
            session['username'] = username
            return redirect("/")
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
        conn=sqlite3.connect(db_path)
        cursor=conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?",(username,))
        id=cursor.fetchone()
        data=jsonify({"username": username,"id":id[0]})
        return data
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
    print(data)
    username = data["username"]
    if username is None:
        return
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