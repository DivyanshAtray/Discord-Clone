from flask import Flask,render_template, request, session, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os,base64
import random
import string,sqlite3
import base64

from datetime import datetime
from werkzeug.utils import secure_filename
from flask import send_from_directory
import threading
import time
from datetime import datetime, timedelta

online_users = set()  # To track online user IDs

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB limit
app.secret_key = "your_secret_key"
socketio = SocketIO(app)


# File upload configurations
dirname = os.path.dirname(__file__)
db_path = os.path.join(dirname, "db.db")
db_path = os.path.abspath(db_path)
print(f"Flask db_path: {os.path.abspath(db_path)}")
UPLOAD_FOLDER = os.path.join(dirname, "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Set upload folder


def generate_random_string(length=10):
    """Generate a random string of uppercase, lowercase characters, and digits."""
    chars = string.ascii_letters + string.digits  # Alphabets and numbers
    return ''.join(random.choices(chars, k=length))



def get_user_friends(user_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT friends FROM friends WHERE user_id = ?", (user_id,))
    friends = cursor.fetchone()
    if friends and friends[0]:  # Check if friends exists and is not None
        friends = friends[0]  # Get the comma-separated string (e.g., "1,2,3")
        friends = friends.split(',')
        friends_data = []
        for friend in friends:
            cursor.execute("SELECT username, image1, image2 FROM users WHERE id = ?", (friend,))
            row = cursor.fetchone()
            if row:
                # Encode the BLOB data to base64
                image1_base64 = base64.b64encode(row[1]).decode('utf-8') if row[1] else None
                image2_base64 = base64.b64encode(row[2]).decode('utf-8') if row[2] else None
                friends_data.append({
                    "username": row[0],
                    "id": friend,
                    "pfp": image1_base64,  # Now a base64-encoded string
                    "banner": image2_base64
                })
        conn.close()
        return friends_data
    else:
        conn.close()
        return "No friends"

@socketio.on("connect")
def handle_connect():
    if 'username' not in session:
        print("No username in session, cannot connect")
        return
    username = session['username']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()
    if user_id:
        user_id = user_id[0]
        socketio.server.enter_room(sid=request.sid, room=str(user_id))
        print(f"User {username} (ID: {user_id}) connected and joined room {user_id}")

        # Add user to online_users set
        online_users.add(user_id)
        print(f"Online users: {online_users}")

        # Get the user's friends
        cursor.execute("SELECT friends FROM friends WHERE user_id = ?", (user_id,))
        friends = cursor.fetchone()
        if friends and friends[0]:
            friend_ids = friends[0].split(',')
            print(f"User {user_id} has friends: {friend_ids}")
            # Broadcast online status to friends
            for friend_id in friend_ids:
                if friend_id:
                    print(f"Broadcasting online status of user {user_id} to friend {friend_id}")
                    emit("user_status", {"user_id": user_id, "status": "online"}, room=str(friend_id))
        else:
            print(f"User {user_id} has no friends")
    else:
        print(f"No user found for username {username}")
    conn.close()

@socketio.on("disconnect")
def handle_disconnect():
    if 'username' not in session:
        print("No username in session, cannot disconnect")
        return
    username = session['username']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()
    if user_id:
        user_id = user_id[0]
        print(f"User {username} (ID: {user_id}) disconnected")

        # Remove user from online_users set
        if user_id in online_users:
            online_users.remove(user_id)
            print(f"Online users after disconnect: {online_users}")

            # Get the user's friends
            cursor.execute("SELECT friends FROM friends WHERE user_id = ?", (user_id,))
            friends = cursor.fetchone()
            if friends and friends[0]:
                friend_ids = friends[0].split(',')
                print(f"User {user_id} has friends: {friend_ids}")
                # Broadcast offline status to friends
                for friend_id in friend_ids:
                    if friend_id:
                        print(f"Broadcasting offline status of user {user_id} to friend {friend_id}")
                        emit("user_status", {"user_id": user_id, "status": "offline"}, room=str(friend_id))
            else:
                print(f"User {user_id} has no friends")
        else:
            print(f"User {user_id} was not in online_users set")
    else:
        print(f"No user found for username {username}")
    conn.close()

@socketio.on("send_message")
def handle_send_message(data):
    username = data.get("username")
    if not username:
        print("No username provided in send_message event")
        return

    message = data.get("message")
    friend_id = data.get("friendId")  # Match the client-side field name
    user_id = data.get("userId")
    reply_to = data.get("replyTo")
    timestamp = data.get("timestamp")
    file_location = data.get("file_location")
    message_id = data.get("message_id")

    # Validate required fields
    if not friend_id:
        print("No friendId provided in send_message event")
        return
    if not user_id:
        print("No userId provided in send_message event")
        return
    if not message and not file_location:
        print("No message or file_location provided in send_message event")
        return
    if not message_id:
        print("No message_id provided in send_message event")
        return

    # Log the message for debugging
    print(f"Received send_message: {username} (ID: {user_id}) to Friend ID {friend_id}: {message}")

    # Prepare the message data to broadcast
    message_data = {
        "username": username,
        "message": message,
        "userId": user_id,
        "friendId": friend_id,
        "replyTo": reply_to,
        "timestamp": timestamp,
        "file_location": file_location,
        "message_id": message_id
    }

    # Send to sender (seen = 1)
    message_data_sender = message_data.copy()
    message_data_sender["seen"] = 1
    print(f"Emitting broadcast_message to sender room {user_id}")
    emit("broadcast_message", message_data_sender, room=str(user_id))

    # Send to recipient (seen = 0)
    message_data_recipient = message_data.copy()
    message_data_recipient["seen"] = 0
    print(f"Emitting broadcast_message to recipient room {friend_id}")
    emit("broadcast_message", message_data_recipient, room=str(friend_id))

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
        cursor.execute('SELECT incoming_request FROM friends WHERE user_id = ?', (friend_id,))
        incoming_requests = cursor.fetchone()

        if incoming_requests and incoming_requests[0]:  # If there are existing incoming requests
            # Parse the delimited string into a list
            incoming_request_list = incoming_requests[0].split(',')

            # Check if the friendId is already in the incoming request list
            if str(user_id) in incoming_request_list:
                conn.close()
                return jsonify(
                    {"error": "You already sent this user a friend request. Please wait for them to respond."}), 400

        # Check if the friend is already in the user's friends list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (friend_id,))
        friends_data = cursor.fetchone()
        if friends_data and friends_data[0]:  # If there are existing friends
            # Parse the delimited string into a list
            friends_list = friends_data[0].split(',')

            if str(user_id) in friends_list:
                conn.close()
                return jsonify({"error": "This user is already in your friends list."}), 400

        # Add the friendId to the incoming_request list
        if incoming_requests and incoming_requests[0]:
            # Append to the existing incoming_request string
            incoming_request_list.append(str(user_id))
            updated_requests = ','.join(incoming_request_list)
            print(updated_requests)
            cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (updated_requests, friend_id))
        else:
            print("new entry must be added ig")
            # Create a new incoming_request entry
            cursor.execute('''SELECT friends FROM friends WHERE user_id=?''',(friend_id,))
            frd = cursor.fetchone()
            if not frd:
                cursor.execute('INSERT INTO friends(user_id,incoming_request) VALUES(?,?)', (friend_id,str(user_id)  ))
            else:
                cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (str(user_id), friend_id))
        conn.commit()
        # --- NEW: LIVE NOTIFICATION ---
        # This sends the data to the recipient's unique Socket.IO room
        socketio.emit('new_friend_request', {
            'sender_id': user_id,
            'sender_username': session['username']
        }, room=str(friend_id))
        # ------------------------------

        conn.close()
        return jsonify({"status": "Friend request sent successfully."}), 200

    except Exception as e:
        if conn:
            conn.close()
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/login')
def login():
    return render_template('actual_login.html')

@app.route('/add_friend', methods=['GET'])
def add_friend():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"}), 401

    friend_id = request.args.get('id', type=int)
    if not friend_id:
        return jsonify({"error": "Friend ID is required"}), 400

    # FIX FOR VS CODE: Initialize variables before the 'try' block
    user_id = None
    my_username = None
    my_pfp_blob = None
    friend_username = None
    friend_pfp_blob = None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Get the current user's ID, username, and PFP
        cursor.execute('SELECT id, username, image1 FROM users WHERE username = ?', (session['username'],))
        user_row = cursor.fetchone()
        if not user_row:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        user_id = user_row[0]
        my_username = user_row[1]
        my_pfp_blob = user_row[2]

        # 2. Get the friend's username and PFP
        cursor.execute('SELECT username, image1 FROM users WHERE id = ?', (friend_id,))
        friend_row = cursor.fetchone()
        if not friend_row:
            conn.close()
            return jsonify({"error": "Friend not found"}), 404
        
        friend_username = friend_row[0]
        friend_pfp_blob = friend_row[1]

        # Get the current user's friend data
        cursor.execute('SELECT friends, incoming_request FROM friends WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            cursor.execute('INSERT INTO friends (user_id, friends, incoming_request) VALUES (?, ?, ?)', (user_id, '', ''))
            conn.commit()
            friends = []
            incoming_requests = []
        else:
            friends = user_data[0].split(",") if user_data[0] else []
            incoming_requests = user_data[1].split(",") if user_data[1] else []

        if str(friend_id) not in incoming_requests:
            conn.close()
            return jsonify({"error": "No friend request from this user"}), 400

        # Add friend to the current user's friend list
        if str(friend_id) not in friends:
            friends.append(str(friend_id))
        friends = [f for f in friends if f]  
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (",".join(friends), user_id))

        # Remove the friend request from incoming requests
        incoming_requests.remove(str(friend_id))
        incoming_requests = [r for r in incoming_requests if r]  
        cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (",".join(incoming_requests) if incoming_requests else '', user_id))

        # Add the current user to the friend's friend list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (friend_id,))
        friend_data = cursor.fetchone()
        if not friend_data:
            cursor.execute('INSERT INTO friends (user_id, friends, incoming_request) VALUES (?, ?, ?)', (friend_id, '', ''))
            conn.commit()
            friend_friends = []
        else:
            friend_friends = friend_data[0].split(",") if friend_data[0] else []

        if str(user_id) not in friend_friends:
            friend_friends.append(str(user_id))
        friend_friends = [f for f in friend_friends if f]  
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (",".join(friend_friends) if friend_friends else '', friend_id))

        # Save to database
        conn.commit()

        # --- LIVE SIDEBAR UPDATE ---
        import base64
        my_pfp = base64.b64encode(my_pfp_blob).decode('utf-8') if my_pfp_blob else None
        friend_pfp = base64.b64encode(friend_pfp_blob).decode('utf-8') if friend_pfp_blob else None

        # Tell YOUR browser to add the friend
        socketio.emit('friend_added', {
            'id': friend_id,
            'username': friend_username,
            'pfp': friend_pfp
        }, room=str(user_id))

        # Tell the FRIEND'S browser to add you
        socketio.emit('friend_added', {
            'id': user_id,
            'username': my_username,
            'pfp': my_pfp
        }, room=str(friend_id))

    except Exception as e:
        conn.close()
        print(f"Error in /add_friend: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    conn.close()
    return jsonify({"status": "ok"})


@app.route('/remove_request')
def remove_request():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    # Get the friend ID (the ID of the user who sent the request)
    friend_id = request.args.get('id', type=int)

    # Check for missing parameters
    if not user_id or not friend_id:
        conn.close()
        return jsonify({"error": "Missing 'id' parameter"}), 400

    try:
        # Check if there is an incoming friend request from the friendId
        cursor.execute('SELECT incoming_request FROM friends WHERE user_id = ?', (user_id,))
        incoming_requests = cursor.fetchone()

        if not incoming_requests or not incoming_requests[0]:
            conn.close()
            return jsonify({"error": "No friend request from this user exists."}), 400

        # Parse the incoming request list
        incoming_request_list = incoming_requests[0].split(',')
        if str(friend_id) not in incoming_request_list:
            conn.close()
            return jsonify({"error": "No friend request from this user exists."}), 400

        # Remove the friendId from the incoming request list
        incoming_request_list.remove(str(friend_id))
        updated_requests = ','.join(incoming_request_list) if incoming_request_list else None

        # Update the incoming_request list in the database
        cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (updated_requests, user_id))

        conn.commit()
        conn.close()
        return jsonify({"status": "Friend request removed successfully!"}), 200

    except Exception as e:
        conn.close()
        print(e)
        return jsonify({"error": str(e)}), 500


@app.route('/profile', methods=['GET'])
def profile():
    id = request.args.get('id', type=int)
    print(f"Profile ID: {id}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    print(f"Profile row: {row}")
    if row:
        # Handle None values for images
        encoded_image1 = base64.b64encode(row[3]).decode('utf-8') if row[3] else ""
        encoded_image2 = base64.b64encode(row[4]).decode('utf-8') if row[4] else ""
        # Map database format to MIME type format
        image1_format = row[5] if len(row) > 5 else "png"  # Default to PNG if not set
        image2_format = row[6] if len(row) > 6 else "png"
        # Ensure format matches MIME type (e.g., 'jpeg' -> 'jpeg', 'png' -> 'png', 'gif' -> 'gif')
        image1_format_mime = image1_format if image1_format in ['png', 'gif', 'jpeg'] else 'png'
        image2_format_mime = image2_format if image2_format in ['png', 'gif', 'jpeg'] else 'png'
        print(f"Encoded image1 length: {len(encoded_image1)}, format: {image1_format_mime}")
        print(f"Encoded image2 length: {len(encoded_image2)}, format: {image2_format_mime}")
        formatted_messages = [{
            "username": row[1],
            "image1": encoded_image1,
            "image2": encoded_image2,
            "image1_format": image1_format_mime,
            "image2_format": image2_format_mime
        }]
        conn.close()
        return jsonify(formatted_messages)
    else:
        conn.close()
        print(f"No user found for ID: {id}")
        return jsonify({"error": "ID doesn't exist or not found"}), 404

@app.route('/logout')
def logout():
    # Clear the user session
    session.pop('username', None)
    # Redirect to the login page
    return redirect('/login')


@app.route('/messages')
def get_messages():
    friend_id = request.args.get('friend_id', type=int)
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    cursor.execute('''
        SELECT * FROM messages 
        WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
        AND timestamp >= datetime('now', '-1 month')
        ORDER BY id ASC
        LIMIT ? OFFSET ?
    ''', (user_id, friend_id, friend_id, user_id, limit, offset))

    messages = cursor.fetchall()
    messages_data = []
    for message in messages:
        timestamp = message[7]
        if timestamp:
            timestamp = f"{timestamp}Z"
        messages_data.append({
            'id': message[0],
            'username': message[1],
            'user_id': message[2],
            'friend_id': message[3],
            'message': message[4],
            'file_location': message[5],
            'reply_to': message[6],
            'timestamp': timestamp,
            'seen': message[8],
            'file_timestamp': message[9]  # Include file_timestamp
        })

    conn.close()
    return jsonify(messages_data)

def delete_old_messages():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM messages WHERE timestamp < datetime('now', '-1 month')")
        conn.commit()
        print("Deleted messages older than 1 month.")
    except Exception as e:
        print(f"Error deleting old messages: {e}")
    finally:
        conn.close()

@app.route('/submit', methods=['POST'])
def submit():
    print("Received /submit request")
    if 'CONTENT_LENGTH' in request.environ:
        print(f"Request content length: {int(request.environ['CONTENT_LENGTH']) / 1024 / 1024} MB")
    username = request.form['username']
    password = request.form['password']
    # Get the base64-encoded cropped images
    image1_base64 = request.form.get('image1-base64')
    image2_base64 = request.form.get('image2-base64')
    image1_format = request.form.get('image1-format', 'png')  # Default to PNG if not specified
    image2_format = request.form.get('image2-format', 'png')

    print(f"Total request form data size: {sum(len(k) + len(v) for k, v in request.form.items()) / 1024 / 1024} MB")
    if image1_base64:
        print(f"Image1 base64 size: {len(image1_base64) / 1024 / 1024} MB")
        print(f"Image1 format: {image1_format}")
    if image2_base64:
        print(f"Image2 base64 size: {len(image2_base64) / 1024 / 1024} MB")
        print(f"Image2 format: {image2_format}")

    # Decode base64 strings into binary data for BLOB storage
    image1_blob = None
    image2_blob = None
    if image1_base64:
        try:
            image1_blob = base64.b64decode(image1_base64)
        except Exception as e:
            print(f"Error decoding image1 base64: {e}")
            flash("Error processing profile picture.", "error")
            return redirect(url_for('signup'))
    if image2_base64:
        try:
            image2_blob = base64.b64decode(image2_base64)
        except Exception as e:
            print(f"Error decoding image2 base64: {e}")
            flash("Error processing banner image.", "error")
            return redirect(url_for('signup'))

    # Check if user already exists
    conn = sqlite3.connect(db_path)  # Use db_path for consistency
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash("User already exists. Please log in.", "error")
        conn.close()
        return redirect('/login')
    else:
        # If user doesn't exist, register them
        cursor.execute("INSERT INTO users (username, password, image1, image2) VALUES (?, ?, ?, ?)",
                       (username, password, sqlite3.Binary(image1_blob) if image1_blob else None, sqlite3.Binary(image2_blob) if image2_blob else None))
        # Get the ID of the newly inserted user
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]
        # Initialize the friends table entry for the new user
        cursor.execute("INSERT INTO friends (user_id, friends, incoming_request) VALUES (?, ?, ?)",
                       (user_id, None, None))
        conn.commit()
        # Set user ID in session
        session['id'] = user_id
        conn.close()

    session['username'] = username  # Save user in session
    flash("Sign-up successful!", "success")
    return redirect(url_for('chatroom'))

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    existing_user = cursor.fetchone()
    if existing_user:
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        user_id = row[0]
        session['username'] = username  # Save user in session
        session['id'] = user_id
        conn.close()  # Close the connection
        return redirect("/")
    else:
        conn.close()  # Close the connection
        flash("Invalid username or password. Please sign up if you don't have an account.", "error")
        return redirect(url_for('login'))  # Redirect back to the login page

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/')
def chatroom():
    friend_id = request.args.get('friend_id')
    # Check if user is logged in
    if 'username' not in session:
        flash("Please log in to access the chatroom.","error")
        return redirect('/login')
    
    # Fetch user's data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT image1, image2 FROM users WHERE id = ?", (session['id'],))
    row = cursor.fetchone()
    
    # Encode the user's PFP and banner to base64
    user_pfp = base64.b64encode(row[0]).decode('utf-8') if row[0] else None
    user_banner = base64.b64encode(row[1]).decode('utf-8') if row[1] else None
    
    # Fetch friend's data if friend_id is provided
    friend_pfp = None
    friend_banner = None
    friend_name = None
    friend_id = friend_id if friend_id else None
    if friend_id:
        cursor.execute("SELECT username, image1, image2 FROM users WHERE id = ?", (friend_id,))
        friend_row = cursor.fetchone()
        if friend_row:
            friend_name = friend_row[0]
            friend_pfp = base64.b64encode(friend_row[1]).decode('utf-8') if friend_row[1] else None
            friend_banner = base64.b64encode(friend_row[2]).decode('utf-8') if friend_row[2] else None
    
    conn.close()
    
    # Fetch friends data
    friends_data = get_user_friends(session["id"])
    print(f"Friends data: {friends_data}")
    
    # Pass variables directly to the template
    return render_template('chatroom.html',
                           user_pfp=user_pfp,
                           user_banner=user_banner,
                           user_name=session['username'],
                           user_id=session['id'],
                           friend_pfp=friend_pfp,
                           friend_banner=friend_banner,
                           friend_name=friend_name,
                           friend_id=friend_id,
                           friends_data=friends_data)



@app.route('/get_username', methods=['GET'])
def get_username():
    print("Hit /get_username")
    username = session.get('username')
    print(f"Session username: {username}")
    if not username:
        return jsonify({"error": "No username in session"}), 401
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        print(f"Row for {username}: {row}")
        if row:
            user_id = row[0]
            conn.close()
            return jsonify({"username": username, "id": user_id})
        else:
            conn.close()
            print(f"No user found for {username}")
            return jsonify({"error": "User not found in database"}), 404
    except Exception as e:
        conn.close()
        print(f"Error in get_username: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500





@app.route('/send_message', methods=['POST'])
def send_message():
    print("Received /send_message request")
    # Delete old messages before processing new ones
    delete_old_messages()

    if 'username' not in session:
        print("User not logged in")
        return jsonify({"status": "error", "error": "User not logged in"}), 401

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()
    if not user_id:
        print(f"User not found for username: {session['username']}")
        conn.close()
        return jsonify({"status": "error", "error": "User not found"}), 404
    user_id = user_id[0]
    print(f"Current user ID: {user_id}")

    # Get form data
    message = request.form.get('message')
    friend_id = request.form.get('friend_id', type=int)
    reply_to = request.form.get('replyTo', type=int)
    file = request.files.get('file')

    if not friend_id:
        print("Friend ID is required")
        conn.close()
        return jsonify({"status": "error", "error": "Friend ID is required"}), 400

    file_location = None
    file_timestamp = None
    if file:
        # Generate a unique filename to avoid conflicts
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        file_location = unique_filename
        file_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Insert the message into the database with seen = 0 (unseen)
        cursor.execute('''
            INSERT INTO messages (username, user_id, friend_id, message, file_location, reply_to, seen, file_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['username'], user_id, friend_id, message, file_location, reply_to if reply_to else None, 0, file_timestamp))
        conn.commit()

        # Get the ID and timestamp of the newly inserted message
        cursor.execute('SELECT id, timestamp FROM messages WHERE id = last_insert_rowid()')
        result = cursor.fetchone()
        message_id = result[0]
        timestamp = result[1]
        if timestamp:
            timestamp = f"{timestamp}Z"
    except Exception as e:
        print(f"Error saving message: {str(e)}")
        conn.close()
        return jsonify({"status": "error", "error": str(e)}), 500

    conn.close()

    # Emit the send_message event via SocketIO to trigger handle_send_message
    print(f"Emitting send_message event: userId={user_id}, friendId={friend_id}, message_id={message_id}")
    socketio.emit('send_message', {
        'message': message,
        'username': session['username'],
        'userId': user_id,
        'friendId': friend_id,
        'replyTo': reply_to if reply_to else None,
        'timestamp': timestamp,
        'file_location': file_location,
        'message_id': message_id
    })

    # Return full data so sender's optimistic UI + broadcast both get file_location
    return jsonify({
        "status": "success",
        "message_id": message_id,
        "timestamp": timestamp,
        "file_location": file_location   # ← This was the missing piece
    })

@app.route('/mark_messages_seen', methods=['POST'])
def mark_messages_seen():
    if 'username' not in session:
        print("Session error: 'username' not in session")
        return jsonify({"status": "error", "error": "User not logged in"}), 401

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()
    if not user_id:
        print(f"User not found for username: {session['username']}")
        conn.close()
        return jsonify({"status": "error", "error": "User not found"}), 404
    user_id = user_id[0]
    print(f"Current user ID: {user_id}")

    # Get the message IDs to mark as seen
    message_ids = request.json.get('message_ids', [])
    # Get friend_id and convert to int (handle if it's a string)
    friend_id = request.json.get('friend_id')
    print(f"Received message_ids: {message_ids}, friend_id: {friend_id}")

    # Validate friend_id and convert to int
    try:
        friend_id = int(friend_id) if friend_id is not None else None
    except (ValueError, TypeError):
        print("Invalid friend_id: must be an integer")
        conn.close()
        return jsonify({"status": "error", "error": "Friend ID must be an integer"}), 400

    if not message_ids or not friend_id:
        print("Missing message_ids or friend_id")
        conn.close()
        return jsonify({"status": "error", "error": "Message IDs and friend ID are required"}), 400

    try:
        # Log the messages before updating
        cursor.execute('SELECT id, user_id, friend_id, seen FROM messages WHERE id IN ({})'.format(','.join('?' * len(message_ids))), message_ids)
        messages = cursor.fetchall()
        print(f"Messages before update: {messages}")

        # Mark the specified messages as seen (only if they are from the friend to the user)
        cursor.execute('''
            UPDATE messages 
            SET seen = 1 
            WHERE id IN ({}) 
            AND user_id = ? 
            AND friend_id = ?
        '''.format(','.join('?' * len(message_ids))), (*message_ids, friend_id, user_id))
        updated_rows = cursor.rowcount
        print(f"Updated {updated_rows} rows (friend to user)")

        # If no rows were updated, try the reverse direction (just in case)
        if updated_rows == 0:
            cursor.execute('''
                UPDATE messages 
                SET seen = 1 
                WHERE id IN ({}) 
                AND user_id = ? 
                AND friend_id = ?
            '''.format(','.join('?' * len(message_ids))), (*message_ids, user_id, friend_id))
            updated_rows = cursor.rowcount
            print(f"Updated {updated_rows} rows (user to friend - fallback)")

        conn.commit()

        # Log the messages after updating
        cursor.execute('SELECT id, user_id, friend_id, seen FROM messages WHERE id IN ({})'.format(','.join('?' * len(message_ids))), message_ids)
        messages_after = cursor.fetchall()
        print(f"Messages after update: {messages_after}")

        if updated_rows == 0:
            print("No rows updated - check if user_id and friend_id match the message")
    except Exception as e:
        print(f"Error updating messages: {str(e)}")
        conn.close()
        return jsonify({"status": "error", "error": str(e)}), 500

    conn.close()
    return jsonify({"status": "success"})


@app.route('/get_unread_counts', methods=['GET'])
def get_unread_counts():
    if 'username' not in session:
        return jsonify({"status": "error", "error": "User not logged in"}), 401

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()
    if not user_id:
        conn.close()
        return jsonify({"status": "error", "error": "User not found"}), 404
    user_id = user_id[0]

    # Get the user's friends
    cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (user_id,))
    friends = cursor.fetchone()
    if not friends or not friends[0]:
        conn.close()
        return jsonify({"unread_counts": {}}), 200

    friends_list = friends[0].split(',')
    unread_counts = {}

    # For each friend, count the number of unread messages (seen = 0)
    for friend_id in friends_list:
        if not friend_id:
            continue
        cursor.execute('''
            SELECT COUNT(*) 
            FROM messages 
            WHERE user_id = ? AND friend_id = ? AND seen = 0
        ''', (friend_id, user_id))
        count = cursor.fetchone()[0]
        unread_counts[friend_id] = count

    conn.close()
    return jsonify({"unread_counts": unread_counts})

@app.route('/get_online_status', methods=['GET'])
def get_online_status():
    if 'username' not in session:
        return jsonify({"status": "error", "error": "User not logged in"}), 401

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],))
    user_id = cursor.fetchone()
    if not user_id:
        conn.close()
        return jsonify({"status": "error", "error": "User not found"}), 404
    user_id = user_id[0]

    # Get the user's friends
    cursor.execute("SELECT friends FROM friends WHERE user_id = ?", (user_id,))
    friends = cursor.fetchone()
    if not friends or not friends[0]:
        conn.close()
        return jsonify({"online_status": {}}), 200

    friend_ids = friends[0].split(',')
    online_status = {}
    for friend_id in friend_ids:
        if friend_id:
            online_status[friend_id] = "online" if int(friend_id) in online_users else "offline"

    conn.close()
    return jsonify({"online_status": online_status})



@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




def delete_old_attachments():
    while True:
        print("Checking for old attachments to delete...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get messages with attachments older than 2 hours
            two_hours_ago = (datetime.now() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                SELECT file_location
                FROM messages
                WHERE file_location IS NOT NULL
                AND file_timestamp < ?
            ''', (two_hours_ago,))
            old_attachments = cursor.fetchall()

            # Delete the files from the uploads folder
            for attachment in old_attachments:
                file_location = attachment[0]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_location)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Deleted old attachment: {file_location}")

                # Update the database to remove the file_location
                cursor.execute('''
                    UPDATE messages
                    SET file_location = NULL
                    WHERE file_location = ?
                ''', (file_location,))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error deleting old attachments: {str(e)}")

        # Sleep for 10 minutes before checking again
        time.sleep(600)

# Start the background thread when the app starts
threading.Thread(target=delete_old_attachments, daemon=True).start()


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash("Please log in to edit your profile.", "error")
        return redirect('/login')

    if request.method == 'GET':
        # (GET logic remains unchanged)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username, image1, image2 FROM users WHERE id = ?", (session['id'],))
        row = cursor.fetchone()
        if not row:
            conn.close()
            flash("User not found.", "error")
            return redirect('/login')
        
        current_pfp = base64.b64encode(row[1]).decode('utf-8') if row[1] else None
        current_banner = base64.b64encode(row[2]).decode('utf-8') if row[2] else None
        
        conn.close()
        
        return render_template('edit_profile.html',
                               current_username=row[0],
                               current_pfp=current_pfp,
                               current_banner=current_banner)

    elif request.method == 'POST':
        # Get form data
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        image1_base64 = request.form.get('image1-base64')  # Base64-encoded PFP
        image2_base64 = request.form.get('image2-base64')  # Base64-encoded banner
        image1_format = request.form.get('image1-format', 'jpeg')  # Default to JPEG
        image2_format = request.form.get('image2-format', 'jpeg')
        
        # Debug: Log the received data
        print(f"Received edit profile data:")
        print(f"New username: {new_username}")
        print(f"New password: {new_password}")
        print(f"Image1 base64 size: {len(image1_base64) / 1024 / 1024 if image1_base64 else 0} MB")
        print(f"Image2 base64 size: {len(image2_base64) / 1024 / 1024 if image2_base64 else 0} MB")
        print(f"Image1 format: {image1_format}")
        print(f"Image2 format: {image2_format}")
        
        # Validate required fields
        if not new_username:
            flash("Username is required.", "error")
            return redirect('/edit_profile')
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Fetch the current user's data (including PFP, banner, and formats)
        cursor.execute("SELECT password, image1, image2, image1_format, image2_format FROM users WHERE id = ?", (session['id'],))
        row = cursor.fetchone()
        if not row:
            conn.close()
            flash("User not found.", "error")
            return redirect('/edit_profile')
        
        # Get current values
        current_password = row[0]
        current_image1 = row[1]  # Current PFP (BLOB)
        current_image2 = row[2]  # Current banner (BLOB)
        current_image1_format = row[3] if row[3] else 'jpeg'  # Current PFP format
        current_image2_format = row[4] if row[4] else 'jpeg'  # Current banner format
        
        # Decode base64 images to binary (BLOB) for database storage
        image1_blob = current_image1  # Default to current PFP
        image2_blob = current_image2  # Default to current banner
        final_image1_format = current_image1_format  # Default to current PFP format
        final_image2_format = current_image2_format  # Default to current banner format
        
        if image1_base64:  # Only update PFP if a new file was uploaded
            try:
                image1_blob = base64.b64decode(image1_base64)
                final_image1_format = image1_format
            except Exception as e:
                print(f"Error decoding image1 base64: {e}")
                flash("Error processing profile picture.", "error")
                conn.close()
                return redirect('/edit_profile')
        
        if image2_base64:  # Only update banner if a new file was uploaded
            try:
                image2_blob = base64.b64decode(image2_base64)
                final_image2_format = image2_format
            except Exception as e:
                print(f"Error decoding image2 base64: {e}")
                flash("Error processing banner image.", "error")
                conn.close()
                return redirect('/edit_profile')
        
        # Check if the new username is already taken (excluding the current user)
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (new_username, session['id']))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            flash("Username already taken. Please choose a different one.", "error")
            return redirect('/edit_profile')
        
        # Use the current password if a new one is not provided
        if not new_password:
            new_password = current_password
        
        # Update the user's data in the database
        try:
            update_query = """
                UPDATE users 
                SET username = ?, 
                    password = ?, 
                    image1 = ?, 
                    image2 = ?, 
                    image1_format = ?, 
                    image2_format = ? 
                WHERE id = ?
            """
            cursor.execute(update_query, (
                new_username,
                new_password,
                sqlite3.Binary(image1_blob) if image1_blob else None,  # Updated or current PFP
                sqlite3.Binary(image2_blob) if image2_blob else None,  # Updated or current banner
                final_image1_format,
                final_image2_format,
                session['id']
            ))
            conn.commit()
            
            # Update the session with the new username
            session['username'] = new_username
        except Exception as e:
            conn.close()
            print(f"Error updating profile: {e}")
            flash("Error updating profile. Please try again.", "error")
            return redirect('/edit_profile')
        
        conn.close()
        
        flash("Profile updated successfully!", "success")
        return redirect('/')

@app.route('/developers', methods=['GET'])
def developer_page():
    return render_template('developer.html')
    

# Register the GIF cropping blueprint
from gif_crop import gif_crop_bp
app.register_blueprint(gif_crop_bp)




if __name__ == '__main__':
    # host="0.0.0.0" tells Flask to listen to all network interfaces
    # This is what allows your phone to connect
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
else:
    # This part is for when you eventually deploy to Render
    import os
    port = int(os.getenv("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
