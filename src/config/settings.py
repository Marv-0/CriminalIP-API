import os
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("CRIMINAL_IP_API_KEY", "")
    
    def save_api_key(self, api_key: str) -> None:
        """API 키를 .env 파일에 저장합니다."""
        with open(".env", "w") as f:
            f.write(f"CRIMINAL_IP_API_KEY={api_key}")
        self.api_key = api_key
    
    def get_api_key(self) -> str:
        """저장된 API 키를 반환합니다."""
        return self.api_key 