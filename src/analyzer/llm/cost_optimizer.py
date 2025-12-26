# src/analyzer/llm/cost_optimizer.py

import re
import hashlib
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TokenEstimate:
    """토큰 추정치"""
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class CostOptimizer:
    """
    LLM API 비용 최적화

    기능:
    1. 코드 압축 (불필요한 부분 제거)
    2. 토큰 추정
    3. 캐싱
    4. 배치 처리
    """

    # GPT-4o 가격 (2024년 기준, USD per 1M tokens)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    }

    def __init__(self, cache_ttl_hours: int = 24):
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(hours=cache_ttl_hours)

    def compress_pine_code(self, code: str, max_chars: int = 6000) -> str:
        """
        Pine 코드 압축

        제거 대상:
        - 주석
        - 빈 줄
        - 불필요한 공백
        - plot 관련 코드 (시각화만)
        """
        if not code:
            return ""

        # 1. 블록 주석 제거
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)

        # 2. 라인 주석 제거 (코드 뒤 주석)
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)

        # 3. 빈 줄 제거
        lines = [line for line in code.split('\n') if line.strip()]

        # 4. plot 관련 코드 제거 (분석에 불필요)
        non_plot_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # plot, plotshape, plotchar, bgcolor, barcolor 등 시각화 코드 제외
            if not any(line_lower.startswith(p) for p in [
                'plot(', 'plot ', 'plotshape', 'plotchar', 'plotarrow',
                'bgcolor', 'barcolor', 'hline', 'fill(',
                'label.new', 'line.new', 'box.new', 'table.'
            ]):
                non_plot_lines.append(line)

        # 5. 연속 공백 제거
        code = '\n'.join(non_plot_lines)
        code = re.sub(r'[ \t]+', ' ', code)

        # 6. 길이 제한
        if len(code) > max_chars:
            # 중요 부분 우선 (strategy, input, entry/exit)
            important_lines = []
            other_lines = []

            for line in code.split('\n'):
                if any(kw in line.lower() for kw in [
                    'strategy(', 'input', 'strategy.entry', 'strategy.exit',
                    'strategy.close', 'long', 'short', 'stop', 'profit'
                ]):
                    important_lines.append(line)
                else:
                    other_lines.append(line)

            # 중요 라인 먼저, 나머지는 공간 허용하는 만큼
            code = '\n'.join(important_lines)
            remaining = max_chars - len(code) - 100

            if remaining > 0:
                other_text = '\n'.join(other_lines)[:remaining]
                code = code + '\n' + other_text

        return code.strip()

    def estimate_tokens(self, text: str) -> int:
        """
        토큰 수 추정 (대략적)

        영어: ~4 chars/token
        한국어/코드: ~2-3 chars/token
        """
        if not text:
            return 0

        # 코드와 일반 텍스트 비율 추정
        code_ratio = len(re.findall(r'[{}\[\]();=]', text)) / max(len(text), 1)

        if code_ratio > 0.05:  # 코드가 많으면
            return len(text) // 3
        else:
            return len(text) // 4

    def estimate_cost(
        self,
        input_text: str,
        output_tokens: int = 1500,
        model: str = "gpt-4o"
    ) -> TokenEstimate:
        """비용 추정"""
        input_tokens = self.estimate_tokens(input_text)

        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])

        cost = (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )

        return TokenEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(cost, 6)
        )

    def get_cache_key(self, code: str, analysis_type: str = "full") -> str:
        """캐시 키 생성"""
        # 코드 해시 + 분석 유형
        code_hash = hashlib.md5(code.encode()).hexdigest()[:16]
        return f"{analysis_type}:{code_hash}"

    def get_cached(self, cache_key: str) -> Optional[str]:
        """캐시된 결과 조회"""
        if cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self._cache_ttl:
                logger.debug(f"Cache hit: {cache_key}")
                return result
            else:
                # 만료된 캐시 삭제
                del self._cache[cache_key]
        return None

    def set_cache(self, cache_key: str, result: str):
        """결과 캐시"""
        self._cache[cache_key] = (result, datetime.now())

        # 캐시 크기 제한 (100개)
        if len(self._cache) > 100:
            # 가장 오래된 항목 제거
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def should_use_mini_model(self, code: str, analysis_type: str = "full") -> bool:
        """
        저비용 모델 사용 여부 결정

        짧은 코드나 간단한 분석은 gpt-4o-mini 사용
        """
        if analysis_type in ["summary", "quick"]:
            return True

        if len(code) < 1000:
            return True

        # 단순 전략 패턴 (EMA 크로스 등)
        simple_patterns = [
            r'ta\.crossover.*ta\.crossunder',
            r'ema.*sma',
            r'rsi\s*[<>]',
        ]

        for pattern in simple_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True

        return False

    def batch_estimate(self, codes: list, model: str = "gpt-4o") -> Dict:
        """배치 비용 추정"""
        total_input = 0
        total_output = 0

        for code in codes:
            compressed = self.compress_pine_code(code)
            estimate = self.estimate_cost(compressed, model=model)
            total_input += estimate.input_tokens
            total_output += estimate.output_tokens

        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
        total_cost = (
            (total_input / 1_000_000) * pricing["input"] +
            (total_output / 1_000_000) * pricing["output"]
        )

        return {
            "count": len(codes),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "estimated_cost_usd": round(total_cost, 4),
            "model": model,
        }

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        logger.info("Cache cleared")
