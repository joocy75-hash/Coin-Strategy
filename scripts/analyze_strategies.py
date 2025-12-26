#!/usr/bin/env python3
"""
전략 품질 분석 스크립트

수집된 전략에 대해:
1. Pine Script 코드 수집
2. 성과 지표 수집
3. 코드 분석 (리페인팅, 과적합 탐지)
4. 종합 점수 계산 및 순위화
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

# 분석 모듈 임포트
from src.analyzer.rule_based.repainting_detector import RepaintingDetector
from src.analyzer.rule_based.overfitting_detector import OverfittingDetector
from src.collector.performance_parser import PerformanceParser, PerformanceMetrics
from src.config import config


@dataclass
class StrategyAnalysis:
    """전략 분석 결과"""
    script_id: str
    title: str
    author: str
    likes: int
    script_url: str

    # 수집 데이터
    pine_code: Optional[str] = None
    pine_version: int = 5
    description: str = ""

    # 성과 지표
    performance: Dict = None

    # 분석 결과
    repainting_issues: List[Dict] = None
    overfitting_issues: List[Dict] = None

    # 점수
    quality_score: float = 0.0
    performance_score: float = 0.0
    code_score: float = 0.0
    total_score: float = 0.0

    # 에러
    error: Optional[str] = None

    def __post_init__(self):
        if self.performance is None:
            self.performance = {}
        if self.repainting_issues is None:
            self.repainting_issues = []
        if self.overfitting_issues is None:
            self.overfitting_issues = []


class StrategyAnalyzer:
    """전략 분석기"""

    # Pine Script 코드 추출용 JavaScript
    JS_EXTRACT_CODE = """
    () => {
        const body = document.body.innerText;
        if (body.includes("//@version=")) {
            const startIdx = body.indexOf("//@version=");
            // Get code from version marker (max 50KB)
            const chunk = body.slice(startIdx, startIdx + 50000);
            // Try to find end of code (common patterns)
            let endIdx = chunk.length;
            const endMarkers = ["\\nOpen-source script", "\\nOpen source script", "\\nDisclaimer", "\\nWarning:"];
            for (const marker of endMarkers) {
                const idx = chunk.indexOf(marker);
                if (idx > 0 && idx < endIdx) endIdx = idx;
            }
            return chunk.slice(0, endIdx).trim();
        }
        return null;
    }
    """

    # 설명 및 성과 추출용 JavaScript
    JS_EXTRACT_META = """
    () => {
        const result = {
            description: "",
            performance: {}
        };

        // 설명 추출
        const descElement = document.querySelector('[class*="description"], .tv-script-widget__description');
        if (descElement) {
            result.description = descElement.innerText.slice(0, 2000);
        }

        // 성과 지표 추출 (Strategy Tester 결과)
        const rows = document.querySelectorAll('[class*="report"] tr, [class*="performance"] tr, table tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td, th');
            if (cells.length >= 2) {
                const label = cells[0].innerText.trim();
                const value = cells[cells.length - 1].innerText.trim();
                if (label && value) {
                    result.performance[label] = value;
                }
            }
        });

        return result;
    }
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.repainting_detector = RepaintingDetector()
        self.overfitting_detector = OverfittingDetector()

    async def analyze_strategy(self, strategy: Dict) -> StrategyAnalysis:
        """단일 전략 분석"""
        analysis = StrategyAnalysis(
            script_id=strategy.get('scriptId', ''),
            title=strategy.get('title', ''),
            author=strategy.get('author', ''),
            likes=strategy.get('likes', 0),
            script_url=strategy.get('href', '')
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                # 전략 페이지 로드
                await page.goto(analysis.script_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # 메타데이터 추출 (설명, 성과)
                meta = await page.evaluate(self.JS_EXTRACT_META)
                analysis.description = meta.get('description', '')

                # 성과 지표 파싱
                if meta.get('performance'):
                    metrics = PerformanceParser.parse(meta['performance'])
                    analysis.performance = metrics.to_dict()

                # "Source code" 버튼 클릭하여 코드 표시
                source_btn = page.locator('button:has-text("Source code")')
                if await source_btn.count() > 0:
                    await source_btn.first.click()
                    await asyncio.sleep(2)

                    # Pine Script 코드 추출
                    analysis.pine_code = await page.evaluate(self.JS_EXTRACT_CODE)

                await browser.close()

            # 코드 분석 (Pine 코드가 있는 경우)
            if analysis.pine_code:
                analysis.pine_version = self._detect_version(analysis.pine_code)
                analysis.repainting_issues = self._check_repainting(analysis.pine_code)
                analysis.overfitting_issues = self._check_overfitting(analysis.pine_code, analysis.performance)

            # 점수 계산
            self._calculate_scores(analysis)

        except Exception as e:
            analysis.error = str(e)
            print(f"  ❌ Error: {e}", flush=True)

        return analysis

    def _detect_version(self, code: str) -> int:
        """Pine Script 버전 감지"""
        import re
        match = re.search(r'//@version=(\d+)', code)
        return int(match.group(1)) if match else 5

    def _check_repainting(self, code: str) -> List[Dict]:
        """리페인팅 체크"""
        try:
            result = self.repainting_detector.analyze(code)
            # RepaintingAnalysis 객체 반환됨
            issues = []
            for issue in result.issues:
                severity = "high" if "CRITICAL" in issue or "HIGH" in issue else "medium" if "MEDIUM" in issue else "low"
                issues.append({"message": issue, "severity": severity})
            return issues
        except Exception as e:
            return [{"error": str(e), "severity": "low"}]

    def _check_overfitting(self, code: str, performance: Dict) -> List[Dict]:
        """과적합 체크"""
        try:
            result = self.overfitting_detector.analyze(code, performance)
            # OverfittingAnalysis 객체 반환됨
            issues = []
            for concern in result.concerns:
                issues.append({
                    "message": concern,
                    "severity": result.risk_level
                })
            return issues
        except Exception as e:
            return [{"error": str(e), "severity": "low"}]

    def _calculate_scores(self, analysis: StrategyAnalysis):
        """점수 계산"""

        # 1. 코드 점수 (100점 만점)
        code_score = 100

        # 리페인팅 이슈 감점
        for issue in analysis.repainting_issues:
            severity = issue.get('severity', 'low')
            if severity == 'high':
                code_score -= 30
            elif severity == 'medium':
                code_score -= 15
            else:
                code_score -= 5

        # 과적합 이슈 감점
        for issue in analysis.overfitting_issues:
            severity = issue.get('severity', 'low')
            if severity == 'high':
                code_score -= 25
            elif severity == 'medium':
                code_score -= 10
            else:
                code_score -= 5

        # 코드가 없으면 0점
        if not analysis.pine_code:
            code_score = 0

        analysis.code_score = max(0, code_score)

        # 2. 성과 점수 (100점 만점)
        perf = analysis.performance
        performance_score = 50  # 기본 점수

        # 수익률
        net_profit = perf.get('net_profit_percent', perf.get('net_profit', 0))
        if net_profit:
            if net_profit > 100:
                performance_score += 20
            elif net_profit > 50:
                performance_score += 15
            elif net_profit > 20:
                performance_score += 10
            elif net_profit < 0:
                performance_score -= 20

        # Profit Factor
        pf = perf.get('profit_factor', 0)
        if pf:
            if pf >= 2:
                performance_score += 15
            elif pf >= 1.5:
                performance_score += 10
            elif pf >= 1:
                performance_score += 5
            else:
                performance_score -= 10

        # Drawdown
        mdd = perf.get('max_drawdown_percent', 0)
        if mdd:
            if abs(mdd) > 50:
                performance_score -= 20
            elif abs(mdd) > 30:
                performance_score -= 10

        # 거래 수
        trades = perf.get('total_trades', 0)
        if trades:
            if trades >= 100:
                performance_score += 10
            elif trades >= 50:
                performance_score += 5
            elif trades < 20:
                performance_score -= 10

        analysis.performance_score = max(0, min(100, performance_score))

        # 3. 품질 점수 (인기도 반영)
        likes = analysis.likes
        if likes >= 1000:
            quality_score = 100
        elif likes >= 500:
            quality_score = 80
        elif likes >= 200:
            quality_score = 60
        elif likes >= 100:
            quality_score = 40
        else:
            quality_score = 20

        analysis.quality_score = quality_score

        # 4. 종합 점수 (가중 평균)
        # 코드 40% + 성과 40% + 인기도 20%
        analysis.total_score = (
            analysis.code_score * 0.4 +
            analysis.performance_score * 0.4 +
            analysis.quality_score * 0.2
        )


class QualityFilter:
    """고품질 전략 필터링"""

    def __init__(self):
        self.min_code_score = config.min_code_score
        self.min_total_score = config.min_total_score
        self.require_no_repainting = config.require_no_repainting
        self.max_overfitting_issues = config.max_overfitting_issues

    def filter_strategies(self, strategies: List[Dict]) -> tuple[List[Dict], Dict]:
        """전략 필터링 및 통계 반환"""
        if not strategies:
            return [], {'total': 0, 'passed': 0, 'pass_rate': 0,
                       'failed_code_score': 0, 'failed_total_score': 0,
                       'failed_repainting': 0, 'failed_overfitting': 0}

        quality_strategies = []
        stats = {
            'total': len(strategies),
            'passed': 0,
            'failed_code_score': 0,
            'failed_total_score': 0,
            'failed_repainting': 0,
            'failed_overfitting': 0
        }

        for strategy in strategies:
            passed, reasons = self._meets_criteria(strategy)
            if passed:
                quality_strategies.append(strategy)
                stats['passed'] += 1
            else:
                for reason in reasons:
                    if 'code_score' in reason:
                        stats['failed_code_score'] += 1
                    elif 'total_score' in reason:
                        stats['failed_total_score'] += 1
                    elif 'repainting' in reason:
                        stats['failed_repainting'] += 1
                    elif 'overfitting' in reason:
                        stats['failed_overfitting'] += 1

        stats['pass_rate'] = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        return quality_strategies, stats

    def _meets_criteria(self, strategy: Dict) -> tuple[bool, List[str]]:
        """전략이 품질 기준을 만족하는지 확인"""
        reasons = []

        code_score = strategy.get('code_score', 0)
        total_score = strategy.get('total_score', 0)
        repainting_issues = strategy.get('repainting_issues', [])
        overfitting_issues = strategy.get('overfitting_issues', [])

        if code_score < self.min_code_score:
            reasons.append(f"code_score {code_score} < {self.min_code_score}")

        if total_score < self.min_total_score:
            reasons.append(f"total_score {total_score:.0f} < {self.min_total_score}")

        if self.require_no_repainting and len(repainting_issues) > 0:
            reasons.append(f"repainting issues: {len(repainting_issues)}개")

        if len(overfitting_issues) > self.max_overfitting_issues:
            reasons.append(f"overfitting issues: {len(overfitting_issues)}개 > {self.max_overfitting_issues}")

        return len(reasons) == 0, reasons


async def main():
    # 수집된 전략 파일 로드
    data_dir = Path("data")
    json_files = sorted(data_dir.glob("collected_*.json"), reverse=True)

    if not json_files:
        print("수집된 전략 파일이 없습니다. quick_collect.py를 먼저 실행하세요.")
        return

    latest_file = json_files[0]
    print(f"분석 대상: {latest_file}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        strategies = json.load(f)

    print(f"총 {len(strategies)}개 전략 분석 시작\n")

    # 분석 실행
    analyzer = StrategyAnalyzer(headless=True)
    results = []

    for i, strategy in enumerate(strategies, 1):
        print(f"[{i}/{len(strategies)}] {strategy['title'][:50]}...", flush=True)

        analysis = await analyzer.analyze_strategy(strategy)
        results.append(asdict(analysis))

        # 간단한 결과 출력
        if analysis.pine_code:
            print(f"  ✓ 코드 수집 완료 (v{analysis.pine_version})", flush=True)
            if analysis.repainting_issues:
                print(f"  ⚠️ 리페인팅 이슈: {len(analysis.repainting_issues)}개", flush=True)
            if analysis.overfitting_issues:
                print(f"  ⚠️ 과적합 이슈: {len(analysis.overfitting_issues)}개", flush=True)
        else:
            print(f"  ⚠️ 코드 없음 (protected)", flush=True)

        print(f"  📊 점수: 코드={analysis.code_score:.0f}, 성과={analysis.performance_score:.0f}, 종합={analysis.total_score:.0f}", flush=True)

        # Rate limiting
        await asyncio.sleep(2)

    # 점수순 정렬
    results.sort(key=lambda x: x['total_score'], reverse=True)

    # === 품질 필터링 ===
    quality_filter = QualityFilter()
    quality_strategies, filter_stats = quality_filter.filter_strategies(results)

    # 전체 분석 결과 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analyzed_path = f"data/analyzed_{timestamp}.json"
    with open(analyzed_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 전체 분석 결과 저장: {analyzed_path}")

    # 고품질 전략만 별도 저장
    quality_path = f"data/quality_{timestamp}.json"
    with open(quality_path, 'w', encoding='utf-8') as f:
        json.dump(quality_strategies, f, ensure_ascii=False, indent=2)
    print(f"✓ 고품질 전략 저장: {quality_path}")

    # 필터링 통계 출력
    print("\n" + "=" * 60)
    print("📊 품질 필터링 통계")
    print("=" * 60)
    print(f"전체 분석: {filter_stats['total']}개")
    print(f"통과: {filter_stats['passed']}개 ({filter_stats['pass_rate']:.1f}%)")
    print(f"\n실패 사유:")
    print(f"  • 코드 점수 미달 (< {config.min_code_score}): {filter_stats['failed_code_score']}개")
    print(f"  • 종합 점수 미달 (< {config.min_total_score}): {filter_stats['failed_total_score']}개")
    print(f"  • 리페인팅 이슈: {filter_stats['failed_repainting']}개")
    print(f"  • 과적합 이슈 (> {config.max_overfitting_issues}개): {filter_stats['failed_overfitting']}개")

    # 상위 5개 출력 (고품질 전략 기준)
    print("\n" + "=" * 60)
    print("🏆 상위 5개 고품질 전략")
    print("=" * 60)

    display_list = quality_strategies[:5] if quality_strategies else results[:5]
    if not quality_strategies:
        print("\n⚠️ 품질 기준을 통과한 전략이 없어 전체 상위 5개를 표시합니다.\n")

    for i, r in enumerate(display_list, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   작성자: {r['author']} | 좋아요: {r['likes']}")
        print(f"   종합: {r['total_score']:.0f}점 (코드: {r['code_score']:.0f}, 성과: {r['performance_score']:.0f}, 품질: {r['quality_score']:.0f})")

        if r['repainting_issues']:
            print(f"   ⚠️ 리페인팅: {len(r['repainting_issues'])}개 이슈")
        if r['overfitting_issues']:
            print(f"   ⚠️ 과적합: {len(r['overfitting_issues'])}개 이슈")


if __name__ == "__main__":
    asyncio.run(main())
