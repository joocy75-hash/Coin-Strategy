"""Configuration management for TradingView Strategy Research Lab."""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Config(BaseSettings):
    """Application configuration using pydantic-settings."""

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Database
    db_path: str = "data/strategies.db"

    # Scraping
    max_strategies: int = 100
    min_likes: int = 200  # 품질 우선: 커뮤니티 검증된 전략
    headless: bool = True
    timeout: int = 30000  # milliseconds

    # Quality Filtering (분석 후 필터링)
    min_code_score: int = 80  # 코드 품질 최소 점수
    min_total_score: int = 60  # 종합 점수 최소
    require_no_repainting: bool = True  # 리페인팅 이슈 없는 전략만
    max_overfitting_issues: int = 2  # 허용 가능한 과적합 이슈 수

    # Analysis
    llm_model: str = "claude-3-5-sonnet-20241022"
    skip_llm: bool = False
    max_retries: int = 3

    # Paths
    output_dir: str = "data/converted"
    platform_path: Optional[str] = None
    logs_dir: str = "logs"

    # Rate Limiting
    rate_limit_delay: float = 1.0  # seconds between requests

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment and .env file."""
        return cls()

    def get_db_path(self) -> Path:
        """Get absolute path to database file."""
        return Path(self.db_path).resolve()

    def get_output_dir(self) -> Path:
        """Get absolute path to output directory."""
        return Path(self.output_dir).resolve()

    def get_logs_dir(self) -> Path:
        """Get absolute path to logs directory."""
        return Path(self.logs_dir).resolve()

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.get_output_dir().mkdir(parents=True, exist_ok=True)
        self.get_logs_dir().mkdir(parents=True, exist_ok=True)
        self.get_db_path().parent.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config.load()
