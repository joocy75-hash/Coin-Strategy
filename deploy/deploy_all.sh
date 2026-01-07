#!/bin/bash

# 통합 관리 스크립트 (Group A, B, C & Proxy)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 그룹별 경로 정의
PROXY_PATH="/root/proxy"
GROUP_A_PATH="/root/service_a"
GROUP_B_PATH="/root/service_b"
GROUP_C_PATH="/root/service_c/strategy-research-lab"

function usage() {
    echo -e "${YELLOW}Usage: $0 {proxy|group_a|group_b|group_c} {up|down|restart|logs|ps}${NC}"
    echo -e "Example: $0 group_c up"
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

TARGET=$1
ACTION=$2

case $TARGET in
    proxy)   BASE_PATH=$PROXY_PATH ;;
    group_a) BASE_PATH=$GROUP_A_PATH ;;
    group_b) BASE_PATH=$GROUP_B_PATH ;;
    group_c) BASE_PATH=$GROUP_C_PATH ;;
    *) echo -e "${RED}Unknown target: $TARGET${NC}"; usage ;;
esac

if [ ! -d "$BASE_PATH" ]; then
    echo -e "${RED}Directory not found: $BASE_PATH${NC}"
    exit 1
fi

cd $BASE_PATH

case $ACTION in
    up)
        echo -e "${GREEN}Starting $TARGET...${NC}"
        docker compose up -d
        ;;
    down)
        echo -e "${YELLOW}Stopping $TARGET...${NC}"
        docker compose down
        ;;
    restart)
        echo -e "${GREEN}Restarting $TARGET...${NC}"
        docker compose restart
        ;;
    logs)
        docker compose logs -f --tail=100
        ;;
    ps)
        docker compose ps
        ;;
    *)
        echo -e "${RED}Unknown action: $ACTION${NC}"
        usage
        ;;
esac
