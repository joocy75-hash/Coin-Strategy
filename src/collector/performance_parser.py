# src/collector/performance_parser.py

import re
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """백테스트 성과 지표"""
    # 수익 관련
    net_profit: Optional[float] = None
    net_profit_percent: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_loss: Optional[float] = None

    # 거래 관련
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    win_rate: Optional[float] = None

    # 리스크 관련
    profit_factor: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None

    # 평균 관련
    avg_trade: Optional[float] = None
    avg_winning_trade: Optional[float] = None
    avg_losing_trade: Optional[float] = None
    largest_winning_trade: Optional[float] = None
    largest_losing_trade: Optional[float] = None

    # 기타
    avg_bars_in_trade: Optional[float] = None
    percent_profitable: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @property
    def is_valid(self) -> bool:
        """유효한 성과 데이터인지 확인"""
        return self.total_trades is not None and self.total_trades > 0


class PerformanceParser:
    """
    TradingView Strategy Tester 성과 파싱

    다양한 형식의 성과 데이터를 통일된 형식으로 변환
    """

    # 지표명 매핑 (다양한 표현 → 표준 키)
    METRIC_MAPPINGS = {
        # Net Profit
        "net_profit": ["net_profit", "netprofit", "net profit", "total net profit"],
        "net_profit_percent": ["net_profit_percent", "net profit %", "profit %"],

        # Gross Profit/Loss
        "gross_profit": ["gross_profit", "grossprofit", "gross profit"],
        "gross_loss": ["gross_loss", "grossloss", "gross loss"],

        # Trades
        "total_trades": ["total_trades", "totaltrades", "total trades", "total closed trades", "trades"],
        "winning_trades": ["winning_trades", "winningtrades", "number of winning trades", "winning trades"],
        "losing_trades": ["losing_trades", "losingtrades", "number of losing trades", "losing trades"],

        # Win Rate
        "win_rate": ["win_rate", "winrate", "percent profitable", "win %", "winning %"],

        # Risk Metrics
        "profit_factor": ["profit_factor", "profitfactor", "profit factor"],
        "max_drawdown": ["max_drawdown", "maxdrawdown", "max drawdown", "maximum drawdown"],
        "max_drawdown_percent": ["max_drawdown_percent", "max drawdown %", "max dd %"],
        "sharpe_ratio": ["sharpe_ratio", "sharperatio", "sharpe ratio", "sharpe"],
        "sortino_ratio": ["sortino_ratio", "sortinoratio", "sortino ratio", "sortino"],

        # Average Metrics
        "avg_trade": ["avg_trade", "avgtrade", "avg trade", "average trade"],
        "avg_winning_trade": ["avg_winning_trade", "avgwinningtrade", "avg winning trade"],
        "avg_losing_trade": ["avg_losing_trade", "avglosingtrade", "avg losing trade"],
        "largest_winning_trade": ["largest_winning_trade", "largestwinningtrade", "largest winning trade"],
        "largest_losing_trade": ["largest_losing_trade", "largestlosingtrade", "largest losing trade"],

        # Other
        "avg_bars_in_trade": ["avg_bars_in_trade", "avgbarsintrade", "avg bars in trades", "avg # bars in trades"],
    }

    @classmethod
    def parse(cls, raw_data: Dict[str, Any]) -> PerformanceMetrics:
        """
        원시 성과 데이터를 PerformanceMetrics로 변환

        Args:
            raw_data: 원시 성과 데이터 (다양한 형식)

        Returns:
            PerformanceMetrics 객체
        """
        metrics = PerformanceMetrics()

        if not raw_data:
            return metrics

        # 원시 데이터 정규화
        normalized = cls._normalize_keys(raw_data)

        # 각 지표 파싱
        for metric_name, aliases in cls.METRIC_MAPPINGS.items():
            for alias in aliases:
                if alias in normalized:
                    value = cls._parse_value(normalized[alias], metric_name)
                    if value is not None:
                        setattr(metrics, metric_name, value)
                    break

        # 계산 가능한 지표 보완
        cls._fill_derived_metrics(metrics)

        return metrics

    @classmethod
    def _normalize_keys(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """키 정규화 (소문자, 특수문자 제거)"""
        normalized = {}

        for key, value in data.items():
            # 키 정규화
            norm_key = key.lower().strip()
            norm_key = re.sub(r'[^a-z0-9]', '_', norm_key)
            norm_key = re.sub(r'_+', '_', norm_key).strip('_')

            # 원본 키도 저장 (alias 매칭용)
            normalized[norm_key] = value
            normalized[key.lower().strip()] = value

        return normalized

    @classmethod
    def _parse_value(cls, value: Any, metric_name: str) -> Optional[float]:
        """
        값 파싱 (문자열 → 숫자)

        처리 형식:
        - "123.45%"
        - "$1,234.56"
        - "-1,234.56 USD"
        - "1.5"
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()

        if not value:
            return None

        try:
            # 특수 케이스: 퍼센트
            is_percent = '%' in value

            # 정리: 숫자, 소수점, 마이너스만 남기기
            cleaned = re.sub(r'[^\d.\-]', '', value.replace(',', ''))

            if not cleaned or cleaned in ['-', '.', '-.']:
                return None

            parsed = float(cleaned)

            # 정수 지표 (거래 수 등)
            if metric_name in ['total_trades', 'winning_trades', 'losing_trades']:
                return int(parsed)

            return parsed

        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse value '{value}' for {metric_name}: {e}")
            return None

    @classmethod
    def _fill_derived_metrics(cls, metrics: PerformanceMetrics):
        """파생 지표 계산"""

        # Win Rate 계산
        if metrics.win_rate is None:
            if metrics.total_trades and metrics.winning_trades:
                metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100

        # Losing trades 계산
        if metrics.losing_trades is None:
            if metrics.total_trades and metrics.winning_trades:
                metrics.losing_trades = metrics.total_trades - metrics.winning_trades

        # Profit Factor 검증
        if metrics.profit_factor is not None:
            # 비현실적인 값 필터링
            if metrics.profit_factor > 100 or metrics.profit_factor < 0:
                logger.warning(f"Unrealistic profit factor: {metrics.profit_factor}")
                metrics.profit_factor = None

    @classmethod
    def parse_from_text(cls, text: str) -> PerformanceMetrics:
        """
        텍스트에서 성과 데이터 추출

        Args:
            text: Strategy Tester 텍스트

        Returns:
            PerformanceMetrics 객체
        """
        raw_data = {}

        # "Label: Value" 패턴 매칭
        patterns = [
            r'([A-Za-z\s]+):\s*([-\d.,]+%?)',
            r'([A-Za-z\s]+)\s+([-\d.,]+%?)\s*$',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                if len(match) == 2:
                    key, value = match
                    raw_data[key.strip()] = value.strip()

        return cls.parse(raw_data)

    @classmethod
    def validate_metrics(cls, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """
        성과 지표 검증

        Returns:
            검증 결과 딕셔너리
        """
        issues = []
        warnings = []

        if metrics.total_trades is not None:
            if metrics.total_trades < 30:
                warnings.append(f"Low trade count: {metrics.total_trades} (minimum 30 recommended)")
            if metrics.total_trades < 10:
                issues.append(f"Very low trade count: {metrics.total_trades}")

        if metrics.profit_factor is not None:
            if metrics.profit_factor > 5:
                warnings.append(f"Very high profit factor: {metrics.profit_factor} (possible overfitting)")
            if metrics.profit_factor < 0:
                issues.append(f"Invalid profit factor: {metrics.profit_factor}")

        if metrics.win_rate is not None:
            if metrics.win_rate > 90:
                warnings.append(f"Very high win rate: {metrics.win_rate}% (possible overfitting)")
            if metrics.win_rate < 10:
                warnings.append(f"Very low win rate: {metrics.win_rate}%")

        if metrics.max_drawdown_percent is not None:
            if abs(metrics.max_drawdown_percent) > 50:
                issues.append(f"High drawdown: {metrics.max_drawdown_percent}%")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "metrics": metrics.to_dict(),
        }
