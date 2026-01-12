#!/bin/bash
# 로컬 서버 실행 스크립트

export APP_BASE_DIR=/Users/mr.joo/Desktop/전략연구소/strategy-research-lab

echo "🚀 Starting Strategy Research Lab API Server..."
echo "📂 Data directory: $APP_BASE_DIR/data"
echo "🌐 API: http://localhost:8080/api/docs"
echo "📊 Dashboard: http://localhost:8080/"
echo ""

python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8080 --reload
