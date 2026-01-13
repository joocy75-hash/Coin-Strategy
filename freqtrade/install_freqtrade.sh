#!/bin/bash
# Freqtrade 최신 버전 설치 스크립트
# 버전: 2025.12 (최신)
# 서버: 141.164.55.245

set -e

echo "=========================================="
echo "Freqtrade 2025.12 설치 시작"
echo "=========================================="

# 1. 시스템 패키지 업데이트
echo "[1/7] 시스템 패키지 업데이트..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev \
    git curl wget build-essential libssl-dev libffi-dev \
    libatlas-base-dev libopenblas-dev

# 2. TA-Lib 설치 (기술적 분석 라이브러리)
echo "[2/7] TA-Lib 설치..."
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
echo "[3/7] Freqtrade 디렉토리 생성..."
FREQTRADE_DIR="$HOME/freqtrade"
mkdir -p $FREQTRADE_DIR
cd $FREQTRADE_DIR

# 4. Freqtrade 클론 (최신 버전)
echo "[4/7] Freqtrade 2025.12 클론..."
if [ -d ".git" ]; then
    git fetch --all
    git checkout stable
    git pull
else
    git clone https://github.com/freqtrade/freqtrade.git .
    git checkout stable
fi

# 5. Python 가상환경 생성 및 활성화
echo "[5/7] Python 가상환경 설정..."
python3 -m venv .venv
source .venv/bin/activate

# 6. Freqtrade 설치
echo "[6/7] Freqtrade 설치..."
pip install --upgrade pip
pip install -e .[all]

# 7. FreqUI 설치 (웹 UI)
echo "[7/7] FreqUI 설치..."
freqtrade install-ui

echo "=========================================="
echo "Freqtrade 설치 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. 설정 파일 생성: freqtrade new-config"
echo "2. 드라이런 시작: freqtrade trade --config config.json --strategy SampleStrategy"
echo "3. 웹 UI 접속: http://141.164.55.245:8080"
echo ""
