# src/analyzer/rule_based/overfitting_detector.py

import re
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class OverfittingAnalysis:
    """과적합 분석 결과"""
    score: float  # 0-100 (높을수록 과적합 위험)
    risk_level: str  # low, medium, high, critical
    parameter_count: int
    magic_numbers: List[str]
    hardcoded_dates: List[str]
    concerns: List[str]
    recommendations: List[str]

class OverfittingDetector:
    """
    전략 과적합(Overfitting) 위험 탐지

    과적합 징후:
    1. 과도한 파라미터 수 (최적화 과잉)
    2. 매직 넘버 (특정 숫자에 과의존)
    3. 특정 날짜 하드코딩 (특정 기간에 최적화)
    4. 비현실적인 성과 지표
    5. 거래 횟수 대비 파라미터 비율
    """

    # 파라미터 수 임계값
    PARAM_THRESHOLDS = {
        "safe": 5,
        "warning": 10,
        "danger": 15,
        "critical": 20
    }

    def analyze(
        self,
        pine_code: str,
        performance: Optional[Dict] = None,
        inputs: Optional[List[Dict]] = None
    ) -> OverfittingAnalysis:
        """과적합 위험 분석"""

        concerns = []
        recommendations = []
        score = 0  # 0에서 시작, 높을수록 위험

        if not pine_code:
            return OverfittingAnalysis(
                score=0,
                risk_level="unknown",
                parameter_count=0,
                magic_numbers=[],
                hardcoded_dates=[],
                concerns=["코드 없음"],
                recommendations=[]
            )

        # 1. 파라미터 수 분석
        param_count, param_score, param_concerns = self._analyze_parameters(pine_code, inputs)
        score += param_score
        concerns.extend(param_concerns)

        # 2. 매직 넘버 탐지
        magic_numbers, magic_score, magic_concerns = self._analyze_magic_numbers(pine_code)
        score += magic_score
        concerns.extend(magic_concerns)

        # 3. 하드코딩된 날짜 탐지
        dates, date_score, date_concerns = self._analyze_hardcoded_dates(pine_code)
        score += date_score
        concerns.extend(date_concerns)

        # 4. 성과 지표 분석 (있는 경우)
        if performance:
            perf_score, perf_concerns = self._analyze_performance(performance, param_count)
            score += perf_score
            concerns.extend(perf_concerns)

        # 5. 코드 복잡도 분석
        complexity_score, complexity_concerns = self._analyze_complexity(pine_code)
        score += complexity_score
        concerns.extend(complexity_concerns)

        # 점수 범위 제한
        score = min(100, score)

        # 위험 수준 결정
        if score >= 70:
            risk_level = "critical"
            recommendations.append("이 전략은 과적합 위험이 매우 높습니다. 실거래 사용을 권장하지 않습니다.")
        elif score >= 50:
            risk_level = "high"
            recommendations.append("파라미터 수를 줄이고, Walk-forward 테스트를 수행하세요.")
        elif score >= 30:
            risk_level = "medium"
            recommendations.append("Out-of-sample 테스트로 검증이 필요합니다.")
        else:
            risk_level = "low"
            recommendations.append("과적합 위험이 낮습니다.")

        return OverfittingAnalysis(
            score=score,
            risk_level=risk_level,
            parameter_count=param_count,
            magic_numbers=magic_numbers[:10],  # 상위 10개만
            hardcoded_dates=dates,
            concerns=concerns,
            recommendations=recommendations
        )

    def _analyze_parameters(
        self,
        code: str,
        inputs: Optional[List[Dict]]
    ) -> tuple[int, float, List[str]]:
        """파라미터 수 분석"""
        concerns = []

        # inputs가 제공되면 사용, 아니면 직접 파싱
        if inputs:
            param_count = len(inputs)
        else:
            # input.int, input.float, input.bool 등 모든 input 패턴
            input_patterns = [
                r'input\s*\(',
                r'input\.int\s*\(',
                r'input\.float\s*\(',
                r'input\.bool\s*\(',
                r'input\.string\s*\(',
                r'input\.source\s*\(',
                r'input\.timeframe\s*\(',
                r'input\.session\s*\(',
            ]

            param_count = 0
            for pattern in input_patterns:
                param_count += len(re.findall(pattern, code, re.IGNORECASE))

        # 점수 계산
        score = 0
        if param_count > self.PARAM_THRESHOLDS["critical"]:
            score = 40
            concerns.append(f"과도한 파라미터 수: {param_count}개 (권장: 5개 이하)")
        elif param_count > self.PARAM_THRESHOLDS["danger"]:
            score = 25
            concerns.append(f"많은 파라미터: {param_count}개")
        elif param_count > self.PARAM_THRESHOLDS["warning"]:
            score = 15
            concerns.append(f"파라미터 수 주의: {param_count}개")

        return param_count, score, concerns

    def _analyze_magic_numbers(self, code: str) -> tuple[List[str], float, List[str]]:
        """매직 넘버 탐지"""
        concerns = []

        # 3자리 이상 숫자 찾기 (단, 버전, 년도 제외)
        all_numbers = re.findall(r'(?<![.\d@])\b(\d{3,})\b(?![.\d])', code)

        # 필터링: 년도(2020-2030), 일반적인 값(100, 200 등) 제외
        suspicious = []
        common_values = {'100', '200', '300', '500', '1000', '2000', '10000'}

        for num in all_numbers:
            num_int = int(num)
            if num in common_values:
                continue
            if 2015 <= num_int <= 2030:  # 년도
                continue
            if num_int % 100 == 0 and num_int <= 10000:  # 라운드 넘버
                continue
            suspicious.append(num)

        # 중복 제거
        magic_numbers = list(set(suspicious))

        # 점수 계산
        score = 0
        if len(magic_numbers) > 10:
            score = 25
            concerns.append(f"다수의 매직 넘버: {len(magic_numbers)}개 (과적합 징후)")
        elif len(magic_numbers) > 5:
            score = 15
            concerns.append(f"매직 넘버 다수: {magic_numbers[:5]}")
        elif len(magic_numbers) > 2:
            score = 5
            concerns.append(f"매직 넘버 발견: {magic_numbers[:3]}")

        return magic_numbers, score, concerns

    def _analyze_hardcoded_dates(self, code: str) -> tuple[List[str], float, List[str]]:
        """하드코딩된 날짜 탐지"""
        concerns = []

        # 날짜 패턴: YYYY-MM-DD, YYYY/MM/DD, timestamp(숫자)
        date_patterns = [
            r'\d{4}[-/]\d{2}[-/]\d{2}',  # 2024-01-15
            r'timestamp\s*\(\s*\d{4}\s*,',  # timestamp(2024,
            r'year\s*==\s*\d{4}',  # year == 2024
            r'month\s*==\s*\d{1,2}',  # month == 3
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, code)
            dates.extend(matches)

        # 점수 계산
        score = 0
        if dates:
            score = 35
            concerns.append(f"하드코딩된 날짜 발견: {dates[:3]} (특정 기간 최적화 의심)")

        return dates, score, concerns

    def _analyze_performance(
        self,
        performance: Dict,
        param_count: int
    ) -> tuple[float, List[str]]:
        """성과 지표 기반 과적합 분석"""
        concerns = []
        score = 0

        profit_factor = performance.get('profit_factor', 0)
        win_rate = performance.get('win_rate', 0)
        total_trades = performance.get('total_trades', 0)

        # 비현실적으로 높은 성과
        if profit_factor > 5 and win_rate > 80:
            score += 30
            concerns.append(f"비현실적 성과: PF={profit_factor}, WR={win_rate}% (과적합 가능성 높음)")
        elif profit_factor > 3 and win_rate > 70:
            score += 15
            concerns.append(f"매우 높은 성과: PF={profit_factor}, WR={win_rate}%")

        # 거래 횟수 대비 파라미터 비율
        if total_trades > 0 and param_count > 0:
            ratio = total_trades / param_count
            if ratio < 10:
                score += 20
                concerns.append(f"거래수/파라미터 비율 낮음: {ratio:.1f} (최소 50 권장)")
            elif ratio < 30:
                score += 10
                concerns.append(f"거래수/파라미터 비율 주의: {ratio:.1f}")

        return score, concerns

    def _analyze_complexity(self, code: str) -> tuple[float, List[str]]:
        """코드 복잡도 분석"""
        concerns = []
        score = 0

        # if 문 개수
        if_count = len(re.findall(r'\bif\b', code))

        # and/or 조건 개수
        condition_count = len(re.findall(r'\b(and|or)\b', code))

        # 과도한 조건 분기
        if if_count > 30:
            score += 15
            concerns.append(f"복잡한 조건 분기: {if_count}개 if문")

        if condition_count > 50:
            score += 10
            concerns.append(f"많은 조건 연결: {condition_count}개 and/or")

        return score, concerns
