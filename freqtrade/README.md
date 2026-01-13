# Freqtrade 통합 가이드

> TradingView Strategy Research Lab과 Freqtrade 연동
> 버전: 2025.12 + FreqAI (머신러닝/강화학습)

## 📦 추가 설치 항목

### 필수 패키지
| 패키지 | 용도 | 크기 |
|--------|------|------|
| TA-Lib | 기술적 분석 지표 | ~50MB |
| FreqUI | 웹 인터페이스 | ~20MB |

### FreqAI (머신러닝)
| 패키지 | 용도 | 크기 |
|--------|------|------|
| scikit-learn | 기본 ML | ~30MB |
| LightGBM | 빠른 그래디언트 부스팅 | ~5MB |
| XGBoost | 정확한 그래디언트 부스팅 | ~100MB |
| CatBoost | 범주형 데이터 특화 | ~200MB |

### FreqAI-RL (강화학습)
| 패키지 | 용도 | 크기 |
|--------|------|------|
| PyTorch | 딥러닝 프레임워크 | ~2GB |
| Stable-Baselines3 | 강화학습 알고리즘 | ~50MB |
| Gymnasium | RL 환경 | ~10MB |
| TensorBoard | 학습 시각화 | ~50MB |

### 최적화 도구
| 패키지 | 용도 | 크기 |
|--------|------|------|
| Optuna | 하이퍼파라미터 최적화 | ~20MB |
| SHAP | 모델 해석 | ~30MB |

**총 용량: ~2.5GB** (FreqAI-RL 포함 시)

## 🚀 설치 방법

### 방법 1: Docker (권장)

```bash
cd freqtrade
docker-compose up -d
```

### 방법 2: 풀 설치 (FreqAI + RL 포함)

```bash
chmod +x install_freqtrade.sh
./install_freqtrade.sh
```

## 🚀 시작하기

### 1. 설정 파일 수정

`config.json` 파일에서 다음 항목 수정:

```json
{
    "exchange": {
        "key": "YOUR_BINANCE_API_KEY",
        "secret": "YOUR_BINANCE_SECRET"
    },
    "telegram": {
        "token": "YOUR_TELEGRAM_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID"
    },
    "api_server": {
        "jwt_secret_key": "RANDOM_STRING_HERE",
        "password": "SECURE_PASSWORD_HERE"
    }
}
```

### 2. 드라이런 (모의매매) 시작

```bash
# Docker
docker-compose up -d

# 직접 설치
source ~/freqtrade/.venv/bin/activate
freqtrade trade --config config.json --strategy SampleStrategy
```

### 3. 웹 UI 접속

- URL: http://141.164.55.245:8080
- Username: freqtrader
- Password: (config.json에서 설정한 비밀번호)

## 📊 전략 변환

TradingView에서 검증된 전략을 Freqtrade 형식으로 변환:

```python
from strategy_converter import FreqtradeStrategyConverter, StrategyInfo

converter = FreqtradeStrategyConverter()

strategy = StrategyInfo(
    name="My Strategy",
    description="검증된 전략",
    timeframe="1h",
    indicators={
        'sma_fast': {'type': 'sma', 'period': 20},
        'sma_slow': {'type': 'sma', 'period': 50},
    },
    entry_conditions=[
        "(dataframe['sma_fast'] > dataframe['sma_slow'])",
    ],
    exit_conditions=[
        "(dataframe['sma_fast'] < dataframe['sma_slow'])",
    ],
    stoploss=-0.05,
    win_rate=0.55,
    profit_factor=1.8,
)

file_path = converter.convert(strategy)
print(f"전략 생성됨: {file_path}")
```

## 🔧 주요 명령어

```bash
# 드라이런 시작 (기본 전략)
freqtrade trade --config config.json --strategy SampleStrategy

# FreqAI 드라이런 (머신러닝)
freqtrade trade --config config_freqai.json --strategy FreqAIStrategy --freqaimodel LightGBMRegressor

# FreqAI 강화학습
freqtrade trade --config config_freqai.json --strategy FreqAIStrategy --freqaimodel ReinforcementLearner

# 백테스트
freqtrade backtesting --config config.json --strategy SampleStrategy --timerange 20240101-20241231

# FreqAI 백테스트
freqtrade backtesting --config config_freqai.json --strategy FreqAIStrategy --freqaimodel LightGBMRegressor --timerange 20240101-20241231

# 파라미터 최적화 (Hyperopt)
freqtrade hyperopt --config config.json --strategy SampleStrategy --hyperopt-loss SharpeHyperOptLoss -e 100

# 데이터 다운로드
freqtrade download-data --config config.json --pairs BTC/USDT ETH/USDT --timeframe 5m 15m 1h 4h --days 365

# 로그 확인
freqtrade show-trades --config config.json

# FreqUI 설치/업데이트
freqtrade install-ui
```

## 🤖 FreqAI 모델 종류

| 모델 | 명령어 | 특징 |
|------|--------|------|
| LightGBM | `--freqaimodel LightGBMRegressor` | 빠름, 기본 추천 |
| XGBoost | `--freqaimodel XGBoostRegressor` | 정확도 높음 |
| CatBoost | `--freqaimodel CatBoostRegressor` | 범주형 데이터 |
| 강화학습 | `--freqaimodel ReinforcementLearner` | 적응형 학습 |

## 📱 텔레그램 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 |
| `/stop` | 봇 정지 |
| `/status` | 현재 포지션 |
| `/profit` | 수익 현황 |
| `/balance` | 잔고 확인 |
| `/daily` | 일일 수익 |
| `/performance` | 성과 분석 |
| `/forcesell all` | 전체 청산 |

## ⚠️ 실전매매 전 체크리스트

- [ ] 드라이런에서 최소 2주 테스트
- [ ] 승률 50% 이상 확인
- [ ] 최대 드로다운 10% 이하 확인
- [ ] API 키 출금 권한 제거
- [ ] IP 화이트리스트 설정
- [ ] 소액($100)으로 1주일 테스트
- [ ] 텔레그램 알림 정상 동작 확인

## 📁 디렉토리 구조

```
freqtrade/
├── config.json              # 기본 설정 (드라이런)
├── config_freqai.json       # FreqAI 설정 (머신러닝)
├── docker-compose.yml       # Docker 설정
├── install_freqtrade.sh     # 풀 설치 스크립트
├── strategy_converter.py    # 전략 변환기
├── README.md               # 이 파일
└── user_data/
    ├── strategies/         # 전략 파일
    │   ├── SampleStrategy.py
    │   └── FreqAIStrategy.py
    ├── data/               # 가격 데이터
    ├── logs/               # 로그
    ├── models/             # FreqAI 학습된 모델
    └── backtest_results/   # 백테스트 결과
```

## 🔗 참고 링크

- [Freqtrade 공식 문서](https://www.freqtrade.io/)
- [Freqtrade GitHub](https://github.com/freqtrade/freqtrade)
- [전략 예제](https://github.com/freqtrade/freqtrade-strategies)
