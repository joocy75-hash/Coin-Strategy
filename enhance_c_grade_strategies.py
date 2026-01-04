#!/usr/bin/env python3
"""
C등급 전략 자동 개선 시스템
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys

# Add trading-agent-system to path
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

print("C-grade Strategy Enhancement System")
print("=" * 80)

# 설정
DB_PATH = "/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db"
OUTPUT_DIR = Path("/Users/mr.joo/Desktop/전략연구소")

# 데이터베이스에서 전략 조회
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT script_id, title, author, pine_code, script_url, analysis_json
    FROM strategies
    WHERE pine_code IS NOT NULL AND pine_code != ''
""")

strategies = []
for row in cursor.fetchall():
    script_id, title, author, pine_code, script_url, analysis_json = row
    analysis = json.loads(analysis_json) if analysis_json else {}
    
    strategies.append({
        'script_id': script_id,
        'title': title,
        'author': author,
        'grade': analysis.get('grade', 'Unknown'),
        'total_score': analysis.get('total_score', 0),
    })

conn.close()

print(f"\nTotal strategies: {len(strategies)}")

# Grade distribution
grade_counts = {}
for s in strategies:
    grade = s['grade']
    grade_counts[grade] = grade_counts.get(grade, 0) + 1

print("\nGrade distribution:")
for grade, count in sorted(grade_counts.items()):
    print(f"  {grade}: {count}")

print("\nSystem ready for enhancement!")
