from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64
import secrets

class AESCipher:
    """AES encryption/decryption using Fernet (AES 128 in CBC mode)"""
    
    def __init__(self, password=None):
        """Initialize cipher with password or generate random key"""
        if password:
            self.key = self._derive_key_from_password(password)
        else:
            # Use environment variable or generate random key
            key_b64 = os.getenv('ENCRYPTION_KEY')
            if key_b64:
                try:
                    self.key = base64.urlsafe_b64decode(key_b64.encode())
                except Exception:
                    self.key = self._generate_key()
            else:
                self.key = self._generate_key()
        
        self.fernet = Fernet(self.key)
    
    def _generate_key(self):
        """Generate a new encryption key"""
        return Fernet.generate_key()
    
    def _derive_key_from_password(self, password):
        """Derive encryption key from password using PBKDF2"""
        # Use a fixed salt for consistency (in production, use unique salts per user)
        salt = os.getenv('ENCRYPTION_SALT', 'secure-sftp-salt').encode()[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data):
        """Encrypt data (bytes or string)"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self.fernet.encrypt(data)
            return encrypted_data
            
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data):
        """Decrypt data"""
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode('utf-8')
            
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return decrypted_data
            
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    def encrypt_file(self, file_path, output_path=None):
        """Encrypt a file"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Encrypt data
            encrypted_data = self.encrypt(file_data)
            
            # Write encrypted file
            if output_path is None:
                output_path = file_path + '.enc'
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return {
                'success': True,
                'input_file': file_path,
                'output_file': output_path,
                'original_size': len(file_data),
                'encrypted_size': len(encrypted_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def decrypt_file(self, encrypted_file_path, output_path=None):
        """Decrypt a file"""
        try:
            if not os.path.exists(encrypted_file_path):
                raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
            
            # Read encrypted file
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            decrypted_data = self.decrypt(encrypted_data)
            
            # Write decrypted file
            if output_path is None:
                if encrypted_file_path.endswith('.enc'):
                    output_path = encrypted_file_path[:-4]  # Remove .enc extension
                else:
                    output_path = encrypted_file_path + '.dec'
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return {
                'success': True,
                'input_file': encrypted_file_path,
                'output_file': output_path,
                'encrypted_size': len(encrypted_data),
                'decrypted_size': len(decrypted_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_key_info(self):
        """Get information about the encryption key"""
        return {
            'key_length': len(self.key),
            'key_b64': base64.urlsafe_b64encode(self.key).decode(),
            'algorithm': 'AES-128-CBC (Fernet)'
        }

class FileEncryptionManager:
    """Manager for handling file encryption with metadata"""
    
    def __init__(self, cipher=None):
        self.cipher = cipher or AESCipher()
    
    def encrypt_with_metadata(self, data, filename, metadata=None):
        """Encrypt data with metadata"""
        try:
            # Prepare metadata
            file_metadata = {
                'filename': filename,
                'size': len(data),
                'encrypted_at': os.urandom(16).hex(),  # Random token for uniqueness
                'metadata': metadata or {}
            }
            
            # Combine metadata and data
            metadata_json = str(file_metadata).encode('utf-8')
            metadata_length = len(metadata_json).to_bytes(4, byteorder='big')
            combined_data = metadata_length + metadata_json + data
            
            # Encrypt combined data
            encrypted_data = self.cipher.encrypt(combined_data)
            
            return {
                'success': True,
                'encrypted_data': encrypted_data,
                'metadata': file_metadata,
                'original_size': len(data),
                'encrypted_size': len(encrypted_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def decrypt_with_metadata(self, encrypted_data):
        """Decrypt data and extract metadata"""
        try:
            # Decrypt data
            decrypted_combined = self.cipher.decrypt(encrypted_data)
            
            # Extract metadata length
            metadata_length = int.from_bytes(decrypted_combined[:4], byteorder='big')
            
            # Extract metadata
            metadata_json = decrypted_combined[4:4+metadata_length]
            file_metadata = eval(metadata_json.decode('utf-8'))  # In production, use json.loads
            
            # Extract original data
            original_data = decrypted_combined[4+metadata_length:]
            
            return {
                'success': True,
                'data': original_data,
                'metadata': file_metadata,
                'decrypted_size': len(original_data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def generate_secure_key():
    """Generate a secure encryption key"""
    return Fernet.generate_key()

def generate_secure_password(length=32):
    """Generate a secure random password"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))
