# C등급 전략 개선 시스템

> 37개 C등급 전략에 리스크 관리를 추가하여 B등급으로 업그레이드하는 자동화 시스템

## Quick Start

```bash
cd /Users/mr.joo/Desktop/전략연구소

# 1. 백테스트 실행
python3 run_enhanced_backtest.py

# 2. 결과 확인
cat c_grade_enhancement_results.csv

# 3. 상세 보고서 보기
cat C_GRADE_IMPROVEMENT_REPORT.md
```

## 주요 파일

| 파일 | 설명 | 크기 |
|------|------|------|
| `C_GRADE_IMPROVEMENT_REPORT.md` | 상세 프로젝트 보고서 | 7.1 KB |
| `PROJECT_SUMMARY.md` | 프로젝트 요약 | 5.3 KB |
| `risk_management_patterns.py` | 리스크 관리 모듈 | 11 KB |
| `run_enhanced_backtest.py` | 백테스트 실행 스크립트 | 9.0 KB |
| `c_grade_enhancement_results.csv` | 백테스트 결과 | 514 B |
| `c_grade_top5_analysis.csv` | Top 5 전략 분석 | 610 B |

## 생성된 전략

### Python 전략 (4개)

1. **SuperTrend Divergence**
   - Original: `enhanced_strategies/1_supertrend_divergence_original.py`
   - Enhanced: `enhanced_strategies/1_supertrend_divergence_enhanced.py`

2. **ATR VWMA Deviation**
   - Original: `enhanced_strategies/2_atr_vwma_deviation_original.py`
   - Enhanced: `enhanced_strategies/2_atr_vwma_deviation_enhanced.py`

### Pine Scripts (5개)

- `enhanced_strategies/1_YUBXfhpq-SuperTrend-Weighted-by-Divergence.pine`
- `enhanced_strategies/2_dTBnHWe8-ATR-Normalized-VWMA-Deviation.pine`
- `enhanced_strategies/3_0E5xrn6O-Kalman-Hull-Kijun-BackQuant.pine`
- `enhanced_strategies/4_oOaiuY4l.pine`
- `enhanced_strategies/5_x0pgNaRA-Support-and-Resistance.pine`

## 리스크 관리 기능

Enhanced 버전에 추가된 기능:

### 1. Stop Loss
- 고정 5% 또는 ATR × 2.0
- 포지션 진입 시 자동 설정

### 2. Take Profit
- Risk:Reward 비율 1:2
- Stop Loss 대비 2배 수익 목표

### 3. Trailing Stop
- 5% 수익 달성 시 활성화
- 최고가 대비 3% 하락 시 청산

### 4. Position Sizing
- Kelly Criterion (1/4 Kelly)
- 최소 2%, 최대 10% 제한

## 백테스트 결과

### SuperTrend Divergence

| 지표 | Original | Enhanced | 개선도 |
|------|----------|----------|--------|
| Sharpe Ratio | -0.44 | -0.43 | +0.01 |
| Profit Factor | 0.95 | 0.93 | -0.02 |
| **Max Drawdown** | **-60.16%** | **-53.69%** | **+6.47%** ⬆ |
| **Win Rate** | **27.64%** | **31.99%** | **+4.34%** ⬆ |

주요 개선:
- Max Drawdown 6.47% 감소 (리스크 관리 효과)
- Win Rate 4.34% 향상 (Take Profit 효과)

## 데이터베이스 현황

총 63개 전략:
- B등급: 3개
- **C등급: 37개** ← 개선 대상
- D등급: 16개
- F등급: 7개

## 다음 단계

1. **나머지 35개 C등급 전략 처리**
   - 동일한 패턴으로 자동화

2. **데이터셋 확장**
   - 10개 → 25개 (Moon Dev 기준)

3. **파라미터 최적화**
   - Optuna로 Stop Loss, Take Profit 최적화

4. **Moon Dev 기준 통과**
   - Sharpe Ratio > 1.5
   - Profit Factor > 1.5
   - Max Drawdown < -30%
   - Win Rate > 40%

## 기술 스택

- Python 3.11
- backtesting.py
- pandas, numpy
- SQLite
- Binance API

## 프로젝트 구조

```
/Users/mr.joo/Desktop/전략연구소/
├── C_GRADE_IMPROVEMENT_REPORT.md      # 상세 보고서
├── PROJECT_SUMMARY.md                 # 프로젝트 요약
├── README_C_GRADE_PROJECT.md          # 본 파일
├── risk_management_patterns.py        # 리스크 관리 모듈
├── run_enhanced_backtest.py           # 백테스트 스크립트
├── c_grade_enhancement_results.csv    # 백테스트 결과
├── c_grade_top5_analysis.csv          # Top 5 분석
└── enhanced_strategies/               # 전략 코드
    ├── [Python strategies × 4]
    └── [Pine scripts × 5]
```

## 문의

프로젝트 위치: `/Users/mr.joo/Desktop/전략연구소/`

---

**프로젝트 완료**: 2026-01-04  
**시스템**: Claude Code + Trading Agent System
