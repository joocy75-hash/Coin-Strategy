#!/usr/bin/env python3
"""
Extract Pine Scripts for top 5 C-grade strategies
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = "/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db"
OUTPUT_DIR = "/Users/mr.joo/Desktop/전략연구소/c_grade_pine_scripts"

# Top 5 strategy IDs from analysis
TOP_5_IDS = [
    "AOTPWbpq-Pivot-Trend-ChartPrime",
    "I0o8N7VW-Supply-and-Demand-Zones-BigBeluga",
    "x0pgNaRA-Support-and-Resistance",
    "dTBnHWe8-ATR-Normalized-VWMA-Deviation",
    "TEST_STRATEGY_001"
]

def extract_pine_scripts():
    """Extract Pine Scripts from database"""
    # Create output directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Extracting Pine Scripts for Top 5 Strategies")
    print("=" * 80)
    print()

    for script_id in TOP_5_IDS:
        query = """
        SELECT
            script_id,
            title,
            author,
            pine_code,
            analysis_json
        FROM strategies
        WHERE script_id = ?
        """

        cursor.execute(query, (script_id,))
        row = cursor.fetchone()

        if not row:
            print(f"ERROR: Strategy {script_id} not found")
            continue

        script_id, title, author, pine_code, analysis_json = row

        # Parse analysis
        analysis = json.loads(analysis_json) if analysis_json else {}
        score = analysis.get('total_score', 'N/A')

        print(f"Strategy: {title}")
        print(f"  Script ID: {script_id}")
        print(f"  Author: {author}")
        print(f"  Score: {score}")

        # Save Pine Script
        safe_filename = script_id.replace('/', '_').replace('\\', '_')
        pine_file = output_path / f"{safe_filename}.pine"

        with open(pine_file, 'w', encoding='utf-8') as f:
            f.write(pine_code if pine_code else "// No Pine Script available")

        print(f"  Saved to: {pine_file}")

        # Save analysis JSON
        analysis_file = output_path / f"{safe_filename}_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)

        print(f"  Analysis saved to: {analysis_file}")
        print()

    conn.close()

    print("=" * 80)
    print(f"Extraction complete. Files saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    extract_pine_scripts()
