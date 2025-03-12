from flask import Flask, request, render_template, redirect, flash
import sqlite3
import os

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages

# Database File
DB_FILE = "users.db"


# Ensure Database Exists
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Create `users` table
        cursor.execute(
            """CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                profile_picture BLOB,
                banner BLOB
);"""
        )
        conn.commit()
        conn.close()
        print("Database initialized.")


init_db()


@app.route("/")
def home():
    return render_template("login_page.html")


@app.route('/chatroom')
def chatroom():
    return render_template('chatroom.html')


@app.route("/submit", methods=["POST"])
def submit_form():
    conn = None
    try:
        # Get form data
        username = request.form.get("username")
        password = request.form.get("password")
        profile_picture = request.form.get("image1")
        banner = request.form.get("image2")

        # Basic validation
        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect("/")

        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Insert data into the database
        cursor.execute(
            "INSERT INTO users (username, password, profile_picture, banner) VALUES (?, ?, ?, ?)",
            (username, password, profile_picture, banner),
        )
        conn.commit()
        flash("Successfully registered!", "success")
    except sqlite3.IntegrityError:
        flash("This username is already taken. Please try again.", "error")
        return redirect("/")
    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect("/")
    finally:
        if conn:
            conn.close()  # Ensure the connection is always closed

    return redirect("/chatroom")


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)