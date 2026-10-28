import os
import base64
from cryptography.fernet import Fernet

def generate_secret_key():
    """Generate a secure secret key for Flask"""
    return base64.b64encode(os.urandom(32)).decode('utf-8')

def generate_encryption_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode('utf-8')

def main():
    try:
        # Generate keys
        secret_key = generate_secret_key()
        encryption_key = generate_encryption_key()
        
        # Create .env file content
        env_content = f"""# Security Keys
SECRET_KEY={secret_key}
ENCRYPTION_KEY={encryption_key}

# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=root1
DB_NAME=evoting_db

# Application Settings
FLASK_APP=run.py
FLASK_ENV=production
"""
        
        # Write to .env file
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✓ Security keys generated and saved to .env file")
        print("⚠ Please ensure to keep the .env file secure and never commit it to version control")
    except Exception as e:
        print(f"Error generating keys: {str(e)}")
        return 1
    return 0

if __name__ == '__main__':
    exit(main())