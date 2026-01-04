# Backtest 모듈 가이드

> **모듈 위치**: `trading-agent-system/src/backtest/`
>
> **목적**: 백테스트 엔진 및 성과 지표 계산
>
> **마지막 업데이트**: 2026-01-04

---

## 🔧 주요 클래스

### BacktestEngine (engine.py)

```python
from backtest import BacktestEngine

engine = BacktestEngine(
    initial_cash=100_000,
    commission=0.001  # 0.1%
)

# 코드에서 백테스트 실행
metrics = await engine.run_from_code(
    strategy_code,
    data,  # pandas DataFrame (OHLCV)
    symbol="BTCUSDT",
    interval="1h"
)

print(f"수익률: {metrics.total_return}%")
print(f"Sharpe Ratio: {metrics.sharpe_ratio}")
print(f"최대 손실폭: {metrics.max_drawdown}%")
```

### 데이터 로드 예제

```python
import pandas as pd

# Binance 데이터 로드
from data import BinanceCollector

collector = BinanceCollector()
data = await collector.get_data(
    symbol="BTCUSDT",
    interval="1h",
    start="2020-01-01",
    end="2024-12-31"
)

# 또는 Parquet 파일 로드
data = pd.read_parquet("data/datasets/BTCUSDT_1h.parquet")
```

---

## 📊 성과 지표

| 지표 | 설명 | 기준 |
|------|------|------|
| Total Return | 총 수익률 | > 0% |
| Sharpe Ratio | 샤프 비율 | > 1.5 |
| Max Drawdown | 최대 손실폭 | < 30% |
| Win Rate | 승률 | > 40% |
| Profit Factor | 수익 팩터 | > 1.5 |

---

## ✅ 작업 시 체크리스트

- [ ] 새로운 지표 추가 시 이 파일 업데이트
- [ ] [HANDOVER.md](../../HANDOVER.md)에 인수인계 작성
