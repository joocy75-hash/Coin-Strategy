#!/bin/bash
#===============================================================================
# 전략연구소 통합 서비스 실행 스크립트
#
# 이 스크립트는 통합 대시보드와 관련된 모든 서비스를 한 번에 실행합니다.
#
# 서비스 목록:
#   - 통합 대시보드 API (8080)
#   - Freqtrade 트레이딩 봇 (8081)
#   - Freqtrade 백테스트 서버 (8082)
#
# 사용법: ./scripts/start_all_services.sh
#===============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   전략연구소 통합 서비스 시작${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# PID 파일 디렉토리
PID_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PID_DIR"

# 함수: 포트 사용 중인지 확인
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # 포트 사용 중
    else
        return 1  # 포트 사용 안 함
    fi
}

# 함수: 서비스 시작
start_service() {
    local name=$1
    local port=$2
    local command=$3
    local pid_file="$PID_DIR/${name}.pid"

    echo -e "${YELLOW}▶ $name 시작 중 (포트: $port)...${NC}"

    if check_port $port; then
        echo -e "${GREEN}  ✓ $name 이미 실행 중 (포트 $port)${NC}"
        return 0
    fi

    # 백그라운드로 실행
    eval "$command" > "$PROJECT_ROOT/logs/${name}.log" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    # 서비스 시작 대기
    sleep 2

    if check_port $port; then
        echo -e "${GREEN}  ✓ $name 시작 완료 (PID: $pid)${NC}"
    else
        echo -e "${RED}  ✗ $name 시작 실패${NC}"
        return 1
    fi
}

# 로그 디렉토리 생성
mkdir -p "$PROJECT_ROOT/logs"

echo -e "${YELLOW}[1/3] 통합 대시보드 API 서버 (8080)${NC}"
start_service "dashboard" 8080 "cd $PROJECT_ROOT/strategy-research-lab && APP_BASE_DIR=\$(pwd) python api/server.py"

echo ""
echo -e "${YELLOW}[2/3] Freqtrade 트레이딩 봇 (8081)${NC}"
start_service "freqtrade_trade" 8081 "cd $PROJECT_ROOT/freqtrade && freqtrade trade --config config.json --strategy SampleStrategy"

echo ""
echo -e "${YELLOW}[3/3] Freqtrade 백테스트 서버 (8082)${NC}"
start_service "freqtrade_backtest" 8082 "cd $PROJECT_ROOT/freqtrade && freqtrade webserver --config config_backtest_server.json"

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}   모든 서비스 시작 완료!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "접속 URL:"
echo -e "  ${GREEN}• 통합 대시보드:${NC}     http://localhost:8080"
echo -e "  ${GREEN}• FreqControl:${NC}       http://localhost:8081"
echo -e "  ${GREEN}• FreqBacktest:${NC}      http://localhost:8082"
echo ""
echo -e "${YELLOW}로그인 정보: admin / admin${NC}"
echo ""
echo -e "서비스 중지: ${BLUE}./scripts/stop_all_services.sh${NC}"
