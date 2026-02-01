#!/bin/bash
#===============================================================================
# 전략연구소 통합 서비스 종료 스크립트
#
# 이 스크립트는 통합 대시보드와 관련된 모든 서비스를 종료합니다.
#
# 사용법: ./scripts/stop_all_services.sh
#===============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.pids"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   전략연구소 통합 서비스 종료${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 함수: 포트로 프로세스 종료
kill_by_port() {
    local port=$1
    local name=$2
    local pids=$(lsof -ti :$port 2>/dev/null)

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}▶ $name 종료 중 (포트: $port)...${NC}"
        echo $pids | xargs kill -9 2>/dev/null
        echo -e "${GREEN}  ✓ $name 종료 완료${NC}"
    else
        echo -e "${GREEN}  - $name 실행 중 아님${NC}"
    fi
}

kill_by_port 8080 "통합 대시보드"
kill_by_port 8081 "Freqtrade 트레이딩"
kill_by_port 8082 "Freqtrade 백테스트"

# PID 파일 정리
rm -f "$PID_DIR"/*.pid 2>/dev/null

echo ""
echo -e "${GREEN}모든 서비스가 종료되었습니다.${NC}"
