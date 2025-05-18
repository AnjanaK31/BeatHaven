import os
from flask import Flask, jsonify, request, render_template, send_from_directory
import flask_cors
import mysql.connector
from mysql.connector import Error
import os
import mysql.connector
import jwt as PyJWT  # Rename the import to avoid conflicts
from mysql.connector import Error
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, jsonify, request, make_response, g
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()

app = Flask(__name__, static_folder='static')
flask_cors.CORS(app)
# Database connection configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'Har!1234',
    'database': 'music_db',
    'auth_plugin': 'mysql_native_password'
}

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(24)) # General Flask secret
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Default secret key for JWT
app.config['JWT_ALGORITHM'] = os.getenv('JWT_ALGORITHM', 'HS256')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 60)))
app.config['COOKIE_JWT_NAME'] = os.getenv('COOKIE_JWT_NAME', 'jwt')
app.config['COOKIE_MAX_AGE'] = timedelta(days=int(os.getenv('COOKIE_MAX_AGE_DAYS', 1))) # For cookie expiry
app.config['COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', 'False').lower() == 'true'
app.config['COOKIE_SAMESITE'] = os.getenv('COOKIE_SAMESITE', 'Lax')

# CORS Configuration
CORS_ORIGIN = os.getenv('CORS_ORIGIN')
if not CORS_ORIGIN:
    print("Warning: CORS_ORIGIN environment variable not set. Using http://localhost for development.")
    CORS_ORIGIN = 'http://localhost'  # Default to localhost without port in development

CORS(
    app,
    origins=[CORS_ORIGIN],  # Always use specific origin
    supports_credentials=True,  # Crucial for sending/receiving cookies cross-origin
    allow_headers=["Content-Type", "Authorization"],  # Allow these headers
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]  # Allow these methods
)

# Bcrypt Initialization
bcrypt = Bcrypt(app)


def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# Serve the static files
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index(2).html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# API Routes based on actual database schema
@app.route('/api/songs', methods=['GET'])
def get_songs():
    print("sending data")
    """Get all songs from the database"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT id, name, album, album_id, artists, artist_ids, track_number, 
       explicit, loudness, mode, duration_ms, time_signature, 
       year, release_date
       FROM tracks_features
       ORDER BY release_date, name
       LIMIT 5000
        """
        cursor.execute(query)
        songs = cursor.fetchall()
        
        # Calculate a "rating" based on popularity or some other metric
        # Here we'll simulate ratings since your schema doesn't have a rating column
        for song in songs:
            # Adding calculated fields needed by frontend
            # Converting loudness to a rating scale (loudness typically ranges from -60 to 0)
            # Higher loudness (closer to 0) gets higher rating
            if 'loudness' in song and song['loudness'] is not None:
                normalized_loudness = min(5, max(1, 5 - abs(song['loudness']) / 20))
                song['rating'] = round(normalized_loudness, 1)
            else:
                song['rating'] = 3.5  # Default rating
                
            # Ensure we have a "title" field which the frontend expects
            song['title'] = song['name']
            
            # Ensure the "artist" field exists for frontend compatibility
            if 'artists' not in song or not song['artists']:
                song['artist'] = "Unknown Artist"
            else:
                song['artist'] = song['artists']
        
        return jsonify(songs)
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/songs/<song_id>', methods=['GET'])
def get_song(song_id):
    """Get details for a specific song"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT id, name, album, album_id, artists, artist_ids, track_number, 
               explicit, loudness, mode, duration_ms, time_signature, 
               year, release_date
        FROM tracks_features
        WHERE id = %s
        """
        cursor.execute(query, (song_id,))
        song = cursor.fetchone()
        
        if not song:
            return jsonify({"error": "Song not found"}), 404
        
        # Add calculated fields needed by frontend
        if 'loudness' in song and song['loudness'] is not None:
            normalized_loudness = min(5, max(1, 5 - abs(song['loudness']) / 20))
            song['rating'] = round(normalized_loudness, 1)
        else:
            song['rating'] = 3.5  # Default rating
            
        # Ensure we have a "title" field which the frontend expects
        song['title'] = song['name']
        
        # Ensure the "artist" field exists for frontend compatibility
        if 'artists' not in song or not song['artists']:
            song['artist'] = "Unknown Artist"
        else:
            song['artist'] = song['artists']
        
        # Check for any user ratings in the database
        try:
            rating_query = """
                SELECT AVG(rating) as avg_rating, COUNT(*) as rating_count
                FROM user_ratings
                WHERE song_id = %s
            """
            cursor.execute(rating_query, (song_id,))
            rating_data = cursor.fetchone()
            
            if rating_data and rating_data['avg_rating'] is not None:
                song['rating'] = round(float(rating_data['avg_rating']), 1)
                song['rating_count'] = rating_data['rating_count']
        except:
            # Table might not exist yet, we'll use the generated rating
            pass
            
        return jsonify(song)
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/songs/<song_id>/rate', methods=['GET', 'POST'])
def rate_song(song_id):
    """Get or add/update a user rating for a song"""
    if request.method == 'GET':
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get average rating and count
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as rating_count
                FROM user_ratings
                WHERE song_id = %s
            """, (song_id,))
            
            result = cursor.fetchone()
            
            if not result or result['avg_rating'] is None:
                return jsonify({
                    "rating": 0,
                    "rating_count": 0
                })
            
            return jsonify({
                "rating": round(float(result['avg_rating']), 1),
                "rating_count": result['rating_count']
            })
            
        except Error as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # POST method implementation
    # Get the JWT token from the cookie
    token = request.cookies.get(app.config['COOKIE_JWT_NAME'])
    
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Decode the JWT token
        payload = PyJWT.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
        user_id = payload.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401
    except PyJWT.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except PyJWT.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    
    data = request.json
    if not data or 'rating' not in data:
        return jsonify({"error": "Rating value is required"}), 400
        
    rating = data['rating']
    try:
        rating = float(rating)
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
    except ValueError:
        return jsonify({"error": "Rating must be a number"}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        
        # Check if the user_ratings table exists, if not create it
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_ratings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                song_id VARCHAR(255) NOT NULL,
                rating DECIMAL(3,1) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_song (user_id, song_id)
            )
        """)
        connection.commit()
        
        # Check if user has already rated this song
        cursor.execute("""
            SELECT id, rating FROM user_ratings 
            WHERE user_id = %s AND song_id = %s
        """, (user_id, song_id))
        
        existing_rating = cursor.fetchone()
        
        if existing_rating:
            # Update existing rating
            cursor.execute("""
                UPDATE user_ratings 
                SET rating = %s 
                WHERE id = %s
            """, (rating, existing_rating[0]))
        else:
            # Add new rating
            cursor.execute("""
                INSERT INTO user_ratings (user_id, song_id, rating)
                VALUES (%s, %s, %s)
            """, (user_id, song_id, rating))
        
        connection.commit()
        
        # Get the new average rating
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as count
            FROM user_ratings
            WHERE song_id = %s
        """, (song_id,))
        result = cursor.fetchone()
        
        new_avg = round(float(result[0]), 1) if result[0] else 0
        rating_count = result[1] if result[1] else 1
        
        return jsonify({
            "success": True,
            "message": "Rating added successfully",
            "new_average_rating": new_avg,
            "rating_count": rating_count
        })
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/artists/<string:artist_id>', methods=['GET'])
def get_artist(artist_id):
    """Get details for a specific artist"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # First find all songs by this artist
        songs_query = """
        SELECT id, name, album, album_id, artists, artist_ids, track_number, 
               explicit, loudness, mode, duration_ms, time_signature, 
               year, release_date
        FROM tracks_features
        WHERE FIND_IN_SET(%s, artist_ids) > 0
        ORDER BY year DESC
        """
        cursor.execute(songs_query, (artist_id,))
        songs = cursor.fetchall()
        
        if not songs:
            return jsonify({"error": "Artist not found"}), 404
        
        # Get artist name from the first track
        artist_name = songs[0]['artists'].split(',')[0]  # Simplistic approach
        
        # Create artist object
        artist = {
            "id": artist_id,
            "name": artist_name,
            "bio": "No biography available",  # Placeholder
            "songs": []
        }
        
        # Process songs
        for song in songs:
            # Calculate rating
            if 'loudness' in song and song['loudness'] is not None:
                normalized_loudness = min(5, max(1, 5 - abs(song['loudness']) / 20))
                song['rating'] = round(normalized_loudness, 1)
            else:
                song['rating'] = 3.5
                
            # Add title for frontend compatibility
            song['title'] = song['name']
            artist['songs'].append(song)
        
        return jsonify(artist)
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Helper endpoint to check database connection
@app.route('/api/status', methods=['GET'])
def check_status():
    """Check database connection status"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM tracks_features")
        count = cursor.fetchone()[0]
        return jsonify({
            "status": "ok", 
            "message": "Connected to database", 
            "tracks_count": count
        })
    
    except Error as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')  # Get email from request

    if not username or not password or not email:
        return jsonify({"error": "Username, email, and password required"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()

        # Create table if it doesn't exist with updated schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """)
        connection.commit()

        # Insert new user with email
        cursor.execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
        """, (username, email, hashed_password))
        connection.commit()

        return jsonify({"message": "User registered successfully"}), 201

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user by username
        cursor.execute("""
            SELECT user_id, username, password_hash
            FROM users
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Check password
        if not bcrypt.check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid username or password"}), 401
        
        # Update last login
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user['user_id'],))
        connection.commit()
        
        # Create JWT token
        payload = {
            'user_id': user['user_id'],
            'username': user['username'],
            'exp': datetime.now(timezone.utc) + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }
        print(payload)
        token = PyJWT.encode(payload, app.config['JWT_SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
        
        # Create response with token
        response = jsonify({"message": "Login successful","user_id":user['user_id'],"username":user['username']})
        response.set_cookie(
            app.config['COOKIE_JWT_NAME'],
            token,
            max_age=app.config['COOKIE_MAX_AGE'].total_seconds(),
            secure=app.config['COOKIE_SECURE'],
            samesite=app.config['COOKIE_SAMESITE'],
            httponly=True
        )
        
        return response, 200

    except Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/auth/user/stats', methods=['GET'])
def get_user_stats():
    """Get statistics for the currently logged-in user"""
    # Get the JWT token from the cookie
    token = request.cookies.get(app.config['COOKIE_JWT_NAME'])
    
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Decode the JWT token
        payload = PyJWT.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
        user_id = payload.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get user information
            cursor.execute("""
                SELECT user_id, username, email, created_at, last_login
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Get user's rating count
            cursor.execute("""
                SELECT COUNT(*) as rating_count
                FROM user_ratings
                WHERE user_id = %s
            """, (user_id,))
            
            rating_result = cursor.fetchone()
            rating_count = rating_result['rating_count'] if rating_result else 0
            
            # Get user's average rating
            cursor.execute("""
                SELECT AVG(rating) as avg_rating
                FROM user_ratings
                WHERE user_id = %s
            """, (user_id,))
            
            avg_rating_result = cursor.fetchone()
            avg_rating = round(float(avg_rating_result['avg_rating']), 1) if avg_rating_result and avg_rating_result['avg_rating'] is not None else 0
            
            # Get user's favorite songs (top 5 rated)
            cursor.execute("""
                SELECT s.id, s.name, s.artists, ur.rating, ur.created_at
                FROM user_ratings ur
                JOIN tracks_features s ON ur.song_id = s.id
                WHERE ur.user_id = %s
                ORDER BY ur.rating DESC
                LIMIT 5
            """, (user_id,))
            
            favorite_songs = cursor.fetchall()
            
            # Format the response
            user_stats = {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email'],
                "member_since": user['created_at'].strftime("%Y-%m-%d") if user['created_at'] else None,
                "last_login": user['last_login'].strftime("%Y-%m-%d %H:%M:%S") if user['last_login'] else None,
                "rating_count": rating_count,
                "average_rating": avg_rating,
                "favorite_songs": favorite_songs
            }
            
            return jsonify(user_stats), 200
            
        except Error as e:
            return jsonify({"error": str(e)}), 500
            
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    except PyJWT.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except PyJWT.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get a user's public profile by ID"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user's public information
        cursor.execute("""
            SELECT user_id, username, created_at
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user's rating count
        cursor.execute("""
            SELECT COUNT(*) as rating_count
            FROM user_ratings
            WHERE user_id = %s
        """, (user_id,))
        
        rating_result = cursor.fetchone()
        rating_count = rating_result['rating_count'] if rating_result else 0
        
        # Get user's favorite songs (top 5 rated)
        cursor.execute("""
            SELECT s.id, s.name, s.artists, ur.rating
            FROM user_ratings ur
            JOIN tracks_features s ON ur.song_id = s.id
            WHERE ur.user_id = %s
            ORDER BY ur.rating DESC
            LIMIT 5
        """, (user_id,))
        
        favorite_songs = cursor.fetchall()
        
        # Format the response
        user_profile = {
            "user_id": user['user_id'],
            "username": user['username'],
            "member_since": user['created_at'].strftime("%Y-%m-%d") if user['created_at'] else None,
            "rating_count": rating_count,
            "favorite_songs": favorite_songs
        }
        
        return jsonify(user_profile), 200
        
    except Error as e:
        return jsonify({"error": str(e)}), 500
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/auth/user/profile', methods=['PUT'])
def update_user_profile():
    """Update the currently logged-in user's profile"""
    # Get the JWT token from the cookie
    token = request.cookies.get(app.config['COOKIE_JWT_NAME'])
    
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Decode the JWT token
        payload = PyJWT.decode(token, app.config['JWT_SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
        user_id = payload.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400
        
        # Get updateable fields
        username = data.get('username')
        email = data.get('email')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        # At least one field must be provided
        if not any([username, email, new_password]):
            return jsonify({"error": "At least one field must be provided for update"}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({"error": "Database connection failed"}), 500
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Get current user data
            cursor.execute("""
                SELECT username, email, password_hash
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # If changing password, verify current password
            if new_password:
                if not current_password:
                    return jsonify({"error": "Current password is required to change password"}), 400
                
                if not bcrypt.check_password_hash(user['password_hash'], current_password):
                    return jsonify({"error": "Current password is incorrect"}), 401
                
                # Hash the new password
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            
            # Check if username is already taken
            if username and username != user['username']:
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = %s AND user_id != %s", (username, user_id))
                result = cursor.fetchone()
                if result['count'] > 0:
                    return jsonify({"error": "Username is already taken"}), 409
            
            # Check if email is already taken
            if email and email != user['email']:
                cursor.execute("SELECT COUNT(*) as count FROM users WHERE email = %s AND user_id != %s", (email, user_id))
                result = cursor.fetchone()
                if result['count'] > 0:
                    return jsonify({"error": "Email is already taken"}), 409
            
            # Build the update query dynamically
            update_fields = []
            params = []
            
            if username:
                update_fields.append("username = %s")
                params.append(username)
            
            if email:
                update_fields.append("email = %s")
                params.append(email)
            
            if new_password:
                update_fields.append("password_hash = %s")
                params.append(hashed_password)
            
            # Add user_id to params
            params.append(user_id)
            
            # Execute the update
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
            cursor.execute(query, params)
            connection.commit()
            
            return jsonify({"message": "Profile updated successfully"}), 200
            
        except Error as e:
            return jsonify({"error": str(e)}), 500
            
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    except PyJWT.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except PyJWT.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>/stats', methods=['GET'])
def get_user_stats_by_id(user_id):
    """Get statistics for a specific user by ID"""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get user information
        cursor.execute("""
            SELECT user_id, username, email, created_at, last_login
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get rating count and average rating
        cursor.execute("""
            SELECT COUNT(*) as rating_count, AVG(rating) as avg_rating
            FROM user_ratings
            WHERE user_id = %s
        """, (user_id,))
        
        stats = cursor.fetchone()
        rating_count = stats['rating_count'] or 0
        avg_rating = round(float(stats['avg_rating']), 1) if stats['avg_rating'] else 0
        
        # Get top 5 favorite songs based on ratings
        cursor.execute("""
            SELECT s.id, s.name, s.artists
            FROM user_ratings ur
            JOIN tracks_features s ON ur.song_id = s.id
            WHERE ur.user_id = %s
            LIMIT 5
        """, (user_id,))
        
        favorite_songs = cursor.fetchall()
        
        return jsonify({
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "member_since": user['created_at'].isoformat() if user['created_at'] else None,
            "last_login": user['last_login'].isoformat() if user['last_login'] else None,
            "rating_count": rating_count,
            "average_rating": avg_rating,
            "favorite_songs": favorite_songs
        })
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/api/users/<int:user_id>/ratings', methods=['GET'])
def get_user_ratings(user_id):
    """Get ratings for a specific user with pagination"""
    # Get pagination parameters
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    # Validate pagination parameters
    if limit < 1 or limit > 100:
        return jsonify({"error": "Limit must be between 1 and 100"}), 400
    if offset < 0:
        return jsonify({"error": "Offset must be non-negative"}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get total count of ratings
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM user_ratings
            WHERE user_id = %s
        """, (user_id,))
        
        total = cursor.fetchone()['total']
        
        # Get paginated ratings with song details
        cursor.execute("""
            SELECT ur.id, ur.song_id, ur.rating, ur.created_at,
                   tf.name as song_name, tf.artists as artist_name
            FROM user_ratings ur
            JOIN tracks_features tf ON ur.song_id = tf.id
            WHERE ur.user_id = %s
            ORDER BY ur.created_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        ratings = cursor.fetchall()
        
        # Format the response
        formatted_ratings = [{
            "id": rating['id'],
            "song_id": rating['song_id'],
            "song_name": rating['song_name'],
            "artist_name": rating['artist_name'],
            "rating": float(rating['rating']),
            "created_at": rating['created_at'].isoformat() if rating['created_at'] else None
        } for rating in ratings]
        
        return jsonify({
            "total": total,
            "limit": limit,
            "offset": offset,
            "ratings": formatted_ratings
        })
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)