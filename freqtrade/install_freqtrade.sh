#!/bin/bash
# Freqtrade 최신 버전 + FreqAI 풀 설치 스크립트
# 버전: 2025.12 (최신)
# 서버: 141.164.55.245

set -e

echo "=========================================="
echo "Freqtrade 2025.12 + FreqAI 풀 설치"
echo "=========================================="

# 1. 시스템 패키지 업데이트
echo "[1/10] 시스템 패키지 업데이트..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev \
    git curl wget build-essential libssl-dev libffi-dev \
    libatlas-base-dev libopenblas-dev libhdf5-dev \
    cmake pkg-config libfreetype6-dev libpng-dev

# 2. TA-Lib 설치 (기술적 분석 라이브러리)
echo "[2/10] TA-Lib 설치..."
if ! command -v ta-lib-config &> /dev/null; then
    cd /tmp
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
fi

# 3. Freqtrade 디렉토리 생성
echo "[3/10] Freqtrade 디렉토리 생성..."
FREQTRADE_DIR="$HOME/freqtrade"
mkdir -p $FREQTRADE_DIR
cd $FREQTRADE_DIR

# 4. Freqtrade 클론 (최신 버전)
echo "[4/10] Freqtrade 2025.12 클론..."
if [ -d ".git" ]; then
    git fetch --all
    git checkout stable
    git pull
else
    git clone https://github.com/freqtrade/freqtrade.git .
    git checkout stable
fi

# 5. Python 가상환경 생성 및 활성화
echo "[5/10] Python 가상환경 설정..."
python3 -m venv .venv
source .venv/bin/activate

# 6. Freqtrade 기본 설치
echo "[6/10] Freqtrade 기본 설치..."
pip install --upgrade pip wheel setuptools

# 모든 의존성 포함 설치 (hyperopt, plot, freqai, freqai-rl)
pip install -e .[all]

# 7. FreqAI 추가 패키지 설치
echo "[7/10] FreqAI ML 패키지 설치..."

# 기본 ML 라이브러리
pip install scikit-learn>=1.3.0
pip install lightgbm>=4.0.0
pip install xgboost>=2.0.0
pip install catboost>=1.2.0

# 딥러닝 (PyTorch)
pip install torch>=2.1.0
pip install pytorch-lightning>=2.1.0

# 강화학습 (FreqAI-RL)
pip install stable-baselines3>=2.2.0
pip install gymnasium>=0.29.0
pip install tensorboard>=2.15.0

# 추가 ML 도구
pip install optuna>=3.4.0  # 하이퍼파라미터 최적화
pip install shap>=0.44.0   # 모델 해석
pip install joblib>=1.3.0  # 병렬 처리

# 8. 데이터 분석 패키지
echo "[8/10] 데이터 분석 패키지 설치..."
pip install pandas-ta>=0.3.14b  # 기술적 지표
pip install ta>=0.11.0          # 추가 지표
pip install scipy>=1.11.0       # 과학 계산
pip install statsmodels>=0.14.0 # 통계 모델

# 9. FreqUI 설치 (웹 UI)
echo "[9/10] FreqUI 설치..."
freqtrade install-ui

# 10. 설정 확인
echo "[10/10] 설치 확인..."
freqtrade --version
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import lightgbm; print(f'LightGBM: {lightgbm.__version__}')"
python -c "import stable_baselines3; print(f'Stable-Baselines3: {stable_baselines3.__version__}')"

echo "=========================================="
echo "Freqtrade + FreqAI 풀 설치 완료!"
echo "=========================================="
echo ""
echo "설치된 기능:"
echo "  ✅ Freqtrade 2025.12 (최신)"
echo "  ✅ FreqUI (웹 인터페이스)"
echo "  ✅ FreqAI (머신러닝)"
echo "  ✅ FreqAI-RL (강화학습)"
echo "  ✅ Hyperopt (파라미터 최적화)"
echo "  ✅ LightGBM, XGBoost, CatBoost"
echo "  ✅ PyTorch + Stable-Baselines3"
echo ""
echo "다음 단계:"
echo "1. 설정 파일 수정: config.json"
echo "2. 드라이런 시작: freqtrade trade --config config.json --strategy SampleStrategy"
echo "3. 웹 UI 접속: http://141.164.55.245:8080"
echo "4. FreqAI 시작: freqtrade trade --freqaimodel LightGBMRegressor --strategy FreqaiExampleStrategy"
echo ""
