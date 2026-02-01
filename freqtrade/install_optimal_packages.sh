#!/bin/bash
# Freqtrade 최적 패키지 설치 스크립트

set -e

echo "🚀 Freqtrade 최적 패키지 설치 시작..."
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 현재 디렉토리 확인
if [ ! -f "config.json" ]; then
    echo -e "${RED}❌ 오류: freqtrade 디렉토리에서 실행해주세요${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 설치할 패키지 카테고리:${NC}"
echo ""
echo "1. 필수 패키지 (TA-Lib)"
echo "2. 머신러닝 기본 (LightGBM, XGBoost, CatBoost)"
echo "3. 강화학습 (PyTorch, Stable-Baselines3) - 약 2GB"
echo "4. 최적화 및 시각화 (Optuna, TensorBoard, SHAP)"
echo "5. 전체 설치"
echo ""
read -p "선택 (1-5): " choice

case $choice in
    1)
        echo -e "${GREEN}📦 필수 패키지 설치 중...${NC}"
        pip3 install TA-Lib
        ;;
    2)
        echo -e "${GREEN}📦 머신러닝 기본 패키지 설치 중...${NC}"
        pip3 install lightgbm xgboost catboost
        ;;
    3)
        echo -e "${YELLOW}⚠️  경고: PyTorch는 약 2GB 용량입니다${NC}"
        read -p "계속하시겠습니까? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            echo -e "${GREEN}📦 강화학습 패키지 설치 중...${NC}"
            pip3 install torch torchvision stable-baselines3 gymnasium
        fi
        ;;
    4)
        echo -e "${GREEN}📦 최적화 및 시각화 패키지 설치 중...${NC}"
        pip3 install optuna tensorboard shap plotly scikit-learn pandas-ta
        ;;
    5)
        echo -e "${GREEN}📦 전체 패키지 설치 중...${NC}"
        echo -e "${YELLOW}⚠️  경고: 전체 설치는 약 3GB 이상 소요됩니다${NC}"
        read -p "계속하시겠습니까? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            pip3 install -r requirements_optimal.txt
        fi
        ;;
    *)
        echo -e "${RED}❌ 잘못된 선택입니다${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ 설치 완료!${NC}"
echo ""
echo -e "${YELLOW}📝 다음 단계:${NC}"
echo "1. Freqtrade 설정 확인: freqtrade show-config"
echo "2. 전략 백테스트: freqtrade backtesting --strategy YourStrategy"
echo "3. 웹 UI 시작: freqtrade webserver"
echo ""
