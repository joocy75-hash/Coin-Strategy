"""
Strategy Architect Agent

Pine Script를 이해하고 백테스트 가능한 Python 전략으로 완전 변환하는 에이전트
- Gemini 3 Pro를 사용한 LLM 기반 변환
- 누락된 지표 자동 구현
- 진입/청산 조건 정확한 변환
- 리스크 관리 로직 추가
"""

from dataclasses import dataclass
from typing import Any
from claude_agent_sdk import AgentDefinition


@dataclass
class ConversionResult:
    """변환 결과 데이터 클래스"""
    success: bool
    python_code: str
    strategy_name: str
    indicators_used: list[str]
    entry_conditions: list[str]
    exit_conditions: list[str]
    has_stop_loss: bool
    has_take_profit: bool
    warnings: list[str]
    errors: list[str]


# Agent Definition for Claude Agent SDK
STRATEGY_ARCHITECT_DEFINITION = AgentDefinition(
    description="""Pine Script를 Python 백테스트 전략으로 완전 변환하는 전문 에이전트.

이 에이전트를 사용해야 하는 경우:
- Pine Script 코드를 Python으로 변환해야 할 때
- TradingView 전략을 backtesting.py 호환 코드로 만들어야 할 때
- 전략의 진입/청산 로직을 분석하고 변환해야 할 때
- 복잡한 지표 조합을 Python으로 구현해야 할 때""",

    prompt="""당신은 Pine Script를 Python으로 변환하는 최고의 전문가입니다.

## 역할
Pine Script 전략을 분석하고, backtesting.py 라이브러리와 호환되는
완전한 Python Strategy 클래스로 변환합니다.

## 변환 프로세스
1. **Pine Script 분석**
   - 사용된 지표 식별 (SMA, EMA, RSI, MACD 등)
   - 진입 조건 파악 (Long/Short)
   - 청산 조건 파악 (Stop Loss, Take Profit, Signal Exit)
   - 리스크 관리 로직 확인

2. **Python 변환 수행**
   - gemini_convert_pine 도구를 사용하여 Gemini 3 Pro로 변환
   - 모든 지표를 pandas-ta 라이브러리로 구현
   - backtesting.py Strategy 클래스 형식 준수

3. **변환 검증**
   - 문법 오류 확인
   - 필수 메서드 (init, next) 존재 확인
   - 지표 계산 로직 검증

## 출력 형식
```python
from backtesting import Strategy
from backtesting.lib import crossover
import pandas_ta as ta
import numpy as np

class StrategyName(Strategy):
    # 최적화 가능한 파라미터
    fast_period = 12
    slow_period = 26

    def init(self):
        # 지표 계산 (self.I() 사용)
        close = self.data.Close
        self.fast_ma = self.I(ta.ema, close, self.fast_period)
        self.slow_ma = self.I(ta.ema, close, self.slow_period)

    def next(self):
        # 진입 조건
        if crossover(self.fast_ma, self.slow_ma):
            self.buy(sl=self.data.Close[-1] * 0.98)  # 2% Stop Loss

        # 청산 조건
        elif crossover(self.slow_ma, self.fast_ma):
            self.position.close()
```

## 주의사항
- 모든 지표는 self.I() 래퍼로 감싸야 합니다
- Stop Loss/Take Profit은 buy()/sell() 메서드의 sl/tp 파라미터 사용
- Position sizing은 size 파라미터로 조절
- 변환이 불가능한 Pine Script 기능은 경고와 함께 대체 구현 제안

## 사용 가능한 도구
- mcp__trading-tools__gemini_analyze: Pine Script 분석
- mcp__trading-tools__gemini_convert_pine: Pine → Python 변환
- Read, Write, Glob: 파일 작업""",

    tools=[
        "mcp__trading-tools__gemini_analyze",
        "mcp__trading-tools__gemini_convert_pine",
        "Read",
        "Write",
        "Glob",
    ]
)


class StrategyArchitectAgent:
    """Strategy Architect 에이전트 클래스"""

    def __init__(self) -> None:
        self.name = "strategy-architect"
        self.definition = STRATEGY_ARCHITECT_DEFINITION

    def get_definition(self) -> AgentDefinition:
        """에이전트 정의 반환"""
        return self.definition

    @staticmethod
    def create_conversion_prompt(
        pine_code: str,
        strategy_name: str,
        additional_requirements: str = ""
    ) -> str:
        """변환 요청 프롬프트 생성"""
        return f"""다음 Pine Script를 Python 전략으로 변환해주세요.

## Pine Script
```pinescript
{pine_code}
```

## 전략 이름
{strategy_name}

## 추가 요구사항
{additional_requirements if additional_requirements else "없음"}

## 작업 순서
1. gemini_analyze 도구로 Pine Script를 먼저 분석
2. gemini_convert_pine 도구로 Python 코드 생성
3. 생성된 코드 검증 및 필요시 수정
4. 최종 Python 코드와 분석 결과 반환"""

    @staticmethod
    def validate_python_code(code: str) -> tuple[bool, list[str]]:
        """생성된 Python 코드 기본 검증"""
        errors = []

        # 필수 import 확인
        if "from backtesting import Strategy" not in code:
            errors.append("Missing: from backtesting import Strategy")

        # Strategy 클래스 확인
        if "class " not in code or "(Strategy)" not in code:
            errors.append("Missing: Strategy class definition")

        # init 메서드 확인
        if "def init(self)" not in code:
            errors.append("Missing: init() method")

        # next 메서드 확인
        if "def next(self)" not in code:
            errors.append("Missing: next() method")

        # self.I() 사용 확인 (지표 래핑)
        if "self.I(" not in code:
            errors.append("Warning: No indicators wrapped with self.I()")

        return len(errors) == 0, errors
