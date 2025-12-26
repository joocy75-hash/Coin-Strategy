# src/analyzer/llm/prompts.py

ANALYSIS_PROMPT_TEMPLATE = """당신은 알고리즘 트레이딩 전략 분석 전문가입니다.

## 분석 대상 전략

- 제목: {title}
- 설명: {description}
- 성과 지표: {performance}

## 사전 분석 결과 (규칙 기반)

{rule_analysis}

## Pine Script 코드

```pinescript
{pine_code}
```

## 분석 요청

다음 항목을 1-10점으로 평가하고 근거를 제시하세요:

1. __로직 견고성 (logic_score)__:
   - 전략 논리가 시장 원리에 부합하는가?
   - 단순 커브피팅이 아닌 재현 가능한 로직인가?

2. __리스크 관리 (risk_score)__:
   - Stop Loss / Take Profit 구현 여부
   - Position Sizing 로직 존재 여부
   - 최대 손실 제한 메커니즘

3. __실거래 적합성 (practical_score)__:
   - 슬리피지, 수수료 고려 여부
   - 현실적인 진입/청산 조건
   - 유동성 고려

4. __코드 품질 (code_quality_score)__:
   - 가독성
   - 에러 처리
   - Python 변환 용이성

JSON 형식으로만 응답 (다른 텍스트 없이):

```json
{{
  "logic_score": 7,
  "logic_reason": "이유...",
  "risk_score": 6,
  "risk_reason": "이유...",
  "practical_score": 5,
  "practical_reason": "이유...",
  "code_quality_score": 7,
  "code_quality_reason": "이유...",
  "overall_recommendation": "PASS|REVIEW|REJECT",
  "key_strengths": ["강점1", "강점2"],
  "key_weaknesses": ["약점1", "약점2"],
  "summary_kr": "한국어 요약 (100자 이내)",
  "conversion_notes": "Python 변환 시 주의사항"
}}
```"""


CONVERSION_PROMPT_TEMPLATE = """당신은 Pine Script를 Python 트레이딩 전략으로 변환하는 전문가입니다.

## 원본 Pine Script
```pinescript
{pine_code}
```

## 변환 요구사항

1. 플랫폼 인터페이스 준수:
   - generate_signal(current_price, candles, current_position) 함수 구현
   - 반환 형식: {{"action": "buy|sell|hold|close", "confidence": 0.0-1.0, ...}}

2. 기술적 지표:
   - numpy 또는 pandas-ta 사용
   - 캔들 데이터: [{{"open", "high", "low", "close", "volume", "timestamp"}}]

3. 포지션 관리:
   - current_position 구조: {{"side": "long|short", "entry_price", "pnl_percent", ...}}
   - 익절/손절 로직 포함

## 출력 형식
완전한 Python 코드만 출력 (설명 없이):
```python
# 여기에 코드
```"""


QUICK_ANALYSIS_PROMPT = """Pine Script 전략을 간단히 평가하세요.

코드:
```
{pine_code}
```

JSON 형식으로 응답:
{{
  "score": 1-10,
  "recommendation": "PASS|REVIEW|REJECT",
  "reason": "한 줄 이유"
}}"""


INDICATOR_EXTRACTION_PROMPT = """다음 Pine Script에서 사용된 기술적 지표를 추출하세요.

```pinescript
{pine_code}
```

JSON 형식으로 응답:
{{
  "indicators": [
    {{"name": "EMA", "params": {{"period": 20}}}},
    {{"name": "RSI", "params": {{"period": 14}}}}
  ],
  "custom_indicators": ["커스텀 지표명1", "커스텀 지표명2"]
}}"""


ENTRY_EXIT_EXTRACTION_PROMPT = """다음 Pine Script에서 진입/청산 조건을 추출하세요.

```pinescript
{pine_code}
```

JSON 형식으로 응답:
{{
  "long_entry": ["조건1", "조건2"],
  "long_exit": ["조건1"],
  "short_entry": ["조건1", "조건2"],
  "short_exit": ["조건1"],
  "stop_loss": "설명 또는 null",
  "take_profit": "설명 또는 null"
}}"""
