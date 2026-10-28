from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64
import os
from typing import Tuple

class Encryption:
    def __init__(self, key: str = None):
        """Initialize encryption with key derivation."""
        master_key = key or os.getenv('ENCRYPTION_KEY')
        if not master_key:
            raise ValueError("Encryption key not provided")
        
        # Use key derivation for better security
        salt = os.getenv('ENCRYPTION_SALT')
        if salt is None:
            salt = b'smart_elect_salt'
        else:
            salt = salt.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Derive the key and initialize Fernet
        key_bytes = base64.b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key_bytes)
        
        # Cache for frequently used values
        self._cache = {}
    
    def encrypt(self, data: str) -> str:
        """Encrypt data using Fernet symmetric encryption with caching."""
        if not isinstance(data, str):
            raise ValueError("Data must be a string")
            
        # Check cache for frequently encrypted values
        cache_key = f"enc_{hash(data)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        encrypted = self.fernet.encrypt(data.encode()).decode()
        self._cache[cache_key] = encrypted
        return encrypted
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt Fernet encrypted data with caching."""
        if not isinstance(encrypted_data, str):
            raise ValueError("Encrypted data must be a string")
            
        # Check cache for frequently decrypted values
        cache_key = f"dec_{hash(encrypted_data)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode()).decode()
            self._cache[cache_key] = decrypted
            return decrypted
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

class AsymmetricEncryption:
    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """Generate a new RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Serialize keys to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    @staticmethod
    def encrypt_vote(public_key_pem: str, vote_data: str) -> str:
        """Encrypt vote data using RSA public key"""
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        
        encrypted = public_key.encrypt(
            vote_data.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt_vote(private_key_pem: str, encrypted_vote: str) -> str:
        """Decrypt vote data using RSA private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        
        encrypted_data = base64.b64decode(encrypted_vote.encode())
        decrypted = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted.decode()