# src/collector/pine_fetcher.py

import asyncio
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

@dataclass
class PineCodeData:
    """Pine Script 코드 및 상세 정보"""
    script_id: str
    pine_code: Optional[str]
    pine_version: int
    performance: Dict
    detailed_description: str
    inputs: List[Dict]  # input 파라미터 목록
    is_protected: bool
    error: Optional[str] = None

class PineCodeFetcher:
    """개별 스크립트 페이지에서 Pine 코드 추출"""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_pine_code(self, script_url: str) -> PineCodeData:
        """
        스크립트 페이지에서 Pine 코드 및 상세 정보 추출
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            )
            page = await context.new_page()

            try:
                await page.goto(script_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # 스크립트 ID 추출
                script_id = self._extract_script_id(script_url)

                # 1. Pine 코드 추출 시도
                pine_code, is_protected = await self._extract_pine_code(page)

                # 2. Pine 버전 감지
                pine_version = self._detect_pine_version(pine_code) if pine_code else 5

                # 3. 성과 지표 추출
                performance = await self._extract_performance(page)

                # 4. 상세 설명 추출
                description = await self._extract_description(page)

                # 5. Input 파라미터 파싱
                inputs = self._parse_inputs(pine_code) if pine_code else []

                return PineCodeData(
                    script_id=script_id,
                    pine_code=pine_code,
                    pine_version=pine_version,
                    performance=performance,
                    detailed_description=description,
                    inputs=inputs,
                    is_protected=is_protected,
                )

            except Exception as e:
                logger.error(f"Error fetching {script_url}: {e}")
                return PineCodeData(
                    script_id=self._extract_script_id(script_url),
                    pine_code=None,
                    pine_version=5,
                    performance={},
                    detailed_description="",
                    inputs=[],
                    is_protected=True,
                    error=str(e)
                )
            finally:
                await browser.close()

    async def _extract_pine_code(self, page: Page) -> tuple[Optional[str], bool]:
        """Pine Script 코드 추출"""

        # 먼저 "Source code" 버튼을 클릭하여 코드 표시
        try:
            source_btn = await page.query_selector('text="Source code"')
            if source_btn:
                await source_btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        # 방법 1: Monaco 에디터에서 추출 (2024년 12월 기준 TradingView 구조)
        try:
            monaco = await page.query_selector('.monaco-editor-tv-pine-light')
            if monaco:
                code = await monaco.inner_text()
                if code and len(code) > 50 and ('//@version' in code or 'strategy(' in code or 'indicator(' in code):
                    return code.strip(), False
        except Exception:
            pass

        # 방법 2: pineViewer/codeContainer에서 추출
        try:
            container = await page.query_selector('[class*="codeContainer"]')
            if container:
                code = await container.inner_text()
                # 행번호 제거 (숫자만 있는 줄 제거)
                lines = code.split('\n')
                code_lines = [l for l in lines if not l.strip().isdigit()]
                clean_code = '\n'.join(code_lines)
                if clean_code and len(clean_code) > 50 and ('//@version' in clean_code or 'strategy(' in clean_code or 'indicator(' in clean_code):
                    return clean_code.strip(), False
        except Exception:
            pass

        # 방법 3: 소스 코드 위젯에서 직접 추출 (구버전)
        try:
            code_element = await page.query_selector('.tv-script-src-widget__content')
            if code_element:
                code = await code_element.inner_text()
                if code and len(code) > 50:
                    return code.strip(), False
        except Exception:
            pass

        # 방법 4: pre/code 태그에서 추출
        try:
            code_blocks = await page.query_selector_all('pre code, .pine-editor-content')
            for block in code_blocks:
                text = await block.inner_text()
                if '//@version' in text or 'strategy(' in text:
                    return text.strip(), False
        except Exception:
            pass

        # 방법 5: 페이지 전체에서 Pine 코드 패턴 검색
        try:
            page_content = await page.content()
            pine_match = re.search(
                r'(//@version=\d[\s\S]*?(?:strategy|indicator)\s*\([^)]+\)[\s\S]*?)(?:</pre>|</code>|$)',
                page_content
            )
            if pine_match:
                return pine_match.group(1).strip(), False
        except Exception:
            pass

        # Protected/Invite-only 스크립트
        logger.info("No source code found (protected or invite-only)")
        return None, True

    async def _extract_performance(self, page: Page) -> Dict:
        """Strategy Tester 성과 지표 추출"""
        performance = {}

        try:
            # Strategy Tester 탭 클릭 (있는 경우)
            tester_tab = await page.query_selector('[data-name="backtesting"]')
            if tester_tab:
                await tester_tab.click()
                await asyncio.sleep(1)

            # 성과 지표 추출
            metrics = await page.evaluate("""
                () => {
                    const data = {};

                    // 다양한 셀렉터로 성과 데이터 찾기
                    const rows = document.querySelectorAll(
                        '.report-data tr, [class*="performance"] tr, [class*="metric"]'
                    );

                    rows.forEach(row => {
                        const label = row.querySelector('td:first-child, [class*="label"]');
                        const value = row.querySelector('td:last-child, [class*="value"]');

                        if (label && value) {
                            const key = label.textContent.trim().toLowerCase()
                                .replace(/[^a-z0-9]/g, '_');
                            data[key] = value.textContent.trim();
                        }
                    });

                    return data;
                }
            """)

            # 숫자 파싱
            for key, value in metrics.items():
                if value:
                    parsed = self._parse_metric_value(value)
                    if parsed is not None:
                        performance[key] = parsed

        except Exception as e:
            logger.debug(f"Performance extraction error: {e}")

        return performance

    async def _extract_description(self, page: Page) -> str:
        """상세 설명 추출"""
        try:
            desc_el = await page.query_selector(
                '.tv-script-widget__description, [class*="description"]'
            )
            if desc_el:
                return (await desc_el.inner_text())[:2000]
        except Exception:
            pass
        return ""

    def _detect_pine_version(self, code: str) -> int:
        """Pine Script 버전 감지"""
        if not code:
            return 5

        match = re.search(r'//@version=(\d+)', code)
        if match:
            return int(match.group(1))
        return 4  # 기본값 (v4로 가정)

    def _parse_inputs(self, code: str) -> List[Dict]:
        """input 파라미터 파싱"""
        inputs = []

        if not code:
            return inputs

        # input.int, input.float, input.bool, input.string 패턴
        patterns = [
            r'(\w+)\s*=\s*input\.(int|float|bool|string)\s*\(\s*([^)]+)\)',
            r'(\w+)\s*=\s*input\s*\(\s*([^)]+)\)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code)
            for match in matches:
                if len(match) >= 2:
                    var_name = match[0]
                    input_type = match[1] if len(match) > 2 else "float"

                    inputs.append({
                        "name": var_name,
                        "type": input_type,
                        "raw": match[-1][:100] if match else ""
                    })

        return inputs

    def _extract_script_id(self, url: str) -> str:
        """URL에서 스크립트 ID 추출"""
        match = re.search(r'/script/([^/]+)', url)
        return match.group(1) if match else ""

    def _parse_metric_value(self, value: str) -> Optional[float]:
        """성과 지표 값 파싱"""
        try:
            # "123.45%", "$1,234.56", "1.5" 등 처리
            cleaned = re.sub(r'[^\d.\-]', '', value.replace(',', ''))
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
