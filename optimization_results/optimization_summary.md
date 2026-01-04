# 파라미터 최적화 결과 요약

생성 일시: 2026-01-04 05:08:37

---

## Moon Dev 기준

| 지표 | 목표 |
|------|------|
| Sharpe Ratio | > 1.5 |
| Win Rate | > 40% |
| Profit Factor | > 1.5 |

---

## AdaptiveMLTrailingStop

### 최적화 전후 비교

| 지표 | 최적화 전 | 최적화 후 | 개선 |
|------|----------|----------|------|
| 평균 수익률 | 21.78% | **23.24%** | +1.46% |
| Sharpe Ratio | -0.09 | **0.05** | +0.14 |
| Win Rate | 34.1% | **35.3%** | +1.2% |
| Profit Factor | 1.09 | **1.12** | +0.03 |
| Max Drawdown | 61.87% | **57.25%** | -4.62% |
| Consistency Rate | 60.0% | **50.0%** | -10.0% |

### Moon Dev 기준 통과 여부

- **최적화 전**: ❌ 미달 (0/3)
- **최적화 후**: ❌ 미달 (0/3)

**개선**: Moon Dev 점수 변화 없음

### 최적 파라미터

```python
kama_length = 20
atr_period = 28
base_multiplier = 2.5
fast_length = 15
slow_length = 50
adaptive_strength = 1.0
stop_loss_percent = 5.0
```

### 변경된 파라미터

- `atr_period`: 21 → **28**

---

## PMaxAsymmetric

### 최적화 전후 비교

| 지표 | 최적화 전 | 최적화 후 | 개선 |
|------|----------|----------|------|
| 평균 수익률 | -1.22% | **32.32%** | +33.53% |
| Sharpe Ratio | -0.27 | **-0.01** | +0.27 |
| Win Rate | 34.5% | **36.2%** | +1.8% |
| Profit Factor | 1.00 | **1.11** | +0.11 |
| Max Drawdown | 58.37% | **60.22%** | +1.85% |
| Consistency Rate | 20.0% | **30.0%** | +10.0% |

### Moon Dev 기준 통과 여부

- **최적화 전**: ❌ 미달 (0/3)
- **최적화 후**: ❌ 미달 (0/3)

**개선**: Moon Dev 점수 변화 없음

### 최적 파라미터

```python
atr_length = 14
upper_multiplier = 2.0
lower_multiplier = 3.0
ma_length = 10
ma_type = EMA
stop_loss_percent = 5.0
```

### 변경된 파라미터

- `atr_length`: 10 → **14**
- `upper_multiplier`: 1.5 → **2.0**

---

## HeikinAshiWick

### 최적화 전후 비교

| 지표 | 최적화 전 | 최적화 후 | 개선 |
|------|----------|----------|------|
| 평균 수익률 | -82.28% | **-82.27%** | +0.01% |
| Sharpe Ratio | -2.00 | **-2.00** | +0.00 |
| Win Rate | 33.6% | **33.6%** | +0.0% |
| Profit Factor | 0.90 | **0.90** | +0.00 |
| Max Drawdown | 87.78% | **87.77%** | -0.01% |
| Consistency Rate | 0.0% | **0.0%** | +0.0% |

### Moon Dev 기준 통과 여부

- **최적화 전**: ❌ 미달 (0/3)
- **최적화 후**: ❌ 미달 (0/3)

**개선**: Moon Dev 점수 변화 없음

### 최적 파라미터

```python
stop_loss_percent = 7.0
```

### 변경된 파라미터

- `stop_loss_percent`: 5.0 → **7.0**

---

## 전체 요약

| 전략 | 최적화 전 Sharpe | 최적화 후 Sharpe | Moon Dev (전) | Moon Dev (후) |
|------|-----------------|-----------------|--------------|-------------|
| AdaptiveMLTrailingStop | -0.09 | **0.05** | 0/3 | **0/3** |
| PMaxAsymmetric | -0.27 | **-0.01** | 0/3 | **0/3** |
| HeikinAshiWick | -2.00 | **-2.00** | 0/3 | **0/3** |

---

## 결론

파라미터 최적화를 통해 각 전략의 성과를 개선하였습니다.

**주의사항**:
- 과최적화 방지를 위해 단순한 파라미터 값을 선호했습니다
- 10개 데이터셋에서 평균 성과를 기준으로 최적화했습니다
- Out-of-sample 테스트를 통해 실전 성과를 추가 검증해야 합니다

