#!/usr/bin/env python3
"""
API Manager - API 키 관리 및 거래소 연결

환경변수에서 API 키를 로드하고 거래소 연결을 관리합니다.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False


@dataclass
class ExchangeConfig:
    """거래소 설정"""
    exchange_id: str = "binance"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None  # OKX 등에서 필요
    use_testnet: bool = True
    paper_trading: bool = True
    options: Dict[str, Any] = field(default_factory=dict)


class APIManager:
    """
    API 키 관리 및 거래소 연결 관리자
    
    Features:
    - 환경변수에서 API 키 로드
    - 다중 거래소 지원
    - Testnet/Mainnet 전환
    - Paper Trading 모드
    """
    
    SUPPORTED_EXCHANGES = ["binance", "bybit", "okx", "bitget"]
    
    def __init__(self):
        self._exchanges: Dict[str, Any] = {}
        self._configs: Dict[str, ExchangeConfig] = {}
        
    def load_config(self, exchange_id: str = "binance") -> ExchangeConfig:
        """환경변수에서 거래소 설정 로드"""
        prefix = exchange_id.upper()
        
        config = ExchangeConfig(
            exchange_id=exchange_id,
            api_key=os.getenv(f"{prefix}_API_KEY"),
            api_secret=os.getenv(f"{prefix}_API_SECRET"),
            passphrase=os.getenv(f"{prefix}_PASSPHRASE"),
            use_testnet=os.getenv("USE_TESTNET", "true").lower() == "true",
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
        )
        
        self._configs[exchange_id] = config
        return config
    
    def get_exchange(self, exchange_id: str = "binance") -> Optional[Any]:
        """거래소 인스턴스 반환 (캐싱)"""
        if not CCXT_AVAILABLE:
            print("Error: ccxt not installed")
            return None
            
        if exchange_id in self._exchanges:
            return self._exchanges[exchange_id]
            
        config = self._configs.get(exchange_id) or self.load_config(exchange_id)
        
        try:
            exchange_class = getattr(ccxt, exchange_id)
            
            exchange_options = {
                "enableRateLimit": True,
                "options": config.options,
            }
            
            # API 키가 있으면 추가
            if config.api_key:
                exchange_options["apiKey"] = config.api_key
            if config.api_secret:
                exchange_options["secret"] = config.api_secret
            if config.passphrase:
                exchange_options["password"] = config.passphrase
                
            # Testnet 설정
            if config.use_testnet:
                if exchange_id == "binance":
                    exchange_options["options"] = {
                        "defaultType": "future",
                        "sandboxMode": True,
                    }
                elif exchange_id == "bybit":
                    exchange_options["options"] = {"testnet": True}
                    
            exchange = exchange_class(exchange_options)
            
            # Testnet URL 설정
            if config.use_testnet:
                exchange.set_sandbox_mode(True)
                
            self._exchanges[exchange_id] = exchange
            return exchange
            
        except Exception as e:
            print(f"Error creating exchange {exchange_id}: {e}")
            return None
    
    def test_connection(self, exchange_id: str = "binance") -> Dict[str, Any]:
        """거래소 연결 테스트"""
        result = {
            "exchange": exchange_id,
            "connected": False,
            "timestamp": datetime.now().isoformat(),
            "error": None,
        }
        
        try:
            exchange = self.get_exchange(exchange_id)
            if not exchange:
                result["error"] = "Failed to create exchange instance"
                return result
                
            # 시장 정보 로드 테스트
            exchange.load_markets()
            result["connected"] = True
            result["markets_count"] = len(exchange.markets)
            
            # 잔고 조회 테스트 (API 키가 있는 경우)
            config = self._configs.get(exchange_id)
            if config and config.api_key and not config.paper_trading:
                try:
                    balance = exchange.fetch_balance()
                    result["balance_available"] = True
                except Exception as e:
                    result["balance_available"] = False
                    result["balance_error"] = str(e)
                    
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def get_balance(self, exchange_id: str = "binance", currency: str = "USDT") -> float:
        """잔고 조회"""
        config = self._configs.get(exchange_id) or self.load_config(exchange_id)
        
        # Paper Trading 모드
        if config.paper_trading:
            return float(os.getenv("PAPER_TRADING_BALANCE", "10000"))
            
        exchange = self.get_exchange(exchange_id)
        if not exchange:
            return 0.0
            
        try:
            balance = exchange.fetch_balance()
            return float(balance.get(currency, {}).get("free", 0))
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return 0.0
    
    def mask_key(self, key: Optional[str], visible_chars: int = 4) -> str:
        """API 키 마스킹 (로깅용)"""
        if not key or len(key) <= visible_chars * 2:
            return "***"
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"
    
    def get_status(self) -> Dict[str, Any]:
        """전체 상태 조회"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "exchanges": {},
        }
        
        for exchange_id, config in self._configs.items():
            status["exchanges"][exchange_id] = {
                "has_api_key": bool(config.api_key),
                "api_key_masked": self.mask_key(config.api_key) if config.api_key else None,
                "use_testnet": config.use_testnet,
                "paper_trading": config.paper_trading,
            }
            
        return status


# 싱글톤 인스턴스
_api_manager: Optional[APIManager] = None


def get_api_manager() -> APIManager:
    """API Manager 싱글톤 인스턴스 반환"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
    return _api_manager


if __name__ == "__main__":
    # 테스트
    manager = get_api_manager()
    
    # 설정 로드
    config = manager.load_config("binance")
    print(f"Binance config loaded:")
    print(f"  API Key: {manager.mask_key(config.api_key)}")
    print(f"  Testnet: {config.use_testnet}")
    print(f"  Paper Trading: {config.paper_trading}")
    
    # 연결 테스트
    print("\nTesting connection...")
    result = manager.test_connection("binance")
    print(f"  Connected: {result['connected']}")
    if result.get("error"):
        print(f"  Error: {result['error']}")
    if result.get("markets_count"):
        print(f"  Markets: {result['markets_count']}")
        
    # 잔고 조회
    balance = manager.get_balance("binance", "USDT")
    print(f"\nUSDT Balance: ${balance:,.2f}")
