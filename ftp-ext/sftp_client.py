import paramiko
import os
import io
from datetime import datetime
import tempfile

class SFTPManager:
    """SFTP client manager for secure file transfers"""
    
    def __init__(self):
        # SECURITY: Require proper SFTP configuration - no insecure defaults
        self.host = os.getenv('SFTP_HOST')
        self.port = int(os.getenv('SFTP_PORT', '22'))
        self.username = os.getenv('SFTP_USERNAME')
        self.password = os.getenv('SFTP_PASSWORD')
        self.remote_path = os.getenv('SFTP_REMOTE_PATH', '/uploads')
        
        # Validate required SFTP configuration
        # Allow development mode when SFTP_DEV_MODE=true
        self.dev_mode = os.getenv('SFTP_DEV_MODE', 'false').lower() == 'true'
        
        if not self.host or not self.username or not self.password:
            if not self.dev_mode:
                raise ValueError(
                    "SFTP configuration required: Set SFTP_HOST, SFTP_USERNAME, and SFTP_PASSWORD environment variables. "
                    "For security, no default credentials are provided. "
                    "For development/testing, set SFTP_DEV_MODE=true to disable SFTP operations."
                )
            else:
                print("WARNING: Running in development mode - SFTP operations will fail gracefully")
        
        # REMOVED: Global state variables that caused persistent fallback issues
        # Each operation will attempt SFTP directly without global state tracking
        
    def _get_sftp_connection(self):
        """Establish SFTP connection with proper security"""
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            
            # Load system host keys for security
            try:
                ssh.load_system_host_keys()
                ssh.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            except FileNotFoundError:
                pass  # No known_hosts file exists yet
            
            # Use RejectPolicy for security - only connect to known hosts
            # For development, you can set SFTP_ACCEPT_UNKNOWN_HOSTS=true to accept unknown hosts
            if os.getenv('SFTP_ACCEPT_UNKNOWN_HOSTS', 'false').lower() == 'true':
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
            
            # Connect with timeout
            if not self.host or not self.username or not self.password:
                raise ValueError("SFTP connection parameters missing")
            
            ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            
            # Get SFTP client
            sftp = ssh.open_sftp()
            
            # Connection successful
            
            return ssh, sftp
        except Exception as e:
            print(f"SFTP connection error: {str(e)}")
            # REMOVED: Global state tracking that caused persistent fallback issues
            raise  # Re-raise exception so calling methods can handle it
    
    def upload_file(self, file_data, remote_filename):
        """Upload file to SFTP server"""
        try:
            # Check if in development mode
            if self.dev_mode:
                return {'success': False, 'error': 'SFTP not configured - running in development mode'}
            
            # Sanitize filename to prevent path traversal attacks
            sanitized_filename = os.path.basename(remote_filename)
            if not sanitized_filename or sanitized_filename.startswith('.'):
                return {'success': False, 'error': 'Invalid filename'}
            
            # REMOVED: Silent fallback to simulation - always try real SFTP
            return self._upload_via_sftp(file_data, sanitized_filename)
            
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _upload_via_sftp(self, file_data, remote_filename):
        """Actual SFTP implementation"""
        ssh = None
        sftp = None
        temp_file_path = None
        
        try:
            ssh, sftp = self._get_sftp_connection()
            
            # Ensure remote directory exists
            try:
                sftp.listdir(self.remote_path)
            except FileNotFoundError:
                sftp.mkdir(self.remote_path)
            
            # Create temporary file for upload
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            # Upload file
            remote_file_path = f"{self.remote_path}/{remote_filename}"
            sftp.put(temp_file_path, remote_file_path)
            
            # Set file permissions - 0o600 for better security (owner read/write only)
            sftp.chmod(remote_file_path, 0o600)
            
            return {
                'success': True,
                'remote_filename': remote_filename,
                'remote_path': remote_file_path,
                'size': len(file_data)
            }
            
        except Exception as e:
            print(f"SFTP upload error: {str(e)}")
            raise  # Re-raise so calling method can handle fallback
        finally:
            # Clean up resources
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    print(f"Warning: Could not remove temp file {temp_file_path}: {e}")
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    def download_file(self, remote_filename):
        """Download file from SFTP server"""
        try:
            # Check if in development mode
            if self.dev_mode:
                return {'success': False, 'error': 'SFTP not configured - running in development mode'}
            
            # Sanitize filename to prevent path traversal attacks
            sanitized_filename = os.path.basename(remote_filename)
            if not sanitized_filename or sanitized_filename.startswith('.'):
                return {'success': False, 'error': 'Invalid filename'}
            
            # REMOVED: Silent fallback to simulation - always try real SFTP
            return self._download_via_sftp(sanitized_filename)
            
        except Exception as e:
            print(f"Download error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _download_via_sftp(self, remote_filename):
        """Actual SFTP implementation"""
        ssh = None
        sftp = None
        temp_file_path = None
        
        try:
            ssh, sftp = self._get_sftp_connection()
            
            remote_file_path = f"{self.remote_path}/{remote_filename}"
            
            # Check if file exists
            try:
                file_stat = sftp.stat(remote_file_path)
            except FileNotFoundError:
                return {'success': False, 'error': 'File not found on server'}
            
            # Create temporary file for download
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # Download file
            sftp.get(remote_file_path, temp_file_path)
            
            # Read file data
            with open(temp_file_path, 'rb') as f:
                file_data = f.read()
            
            return {
                'success': True,
                'data': file_data,
                'size': len(file_data)
            }
            
        except Exception as e:
            print(f"SFTP download error: {str(e)}")
            raise  # Re-raise so calling method can handle fallback
        finally:
            # Clean up resources
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    print(f"Warning: Could not remove temp file {temp_file_path}: {e}")
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    def list_files(self, remote_directory=None):
        """List files in remote directory"""
        try:
            # Check if in development mode
            if self.dev_mode:
                return {'success': False, 'error': 'SFTP not configured - running in development mode'}
            
            # Validate directory path if provided
            if remote_directory:
                # Prevent path traversal - normalize and validate path
                normalized_dir = os.path.normpath(remote_directory)
                if '..' in normalized_dir or normalized_dir.startswith('/'):
                    return {'success': False, 'error': 'Invalid directory path'}
            
            # REMOVED: Silent fallback to simulation - always try real SFTP
            return self._list_files_via_sftp(remote_directory)
                
        except Exception as e:
            print(f"List files error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def _list_files_via_sftp(self, remote_directory=None):
        """Actual SFTP list implementation"""
        ssh = None
        sftp = None
        
        try:
            ssh, sftp = self._get_sftp_connection()
            
            directory = remote_directory or self.remote_path
            files = []
            
            # List directory contents
            for item in sftp.listdir_attr(directory):
                file_info = {
                    'filename': item.filename,
                    'size': item.st_size,
                    'modified': datetime.fromtimestamp(item.st_mtime).isoformat() if item.st_mtime else datetime.now().isoformat(),
                    'is_directory': item.st_mode is not None and (item.st_mode & 0o040000) != 0
                }
                files.append(file_info)
            
            return {
                'success': True,
                'files': files
            }
            
        except Exception as e:
            print(f"SFTP list error: {str(e)}")
            raise  # Re-raise so calling method can handle fallback
        finally:
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    def delete_file(self, remote_filename):
        """Delete file from SFTP server"""
        try:
            # Check if in development mode
            if self.dev_mode:
                return {'success': False, 'error': 'SFTP not configured - running in development mode'}
            
            # Sanitize filename to prevent path traversal attacks
            sanitized_filename = os.path.basename(remote_filename)
            if not sanitized_filename or sanitized_filename.startswith('.'):
                return {'success': False, 'error': 'Invalid filename'}
            
            # REMOVED: Silent fallback to simulation - always try real SFTP
            return self._delete_file_via_sftp(sanitized_filename)
                
        except Exception as e:
            print(f"Delete file error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def _delete_file_via_sftp(self, remote_filename):
        """Actual SFTP delete implementation"""
        ssh = None
        sftp = None
        
        try:
            ssh, sftp = self._get_sftp_connection()
            
            remote_file_path = f"{self.remote_path}/{remote_filename}"
            
            # Check if file exists
            try:
                sftp.stat(remote_file_path)
            except FileNotFoundError:
                return {'success': False, 'error': 'File not found on server'}
            
            # Delete file
            sftp.remove(remote_file_path)
            
            return {'success': True}
            
        except Exception as e:
            print(f"SFTP delete error: {str(e)}")
            raise  # Re-raise so calling method can handle fallback
        finally:
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
    
    def test_connection(self):
        """Test SFTP connection"""
        try:
            # Check if in development mode
            if self.dev_mode:
                return {'success': False, 'error': 'SFTP not configured - running in development mode'}
            
            # REMOVED: Silent fallback to simulation - always try real SFTP
            return self._test_connection_via_sftp()
                
        except Exception as e:
            print(f"Test connection error: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def _test_connection_via_sftp(self):
        """Actual SFTP connection test implementation"""
        ssh = None
        sftp = None
        
        try:
            ssh, sftp = self._get_sftp_connection()
            
            # Try to list remote directory
            sftp.listdir(self.remote_path)
            return {'success': True, 'message': 'SFTP connection successful'}
            
        except Exception as e:
            print(f"SFTP connection test error: {str(e)}")
            raise  # Re-raise so calling method can handle fallback
        finally:
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass
                    
    def get_connection_status(self):
        """Get current connection status"""
        return {
            'message': 'SFTP connection configured' if (self.host and self.username and self.password) else 'SFTP not configured',
            'host': self.host or 'Not configured',
            'username': self.username or 'Not configured'
        }
