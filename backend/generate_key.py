# -*- coding: utf-8 -*-

import os
import base64

def generate_jwt_key(length=32):
    # Generate a secure random key
    random_bytes = os.urandom(length)
    # Encode in base64 for readable string
    jwt_key = base64.b64encode(random_bytes).decode('utf-8')
    return jwt_key

def main():
    # Generate a 32 bytes (256 bits) key
    jwt_key = generate_jwt_key()
    
    print("\nJWT key generated successfully!")
    print("=" * 50)
    print("\nYour new JWT key:")
    print("=" * 50)
    print(jwt_key)
    print("=" * 50)
    print("\nCopy this key to your .env file as JWT_SECRET_KEY value")
    print("Example: JWT_SECRET_KEY=" + jwt_key)
    print("\nKeep this key secure and never share it!\n")

if __name__ == "__main__":
    main()