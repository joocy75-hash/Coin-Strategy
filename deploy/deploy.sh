#!/bin/bash
# 원격 서버 배포 스크립트
# 로컬에서 실행: ./deploy/deploy.sh

set -e

# 설정
SERVER_IP="152.42.169.132"
SERVER_USER="root"
SERVER_PASS="Wnrkswl!23"
PROJECT_DIR="/opt/strategy-research-lab"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "Strategy Research Lab - 서버 배포"
echo "=========================================="
echo "로컬: $LOCAL_DIR"
echo "서버: $SERVER_USER@$SERVER_IP:$PROJECT_DIR"
echo ""

# sshpass 확인
if ! command -v sshpass &> /dev/null; then
    echo "sshpass가 필요합니다. 설치 중..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    else
        apt-get install -y sshpass
    fi
fi

# SSH 명령 함수
ssh_cmd() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"
}

# SCP 명령 함수
scp_cmd() {
    sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no -r "$1" "$SERVER_USER@$SERVER_IP:$2"
}

echo "[1/6] 서버 디렉토리 준비..."
ssh_cmd "mkdir -p $PROJECT_DIR && mkdir -p $PROJECT_DIR/data/converted && mkdir -p $PROJECT_DIR/logs"

echo "[2/6] 프로젝트 파일 전송..."
# 필요한 파일만 전송
scp_cmd "$LOCAL_DIR/src" "$PROJECT_DIR/"
scp_cmd "$LOCAL_DIR/deploy" "$PROJECT_DIR/"
scp_cmd "$LOCAL_DIR/requirements.txt" "$PROJECT_DIR/"
scp_cmd "$LOCAL_DIR/main.py" "$PROJECT_DIR/"

# .env 파일 있으면 전송
if [ -f "$LOCAL_DIR/.env" ]; then
    scp_cmd "$LOCAL_DIR/.env" "$PROJECT_DIR/"
fi

echo "[3/6] 서버 설정 스크립트 실행..."
ssh_cmd "chmod +x $PROJECT_DIR/deploy/setup_server.sh && $PROJECT_DIR/deploy/setup_server.sh"

echo "[4/6] systemd 서비스 설치..."
ssh_cmd "cp $PROJECT_DIR/deploy/strategy-collector.service /etc/systemd/system/"
ssh_cmd "cp $PROJECT_DIR/deploy/strategy-single.service /etc/systemd/system/"
ssh_cmd "cp $PROJECT_DIR/deploy/strategy-collector.timer /etc/systemd/system/"
ssh_cmd "systemctl daemon-reload"

echo "[5/6] 서비스 활성화..."
# 연속 실행 서비스 사용 (타이머 대신)
ssh_cmd "systemctl enable strategy-collector.service"
ssh_cmd "systemctl start strategy-collector.service"

echo "[6/6] 상태 확인..."
ssh_cmd "systemctl status strategy-collector.service --no-pager || true"

echo ""
echo "=========================================="
echo "✅ 배포 완료!"
echo "=========================================="
echo ""
echo "유용한 명령어:"
echo "  로그 확인: ssh $SERVER_USER@$SERVER_IP 'journalctl -u strategy-collector -f'"
echo "  상태 확인: ssh $SERVER_USER@$SERVER_IP 'systemctl status strategy-collector'"
echo "  재시작: ssh $SERVER_USER@$SERVER_IP 'systemctl restart strategy-collector'"
echo "  중지: ssh $SERVER_USER@$SERVER_IP 'systemctl stop strategy-collector'"
echo ""
