#!/bin/bash

# Freqtrade 서버 배포 스크립트
# 서버: 141.164.55.245

set -e

SERVER_IP="141.164.55.245"
SERVER_USER="root"
SERVER_PASSWORD="[Br76r(6mMDr%?ia"
REMOTE_DIR="/root/freqtrade-live"

echo "=============================================="
echo "🚀 Freqtrade 서버 배포 시작"
echo "=============================================="
echo ""
echo "서버: $SERVER_IP"
echo "배포 경로: $REMOTE_DIR"
echo ""

# 1. 배포 파일 준비
echo "📦 배포 파일 준비 중..."
mkdir -p deploy_package/freqtrade

# Freqtrade 설정 파일
cp freqtrade/config.json deploy_package/freqtrade/
cp -r freqtrade/user_data deploy_package/freqtrade/

# 환경 변수 파일
cat > deploy_package/.env << 'EOF'
# Bitget API
BITGET_API_KEY=bg_6563f559d91c72bd3a2b2e552a1c9cec
BITGET_API_SECRET=1db14e0f08b08663d07e60b19af10ecd1ec6f9e162e0cde923dec2770e6b786f
BITGET_API_PASSWORD=Wnrkswl123

# Telegram Notification
TELEGRAM_BOT_TOKEN=8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M
TELEGRAM_CHAT_ID=7980845952
EOF

# Docker Compose 파일
cat > deploy_package/docker-compose.yml << 'EOF'
version: '3.8'

services:
  freqtrade:
    image: freqtradeorg/freqtrade:stable
    container_name: freqtrade-live
    restart: always
    ports:
      - "8082:8080"
    volumes:
      - ./freqtrade/user_data:/freqtrade/user_data
      - ./freqtrade/config.json:/freqtrade/config.json
    environment:
      - TZ=Asia/Seoul
    command: >
      trade
      --config /freqtrade/config.json
      --strategy SimpleAdaptiveStrategy
    networks:
      - trading-network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  trading-network:
    driver: bridge
EOF

# 서버 설정 스크립트
cat > deploy_package/setup_server.sh << 'EOF'
#!/bin/bash

set -e

echo "🔧 서버 환경 설정 중..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "📦 Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    rm get-docker.sh
else
    echo "✅ Docker 이미 설치됨"
fi

# Docker Compose 설치 확인
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Docker Compose 설치 중..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose 이미 설치됨"
fi

# 방화벽 설정
echo "🔥 방화벽 설정 중..."
if command -v ufw &> /dev/null; then
    ufw allow 8082/tcp
    ufw --force enable
fi

echo "✅ 서버 환경 설정 완료!"
EOF

chmod +x deploy_package/setup_server.sh

# 시작 스크립트
cat > deploy_package/start_trading.sh << 'EOF'
#!/bin/bash

echo "=============================================="
echo "🚀 Freqtrade 실전매매 시작"
echo "=============================================="
echo ""

# 기존 컨테이너 중지 및 제거
echo "🛑 기존 컨테이너 중지 중..."
docker-compose down 2>/dev/null || true

# 최신 이미지 pull
echo "📥 최신 Freqtrade 이미지 다운로드 중..."
docker-compose pull

# 컨테이너 시작
echo "🚀 Freqtrade 시작 중..."
docker-compose up -d

# 로그 확인
echo ""
echo "✅ Freqtrade 시작 완료!"
echo ""
echo "📊 모니터링:"
echo "   API: http://141.164.55.245:8082"
echo "   사용자명: admin"
echo "   비밀번호: admin"
echo ""
echo "📝 로그 확인:"
echo "   docker-compose logs -f freqtrade"
echo ""
echo "🛑 중지:"
echo "   docker-compose down"
echo ""

# 5초 후 로그 표시
sleep 5
echo "📋 실시간 로그 (Ctrl+C로 종료):"
docker-compose logs -f freqtrade
EOF

chmod +x deploy_package/start_trading.sh

# 중지 스크립트
cat > deploy_package/stop_trading.sh << 'EOF'
#!/bin/bash

echo "🛑 Freqtrade 중지 중..."
docker-compose down

echo "✅ Freqtrade 중지 완료!"
EOF

chmod +x deploy_package/stop_trading.sh

# 상태 확인 스크립트
cat > deploy_package/check_status.sh << 'EOF'
#!/bin/bash

echo "=============================================="
echo "📊 Freqtrade 상태 확인"
echo "=============================================="
echo ""

# 컨테이너 상태
echo "🐳 Docker 컨테이너 상태:"
docker-compose ps
echo ""

# 최근 로그
echo "📋 최근 로그 (마지막 20줄):"
docker-compose logs --tail=20 freqtrade
echo ""

# API 상태 확인
echo "🌐 API 상태 확인:"
curl -s http://localhost:8080/api/v1/ping || echo "API 응답 없음"
echo ""
EOF

chmod +x deploy_package/check_status.sh

echo "✅ 배포 파일 준비 완료!"
echo ""

# 2. 서버에 파일 전송
echo "📤 서버에 파일 전송 중..."

# sshpass 설치 확인
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass가 설치되어 있지 않습니다."
    echo "   수동으로 파일을 전송해주세요:"
    echo ""
    echo "   scp -r deploy_package/* root@$SERVER_IP:$REMOTE_DIR/"
    echo ""
    exit 1
fi

# SSH 키 확인 비활성화 및 파일 전송
export SSHPASS="$SERVER_PASSWORD"

# 원격 디렉토리 생성
sshpass -e ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR"

# 파일 전송
sshpass -e scp -o StrictHostKeyChecking=no -r deploy_package/* $SERVER_USER@$SERVER_IP:$REMOTE_DIR/

echo "✅ 파일 전송 완료!"
echo ""

# 3. 서버에서 설정 실행
echo "🔧 서버 환경 설정 중..."

sshpass -e ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/freqtrade-live
chmod +x *.sh
./setup_server.sh
ENDSSH

echo "✅ 서버 환경 설정 완료!"
echo ""

# 4. 배포 완료 안내
echo "=============================================="
echo "✅ 배포 완료!"
echo "=============================================="
echo ""
echo "📝 다음 단계:"
echo ""
echo "1. 서버 접속:"
echo "   ssh root@$SERVER_IP"
echo ""
echo "2. Freqtrade 시작:"
echo "   cd $REMOTE_DIR"
echo "   ./start_trading.sh"
echo ""
echo "3. 상태 확인:"
echo "   ./check_status.sh"
echo ""
echo "4. 중지:"
echo "   ./stop_trading.sh"
echo ""
echo "5. 모니터링:"
echo "   http://$SERVER_IP:8082"
echo "   사용자명: admin"
echo "   비밀번호: admin"
echo ""
echo "=============================================="
