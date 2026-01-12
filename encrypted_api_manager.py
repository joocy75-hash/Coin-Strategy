#!/usr/bin/env python3
"""
Encrypted API Manager - 보안 강화된 API 키 관리

시스템 키체인 또는 암호화된 파일을 통해 API 키를 안전하게 관리합니다.
"""

import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography not installed. Using basic encryption.")


@dataclass
class APICredentials:
    """API 자격 증명"""
    api_key: str
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    exchange: str = "binance"
    is_testnet: bool = True
    created_at: Optional[str] = None


class SecureAPIManager:
    """
    보안 강화된 API 키 관리자
    
    Features:
    - Fernet 대칭 암호화
    - 환경변수 기반 마스터 키
    - 암호화된 파일 저장
    - 키 마스킹 로깅
    """
    
    def __init__(self, storage_path: str = ".secure_keys"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cipher = self._init_cipher()
        
    def _init_cipher(self) -> Optional[Any]:
        """암호화 cipher 초기화"""
        if not CRYPTO_AVAILABLE:
            return None
            
        # 마스터 키는 환경변수에서 가져옴
        master_key = os.getenv("MASTER_ENCRYPTION_KEY", "default_dev_key_change_in_prod")
        salt = os.getenv("ENCRYPTION_SALT", "strategy_research_lab").encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """데이터 암호화"""
        if self._cipher:
            return self._cipher.encrypt(data.encode()).decode()
        # Fallback: Base64 인코딩 (개발용)
        return base64.b64encode(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        if self._cipher:
            return self._cipher.decrypt(encrypted_data.encode()).decode()
        # Fallback: Base64 디코딩
        return base64.b64decode(encrypted_data.encode()).decode()
    
    def store_credentials(self, name: str, credentials: APICredentials) -> bool:
        """자격 증명 암호화 저장"""
        try:
            data = {
                "api_key": self.encrypt(credentials.api_key),
                "api_secret": self.encrypt(credentials.api_secret) if credentials.api_secret else None,
                "passphrase": self.encrypt(credentials.passphrase) if credentials.passphrase else None,
                "exchange": credentials.exchange,
                "is_testnet": credentials.is_testnet,
                "created_at": datetime.now().isoformat(),
            }
            
            file_path = self.storage_path / f"{name}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            os.chmod(file_path, 0o600)
            return True
            
        except Exception as e:
            print(f"Error storing credentials: {e}")
            return False
    
    def load_credentials(self, name: str) -> Optional[APICredentials]:
        """자격 증명 로드 및 복호화"""
        try:
            file_path = self.storage_path / f"{name}.json"
            if not file_path.exists():
                return None
                
            with open(file_path, "r") as f:
                data = json.load(f)
            
            return APICredentials(
                api_key=self.decrypt(data["api_key"]),
                api_secret=self.decrypt(data["api_secret"]) if data.get("api_secret") else None,
                passphrase=self.decrypt(data["passphrase"]) if data.get("passphrase") else None,
                exchange=data.get("exchange", "binance"),
                is_testnet=data.get("is_testnet", True),
                created_at=data.get("created_at"),
            )
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def delete_credentials(self, name: str) -> bool:
        """자격 증명 삭제"""
        try:
            file_path = self.storage_path / f"{name}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting credentials: {e}")
            return False
    
    def list_credentials(self) -> list:
        """저장된 자격 증명 목록"""
        return [f.stem for f in self.storage_path.glob("*.json")]
    
    @staticmethod
    def mask_key(key: str, visible_chars: int = 4) -> str:
        """API 키 마스킹 (로깅용)"""
        if not key or len(key) <= visible_chars * 2:
            return "***"
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"
    
    def get_from_env(self, exchange: str = "binance") -> Optional[APICredentials]:
        """환경변수에서 자격 증명 로드"""
        prefix = exchange.upper()
        
        api_key = os.getenv(f"{prefix}_API_KEY")
        api_secret = os.getenv(f"{prefix}_API_SECRET")
        
        if not api_key:
            return None
            
        return APICredentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=os.getenv(f"{prefix}_PASSPHRASE"),
            exchange=exchange,
            is_testnet=os.getenv("USE_TESTNET", "true").lower() == "true",
        )


# 싱글톤 인스턴스
_manager: Optional[SecureAPIManager] = None


def get_api_manager() -> SecureAPIManager:
    """API Manager 싱글톤 인스턴스 반환"""
    global _manager
    if _manager is None:
        _manager = SecureAPIManager()
    return _manager


if __name__ == "__main__":
    # 테스트
    manager = get_api_manager()
    
    # 환경변수에서 로드 테스트
    creds = manager.get_from_env("binance")
    if creds:
        print(f"Loaded from env: {manager.mask_key(creds.api_key)}")
    else:
        print("No credentials in environment variables")
    
    # 암호화 저장 테스트
    test_creds = APICredentials(
        api_key="test_api_key_12345",
        api_secret="test_secret_67890",
        exchange="binance",
        is_testnet=True,
    )
    
    if manager.store_credentials("test_exchange", test_creds):
        print("Credentials stored successfully")
        
        # 로드 테스트
        loaded = manager.load_credentials("test_exchange")
        if loaded:
            print(f"Loaded: {manager.mask_key(loaded.api_key)}")
            
        # 정리
        manager.delete_credentials("test_exchange")
        print("Test credentials deleted")
