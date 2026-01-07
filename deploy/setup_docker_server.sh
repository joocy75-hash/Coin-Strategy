#!/bin/bash
# Docker 기반 서버 초기 설정 스크립트

set -e

echo "=========================================="
echo "Strategy Research Lab - Docker 서버 설정 시작"
echo "=========================================="

# 1. 시스템 패키지 업데이트
echo "[1/5] 시스템 패키지 업데이트..."
apt-get update -y
apt-get install -y git wget curl rsync sshpass

# 2. Docker 및 Docker Compose 설치 확인
if ! command -v docker &> /dev/null; then
    echo "[2/5] Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "[2/5] Docker가 이미 설치되어 있습니다."
fi

# 3. 공통 네트워크 생성
echo "[3/5] 공통 네트워크(proxy-net) 생성..."
docker network create proxy-net || true

# 4. 프록시 디렉토리 및 설정 파일 생성
echo "[4/5] 프록시 설정 중..."
mkdir -p /root/proxy/conf.d /root/proxy/certs /root/proxy/logs
mkdir -p /root/service_c/strategy-research-lab

# 5. 관리 스크립트 권한 부여
echo "[5/5] 관리 스크립트 설정..."
if [ -f "/root/deploy.sh" ]; then
    chmod +x /root/deploy.sh
fi

echo "=========================================="
echo "✅ Docker 서버 설정 완료!"
echo "=========================================="
