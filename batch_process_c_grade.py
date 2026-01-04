#!/usr/bin/env python3
"""
Batch Processing Script for C-Grade Strategy Enhancement

This script automates:
1. Pine Script extraction from database
2. Basic indicator detection
3. Risk management template selection
4. Batch backtest execution
5. Performance comparison (before/after)

Usage:
    python batch_process_c_grade.py --batch 1
    python batch_process_c_grade.py --strategy AOTPWbpq-Pivot-Trend-ChartPrime
    python batch_process_c_grade.py --all
"""

import argparse
import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys

# Paths
DB_PATH = "/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/data/strategies.db"
ANALYSIS_RESULTS = "/Users/mr.joo/Desktop/전략연구소/c_grade_analysis_results.json"
PINE_SCRIPTS_DIR = "/Users/mr.joo/Desktop/전략연구소/c_grade_pine_scripts"
OUTPUT_DIR = "/Users/mr.joo/Desktop/전략연구소/enhanced_strategies_batch"
RISK_MGMT_MODULE = "/Users/mr.joo/Desktop/전략연구소/risk_management_patterns.py"

# Batch definitions (from analysis report)
BATCH_1_IDS = [
    "AOTPWbpq-Pivot-Trend-ChartPrime",
    "I0o8N7VW-Supply-and-Demand-Zones-BigBeluga",
    "x0pgNaRA-Support-and-Resistance",
    "dTBnHWe8-ATR-Normalized-VWMA-Deviation",
    "TEST_STRATEGY_001",
    "ibJoSrFp-Power-Hour-Trendlines-LuxAlgo",
    "ETN2PyhG-Structure-Lite-Automatic-Major-Trend-Lines",
    "z8gaWHWQ-Auto-Anchored-Fibonacci-Volume-Profile-Custom-Array-Engine",
]

BATCH_2_IDS = [
    "YKgJa5BY-S-R-Zones-Signals-V6-4-Rejection-Break",
    "yEpX7uTv-Order-Blocks-Imbalance",
    "31FxM7aE-ADX-Volatility-Waves-BOSWaves",
    "EtN6uzq9-Apex-Trend-Liquidity-Master-V2-1",
]


class PineScriptAnalyzer:
    """Analyze Pine Script to extract indicators and logic"""

    @staticmethod
    def detect_indicators(pine_code: str) -> Dict[str, List[str]]:
        """Detect which indicators are used"""
        indicators = {
            'sma': [],
            'ema': [],
            'rsi': [],
            'macd': [],
            'atr': [],
            'bollinger': [],
            'vwap': [],
            'vwma': [],
            'stochastic': [],
            'adx': [],
            'cci': [],
            'mfi': [],
            'obv': [],
            'pivot': [],
        }

        # Pattern matching for each indicator
        patterns = {
            'sma': r'ta\.sma\([^)]+\)',
            'ema': r'ta\.ema\([^)]+\)',
            'rsi': r'ta\.rsi\([^)]+\)',
            'macd': r'ta\.macd\([^)]+\)',
            'atr': r'ta\.atr\([^)]+\)',
            'bollinger': r'ta\.bb[^(]*\([^)]+\)',
            'vwap': r'ta\.vwap\([^)]+\)',
            'vwma': r'ta\.vwma\([^)]+\)',
            'stochastic': r'ta\.stoch\([^)]+\)',
            'adx': r'ta\.adx\([^)]+\)',
            'cci': r'ta\.cci\([^)]+\)',
            'mfi': r'ta\.mfi\([^)]+\)',
            'obv': r'ta\.obv\([^)]+\)',
            'pivot': r'ta\.pivot(high|low)\([^)]+\)',
        }

        for indicator, pattern in patterns.items():
            matches = re.findall(pattern, pine_code)
            if matches:
                indicators[indicator] = matches

        return {k: v for k, v in indicators.items() if v}

    @staticmethod
    def detect_entry_signals(pine_code: str) -> Dict[str, Any]:
        """Detect entry signal logic"""
        signals = {
            'long_conditions': [],
            'short_conditions': [],
            'uses_crossover': False,
            'uses_crossunder': False,
            'uses_comparison': False,
        }

        # Check for crossover/crossunder
        if 'ta.crossover' in pine_code:
            signals['uses_crossover'] = True
            signals['long_conditions'].append('crossover detected')

        if 'ta.crossunder' in pine_code:
            signals['uses_crossunder'] = True
            signals['short_conditions'].append('crossunder detected')

        # Check for comparisons
        if re.search(r'close\s*>\s*', pine_code) or re.search(r'>\s*close', pine_code):
            signals['uses_comparison'] = True
            signals['long_conditions'].append('price comparison')

        if re.search(r'close\s*<\s*', pine_code) or re.search(r'<\s*close', pine_code):
            signals['uses_comparison'] = True
            signals['short_conditions'].append('price comparison')

        return signals

    @staticmethod
    def suggest_risk_management(pine_code: str, indicators: Dict[str, List[str]]) -> Dict[str, Any]:
        """Suggest appropriate risk management based on strategy characteristics"""
        suggestions = {
            'stop_loss_type': 'fixed',
            'stop_loss_percent': 5.0,
            'use_atr_sl': False,
            'atr_multiplier': 2.0,
            'take_profit_type': 'rr_ratio',
            'rr_ratio': 2.0,
            'use_trailing_stop': True,
            'trailing_activation': 5.0,
            'trailing_percent': 3.0,
        }

        # If ATR is used, recommend ATR-based stop loss
        if 'atr' in indicators:
            suggestions['stop_loss_type'] = 'atr'
            suggestions['use_atr_sl'] = True
            suggestions['atr_multiplier'] = 2.5

        # If high-frequency indicators (short-term), tighter stops
        if 'rsi' in indicators or 'stochastic' in indicators:
            suggestions['stop_loss_percent'] = 3.0
            suggestions['trailing_percent'] = 2.0

        # If trend-following (MA-based), wider stops
        if 'sma' in indicators or 'ema' in indicators:
            suggestions['stop_loss_percent'] = 7.0
            suggestions['rr_ratio'] = 3.0

        return suggestions


class StrategyConverter:
    """Convert Pine Script to Python backtest strategy"""

    def __init__(self, script_id: str, pine_code: str, analysis: Dict[str, Any]):
        self.script_id = script_id
        self.pine_code = pine_code
        self.analysis = analysis
        self.analyzer = PineScriptAnalyzer()

    def generate_python_template(self) -> str:
        """Generate Python strategy template with risk management"""
        indicators = self.analyzer.detect_indicators(self.pine_code)
        signals = self.analyzer.detect_entry_signals(self.pine_code)
        risk_mgmt = self.analyzer.suggest_risk_management(self.pine_code, indicators)

        strategy_name = self.script_id.split('-')[-1].replace('-', '_')

        template = f'''"""
Enhanced Strategy: {self.analysis.get('title', self.script_id)}
Original Pine Script ID: {self.script_id}
Enhanced with Risk Management

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
from risk_management_patterns import EnhancedRiskManagementMixin


class {strategy_name}_Enhanced(Strategy, EnhancedRiskManagementMixin):
    """
    Enhanced version with risk management

    Detected Indicators:
{self._format_indicators(indicators)}

    Entry Signals:
{self._format_signals(signals)}
    """

    # Risk Management Parameters (from analysis)
    use_fixed_sl = {not risk_mgmt['use_atr_sl']}
    use_atr_sl = {risk_mgmt['use_atr_sl']}
    use_rr_tp = True
    use_trailing_stop = {risk_mgmt['use_trailing_stop']}

    sl_percent = {risk_mgmt['stop_loss_percent']}
    atr_sl_multiplier = {risk_mgmt['atr_multiplier']}
    rr_ratio = {risk_mgmt['rr_ratio']}
    trailing_activation = {risk_mgmt['trailing_activation']}
    trailing_percent = {risk_mgmt['trailing_percent']}

    # Strategy Parameters (TODO: Extract from Pine Script)
    # Add your strategy-specific parameters here

    def init(self):
        """Initialize indicators and risk management"""
        self.init_risk_management()

        # TODO: Initialize indicators based on Pine Script
        # Detected indicators: {list(indicators.keys())}

{self._generate_indicator_init(indicators)}

    def next(self):
        """Execute strategy logic"""
        # TODO: Implement entry/exit logic from Pine Script

        # Example long entry condition (replace with actual logic)
        # if self.some_indicator[-1] > threshold:
        #     if not self.position:
        #         self.buy()

        # Example short entry condition
        # if self.some_indicator[-1] < threshold:
        #     if not self.position:
        #         self.sell()

        # Risk management (KEEP THIS AT END)
        self.manage_risk()


def run_backtest():
    """Run backtest with BTC data"""
    import sys
    sys.path.append('/Users/mr.joo/Desktop/전략연구소')

    # Load data (adjust path as needed)
    data_path = '/Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/btc_data.csv'
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)

    # Ensure column names are capitalized
    df.columns = [col.capitalize() for col in df.columns]

    # Run backtest
    bt = Backtest(
        df,
        {strategy_name}_Enhanced,
        cash=100000,
        commission=0.001,
        exclusive_orders=True
    )

    stats = bt.run()
    print(stats)

    # Plot results
    bt.plot()

    return stats


if __name__ == '__main__':
    stats = run_backtest()
'''
        return template

    def _format_indicators(self, indicators: Dict[str, List[str]]) -> str:
        """Format indicators for docstring"""
        if not indicators:
            return "    - None detected (manual implementation required)"

        lines = []
        for indicator, matches in indicators.items():
            lines.append(f"    - {indicator.upper()}: {len(matches)} instance(s)")
        return '\n'.join(lines)

    def _format_signals(self, signals: Dict[str, Any]) -> str:
        """Format signals for docstring"""
        lines = []
        if signals['uses_crossover']:
            lines.append("    - Crossover signals detected")
        if signals['uses_crossunder']:
            lines.append("    - Crossunder signals detected")
        if signals['uses_comparison']:
            lines.append("    - Price comparison logic detected")

        if not lines:
            lines.append("    - Manual signal extraction required")

        return '\n'.join(lines)

    def _generate_indicator_init(self, indicators: Dict[str, List[str]]) -> str:
        """Generate indicator initialization code"""
        lines = []

        for indicator in indicators.keys():
            if indicator == 'sma':
                lines.append("        # self.sma = self.I(ta.sma, self.data.Close, length=20)")
            elif indicator == 'ema':
                lines.append("        # self.ema = self.I(ta.ema, self.data.Close, length=20)")
            elif indicator == 'rsi':
                lines.append("        # self.rsi = self.I(ta.rsi, self.data.Close, length=14)")
            elif indicator == 'macd':
                lines.append("        # macd = self.I(ta.macd, self.data.Close, fast=12, slow=26)")
            elif indicator == 'atr':
                lines.append("        # self.atr = self.I(ta.atr, self.data.High, self.data.Low, self.data.Close, length=14)")
            elif indicator == 'bollinger':
                lines.append("        # bb = self.I(ta.bbands, self.data.Close, length=20)")
            elif indicator == 'vwma':
                lines.append("        # self.vwma = self.I(ta.vwma, self.data.Close, self.data.Volume, length=20)")

        if not lines:
            lines.append("        # TODO: Add indicator initialization")

        return '\n'.join(lines)


class BatchProcessor:
    """Process multiple strategies in batch"""

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)

        # Load analysis results
        with open(ANALYSIS_RESULTS, 'r') as f:
            self.analysis_results = json.load(f)

    def get_strategy_from_db(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy from database"""
        cursor = self.conn.cursor()

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
            return None

        return {
            'script_id': row[0],
            'title': row[1],
            'author': row[2],
            'pine_code': row[3],
            'analysis': json.loads(row[4]) if row[4] else {}
        }

    def process_strategy(self, script_id: str) -> bool:
        """Process a single strategy"""
        print(f"\n{'='*80}")
        print(f"Processing: {script_id}")
        print(f"{'='*80}")

        # Get strategy from database
        strategy = self.get_strategy_from_db(script_id)

        if not strategy:
            print(f"ERROR: Strategy {script_id} not found in database")
            return False

        print(f"Title: {strategy['title']}")
        print(f"Author: {strategy['author']}")

        # Convert to Python template
        converter = StrategyConverter(
            script_id=strategy['script_id'],
            pine_code=strategy['pine_code'],
            analysis=strategy['analysis']
        )

        python_code = converter.generate_python_template()

        # Save Python file
        safe_filename = script_id.replace('/', '_').replace('\\', '_')
        output_file = self.output_dir / f"{safe_filename}_enhanced.py"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(python_code)

        print(f"✓ Generated Python template: {output_file}")

        # Save Pine Script for reference
        pine_file = self.output_dir / f"{safe_filename}_original.pine"
        with open(pine_file, 'w', encoding='utf-8') as f:
            f.write(strategy['pine_code'])

        print(f"✓ Saved original Pine Script: {pine_file}")

        # Save analysis
        analysis_file = self.output_dir / f"{safe_filename}_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(strategy['analysis'], f, indent=2)

        print(f"✓ Saved analysis: {analysis_file}")

        return True

    def process_batch(self, batch_number: int) -> Dict[str, Any]:
        """Process an entire batch"""
        if batch_number == 1:
            strategy_ids = BATCH_1_IDS
        elif batch_number == 2:
            strategy_ids = BATCH_2_IDS
        else:
            print(f"ERROR: Invalid batch number {batch_number}")
            return {}

        print(f"\n{'#'*80}")
        print(f"# BATCH {batch_number} PROCESSING")
        print(f"# Total strategies: {len(strategy_ids)}")
        print(f"{'#'*80}")

        results = {
            'batch': batch_number,
            'total': len(strategy_ids),
            'processed': 0,
            'failed': 0,
            'strategies': []
        }

        for i, script_id in enumerate(strategy_ids, 1):
            print(f"\n[{i}/{len(strategy_ids)}] Processing {script_id}...")

            success = self.process_strategy(script_id)

            if success:
                results['processed'] += 1
                results['strategies'].append({
                    'script_id': script_id,
                    'status': 'success'
                })
            else:
                results['failed'] += 1
                results['strategies'].append({
                    'script_id': script_id,
                    'status': 'failed'
                })

        # Save batch results
        batch_results_file = self.output_dir / f"batch_{batch_number}_results.json"
        with open(batch_results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n{'='*80}")
        print(f"BATCH {batch_number} COMPLETE")
        print(f"{'='*80}")
        print(f"Processed: {results['processed']}/{results['total']}")
        print(f"Failed: {results['failed']}/{results['total']}")
        print(f"Results saved to: {batch_results_file}")

        return results

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Batch process C-grade strategies')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--batch', type=int, choices=[1, 2],
                      help='Process batch 1 or 2')
    group.add_argument('--strategy', type=str,
                      help='Process single strategy by script_id')
    group.add_argument('--all', action='store_true',
                      help='Process all batches')

    args = parser.parse_args()

    processor = BatchProcessor()

    try:
        if args.strategy:
            processor.process_strategy(args.strategy)

        elif args.batch:
            processor.process_batch(args.batch)

        elif args.all:
            processor.process_batch(1)
            processor.process_batch(2)

    finally:
        processor.close()


if __name__ == '__main__':
    main()
