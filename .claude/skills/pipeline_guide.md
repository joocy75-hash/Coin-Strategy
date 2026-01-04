# Pipeline 자동화 가이드

> **모듈 위치**: `trading-agent-system/src/orchestrator/`
>
> **목적**: 6단계 파이프라인 자동화
>
> **마지막 업데이트**: 2026-01-04

---

## 🔄 6단계 워크플로우

```
COLLECT → ANALYZE → CONVERT → OPTIMIZE → BACKTEST → REPORT
```

---

## 🔧 사용 예제

### 기본 실행

```python
from orchestrator import TradingPipeline, PipelineConfig

config = PipelineConfig(
    max_strategies=20,
    min_quality_score=60.0,
    symbols=["BTCUSDT", "ETHUSDT"],
    intervals=["1h", "4h"],
    output_dir="pipeline_output"
)

pipeline = TradingPipeline(config)
results = await pipeline.run_full_pipeline()

for result in results:
    print(f"{result.stage.value}: {'✓' if result.success else '✗'}")
```

### 개별 단계 실행

```python
# 수집만 실행
collect_result = await pipeline.run_stage(PipelineStage.COLLECT)

# 분석만 실행
analyze_result = await pipeline.run_stage(PipelineStage.ANALYZE)
```

### 상태 관리

```python
# 일시정지
pipeline.pause()

# 재개
pipeline.resume()

# 취소
pipeline.cancel()

# 상태 확인
status = pipeline.get_status()
print(status["current_stage"])
```

---

## 📝 설정 옵션

```python
config = PipelineConfig(
    # 수집 설정
    max_strategies=20,
    min_likes=50,

    # 분석 설정
    skip_llm_analysis=False,
    min_quality_score=60.0,

    # 백테스트 설정
    symbols=["BTCUSDT", "ETHUSDT"],
    intervals=["1h", "4h"],
    initial_cash=100_000,
    commission=0.001,

    # 최적화 설정
    variation_count=3,
    parallel_backtests=4,

    # 출력 설정
    output_dir="pipeline_output",
    save_intermediate=True,

    # 콜백
    on_stage_complete=my_callback,
    on_error=my_error_handler
)
```

---

## ✅ 작업 시 체크리스트

- [ ] 새로운 단계 추가 시 이 파일 업데이트
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
