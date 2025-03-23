from flask import Flask,render_template, request, session, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os,base64
import random
import string,sqlite3
import base64

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
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
        return
    username = session['username']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()
    conn.close()
    if user_id:
        user_id = user_id[0]
        socketio.server.enter_room(sid=request.sid, room=str(user_id))
        print(f"User {username} (ID: {user_id}) connected and joined room {user_id}")

@socketio.on("disconnect")
def handle_disconnect():
    print("A user disconnected")

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

    # Log the message for debugging
    print(f"{username} (ID: {user_id}) to Friend ID {friend_id}: {message}")

    # Prepare the message data to broadcast
    message_data = {
        "username": username,
        "message": message,
        "userId": user_id,
        "friendId": friend_id,
        "replyTo": reply_to,
        "timestamp": timestamp,
        "file_location": file_location
    }

    # Send to sender
    emit("broadcast_message", message_data, room=str(user_id))
    # Send to recipient
    emit("broadcast_message", message_data, room=str(friend_id))

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
        conn.close()
        return jsonify({"status": "Friend request sent successfully."}), 200

    except Exception as e:
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

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get the current user's ID
        cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
        user_id = cursor.fetchone()
        if not user_id:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        user_id = user_id[0]

        # Check if the friend exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (friend_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Friend not found"}), 404

        # Get the current user's friend data
        cursor.execute('SELECT friends, incoming_request FROM friends WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            # If no friend data exists, initialize it
            cursor.execute('INSERT INTO friends (user_id, friends, incoming_request) VALUES (?, ?, ?)', (user_id, '', ''))
            conn.commit()
            friends = []
            incoming_requests = []
        else:
            friends = user_data[0].split(",") if user_data[0] else []
            incoming_requests = user_data[1].split(",") if user_data[1] else []

        # Check if the friend_id is in incoming requests
        if str(friend_id) not in incoming_requests:
            conn.close()
            return jsonify({"error": "No friend request from this user"}), 400

        # Add friend to the current user's friend list
        if str(friend_id) not in friends:
            friends.append(str(friend_id))
        friends = [f for f in friends if f]  # Remove empty strings
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (",".join(friends), user_id))

        # Remove the friend request from incoming requests
        incoming_requests.remove(str(friend_id))
        incoming_requests = [r for r in incoming_requests if r]  # Remove empty strings
        cursor.execute('UPDATE friends SET incoming_request = ? WHERE user_id = ?', (",".join(incoming_requests) if incoming_requests else '', user_id))

        # Add the current user to the friend's friend list
        cursor.execute('SELECT friends FROM friends WHERE user_id = ?', (friend_id,))
        friend_data = cursor.fetchone()
        if not friend_data:
            # If no friend data exists for the friend, initialize it
            cursor.execute('INSERT INTO friends (user_id, friends, incoming_request) VALUES (?, ?, ?)', (friend_id, '', ''))
            conn.commit()
            friend_friends = []
        else:
            friend_friends = friend_data[0].split(",") if friend_data[0] else []

        if str(user_id) not in friend_friends:
            friend_friends.append(str(user_id))
        friend_friends = [f for f in friend_friends if f]  # Remove empty strings
        cursor.execute('UPDATE friends SET friends = ? WHERE user_id = ?', (",".join(friend_friends) if friend_friends else '', friend_id))

        conn.commit()
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
    limit = request.args.get('limit', default=50, type=int)  # Default to 50 messages
    offset = request.args.get('offset', default=0, type=int)  # For pagination
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    # Fetch messages with limit and offset for pagination
    cursor.execute('''
        SELECT * FROM messages 
        WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
        AND timestamp >= datetime('now', '-1 month')  -- Exclude messages older than 1 month
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (user_id, friend_id, friend_id, user_id, limit, offset))

    messages = cursor.fetchall()
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message[0],
            'username': message[1],
            'user_id': message[2],
            'friend_id': message[3],
            'message': message[4],
            'file_location': message[5],
            'reply_to': message[6],
            'timestamp': message[7]  # Include timestamp
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
        return redirect("/")
    else:
        flash("Pls Signup!!","error")

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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT image1,image2 FROM users WHERE id = ?", (session['id'],))
    row = cursor.fetchone()
    user_data ={
        "username":session['username'],
        "id":session['id'],
        "pfp":row[0],
        "banner":row[1]
    }
    friends_data = get_user_friends(session["id"])
    print(friends_data)
    return render_template('chatroom.html', user_data=user_data, friends_data=friends_data,friend_id=friend_id)



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
    # Delete old messages before processing new ones
    delete_old_messages()

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

    # Get form data
    message = request.form.get('message')
    friend_id = request.form.get('friend_id', type=int)
    reply_to = request.form.get('replyTo', type=int)
    file = request.files.get('file')

    if not friend_id:
        conn.close()
        return jsonify({"status": "error", "error": "Friend ID is required"}), 400

    file_location = None
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_location = filename

    try:
        # Insert the message into the database
        cursor.execute('''
            INSERT INTO messages (username, user_id, friend_id, message, file_location, reply_to)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['username'], user_id, friend_id, message, file_location, reply_to if reply_to else None))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "error": str(e)}), 500

    conn.close()
    return jsonify({"status": "success"})





# Register the GIF cropping blueprint
from gif_crop import gif_crop_bp
app.register_blueprint(gif_crop_bp)


if __name__ == '__main__':
    socketio.run(app,debug=True,allow_unsafe_werkzeug=True)
