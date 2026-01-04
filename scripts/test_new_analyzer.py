#!/usr/bin/env python3
"""
Test script to analyze strategies using the new StrategyScorer pipeline.

This script:
1. Loads strategies from the database
2. Runs comprehensive analysis using:
   - RepaintingDetector (rule-based)
   - OverfittingDetector (rule-based)
   - RiskChecker (rule-based)
   - LLMDeepAnalyzer (Claude API, optional)
   - StrategyScorer (final scoring)
3. Updates the database with new analysis results
"""

import asyncio
import json
import logging
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.analyzer import StrategyScorer, FinalScore
from src.storage import StrategyDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


async def get_unanalyzed_strategies(db_path: str, limit: int = None) -> List[Dict[str, Any]]:
    """Get strategies from database that need analysis."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get strategies with Pine code
    query = """
        SELECT script_id, title, author, likes, views,
               pine_code, pine_version,
               performance_json, description, script_url
        FROM strategies
        WHERE pine_code IS NOT NULL AND pine_code != ''
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    strategies = []
    for row in rows:
        strategies.append({
            'script_id': row['script_id'],
            'title': row['title'],
            'author': row['author'],
            'likes': row['likes'],
            'views': row['views'],
            'pine_code': row['pine_code'],
            'pine_version': row['pine_version'],
            'performance_json': row['performance_json'],
            'description': row['description'] or '',
            'script_url': row['script_url'] or ''
        })

    return strategies


async def save_analysis_to_db(db_path: str, script_id: str, score: FinalScore) -> None:
    """Save analysis results to database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Convert FinalScore to JSON
    analysis_json = {
        'total_score': score.total_score,
        'grade': score.grade,
        'status': score.status,
        'repainting_score': score.repainting_score,
        'overfitting_score': score.overfitting_score,
        'risk_score': score.risk_score,
        'llm_score': score.llm_score,
        'repainting_analysis': score.repainting_analysis,
        'overfitting_analysis': score.overfitting_analysis,
        'risk_analysis': score.risk_analysis,
        'llm_analysis': score.llm_analysis,
        'analyzed_at': score.analyzed_at.isoformat(),
        'analysis_version': score.analysis_version
    }

    cur.execute("""
        UPDATE strategies
        SET analysis_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE script_id = ?
    """, [json.dumps(analysis_json, ensure_ascii=False), script_id])

    conn.commit()
    conn.close()


async def analyze_strategy_batch(
    strategies: List[Dict],
    config: Config,
    skip_llm: bool = False
) -> List[Dict]:
    """Analyze a batch of strategies."""

    # Initialize scorer
    api_key = None
    if not skip_llm:
        api_key = config.anthropic_api_key
        if not api_key:
            logger.warning("No Anthropic API key found. Running without LLM analysis.")
            skip_llm = True
            api_key = None

    scorer = StrategyScorer(
        llm_api_key=api_key,
        llm_model=config.llm_model
    )

    results = []

    for i, strategy in enumerate(strategies, 1):
        script_id = strategy['script_id']
        title = strategy['title']
        pine_code = strategy['pine_code']

        logger.info(f"\n{'='*70}")
        logger.info(f"[{i}/{len(strategies)}] Analyzing: {title[:60]}")
        logger.info(f"Author: {strategy['author']} | Likes: {strategy['likes']}")
        logger.info(f"{'='*70}")

        try:
            # Parse performance JSON if available
            performance = {}
            if strategy.get('performance_json'):
                try:
                    performance = json.loads(strategy['performance_json'])
                except:
                    pass

            # Run comprehensive analysis
            score = await scorer.score_strategy(
                pine_code=pine_code,
                title=title,
                description=strategy.get('description', ''),
                performance=performance,
                skip_llm=skip_llm
            )

            # Log results
            logger.info(f"✓ Analysis complete!")
            logger.info(f"  Total Score: {score.total_score:.1f}/100 | Grade: {score.grade} | Status: {score.status}")
            logger.info(f"  Breakdown:")
            logger.info(f"    - Repainting:  {score.repainting_score:.1f}/100 ({score.repainting_analysis.get('risk_level', 'N/A')})")
            logger.info(f"    - Overfitting: {score.overfitting_score:.1f}/100 ({score.overfitting_analysis.get('risk_level', 'N/A')})")
            logger.info(f"    - Risk Mgmt:   {score.risk_score:.1f}/100 ({score.risk_analysis.get('risk_level', 'N/A')})")
            logger.info(f"    - LLM Score:   {score.llm_score:.1f}/100")

            if score.repainting_analysis.get('issues'):
                logger.info(f"  ⚠ Repainting Issues ({len(score.repainting_analysis['issues'])}):")
                for issue in score.repainting_analysis['issues'][:3]:
                    logger.info(f"    - {issue}")

            if score.overfitting_analysis.get('concerns'):
                logger.info(f"  ⚠ Overfitting Concerns ({len(score.overfitting_analysis['concerns'])}):")
                for concern in score.overfitting_analysis['concerns'][:3]:
                    logger.info(f"    - {concern}")

            if score.llm_analysis:
                logger.info(f"  💡 LLM Recommendation: {score.llm_analysis.get('recommendation', 'N/A')}")
                if score.llm_analysis.get('summary'):
                    logger.info(f"  Summary: {score.llm_analysis['summary'][:100]}...")

            # Save to database
            await save_analysis_to_db(config.db_path, script_id, score)
            logger.info(f"  ✓ Saved to database")

            results.append({
                'script_id': script_id,
                'title': title,
                'score': score
            })

            # Rate limiting
            if not skip_llm:
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"  ✗ Analysis failed: {e}", exc_info=True)
            results.append({
                'script_id': script_id,
                'title': title,
                'error': str(e)
            })

    return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Test new StrategyScorer analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=5,
        help='Number of strategies to analyze (default: 5)'
    )
    parser.add_argument(
        '--skip-llm',
        action='store_true',
        help='Skip LLM deep analysis (faster, cheaper)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Analyze all strategies in database'
    )

    args = parser.parse_args()

    # Load config
    config = Config.load()
    config.ensure_directories()

    db_path = str(Path(config.db_path).resolve())

    logger.info("="*70)
    logger.info("TradingView Strategy Analyzer - Test Run")
    logger.info("="*70)
    logger.info(f"Database: {db_path}")
    logger.info(f"LLM Analysis: {'DISABLED' if args.skip_llm else 'ENABLED'}")
    logger.info(f"Limit: {'ALL' if args.all else args.limit}")
    logger.info("="*70)

    # Get strategies
    limit = None if args.all else args.limit
    strategies = await get_unanalyzed_strategies(db_path, limit=limit)

    if not strategies:
        logger.warning("No strategies found in database!")
        return

    logger.info(f"\nFound {len(strategies)} strategies to analyze\n")

    # Run analysis
    start_time = datetime.now()
    results = await analyze_strategy_batch(
        strategies,
        config,
        skip_llm=args.skip_llm
    )
    duration = (datetime.now() - start_time).total_seconds()

    # Print summary
    logger.info("\n" + "="*70)
    logger.info("ANALYSIS SUMMARY")
    logger.info("="*70)

    successful = [r for r in results if 'score' in r]
    failed = [r for r in results if 'error' in r]

    logger.info(f"Total Analyzed: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"Duration: {duration:.1f}s ({duration/len(results):.1f}s per strategy)")

    if successful:
        scores = [r['score'].total_score for r in successful]
        avg_score = sum(scores) / len(scores)

        logger.info(f"\nScore Statistics:")
        logger.info(f"  Average: {avg_score:.1f}/100")
        logger.info(f"  Min: {min(scores):.1f}")
        logger.info(f"  Max: {max(scores):.1f}")

        # Grade distribution
        grades = {}
        statuses = {}
        for r in successful:
            grade = r['score'].grade
            status = r['score'].status
            grades[grade] = grades.get(grade, 0) + 1
            statuses[status] = statuses.get(status, 0) + 1

        logger.info(f"\nGrade Distribution:")
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grades.get(grade, 0)
            if count > 0:
                logger.info(f"  {grade}: {count}")

        logger.info(f"\nStatus Distribution:")
        for status, count in statuses.items():
            logger.info(f"  {status}: {count}")

        # Top 3
        logger.info(f"\nTop 3 Strategies:")
        top3 = sorted(successful, key=lambda x: x['score'].total_score, reverse=True)[:3]
        for i, r in enumerate(top3, 1):
            logger.info(f"  {i}. {r['title'][:50]}")
            logger.info(f"     Score: {r['score'].total_score:.1f} | Grade: {r['score'].grade}")

    if failed:
        logger.info(f"\nFailed Analyses:")
        for r in failed:
            logger.info(f"  - {r['title'][:50]}: {r['error']}")

    logger.info("\n" + "="*70)
    logger.info("Analysis complete! Check the database for full results.")
    logger.info("="*70)


if __name__ == '__main__':
    asyncio.run(main())
