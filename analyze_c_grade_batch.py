#!/usr/bin/env python3
"""
Analyze all C-grade strategies for batch processing
Identifies viable candidates for risk management enhancement
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Any

# Database path
DB_PATH = "/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db"

# Common indicators that are easy to implement in Python
EASY_INDICATORS = {
    'sma': ['sma', 'simple moving average', 'ta.sma'],
    'ema': ['ema', 'exponential moving average', 'ta.ema'],
    'rsi': ['rsi', 'relative strength', 'ta.rsi'],
    'macd': ['macd', 'ta.macd'],
    'atr': ['atr', 'average true range', 'ta.atr'],
    'bollinger': ['bollinger', 'bb', 'ta.bb'],
    'stochastic': ['stoch', 'stochastic', 'ta.stoch'],
    'adx': ['adx', 'ta.adx'],
    'cci': ['cci', 'commodity channel', 'ta.cci'],
    'mfi': ['mfi', 'money flow', 'ta.mfi'],
    'obv': ['obv', 'on balance volume', 'ta.obv'],
    'vwap': ['vwap', 'volume weighted'],
    'vwma': ['vwma', 'volume weighted ma'],
}

# Difficult/custom indicators
DIFFICULT_INDICATORS = [
    'kalman', 'polynomial', 'custom array', 'machine learning',
    'neural', 'ai', 'proprietary', 'encrypted'
]

def connect_db():
    """Connect to SQLite database"""
    return sqlite3.connect(DB_PATH)

def get_all_c_grade_strategies(conn) -> List[Dict[str, Any]]:
    """Get all C-grade strategies from database"""
    cursor = conn.cursor()

    query = """
    SELECT
        script_id,
        title,
        author,
        pine_code,
        analysis_json,
        performance_json,
        script_url,
        description
    FROM strategies
    WHERE json_extract(analysis_json, '$.grade') = 'C'
    ORDER BY json_extract(analysis_json, '$.total_score') DESC
    """

    cursor.execute(query)
    columns = [col[0] for col in cursor.description]

    strategies = []
    for row in cursor.fetchall():
        strategy = dict(zip(columns, row))

        # Parse JSON fields
        if strategy['analysis_json']:
            strategy['analysis'] = json.loads(strategy['analysis_json'])
        else:
            strategy['analysis'] = {}

        if strategy['performance_json']:
            strategy['performance'] = json.loads(strategy['performance_json'])
        else:
            strategy['performance'] = {}

        strategies.append(strategy)

    return strategies

def detect_indicators(pine_code: str) -> Dict[str, Any]:
    """Detect which indicators are used in Pine Script code"""
    if not pine_code:
        return {'easy': [], 'difficult': [], 'unknown': []}

    pine_lower = pine_code.lower()

    # Detect easy indicators
    easy_found = []
    for indicator_name, patterns in EASY_INDICATORS.items():
        for pattern in patterns:
            if pattern in pine_lower:
                if indicator_name not in easy_found:
                    easy_found.append(indicator_name)
                break

    # Detect difficult indicators
    difficult_found = []
    for pattern in DIFFICULT_INDICATORS:
        if pattern in pine_lower:
            difficult_found.append(pattern)

    return {
        'easy': easy_found,
        'difficult': difficult_found,
        'has_ta_lib': 'ta.' in pine_code,
        'custom_functions': len(re.findall(r'^(?:export\s+)?(?:method\s+)?(\w+)\s*\(', pine_code, re.MULTILINE))
    }

def assess_complexity(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Assess conversion complexity for a strategy"""
    pine_code = strategy.get('pine_code', '')
    indicators = detect_indicators(pine_code)
    analysis = strategy.get('analysis', {})

    # Calculate complexity score (lower is better)
    complexity_score = 0
    complexity_factors = []

    # Factor 1: Difficult indicators (+30 each)
    if indicators['difficult']:
        complexity_score += len(indicators['difficult']) * 30
        complexity_factors.append(f"Difficult indicators: {', '.join(indicators['difficult'])}")

    # Factor 2: No easy indicators (+20)
    if not indicators['easy']:
        complexity_score += 20
        complexity_factors.append("No common indicators detected")

    # Factor 3: Many custom functions (+10 per function over 5)
    custom_funcs = indicators.get('custom_functions', 0)
    if custom_funcs > 5:
        complexity_score += (custom_funcs - 5) * 10
        complexity_factors.append(f"Many custom functions: {custom_funcs}")

    # Factor 4: Repainting issues (+40)
    repainting = analysis.get('issues', {}).get('repainting', [])
    if repainting:
        complexity_score += 40
        complexity_factors.append(f"Repainting issues: {len(repainting)}")

    # Factor 5: Code length (longer = more complex)
    code_lines = len(pine_code.split('\n')) if pine_code else 0
    if code_lines > 500:
        complexity_score += 20
        complexity_factors.append(f"Long code: {code_lines} lines")
    elif code_lines > 300:
        complexity_score += 10
        complexity_factors.append(f"Medium code: {code_lines} lines")

    # Determine complexity level
    if complexity_score <= 20:
        complexity_level = "LOW"
    elif complexity_score <= 50:
        complexity_level = "MEDIUM"
    else:
        complexity_level = "HIGH"

    return {
        'score': complexity_score,
        'level': complexity_level,
        'factors': complexity_factors,
        'indicators': indicators,
        'code_lines': code_lines
    }

def calculate_priority_score(strategy: Dict[str, Any], complexity: Dict[str, Any]) -> float:
    """Calculate priority score for processing order"""
    analysis = strategy.get('analysis', {})

    # Base score from strategy total score
    total_score = analysis.get('total_score', 50)
    priority = total_score

    # Bonus for high score (closer to B-grade threshold of 70)
    if total_score >= 65:
        priority += 10
    elif total_score >= 60:
        priority += 5

    # Penalty for complexity
    complexity_score = complexity.get('score', 0)
    priority -= complexity_score * 0.3

    # Bonus for having easy indicators
    easy_indicators = complexity.get('indicators', {}).get('easy', [])
    priority += len(easy_indicators) * 2

    # Penalty for repainting
    repainting = analysis.get('issues', {}).get('repainting', [])
    if repainting:
        priority -= 10

    return round(priority, 2)

def estimate_improvement_potential(strategy: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate potential improvement from adding risk management"""
    analysis = strategy.get('analysis', {})
    metrics = analysis.get('metrics', {})

    # Based on previous success with SuperTrend Divergence and ATR VWMA
    # MaxDD improved by ~6.5%, which can boost score by 5-8 points

    current_score = analysis.get('total_score', 50)

    # Estimate improvement
    # Conservative: +3 points, Realistic: +5 points, Optimistic: +8 points
    conservative = current_score + 3
    realistic = current_score + 5
    optimistic = current_score + 8

    # Check if realistic improvement would reach B-grade (70+)
    reaches_b_grade = realistic >= 70

    return {
        'current_score': current_score,
        'conservative': conservative,
        'realistic': realistic,
        'optimistic': optimistic,
        'reaches_b_grade': reaches_b_grade,
        'points_needed_for_b': max(0, 70 - current_score)
    }

def analyze_strategies():
    """Main analysis function"""
    print("=" * 80)
    print("C-GRADE STRATEGY BATCH ANALYSIS")
    print("=" * 80)
    print()

    # Connect to database
    conn = connect_db()
    strategies = get_all_c_grade_strategies(conn)

    print(f"Total C-grade strategies found: {len(strategies)}")
    print()

    # Analyze each strategy
    analyzed_strategies = []

    for i, strategy in enumerate(strategies, 1):
        print(f"[{i}/{len(strategies)}] Analyzing: {strategy['title']}")

        complexity = assess_complexity(strategy)
        priority = calculate_priority_score(strategy, complexity)
        improvement = estimate_improvement_potential(strategy)

        analyzed_strategies.append({
            'strategy': strategy,
            'complexity': complexity,
            'priority': priority,
            'improvement': improvement
        })

    # Sort by priority score (highest first)
    analyzed_strategies.sort(key=lambda x: x['priority'], reverse=True)

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()

    # Display top 10 candidates
    print("TOP 10 VIABLE CANDIDATES FOR PROCESSING:")
    print()

    for i, item in enumerate(analyzed_strategies[:10], 1):
        strategy = item['strategy']
        complexity = item['complexity']
        improvement = item['improvement']

        print(f"{i}. {strategy['title']}")
        print(f"   Script ID: {strategy['script_id']}")
        print(f"   Current Score: {improvement['current_score']}")
        print(f"   Priority Score: {item['priority']}")
        print(f"   Complexity: {complexity['level']} ({complexity['score']} points)")
        print(f"   Easy Indicators: {', '.join(complexity['indicators']['easy']) if complexity['indicators']['easy'] else 'None'}")
        print(f"   Estimated Improvement: {improvement['realistic']} (realistic)")
        print(f"   Reaches B-grade: {'YES' if improvement['reaches_b_grade'] else 'NO'}")
        print()

    conn.close()

    return analyzed_strategies

if __name__ == "__main__":
    results = analyze_strategies()

    # Save results to JSON for further processing
    output_file = "/Users/mr.joo/Desktop/전략연구소/c_grade_analysis_results.json"

    # Convert to serializable format
    serializable_results = []
    for item in results:
        serializable_results.append({
            'script_id': item['strategy']['script_id'],
            'title': item['strategy']['title'],
            'author': item['strategy']['author'],
            'current_score': item['improvement']['current_score'],
            'priority': item['priority'],
            'complexity': item['complexity'],
            'improvement': item['improvement'],
            'has_pine_code': bool(item['strategy'].get('pine_code'))
        })

    with open(output_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
