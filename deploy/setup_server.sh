#!/bin/bash
# 서버 초기 설정 스크립트
# Ubuntu 22.04 LTS 용

set -e

echo "=========================================="
echo "Strategy Research Lab - 서버 설정 시작"
echo "=========================================="

# 프로젝트 디렉토리
PROJECT_DIR="/opt/strategy-research-lab"
VENV_DIR="$PROJECT_DIR/venv"

# 1. 시스템 패키지 업데이트
echo "[1/7] 시스템 패키지 업데이트..."
apt-get update -y
apt-get install -y python3-pip python3-venv git wget curl

# 2. Playwright 의존성 설치
echo "[2/7] Playwright 브라우저 의존성 설치..."
apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0

# 3. 프로젝트 디렉토리 생성
echo "[3/7] 프로젝트 디렉토리 설정..."
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/data
mkdir -p $PROJECT_DIR/data/converted
mkdir -p $PROJECT_DIR/logs

# 4. Python 가상환경 생성
echo "[4/7] Python 가상환경 생성..."
python3 -m venv $VENV_DIR

# 5. pip 업그레이드 및 의존성 설치
echo "[5/7] Python 의존성 설치..."
source $VENV_DIR/bin/activate
pip install --upgrade pip
pip install -r $PROJECT_DIR/requirements.txt

# 6. Playwright 브라우저 설치
echo "[6/7] Playwright 브라우저 설치..."
playwright install chromium
playwright install-deps chromium

# 7. 환경변수 파일 확인
echo "[7/7] 환경 설정 확인..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  .env 파일이 없습니다. 생성합니다..."
    cat > $PROJECT_DIR/.env << 'EOF'
# TradingView Strategy Research Lab 설정

# OpenAI API 키 (LLM 분석용 - 선택사항)
# OPENAI_API_KEY=your_api_key_here

# 데이터베이스 경로
DB_PATH=data/strategies.db

# 스크래핑 설정
MAX_STRATEGIES=50
MIN_LIKES=500
HEADLESS=true
RATE_LIMIT_DELAY=1.5

# LLM 설정 (API 키가 없으면 자동 스킵)
SKIP_LLM=true
LLM_MODEL=gpt-4o

# 출력 디렉토리
OUTPUT_DIR=data/converted
LOGS_DIR=logs
EOF
fi

echo "=========================================="
echo "✅ 서버 설정 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. .env 파일 수정: nano $PROJECT_DIR/.env"
echo "2. 서비스 시작: systemctl start strategy-collector"
echo "3. 로그 확인: journalctl -u strategy-collector -f"
