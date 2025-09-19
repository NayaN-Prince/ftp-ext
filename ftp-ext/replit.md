# Secure SFTP Transfer Application

## Overview
A secure file transfer application with both Chrome extension and web interface components. Features AES encryption, gzip compression, user authentication with JWT tokens, and PostgreSQL database integration.

## Project Architecture

### Backend (Flask API)
- **Framework**: Flask with Flask-CORS
- **Database**: PostgreSQL with memory fallback
- **Authentication**: JWT tokens with bcrypt password hashing
- **Security**: AES encryption for file transfers
- **Compression**: Gzip compression for files

### Frontend (Web Interface)
- **Technology**: HTML5, CSS3, JavaScript (Vanilla)
- **UI Framework**: Bootstrap 5.3.0 with Font Awesome 6.0.0
- **Features**: Drag & drop file upload, transfer history, user management

### Chrome Extension
- **Manifest**: Version 3 Chrome extension
- **Components**: Background service worker, content scripts, popup interface
- **Permissions**: Storage, activeTab, scripting

## Recent Changes (September 16, 2025)
- **Project Import**: Successfully imported from GitHub and configured for Replit environment
- **Dependencies**: Installed Python 3.11 and all required packages via uv
- **Database**: Connected to PostgreSQL database with automatic table creation
- **Workflow**: Set up Flask server workflow running on port 5000 with SFTP development mode
- **Structure**: Reorganized project files to root directory for proper Replit operation

## Current Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (configured)
- `SFTP_DEV_MODE=true`: Enables development mode for SFTP operations
- `JWT_SECRET`: Auto-generated for JWT token signing
- `SESSION_SECRET`: Auto-generated for Flask sessions

### Server Configuration
- **Host**: 0.0.0.0 (accessible from Replit proxy)
- **Port**: 5000 (required for Replit frontend hosting)
- **CORS**: Enabled for all origins to support extension integration
- **Debug Mode**: Disabled for security

## User Preferences
- Using Python with uv package manager
- PostgreSQL database preferred over fallback storage
- Development mode enabled for SFTP operations (no external SFTP server required)
- Web interface served on same port as API for simplicity

## Project Structure
```
/
├── server.py              # Main Flask application
├── database.py            # PostgreSQL database manager
├── sftp_client.py         # SFTP client with dev mode support
├── encryption.py          # AES encryption utilities
├── static/               # Web interface assets
│   ├── index.html        # Main web interface
│   ├── style.css         # Application styling
│   └── script.js         # Frontend JavaScript
├── icons/                # Chrome extension icons
├── manifest.json         # Chrome extension manifest
├── popup.html/css/js     # Extension popup interface
├── background.js         # Extension background service worker
├── content.js            # Extension content script
├── pyproject.toml        # Python dependencies
└── uv.lock              # Dependency lock file
```

## API Endpoints
- `GET /api/health` - Health check
- `POST /api/register` - User registration
- `POST /api/login` - User authentication
- `POST /api/logout` - User logout
- `POST /api/verify-token` - Token verification
- `GET /api/recent-transfers` - Get transfer history
- `POST /api/upload` - File upload with encryption
- `GET /api/download/<id>` - File download with decryption

## Security Features
- JWT-based authentication with configurable expiration
- bcrypt password hashing with salt
- AES encryption for file data
- CORS properly configured for extension integration
- SQL injection protection via parameterized queries
- Development mode fallback for SFTP operations