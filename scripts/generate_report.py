#!/usr/bin/env python3
"""
HTML 리포트 생성 스크립트

전략 연구소 데이터베이스에서 데이터를 조회하여
단일 HTML 파일로 리포트를 생성합니다.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from jinja2 import Template
from src.storage import StrategyDatabase

logger = logging.getLogger(__name__)


# HTML 템플릿 (단일 파일로 모든 스타일 포함)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Strategy Research Lab - 분석 리포트</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

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
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        header {
            background: var(--bg-secondary);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow);
        }

        h1 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: var(--accent-blue);
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 5px;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-blue);
        }

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

        .filter-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        input, select {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--accent-blue);
        }

        .table-container {
            background: var(--bg-secondary);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            margin-bottom: 30px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: var(--bg-tertiary);
        }

        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            user-select: none;
        }

        th:hover {
            color: var(--accent-blue);
        }

        tbody tr {
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: background 0.2s;
        }

        tbody tr:hover {
            background: var(--bg-tertiary);
        }

        td {
            padding: 12px 15px;
            font-size: 0.9rem;
        }

        .grade {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        .grade-A { background: var(--accent-green); color: #000; }
        .grade-B { background: var(--accent-blue); color: #000; }
        .grade-C { background: var(--accent-yellow); color: #000; }
        .grade-D { background: var(--accent-red); color: #fff; }
        .grade-F { background: #6e7681; color: #fff; }

        .status {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85rem;
        }

        .status-passed { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); }
        .status-review { background: rgba(210, 153, 34, 0.2); color: var(--accent-yellow); }
        .status-rejected { background: rgba(248, 81, 73, 0.2); color: var(--accent-red); }

        .risk-indicator {
            display: flex;
            gap: 8px;
            align-items: center;
            font-size: 0.85rem;
        }

        .risk-bar {
            height: 6px;
            width: 60px;
            background: var(--bg-tertiary);
            border-radius: 3px;
            overflow: hidden;
        }

        .risk-fill {
            height: 100%;
            transition: width 0.3s;
        }

        .risk-low { background: var(--accent-green); }
        .risk-medium { background: var(--accent-yellow); }
        .risk-high { background: var(--accent-red); }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
            padding: 20px;
        }

        .modal.active {
            display: flex;
            align-items: flex-start;
            justify-content: center;
        }

        .modal-content {
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            max-width: 1200px;
            width: 100%;
            margin: 40px 0;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.5);
        }

        .modal-header {
            padding: 25px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .modal-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .modal-meta {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .close-modal {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: all 0.2s;
        }

        .close-modal:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .modal-body {
            padding: 25px;
            max-height: 70vh;
            overflow-y: auto;
        }

        .detail-section {
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--accent-blue);
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .detail-item {
            background: var(--bg-tertiary);
            padding: 15px;
            border-radius: 6px;
        }

        .detail-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 5px;
        }

        .detail-value {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .code-block {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 15px;
            overflow-x: auto;
            position: relative;
        }

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .code-title {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .copy-btn {
            background: var(--accent-blue);
            border: none;
            color: #000;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.85rem;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }

        .copy-btn:hover {
            opacity: 0.8;
        }

        .copy-btn.copied {
            background: var(--accent-green);
        }

        pre {
            margin: 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            color: var(--text-primary);
        }

        code {
            font-family: inherit;
        }

        .analysis-list {
            list-style: none;
            padding: 0;
        }

        .analysis-list li {
            padding: 8px 12px;
            margin-bottom: 6px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            border-left: 3px solid var(--accent-blue);
        }

        .analysis-list.issues li {
            border-left-color: var(--accent-red);
        }

        .analysis-list.positives li {
            border-left-color: var(--accent-green);
        }

        .no-data {
            color: var(--text-secondary);
            font-style: italic;
            text-align: center;
            padding: 40px;
        }

        .footer {
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.9rem;
            border-top: 1px solid var(--border-color);
            margin-top: 40px;
        }

        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-tertiary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #484f58;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TradingView Strategy Research Lab</h1>
            <p class="subtitle">생성일: {{ generated_at }} | 총 {{ stats.total_strategies }}개 전략</p>
        </header>

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
                <div class="stat-label">통과 전략</div>
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
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                    <option value="F">F</option>
                </select>
            </div>
            <div class="filter-group">
                <label>상태:</label>
                <select id="statusFilter">
                    <option value="">전체</option>
                    <option value="passed">통과</option>
                    <option value="review">검토</option>
                    <option value="rejected">거부</option>
                </select>
            </div>
            <div class="filter-group">
                <label>최소 점수:</label>
                <input type="number" id="minScore" min="0" max="100" placeholder="0">
            </div>
        </div>

        <div class="table-container">
            <table id="strategiesTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('title')">전략명</th>
                        <th onclick="sortTable('author')">작성자</th>
                        <th onclick="sortTable('likes')">좋아요</th>
                        <th onclick="sortTable('score')">점수</th>
                        <th onclick="sortTable('grade')">등급</th>
                        <th onclick="sortTable('status')">상태</th>
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
                        data-status="{{ strategy.status }}"
                        data-score="{{ strategy.score }}">
                        <td>{{ strategy.title }}</td>
                        <td>{{ strategy.author }}</td>
                        <td>{{ strategy.likes }}</td>
                        <td><strong>{{ "%.1f"|format(strategy.score) }}</strong></td>
                        <td><span class="grade grade-{{ strategy.grade }}">{{ strategy.grade }}</span></td>
                        <td><span class="status status-{{ strategy.status }}">{{ strategy.status }}</span></td>
                        <td>
                            <div class="risk-indicator">
                                <div class="risk-bar">
                                    <div class="risk-fill risk-{{ strategy.repainting_risk }}"
                                         style="width: {{ strategy.repainting_score }}%;"></div>
                                </div>
                                <span>{{ "%.0f"|format(strategy.repainting_score) }}</span>
                            </div>
                        </td>
                        <td>
                            <div class="risk-indicator">
                                <div class="risk-bar">
                                    <div class="risk-fill risk-{{ strategy.overfitting_risk }}"
                                         style="width: {{ strategy.overfitting_score }}%;"></div>
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
            <p>TradingView Strategy Research Lab | 자동 생성된 리포트</p>
        </div>
    </div>

    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2 class="modal-title" id="modalTitle"></h2>
                    <div class="modal-meta" id="modalMeta"></div>
                </div>
                <button class="close-modal" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        const strategiesData = {{ strategies_json|safe }};
        let currentSort = { column: 'score', ascending: false };

        function sortTable(column) {
            currentSort.ascending = currentSort.column === column ? !currentSort.ascending : false;
            currentSort.column = column;
            const rows = Array.from(document.querySelectorAll('.strategy-row'));
            rows.sort((a, b) => {
                let aVal = a.dataset[column];
                let bVal = b.dataset[column];
                if (column === 'likes' || column === 'score') {
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                }
                if (aVal < bVal) return currentSort.ascending ? -1 : 1;
                if (aVal > bVal) return currentSort.ascending ? 1 : -1;
                return 0;
            });
            const tbody = document.getElementById('strategiesBody');
            rows.forEach(row => tbody.appendChild(row));
        }

        function applyFilters() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const gradeFilter = document.getElementById('gradeFilter').value;
            const statusFilter = document.getElementById('statusFilter').value;
            const minScore = parseFloat(document.getElementById('minScore').value) || 0;
            document.querySelectorAll('.strategy-row').forEach(row => {
                const title = row.dataset.title;
                const author = row.dataset.author;
                const grade = row.dataset.grade;
                const status = row.dataset.status;
                const score = parseFloat(row.dataset.score) || 0;
                const matchSearch = !searchTerm || title.includes(searchTerm) || author.includes(searchTerm);
                const matchGrade = !gradeFilter || grade === gradeFilter;
                const matchStatus = !statusFilter || status === statusFilter;
                const matchScore = score >= minScore;
                row.style.display = matchSearch && matchGrade && matchStatus && matchScore ? '' : 'none';
            });
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);
        document.getElementById('gradeFilter').addEventListener('change', applyFilters);
        document.getElementById('statusFilter').addEventListener('change', applyFilters);
        document.getElementById('minScore').addEventListener('input', applyFilters);

        document.querySelectorAll('.strategy-row').forEach(row => {
            row.addEventListener('click', () => {
                const scriptId = row.dataset.id;
                const strategy = strategiesData.find(s => s.script_id === scriptId);
                if (strategy) showDetail(strategy);
            });
        });

        function showDetail(strategy) {
            document.getElementById('modalTitle').textContent = strategy.title;
            const metaEl = document.getElementById('modalMeta');
            metaEl.textContent = '';
            metaEl.appendChild(document.createTextNode('작성자: ' + strategy.author + ' | 좋아요: ' + strategy.likes + ' | 점수: ' + strategy.score.toFixed(1)));

            const bodyEl = document.getElementById('modalBody');
            bodyEl.textContent = '';

            const section1 = createDetailSection(strategy);
            bodyEl.appendChild(section1);

            if (strategy.analysis) {
                if (strategy.analysis.repainting_analysis) {
                    bodyEl.appendChild(createRepaintSection(strategy.analysis.repainting_analysis));
                }
                if (strategy.analysis.overfitting_analysis) {
                    bodyEl.appendChild(createOverfitSection(strategy.analysis.overfitting_analysis));
                }
            }

            if (strategy.pine_code) {
                bodyEl.appendChild(createCodeSection(strategy));
            }

            if (strategy.converted_path) {
                bodyEl.appendChild(createConvertedSection(strategy.converted_path));
            }

            document.getElementById('detailModal').classList.add('active');
        }

        function createDetailSection(strategy) {
            const section = document.createElement('div');
            section.className = 'detail-section';
            const title = document.createElement('h3');
            title.className = 'section-title';
            title.textContent = '기본 정보';
            section.appendChild(title);
            const grid = document.createElement('div');
            grid.className = 'detail-grid';
            grid.appendChild(createDetailItem('등급', createGradeBadge(strategy.grade)));
            grid.appendChild(createDetailItem('상태', createStatusBadge(strategy.status)));
            grid.appendChild(createDetailItem('리페인팅 점수', strategy.repainting_score.toFixed(1)));
            grid.appendChild(createDetailItem('오버피팅 점수', strategy.overfitting_score.toFixed(1)));
            section.appendChild(grid);
            return section;
        }

        function createDetailItem(label, value) {
            const item = document.createElement('div');
            item.className = 'detail-item';
            const labelEl = document.createElement('div');
            labelEl.className = 'detail-label';
            labelEl.textContent = label;
            const valueEl = document.createElement('div');
            valueEl.className = 'detail-value';
            if (typeof value === 'string') {
                valueEl.textContent = value;
            } else {
                valueEl.appendChild(value);
            }
            item.appendChild(labelEl);
            item.appendChild(valueEl);
            return item;
        }

        function createGradeBadge(grade) {
            const badge = document.createElement('span');
            badge.className = 'grade grade-' + grade;
            badge.textContent = grade;
            return badge;
        }

        function createStatusBadge(status) {
            const badge = document.createElement('span');
            badge.className = 'status status-' + status;
            badge.textContent = status;
            return badge;
        }

        function createRepaintSection(repaint) {
            const section = document.createElement('div');
            section.className = 'detail-section';
            const title = document.createElement('h3');
            title.className = 'section-title';
            title.textContent = '리페인팅 분석';
            section.appendChild(title);
            const grid = document.createElement('div');
            grid.className = 'detail-grid';
            grid.appendChild(createDetailItem('위험 수준', repaint.risk_level || 'NONE'));
            section.appendChild(grid);
            if (repaint.issues && repaint.issues.length > 0) {
                const p = document.createElement('p');
                p.style.margin = '10px 0 8px';
                p.style.color = 'var(--text-secondary)';
                p.style.fontSize = '0.9rem';
                p.textContent = '발견된 문제:';
                section.appendChild(p);
                const ul = document.createElement('ul');
                ul.className = 'analysis-list issues';
                repaint.issues.forEach(issue => {
                    const li = document.createElement('li');
                    li.textContent = issue;
                    ul.appendChild(li);
                });
                section.appendChild(ul);
            } else {
                const p = document.createElement('p');
                p.style.color = 'var(--accent-green)';
                p.style.marginTop = '10px';
                p.textContent = '리페인팅 이슈 없음';
                section.appendChild(p);
            }
            return section;
        }

        function createOverfitSection(overfit) {
            const section = document.createElement('div');
            section.className = 'detail-section';
            const title = document.createElement('h3');
            title.className = 'section-title';
            title.textContent = '오버피팅 분석';
            section.appendChild(title);
            const grid = document.createElement('div');
            grid.className = 'detail-grid';
            grid.appendChild(createDetailItem('위험 수준', overfit.risk_level || 'low'));
            grid.appendChild(createDetailItem('파라미터 수', (overfit.parameter_count || 0) + '개'));
            section.appendChild(grid);
            if (overfit.concerns && overfit.concerns.length > 0) {
                const p = document.createElement('p');
                p.style.margin = '10px 0 8px';
                p.style.color = 'var(--text-secondary)';
                p.style.fontSize = '0.9rem';
                p.textContent = '우려사항:';
                section.appendChild(p);
                const ul = document.createElement('ul');
                ul.className = 'analysis-list issues';
                overfit.concerns.forEach(concern => {
                    const li = document.createElement('li');
                    li.textContent = concern;
                    ul.appendChild(li);
                });
                section.appendChild(ul);
            }
            return section;
        }

        function createCodeSection(strategy) {
            const section = document.createElement('div');
            section.className = 'detail-section';
            const title = document.createElement('h3');
            title.className = 'section-title';
            title.textContent = 'Pine Script 코드';
            section.appendChild(title);
            const codeBlock = document.createElement('div');
            codeBlock.className = 'code-block';
            const header = document.createElement('div');
            header.className = 'code-header';
            const codeTitle = document.createElement('span');
            codeTitle.className = 'code-title';
            codeTitle.textContent = 'pine_script_v' + (strategy.pine_version || 5);
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.textContent = '복사';
            const codeId = 'pine-code-' + strategy.script_id;
            copyBtn.onclick = () => copyCode(codeId, copyBtn);
            header.appendChild(codeTitle);
            header.appendChild(copyBtn);
            codeBlock.appendChild(header);
            const pre = document.createElement('pre');
            const code = document.createElement('code');
            code.id = codeId;
            code.textContent = strategy.pine_code;
            pre.appendChild(code);
            codeBlock.appendChild(pre);
            section.appendChild(codeBlock);
            return section;
        }

        function createConvertedSection(path) {
            const section = document.createElement('div');
            section.className = 'detail-section';
            const title = document.createElement('h3');
            title.className = 'section-title';
            title.textContent = '변환된 Python 코드';
            section.appendChild(title);
            const item = createDetailItem('파일 경로', path);
            item.querySelector('.detail-value').style.fontSize = '0.9rem';
            item.querySelector('.detail-value').style.wordBreak = 'break-all';
            section.appendChild(item);
            return section;
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });

        document.getElementById('detailModal').addEventListener('click', (e) => {
            if (e.target.id === 'detailModal') closeModal();
        });

        function copyCode(elementId, btn) {
            const code = document.getElementById(elementId).textContent;
            navigator.clipboard.writeText(code).then(() => {
                const originalText = btn.textContent;
                btn.textContent = '복사됨!';
                btn.classList.add('copied');
                setTimeout(() => {
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


async def generate_html_report(
    db_path: str = "data/strategies.db",
    output_path: str = "data/report.html"
) -> str:
    """
    HTML 리포트 생성

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

            repainting_score = analysis.get("repainting_score", 0)
            if repainting_score >= 80:
                repainting_risk = "low"
            elif repainting_score >= 60:
                repainting_risk = "medium"
            else:
                repainting_risk = "high"

            overfitting_score = analysis.get("overfitting_score", 0)
            if overfitting_score <= 30:
                overfitting_risk = "low"
            elif overfitting_score <= 60:
                overfitting_risk = "medium"
            else:
                overfitting_risk = "high"

            strategy_data = {
                "script_id": strategy.script_id,
                "title": strategy.title,
                "author": strategy.author,
                "likes": strategy.likes,
                "score": analysis.get("total_score", 0),
                "grade": analysis.get("grade", "F"),
                "status": analysis.get("status", "unknown"),
                "repainting_score": repainting_score,
                "overfitting_score": overfitting_score,
                "repainting_risk": repainting_risk,
                "overfitting_risk": overfitting_risk,
            }
            strategies.append(strategy_data)

            full_data = {
                **strategy_data,
                "pine_code": strategy.pine_code or "",
                "pine_version": strategy.pine_version,
                "analysis": analysis,
                "converted_path": analysis.get("converted_path", ""),
            }
            strategies_json_data.append(full_data)

        strategies.sort(key=lambda x: x["score"], reverse=True)
        strategies_json_data.sort(key=lambda x: x["score"], reverse=True)

        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stats=stats,
            strategies=strategies,
            strategies_json=json.dumps(strategies_json_data, ensure_ascii=False)
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_content, encoding="utf-8")

        logger.info(f"HTML 리포트 생성 완료: {output_file}")
        logger.info(f"  - 총 전략: {stats.total_strategies}")
        logger.info(f"  - 분석 완료: {stats.analyzed_count}")
        logger.info(f"  - 통과: {stats.passed_count}")

        return str(output_file.absolute())

    finally:
        await db.close()


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="HTML 리포트 생성")
    parser.add_argument("--db", default="data/strategies.db", help="데이터베이스 파일 경로")
    parser.add_argument("--output", default="data/report.html", help="출력 HTML 파일 경로")
    parser.add_argument("--debug", action="store_true", help="디버그 모드")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    output_path = await generate_html_report(db_path=args.db, output_path=args.output)

    print(f"\n리포트 생성 완료!")
    print(f"파일: {output_path}")
    print(f"\n브라우저에서 열기:")
    print(f"  open {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
