import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CryptoUtils:
    """암호화 유틸리티 클래스"""
    
    @staticmethod
    def generate_key(password, salt=None):
        """비밀번호와 솔트를 사용하여 암호화 키 생성"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def encrypt(text, key):
        """텍스트 암호화"""
        f = Fernet(key)
        return f.encrypt(text.encode()).decode()
    
    @staticmethod
    def decrypt(encrypted_text, key):
        """암호화된 텍스트 복호화"""
        f = Fernet(key)
        return f.decrypt(encrypted_text.encode()).decode() 