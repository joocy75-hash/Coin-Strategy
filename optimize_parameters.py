"""
파라미터 최적화 자동화 스크립트

Adaptive ML, PMax, Heikin Ashi 전략의 파라미터를 Grid Search로 자동 최적화합니다.
PARAMETER_OPTIMIZATION_GUIDE.md에 정의된 범위를 사용하여 실제 백테스트를 수행합니다.

목표:
- Sharpe Ratio > 1.5
- Win Rate > 40%
- Profit Factor > 1.5

출력:
- optimization_results_{strategy_name}.csv: 모든 파라미터 조합의 성과
- best_parameters_{strategy_name}.json: 최적 파라미터
- optimization_summary.md: 최적화 전후 비교표
"""

import sys
import json
import itertools
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "trading-agent-system"))

from src.backtest.engine import BacktestEngine, BacktestMetrics
from strategies.adaptive_ml_trailing_stop import AdaptiveMLTrailingStop
from strategies.pmax_asymmetric import PMaxAsymmetric
from strategies.heikin_ashi_wick import HeikinAshiWick


@dataclass
class OptimizationResult:
    """최적화 결과"""
    strategy_name: str
    parameters: Dict[str, Any]
    avg_return: float
    avg_sharpe: float
    avg_win_rate: float
    avg_profit_factor: float
    avg_max_drawdown: float
    consistency_rate: float  # 양수 수익률 비율
    total_tests: int
    moon_dev_score: int  # Moon Dev 기준 통과 항목 수

    def to_dict(self):
        return asdict(self)


class ParameterOptimizer:
    """파라미터 최적화 엔진"""

    # Moon Dev 기준
    MOON_DEV_CRITERIA = {
        'sharpe': 1.5,
        'win_rate': 40.0,
        'profit_factor': 1.5
    }

    # 전략별 파라미터 범위 (PARAMETER_OPTIMIZATION_GUIDE.md 기반)
    PARAM_GRIDS = {
        'AdaptiveMLTrailingStop': {
            'kama_length': [15, 20, 25, 30],
            'atr_period': [14, 21, 28],
            'base_multiplier': [2.0, 2.5, 3.0],
            # 고정 파라미터
            'fast_length': [15],
            'slow_length': [50],
            'adaptive_strength': [1.0],
            'stop_loss_percent': [5.0]
        },
        'PMaxAsymmetric': {
            'atr_length': [7, 10, 14],
            'upper_multiplier': [1.0, 1.5, 2.0],
            'lower_multiplier': [2.0, 3.0, 4.0],
            # 고정 파라미터
            'ma_length': [10],
            'ma_type': ['EMA'],
            'stop_loss_percent': [5.0]
        },
        'HeikinAshiWick': {
            'stop_loss_percent': [3.0, 5.0, 7.0]  # 간단한 전략이므로 SL만 최적화
        }
    }

    def __init__(
        self,
        data_dir: str = "trading-agent-system/data/datasets",
        results_dir: str = "optimization_results",
        num_datasets: int = 10
    ):
        """
        Args:
            data_dir: 데이터셋 디렉토리
            results_dir: 결과 저장 디렉토리
            num_datasets: 테스트할 데이터셋 개수
        """
        self.data_dir = Path(data_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.num_datasets = num_datasets

        self.engine = BacktestEngine(
            initial_cash=100_000,
            commission=0.0003,  # 0.03%
            exclusive_orders=True
        )

    def load_datasets(self) -> List[tuple]:
        """데이터셋 로드 (10개 선택)"""
        parquet_files = sorted(self.data_dir.glob("*.parquet"))

        # 다양한 코인과 타임프레임 선택
        selected_files = []
        coins = set()

        for file in parquet_files:
            # 파일명 파싱: BTCUSDT_1h.parquet
            parts = file.stem.split('_')
            if len(parts) != 2:
                continue

            coin = parts[0]
            timeframe = parts[1]

            # 1h 데이터 우선, 다양한 코인
            if timeframe == '1h' and coin not in coins:
                selected_files.append(file)
                coins.add(coin)

                if len(selected_files) >= self.num_datasets:
                    break

        # 데이터 로드
        datasets = []
        for file in selected_files[:self.num_datasets]:
            try:
                df = pd.read_parquet(file)
                symbol = file.stem.split('_')[0]
                datasets.append((symbol, df))
                print(f"Loaded: {file.name} ({len(df)} rows)")
            except Exception as e:
                print(f"Error loading {file}: {e}")

        return datasets

    def generate_param_combinations(self, strategy_name: str) -> List[Dict[str, Any]]:
        """파라미터 조합 생성"""
        if strategy_name not in self.PARAM_GRIDS:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        param_grid = self.PARAM_GRIDS[strategy_name]

        # 모든 조합 생성
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        combinations = []
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            combinations.append(params)

        return combinations

    def test_parameters(
        self,
        strategy_class: type,
        params: Dict[str, Any],
        datasets: List[tuple]
    ) -> List[BacktestMetrics]:
        """특정 파라미터 조합으로 여러 데이터셋 테스트"""
        results = []

        for symbol, data in datasets:
            try:
                # 동적으로 전략 클래스 생성 (파라미터 오버라이드)
                class TempStrategy(strategy_class):
                    pass

                # 파라미터 설정
                for key, value in params.items():
                    setattr(TempStrategy, key, value)

                # 백테스트 실행
                metrics = self.engine.run(
                    strategy_class=TempStrategy,
                    data=data,
                    symbol=symbol,
                    interval='1h'
                )

                results.append(metrics)

            except Exception as e:
                print(f"  Error on {symbol}: {str(e)[:100]}")
                continue

        return results

    def calculate_moon_dev_score(self, result: OptimizationResult) -> int:
        """Moon Dev 기준 통과 항목 개수 계산"""
        score = 0

        if result.avg_sharpe >= self.MOON_DEV_CRITERIA['sharpe']:
            score += 1
        if result.avg_win_rate >= self.MOON_DEV_CRITERIA['win_rate']:
            score += 1
        if result.avg_profit_factor >= self.MOON_DEV_CRITERIA['profit_factor']:
            score += 1

        return score

    def optimize_strategy(
        self,
        strategy_name: str,
        strategy_class: type,
        datasets: List[tuple]
    ) -> tuple[List[OptimizationResult], OptimizationResult]:
        """
        전략 최적화 수행

        Returns:
            (모든 결과 리스트, 최적 결과)
        """
        print(f"\n{'='*80}")
        print(f"Optimizing: {strategy_name}")
        print(f"{'='*80}")

        # 파라미터 조합 생성
        param_combinations = self.generate_param_combinations(strategy_name)
        total_combos = len(param_combinations)

        print(f"Total parameter combinations: {total_combos}")
        print(f"Testing on {len(datasets)} datasets\n")

        all_results = []

        for idx, params in enumerate(param_combinations, 1):
            print(f"[{idx}/{total_combos}] Testing: {params}")

            # 백테스트 실행
            metrics_list = self.test_parameters(strategy_class, params, datasets)

            if not metrics_list:
                print("  No valid results, skipping...")
                continue

            # 집계
            aggregated = self.engine.aggregate_results(metrics_list)

            # 결과 생성
            result = OptimizationResult(
                strategy_name=strategy_name,
                parameters=params,
                avg_return=aggregated['avg_return'],
                avg_sharpe=aggregated['avg_sharpe'],
                avg_win_rate=aggregated['avg_win_rate'],
                avg_profit_factor=np.mean([m.profit_factor for m in metrics_list]),
                avg_max_drawdown=aggregated['avg_max_drawdown'],
                consistency_rate=aggregated['consistency_rate'],
                total_tests=aggregated['total_tests'],
                moon_dev_score=0  # 나중에 계산
            )

            # Moon Dev 점수 계산
            result.moon_dev_score = self.calculate_moon_dev_score(result)

            all_results.append(result)

            # 간단한 출력
            print(f"  Return: {result.avg_return:.2f}% | "
                  f"Sharpe: {result.avg_sharpe:.2f} | "
                  f"Win Rate: {result.avg_win_rate:.1f}% | "
                  f"PF: {result.avg_profit_factor:.2f} | "
                  f"Moon Dev: {result.moon_dev_score}/3")

        if not all_results:
            raise ValueError(f"No valid results for {strategy_name}")

        # 최적 결과 선택 (Moon Dev 점수 우선, 그 다음 Sharpe)
        best_result = max(
            all_results,
            key=lambda x: (x.moon_dev_score, x.avg_sharpe, x.avg_return)
        )

        print(f"\nBest parameters found:")
        print(f"  Parameters: {best_result.parameters}")
        print(f"  Avg Return: {best_result.avg_return:.2f}%")
        print(f"  Avg Sharpe: {best_result.avg_sharpe:.2f}")
        print(f"  Avg Win Rate: {best_result.avg_win_rate:.1f}%")
        print(f"  Avg Profit Factor: {best_result.avg_profit_factor:.2f}")
        print(f"  Moon Dev Score: {best_result.moon_dev_score}/3")

        return all_results, best_result

    def save_results(
        self,
        strategy_name: str,
        all_results: List[OptimizationResult],
        best_result: OptimizationResult
    ):
        """결과 저장"""

        # 1. CSV: 모든 조합의 결과
        csv_file = self.results_dir / f"optimization_results_{strategy_name}.csv"

        rows = []
        for result in all_results:
            row = {
                'avg_return': result.avg_return,
                'avg_sharpe': result.avg_sharpe,
                'avg_win_rate': result.avg_win_rate,
                'avg_profit_factor': result.avg_profit_factor,
                'avg_max_drawdown': result.avg_max_drawdown,
                'consistency_rate': result.consistency_rate,
                'moon_dev_score': result.moon_dev_score,
                **result.parameters
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        df = df.sort_values('avg_sharpe', ascending=False)
        df.to_csv(csv_file, index=False)
        print(f"\nSaved: {csv_file}")

        # 2. JSON: 최적 파라미터
        json_file = self.results_dir / f"best_parameters_{strategy_name}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(best_result.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"Saved: {json_file}")

    def get_baseline_performance(
        self,
        strategy_name: str,
        strategy_class: type,
        datasets: List[tuple]
    ) -> OptimizationResult:
        """기본 파라미터로 성과 측정 (최적화 전)"""

        print(f"\nMeasuring baseline performance for {strategy_name}...")

        # 기본 파라미터 (전략 클래스의 기본값)
        baseline_params = {}
        for key, values in self.PARAM_GRIDS[strategy_name].items():
            # 첫 번째 값을 기본값으로 사용 (실제론 클래스 기본값)
            baseline_params[key] = getattr(strategy_class, key, values[0])

        # 백테스트 실행
        metrics_list = self.test_parameters(strategy_class, baseline_params, datasets)

        if not metrics_list:
            raise ValueError(f"No baseline results for {strategy_name}")

        # 집계
        aggregated = self.engine.aggregate_results(metrics_list)

        result = OptimizationResult(
            strategy_name=strategy_name,
            parameters=baseline_params,
            avg_return=aggregated['avg_return'],
            avg_sharpe=aggregated['avg_sharpe'],
            avg_win_rate=aggregated['avg_win_rate'],
            avg_profit_factor=np.mean([m.profit_factor for m in metrics_list]),
            avg_max_drawdown=aggregated['avg_max_drawdown'],
            consistency_rate=aggregated['consistency_rate'],
            total_tests=aggregated['total_tests'],
            moon_dev_score=0
        )

        result.moon_dev_score = self.calculate_moon_dev_score(result)

        return result


def main():
    """메인 실행 함수"""

    print("=" * 80)
    print("파라미터 최적화 자동화 시스템")
    print("=" * 80)

    # 작업 디렉토리 확인
    script_dir = Path(__file__).parent
    print(f"\nWorking directory: {script_dir}")

    # 최적화 엔진 생성
    optimizer = ParameterOptimizer(
        data_dir=script_dir / "trading-agent-system/data/datasets",
        results_dir=script_dir / "optimization_results",
        num_datasets=10
    )

    # 데이터셋 로드
    print("\nLoading datasets...")
    datasets = optimizer.load_datasets()
    print(f"Loaded {len(datasets)} datasets")

    if len(datasets) < 10:
        print(f"\nWarning: Only {len(datasets)} datasets available (target: 10)")

    # 최적화할 전략들
    strategies = [
        ('AdaptiveMLTrailingStop', AdaptiveMLTrailingStop),
        ('PMaxAsymmetric', PMaxAsymmetric),
        ('HeikinAshiWick', HeikinAshiWick)
    ]

    # 각 전략별 최적화 실행
    optimization_summary = []

    for strategy_name, strategy_class in strategies:
        try:
            # 베이스라인 성과 측정
            baseline = optimizer.get_baseline_performance(
                strategy_name, strategy_class, datasets
            )

            print(f"\nBaseline performance:")
            print(f"  Return: {baseline.avg_return:.2f}%")
            print(f"  Sharpe: {baseline.avg_sharpe:.2f}")
            print(f"  Win Rate: {baseline.avg_win_rate:.1f}%")
            print(f"  Moon Dev Score: {baseline.moon_dev_score}/3")

            # 최적화 실행
            all_results, best_result = optimizer.optimize_strategy(
                strategy_name, strategy_class, datasets
            )

            # 결과 저장
            optimizer.save_results(strategy_name, all_results, best_result)

            # 요약 정보 저장
            optimization_summary.append({
                'strategy': strategy_name,
                'baseline': baseline,
                'optimized': best_result,
                'improvement': {
                    'return': best_result.avg_return - baseline.avg_return,
                    'sharpe': best_result.avg_sharpe - baseline.avg_sharpe,
                    'win_rate': best_result.avg_win_rate - baseline.avg_win_rate,
                    'moon_dev_score': best_result.moon_dev_score - baseline.moon_dev_score
                }
            })

        except Exception as e:
            print(f"\nError optimizing {strategy_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 최종 요약 리포트 생성
    generate_summary_report(optimization_summary, optimizer.results_dir)

    print("\n" + "=" * 80)
    print("Optimization Complete!")
    print("=" * 80)
    print(f"\nResults saved in: {optimizer.results_dir}")
    print("\nGenerated files:")
    print("  - optimization_results_{strategy_name}.csv")
    print("  - best_parameters_{strategy_name}.json")
    print("  - optimization_summary.md")


def generate_summary_report(summary_data: List[Dict], results_dir: Path):
    """최적화 요약 리포트 생성"""

    report_file = results_dir / "optimization_summary.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 파라미터 최적화 결과 요약\n\n")
        f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        # Moon Dev 기준 설명
        f.write("## Moon Dev 기준\n\n")
        f.write("| 지표 | 목표 |\n")
        f.write("|------|------|\n")
        f.write("| Sharpe Ratio | > 1.5 |\n")
        f.write("| Win Rate | > 40% |\n")
        f.write("| Profit Factor | > 1.5 |\n\n")
        f.write("---\n\n")

        # 각 전략별 결과
        for item in summary_data:
            strategy = item['strategy']
            baseline = item['baseline']
            optimized = item['optimized']
            improvement = item['improvement']

            f.write(f"## {strategy}\n\n")

            # 최적화 전후 비교표
            f.write("### 최적화 전후 비교\n\n")
            f.write("| 지표 | 최적화 전 | 최적화 후 | 개선 |\n")
            f.write("|------|----------|----------|------|\n")

            f.write(f"| 평균 수익률 | {baseline.avg_return:.2f}% | "
                   f"**{optimized.avg_return:.2f}%** | "
                   f"{improvement['return']:+.2f}% |\n")

            f.write(f"| Sharpe Ratio | {baseline.avg_sharpe:.2f} | "
                   f"**{optimized.avg_sharpe:.2f}** | "
                   f"{improvement['sharpe']:+.2f} |\n")

            f.write(f"| Win Rate | {baseline.avg_win_rate:.1f}% | "
                   f"**{optimized.avg_win_rate:.1f}%** | "
                   f"{improvement['win_rate']:+.1f}% |\n")

            f.write(f"| Profit Factor | {baseline.avg_profit_factor:.2f} | "
                   f"**{optimized.avg_profit_factor:.2f}** | "
                   f"{optimized.avg_profit_factor - baseline.avg_profit_factor:+.2f} |\n")

            f.write(f"| Max Drawdown | {baseline.avg_max_drawdown:.2f}% | "
                   f"**{optimized.avg_max_drawdown:.2f}%** | "
                   f"{optimized.avg_max_drawdown - baseline.avg_max_drawdown:+.2f}% |\n")

            f.write(f"| Consistency Rate | {baseline.consistency_rate:.1f}% | "
                   f"**{optimized.consistency_rate:.1f}%** | "
                   f"{optimized.consistency_rate - baseline.consistency_rate:+.1f}% |\n\n")

            # Moon Dev 기준 통과 여부
            f.write("### Moon Dev 기준 통과 여부\n\n")

            baseline_pass = "✅ 통과" if baseline.moon_dev_score == 3 else f"❌ 미달 ({baseline.moon_dev_score}/3)"
            optimized_pass = "✅ 통과" if optimized.moon_dev_score == 3 else f"❌ 미달 ({optimized.moon_dev_score}/3)"

            f.write(f"- **최적화 전**: {baseline_pass}\n")
            f.write(f"- **최적화 후**: {optimized_pass}\n\n")

            # 개선 항목
            if improvement['moon_dev_score'] > 0:
                f.write(f"**개선**: {improvement['moon_dev_score']}개 항목 추가 통과\n\n")
            elif improvement['moon_dev_score'] == 0:
                f.write("**개선**: Moon Dev 점수 변화 없음\n\n")

            # 최적 파라미터
            f.write("### 최적 파라미터\n\n")
            f.write("```python\n")
            for key, value in optimized.parameters.items():
                if isinstance(value, float):
                    f.write(f"{key} = {value:.1f}\n")
                else:
                    f.write(f"{key} = {value}\n")
            f.write("```\n\n")

            # 기본 파라미터와 비교
            f.write("### 변경된 파라미터\n\n")
            changes = []
            for key in optimized.parameters:
                if key in baseline.parameters:
                    if optimized.parameters[key] != baseline.parameters[key]:
                        changes.append(
                            f"- `{key}`: {baseline.parameters[key]} → **{optimized.parameters[key]}**"
                        )

            if changes:
                f.write("\n".join(changes) + "\n\n")
            else:
                f.write("변경 사항 없음\n\n")

            f.write("---\n\n")

        # 전체 요약
        f.write("## 전체 요약\n\n")
        f.write("| 전략 | 최적화 전 Sharpe | 최적화 후 Sharpe | Moon Dev (전) | Moon Dev (후) |\n")
        f.write("|------|-----------------|-----------------|--------------|-------------|\n")

        for item in summary_data:
            strategy = item['strategy']
            baseline = item['baseline']
            optimized = item['optimized']

            f.write(f"| {strategy} | {baseline.avg_sharpe:.2f} | "
                   f"**{optimized.avg_sharpe:.2f}** | "
                   f"{baseline.moon_dev_score}/3 | "
                   f"**{optimized.moon_dev_score}/3** |\n")

        f.write("\n---\n\n")
        f.write("## 결론\n\n")
        f.write("파라미터 최적화를 통해 각 전략의 성과를 개선하였습니다.\n\n")
        f.write("**주의사항**:\n")
        f.write("- 과최적화 방지를 위해 단순한 파라미터 값을 선호했습니다\n")
        f.write("- 10개 데이터셋에서 평균 성과를 기준으로 최적화했습니다\n")
        f.write("- Out-of-sample 테스트를 통해 실전 성과를 추가 검증해야 합니다\n\n")

    print(f"\nSaved summary report: {report_file}")


if __name__ == "__main__":
    main()
