"""
Conversion Cache

Caches conversion results to avoid redundant LLM API calls.
Uses SHA256 hashing of Pine Script code for cache keys.
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached conversion entry"""
    pine_code_hash: str
    python_code: str
    strategy_used: str
    cost_usd: float
    timestamp: str
    ttl_days: int = 30


class ConversionCache:
    """
    File-based cache for conversion results.

    Benefits:
    - Avoid redundant LLM API calls
    - Instant results for re-conversions
    - Cost savings

    Example:
        >>> cache = ConversionCache()
        >>> cached = cache.get(pine_code)
        >>> if not cached:
        ...     result = await converter.convert(ast)
        ...     cache.set(pine_code, result)
    """

    def __init__(self, cache_dir: str = ".cache/conversions"):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Initialized ConversionCache at {self.cache_dir}")

    def get(self, pine_code: str) -> Optional[dict]:
        """
        Get cached conversion result.

        Args:
            pine_code: Pine Script source code

        Returns:
            Cached result dict or None
        """
        cache_key = self._compute_cache_key(pine_code)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        # Load and validate
        try:
            with open(cache_file, 'r') as f:
                entry = json.load(f)

            # Check TTL
            if self._is_expired(entry):
                logger.debug(f"Cache entry expired: {cache_key}")
                cache_file.unlink()  # Delete expired
                return None

            logger.debug(f"Cache hit: {cache_key}")
            return entry

        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def set(self, pine_code: str, result: dict):
        """
        Cache conversion result.

        Args:
            pine_code: Pine Script source code
            result: Conversion result to cache
        """
        cache_key = self._compute_cache_key(pine_code)
        cache_file = self.cache_dir / f"{cache_key}.json"

        entry = {
            "pine_code_hash": cache_key,
            "python_code": result.get("python_code", ""),
            "strategy_used": result.get("strategy_used", "unknown"),
            "cost_usd": result.get("cost_usd", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
            "ttl_days": 30,
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(entry, f, indent=2)

            logger.debug(f"Cached result: {cache_key}")

        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self, older_than_days: int = 30):
        """
        Clear old cache entries.

        Args:
            older_than_days: Delete entries older than this
        """
        count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    entry = json.load(f)

                if self._is_expired(entry, older_than_days):
                    cache_file.unlink()
                    count += 1

            except Exception:
                pass

        logger.info(f"Cleared {count} expired cache entries")

    def _compute_cache_key(self, pine_code: str) -> str:
        """Compute SHA256 hash of Pine code"""
        return hashlib.sha256(pine_code.encode()).hexdigest()

    def _is_expired(self, entry: dict, ttl_days: int = None) -> bool:
        """Check if cache entry is expired"""
        ttl = ttl_days or entry.get("ttl_days", 30)

        timestamp_str = entry.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.utcnow() - timestamp
            return age > timedelta(days=ttl)
        except:
            return True  # Assume expired if can't parse
