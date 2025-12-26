# src/collector/session_manager.py

import asyncio
import random
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """프록시 정보"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    fail_count: int = 0
    last_used: Optional[datetime] = None

    @property
    def url(self) -> str:
        """프록시 URL 생성"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        """프록시 상태 확인"""
        return self.fail_count < 3


@dataclass
class RateLimitConfig:
    """Rate Limiting 설정"""
    requests_per_minute: int = 20
    min_delay: float = 2.0
    max_delay: float = 8.0
    backoff_base: float = 2.0
    max_backoff: float = 300.0


class SessionManager:
    """
    세션 관리자

    기능:
    - 프록시 로테이션
    - Rate Limiting
    - 지수 백오프
    - User-Agent 로테이션
    - 쿠키 관리
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    VIEWPORT_SIZES = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 2560, "height": 1440},
    ]

    def __init__(
        self,
        proxies: Optional[List[ProxyInfo]] = None,
        rate_limit: Optional[RateLimitConfig] = None,
    ):
        self.proxies = proxies or []
        self.rate_limit = rate_limit or RateLimitConfig()

        self._current_proxy_index = 0
        self._request_times: List[datetime] = []
        self._consecutive_errors = 0
        self._cookies: Dict[str, str] = {}

    def get_random_user_agent(self) -> str:
        """랜덤 User-Agent 반환"""
        return random.choice(self.USER_AGENTS)

    def get_random_viewport(self) -> Dict[str, int]:
        """랜덤 뷰포트 크기 반환"""
        return random.choice(self.VIEWPORT_SIZES)

    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """다음 프록시 반환 (라운드 로빈)"""
        if not self.proxies:
            return None

        # 건강한 프록시 필터링
        healthy_proxies = [p for p in self.proxies if p.is_healthy]

        if not healthy_proxies:
            # 모든 프록시 리셋
            logger.warning("All proxies failed, resetting...")
            for p in self.proxies:
                p.fail_count = 0
            healthy_proxies = self.proxies

        # 라운드 로빈
        self._current_proxy_index = (self._current_proxy_index + 1) % len(healthy_proxies)
        proxy = healthy_proxies[self._current_proxy_index]
        proxy.last_used = datetime.now()

        return proxy

    def mark_proxy_failed(self, proxy: ProxyInfo):
        """프록시 실패 기록"""
        proxy.fail_count += 1
        logger.warning(f"Proxy {proxy.host}:{proxy.port} failed ({proxy.fail_count} times)")

    def mark_proxy_success(self, proxy: ProxyInfo):
        """프록시 성공 시 실패 카운트 리셋"""
        proxy.fail_count = 0

    async def wait_for_rate_limit(self):
        """Rate Limit 대기"""
        now = datetime.now()

        # 1분 이상 지난 요청 제거
        cutoff = now - timedelta(minutes=1)
        self._request_times = [t for t in self._request_times if t > cutoff]

        # Rate limit 체크
        if len(self._request_times) >= self.rate_limit.requests_per_minute:
            # 가장 오래된 요청이 1분 지날 때까지 대기
            oldest = min(self._request_times)
            wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()

            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        # 요청 시간 기록
        self._request_times.append(datetime.now())

        # 랜덤 딜레이
        delay = random.uniform(self.rate_limit.min_delay, self.rate_limit.max_delay)
        await asyncio.sleep(delay)

    async def exponential_backoff(self, attempt: Optional[int] = None) -> float:
        """지수 백오프"""
        if attempt is None:
            attempt = self._consecutive_errors

        delay = min(
            self.rate_limit.max_backoff,
            (self.rate_limit.backoff_base ** attempt) + random.uniform(0, 1)
        )

        logger.info(f"Exponential backoff: waiting {delay:.1f}s (attempt {attempt})")
        await asyncio.sleep(delay)

        return delay

    def record_success(self):
        """성공 기록 - 에러 카운트 리셋"""
        self._consecutive_errors = 0

    def record_error(self):
        """에러 기록"""
        self._consecutive_errors += 1
        return self._consecutive_errors

    def get_browser_context_options(self) -> Dict:
        """브라우저 컨텍스트 옵션 생성"""
        options = {
            "user_agent": self.get_random_user_agent(),
            "viewport": self.get_random_viewport(),
            "locale": random.choice(["en-US", "en-GB", "en"]),
            "timezone_id": random.choice([
                "America/New_York",
                "America/Los_Angeles",
                "Europe/London",
                "Asia/Tokyo",
            ]),
            "permissions": ["geolocation"],
            "geolocation": {
                "longitude": random.uniform(-122, -74),
                "latitude": random.uniform(34, 47),
            },
            "color_scheme": random.choice(["light", "dark"]),
        }

        # 프록시 추가
        proxy = self.get_next_proxy()
        if proxy:
            options["proxy"] = {"server": proxy.url}

        return options

    def get_stealth_scripts(self) -> List[str]:
        """봇 탐지 우회 스크립트"""
        return [
            # webdriver 속성 숨기기
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """,

            # plugins 속성 설정
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """,

            # Chrome 객체 설정
            """
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            """,

            # permissions 쿼리 오버라이드
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,

            # 언어 설정
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """,
        ]

    def set_cookies(self, cookies: Dict[str, str]):
        """쿠키 설정"""
        self._cookies.update(cookies)

    def get_cookies(self) -> Dict[str, str]:
        """쿠키 반환"""
        return self._cookies.copy()

    def clear_cookies(self):
        """쿠키 초기화"""
        self._cookies.clear()

    @property
    def consecutive_errors(self) -> int:
        """연속 에러 수"""
        return self._consecutive_errors

    def should_rotate_proxy(self) -> bool:
        """프록시 로테이션 필요 여부"""
        return self._consecutive_errors >= 2

    def add_proxy(self, host: str, port: int, username: str = None, password: str = None):
        """프록시 추가"""
        self.proxies.append(ProxyInfo(
            host=host,
            port=port,
            username=username,
            password=password,
        ))

    def load_proxies_from_file(self, filepath: str):
        """파일에서 프록시 로드 (host:port:user:pass 형식)"""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split(':')
                    if len(parts) >= 2:
                        host = parts[0]
                        port = int(parts[1])
                        username = parts[2] if len(parts) > 2 else None
                        password = parts[3] if len(parts) > 3 else None

                        self.add_proxy(host, port, username, password)

            logger.info(f"Loaded {len(self.proxies)} proxies from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
