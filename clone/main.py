from flask import Flask,render_template, request, session, flash, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import os,base64
import random
import string,sqlite3

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
    if friends:
        friends=friends[0]
    if friends:
        friends = friends[0]
        friends = friends.split(',')
        friends_data=[]
        for friend in friends:
            cursor.execute("SELECT username,image1,image2 FROM users WHERE id = ?", (friend,))
            row = cursor.fetchone()
            print(row[0])
            if row:
                friends_data.append({"username":row[0],
                                     "id":friend,
                                     "pfp": row[1],
                                     "banner": row[2]
                                     })
        conn.close()
        return friends_data
    else:
        return "No friends"

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
@app.route('/add_friend')
def add_friend():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get the current user's ID
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['username'],))
    user_id = cursor.fetchone()[0]

    # Get the friend ID (the ID of the user sending the friend request)
    friend_id = request.args.get('id', type=int)
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
        if not incoming_request_list:
            print(incoming_request_list)
            updated_requests = None
        else:
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
            updated_friend_friends=str(user_id)
            cursor.execute('INSERT INTO friends(user_id,friends) VALUES(?,?)', (friend_id, str(user_id)))

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

@app.route('/messages', methods=['GET'])
def get_last_messages():
    try:
        conn = sqlite3.connect(db_path)
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


@socketio.on("send_message")
def handle_send_message(data):
    username = data["username"]
    if username is None:
        return
    message = data["message"]
    print(f"{username}: {message}")

    # Add userId to the broadcast
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_id = cursor.fetchone()
    conn.close()
    user_id = user_id[0] if user_id else None

    emit("broadcast_message", {"username": username, "message": message, "userId": user_id}, broadcast=True)


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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (username, message, file_location) VALUES (?, ?, ?)",
                   (username, message, new_file_name))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})





# Register the GIF cropping blueprint
from gif_crop import gif_crop_bp
app.register_blueprint(gif_crop_bp)


if __name__ == '__main__':
    socketio.run(app,debug=True,allow_unsafe_werkzeug=True)
