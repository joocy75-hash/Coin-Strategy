#!/usr/bin/env python3
"""
C등급 전략 분석 스크립트
TradingView 점수 기반으로 C등급(60-69.99점) 전략 추출 및 분석
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path

# 데이터베이스 경로
DB_PATH = "/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db"
OUTPUT_DIR = "/Users/mr.joo/Desktop/전략연구소"

def calculate_tradingview_score(performance_json):
    """
    TradingView 점수 계산
    - Win Rate (30%)
    - Profit Factor (25%)
    - Total Trades (15%)
    - Net Profit (30%)
    """
    try:
        if not performance_json:
            return 0

        perf = json.loads(performance_json) if isinstance(performance_json, str) else performance_json

        # 기본값 설정
        win_rate = perf.get('win_rate', 0)
        profit_factor = perf.get('profit_factor', 0)
        total_trades = perf.get('total_trades', 0)
        net_profit_pct = perf.get('net_profit_pct', 0)

        # 점수 계산 (0-100점)
        win_rate_score = min(win_rate, 100) * 0.30

        # Profit Factor: 1.0 = 0점, 2.0 = 50점, 3.0+ = 100점
        pf_score = min((profit_factor - 1.0) * 50, 100) * 0.25

        # Total Trades: 100 = 50점, 200+ = 100점
        trades_score = min(total_trades / 2, 100) * 0.15

        # Net Profit: 100% = 50점, 200%+ = 100점
        profit_score = min(net_profit_pct / 2, 100) * 0.30

        total_score = win_rate_score + pf_score + trades_score + profit_score

        return round(total_score, 2)

    except Exception as e:
        print(f"Score calculation error: {e}")
        return 0

def get_c_grade_strategies():
    """C등급 전략 조회 (60-69.99점)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT script_id, title, author, pine_code, performance_json, analysis_json, script_url
        FROM strategies
    """)

    strategies = []
    for row in cursor.fetchall():
        script_id, title, author, pine_code, performance_json, analysis_json, script_url = row

        score = calculate_tradingview_score(performance_json)

        # C등급: 60-69.99점
        if 60 <= score < 70:
            perf = json.loads(performance_json) if performance_json else {}
            analysis = json.loads(analysis_json) if analysis_json else {}

            strategies.append({
                'script_id': script_id,
                'title': title,
                'author': author,
                'score': score,
                'win_rate': perf.get('win_rate', 0),
                'profit_factor': perf.get('profit_factor', 0),
                'total_trades': perf.get('total_trades', 0),
                'net_profit_pct': perf.get('net_profit_pct', 0),
                'max_drawdown': perf.get('max_drawdown', 0),
                'sharpe_ratio': perf.get('sharpe_ratio', 0),
                'pine_code': pine_code,
                'script_url': script_url,
                'has_stop_loss': 'stop' in (pine_code or '').lower(),
                'has_take_profit': 'take' in (pine_code or '').lower() or 'tp' in (pine_code or '').lower(),
                'has_trailing_stop': 'trail' in (pine_code or '').lower(),
            })

    conn.close()

    return sorted(strategies, key=lambda x: x['score'], reverse=True)

def main():
    print("=" * 80)
    print("C등급 전략 분석 시작")
    print("=" * 80)

    strategies = get_c_grade_strategies()

    print(f"\n총 C등급 전략: {len(strategies)}개")

    if not strategies:
        print("C등급 전략이 없습니다.")
        return

    # 데이터프레임 생성
    df = pd.DataFrame(strategies)

    # CSV 저장
    csv_path = Path(OUTPUT_DIR) / "c_grade_strategies.csv"
    df[['script_id', 'title', 'author', 'score', 'win_rate', 'profit_factor',
        'total_trades', 'net_profit_pct', 'max_drawdown', 'sharpe_ratio',
        'has_stop_loss', 'has_take_profit', 'has_trailing_stop']].to_csv(csv_path, index=False)

    print(f"\nCSV 저장: {csv_path}")

    # Top 5 C등급 전략
    print("\n" + "=" * 80)
    print("Top 5 C등급 전략")
    print("=" * 80)

    for i, strategy in enumerate(strategies[:5], 1):
        print(f"\n{i}. {strategy['title']}")
        print(f"   점수: {strategy['score']}")
        print(f"   승률: {strategy['win_rate']:.1f}%")
        print(f"   Profit Factor: {strategy['profit_factor']:.2f}")
        print(f"   총 거래: {strategy['total_trades']}")
        print(f"   순수익: {strategy['net_profit_pct']:.1f}%")
        print(f"   Stop Loss: {'✓' if strategy['has_stop_loss'] else '✗'}")
        print(f"   Take Profit: {'✓' if strategy['has_take_profit'] else '✗'}")
        print(f"   Trailing Stop: {'✓' if strategy['has_trailing_stop'] else '✗'}")

    # 리스크 관리 통계
    print("\n" + "=" * 80)
    print("리스크 관리 현황")
    print("=" * 80)

    stop_loss_count = sum(1 for s in strategies if s['has_stop_loss'])
    take_profit_count = sum(1 for s in strategies if s['has_take_profit'])
    trailing_stop_count = sum(1 for s in strategies if s['has_trailing_stop'])

    print(f"Stop Loss 사용: {stop_loss_count}/{len(strategies)} ({stop_loss_count/len(strategies)*100:.1f}%)")
    print(f"Take Profit 사용: {take_profit_count}/{len(strategies)} ({take_profit_count/len(strategies)*100:.1f}%)")
    print(f"Trailing Stop 사용: {trailing_stop_count}/{len(strategies)} ({trailing_stop_count/len(strategies)*100:.1f}%)")

    # Pine Script 코드 저장 (Top 5)
    pine_dir = Path(OUTPUT_DIR) / "c_grade_pine_scripts"
    pine_dir.mkdir(exist_ok=True)

    for i, strategy in enumerate(strategies[:5], 1):
        if strategy['pine_code']:
            pine_file = pine_dir / f"{i}_{strategy['script_id']}.pine"
            with open(pine_file, 'w', encoding='utf-8') as f:
                f.write(strategy['pine_code'])
            print(f"\nPine Script 저장: {pine_file}")

    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    main()
