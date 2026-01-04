"""
Extract Missing Batch 1 Pine Scripts from Database
=================================================

Extracts the remaining 3 Pine scripts for Batch 1 C-grade strategies.

Author: Strategy Research Lab
Date: 2026-01-04
"""

import sqlite3
from pathlib import Path

# Configuration
DB_PATH = Path('/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db')
OUTPUT_DIR = Path('/Users/mr.joo/Desktop/전략연구소/c_grade_pine_scripts')

# Missing strategy IDs
MISSING_STRATEGIES = [
    'ibJoSrFp-Power-Hour-Trendlines-LuxAlgo',
    'ETN2PyhG-Structure-Lite-Automatic-Major-Trend-Lines',
    'z8gaWHWQ-Auto-Anchored-Fibonacci-Volume-Profile-Custom-Array-Engine',
]


def extract_pine_scripts():
    """Extract Pine scripts from database."""

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("Extracting Missing Batch 1 Pine Scripts")
    print("=" * 80)
    print()

    extracted = 0

    for script_id in MISSING_STRATEGIES:
        # Try to find by exact ID
        cursor.execute("""
            SELECT script_id, title, pine_code
            FROM strategies
            WHERE script_id = ?
        """, (script_id,))

        result = cursor.fetchone()

        if not result:
            # Try fuzzy match (part of ID)
            partial_id = script_id.split('-')[0]
            cursor.execute("""
                SELECT script_id, title, pine_code
                FROM strategies
                WHERE script_id LIKE ?
                LIMIT 1
            """, (f"{partial_id}%",))
            result = cursor.fetchone()

        if result:
            actual_id, title, pine_code = result

            if pine_code:
                # Save Pine script
                output_file = OUTPUT_DIR / f"{actual_id}.pine"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(pine_code)

                print(f"✓ Extracted: {actual_id}")
                print(f"  Title: {title}")
                print(f"  Size: {len(pine_code)} bytes")
                print(f"  Saved to: {output_file.name}")
                print()

                extracted += 1
            else:
                print(f"✗ No Pine script for: {script_id}")
                print()
        else:
            print(f"✗ Not found in database: {script_id}")
            print()

    conn.close()

    print("=" * 80)
    print(f"Extraction Complete: {extracted}/{len(MISSING_STRATEGIES)} strategies")
    print("=" * 80)


if __name__ == "__main__":
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extract_pine_scripts()
