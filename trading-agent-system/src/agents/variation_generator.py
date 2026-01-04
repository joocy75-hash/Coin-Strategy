"""
Variation Generator Agent

기본 전략에서 다양한 변형 전략을 자동 생성하는 에이전트
- 기본 전략 + 보조 지표 조합 (ADX, VWAP, MFI 등)
- 파라미터 변형 (기간, 임계값 등)
- 필터 조건 추가 (시장 상황, 변동성 등)
- 최소 4개 이상의 변형 전략 자동 생성
"""

from dataclasses import dataclass, field
from typing import Any
from claude_agent_sdk import AgentDefinition


@dataclass
class VariationConfig:
    """변형 전략 설정"""
    base_strategy: str
    add_trend_filter: bool = True
    add_volatility_filter: bool = True
    add_volume_filter: bool = False
    param_variations: int = 3
    indicators_to_add: list[str] = field(default_factory=list)


@dataclass
class GeneratedVariation:
    """생성된 변형 전략"""
    name: str
    python_code: str
    description: str
    added_indicators: list[str]
    modified_params: dict[str, Any]


# 지표 라이브러리 정의
INDICATOR_LIBRARY = {
    "trend": {
        "ADX": {
            "code": "self.adx = self.I(ta.adx, self.data.High, self.data.Low, self.data.Close, 14)",
            "filter": "self.adx[-1] > 25",  # 트렌드 존재 시에만 거래
            "description": "Average Directional Index - 트렌드 강도 측정"
        },
        "Supertrend": {
            "code": "st = ta.supertrend(self.data.High, self.data.Low, self.data.Close, 10, 3)\nself.supertrend = self.I(lambda: st['SUPERT_10_3.0'])",
            "filter": "self.data.Close[-1] > self.supertrend[-1]",
            "description": "Supertrend - 트렌드 방향 및 지지/저항"
        },
        "Ichimoku": {
            "code": "ich = ta.ichimoku(self.data.High, self.data.Low, self.data.Close)\nself.tenkan = self.I(lambda: ich[0]['ITS_9'])\nself.kijun = self.I(lambda: ich[0]['IKS_26'])",
            "filter": "self.data.Close[-1] > self.tenkan[-1] and self.tenkan[-1] > self.kijun[-1]",
            "description": "Ichimoku Cloud - 트렌드, 모멘텀, 지지/저항"
        },
    },
    "momentum": {
        "RSI": {
            "code": "self.rsi = self.I(ta.rsi, self.data.Close, 14)",
            "filter": "30 < self.rsi[-1] < 70",  # 과매수/과매도 필터
            "description": "Relative Strength Index - 모멘텀 측정"
        },
        "MACD": {
            "code": "macd = ta.macd(self.data.Close, 12, 26, 9)\nself.macd_line = self.I(lambda: macd['MACD_12_26_9'])\nself.macd_signal = self.I(lambda: macd['MACDs_12_26_9'])",
            "filter": "self.macd_line[-1] > self.macd_signal[-1]",
            "description": "MACD - 트렌드 추종 모멘텀"
        },
        "Stochastic": {
            "code": "stoch = ta.stoch(self.data.High, self.data.Low, self.data.Close, 14, 3, 3)\nself.stoch_k = self.I(lambda: stoch['STOCHk_14_3_3'])\nself.stoch_d = self.I(lambda: stoch['STOCHd_14_3_3'])",
            "filter": "20 < self.stoch_k[-1] < 80",
            "description": "Stochastic Oscillator - 과매수/과매도"
        },
        "MFI": {
            "code": "self.mfi = self.I(ta.mfi, self.data.High, self.data.Low, self.data.Close, self.data.Volume, 14)",
            "filter": "self.mfi[-1] < 80",  # 과매수 필터
            "description": "Money Flow Index - 볼륨 가중 RSI"
        },
    },
    "volatility": {
        "ATR": {
            "code": "self.atr = self.I(ta.atr, self.data.High, self.data.Low, self.data.Close, 14)",
            "filter": "self.atr[-1] > self.atr[-1] * 0.5",  # 최소 변동성
            "description": "Average True Range - 변동성 측정"
        },
        "BB": {
            "code": "bb = ta.bbands(self.data.Close, 20, 2)\nself.bb_upper = self.I(lambda: bb['BBU_20_2.0'])\nself.bb_lower = self.I(lambda: bb['BBL_20_2.0'])\nself.bb_mid = self.I(lambda: bb['BBM_20_2.0'])",
            "filter": "self.bb_lower[-1] < self.data.Close[-1] < self.bb_upper[-1]",
            "description": "Bollinger Bands - 변동성 밴드"
        },
        "Keltner": {
            "code": "kc = ta.kc(self.data.High, self.data.Low, self.data.Close, 20, 2)\nself.kc_upper = self.I(lambda: kc['KCUe_20_2'])\nself.kc_lower = self.I(lambda: kc['KCLe_20_2'])",
            "filter": "self.kc_lower[-1] < self.data.Close[-1] < self.kc_upper[-1]",
            "description": "Keltner Channel - ATR 기반 밴드"
        },
    },
    "volume": {
        "VWAP": {
            "code": "self.vwap = self.I(ta.vwap, self.data.High, self.data.Low, self.data.Close, self.data.Volume)",
            "filter": "self.data.Close[-1] > self.vwap[-1]",  # 가격이 VWAP 위
            "description": "Volume Weighted Average Price"
        },
        "OBV": {
            "code": "self.obv = self.I(ta.obv, self.data.Close, self.data.Volume)",
            "filter": "self.obv[-1] > self.obv[-2]",  # OBV 상승
            "description": "On Balance Volume - 매집/분산"
        },
        "CMF": {
            "code": "self.cmf = self.I(ta.cmf, self.data.High, self.data.Low, self.data.Close, self.data.Volume, 20)",
            "filter": "self.cmf[-1] > 0",  # 매수 압력
            "description": "Chaikin Money Flow"
        },
    },
}


# Agent Definition
VARIATION_GENERATOR_DEFINITION = AgentDefinition(
    description="""기본 전략에서 다양한 변형 전략을 자동 생성하는 에이전트.

이 에이전트를 사용해야 하는 경우:
- 기본 전략에 보조 지표를 추가하고 싶을 때
- 파라미터 조합을 다양하게 테스트하고 싶을 때
- 필터 조건을 추가하여 전략을 개선하고 싶을 때
- Moon Dev 스타일의 지표 조합 전략을 만들고 싶을 때""",

    prompt="""당신은 트레이딩 전략 변형 생성 전문가입니다.

## 역할
기본 전략을 받아서 다양한 변형 전략을 생성합니다.
Moon Dev의 접근법처럼 지표 조합으로 edge를 강화합니다.

## 변형 전략 생성 방식

### 1. 트렌드 필터 추가
기본 전략에 ADX, Supertrend, Ichimoku 등을 추가하여
트렌드가 있을 때만 거래하도록 필터링

### 2. 모멘텀 필터 추가
RSI, MACD, Stochastic 등으로 모멘텀 확인
과매수/과매도 구간 필터링

### 3. 변동성 필터 추가
ATR, Bollinger Bands 등으로 변동성 확인
적정 변동성 구간에서만 거래

### 4. 볼륨 필터 추가
VWAP, OBV 등으로 볼륨 확인
볼륨이 뒷받침될 때만 거래

### 5. 파라미터 변형
기존 파라미터를 체계적으로 변형
예: fast_period: [8, 12, 20], slow_period: [21, 26, 50]

## 출력 형식
각 변형 전략은 다음을 포함:
1. 전략 이름 (예: BaseStrategy_ADX_RSI)
2. 완전한 Python 코드
3. 추가된 지표 목록
4. 변형 설명

## 변형 생성 규칙
- 최소 4개 이상의 변형 생성
- 각 변형은 논리적으로 의미 있어야 함
- 과도한 복잡성 피하기 (최대 3개 필터)
- 파라미터는 합리적인 범위 내에서 변형

## 사용 가능한 지표
- trend: ADX, Supertrend, Ichimoku
- momentum: RSI, MACD, Stochastic, MFI
- volatility: ATR, BB (Bollinger), Keltner
- volume: VWAP, OBV, CMF

## 사용 가능한 도구
- mcp__trading-tools__gemini_analyze: 전략 분석
- Read, Write, Glob: 파일 작업""",

    tools=[
        "mcp__trading-tools__gemini_analyze",
        "Read",
        "Write",
        "Glob",
    ]
)


class VariationGeneratorAgent:
    """Variation Generator 에이전트 클래스"""

    def __init__(self) -> None:
        self.name = "variation-generator"
        self.definition = VARIATION_GENERATOR_DEFINITION
        self.indicator_library = INDICATOR_LIBRARY

    def get_definition(self) -> AgentDefinition:
        """에이전트 정의 반환"""
        return self.definition

    def get_indicator_code(self, category: str, indicator: str) -> dict[str, str] | None:
        """지표 코드 반환"""
        if category in self.indicator_library:
            if indicator in self.indicator_library[category]:
                return self.indicator_library[category][indicator]
        return None

    def get_all_indicators(self) -> dict[str, list[str]]:
        """모든 지표 목록 반환"""
        return {
            category: list(indicators.keys())
            for category, indicators in self.indicator_library.items()
        }

    @staticmethod
    def create_variation_prompt(
        base_strategy_code: str,
        base_strategy_name: str,
        variation_config: VariationConfig | None = None
    ) -> str:
        """변형 생성 요청 프롬프트 생성"""
        config_str = ""
        if variation_config:
            config_str = f"""
## 변형 설정
- 트렌드 필터 추가: {variation_config.add_trend_filter}
- 변동성 필터 추가: {variation_config.add_volatility_filter}
- 볼륨 필터 추가: {variation_config.add_volume_filter}
- 파라미터 변형 수: {variation_config.param_variations}
- 추가할 지표: {variation_config.indicators_to_add}"""

        return f"""다음 기본 전략에서 변형 전략들을 생성해주세요.

## 기본 전략 코드
```python
{base_strategy_code}
```

## 기본 전략 이름
{base_strategy_name}
{config_str}

## 작업 순서
1. 기본 전략 분석 (사용된 지표, 진입/청산 조건)
2. 트렌드 필터 추가 변형 생성 (ADX 또는 Supertrend)
3. 모멘텀 필터 추가 변형 생성 (RSI 또는 MFI)
4. 변동성 필터 추가 변형 생성 (ATR 또는 BB)
5. 복합 필터 변형 생성 (트렌드 + 모멘텀)

각 변형 전략을 별도 Python 파일로 저장해주세요."""

    @staticmethod
    def generate_variation_name(
        base_name: str,
        added_indicators: list[str]
    ) -> str:
        """변형 전략 이름 생성"""
        indicator_suffix = "_".join(added_indicators)
        return f"{base_name}_{indicator_suffix}"
