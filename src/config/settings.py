import os
import json
from dotenv import load_dotenv
from ..utils.crypto import CryptoUtils

class Settings:
    """애플리케이션 설정 관리 클래스"""
    
    def __init__(self):
        """설정 초기화"""
        load_dotenv()
        
        # 암호화 키와 솔트 가져오기 또는 생성
        self._load_or_create_crypto_key()
        
        # API 키 가져오기
        encrypted_api_key = os.getenv("CRIMINAL_IP_API_KEY", "")
        if encrypted_api_key:
            try:
                self.api_key = CryptoUtils.decrypt(encrypted_api_key, self.crypto_key)
            except Exception:
                self.api_key = ""
        else:
            self.api_key = ""
    
    def _load_or_create_crypto_key(self):
        """암호화 키와 솔트 로드 또는 생성"""
        # 고정된 비밀번호 (실제 환경에서는 더 안전한 방법 사용 필요)
        password = "criminal_ip_api_secret"
        
        # 솔트 로드 또는 생성
        salt = os.getenv("CRYPTO_SALT")
        if salt:
            salt = salt.encode()
        else:
            salt = os.urandom(16)
            with open(".env", "a") as f:
                f.write(f"\nCRYPTO_SALT={salt.decode()}")
        
        # 암호화 키 생성
        self.crypto_key, _ = CryptoUtils.generate_key(password, salt)
    
    def get_api_key(self) -> str:
        """저장된 API 키를 반환합니다."""
        return self.api_key
    
    def save_api_key(self, api_key: str) -> None:
        """API 키를 암호화하여 .env 파일에 저장합니다."""
        # API 키 암호화
        encrypted_api_key = CryptoUtils.encrypt(api_key, self.crypto_key)
        
        # .env 파일에 저장
        with open(".env", "w") as f:
            f.write(f"CRIMINAL_IP_API_KEY={encrypted_api_key}\n")
            # 솔트도 함께 저장
            f.write(f"CRYPTO_SALT={os.getenv('CRYPTO_SALT', '').encode().decode()}\n")
        
        self.api_key = api_key 