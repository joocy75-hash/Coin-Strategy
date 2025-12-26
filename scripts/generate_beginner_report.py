#!/usr/bin/env python3
"""
초보자 친화적 HTML 리포트 생성 스크립트

전략 연구소 데이터베이스에서 데이터를 조회하여
초보자도 이해할 수 있는 HTML 리포트를 생성합니다.

개선된 기능:
- 카드뷰/테이블뷰 토글
- 용어 설명 툴팁 (리페인팅, 오버피팅, 백테스트)
- 사용 권장 여부 배지
- 백테스트 성과 시각화
- 초보자용 전략 설명
- XSS 방지를 위한 안전한 DOM 조작
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from jinja2 import Template
from src.storage import StrategyDatabase

logger = logging.getLogger(__name__)


# =====================================================
# 헬퍼 함수들
# =====================================================

def get_recommendation_type(score: float, grade: str, repainting_score: float, overfitting_score: float) -> str:
    """사용 권장 여부 결정"""
    if grade in ['A', 'B'] and repainting_score >= 70 and overfitting_score <= 40:
        return 'recommended'
    elif grade in ['D', 'F'] or repainting_score < 50 or overfitting_score > 60:
        return 'not_recommended'
    else:
        return 'review_needed'


def get_recommendation_icon(rec_type: str) -> str:
    """권장 아이콘"""
    return {'recommended': '✅', 'review_needed': '⚠️', 'not_recommended': '❌'}.get(rec_type, '⚠️')


def get_recommendation_title(rec_type: str) -> str:
    """권장 타이틀"""
    return {'recommended': '사용 권장', 'review_needed': '검토 필요', 'not_recommended': '사용 비권장'}.get(rec_type, '검토 필요')


def get_recommendation_reason(score: float, grade: str, rec_type: str) -> str:
    """권장 이유 생성"""
    if rec_type == 'recommended':
        return f"총점 {score:.1f}점으로 양호하며, 리페인팅/오버피팅 위험이 낮습니다. 실제 사용 전 충분한 테스트를 권장합니다."
    elif rec_type == 'not_recommended':
        return f"분석 결과 위험 요소가 발견되었습니다. 리페인팅이나 오버피팅 가능성이 높아 실제 투자에 사용하지 않는 것을 권장합니다."
    else:
        return f"총점 {score:.1f}점으로 사용 가능하나, 일부 주의사항이 있습니다. 실거래 전 충분한 검토가 필요합니다."


def get_risk_level(repainting_score: float, overfitting_score: float) -> str:
    """위험 수준 결정"""
    if repainting_score < 50 or overfitting_score > 70:
        return 'high'
    elif repainting_score < 70 or overfitting_score > 50:
        return 'medium'
    else:
        return 'low'


def get_risk_message(repainting_score: float, overfitting_score: float) -> str:
    """위험 메시지 생성"""
    messages = []
    if repainting_score < 60:
        messages.append('리페인팅 위험이 있습니다')
    if overfitting_score > 50:
        messages.append('오버피팅 가능성이 있습니다')
    return ', '.join(messages) if messages else ''


# =====================================================
# HTML 템플릿 (안전한 DOM 조작 사용)
# =====================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Strategy Research Lab - 초보자용 리포트</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-red: #f85149;
            --accent-purple: #bc8cff;
            --accent-orange: #f0883e;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            background: var(--bg-secondary);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow);
        }
        h1 { font-size: 2rem; font-weight: 600; margin-bottom: 10px; color: var(--accent-blue); }
        .subtitle { color: var(--text-secondary); font-size: 0.95rem; }
        .beginner-guide {
            background: linear-gradient(135deg, #1a1f35 0%, #161b22 100%);
            border: 1px solid var(--accent-blue);
            border-radius: 12px;
            padding: 20px 25px;
            margin-bottom: 25px;
            position: relative;
        }
        .beginner-guide::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
        }
        .beginner-guide h3 { color: var(--accent-blue); margin-bottom: 12px; font-size: 1.1rem; }
        .beginner-guide p { color: var(--text-secondary); font-size: 0.9rem; line-height: 1.7; }
        .highlight { color: var(--accent-yellow); font-weight: 600; }
        .tooltip-term {
            position: relative;
            cursor: help;
            border-bottom: 1px dotted var(--accent-blue);
            color: var(--accent-blue);
        }
        .tooltip-term:hover .tooltip-content { visibility: visible; opacity: 1; transform: translateY(0); }
        .tooltip-content {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(10px);
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 16px;
            width: 280px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            transition: all 0.2s ease;
            font-size: 0.85rem;
            line-height: 1.5;
            color: var(--text-primary);
            text-align: left;
        }
        .tooltip-content::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 8px solid transparent;
            border-top-color: var(--bg-tertiary);
        }
        .tooltip-title { font-weight: 600; color: var(--accent-blue); margin-bottom: 6px; display: block; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: var(--bg-secondary); padding: 20px; border-radius: 8px; border: 1px solid var(--border-color); }
        .stat-label { color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 5px; }
        .stat-value { font-size: 1.8rem; font-weight: 700; color: var(--accent-blue); }
        .filters {
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }
        .filter-group { display: flex; align-items: center; gap: 8px; }
        label { color: var(--text-secondary); font-size: 0.9rem; }
        input, select {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }
        input:focus, select:focus { outline: none; border-color: var(--accent-blue); }
        .view-toggle { display: flex; gap: 10px; margin-bottom: 20px; }
        .view-btn {
            padding: 8px 16px;
            border: 1px solid var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .view-btn.active { background: var(--accent-blue); color: #000; border-color: var(--accent-blue); }
        .view-btn:hover:not(.active) { border-color: var(--accent-blue); color: var(--accent-blue); }
        .strategy-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .strategy-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .strategy-card:hover { border-color: var(--accent-blue); transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3); }
        .strategy-card-header { padding: 20px; border-bottom: 1px solid var(--border-color); position: relative; }
        .strategy-card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; color: var(--text-primary); padding-right: 80px; }
        .strategy-card-author { color: var(--text-secondary); font-size: 0.85rem; }
        .recommendation-badge {
            position: absolute;
            top: 15px;
            right: 15px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge-recommended { background: rgba(63, 185, 80, 0.15); color: var(--accent-green); border: 1px solid rgba(63, 185, 80, 0.3); }
        .badge-caution { background: rgba(210, 153, 34, 0.15); color: var(--accent-yellow); border: 1px solid rgba(210, 153, 34, 0.3); }
        .badge-not-recommended { background: rgba(248, 81, 73, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 81, 73, 0.3); }
        .strategy-summary { padding: 15px 20px; background: var(--bg-tertiary); border-bottom: 1px solid var(--border-color); }
        .summary-text { font-size: 0.95rem; color: var(--text-primary); line-height: 1.6; }
        .backtest-metrics { padding: 15px 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; border-bottom: 1px solid var(--border-color); }
        .metric-item { text-align: center; }
        .metric-label { font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 4px; display: block; }
        .metric-value { font-size: 1.1rem; font-weight: 700; }
        .metric-value.positive { color: var(--accent-green); }
        .metric-value.negative { color: var(--accent-red); }
        .metric-value.neutral { color: var(--text-primary); }
        .no-backtest { padding: 15px 20px; text-align: center; color: var(--text-secondary); font-size: 0.9rem; border-bottom: 1px solid var(--border-color); background: rgba(139, 148, 158, 0.05); }
        .risk-warning-box { padding: 12px 16px; margin: 15px; border-radius: 8px; font-size: 0.85rem; display: flex; align-items: flex-start; gap: 10px; }
        .risk-warning-box.high { background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3); color: var(--accent-red); }
        .risk-warning-box.medium { background: rgba(210, 153, 34, 0.1); border: 1px solid rgba(210, 153, 34, 0.3); color: var(--accent-yellow); }
        .strategy-card-footer { padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .card-stats { display: flex; gap: 15px; font-size: 0.85rem; color: var(--text-secondary); }
        .card-stat { display: flex; align-items: center; gap: 5px; }
        .table-container { background: var(--bg-secondary); border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color); margin-bottom: 30px; display: none; }
        .table-container.active { display: block; }
        .strategy-cards-grid.active { display: grid; }
        .strategy-cards-grid:not(.active) { display: none; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: var(--bg-tertiary); }
        th { padding: 15px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; }
        th:hover { color: var(--accent-blue); }
        tbody tr { border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.2s; }
        tbody tr:hover { background: var(--bg-tertiary); }
        td { padding: 12px 15px; font-size: 0.9rem; }
        .grade { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }
        .grade-A { background: var(--accent-green); color: #000; }
        .grade-B { background: var(--accent-blue); color: #000; }
        .grade-C { background: var(--accent-yellow); color: #000; }
        .grade-D { background: var(--accent-orange); color: #000; }
        .grade-F { background: var(--accent-red); color: #fff; }
        .risk-indicator { display: flex; gap: 8px; align-items: center; font-size: 0.85rem; }
        .risk-bar { height: 6px; width: 60px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; }
        .risk-fill { height: 100%; transition: width 0.3s; }
        .risk-low { background: var(--accent-green); }
        .risk-medium { background: var(--accent-yellow); }
        .risk-high { background: var(--accent-red); }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.85); z-index: 1000; overflow-y: auto; padding: 20px; }
        .modal.active { display: flex; align-items: flex-start; justify-content: center; }
        .modal-content { background: var(--bg-secondary); border-radius: 16px; border: 1px solid var(--border-color); max-width: 900px; width: 100%; margin: 40px 0; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5); }
        .modal-header { padding: 25px 30px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: flex-start; }
        .modal-title { font-size: 1.4rem; font-weight: 600; margin-bottom: 8px; }
        .modal-meta { color: var(--text-secondary); font-size: 0.9rem; }
        .close-modal { background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer; padding: 0; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 8px; transition: all 0.2s; }
        .close-modal:hover { background: var(--bg-tertiary); color: var(--text-primary); }
        .modal-body { padding: 25px 30px; max-height: 70vh; overflow-y: auto; }
        .detail-section { margin-bottom: 25px; }
        .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 15px; color: var(--accent-blue); }
        .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .detail-item { background: var(--bg-tertiary); padding: 15px; border-radius: 6px; }
        .detail-label { color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 5px; }
        .detail-value { font-size: 1.1rem; font-weight: 600; }
        .recommendation-box { padding: 20px; border-radius: 12px; margin-bottom: 25px; }
        .recommendation-box.recommended { background: rgba(63, 185, 80, 0.1); border: 1px solid rgba(63, 185, 80, 0.3); }
        .recommendation-box.caution { background: rgba(210, 153, 34, 0.1); border: 1px solid rgba(210, 153, 34, 0.3); }
        .recommendation-box.not-recommended { background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3); }
        .recommendation-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
        .recommendation-header .icon { font-size: 1.5rem; }
        .recommendation-header h4 { font-size: 1.1rem; font-weight: 600; }
        .recommendation-box.recommended h4 { color: var(--accent-green); }
        .recommendation-box.caution h4 { color: var(--accent-yellow); }
        .recommendation-box.not-recommended h4 { color: var(--accent-red); }
        .recommendation-reason { font-size: 0.95rem; color: var(--text-primary); line-height: 1.6; }
        .code-block { background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; padding: 15px; overflow-x: auto; }
        .code-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .code-title { font-size: 0.9rem; color: var(--text-secondary); }
        .copy-btn { background: var(--accent-blue); border: none; color: #000; padding: 6px 12px; border-radius: 4px; font-size: 0.85rem; cursor: pointer; font-weight: 600; transition: all 0.2s; }
        .copy-btn:hover { opacity: 0.8; }
        .copy-btn.copied { background: var(--accent-green); }
        pre { margin: 0; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 0.85rem; line-height: 1.5; color: var(--text-primary); white-space: pre-wrap; word-wrap: break-word; }
        .analysis-list { list-style: none; padding: 0; }
        .analysis-list li { padding: 8px 12px; margin-bottom: 6px; background: var(--bg-tertiary); border-radius: 4px; border-left: 3px solid var(--accent-blue); }
        .analysis-list.issues li { border-left-color: var(--accent-red); }
        .footer { text-align: center; padding: 30px; color: var(--text-secondary); font-size: 0.9rem; border-top: 1px solid var(--border-color); margin-top: 40px; }
        @media (max-width: 768px) {
            .strategy-cards-grid { grid-template-columns: 1fr; }
            .backtest-metrics { grid-template-columns: 1fr; }
            .tooltip-content { width: 220px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TradingView Strategy Research Lab</h1>
            <p class="subtitle">생성일: {{ generated_at }} | 총 {{ stats.total_strategies }}개 전략</p>
        </header>

        <div class="beginner-guide">
            <h3>📚 초보자를 위한 안내</h3>
            <p>
                이 리포트는 TradingView 전략들의 <span class="highlight">신뢰성과 안전성</span>을 분석한 결과입니다.
                <span class="tooltip-term">리페인팅<span class="tooltip-content"><span class="tooltip-title">리페인팅이란?</span>과거 차트에서는 좋아 보이지만, 실제 매매 시점에는 신호가 바뀌는 현상입니다.</span></span>과
                <span class="tooltip-term">오버피팅<span class="tooltip-content"><span class="tooltip-title">오버피팅이란?</span>과거 데이터에만 지나치게 맞춰진 전략입니다. 새로운 시장에서는 성과가 나쁠 수 있습니다.</span></span>
                위험을 확인하고,
                <span class="tooltip-term">백테스트<span class="tooltip-content"><span class="tooltip-title">백테스트란?</span>과거 데이터로 전략을 테스트하는 것입니다. 과거 성과가 미래를 보장하지는 않습니다.</span></span>
                결과를 초보자 눈높이에서 해석해 드립니다.
            </p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">총 전략 수</div>
                <div class="stat-value">{{ stats.total_strategies }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">분석 완료</div>
                <div class="stat-value">{{ stats.analyzed_count }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">권장 전략</div>
                <div class="stat-value" style="color: var(--accent-green);">{{ stats.passed_count }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">평균 점수</div>
                <div class="stat-value" style="color: var(--accent-purple);">{{ "%.1f"|format(stats.avg_score) }}</div>
            </div>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label>검색:</label>
                <input type="text" id="searchInput" placeholder="전략명 또는 작성자...">
            </div>
            <div class="filter-group">
                <label>등급:</label>
                <select id="gradeFilter">
                    <option value="">전체</option>
                    <option value="A">A (매우 우수)</option>
                    <option value="B">B (우수)</option>
                    <option value="C">C (보통)</option>
                    <option value="D">D (미흡)</option>
                    <option value="F">F (부적합)</option>
                </select>
            </div>
            <div class="filter-group">
                <label>권장여부:</label>
                <select id="recommendFilter">
                    <option value="">전체</option>
                    <option value="recommended">✅ 권장</option>
                    <option value="review_needed">⚠️ 검토필요</option>
                    <option value="not_recommended">❌ 비권장</option>
                </select>
            </div>
            <div class="filter-group">
                <label>최소 점수:</label>
                <input type="number" id="minScore" min="0" max="100" placeholder="0">
            </div>
        </div>

        <div class="view-toggle">
            <button class="view-btn active" data-view="card" onclick="toggleView('card')">📋 카드 뷰</button>
            <button class="view-btn" data-view="table" onclick="toggleView('table')">📊 테이블 뷰</button>
        </div>

        <div class="strategy-cards-grid active" id="cardView">
            {% for strategy in strategies %}
            <div class="strategy-card"
                 data-id="{{ strategy.script_id }}"
                 data-title="{{ strategy.title|lower }}"
                 data-author="{{ strategy.author|lower }}"
                 data-grade="{{ strategy.grade }}"
                 data-score="{{ strategy.score }}"
                 data-recommend="{{ strategy.recommendation_type }}"
                 onclick="showDetailFromCard('{{ strategy.script_id }}')">
                <div class="strategy-card-header">
                    <div class="strategy-card-title">{{ strategy.title }}</div>
                    <div class="strategy-card-author">by {{ strategy.author }}</div>
                    {% if strategy.recommendation_type == 'recommended' %}
                    <div class="recommendation-badge badge-recommended">✅ 권장</div>
                    {% elif strategy.recommendation_type == 'review_needed' %}
                    <div class="recommendation-badge badge-caution">⚠️ 검토</div>
                    {% else %}
                    <div class="recommendation-badge badge-not-recommended">❌ 비권장</div>
                    {% endif %}
                </div>
                {% if strategy.summary %}
                <div class="strategy-summary">
                    <div class="summary-text">{{ strategy.summary }}</div>
                </div>
                {% endif %}
                {% if strategy.has_performance %}
                <div class="backtest-metrics">
                    <div class="metric-item">
                        <span class="metric-label">수익률</span>
                        <span class="metric-value {{ 'positive' if strategy.net_profit_pct > 0 else 'negative' if strategy.net_profit_pct < 0 else 'neutral' }}">{{ "%.1f"|format(strategy.net_profit_pct) }}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">최대손실</span>
                        <span class="metric-value negative">{{ "%.1f"|format(strategy.max_drawdown_pct) }}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">승률</span>
                        <span class="metric-value {{ 'positive' if strategy.win_rate > 50 else 'neutral' }}">{{ "%.1f"|format(strategy.win_rate) }}%</span>
                    </div>
                </div>
                {% else %}
                <div class="no-backtest">📊 백테스트 데이터 없음</div>
                {% endif %}
                {% if strategy.risk_level in ['high', 'critical'] %}
                <div class="risk-warning-box high">
                    <span>⚠️</span>
                    <span>{{ strategy.risk_message }}</span>
                </div>
                {% elif strategy.risk_level == 'medium' and strategy.risk_message %}
                <div class="risk-warning-box medium">
                    <span>📌</span>
                    <span>{{ strategy.risk_message }}</span>
                </div>
                {% endif %}
                <div class="strategy-card-footer">
                    <span class="grade grade-{{ strategy.grade }}">{{ strategy.grade }}등급</span>
                    <div class="card-stats">
                        <span class="card-stat">❤️ {{ strategy.likes }}</span>
                        <span class="card-stat">📊 {{ "%.0f"|format(strategy.score) }}점</span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="table-container" id="tableView">
            <table id="strategiesTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('title')">전략명</th>
                        <th onclick="sortTable('author')">작성자</th>
                        <th onclick="sortTable('likes')">좋아요</th>
                        <th onclick="sortTable('score')">점수</th>
                        <th onclick="sortTable('grade')">등급</th>
                        <th>권장</th>
                        <th>리페인팅</th>
                        <th>오버피팅</th>
                    </tr>
                </thead>
                <tbody id="strategiesBody">
                    {% for strategy in strategies %}
                    <tr class="strategy-row"
                        data-id="{{ strategy.script_id }}"
                        data-title="{{ strategy.title|lower }}"
                        data-author="{{ strategy.author|lower }}"
                        data-grade="{{ strategy.grade }}"
                        data-score="{{ strategy.score }}"
                        data-recommend="{{ strategy.recommendation_type }}">
                        <td>{{ strategy.title }}</td>
                        <td>{{ strategy.author }}</td>
                        <td>{{ strategy.likes }}</td>
                        <td><strong>{{ "%.1f"|format(strategy.score) }}</strong></td>
                        <td><span class="grade grade-{{ strategy.grade }}">{{ strategy.grade }}</span></td>
                        <td>{{ strategy.recommendation_icon }}</td>
                        <td>
                            <div class="risk-indicator">
                                <div class="risk-bar">
                                    <div class="risk-fill risk-{{ strategy.repainting_risk }}" style="width: {{ strategy.repainting_score }}%;"></div>
                                </div>
                                <span>{{ "%.0f"|format(strategy.repainting_score) }}</span>
                            </div>
                        </td>
                        <td>
                            <div class="risk-indicator">
                                <div class="risk-bar">
                                    <div class="risk-fill risk-{{ strategy.overfitting_risk }}" style="width: {{ strategy.overfitting_score }}%;"></div>
                                </div>
                                <span>{{ "%.0f"|format(strategy.overfitting_score) }}</span>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>TradingView Strategy Research Lab | 초보자를 위한 전략 분석 리포트</p>
            <p style="margin-top: 8px; font-size: 0.8rem;">⚠️ 이 리포트는 참고용이며, 투자 결정에 대한 책임은 본인에게 있습니다.</p>
        </div>
    </div>

    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2 class="modal-title" id="modalTitle"></h2>
                    <div class="modal-meta" id="modalMeta"></div>
                </div>
                <button class="close-modal" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        // 안전한 데이터 - 서버에서 이스케이프된 JSON
        const strategiesData = {{ strategies_json|safe }};
        let currentSort = { column: 'score', ascending: false };
        let currentView = 'card';

        // 안전한 텍스트 이스케이프 함수
        function escapeHtml(text) {
            if (text === null || text === undefined) return '';
            const div = document.createElement('div');
            div.textContent = String(text);
            return div.textContent;
        }

        // 안전한 요소 생성 함수
        function createEl(tag, className, textContent) {
            const el = document.createElement(tag);
            if (className) el.className = className;
            if (textContent !== undefined) el.textContent = textContent;
            return el;
        }

        function toggleView(view) {
            currentView = view;
            document.querySelectorAll('.view-btn').forEach(function(btn) {
                btn.classList.toggle('active', btn.dataset.view === view);
            });
            document.getElementById('cardView').classList.toggle('active', view === 'card');
            document.getElementById('tableView').classList.toggle('active', view === 'table');
        }

        function sortTable(column) {
            currentSort.ascending = currentSort.column === column ? !currentSort.ascending : false;
            currentSort.column = column;
            var rows = Array.from(document.querySelectorAll('.strategy-row'));
            rows.sort(function(a, b) {
                var aVal = a.dataset[column];
                var bVal = b.dataset[column];
                if (column === 'likes' || column === 'score') {
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                }
                if (aVal < bVal) return currentSort.ascending ? -1 : 1;
                if (aVal > bVal) return currentSort.ascending ? 1 : -1;
                return 0;
            });
            var tbody = document.getElementById('strategiesBody');
            rows.forEach(function(row) { tbody.appendChild(row); });
        }

        function applyFilters() {
            var searchTerm = document.getElementById('searchInput').value.toLowerCase();
            var gradeFilter = document.getElementById('gradeFilter').value;
            var recommendFilter = document.getElementById('recommendFilter').value;
            var minScore = parseFloat(document.getElementById('minScore').value) || 0;

            var elements = document.querySelectorAll('.strategy-card, .strategy-row');
            elements.forEach(function(el) {
                var title = el.dataset.title || '';
                var author = el.dataset.author || '';
                var grade = el.dataset.grade || '';
                var recommend = el.dataset.recommend || '';
                var score = parseFloat(el.dataset.score) || 0;

                var matchSearch = !searchTerm || title.indexOf(searchTerm) !== -1 || author.indexOf(searchTerm) !== -1;
                var matchGrade = !gradeFilter || grade === gradeFilter;
                var matchRecommend = !recommendFilter || recommend === recommendFilter;
                var matchScore = score >= minScore;

                el.style.display = matchSearch && matchGrade && matchRecommend && matchScore ? '' : 'none';
            });
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('gradeFilter').addEventListener('change', applyFilters);
        document.getElementById('recommendFilter').addEventListener('change', applyFilters);
        document.getElementById('minScore').addEventListener('input', applyFilters);

        document.querySelectorAll('.strategy-row').forEach(function(row) {
            row.addEventListener('click', function() {
                var strategy = strategiesData.find(function(s) { return s.script_id === row.dataset.id; });
                if (strategy) showDetail(strategy);
            });
        });

        function showDetailFromCard(scriptId) {
            var strategy = strategiesData.find(function(s) { return s.script_id === scriptId; });
            if (strategy) showDetail(strategy);
        }

        function showDetail(strategy) {
            document.getElementById('modalTitle').textContent = escapeHtml(strategy.title);
            document.getElementById('modalMeta').textContent = '작성자: ' + escapeHtml(strategy.author) + ' | 좋아요: ' + strategy.likes + ' | 점수: ' + strategy.score.toFixed(1);

            var bodyEl = document.getElementById('modalBody');
            // 안전하게 자식 요소 제거
            while (bodyEl.firstChild) {
                bodyEl.removeChild(bodyEl.firstChild);
            }

            // 권장사항 박스
            bodyEl.appendChild(createRecommendationBox(strategy));

            // 기본 정보
            bodyEl.appendChild(createDetailSection(strategy));

            // 분석 상세
            if (strategy.analysis) {
                if (strategy.analysis.repainting_analysis) {
                    bodyEl.appendChild(createAnalysisSection('리페인팅 분석', strategy.analysis.repainting_analysis, 'repainting'));
                }
                if (strategy.analysis.overfitting_analysis) {
                    bodyEl.appendChild(createAnalysisSection('오버피팅 분석', strategy.analysis.overfitting_analysis, 'overfitting'));
                }
            }

            // Pine 코드
            if (strategy.pine_code) {
                bodyEl.appendChild(createCodeSection(strategy));
            }

            document.getElementById('detailModal').classList.add('active');
        }

        function createRecommendationBox(strategy) {
            var section = createEl('div', 'recommendation-box');
            var recType = strategy.recommendation_type || 'review_needed';
            var recIcon = strategy.recommendation_icon || '⚠️';
            var recTitle = strategy.recommendation_title || '검토 필요';
            var recReason = strategy.recommendation_reason || getDefaultReason(strategy);

            if (recType === 'recommended') {
                section.classList.add('recommended');
            } else if (recType === 'not_recommended') {
                section.classList.add('not-recommended');
            } else {
                section.classList.add('caution');
            }

            var header = createEl('div', 'recommendation-header');
            var iconSpan = createEl('span', 'icon', recIcon);
            var titleEl = createEl('h4', '', recTitle);
            header.appendChild(iconSpan);
            header.appendChild(titleEl);

            var reasonEl = createEl('p', 'recommendation-reason', recReason);

            section.appendChild(header);
            section.appendChild(reasonEl);
            return section;
        }

        function getDefaultReason(strategy) {
            var score = strategy.score || 0;
            var grade = strategy.grade || 'F';
            if (grade === 'A' || score >= 80) return '분석 결과 리페인팅과 오버피팅 위험이 낮고 품질이 우수합니다.';
            if (grade === 'B' || score >= 65) return '전반적으로 양호하나 일부 주의가 필요합니다.';
            if (grade === 'C' || score >= 50) return '몇 가지 위험 요소가 발견되었습니다. 주의가 필요합니다.';
            return '심각한 위험 요소가 발견되었습니다. 사용을 권장하지 않습니다.';
        }

        function createDetailSection(strategy) {
            var section = createEl('div', 'detail-section');
            var title = createEl('h3', 'section-title', '기본 정보');
            section.appendChild(title);

            var grid = createEl('div', 'detail-grid');

            // 등급
            var item1 = createEl('div', 'detail-item');
            var label1 = createEl('div', 'detail-label', '등급');
            var value1 = createEl('div', 'detail-value');
            var gradeBadge = createEl('span', 'grade grade-' + strategy.grade, strategy.grade);
            value1.appendChild(gradeBadge);
            item1.appendChild(label1);
            item1.appendChild(value1);
            grid.appendChild(item1);

            // 총점
            var item2 = createEl('div', 'detail-item');
            var label2 = createEl('div', 'detail-label', '총점');
            var value2 = createEl('div', 'detail-value', strategy.score.toFixed(1) + '점');
            item2.appendChild(label2);
            item2.appendChild(value2);
            grid.appendChild(item2);

            // 리페인팅 점수
            var item3 = createEl('div', 'detail-item');
            var label3 = createEl('div', 'detail-label', '리페인팅 점수');
            var value3 = createEl('div', 'detail-value', strategy.repainting_score.toFixed(1) + ' (높을수록 안전)');
            item3.appendChild(label3);
            item3.appendChild(value3);
            grid.appendChild(item3);

            // 오버피팅 점수
            var item4 = createEl('div', 'detail-item');
            var label4 = createEl('div', 'detail-label', '오버피팅 점수');
            var value4 = createEl('div', 'detail-value', strategy.overfitting_score.toFixed(1) + ' (낮을수록 안전)');
            item4.appendChild(label4);
            item4.appendChild(value4);
            grid.appendChild(item4);

            section.appendChild(grid);
            return section;
        }

        function createAnalysisSection(titleText, analysis, type) {
            var section = createEl('div', 'detail-section');
            var title = createEl('h3', 'section-title', titleText);
            section.appendChild(title);

            var riskLevel = analysis.risk_level || 'N/A';
            var riskP = createEl('p', '', '위험 수준: ');
            var riskStrong = createEl('strong', '', riskLevel);
            riskP.appendChild(riskStrong);
            riskP.style.marginBottom = '10px';
            section.appendChild(riskP);

            var items = type === 'repainting' ? (analysis.issues || []) : (analysis.concerns || []);
            if (items.length > 0) {
                var ul = createEl('ul', 'analysis-list issues');
                items.forEach(function(item) {
                    var li = createEl('li', '', escapeHtml(item));
                    ul.appendChild(li);
                });
                section.appendChild(ul);
            } else {
                var noIssue = createEl('p', '', '문제 없음');
                noIssue.style.color = 'var(--accent-green)';
                section.appendChild(noIssue);
            }

            return section;
        }

        function createCodeSection(strategy) {
            var section = createEl('div', 'detail-section');
            var title = createEl('h3', 'section-title', 'Pine Script 코드');
            section.appendChild(title);

            var codeBlock = createEl('div', 'code-block');

            var header = createEl('div', 'code-header');
            var codeTitle = createEl('span', 'code-title', 'pine_script_v' + (strategy.pine_version || 5));
            var copyBtn = createEl('button', 'copy-btn', '복사');
            var codeId = 'pine-code-' + strategy.script_id;
            copyBtn.onclick = function() { copyCode(codeId, copyBtn); };
            header.appendChild(codeTitle);
            header.appendChild(copyBtn);
            codeBlock.appendChild(header);

            var pre = createEl('pre');
            var code = createEl('code');
            code.id = codeId;
            code.textContent = strategy.pine_code; // 안전한 textContent 사용
            pre.appendChild(code);
            codeBlock.appendChild(pre);

            section.appendChild(codeBlock);
            return section;
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModal();
        });

        document.getElementById('detailModal').addEventListener('click', function(e) {
            if (e.target.id === 'detailModal') closeModal();
        });

        function copyCode(elementId, btn) {
            var code = document.getElementById(elementId).textContent;
            navigator.clipboard.writeText(code).then(function() {
                var originalText = btn.textContent;
                btn.textContent = '복사됨!';
                btn.classList.add('copied');
                setTimeout(function() {
                    btn.textContent = originalText;
                    btn.classList.remove('copied');
                }, 2000);
            });
        }

        sortTable('score');
    </script>
</body>
</html>
"""


# =====================================================
# 메인 함수
# =====================================================

async def generate_beginner_report(
    db_path: str = "data/strategies.db",
    output_path: str = "data/beginner_report.html"
) -> str:
    """
    초보자 친화적 HTML 리포트 생성

    Args:
        db_path: 데이터베이스 파일 경로
        output_path: 출력 HTML 파일 경로

    Returns:
        생성된 HTML 파일 경로
    """
    db = StrategyDatabase(db_path)
    await db.init_db()

    try:
        stats = await db.get_stats()
        strategies_raw = await db.search_strategies()

        strategies = []
        strategies_json_data = []

        for strategy in strategies_raw:
            if not strategy.analysis:
                continue

            analysis = strategy.analysis
            performance = strategy.performance or {}

            # 점수 추출
            repainting_score = analysis.get("repainting_score", 0)
            overfitting_score = analysis.get("overfitting_score", 0)
            total_score = analysis.get("total_score", 0)
            grade = analysis.get("grade", "F")

            # 위험 수준
            if repainting_score >= 80:
                repainting_risk = "low"
            elif repainting_score >= 60:
                repainting_risk = "medium"
            else:
                repainting_risk = "high"

            if overfitting_score <= 30:
                overfitting_risk = "low"
            elif overfitting_score <= 60:
                overfitting_risk = "medium"
            else:
                overfitting_risk = "high"

            # 권장 여부 계산
            rec_type = get_recommendation_type(total_score, grade, repainting_score, overfitting_score)
            rec_icon = get_recommendation_icon(rec_type)
            rec_title = get_recommendation_title(rec_type)
            rec_reason = get_recommendation_reason(total_score, grade, rec_type)

            # 위험 수준 및 메시지
            risk_level = get_risk_level(repainting_score, overfitting_score)
            risk_message = get_risk_message(repainting_score, overfitting_score)

            # 백테스트 데이터
            has_performance = bool(performance)
            net_profit_pct = performance.get("net_profit_percent", performance.get("net_profit_pct", 0)) or 0
            max_drawdown_pct = performance.get("max_drawdown_percent", performance.get("max_drawdown_pct", 0)) or 0
            win_rate = performance.get("win_rate", 0) or 0

            # 요약 (LLM 분석 결과가 있으면 사용)
            llm_analysis = analysis.get("llm_analysis") or {}
            summary = llm_analysis.get("summary_kr", "") or llm_analysis.get("summary", "")

            # Jinja 템플릿용 데이터
            strategy_data = {
                "script_id": strategy.script_id,
                "title": strategy.title,
                "author": strategy.author,
                "likes": strategy.likes,
                "score": total_score,
                "grade": grade,
                "status": analysis.get("status", "unknown"),
                "repainting_score": repainting_score,
                "overfitting_score": overfitting_score,
                "repainting_risk": repainting_risk,
                "overfitting_risk": overfitting_risk,
                "recommendation_type": rec_type,
                "recommendation_icon": rec_icon,
                "recommendation_title": rec_title,
                "recommendation_reason": rec_reason,
                "risk_level": risk_level,
                "risk_message": risk_message,
                "has_performance": has_performance,
                "net_profit_pct": net_profit_pct,
                "max_drawdown_pct": max_drawdown_pct,
                "win_rate": win_rate,
                "summary": summary,
            }
            strategies.append(strategy_data)

            # JSON용 전체 데이터
            full_data = {
                **strategy_data,
                "pine_code": strategy.pine_code or "",
                "pine_version": strategy.pine_version,
                "analysis": analysis,
                "performance": performance,
                "explanation": llm_analysis,
            }
            strategies_json_data.append(full_data)

        # 점수순 정렬
        strategies.sort(key=lambda x: x["score"], reverse=True)
        strategies_json_data.sort(key=lambda x: x["score"], reverse=True)

        # HTML 렌더링
        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stats=stats,
            strategies=strategies,
            strategies_json=json.dumps(strategies_json_data, ensure_ascii=False)
        )

        # 파일 저장
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")

        logger.info(f"초보자용 HTML 리포트 생성 완료: {output_file}")
        logger.info(f"  - 총 전략: {stats.total_strategies}")
        logger.info(f"  - 분석 완료: {stats.analyzed_count}")
        logger.info(f"  - 권장 전략: {stats.passed_count}")

        return str(output_file.absolute())

    finally:
        await db.close()


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="초보자 친화적 HTML 리포트 생성")
    parser.add_argument("--db", default="data/strategies.db", help="데이터베이스 파일 경로")
    parser.add_argument("--output", default="data/beginner_report.html", help="출력 HTML 파일 경로")
    parser.add_argument("--debug", action="store_true", help="디버그 모드")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    output_path = await generate_beginner_report(db_path=args.db, output_path=args.output)

    print(f"\n✅ 초보자용 리포트 생성 완료!")
    print(f"📄 파일: {output_path}")
    print(f"\n🌐 브라우저에서 열기:")
    print(f"   open {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
