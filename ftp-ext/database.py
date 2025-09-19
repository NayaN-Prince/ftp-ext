import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import os
import logging
import json

class Database:
    """PostgreSQL database manager for SFTP application"""
    
    def __init__(self):
        # PostgreSQL connection
        self.database_url = os.getenv('DATABASE_URL')
        
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = True
            print("Connected to PostgreSQL database")
            self._create_tables()
            
        except Exception as e:
            print(f"PostgreSQL connection failed: {str(e)}")
            # Fallback to in-memory storage for development
            self._use_memory_storage()
    
    def _create_tables(self):
        """Create database tables"""
        try:
            with self.conn.cursor() as cursor:
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        email VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Transfers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transfers (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        filename TEXT NOT NULL,
                        original_size BIGINT,
                        compressed_size BIGINT,
                        encrypted_size BIGINT,
                        remote_filename TEXT,
                        type VARCHAR(50) DEFAULT 'upload',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        compression_ratio NUMERIC(5,2)
                    )
                """)
                
                # Activities table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS activities (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        activity_type VARCHAR(100) NOT NULL,
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ip_address INET
                    )
                """)
                
                # Sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        session_token TEXT UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_transfers_user_timestamp ON transfers(user_id, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activities_user_timestamp ON activities(user_id, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
                
            print("Database tables created successfully")
            
        except Exception as e:
            print(f"Table creation failed: {str(e)}")
            raise
    
    def _use_memory_storage(self):
        """Fallback to in-memory storage for development"""
        print("Using in-memory storage (development mode)")
        self.memory_storage = {
            'users': {},
            'transfers': {},
            'activities': {},
            'sessions': {}
        }
        self.memory_mode = True
        self.next_id = 1
        self.conn = None
    
    def _get_next_id(self):
        """Get next ID for memory storage"""
        if hasattr(self, 'memory_mode') and self.memory_mode:
            self.next_id += 1
            return str(self.next_id)
        return None
    
    # User management
    def create_user(self, user_data):
        """Create a new user"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                user_id = self._get_next_id()
                user_data['id'] = user_id
                self.memory_storage['users'][user_id] = user_data
                return user_id
            
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, email, created_at, active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_data['username'],
                    user_data['password_hash'],
                    user_data.get('email'),
                    user_data.get('created_at', datetime.utcnow()),
                    user_data.get('active', True)
                ))
                user_id = cursor.fetchone()[0]
                return str(user_id)
            
        except Exception as e:
            print(f"Create user error: {str(e)}")
            return None
    
    def get_user(self, username):
        """Get user by username"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                for user in self.memory_storage['users'].values():
                    if user.get('username') == username:
                        return user
                return None
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user:
                    return dict(user)
                return None
            
        except Exception as e:
            print(f"Get user error: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                return self.memory_storage['users'].get(user_id)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if user:
                    return dict(user)
                return None
            
        except Exception as e:
            print(f"Get user by ID error: {str(e)}")
            return None
    
    def update_user_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                if user_id in self.memory_storage['users']:
                    self.memory_storage['users'][user_id]['last_login'] = datetime.utcnow()
                return
            
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users SET last_login = %s WHERE id = %s
                """, (datetime.utcnow(), user_id))
            
        except Exception as e:
            print(f"Update user login error: {str(e)}")
    
    # Transfer logging
    def log_transfer(self, transfer_data):
        """Log a file transfer"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                transfer_id = self._get_next_id()
                transfer_data['id'] = transfer_id
                self.memory_storage['transfers'][transfer_id] = transfer_data
                return transfer_id
            
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transfers (user_id, filename, original_size, compressed_size, 
                                         encrypted_size, remote_filename, type, compression_ratio)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    transfer_data['user_id'],
                    transfer_data['filename'],
                    transfer_data.get('original_size'),
                    transfer_data.get('compressed_size'),
                    transfer_data.get('encrypted_size'),
                    transfer_data.get('remote_filename'),
                    transfer_data.get('type', 'upload'),
                    transfer_data.get('compression_ratio')
                ))
                transfer_id = cursor.fetchone()[0]
                return str(transfer_id)
            
        except Exception as e:
            print(f"Log transfer error: {str(e)}")
            return None
    
    def get_transfer(self, transfer_id, user_id=None):
        """Get transfer by ID"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                transfer = self.memory_storage['transfers'].get(transfer_id)
                if transfer and (not user_id or transfer.get('user_id') == user_id):
                    return transfer
                return None
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                if user_id:
                    cursor.execute("SELECT * FROM transfers WHERE id = %s AND user_id = %s", 
                                 (transfer_id, user_id))
                else:
                    cursor.execute("SELECT * FROM transfers WHERE id = %s", (transfer_id,))
                
                transfer = cursor.fetchone()
                if transfer:
                    return dict(transfer)
                return None
            
        except Exception as e:
            print(f"Get transfer error: {str(e)}")
            return None
    
    def get_recent_transfers(self, user_id, limit=10):
        """Get recent transfers for a user"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                user_transfers = [
                    t for t in self.memory_storage['transfers'].values()
                    if t.get('user_id') == user_id
                ]
                user_transfers.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
                return user_transfers[:limit]
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM transfers 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (user_id, limit))
                
                transfers = cursor.fetchall()
                
                # Format for JSON response
                formatted_transfers = []
                for transfer in transfers:
                    formatted_transfer = {
                        'id': str(transfer['id']),
                        'filename': transfer['filename'] or 'Unknown',
                        'type': transfer['type'] or 'unknown',
                        'size': self._format_size(transfer['original_size'] or 0),
                        'compressed_size': self._format_size(transfer['compressed_size'] or 0),
                        'compression_ratio': float(transfer['compression_ratio']) if transfer['compression_ratio'] else 0,
                        'timestamp': transfer['timestamp'].isoformat() if transfer['timestamp'] else datetime.utcnow().isoformat()
                    }
                    formatted_transfers.append(formatted_transfer)
                
                return formatted_transfers
            
        except Exception as e:
            print(f"Get recent transfers error: {str(e)}")
            return []
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    # Activity logging
    def log_activity(self, user_id, activity_type, details=None):
        """Log user activity"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                activity_data = {
                    'user_id': user_id,
                    'activity_type': activity_type,
                    'details': details or {},
                    'timestamp': datetime.utcnow(),
                    'ip_address': None
                }
                activity_id = self._get_next_id()
                activity_data['id'] = activity_id
                self.memory_storage['activities'][activity_id] = activity_data
                return activity_id
            
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO activities (user_id, activity_type, details)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    activity_type,
                    json.dumps(details) if details else None
                ))
                activity_id = cursor.fetchone()[0]
                return str(activity_id)
            
        except Exception as e:
            print(f"Log activity error: {str(e)}")
            return None
    
    def get_user_activities(self, user_id, limit=50):
        """Get user activities"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                user_activities = [
                    a for a in self.memory_storage['activities'].values()
                    if a.get('user_id') == user_id
                ]
                user_activities.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
                return user_activities[:limit]
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM activities 
                    WHERE user_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (user_id, limit))
                
                activities = cursor.fetchall()
                return [dict(activity) for activity in activities]
            
        except Exception as e:
            print(f"Get user activities error: {str(e)}")
            return []
    
    # Session management
    def create_session(self, session_data):
        """Create user session"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                session_data['created_at'] = datetime.utcnow()
                session_data['expires_at'] = datetime.utcnow() + timedelta(hours=24)
                session_id = self._get_next_id()
                session_data['id'] = session_id
                self.memory_storage['sessions'][session_id] = session_data
                return session_id
            
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sessions (user_id, session_token, expires_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    session_data['user_id'],
                    session_data['session_token'],
                    session_data.get('expires_at', datetime.utcnow() + timedelta(hours=24))
                ))
                session_id = cursor.fetchone()[0]
                return str(session_id)
            
        except Exception as e:
            print(f"Create session error: {str(e)}")
            return None
    
    def get_session(self, session_id):
        """Get session by ID"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                session = self.memory_storage['sessions'].get(session_id)
                if session and session.get('expires_at', datetime.min) > datetime.utcnow():
                    return session
                return None
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM sessions 
                    WHERE id = %s AND expires_at > %s
                """, (session_id, datetime.utcnow()))
                
                session = cursor.fetchone()
                if session:
                    return dict(session)
                return None
            
        except Exception as e:
            print(f"Get session error: {str(e)}")
            return None
    
    def delete_session(self, session_id):
        """Delete session"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                if session_id in self.memory_storage['sessions']:
                    del self.memory_storage['sessions'][session_id]
                return
            
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            
        except Exception as e:
            print(f"Delete session error: {str(e)}")
    
    # Cleanup methods
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                now = datetime.utcnow()
                expired_sessions = [
                    sid for sid, session in self.memory_storage['sessions'].items()
                    if session.get('expires_at', datetime.min) <= now
                ]
                for sid in expired_sessions:
                    del self.memory_storage['sessions'][sid]
                return len(expired_sessions)
            
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE expires_at <= %s", (datetime.utcnow(),))
                return cursor.rowcount
            
        except Exception as e:
            print(f"Cleanup expired sessions error: {str(e)}")
            return 0
    
    def get_stats(self):
        """Get database statistics"""
        try:
            if hasattr(self, 'memory_mode') and self.memory_mode:
                return {
                    'users': len(self.memory_storage['users']),
                    'transfers': len(self.memory_storage['transfers']),
                    'activities': len(self.memory_storage['activities']),
                    'sessions': len(self.memory_storage['sessions']),
                    'storage_mode': 'memory'
                }
            
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM transfers")
                transfers_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM activities")
                activities_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM sessions")
                sessions_count = cursor.fetchone()[0]
                
                return {
                    'users': users_count,
                    'transfers': transfers_count,
                    'activities': activities_count,
                    'sessions': sessions_count,
                    'storage_mode': 'postgresql'
                }
            
        except Exception as e:
            print(f"Get stats error: {str(e)}")
            return {}