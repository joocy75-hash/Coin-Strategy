# AI Agent 시스템 가이드

> **모듈 위치**: `trading-agent-system/src/agents/`
>
> **목적**: 4개 전문 AI 에이전트 (변환, 변형 생성, 백테스트, 결과 분석)
>
> **마지막 업데이트**: 2026-01-04

---

## 🤖 4개 AI 에이전트

### 1. StrategyArchitect (strategy_architect.py)

Pine Script → Python 완전 변환

```python
from agents import StrategyArchitectAgent

agent = StrategyArchitectAgent()
python_code = await agent.convert(pine_code, strategy_name="My Strategy")
```

### 2. VariationGenerator (variation_generator.py)

지표 조합 변형 전략 생성

```python
from agents import VariationGeneratorAgent

agent = VariationGeneratorAgent()
variations = await agent.generate_variations(
    base_strategy_code,
    count=4  # 4개 변형 생성
)

for i, variation in enumerate(variations):
    print(f"변형 {i+1}: {variation.description}")
```

### 3. BacktestRunner (backtest_runner.py)

다중 데이터셋 병렬 백테스트

```python
from agents import BacktestRunnerAgent

agent = BacktestRunnerAgent()
results = await agent.run_backtests(
    strategy_code,
    symbols=["BTCUSDT", "ETHUSDT"],
    intervals=["1h", "4h"]
)
```

### 4. ResultAnalyzer (result_analyzer.py)

결과 집계 및 랭킹

```python
from agents import ResultAnalyzerAgent

agent = ResultAnalyzerAgent()
top_strategies = await agent.analyze_and_rank(
    backtest_results,
    min_sharpe=1.5,
    min_profit_factor=1.5
)
```

---

## ✅ 작업 시 체크리스트

- [ ] 새로운 에이전트 추가 시 이 파일 업데이트
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
