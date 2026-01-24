# 🚀 Freqtrade 최적 세팅 가이드

## 📋 개요

Freqtrade를 최대한 활용하기 위한 추가 패키지 및 설정 가이드입니다.

## 📦 추가 패키지 요약

| 카테고리 | 패키지 | 용도 | 우선순위 |
|---------|--------|------|---------|
| **필수** | TA-Lib | 기술적 분석 지표 | ⭐⭐⭐ |
| **필수** | FreqUI | 웹 인터페이스 | ⭐⭐⭐ |
| **ML** | LightGBM | 빠른 그래디언트 부스팅 | ⭐⭐⭐ |
| **ML** | XGBoost | 정확한 그래디언트 부스팅 | ⭐⭐ |
| **ML** | CatBoost | 범주형 데이터 특화 | ⭐⭐ |
| **RL** | PyTorch (~2GB) | 딥러닝 프레임워크 | ⭐ |
| **RL** | Stable-Baselines3 | 강화학습 알고리즘 | ⭐ |
| **RL** | Gymnasium | RL 환경 | ⭐ |
| **최적화** | Optuna | 하이퍼파라미터 자동 최적화 | ⭐⭐⭐ |
| **시각화** | TensorBoard | 학습 과정 시각화 | ⭐⭐ |
| **해석** | SHAP | 모델 예측 해석 | ⭐⭐ |

## 🎯 권장 설치 순서

### 1단계: 필수 패키지 (모든 사용자)

```bash
cd freqtrade
pip3 install TA-Lib
```

### 2단계: 머신러닝 기본 (ML 전략 사용자)

```bash
pip3 install lightgbm xgboost catboost
```

### 3단계: 최적화 도구 (성능 향상 원하는 사용자)

```bash
pip3 install optuna tensorboard shap plotly scikit-learn pandas-ta
```

### 4단계: 강화학습 (고급 사용자, 선택)

⚠️ **주의**: PyTorch는 약 2GB 용량입니다

```bash
pip3 install torch torchvision stable-baselines3 gymnasium
```

## 🚀 빠른 설치

### 방법 1: 대화형 설치 스크립트

```bash
cd freqtrade
./install_optimal_packages.sh
```

### 방법 2: 전체 설치

```bash
cd freqtrade
pip3 install -r requirements_optimal.txt
```

## 📊 패키지별 상세 설명

### TA-Lib (필수)

**용도**: 기술적 분석 지표 계산
- RSI, MACD, Bollinger Bands 등 150+ 지표
- C로 작성되어 매우 빠름

**설치**:
```bash
# macOS
brew install ta-lib
pip3 install TA-Lib

# Ubuntu/Debian
sudo apt-get install ta-lib
pip3 install TA-Lib
```

### LightGBM (추천)

**용도**: 빠른 머신러닝 모델
- 메모리 효율적
- 빠른 학습 속도
- 높은 정확도

**사용 예시**:
```python
from freqtrade.freqai.prediction_models.LightGBMClassifier import LightGBMClassifier
```

### XGBoost

**용도**: 정확한 머신러닝 모델
- 높은 예측 정확도
- 과적합 방지 기능
- 병렬 처리 지원

### CatBoost

**용도**: 범주형 데이터 특화
- 범주형 변수 자동 처리
- 과적합 방지
- GPU 가속 지원

### PyTorch (고급)

**용도**: 딥러닝 및 강화학습
- 신경망 구축
- 강화학습 에이전트
- 커스텀 모델 개발

⚠️ **주의**: 
- 용량: ~2GB
- GPU 사용 시 CUDA 필요
- 고급 사용자 전용

### Stable-Baselines3 (고급)

**용도**: 강화학습 알고리즘
- PPO, A2C, SAC 등
- 자동 매매 에이전트 학습
- 환경 상호작용

### Optuna (추천)

**용도**: 하이퍼파라미터 최적화
- 자동 파라미터 튜닝
- 베이지안 최적화
- 병렬 실행 지원

**사용 예시**:
```bash
freqtrade hyperopt --strategy YourStrategy --hyperopt-loss SharpeHyperOptLoss
```

### TensorBoard

**용도**: 학습 과정 시각화
- 손실 함수 그래프
- 메트릭 추적
- 모델 구조 시각화

**사용 예시**:
```bash
tensorboard --logdir user_data/models/
```

### SHAP

**용도**: 모델 예측 해석
- 특성 중요도 분석
- 예측 설명
- 모델 디버깅

## 🔧 설정 최적화

### config.json 권장 설정

```json
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": 20.0,
  "dry_run": true,
  "trading_mode": "spot",
  
  "api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8081,
    "username": "admin",
    "password": "admin"
  },
  
  "freqai": {
    "enabled": true,
    "purge_old_models": true,
    "train_period_days": 30,
    "backtest_period_days": 7,
    "identifier": "unique_id",
    "feature_parameters": {
      "include_timeframes": ["5m", "15m", "1h"],
      "include_corr_pairlist": ["BTC/USDT", "ETH/USDT"]
    },
    "data_split_parameters": {
      "test_size": 0.33,
      "shuffle": false
    },
    "model_training_parameters": {
      "n_estimators": 1000
    }
  }
}
```

## 📈 성능 최적화 팁

### 1. 백테스트 속도 향상

```bash
# 병렬 처리 사용
freqtrade backtesting --strategy YourStrategy --timerange 20240101-20241231 -j 4

# 캐시 사용
freqtrade backtesting --strategy YourStrategy --cache none
```

### 2. 메모리 최적화

```python
# 전략 파일에서
def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    # 불필요한 컬럼 제거
    dataframe = dataframe[['open', 'high', 'low', 'close', 'volume']]
    return dataframe
```

### 3. FreqAI 최적화

```json
{
  "freqai": {
    "feature_parameters": {
      "include_timeframes": ["5m", "1h"],  // 타임프레임 줄이기
      "include_corr_pairlist": ["BTC/USDT"]  // 상관관계 페어 줄이기
    }
  }
}
```

## 🧪 테스트 및 검증

### 1. 설치 확인

```bash
freqtrade show-config
freqtrade list-strategies
```

### 2. 백테스트 실행

```bash
freqtrade backtesting \
  --strategy SimpleAdaptiveStrategy \
  --timerange 20240101-20241231 \
  --export trades
```

### 3. 웹 UI 시작

```bash
freqtrade webserver --config config.json
```

접속: http://localhost:8081

## 📚 추가 리소스

- [Freqtrade 공식 문서](https://www.freqtrade.io/en/stable/)
- [FreqAI 가이드](https://www.freqtrade.io/en/stable/freqai/)
- [전략 개발 가이드](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Discord 커뮤니티](https://discord.gg/freqtrade)

## ⚠️ 주의사항

1. **Dry Run으로 시작**: 실전 거래 전에 충분히 테스트
2. **소액으로 시작**: 실전 거래는 소액으로 시작
3. **정기 모니터링**: 봇을 정기적으로 확인
4. **백업**: 설정 파일과 데이터베이스 정기 백업
5. **API 키 보안**: API 키를 절대 공유하지 마세요

## 🆘 문제 해결

### TA-Lib 설치 실패

```bash
# macOS
brew install ta-lib

# Ubuntu
sudo apt-get install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

### PyTorch 설치 실패

```bash
# CPU 버전만 설치 (용량 절약)
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 메모리 부족

```bash
# 스왑 메모리 증가 (Linux)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

**Happy Trading! 🚀**
