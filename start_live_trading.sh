#!/bin/bash

echo "=============================================="
echo "🚀 Freqtrade 실전매매 시작"
echo "=============================================="
echo ""
echo "⚙️  설정 정보:"
echo "   전략: SimpleAdaptiveStrategy"
echo "   거래소: Bitget"
echo "   거래쌍: BTC/USDT, ETH/USDT, SOL/USDT"
echo "   거래당 금액: 20 USDT"
echo "   최대 동시 거래: 3개"
echo ""
echo "🌐 모니터링:"
echo "   API: http://localhost:8081"
echo "   사용자명: admin"
echo "   비밀번호: admin"
echo ""
echo "⚠️  주의: 실제 자금이 사용됩니다!"
echo ""
read -p "계속하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 취소되었습니다."
    exit 1
fi

echo ""
echo "🚀 봇 시작 중..."
echo ""

# Freqtrade 실행
freqtrade trade --config freqtrade/config.json --strategy SimpleAdaptiveStrategy
