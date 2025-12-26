"""
데이터 내보내기

JSON/CSV 형식으로 분석 결과 내보내기
+ 간단 리포트 생성 (전략 설명 + 백테스트 결과 요약)
"""

import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import StrategyModel, DatabaseStats
from .database import StrategyDatabase

logger = logging.getLogger(__name__)


class SimpleReportGenerator:
    """
    간단한 전략 리포트 생성기

    사용자가 원하는 것: 좋은 전략의 설명 + 백테스트 결과만 깔끔하게 받기
    """

    # 등급별 이모지와 설명
    GRADE_INFO = {
        "A": ("🏆", "우수", "Moon Dev 기준 완전 통과"),
        "B": ("✅", "양호", "대부분 기준 통과"),
        "C": ("⚠️", "보통", "최소 기준 통과"),
        "D": ("🔍", "검토 필요", "일부 기준 미달"),
        "F": ("❌", "부적합", "기준 미달"),
    }

    def generate_strategy_card(
        self,
        strategy: StrategyModel,
        backtest_result: Optional[Dict[str, Any]] = None,
        rank: int = 1,
        include_code: bool = False
    ) -> str:
        """
        단일 전략 카드 생성

        Args:
            strategy: 전략 모델
            backtest_result: 백테스트 결과 (없으면 분석 결과만 표시)
            rank: 순위
            include_code: Pine Script 코드 포함 여부

        Returns:
            포맷된 전략 카드 문자열
        """
        analysis = strategy.analysis or {}
        grade = analysis.get("grade", "N/A")
        grade_emoji, grade_text, grade_desc = self.GRADE_INFO.get(grade, ("❓", "미분석", "분석 필요"))

        lines = [
            "",
            "═" * 60,
            f"{grade_emoji} 추천 전략 #{rank}: {strategy.title}",
            "═" * 60,
            "",
            "📝 전략 정보",
            "─" * 60,
            f"  • 작성자: {strategy.author}",
            f"  • 좋아요: {strategy.likes:,}",
            f"  • URL: {strategy.script_url or 'N/A'}",
            "",
        ]

        # 전략 설명 (LLM 분석 결과 또는 description)
        llm_analysis = analysis.get("llm_analysis", {})
        if isinstance(llm_analysis, dict):
            summary = llm_analysis.get("summary_kr", "")
            strengths = llm_analysis.get("strengths", [])
            weaknesses = llm_analysis.get("weaknesses", [])

            if summary:
                lines.extend([
                    "📖 전략 설명",
                    "─" * 60,
                    f"  {summary}",
                    "",
                ])

            if strengths:
                lines.append("  ✅ 강점:")
                for s in strengths[:3]:  # 상위 3개만
                    lines.append(f"     • {s}")
                lines.append("")

            if weaknesses:
                lines.append("  ⚠️ 주의사항:")
                for w in weaknesses[:2]:  # 상위 2개만
                    lines.append(f"     • {w}")
                lines.append("")

        elif strategy.description:
            # LLM 분석 없으면 원본 설명 사용
            desc = strategy.description[:200] + "..." if len(strategy.description) > 200 else strategy.description
            lines.extend([
                "📖 전략 설명",
                "─" * 60,
                f"  {desc}",
                "",
            ])

        # 분석 결과
        lines.extend([
            "📊 분석 결과",
            "─" * 60,
        ])

        total_score = analysis.get("total_score", 0)
        lines.append(f"  총점        │ {total_score:.1f}/100 ({grade} 등급)")

        # Repainting 위험
        repainting = analysis.get("repainting_analysis", {})
        if isinstance(repainting, dict):
            risk = repainting.get("risk_level", "N/A")
            lines.append(f"  리페인팅    │ {risk}")

        # Overfitting 위험
        overfitting = analysis.get("overfitting_analysis", {})
        if isinstance(overfitting, dict):
            risk = overfitting.get("risk_level", "N/A")
            param_count = overfitting.get("parameter_count", 0)
            lines.append(f"  과적합 위험 │ {risk} (파라미터 {param_count}개)")

        lines.append("")

        # 백테스트 결과 (있는 경우)
        if backtest_result:
            symbol = backtest_result.get("symbol", "BTCUSDT")
            interval = backtest_result.get("interval", "1h")
            start = backtest_result.get("start_date", "")[:10]
            end = backtest_result.get("end_date", "")[:10]

            lines.extend([
                f"📈 백테스트 결과 ({symbol}, {interval})",
                "─" * 60,
                f"  기간        │ {start} ~ {end}",
                f"  수익률      │ {backtest_result.get('total_return', 0):+.1f}%",
                f"  승률        │ {backtest_result.get('win_rate', 0):.1f}%",
                f"  최대 낙폭   │ -{backtest_result.get('max_drawdown', 0):.1f}%",
                f"  Sharpe      │ {backtest_result.get('sharpe_ratio', 0):.2f}",
                f"  거래 수     │ {backtest_result.get('total_trades', 0):,}회",
                "",
            ])

            # Moon Dev 기준 통과 여부
            sharpe = backtest_result.get("sharpe_ratio", 0)
            max_dd = backtest_result.get("max_drawdown", 0)
            win_rate = backtest_result.get("win_rate", 0)

            passed = sharpe >= 1.5 and max_dd <= 30 and win_rate >= 40
            status = "✅ Moon Dev 기준 통과" if passed else "⚠️ 일부 기준 미달"
            lines.append(f"  상태        │ {status}")

        # TradingView 성과 데이터 (백테스트 결과 없을 때)
        elif strategy.performance:
            perf = strategy.performance
            lines.extend([
                "📈 TradingView 성과 (참고용)",
                "─" * 60,
            ])

            if "net_profit" in perf:
                lines.append(f"  순이익      │ {perf.get('net_profit', 'N/A')}")
            if "win_rate" in perf:
                lines.append(f"  승률        │ {perf.get('win_rate', 'N/A')}")
            if "max_drawdown" in perf:
                lines.append(f"  최대 낙폭   │ {perf.get('max_drawdown', 'N/A')}")
            if "total_trades" in perf:
                lines.append(f"  거래 수     │ {perf.get('total_trades', 'N/A')}")

            lines.append("")
            lines.append("  ⚠️ 실제 백테스트 미실행 (TradingView 데이터)")

        lines.extend([
            "",
            "─" * 60,
            f"  등급: {grade} ({grade_text}) - {grade_desc}",
            "═" * 60,
        ])

        # Pine Script 코드 포함 (옵션)
        if include_code and strategy.pine_code:
            lines.extend([
                "",
                "📜 Pine Script 코드",
                "─" * 60,
                "```pinescript",
                strategy.pine_code,
                "```",
                "─" * 60,
            ])

        return "\n".join(lines)

    def generate_top_strategies_report(
        self,
        strategies: List[StrategyModel],
        backtest_results: Optional[Dict[str, Dict[str, Any]]] = None,
        top_n: int = 5,
        include_code: bool = False
    ) -> str:
        """
        상위 N개 전략 리포트 생성

        Args:
            strategies: 전략 리스트 (이미 정렬된 상태)
            backtest_results: script_id -> 백테스트 결과 매핑
            top_n: 상위 N개
            include_code: Pine Script 코드 포함 여부

        Returns:
            전체 리포트 문자열
        """
        backtest_results = backtest_results or {}

        lines = [
            "",
            "╔" + "═" * 58 + "╗",
            "║" + " 🎯 AI 추천 트레이딩 전략 TOP " + str(top_n) + " ".center(27) + "║",
            "╚" + "═" * 58 + "╝",
            "",
            f"  생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  분석 대상: {len(strategies)}개 전략 중 상위 {min(top_n, len(strategies))}개 선별",
            "",
        ]

        # 각 전략 카드 추가
        for i, strategy in enumerate(strategies[:top_n], 1):
            backtest = backtest_results.get(strategy.script_id)
            card = self.generate_strategy_card(strategy, backtest, rank=i, include_code=include_code)
            lines.append(card)

        # 요약
        lines.extend([
            "",
            "═" * 60,
            "📋 요약",
            "═" * 60,
            "",
        ])

        # 등급 분포
        grade_counts = {}
        for s in strategies[:top_n]:
            grade = (s.analysis or {}).get("grade", "N/A")
            grade_counts[grade] = grade_counts.get(grade, 0) + 1

        for grade in ["A", "B", "C", "D", "F"]:
            if grade in grade_counts:
                emoji, text, _ = self.GRADE_INFO[grade]
                lines.append(f"  {emoji} {grade}등급: {grade_counts[grade]}개")

        lines.extend([
            "",
            "─" * 60,
            "  💡 A, B 등급 전략을 우선 검토하세요.",
            "  ⚠️ 실거래 전 반드시 추가 백테스트를 진행하세요.",
            "═" * 60,
            "",
        ])

        return "\n".join(lines)

    def print_strategy(
        self,
        strategy: StrategyModel,
        backtest_result: Optional[Dict[str, Any]] = None,
        include_code: bool = False
    ) -> None:
        """전략 카드를 터미널에 출력"""
        print(self.generate_strategy_card(strategy, backtest_result, include_code=include_code))

    def print_top_strategies(
        self,
        strategies: List[StrategyModel],
        backtest_results: Optional[Dict[str, Dict[str, Any]]] = None,
        top_n: int = 5,
        include_code: bool = False
    ) -> None:
        """상위 전략 리포트를 터미널에 출력"""
        print(self.generate_top_strategies_report(strategies, backtest_results, top_n, include_code))

    def save_strategies_with_code(
        self,
        strategies: List[StrategyModel],
        output_dir: str = "data/exports/strategies",
        grades: Optional[List[str]] = None
    ) -> List[str]:
        """
        통과한 전략들의 Pine Script 코드를 개별 파일로 저장

        Args:
            strategies: 전략 리스트
            output_dir: 출력 디렉토리
            grades: 저장할 등급 필터 (기본: ["A", "B"])

        Returns:
            저장된 파일 경로 리스트
        """
        grades = grades or ["A", "B"]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []

        for strategy in strategies:
            # 등급 필터
            analysis = strategy.analysis or {}
            grade = analysis.get("grade", "N/A")
            if grade not in grades:
                continue

            # Pine 코드가 없으면 스킵
            if not strategy.pine_code:
                continue

            # 안전한 파일명 생성
            safe_title = "".join(
                c for c in strategy.title if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            safe_title = safe_title.replace(" ", "_")[:40]

            filename = f"{grade}_{safe_title}_{strategy.script_id}.pine"
            file_path = output_path / filename

            # 파일 저장 (메타데이터 포함)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"// ═══════════════════════════════════════════════════════\n")
                f.write(f"// 🎯 {strategy.title}\n")
                f.write(f"// ═══════════════════════════════════════════════════════\n")
                f.write(f"// 작성자: {strategy.author}\n")
                f.write(f"// 좋아요: {strategy.likes:,}\n")
                f.write(f"// 등급: {grade} ({analysis.get('total_score', 0):.1f}점)\n")
                f.write(f"// URL: {strategy.script_url or 'N/A'}\n")
                f.write(f"// ═══════════════════════════════════════════════════════\n\n")
                f.write(strategy.pine_code)

            saved_files.append(str(file_path))

        return saved_files


class DataExporter:
    """
    분석 결과 내보내기 클래스

    지원 형식:
    - JSON: 전체 데이터 (메타데이터 + 분석 결과)
    - CSV: 테이블 형식 (주요 필드만)
    - 요약 리포트: 마크다운 형식
    """

    def __init__(self, output_dir: str = "data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def export_to_json(
        self,
        strategies: List[StrategyModel],
        filename: Optional[str] = None,
        include_pine_code: bool = True,
    ) -> str:
        """
        JSON 파일로 내보내기

        Args:
            strategies: 전략 리스트
            filename: 파일명 (없으면 자동 생성)
            include_pine_code: Pine 코드 포함 여부

        Returns:
            저장된 파일 경로
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategies_{timestamp}.json"

        output_path = self.output_dir / filename

        try:
            # 데이터 준비
            data = {
                "exported_at": datetime.now().isoformat(),
                "total_count": len(strategies),
                "strategies": [],
            }

            for strategy in strategies:
                strategy_dict = strategy.model_dump()

                # Pine 코드 제외 옵션
                if not include_pine_code:
                    strategy_dict["pine_code"] = None

                data["strategies"].append(strategy_dict)

            # JSON 저장
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Exported {len(strategies)} strategies to JSON: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            raise

    async def export_to_csv(
        self,
        strategies: List[StrategyModel],
        filename: Optional[str] = None,
    ) -> str:
        """
        CSV 파일로 내보내기

        Args:
            strategies: 전략 리스트
            filename: 파일명 (없으면 자동 생성)

        Returns:
            저장된 파일 경로
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategies_{timestamp}.csv"

        output_path = self.output_dir / filename

        try:
            # CSV 필드 정의
            fieldnames = [
                "script_id",
                "title",
                "author",
                "likes",
                "views",
                "pine_version",
                "total_score",
                "grade",
                "status",
                "repainting_risk",
                "overfitting_risk",
                "script_url",
                "created_at",
            ]

            with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for strategy in strategies:
                    # 분석 결과 추출
                    analysis = strategy.analysis or {}

                    # Repainting 위험
                    repainting_analysis = analysis.get("repainting_analysis", {})
                    if isinstance(repainting_analysis, dict):
                        repainting_risk = repainting_analysis.get("risk_level", "N/A")
                    else:
                        repainting_risk = "N/A"

                    # Overfitting 위험
                    overfitting_analysis = analysis.get("overfitting_analysis", {})
                    if isinstance(overfitting_analysis, dict):
                        overfitting_risk = overfitting_analysis.get("risk_level", "N/A")
                    else:
                        overfitting_risk = "N/A"

                    row = {
                        "script_id": strategy.script_id,
                        "title": strategy.title,
                        "author": strategy.author,
                        "likes": strategy.likes,
                        "views": strategy.views,
                        "pine_version": strategy.pine_version,
                        "total_score": analysis.get("total_score", "N/A"),
                        "grade": analysis.get("grade", "N/A"),
                        "status": analysis.get("status", "N/A"),
                        "repainting_risk": repainting_risk,
                        "overfitting_risk": overfitting_risk,
                        "script_url": strategy.script_url,
                        "created_at": (
                            strategy.created_at.isoformat()
                            if strategy.created_at
                            else ""
                        ),
                    }

                    writer.writerow(row)

            logger.info(f"Exported {len(strategies)} strategies to CSV: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise

    async def export_summary_report(
        self,
        db: StrategyDatabase,
        filename: Optional[str] = None,
    ) -> str:
        """
        요약 리포트 생성 (마크다운)

        Args:
            db: StrategyDatabase 인스턴스
            filename: 파일명 (없으면 자동 생성)

        Returns:
            저장된 파일 경로
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_report_{timestamp}.md"

        output_path = self.output_dir / filename

        try:
            # 통계 조회
            stats = await db.get_stats()

            # 상위 전략 조회
            from .models import SearchFilters

            top_strategies = await db.search_strategies(
                SearchFilters(
                    has_analysis=True,
                    order_by="likes",
                    order_desc=True,
                    limit=20,
                )
            )

            # 리포트 생성
            report_lines = [
                "# TradingView 전략 연구소 - 분석 요약 리포트",
                "",
                f"생성일시: {stats.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "---",
                "",
                "## 📊 전체 통계",
                "",
                f"- **전체 전략 수**: {stats.total_strategies:,}개",
                f"- **Pine 코드 보유**: {stats.with_pine_code:,}개 ({stats.with_pine_code/max(stats.total_strategies,1)*100:.1f}%)",
                f"- **오픈소스**: {stats.open_source_count:,}개",
                f"- **분석 완료**: {stats.analyzed_count:,}개",
                "",
                "### 분석 결과",
                "",
                f"- ✅ **통과**: {stats.passed_count:,}개 ({stats.passed_count/max(stats.analyzed_count,1)*100:.1f}%)",
                f"- 🔍 **검토 필요**: {stats.review_count:,}개 ({stats.review_count/max(stats.analyzed_count,1)*100:.1f}%)",
                f"- ❌ **거부**: {stats.rejected_count:,}개 ({stats.rejected_count/max(stats.analyzed_count,1)*100:.1f}%)",
                "",
                "### 등급 분포",
                "",
            ]

            # 등급 분포 테이블
            total_graded = sum(stats.grade_distribution.values())
            for grade in ["A", "B", "C", "D", "F"]:
                count = stats.grade_distribution.get(grade, 0)
                pct = count / max(total_graded, 1) * 100
                bar = "█" * int(pct / 2)
                report_lines.append(f"- **{grade}**: {count:,}개 ({pct:.1f}%) {bar}")

            report_lines.extend(
                [
                    "",
                    "### 평균 지표",
                    "",
                    f"- 평균 좋아요: {stats.avg_likes:.1f}",
                    f"- 평균 점수: {stats.avg_score:.1f}/100",
                    "",
                ]
            )

            # 최고 점수 전략
            if stats.top_strategy:
                top = stats.top_strategy
                report_lines.extend(
                    [
                        "### 🏆 최고 점수 전략",
                        "",
                        f"- **제목**: {top['title']}",
                        f"- **작성자**: {top['author']}",
                        f"- **점수**: {top['score']:.1f}점 (등급: {top['grade']})",
                        f"- **좋아요**: {top['likes']:,}",
                        "",
                    ]
                )

            # 상위 전략 리스트
            report_lines.extend(
                [
                    "---",
                    "",
                    "## 🔝 상위 전략 (좋아요 기준)",
                    "",
                    "| 순위 | 제목 | 작성자 | 좋아요 | 점수 | 등급 | 상태 |",
                    "|------|------|--------|--------|------|------|------|",
                ]
            )

            for i, strategy in enumerate(top_strategies[:20], 1):
                analysis = strategy.analysis or {}
                score = analysis.get("total_score", "N/A")
                grade = analysis.get("grade", "N/A")
                status = analysis.get("status", "N/A")

                # 상태 이모지
                status_emoji = {
                    "passed": "✅",
                    "review": "🔍",
                    "rejected": "❌",
                }.get(status, "")

                # 제목 길이 제한
                title = strategy.title[:50] + "..." if len(strategy.title) > 50 else strategy.title

                report_lines.append(
                    f"| {i} | {title} | {strategy.author} | {strategy.likes:,} | "
                    f"{score} | {grade} | {status_emoji} {status} |"
                )

            report_lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## 📈 분석 세부사항",
                    "",
                ]
            )

            # 통과한 전략들의 상세 정보
            passed_strategies = [s for s in top_strategies if s.analysis and s.analysis.get("status") == "passed"]

            if passed_strategies:
                report_lines.extend(
                    [
                        "### ✅ 통과 전략 상세",
                        "",
                    ]
                )

                for strategy in passed_strategies[:10]:
                    analysis = strategy.analysis
                    repainting = analysis.get("repainting_analysis", {})
                    overfitting = analysis.get("overfitting_analysis", {})
                    llm = analysis.get("llm_analysis", {})

                    report_lines.extend(
                        [
                            f"#### {strategy.title}",
                            "",
                            f"- **작성자**: {strategy.author}",
                            f"- **좋아요**: {strategy.likes:,}",
                            f"- **총점**: {analysis.get('total_score', 'N/A'):.1f}점 (등급: {analysis.get('grade', 'N/A')})",
                            "",
                            "**분석 결과**:",
                            "",
                        ]
                    )

                    # Repainting 분석
                    if isinstance(repainting, dict):
                        risk_level = repainting.get("risk_level", "N/A")
                        report_lines.append(f"- Repainting 위험: {risk_level}")

                    # Overfitting 분석
                    if isinstance(overfitting, dict):
                        risk_level = overfitting.get("risk_level", "N/A")
                        param_count = overfitting.get("parameter_count", 0)
                        report_lines.append(f"- 과적합 위험: {risk_level} (파라미터: {param_count}개)")

                    # LLM 분석
                    if isinstance(llm, dict):
                        summary = llm.get("summary", "")
                        if summary:
                            report_lines.append(f"- LLM 평가: {summary}")

                    report_lines.append("")

            # 푸터
            report_lines.extend(
                [
                    "---",
                    "",
                    "*Generated by TradingView Strategy Research Lab*",
                ]
            )

            # 파일 저장
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))

            logger.info(f"Exported summary report: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting summary report: {e}")
            raise

    async def export_analysis_details(
        self,
        strategies: List[StrategyModel],
        filename: Optional[str] = None,
    ) -> str:
        """
        분석 상세 내용 JSON 내보내기 (분석 결과만)

        Args:
            strategies: 전략 리스트
            filename: 파일명

        Returns:
            저장된 파일 경로
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_details_{timestamp}.json"

        output_path = self.output_dir / filename

        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "total_count": len(strategies),
                "analyses": [],
            }

            for strategy in strategies:
                if not strategy.analysis:
                    continue

                analysis_data = {
                    "script_id": strategy.script_id,
                    "title": strategy.title,
                    "author": strategy.author,
                    "likes": strategy.likes,
                    "analysis": strategy.analysis,
                }

                data["analyses"].append(analysis_data)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(
                f"Exported analysis details for {len(data['analyses'])} strategies: {output_path}"
            )
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting analysis details: {e}")
            raise

    async def export_pine_codes(
        self,
        strategies: List[StrategyModel],
        output_subdir: Optional[str] = None,
    ) -> str:
        """
        Pine 코드를 개별 파일로 내보내기

        Args:
            strategies: 전략 리스트
            output_subdir: 출력 서브디렉토리 (없으면 자동 생성)

        Returns:
            출력 디렉토리 경로
        """
        if not output_subdir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_subdir = f"pine_codes_{timestamp}"

        output_dir = self.output_dir / output_subdir
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            exported_count = 0

            for strategy in strategies:
                if not strategy.pine_code:
                    continue

                # 파일명 생성 (안전한 파일명)
                safe_title = "".join(
                    c for c in strategy.title if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                safe_title = safe_title.replace(" ", "_")[:50]

                filename = f"{strategy.script_id}_{safe_title}.pine"
                file_path = output_dir / filename

                # Pine 코드 저장
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"// {strategy.title}\n")
                    f.write(f"// Author: {strategy.author}\n")
                    f.write(f"// Likes: {strategy.likes}\n")
                    f.write(f"// URL: {strategy.script_url}\n")
                    f.write("\n")
                    f.write(strategy.pine_code)

                exported_count += 1

            logger.info(f"Exported {exported_count} Pine codes to: {output_dir}")
            return str(output_dir)

        except Exception as e:
            logger.error(f"Error exporting Pine codes: {e}")
            raise
