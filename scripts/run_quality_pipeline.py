#!/usr/bin/env python3
"""
고품질 전략 수집 자동화 파이프라인

24시간 서버 운영용 - 품질 우선 수집
1. TradingView에서 전략 수집 (min_likes 200+)
2. Pine Script 코드 추출 및 분석
3. 품질 필터링 (리페인팅/과적합 검사)
4. 고품질 전략만 별도 저장

Usage:
    python scripts/run_quality_pipeline.py
    python scripts/run_quality_pipeline.py --max-count 100 --min-likes 300
    python scripts/run_quality_pipeline.py --continuous --interval 3600
"""

import asyncio
import argparse
import json
import sys
import signal
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from src.analyzer.rule_based.repainting_detector import RepaintingDetector
from src.analyzer.rule_based.overfitting_detector import OverfittingDetector
from src.config import config  # 전역 인스턴스 사용 (analyze_strategies.py와 통일)
from src.collector.quality_scorer import QualityMetrics, PreCollectionFilter, get_author_trust_score

# 전역 종료 플래그
SHUTDOWN_FLAG = False


def signal_handler(signum, frame):
    global SHUTDOWN_FLAG
    print("\n⚠️ 종료 신호 수신. 현재 작업 완료 후 종료합니다...")
    SHUTDOWN_FLAG = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# === JavaScript 코드 ===
JS_EXTRACT_STRATEGIES = """
() => {
    const articles = document.querySelectorAll("article");
    return Array.from(articles).map(art => {
        const titleLink = art.querySelector('a[data-qa-id="ui-lib-card-link-title"]');
        const title = titleLink ? titleLink.textContent.trim() : "";
        const href = titleLink ? titleLink.getAttribute("href") : "";
        const scriptIdMatch = href.match(/script\\/([^/]+)/);
        const scriptId = scriptIdMatch ? scriptIdMatch[1] : "";

        let author = "";
        const allLinks = art.querySelectorAll("a");
        for (const link of allLinks) {
            const h = link.getAttribute("href") || "";
            if (h.includes("/u/")) {
                author = link.textContent.trim().replace(/^by\\s*/i, "");
                break;
            }
        }

        // === 좋아요(Boosts) 수집 ===
        let likes = 0;
        const boostBtn = art.querySelector('[data-qa-id="ui-lib-card-like-button"]');
        if (boostBtn) {
            const ariaLabel = boostBtn.querySelector("[aria-label]");
            if (ariaLabel) {
                const labelText = ariaLabel.getAttribute("aria-label") || "";
                const match = labelText.match(/(\\d+)\\s*boost/i);
                if (match) likes = parseInt(match[1]) || 0;
            }
        }
        if (likes === 0 && boostBtn) {
            const digits = boostBtn.querySelectorAll('[class*="digit"]');
            if (digits.length > 0) {
                let numStr = "";
                digits.forEach(d => numStr += d.textContent.trim());
                likes = parseInt(numStr) || 0;
            }
        }

        // === 댓글 수 수집 ===
        let comments = 0;
        const commentBtn = art.querySelector('[data-qa-id="ui-lib-card-comment-button"], [class*="comment"]');
        if (commentBtn) {
            const commentText = commentBtn.textContent.trim();
            const commentMatch = commentText.match(/(\\d+)/);
            if (commentMatch) comments = parseInt(commentMatch[1]) || 0;
        }

        // === 조회수 수집 ===
        let views = 0;
        const viewsEl = art.querySelector('[class*="views"], [class*="eye"]');
        if (viewsEl) {
            const viewsText = viewsEl.textContent.trim();
            const viewsMatch = viewsText.match(/([\\d.]+)([KkMm])?/);
            if (viewsMatch) {
                let num = parseFloat(viewsMatch[1]);
                const suffix = viewsMatch[2];
                if (suffix === 'K' || suffix === 'k') num *= 1000;
                if (suffix === 'M' || suffix === 'm') num *= 1000000;
                views = Math.floor(num);
            }
        }

        // === 팔로워/사용자 수 (있는 경우) ===
        let users = 0;
        const usersEl = art.querySelector('[class*="users"], [class*="follower"]');
        if (usersEl) {
            const usersText = usersEl.textContent.trim();
            const usersMatch = usersText.match(/([\\d.]+)([KkMm])?/);
            if (usersMatch) {
                let num = parseFloat(usersMatch[1]);
                const suffix = usersMatch[2];
                if (suffix === 'K' || suffix === 'k') num *= 1000;
                if (suffix === 'M' || suffix === 'm') num *= 1000000;
                users = Math.floor(num);
            }
        }

        const scriptIcon = art.querySelector('[class*="script-icon-wrap"]');
        const iconTitle = scriptIcon ? scriptIcon.getAttribute("title") || "" : "";
        const isOpenSource = !iconTitle.toLowerCase().includes("invite") &&
                             !iconTitle.toLowerCase().includes("protected");

        const descEl = art.querySelector('a[data-qa-id="ui-lib-card-link-paragraph"]');
        const description = descEl ? descEl.textContent.trim().slice(0, 500) : "";

        // === 인기도 종합 점수 계산 ===
        // 좋아요 40% + 댓글 30% + 조회수 20% + 사용자 10%
        const popularityScore = (likes * 1.0) + (comments * 5) + (views * 0.01) + (users * 0.5);

        return {
            scriptId, title, author, likes, comments, views, users,
            popularityScore, href, isOpenSource, description
        };
    }).filter(card => card.scriptId && card.title);
}
"""

JS_EXTRACT_CODE = """
() => {
    const body = document.body.innerText;
    if (body.includes("//@version=")) {
        const startIdx = body.indexOf("//@version=");
        const chunk = body.slice(startIdx, startIdx + 50000);
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

# 전략 상세 페이지에서 품질 지표 추출
JS_EXTRACT_QUALITY_METRICS = """
() => {
    const result = {
        likes: 0,
        views: 0,
        comments: 0,
        authorFollowers: 0,
        authorScriptsCount: 0,
        pineVersion: 5,
        isOpenSource: false,
        isVerified: false
    };

    // 좋아요/Boosts
    const boostElements = document.querySelectorAll('[class*="boost"], [data-name*="boost"]');
    boostElements.forEach(el => {
        const text = el.textContent.trim();
        const match = text.match(/(\\d[\\d,]*)/);
        if (match) {
            const num = parseInt(match[1].replace(/,/g, ''));
            if (num > result.likes) result.likes = num;
        }
    });

    // 조회수
    const viewsEl = document.querySelector('[class*="views"]');
    if (viewsEl) {
        const text = viewsEl.textContent.trim();
        const match = text.match(/([\\d,.]+)([KkMm])?/);
        if (match) {
            let num = parseFloat(match[1].replace(/,/g, ''));
            if (match[2] === 'K' || match[2] === 'k') num *= 1000;
            if (match[2] === 'M' || match[2] === 'm') num *= 1000000;
            result.views = Math.floor(num);
        }
    }

    // 댓글 수 (더 정확한 셀렉터)
    const commentTab = document.querySelector('[class*="comment"] [class*="count"], [data-name*="comment"]');
    if (commentTab) {
        const match = commentTab.textContent.match(/(\\d+)/);
        if (match) result.comments = parseInt(match[1]);
    }

    // Pine Script 버전
    const bodyText = document.body.innerText;
    const versionMatch = bodyText.match(/\\/\\/@version=(\\d+)/);
    if (versionMatch) result.pineVersion = parseInt(versionMatch[1]);

    // 오픈소스 여부
    result.isOpenSource = bodyText.includes('Open-source script') ||
                          bodyText.includes('Open source script') ||
                          bodyText.includes('오픈 소스');

    // 작성자 프로필 정보 (있는 경우)
    const followerEl = document.querySelector('[class*="follower"] [class*="count"], [class*="subscribers"]');
    if (followerEl) {
        const match = followerEl.textContent.match(/([\\d,.]+)([KkMm])?/);
        if (match) {
            let num = parseFloat(match[1].replace(/,/g, ''));
            if (match[2] === 'K' || match[2] === 'k') num *= 1000;
            if (match[2] === 'M' || match[2] === 'm') num *= 1000000;
            result.authorFollowers = Math.floor(num);
        }
    }

    return result;
}
"""


class QualityPipeline:
    """고품질 전략 수집 파이프라인 - 양보다 질 우선"""

    def __init__(self, min_pre_quality_score: float = 40.0):
        self.config = config  # 전역 config 인스턴스 사용
        self.repainting_detector = RepaintingDetector()
        self.overfitting_detector = OverfittingDetector()
        self.pre_filter = PreCollectionFilter(
            min_quality_score=min_pre_quality_score,
            min_likes=100,
            require_open_source=True,
            min_pine_version=4
        )
        self.stats = {
            "total_found": 0,         # 발견된 전략 수
            "pre_filtered": 0,        # 사전 필터링 통과
            "total_analyzed": 0,      # 분석 완료
            "passed_quality": 0,      # 최종 통과
            "failed_pre_filter": 0,   # 사전 필터링 탈락
            "failed_repainting": 0,
            "failed_overfitting": 0,
            "failed_score": 0,
            "no_code": 0
        }

    async def run(self, max_count: int, min_likes: int) -> List[Dict]:
        """파이프라인 실행"""
        print("=" * 60)
        print("🚀 고품질 전략 수집 파이프라인 (양보다 질)")
        print("=" * 60)
        print(f"설정: max_count={max_count}, min_likes={min_likes}")
        print(f"사전 필터: 품질점수>={self.pre_filter.min_quality_score}, "
              f"오픈소스={self.pre_filter.require_open_source}")
        print(f"코드 분석: code_score>={self.config.min_code_score}, "
              f"no_repainting={self.config.require_no_repainting}")
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.headless)

            # 1단계: 전략 목록에서 후보 수집
            print("📥 1단계: 전략 후보 수집...")
            candidates = await self._collect_candidates(browser, max_count * 3, min_likes)
            self.stats["total_found"] = len(candidates)
            print(f"   발견: {len(candidates)}개")

            if SHUTDOWN_FLAG or not candidates:
                await browser.close()
                return []

            # 2단계: 상세 페이지 방문하여 품질 지표 수집 + 사전 필터링
            print("\n📊 2단계: 품질 지표 수집 및 사전 필터링...")
            qualified_strategies = await self._pre_filter_strategies(
                browser, candidates, max_count
            )
            self.stats["pre_filtered"] = len(qualified_strategies)
            print(f"\n   사전 필터 통과: {len(qualified_strategies)}개 "
                  f"({len(qualified_strategies)*100//max(1,len(candidates))}%)")

            if SHUTDOWN_FLAG or not qualified_strategies:
                await browser.close()
                return []

            # 3단계: 코드 분석 및 최종 품질 검사
            print("\n🔍 3단계: 코드 분석 및 최종 검증...")
            quality_strategies = []

            for i, strategy in enumerate(qualified_strategies, 1):
                if SHUTDOWN_FLAG:
                    print("\n⚠️ 종료 요청으로 분석 중단")
                    break

                print(f"\n[{i}/{len(qualified_strategies)}] {strategy['title'][:40]}... "
                      f"(사전점수:{strategy.get('pre_quality_score', 0):.0f})")

                # 코드 분석 실행
                analysis = await self._analyze_strategy(browser, strategy)
                self.stats["total_analyzed"] += 1

                # 최종 품질 검사
                if self._passes_quality_check(analysis):
                    quality_strategies.append(analysis)
                    self.stats["passed_quality"] += 1
                    print(f"   ✅ 최종 통과 (코드:{analysis['code_score']:.0f}, "
                          f"종합:{analysis['total_score']:.0f})")
                else:
                    self._log_failure_reason(analysis)

                # Rate limiting
                await asyncio.sleep(2)

            await browser.close()

        # 4단계: 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._save_results(quality_strategies, timestamp)
        self._print_summary()

        return quality_strategies

    async def _collect_candidates(self, browser, max_count: int, min_likes: int) -> List[Dict]:
        """1단계: 전략 목록에서 후보 수집 (기본 필터만)"""
        page = await browser.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, "webdriver", {get: () => undefined});
        """)

        try:
            await page.goto("https://www.tradingview.com/scripts/",
                          wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            # Strategies 필터
            all_types_btn = page.locator('button:has-text("All types")')
            if await all_types_btn.count() > 0:
                await all_types_btn.first.click()
                await asyncio.sleep(1)
                strategies_opt = page.locator('text="Strategies"')
                if await strategies_opt.count() > 0:
                    await strategies_opt.first.click()
                    await asyncio.sleep(2)

            # 인기순 정렬
            popular_link = page.locator('a:has-text("Popular")')
            if await popular_link.count() > 0:
                await popular_link.first.click()
                await asyncio.sleep(3)

            # 데이터 수집
            all_strategies = []
            click_count = 0

            while len(all_strategies) < max_count and click_count < 20:
                if SHUTDOWN_FLAG:
                    break

                data = await page.evaluate(JS_EXTRACT_STRATEGIES)

                for item in data:
                    if item['isOpenSource'] and item['likes'] >= min_likes:
                        if not any(s['scriptId'] == item['scriptId'] for s in all_strategies):
                            all_strategies.append(item)

                if len(all_strategies) >= max_count:
                    break

                show_more = page.locator('button:has-text("Show more publications")')
                if await show_more.count() > 0:
                    await show_more.first.click()
                    click_count += 1
                    await asyncio.sleep(3)
                else:
                    break

        finally:
            await page.close()

        # 인기도순 정렬
        all_strategies.sort(key=lambda x: x.get('popularityScore', x['likes']), reverse=True)
        return all_strategies[:max_count]

    async def _pre_filter_strategies(
        self, browser, candidates: List[Dict], max_qualified: int
    ) -> List[Dict]:
        """2단계: 상세 페이지에서 품질 지표 수집 + 사전 필터링"""
        qualified = []

        for i, candidate in enumerate(candidates, 1):
            if SHUTDOWN_FLAG or len(qualified) >= max_qualified:
                break

            # 알려진 신뢰 작성자인지 확인
            trust_followers, is_verified = get_author_trust_score(candidate.get('author', ''))

            # 품질 메트릭 객체 생성
            metrics = QualityMetrics(
                script_id=candidate.get('scriptId', ''),
                title=candidate.get('title', ''),
                author=candidate.get('author', ''),
                script_url=candidate.get('href', ''),
                likes=candidate.get('likes', 0),
                views=candidate.get('views', 0),
                comments=candidate.get('comments', 0),
                author_followers=trust_followers if trust_followers > 0 else 0,
                is_verified=is_verified,
                pine_version=5,  # 기본값, 상세 페이지에서 업데이트
                is_open_source=candidate.get('isOpenSource', True)
            )

            # 상세 페이지 방문하여 추가 정보 수집
            try:
                page = await browser.new_page()
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """)

                await page.goto(metrics.script_url, wait_until="networkidle", timeout=20000)
                await asyncio.sleep(1)

                # 품질 지표 추출
                page_metrics = await page.evaluate(JS_EXTRACT_QUALITY_METRICS)

                # 메트릭 업데이트
                if page_metrics['likes'] > metrics.likes:
                    metrics.likes = page_metrics['likes']
                if page_metrics['views'] > metrics.views:
                    metrics.views = page_metrics['views']
                if page_metrics['comments'] > metrics.comments:
                    metrics.comments = page_metrics['comments']
                if page_metrics['authorFollowers'] > metrics.author_followers:
                    metrics.author_followers = page_metrics['authorFollowers']
                metrics.pine_version = page_metrics['pineVersion']
                metrics.is_open_source = page_metrics['isOpenSource']

                await page.close()

            except Exception as e:
                print(f"   [{i}] {candidate['title'][:30]}... ⚠️ 페이지 로드 실패")
                self.stats["failed_pre_filter"] += 1
                continue

            # 품질 점수 계산
            metrics.calculate_scores()

            # 사전 필터링
            should_collect, reasons = self.pre_filter.should_collect(metrics)

            if should_collect:
                candidate['pre_quality_score'] = metrics.total_quality_score
                candidate['quality_metrics'] = metrics.to_dict()
                qualified.append(candidate)
                print(f"   [{i}] {candidate['title'][:30]}... ✓ "
                      f"(점수:{metrics.total_quality_score:.0f}, "
                      f"좋아요:{metrics.likes}, 조회:{metrics.views})")
            else:
                self.stats["failed_pre_filter"] += 1
                reason_str = reasons[0] if reasons else "기준 미달"
                print(f"   [{i}] {candidate['title'][:30]}... ✗ {reason_str}")

            await asyncio.sleep(1)  # Rate limiting

        # 품질 점수순 정렬
        qualified.sort(key=lambda x: x.get('pre_quality_score', 0), reverse=True)
        return qualified[:max_qualified]

    async def _analyze_strategy(self, browser, strategy: Dict) -> Dict:
        """단일 전략 분석"""
        analysis = {
            "script_id": strategy.get('scriptId', ''),
            "title": strategy.get('title', ''),
            "author": strategy.get('author', ''),
            "likes": strategy.get('likes', 0),
            "comments": strategy.get('comments', 0),
            "views": strategy.get('views', 0),
            "users": strategy.get('users', 0),
            "popularity_score": strategy.get('popularityScore', 0),
            "script_url": strategy.get('href', ''),
            "pine_code": None,
            "pine_version": 5,
            "repainting_issues": [],
            "overfitting_issues": [],
            "code_score": 0,
            "performance_score": 50,
            "quality_score": 0,
            "total_score": 0,
            "collected_at": datetime.now().isoformat(),
            "error": None
        }

        page = await browser.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        try:
            await page.goto(analysis['script_url'],
                          wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Source code 버튼 클릭
            source_btn = page.locator('button:has-text("Source code")')
            if await source_btn.count() > 0:
                await source_btn.first.click()
                await asyncio.sleep(2)

                # Pine Script 추출
                analysis['pine_code'] = await page.evaluate(JS_EXTRACT_CODE)

        except Exception as e:
            analysis['error'] = str(e)
        finally:
            await page.close()

        # 코드 분석
        if analysis['pine_code']:
            analysis['pine_version'] = self._detect_version(analysis['pine_code'])
            analysis['repainting_issues'] = self._check_repainting(analysis['pine_code'])
            analysis['overfitting_issues'] = self._check_overfitting(analysis['pine_code'])
        else:
            self.stats["no_code"] += 1

        # 점수 계산
        self._calculate_scores(analysis)

        return analysis

    def _detect_version(self, code: str) -> int:
        import re
        match = re.search(r'//@version=(\d+)', code)
        return int(match.group(1)) if match else 5

    def _check_repainting(self, code: str) -> List[Dict]:
        try:
            result = self.repainting_detector.analyze(code)
            return [{"message": issue, "severity": "high" if "CRITICAL" in issue or "HIGH" in issue else "medium"}
                    for issue in result.issues]
        except Exception as e:
            print(f"⚠️ 리페인팅 분석 실패: {e}")
            return []  # 에러시 빈 리스트 반환 (분석 불가로 처리)

    def _check_overfitting(self, code: str) -> List[Dict]:
        try:
            result = self.overfitting_detector.analyze(code, {})
            return [{"message": concern, "severity": result.risk_level}
                    for concern in result.concerns]
        except Exception as e:
            print(f"⚠️ 과적합 분석 실패: {e}")
            return []  # 에러시 빈 리스트 반환

    def _calculate_scores(self, analysis: Dict):
        # 코드 점수
        code_score = 100

        for issue in analysis['repainting_issues']:
            severity = issue.get('severity', 'low')
            if severity == 'high':
                code_score -= 30
            elif severity == 'medium':
                code_score -= 15
            else:
                code_score -= 5

        for issue in analysis['overfitting_issues']:
            severity = issue.get('severity', 'low')
            if severity in ['high', 'critical']:
                code_score -= 25
            elif severity == 'medium':
                code_score -= 10
            else:
                code_score -= 5

        if not analysis['pine_code']:
            code_score = 0

        analysis['code_score'] = max(0, code_score)

        # 인기도 점수
        likes = analysis['likes']
        if likes >= 1000:
            analysis['quality_score'] = 100
        elif likes >= 500:
            analysis['quality_score'] = 80
        elif likes >= 200:
            analysis['quality_score'] = 60
        else:
            analysis['quality_score'] = 40

        # 종합 점수
        analysis['total_score'] = (
            analysis['code_score'] * 0.4 +
            analysis['performance_score'] * 0.4 +
            analysis['quality_score'] * 0.2
        )

    def _passes_quality_check(self, analysis: Dict) -> bool:
        """품질 기준 통과 여부 (중복 카운팅 방지)"""
        # 코드 없으면 실패
        if not analysis['pine_code']:
            return False

        failed = False

        # 리페인팅 이슈 검사
        if self.config.require_no_repainting and analysis['repainting_issues']:
            high_issues = [i for i in analysis['repainting_issues']
                         if i.get('severity') in ['high', 'critical']]
            if high_issues:
                self.stats["failed_repainting"] += 1
                failed = True

        # 과적합 이슈 검사
        if len(analysis['overfitting_issues']) > self.config.max_overfitting_issues:
            self.stats["failed_overfitting"] += 1
            failed = True

        # 점수 검사 (code_score 또는 total_score 미달 시 한 번만 카운팅)
        score_failed = (analysis['code_score'] < self.config.min_code_score or
                       analysis['total_score'] < self.config.min_total_score)
        if score_failed:
            self.stats["failed_score"] += 1
            failed = True

        return not failed

    def _log_failure_reason(self, analysis: Dict):
        """실패 이유 출력"""
        reasons = []
        if not analysis['pine_code']:
            reasons.append("코드 없음")
        if analysis['repainting_issues']:
            reasons.append(f"리페인팅 {len(analysis['repainting_issues'])}개")
        if analysis['code_score'] < self.config.min_code_score:
            reasons.append(f"코드점수 {analysis['code_score']:.0f}")
        print(f"   ❌ 탈락: {', '.join(reasons) if reasons else '기준 미달'}")

    def _save_results(self, strategies: List[Dict], timestamp: str):
        """결과 저장"""
        Path("data").mkdir(exist_ok=True)

        # 고품질 전략 저장
        if strategies:
            quality_path = f"data/quality_{timestamp}.json"
            with open(quality_path, 'w', encoding='utf-8') as f:
                json.dump(strategies, f, ensure_ascii=False, indent=2)
            print(f"\n💾 고품질 전략 저장: {quality_path}")

    def _print_summary(self):
        """요약 출력"""
        print("\n" + "=" * 60)
        print("📊 수집 결과 요약 (양보다 질 파이프라인)")
        print("=" * 60)

        # 단계별 통과율
        found = self.stats['total_found']
        pre_filtered = self.stats['pre_filtered']
        analyzed = self.stats['total_analyzed']
        passed = self.stats['passed_quality']

        print("\n📈 단계별 필터링:")
        print(f"  1️⃣ 후보 발견: {found}개")
        print(f"  2️⃣ 사전 필터 통과: {pre_filtered}개 "
              f"({pre_filtered*100//max(1,found)}%)")
        print(f"  3️⃣ 코드 분석 완료: {analyzed}개")
        print(f"  4️⃣ 최종 품질 통과: {passed}개 "
              f"({passed*100//max(1,analyzed)}%)")

        # 효율성 지표
        efficiency = passed * 100 // max(1, found)
        print(f"\n🎯 전체 효율: {efficiency}% (최종통과/후보발견)")

        # 탈락 상세
        print("\n❌ 탈락 사유:")
        print(f"  - 사전 필터 탈락: {self.stats['failed_pre_filter']}개")
        print(f"  - 리페인팅 이슈: {self.stats['failed_repainting']}개")
        print(f"  - 과적합 이슈: {self.stats['failed_overfitting']}개")
        print(f"  - 점수 미달: {self.stats['failed_score']}개")
        print(f"  - 코드 없음: {self.stats['no_code']}개")


async def continuous_run(pipeline: QualityPipeline, max_count: int,
                        min_likes: int, interval: int):
    """연속 실행 모드"""
    run_count = 0
    while not SHUTDOWN_FLAG:
        run_count += 1
        print(f"\n🔄 === 실행 #{run_count} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n")

        try:
            await pipeline.run(max_count, min_likes)
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        if SHUTDOWN_FLAG:
            break

        print(f"\n⏰ 다음 실행까지 {interval}초 대기...")
        for _ in range(interval):
            if SHUTDOWN_FLAG:
                break
            await asyncio.sleep(1)

    print("\n✅ 파이프라인 종료")


async def main():
    parser = argparse.ArgumentParser(description="고품질 전략 수집 파이프라인")
    parser.add_argument("--max-count", "-m", type=int, default=50,
                       help="최대 수집 전략 수 (default: 50)")
    parser.add_argument("--min-likes", "-l", type=int, default=200,
                       help="최소 좋아요 수 (default: 200)")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="연속 실행 모드")
    parser.add_argument("--interval", "-i", type=int, default=3600,
                       help="연속 실행 간격 (초, default: 3600)")

    args = parser.parse_args()

    pipeline = QualityPipeline()

    if args.continuous:
        print("🔄 연속 실행 모드 (Ctrl+C로 종료)")
        await continuous_run(pipeline, args.max_count, args.min_likes, args.interval)
    else:
        await pipeline.run(args.max_count, args.min_likes)


if __name__ == "__main__":
    asyncio.run(main())
