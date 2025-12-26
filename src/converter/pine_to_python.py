# src/converter/pine_to_python.py

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """변환 결과"""
    success: bool
    python_code: str
    indicators_used: List[str]
    warnings: List[str]
    errors: List[str]


class PineScriptConverter:
    """
    Pine Script → Python 변환기 (규칙 기반)

    LLM 없이 기본적인 변환 수행
    복잡한 변환은 LLM에 위임
    """

    # Pine → Python 함수 매핑
    FUNCTION_MAPPINGS = {
        # 이동평균
        r'ta\.sma\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'self._sma(\1, \2)',
        r'ta\.ema\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'self._ema(\1, \2)',
        r'ta\.wma\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'self._wma(\1, \2)',
        r'ta\.rma\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'self._rma(\1, \2)',

        # 오실레이터
        r'ta\.rsi\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'self._rsi(\1, \2)',
        r'ta\.macd\s*\(': r'self._macd(',
        r'ta\.stoch\s*\(': r'self._stoch(',

        # 변동성
        r'ta\.atr\s*\(\s*(\d+)\s*\)': r'self._atr(\1)',
        r'ta\.bb\s*\(': r'self._bollinger(',

        # 크로스오버
        r'ta\.crossover\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)': r'(\1[-1] <= \2[-1] and \1[-0] > \2[-0])',
        r'ta\.crossunder\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)': r'(\1[-1] >= \2[-1] and \1[-0] < \2[-0])',

        # 최고/최저
        r'ta\.highest\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'max(\1[-\2:])',
        r'ta\.lowest\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'min(\1[-\2:])',

        # 변화량
        r'ta\.change\s*\(\s*(\w+)\s*\)': r'(\1[-0] - \1[-1])',
        r'ta\.change\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)': r'(\1[-0] - \1[-\2])',

        # 기타
        r'math\.abs\s*\(': r'abs(',
        r'math\.max\s*\(': r'max(',
        r'math\.min\s*\(': r'min(',
        r'math\.round\s*\(': r'round(',
        r'nz\s*\(\s*(\w+)\s*\)': r'(\1 if \1 is not None else 0)',
    }

    # Pine 데이터 → Python 매핑
    DATA_MAPPINGS = {
        r'\bclose\b': 'closes[-1]',
        r'\bopen\b': 'opens[-1]',
        r'\bhigh\b': 'highs[-1]',
        r'\blow\b': 'lows[-1]',
        r'\bvolume\b': 'volumes[-1]',
        r'\bclose\[(\d+)\]': r'closes[-\1-1]',
        r'\bopen\[(\d+)\]': r'opens[-\1-1]',
        r'\bhigh\[(\d+)\]': r'highs[-\1-1]',
        r'\blow\[(\d+)\]': r'lows[-\1-1]',
    }

    # 연산자 매핑
    OPERATOR_MAPPINGS = {
        r'\band\b': 'and',
        r'\bor\b': 'or',
        r'\bnot\b': 'not',
        r'\btrue\b': 'True',
        r'\bfalse\b': 'False',
        r':=': '=',
    }

    def __init__(self):
        self.indicators_used = []
        self.warnings = []
        self.errors = []

    def convert(self, pine_code: str) -> ConversionResult:
        """
        Pine Script를 Python으로 변환

        Args:
            pine_code: Pine Script 코드

        Returns:
            ConversionResult 객체
        """
        self.indicators_used = []
        self.warnings = []
        self.errors = []

        if not pine_code:
            return ConversionResult(
                success=False,
                python_code="",
                indicators_used=[],
                warnings=[],
                errors=["Empty code provided"]
            )

        try:
            # 1. 전처리
            code = self._preprocess(pine_code)

            # 2. 입력 파라미터 추출
            inputs = self._extract_inputs(code)

            # 3. 전략 설정 추출
            strategy_settings = self._extract_strategy_settings(code)

            # 4. 진입/청산 조건 추출
            entry_exit = self._extract_entry_exit(code)

            # 5. Python 코드 생성
            python_code = self._generate_python(
                inputs=inputs,
                strategy_settings=strategy_settings,
                entry_exit=entry_exit,
                original_code=code
            )

            return ConversionResult(
                success=True,
                python_code=python_code,
                indicators_used=list(set(self.indicators_used)),
                warnings=self.warnings,
                errors=self.errors
            )

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return ConversionResult(
                success=False,
                python_code="",
                indicators_used=[],
                warnings=self.warnings,
                errors=[str(e)]
            )

    def _preprocess(self, code: str) -> str:
        """코드 전처리"""
        # 주석 제거
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)

        # 빈 줄 정리
        lines = [line for line in code.split('\n') if line.strip()]
        return '\n'.join(lines)

    def _extract_inputs(self, code: str) -> List[Dict]:
        """입력 파라미터 추출"""
        inputs = []

        patterns = [
            # input.int("label", defval, ...)
            r'(\w+)\s*=\s*input\.int\s*\(\s*(\d+)',
            r'(\w+)\s*=\s*input\.float\s*\(\s*([0-9.]+)',
            r'(\w+)\s*=\s*input\.bool\s*\(\s*(true|false)',
            r'(\w+)\s*=\s*input\s*\(\s*([^,)]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    name = match[0]
                    default = match[1]

                    # 타입 추론
                    try:
                        if '.' in default:
                            default_val = float(default)
                            param_type = "float"
                        elif default.lower() in ['true', 'false']:
                            default_val = default.lower() == 'true'
                            param_type = "bool"
                        else:
                            default_val = int(default)
                            param_type = "int"
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Could not parse parameter default value '{default}': {e}")
                        default_val = default
                        param_type = "str"

                    inputs.append({
                        "name": name,
                        "type": param_type,
                        "default": default_val
                    })

        return inputs

    def _extract_strategy_settings(self, code: str) -> Dict:
        """전략 설정 추출"""
        settings = {
            "title": "Converted Strategy",
            "overlay": True,
            "pyramiding": 0,
            "default_qty_type": "percent_of_equity",
            "default_qty_value": 10,
        }

        # strategy() 함수 파싱
        strategy_match = re.search(
            r'strategy\s*\(\s*["\']([^"\']+)["\']',
            code
        )
        if strategy_match:
            settings["title"] = strategy_match.group(1)

        # pyramiding
        pyramid_match = re.search(r'pyramiding\s*=\s*(\d+)', code)
        if pyramid_match:
            settings["pyramiding"] = int(pyramid_match.group(1))

        return settings

    def _extract_entry_exit(self, code: str) -> Dict:
        """진입/청산 조건 추출"""
        conditions = {
            "long_entry": [],
            "long_exit": [],
            "short_entry": [],
            "short_exit": [],
            "stop_loss": None,
            "take_profit": None,
        }

        # strategy.entry 추출
        entry_patterns = [
            (r'strategy\.entry\s*\(\s*["\']long["\'].*?when\s*=\s*([^,)]+)', "long_entry"),
            (r'strategy\.entry\s*\(\s*["\']short["\'].*?when\s*=\s*([^,)]+)', "short_entry"),
            (r'if\s+([^:]+)\s*\n\s*strategy\.entry\s*\(\s*["\']long["\']', "long_entry"),
            (r'if\s+([^:]+)\s*\n\s*strategy\.entry\s*\(\s*["\']short["\']', "short_entry"),
        ]

        for pattern, condition_type in entry_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                conditions[condition_type].append(match.strip())

        # strategy.exit 추출
        exit_match = re.search(r'strategy\.exit\s*\([^)]*stop\s*=\s*([^,)]+)', code)
        if exit_match:
            conditions["stop_loss"] = exit_match.group(1).strip()

        profit_match = re.search(r'strategy\.exit\s*\([^)]*profit\s*=\s*([^,)]+)', code)
        if profit_match:
            conditions["take_profit"] = profit_match.group(1).strip()

        return conditions

    def _generate_python(
        self,
        inputs: List[Dict],
        strategy_settings: Dict,
        entry_exit: Dict,
        original_code: str
    ) -> str:
        """Python 코드 생성"""

        # 클래스 이름 생성
        title = strategy_settings.get("title", "Strategy")
        class_name = ''.join(word.capitalize() for word in re.sub(r'[^a-zA-Z0-9]', ' ', title).split())
        if not class_name:
            class_name = "ConvertedStrategy"

        # 파라미터 문자열
        params_init = ""
        for inp in inputs:
            params_init += f'        self.{inp["name"]} = params.get("{inp["name"]}", {repr(inp["default"])})\n'

        if not params_init:
            params_init = "        # No parameters defined\n        pass"

        # 진입 조건 변환
        long_condition = self._convert_condition(entry_exit.get("long_entry", []))
        short_condition = self._convert_condition(entry_exit.get("short_entry", []))

        # 인디케이터 목록
        indicators = self._detect_indicators(original_code)
        self.indicators_used = indicators

        template = f'''"""
{strategy_settings.get("title", "Converted Strategy")}

Auto-converted from Pine Script
Indicators used: {", ".join(indicators) if indicators else "None detected"}
"""

import numpy as np
from typing import List, Dict, Optional


class {class_name}:
    """Converted from Pine Script"""

    def __init__(self, params: Dict = None, user_id: int = None):
        params = params or {{}}
        self.user_id = user_id
        self.strategy_code = "{class_name.lower()}"

        # Parameters
{params_init}

        # Risk management defaults
        self.stop_loss_pct = params.get("stop_loss_percent", 2.0)
        self.take_profit_pct = params.get("take_profit_percent", 4.0)

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """Generate trading signal"""

        # Extract price data
        if len(candles) < 50:
            return self._hold("Insufficient data")

        closes = np.array([c["close"] for c in candles])
        opens = np.array([c["open"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        volumes = np.array([c.get("volume", 0) for c in candles])

        # Check exit conditions first
        if current_position:
            exit_signal = self._check_exit(current_position, current_price)
            if exit_signal:
                return exit_signal

        # Entry conditions
        if not current_position:
            # Long entry
            if self._check_long_entry(closes, opens, highs, lows, volumes):
                return {{
                    "action": "buy",
                    "confidence": 0.7,
                    "reason": "Long entry signal",
                    "stop_loss": self.stop_loss_pct,
                    "take_profit": self.take_profit_pct,
                    "strategy_type": self.strategy_code
                }}

            # Short entry
            if self._check_short_entry(closes, opens, highs, lows, volumes):
                return {{
                    "action": "sell",
                    "confidence": 0.7,
                    "reason": "Short entry signal",
                    "stop_loss": self.stop_loss_pct,
                    "take_profit": self.take_profit_pct,
                    "strategy_type": self.strategy_code
                }}

        return self._hold("No signal")

    def _check_long_entry(self, closes, opens, highs, lows, volumes) -> bool:
        """Check long entry conditions"""
        try:
            # Converted conditions (customize as needed)
            {self._generate_condition_code(long_condition, "long")}
        except Exception:
            return False

    def _check_short_entry(self, closes, opens, highs, lows, volumes) -> bool:
        """Check short entry conditions"""
        try:
            # Converted conditions (customize as needed)
            {self._generate_condition_code(short_condition, "short")}
        except Exception:
            return False

    def _check_exit(self, position: Dict, current_price: float) -> Optional[Dict]:
        """Check exit conditions"""
        pnl_pct = position.get("pnl_percent", 0)

        if pnl_pct >= self.take_profit_pct:
            return {{
                "action": "close",
                "confidence": 0.9,
                "reason": f"Take Profit: {{pnl_pct:.2f}}%",
                "strategy_type": self.strategy_code
            }}

        if pnl_pct <= -self.stop_loss_pct:
            return {{
                "action": "close",
                "confidence": 0.95,
                "reason": f"Stop Loss: {{pnl_pct:.2f}}%",
                "strategy_type": self.strategy_code
            }}

        return None

    def _hold(self, reason: str) -> Dict:
        """Return hold signal"""
        return {{
            "action": "hold",
            "confidence": 0.5,
            "reason": reason,
            "strategy_type": self.strategy_code
        }}

    # === Indicator Methods ===

    def _sma(self, data: np.ndarray, period: int) -> float:
        """Simple Moving Average"""
        if len(data) < period:
            return data[-1]
        return np.mean(data[-period:])

    def _ema(self, data: np.ndarray, period: int) -> float:
        """Exponential Moving Average"""
        if len(data) < period:
            return data[-1]
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema

    def _rsi(self, data: np.ndarray, period: int = 14) -> float:
        """Relative Strength Index"""
        if len(data) < period + 1:
            return 50.0
        deltas = np.diff(data[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Average True Range"""
        if len(closes) < period + 1:
            return highs[-1] - lows[-1]
        tr = np.maximum(
            highs[-period:] - lows[-period:],
            np.maximum(
                np.abs(highs[-period:] - closes[-period-1:-1]),
                np.abs(lows[-period:] - closes[-period-1:-1])
            )
        )
        return np.mean(tr)


# Function interface for compatibility
def generate_signal(
    current_price: float,
    candles: List[Dict],
    params: Dict = None,
    current_position: Optional[Dict] = None
) -> Dict:
    """Function wrapper"""
    strategy = {class_name}(params)
    return strategy.generate_signal(current_price, candles, current_position)
'''

        return template

    def _convert_condition(self, conditions: List[str]) -> str:
        """조건 변환"""
        if not conditions:
            return "True  # TODO: Add conditions"

        converted = []
        for cond in conditions:
            # 함수 매핑 적용
            for pattern, replacement in self.FUNCTION_MAPPINGS.items():
                cond = re.sub(pattern, replacement, cond, flags=re.IGNORECASE)

            # 데이터 매핑 적용
            for pattern, replacement in self.DATA_MAPPINGS.items():
                cond = re.sub(pattern, replacement, cond, flags=re.IGNORECASE)

            # 연산자 매핑 적용
            for pattern, replacement in self.OPERATOR_MAPPINGS.items():
                cond = re.sub(pattern, replacement, cond, flags=re.IGNORECASE)

            converted.append(cond)

        return " and ".join(converted)

    def _generate_condition_code(self, condition: str, side: str) -> str:
        """조건 코드 생성"""
        if condition == "True  # TODO: Add conditions":
            if side == "long":
                return """# Default: EMA crossover
            ema_fast = self._ema(closes, 9)
            ema_slow = self._ema(closes, 21)
            rsi = self._rsi(closes, 14)
            return ema_fast > ema_slow and rsi < 70"""
            else:
                return """# Default: EMA crossunder
            ema_fast = self._ema(closes, 9)
            ema_slow = self._ema(closes, 21)
            rsi = self._rsi(closes, 14)
            return ema_fast < ema_slow and rsi > 30"""

        return f"return {condition}"

    def _detect_indicators(self, code: str) -> List[str]:
        """사용된 인디케이터 탐지"""
        indicators = []

        indicator_patterns = {
            "SMA": r'ta\.sma|sma\(',
            "EMA": r'ta\.ema|ema\(',
            "RSI": r'ta\.rsi|rsi\(',
            "MACD": r'ta\.macd|macd\(',
            "ATR": r'ta\.atr|atr\(',
            "Bollinger Bands": r'ta\.bb|bollinger',
            "Stochastic": r'ta\.stoch|stoch\(',
            "ADX": r'ta\.adx|adx\(',
            "CCI": r'ta\.cci|cci\(',
            "VWAP": r'ta\.vwap|vwap',
            "Supertrend": r'supertrend',
            "Ichimoku": r'ichimoku',
            "Pivot Points": r'pivot',
        }

        for name, pattern in indicator_patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                indicators.append(name)

        return indicators
