# Analyzer 모듈 가이드

> **모듈 위치**: `strategy-research-lab/src/analyzer/`
>
> **목적**: Pine Script 전략 품질 분석 (Repainting, Overfitting, Risk, LLM 분석)
>
> **마지막 업데이트**: 2026-01-04

---

## 📁 모듈 구조

```
src/analyzer/
├── rule_based/
│   ├── repainting_detector.py   # Repainting 위험 탐지
│   ├── overfitting_detector.py  # 과적합 위험 탐지
│   └── risk_checker.py          # 리스크 관리 체크
├── llm/
│   ├── deep_analyzer.py         # Claude API 심층 분석
│   └── prompts.py               # LLM 프롬프트 템플릿
└── scorer.py                     # 종합 점수 산출
```

---

## 🔧 주요 클래스

### 1. RepaintingDetector (repainting_detector.py)

#### 사용 예제

```python
from analyzer import RepaintingDetector

detector = RepaintingDetector()
result = detector.detect(pine_code)

print(f"리스크 레벨: {result.risk_level}")  # "safe", "warning", "danger"
print(f"점수: {result.score}/100")
print(f"탐지된 패턴: {result.detected_patterns}")
```

#### 탐지 패턴

| 패턴 | 위험도 | 설명 |
|------|--------|------|
| `security()` lookahead | 높음 | 미래 데이터 참조 |
| `barstate.isrealtime` | 중간 | 실시간/히스토리 구분 |
| `request.security()` offset | 높음 | 오프셋 미래 참조 |

---

### 2. OverfittingDetector (overfitting_detector.py)

#### 사용 예제

```python
from analyzer import OverfittingDetector

detector = OverfittingDetector()
result = detector.detect(pine_code)

print(f"점수: {result.score}/100")
print(f"매직넘버 개수: {len(result.magic_numbers)}")
print(f"파라미터 개수: {result.parameter_count}")
```

---

### 3. LLMDeepAnalyzer (deep_analyzer.py)

#### 사용 예제

```python
from analyzer import LLMDeepAnalyzer

analyzer = LLMDeepAnalyzer(api_key="sk-ant-...")
result = await analyzer.analyze(pine_code)

print(f"로직 견고성: {result.logic_robustness}/10")
print(f"실거래 적합성: {result.real_trading_viability}/10")
print(f"요약: {result.summary}")
```

#### 주요 설정

```python
# .env 파일
ANTHROPIC_API_KEY=sk-ant-api03-...
LLM_MODEL=claude-3-5-sonnet-20241022  # 또는 claude-3-5-haiku-20241022 (저비용)
```

---

### 4. StrategyScorer (scorer.py)

전체 분석 결과를 종합하여 A~F 등급 산출

#### 사용 예제

```python
from analyzer import StrategyScorer

scorer = StrategyScorer()
final_score = scorer.calculate_final_score(
    repainting_result,
    overfitting_result,
    risk_result,
    llm_result
)

print(f"총점: {final_score.total_score}/100")
print(f"등급: {final_score.grade}")  # A, B, C, D, F
print(f"권장: {final_score.recommended}")  # True/False
```

#### 등급 기준

| 등급 | 점수 | 의미 |
|------|------|------|
| A | 80~100 | 매우 우수 (실거래 권장) |
| B | 60~79 | 우수 (검토 후 사용) |
| C | 40~59 | 보통 (주의 필요) |
| D | 20~39 | 미흡 (비권장) |
| F | 0~19 | 불량 (사용 금지) |

---

## 🚨 알려진 이슈

### 이슈 1: Claude API Rate Limit

**해결 방법**:
```python
# Haiku 모델 사용 (저비용, 빠른 속도)
analyzer = LLMDeepAnalyzer(model="claude-3-5-haiku-20241022")
```

### 이슈 2: 분석 시간 오래 걸림

**해결 방법**: LLM 분석 스킵
```python
# skip_llm_analysis=True
from analyzer import StrategyScorer
final_score = scorer.calculate_final_score(
    repainting_result,
    overfitting_result,
    risk_result,
    llm_result=None  # LLM 분석 결과 없이 계산
)
```

---

## 🔄 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2025-12-25 | 1.1 | OpenAI → Claude API 전환 | Claude |
| 2025-12-24 | 1.0 | 초기 구현 완료 | Claude |

---

## ✅ 작업 시 체크리스트

- [ ] 새로운 탐지 패턴 추가 시 이 파일 업데이트
- [ ] LLM 프롬프트 변경 시 prompts.py 문서화
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
