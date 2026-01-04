# Converter 모듈 가이드

> **모듈 위치**: `strategy-research-lab/src/converter/`
>
> **목적**: Pine Script → Python 변환
>
> **마지막 업데이트**: 2026-01-04

---

## 🔧 주요 클래스

### PineScriptConverter (pine_to_python.py)

#### 사용 예제

```python
from converter import PineScriptConverter

converter = PineScriptConverter(model_name="gemini-2.0-flash-exp")
python_code = await converter.convert(
    pine_code,
    strategy_name="My Strategy"
)

print(python_code)  # Python 코드 출력
```

### StrategyGenerator (strategy_generator.py)

백테스트용 Strategy 클래스 생성

```python
from converter import StrategyGenerator

generator = StrategyGenerator()
strategy_class = generator.generate(
    python_code,
    strategy_name="My Strategy"
)

# 파일로 저장
with open("my_strategy.py", "w") as f:
    f.write(strategy_class)
```

---

## 🚨 알려진 이슈

### 이슈 1: 복잡한 조건문 변환 실패

**해결 방법**: LLM 기반 변환 사용 (Gemini API)

### 이슈 2: 커스텀 함수 미지원

**해결 방법**: 수동으로 Python 함수 작성 후 병합

---

## ✅ 작업 시 체크리스트

- [ ] 변환 규칙 추가 시 예제 코드 작성
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
