from flask import Flask, request, jsonify, send_from_directory, session, render_template_string
from flask_cors import CORS
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
import threading
import json
from database import Database
from sftp_client import SFTPManager
from encryption import AESCipher
import gzip
import io
import base64

app = Flask(__name__)
app.secret_key = os.getenv('SESSION_SECRET', 'dev-session-key-' + str(os.urandom(16).hex()))
CORS(app, origins=['*'])

# Initialize components
db = Database()
sftp_manager = SFTPManager()
aes_cipher = AESCipher()

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-jwt-key-' + str(os.urandom(16).hex()))
JWT_EXPIRATION_HOURS = 24

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Check if user already exists
        if db.get_user(username):
            return jsonify({'error': 'Username already exists'}), 409
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_data = {
            'username': username,
            'password_hash': password_hash.decode('utf-8'),
            'email': email,
            'created_at': datetime.utcnow(),
            'active': True
        }
        
        user_id = db.create_user(user_data)
        
        # Log registration
        db.log_activity(user_id, 'user_registered', {'username': username})
        
        return jsonify({'message': 'User registered successfully'}), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Get user from database
        user = db.get_user(username)
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Invalid username or password'}), 401
        
        if not user.get('active', True):
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Generate JWT token
        payload = {
            'user_id': str(user['id']),
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        # Update last login
        db.update_user_login(str(user['id']))
        
        # Log login
        db.log_activity(str(user['id']), 'user_login', {'username': username})
        
        return jsonify({
            'token': token,
            'username': username,
            'expires_in': JWT_EXPIRATION_HOURS * 3600
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
            username = payload['username']
            
            # Log logout
            db.log_activity(user_id, 'user_logout', {'username': username})
            
        except jwt.ExpiredSignatureError:
            pass  # Token already expired
        except jwt.InvalidTokenError:
            pass  # Invalid token
        
        return jsonify({'message': 'Logged out successfully'}), 200
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    """Verify JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            return jsonify({
                'valid': True,
                'user_id': payload['user_id'],
                'username': payload['username']
            }), 200
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return jsonify({'error': 'Token verification failed'}), 500

@app.route('/api/recent-transfers', methods=['GET'])
def recent_transfers():
    """Get recent transfers for authenticated user"""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get recent transfers from database
        transfers = db.get_recent_transfers(user_id, limit=10)
        
        return jsonify(transfers), 200
        
    except Exception as e:
        print(f"Recent transfers error: {str(e)}")
        return jsonify({'error': 'Failed to fetch transfers'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file with encryption and compression"""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
            username = payload['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file data
        file_data = file.read()
        original_size = len(file_data)
        
        # Compress file using gzip
        compressed_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed_buffer, mode='wb') as gz_file:
            gz_file.write(file_data)
        compressed_data = compressed_buffer.getvalue()
        compressed_size = len(compressed_data)
        
        # Encrypt compressed data
        encrypted_data = aes_cipher.encrypt(compressed_data)
        
        # Prepare SFTP upload
        remote_filename = f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}.enc"
        
        # Upload to SFTP server (simulated - in real implementation, use actual SFTP)
        upload_result = sftp_manager.upload_file(encrypted_data, remote_filename)
        
        if upload_result['success']:
            # Log transfer
            transfer_data = {
                'user_id': user_id,
                'filename': file.filename,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'encrypted_size': len(encrypted_data),
                'remote_filename': remote_filename,
                'type': 'upload',
                'timestamp': datetime.utcnow(),
                'compression_ratio': round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0
            }
            
            transfer_id = db.log_transfer(transfer_data)
            
            # Log activity
            db.log_activity(user_id, 'file_upload', {
                'filename': file.filename,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': transfer_data['compression_ratio']
            })
            
            return jsonify({
                'message': 'File uploaded successfully',
                'transfer_id': str(transfer_id),
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': transfer_data['compression_ratio'],
                'remote_filename': remote_filename
            }), 200
        else:
            return jsonify({'error': 'Upload failed: ' + upload_result.get('error', 'Unknown error')}), 500
            
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/download/<transfer_id>', methods=['GET'])
def download_file(transfer_id):
    """Download and decrypt file"""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get transfer info
        transfer = db.get_transfer(transfer_id, user_id)
        if not transfer:
            return jsonify({'error': 'Transfer not found or access denied'}), 404
        
        # Download from SFTP server
        download_result = sftp_manager.download_file(transfer['remote_filename'])
        
        if not download_result['success']:
            return jsonify({'error': 'Download failed: ' + download_result.get('error', 'Unknown error')}), 500
        
        encrypted_data = download_result['data']
        
        # Decrypt data
        try:
            compressed_data = aes_cipher.decrypt(encrypted_data)
        except Exception as e:
            return jsonify({'error': 'Decryption failed'}), 500
        
        # Decompress data
        try:
            decompressed_data = gzip.decompress(compressed_data)
        except Exception as e:
            return jsonify({'error': 'Decompression failed'}), 500
        
        # Log download activity
        db.log_activity(user_id, 'file_download', {
            'filename': transfer['filename'],
            'transfer_id': transfer_id
        })
        
        # Return file data as base64 for web client
        file_data_b64 = base64.b64encode(decompressed_data).decode('utf-8')
        
        return jsonify({
            'filename': transfer['filename'],
            'data': file_data_b64,
            'size': len(decompressed_data)
        }), 200
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

# Web interface route
@app.route('/', methods=['GET'])
def web_interface():
    """Serve the web interface"""
    with open('static/index.html', 'r') as f:
        return f.read()

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("Starting Secure SFTP Transfer Server...")
    print("Server running on: http://0.0.0.0:5000")
    print("API endpoints available at /api/*")
    print("Web interface available at /")
    
    # Use debug mode only in development
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Run single server on port 5000 with both web interface and API
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
