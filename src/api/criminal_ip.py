import requests
from typing import Dict, Any

class CriminalIPAPI:
    BASE_URL = "https://api.criminalip.io/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict:
        """API 요청을 수행하는 내부 메서드"""
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def search_ip(self, ip: str) -> Dict:
        """IP 주소 검색"""
        return self._make_request("asset/ip/report", {"ip": ip, "full": "true"})
    
    def search_domain(self, domain: str) -> Dict:
        """도메인 검색"""
        return self._make_request("domain/data", {"domain": domain})
    
    def port_scan(self, ip: str) -> Dict:
        """포트 스캔"""
        return self._make_request("port/scan", {"ip": ip})
    
    def ip_summary(self, ip: str) -> Dict:
        """IP 주소 상세 정보 조회"""
        return self._make_request("asset/ip/report", {"ip": ip, "full": "true"})
    
    def ip_detail(self, ip: str) -> Dict:
        """IP 주소 상세 리포트 조회"""
        return self._make_request("asset/ip/report", {"ip": ip, "full": "true"})
    
    def ip_reputation(self, ip: str) -> Dict:
        """IP 주소 평판 정보 조회"""
        return self._make_request("ip/reputation", {"ip": ip}) 