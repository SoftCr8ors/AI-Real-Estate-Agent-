"""
Encryption utilities for sensitive data (AI API keys).
Uses Fernet symmetric encryption with key from environment.
"""

import os
from typing import Optional

from cryptography.fernet import Fernet


class CryptoService:
    """
    Encrypts and decrypts sensitive settings like API keys.
    Encryption key must be in ENCRYPTION_KEY env var.
    """
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialize()
    
    def _initialize(self):
        """Load encryption key from environment."""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            # For development: generate a key (WARNING: will change on restart)
            # For production: MUST set ENCRYPTION_KEY in environment
            import warnings
            warnings.warn(
                "ENCRYPTION_KEY not set. Using generated key (data will be lost on restart). "
                "Set ENCRYPTION_KEY in production!",
                UserWarning
            )
            key = Fernet.generate_key().decode()
        
        # Ensure key is bytes
        key_bytes = key.encode() if isinstance(key, str) else key
        self._fernet = Fernet(key_bytes)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.
        
        Args:
            plaintext: The secret to encrypt (e.g., API key)
            
        Returns:
            Encrypted string safe to store in database
        """
        if not plaintext:
            return ""
        
        if not self._fernet:
            raise RuntimeError("Crypto service not initialized")
        
        encrypted_bytes = self._fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext back to plaintext.
        
        Args:
            ciphertext: Encrypted string from database
            
        Returns:
            Decrypted plaintext (original API key)
            
        Raises:
            cryptography.fernet.InvalidToken: If ciphertext is corrupted or key changed
        """
        if not ciphertext:
            return ""
        
        if not self._fernet:
            raise RuntimeError("Crypto service not initialized")
        
        decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key for ENCRYPTION_KEY environment variable.
        
        Usage:
            python -c "from app.core.crypto import CryptoService; print(CryptoService.generate_key())"
        
        Returns:
            Base64-encoded Fernet key (44 chars)
        """
        return Fernet.generate_key().decode()


# Global singleton instance
crypto_service = CryptoService()