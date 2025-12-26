#!/bin/bash
# 원격 서버 자동 수집기 배포 스크립트
# 사용법: ./scripts/deploy_collector.sh

set -e

# 서버 정보
REMOTE_USER="root"
REMOTE_HOST="152.42.169.132"
REMOTE_PASS="Wnrkswl!23"
REMOTE_DIR="/opt/strategy-research-lab"

# 로컬 디렉토리
LOCAL_DIR="/Users/mr.joo/Desktop/전략연구소/strategy-research-lab"

echo "============================================"
echo "🚀 전략 수집기 원격 서버 배포"
echo "============================================"

# 1. 필요한 파일들 압축
echo "📦 파일 압축 중..."
cd "$LOCAL_DIR"
tar -czvf /tmp/strategy-collector.tar.gz \
    src/collector/human_like_scraper.py \
    src/storage/ \
    requirements.txt \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git'

# 2. 서버로 전송
echo "📤 서버로 전송 중..."
expect -c "
set timeout 120
spawn scp -o StrictHostKeyChecking=no /tmp/strategy-collector.tar.gz $REMOTE_USER@$REMOTE_HOST:/tmp/
expect \"password:\"
send \"$REMOTE_PASS\r\"
expect eof
"

# 3. 서버에서 압축 해제 및 설정
echo "⚙️ 서버 설정 중..."
expect -c "
set timeout 300
spawn ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST
expect \"password:\"
send \"$REMOTE_PASS\r\"
expect \"# \"

# 디렉토리 생성 및 압축 해제
send \"mkdir -p $REMOTE_DIR && cd $REMOTE_DIR && tar -xzvf /tmp/strategy-collector.tar.gz\r\"
expect \"# \"

# Python 환경 설정
send \"pip3 install playwright aiosqlite numpy pandas --quiet\r\"
expect \"# \"

# Playwright 브라우저 설치
send \"playwright install chromium --with-deps\r\"
expect \"# \"

send \"exit\r\"
expect eof
"

echo "✅ 배포 완료!"
echo "============================================"
