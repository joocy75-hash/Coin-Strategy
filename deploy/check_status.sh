#!/bin/bash
# 서버 상태 확인 스크립트

SERVER_IP="141.164.55.245"
SERVER_USER="root"
SERVER_PASS="Wnrkswl!23"

ssh_cmd() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"
}

echo "=========================================="
echo "Strategy Research Lab - 상태 확인"
echo "=========================================="

echo ""
echo "📊 서비스 상태:"
ssh_cmd "systemctl status strategy-collector --no-pager" 2>/dev/null || echo "서비스 미실행"

echo ""
echo "📁 데이터베이스 상태:"
ssh_cmd "ls -lh /opt/strategy-research-lab/data/strategies.db 2>/dev/null || echo '데이터베이스 없음'"

echo ""
echo "📈 수집된 전략 수:"
ssh_cmd "cd /opt/strategy-research-lab && source venv/bin/activate && python3 -c \"
import sqlite3
try:
    conn = sqlite3.connect('data/strategies.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM strategies')
    print(f'총 전략 수: {cur.fetchone()[0]}개')
    cur.execute('SELECT COUNT(*) FROM strategies WHERE converted_path IS NOT NULL')
    print(f'변환된 전략: {cur.fetchone()[0]}개')
    conn.close()
except Exception as e:
    print(f'조회 실패: {e}')
\" 2>/dev/null" || echo "조회 실패"

echo ""
echo "📝 최근 로그 (10줄):"
ssh_cmd "journalctl -u strategy-collector --no-pager -n 10" 2>/dev/null || echo "로그 없음"

echo ""
echo "💾 디스크 사용량:"
ssh_cmd "df -h / | tail -1"

echo ""
echo "🧠 메모리 사용량:"
ssh_cmd "free -h | grep Mem"
