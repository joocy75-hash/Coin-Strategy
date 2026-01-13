#!/usr/bin/env python3
"""
Pine Script Parser - pynescript 기반 AST 분석

Pine Script를 AST로 파싱하여 정적 분석을 수행합니다.
LLM 호출 없이 리페인팅/오버피팅 위험을 탐지합니다.

GitHub: https://github.com/elbakramer/pynescript
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# pynescript 임포트 시도
try:
    import pynescript
    from pynescript import parse
    from pynescript.ast import nodes as ast_nodes
    PYNESCRIPT_AVAILABLE = True
except ImportError:
    PYNESCRIPT_AVAILABLE = False
    pynescript = None


class RiskLevel(Enum):
    """위험 수준"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RepaintingIssue:
    """리페인팅 이슈"""
    type: str
    severity: RiskLevel
    line: Optional[int] = None
    code_snippet: Optional[str] = None
    description: str = ""
    recommendation: str = ""


@dataclass
class OverfittingIssue:
    """오버피팅 이슈"""
    type: str
    severity: RiskLevel
    count: int = 0
    examples: List[str] = field(default_factory=list)
    description: str = ""
    recommendation: str = ""


@dataclass
class PineAnalysisResult:
    """Pine Script 분석 결과"""
    success: bool
    pine_version: int = 5
    
    # 리페인팅 분석
    repainting_risk: RiskLevel = RiskLevel.NONE
    repainting_score: float = 100.0
    repainting_issues: List[RepaintingIssue] = field(default_factory=list)
    
    # 오버피팅 분석
    overfitting_risk: RiskLevel = RiskLevel.NONE
    overfitting_score: float = 100.0
    overfitting_issues: List[OverfittingIssue] = field(default_factory=list)
    
    # 코드 메트릭
    total_lines: int = 0
    parameter_count: int = 0
    indicator_count: int = 0
    condition_complexity: int = 0
    
    # 에러
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "pine_version": self.pine_version,
            "repainting": {
                "risk": self.repainting_risk.value,
                "score": self.repainting_score,
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity.value,
                        "line": i.line,
                        "description": i.description,
                        "recommendation": i.recommendation,
                    }
                    for i in self.repainting_issues
                ],
            },
            "overfitting": {
                "risk": self.overfitting_risk.value,
                "score": self.overfitting_score,
                "issues": [
                    {
                        "type": i.type,
                        "severity": i.severity.value,
                        "count": i.count,
                        "examples": i.examples[:5],
                        "description": i.description,
                        "recommendation": i.recommendation,
                    }
                    for i in self.overfitting_issues
                ],
            },
            "metrics": {
                "total_lines": self.total_lines,
                "parameter_count": self.parameter_count,
                "indicator_count": self.indicator_count,
                "condition_complexity": self.condition_complexity,
            },
            "error": self.error,
        }


class PineScriptAnalyzer:
    """
    Pine Script 정적 분석기
    
    pynescript를 사용하여 AST 기반 분석을 수행합니다.
    LLM 호출 없이 리페인팅/오버피팅 위험을 탐지합니다.
    """
    
    # 리페인팅 위험 패턴
    REPAINTING_PATTERNS = {
        # Critical - 확실한 리페인팅
        "critical": [
            (r'\blookahead\s*=\s*barmerge\.lookahead_on\b', "lookahead_on 사용"),
            (r'\brequest\.security\s*\([^)]*lookahead\s*=\s*barmerge\.lookahead_on', "security lookahead_on"),
        ],
        # High - 높은 리페인팅 위험
        "high": [
            (r'\bbarstate\.isrealtime\b', "barstate.isrealtime 사용"),
            (r'\bbarstate\.isconfirmed\s*==\s*false\b', "미확정 바 사용"),
            (r'\btimenow\b', "timenow 사용 (실시간 변경)"),
            (r'\bsecurity\s*\([^)]*\)\s*(?!.*lookahead)', "security without lookahead (v4)"),
        ],
        # Medium - 중간 위험
        "medium": [
            (r'\bvarip\b', "varip 변수 사용"),
            (r'\brequest\.security\s*\([^)]*gaps\s*=\s*barmerge\.gaps_on', "gaps_on 사용"),
            (r'\bta\.pivothigh\b|\bta\.pivotlow\b', "피봇 함수 (지연 확정)"),
            (r'\bta\.valuewhen\b', "valuewhen 함수"),
        ],
        # Low - 낮은 위험 (주의 필요)
        "low": [
            (r'\bclose\[\d+\]', "과거 close 참조"),
            (r'\bhigh\[\d+\]|\blow\[\d+\]', "과거 high/low 참조"),
        ],
    }
    
    # 오버피팅 위험 패턴
    OVERFITTING_PATTERNS = {
        # 매직 넘버 (하드코딩된 숫자)
        "magic_numbers": r'\b(?<!\.)\d+\.?\d*(?!\d)(?!\s*[,\)\]])',
        # 하드코딩된 날짜
        "hardcoded_dates": r'\b(19|20)\d{2}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b',
        # timestamp 패턴
        "timestamp": r'\btimestamp\s*\(\s*\d{4}',
        # 연도 체크
        "year_check": r'\byear\s*[<>=!]+\s*\d{4}\b',
        # 월 체크
        "month_check": r'\bmonth\s*[<>=!]+\s*\d{1,2}\b',
        # 복잡한 조건
        "complex_conditions": r'\b(and|or)\b',
        # input 파라미터
        "input_params": r'\binput\s*\.\s*(int|float|bool|string|source|timeframe)',
    }
    
    # 안전한 숫자 (오버피팅으로 간주하지 않음)
    SAFE_NUMBERS = {0, 1, 2, 3, 5, 10, 14, 20, 50, 100, 200}
    
    def __init__(self, use_pynescript: bool = True):
        """
        Args:
            use_pynescript: pynescript AST 파싱 사용 여부
        """
        self.use_pynescript = use_pynescript and PYNESCRIPT_AVAILABLE
        
    def analyze(self, pine_code: str) -> PineAnalysisResult:
        """
        Pine Script 코드 분석
        
        Args:
            pine_code: Pine Script 소스 코드
            
        Returns:
            PineAnalysisResult: 분석 결과
        """
        if not pine_code or len(pine_code.strip()) < 10:
            return PineAnalysisResult(
                success=False,
                error="코드가 너무 짧거나 비어있습니다."
            )
        
        result = PineAnalysisResult(success=True)
        
        # 기본 메트릭
        result.total_lines = len(pine_code.split('\n'))
        result.pine_version = self._detect_version(pine_code)
        
        # AST 기반 분석 (pynescript 사용 가능한 경우)
        if self.use_pynescript:
            try:
                ast_result = self._analyze_with_ast(pine_code)
                if ast_result:
                    result.parameter_count = ast_result.get("parameters", 0)
                    result.indicator_count = ast_result.get("indicators", 0)
                    result.condition_complexity = ast_result.get("complexity", 0)
            except Exception as e:
                # AST 파싱 실패 시 정규식 기반 분석으로 폴백
                pass
        
        # 정규식 기반 분석 (항상 수행)
        self._analyze_repainting(pine_code, result)
        self._analyze_overfitting(pine_code, result)
        
        # 최종 점수 계산
        self._calculate_scores(result)
        
        return result
    
    def _detect_version(self, code: str) -> int:
        """Pine Script 버전 감지"""
        match = re.search(r'//@version\s*=?\s*(\d+)', code)
        if match:
            return int(match.group(1))
        
        # 버전 표시 없으면 문법으로 추정
        if 'request.security' in code or 'ta.' in code:
            return 5
        elif 'security(' in code:
            return 4
        return 5
    
    def _analyze_with_ast(self, code: str) -> Optional[Dict[str, int]]:
        """pynescript AST 기반 분석"""
        if not PYNESCRIPT_AVAILABLE:
            return None
            
        try:
            tree = parse(code)
            
            metrics = {
                "parameters": 0,
                "indicators": 0,
                "complexity": 0,
            }
            
            # AST 순회하며 메트릭 수집
            self._walk_ast(tree, metrics)
            
            return metrics
            
        except Exception:
            return None
    
    def _walk_ast(self, node, metrics: Dict[str, int]):
        """AST 노드 순회"""
        if not PYNESCRIPT_AVAILABLE or node is None:
            return
            
        # input 함수 호출 카운트
        if hasattr(node, 'func') and hasattr(node.func, 'id'):
            if 'input' in str(node.func.id):
                metrics["parameters"] += 1
            elif any(ind in str(node.func.id) for ind in ['sma', 'ema', 'rsi', 'macd', 'bb']):
                metrics["indicators"] += 1
        
        # 조건문 복잡도
        if hasattr(node, '__class__') and 'If' in node.__class__.__name__:
            metrics["complexity"] += 1
        
        # 자식 노드 순회
        for child in getattr(node, 'children', []):
            self._walk_ast(child, metrics)
    
    def _analyze_repainting(self, code: str, result: PineAnalysisResult):
        """리페인팅 위험 분석"""
        lines = code.split('\n')
        
        for severity, patterns in self.REPAINTING_PATTERNS.items():
            risk_level = {
                "critical": RiskLevel.CRITICAL,
                "high": RiskLevel.HIGH,
                "medium": RiskLevel.MEDIUM,
                "low": RiskLevel.LOW,
            }[severity]
            
            for pattern, description in patterns:
                for i, line in enumerate(lines, 1):
                    # 주석 제외
                    if line.strip().startswith('//'):
                        continue
                        
                    if re.search(pattern, line, re.IGNORECASE):
                        result.repainting_issues.append(RepaintingIssue(
                            type=description,
                            severity=risk_level,
                            line=i,
                            code_snippet=line.strip()[:100],
                            description=f"{description} - 리페인팅 위험",
                            recommendation=self._get_repainting_recommendation(description),
                        ))
        
        # 최고 위험 수준 결정
        if result.repainting_issues:
            max_severity = max(i.severity.value for i in result.repainting_issues)
            result.repainting_risk = RiskLevel(max_severity)
    
    def _analyze_overfitting(self, code: str, result: PineAnalysisResult):
        """오버피팅 위험 분석"""
        # 주석 제거
        code_no_comments = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code_no_comments = re.sub(r'/\*.*?\*/', '', code_no_comments, flags=re.DOTALL)
        
        # 매직 넘버 분석
        magic_numbers = re.findall(self.OVERFITTING_PATTERNS["magic_numbers"], code_no_comments)
        suspicious_numbers = []
        for num_str in magic_numbers:
            try:
                num = float(num_str)
                if num not in self.SAFE_NUMBERS and num > 3:
                    suspicious_numbers.append(num_str)
            except ValueError:
                pass
        
        if len(suspicious_numbers) > 5:
            result.overfitting_issues.append(OverfittingIssue(
                type="magic_numbers",
                severity=RiskLevel.MEDIUM if len(suspicious_numbers) < 15 else RiskLevel.HIGH,
                count=len(suspicious_numbers),
                examples=suspicious_numbers[:10],
                description=f"{len(suspicious_numbers)}개의 하드코딩된 숫자 발견",
                recommendation="input() 함수로 파라미터화하여 최적화 가능하게 만드세요.",
            ))
        
        # 하드코딩된 날짜
        dates = re.findall(self.OVERFITTING_PATTERNS["hardcoded_dates"], code_no_comments)
        if dates:
            result.overfitting_issues.append(OverfittingIssue(
                type="hardcoded_dates",
                severity=RiskLevel.HIGH,
                count=len(dates),
                examples=['-'.join(d) for d in dates[:5]],
                description="하드코딩된 날짜 발견 - 특정 기간에만 작동할 수 있음",
                recommendation="날짜 필터를 제거하거나 input으로 변경하세요.",
            ))
        
        # timestamp 패턴
        timestamps = re.findall(self.OVERFITTING_PATTERNS["timestamp"], code_no_comments)
        if timestamps:
            result.overfitting_issues.append(OverfittingIssue(
                type="timestamp_filter",
                severity=RiskLevel.HIGH,
                count=len(timestamps),
                examples=timestamps[:5],
                description="timestamp 기반 필터 발견",
                recommendation="특정 시간대 필터는 오버피팅 위험이 높습니다.",
            ))
        
        # input 파라미터 수
        inputs = re.findall(self.OVERFITTING_PATTERNS["input_params"], code_no_comments)
        result.parameter_count = max(result.parameter_count, len(inputs))
        
        if len(inputs) > 10:
            result.overfitting_issues.append(OverfittingIssue(
                type="too_many_parameters",
                severity=RiskLevel.MEDIUM if len(inputs) < 20 else RiskLevel.HIGH,
                count=len(inputs),
                description=f"{len(inputs)}개의 파라미터 - 과최적화 위험",
                recommendation="파라미터 수를 줄이고 핵심 로직에 집중하세요.",
            ))
        
        # 복잡한 조건
        conditions = re.findall(self.OVERFITTING_PATTERNS["complex_conditions"], code_no_comments)
        result.condition_complexity = max(result.condition_complexity, len(conditions))
        
        if len(conditions) > 20:
            result.overfitting_issues.append(OverfittingIssue(
                type="complex_conditions",
                severity=RiskLevel.MEDIUM,
                count=len(conditions),
                description="복잡한 조건문 - 커브피팅 위험",
                recommendation="조건을 단순화하고 핵심 신호에 집중하세요.",
            ))
        
        # 최고 위험 수준 결정
        if result.overfitting_issues:
            max_severity = max(i.severity.value for i in result.overfitting_issues)
            result.overfitting_risk = RiskLevel(max_severity)
    
    def _calculate_scores(self, result: PineAnalysisResult):
        """점수 계산"""
        # 리페인팅 점수 (100점 만점)
        repainting_deductions = {
            RiskLevel.CRITICAL: 50,
            RiskLevel.HIGH: 30,
            RiskLevel.MEDIUM: 15,
            RiskLevel.LOW: 5,
        }
        
        repainting_penalty = sum(
            repainting_deductions.get(issue.severity, 0)
            for issue in result.repainting_issues
        )
        result.repainting_score = max(0, 100 - repainting_penalty)
        
        # 오버피팅 점수 (100점 만점)
        overfitting_deductions = {
            RiskLevel.CRITICAL: 40,
            RiskLevel.HIGH: 25,
            RiskLevel.MEDIUM: 12,
            RiskLevel.LOW: 5,
        }
        
        overfitting_penalty = sum(
            overfitting_deductions.get(issue.severity, 0)
            for issue in result.overfitting_issues
        )
        result.overfitting_score = max(0, 100 - overfitting_penalty)
    
    def _get_repainting_recommendation(self, issue_type: str) -> str:
        """리페인팅 이슈별 권장사항"""
        recommendations = {
            "lookahead_on 사용": "lookahead=barmerge.lookahead_off로 변경하세요.",
            "security lookahead_on": "request.security에서 lookahead_off를 사용하세요.",
            "barstate.isrealtime 사용": "실시간 바 체크를 제거하거나 barstate.isconfirmed를 사용하세요.",
            "미확정 바 사용": "barstate.isconfirmed == true 조건을 사용하세요.",
            "timenow 사용 (실시간 변경)": "timenow 대신 time을 사용하세요.",
            "security without lookahead (v4)": "Pine v5로 업그레이드하고 lookahead_off를 명시하세요.",
            "varip 변수 사용": "varip는 실시간에서만 업데이트됩니다. var 사용을 고려하세요.",
            "gaps_on 사용": "gaps_off 사용을 권장합니다.",
            "피봇 함수 (지연 확정)": "피봇은 N개 바 후에 확정됩니다. 지연을 고려하세요.",
            "valuewhen 함수": "valuewhen은 조건 발생 시점의 값을 반환합니다.",
        }
        return recommendations.get(issue_type, "코드를 검토하고 리페인팅 위험을 제거하세요.")


# 싱글톤 인스턴스
_analyzer: Optional[PineScriptAnalyzer] = None


def get_pine_analyzer() -> PineScriptAnalyzer:
    """Pine Script 분석기 싱글톤 인스턴스"""
    global _analyzer
    if _analyzer is None:
        _analyzer = PineScriptAnalyzer()
    return _analyzer


def analyze_pine_script(code: str) -> Dict[str, Any]:
    """
    Pine Script 분석 (편의 함수)
    
    Args:
        code: Pine Script 소스 코드
        
    Returns:
        분석 결과 딕셔너리
    """
    analyzer = get_pine_analyzer()
    result = analyzer.analyze(code)
    return result.to_dict()


if __name__ == "__main__":
    # 테스트
    test_code = '''
//@version=5
strategy("Test Strategy", overlay=true)

// 리페인팅 위험 코드
data = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)

// 오버피팅 위험 코드
length = input.int(14, "Length")
threshold = 0.0234  // 매직 넘버
startDate = timestamp(2020, 1, 1)

if time > startDate
    if ta.crossover(ta.sma(close, length), ta.sma(close, 50))
        strategy.entry("Long", strategy.long)
'''
    
    print("Pine Script 분석 테스트")
    print("=" * 50)
    print(f"pynescript 사용 가능: {PYNESCRIPT_AVAILABLE}")
    print()
    
    result = analyze_pine_script(test_code)
    
    print(f"분석 성공: {result['success']}")
    print(f"Pine 버전: {result['pine_version']}")
    print()
    print(f"리페인팅 위험: {result['repainting']['risk']}")
    print(f"리페인팅 점수: {result['repainting']['score']}")
    for issue in result['repainting']['issues']:
        print(f"  - [{issue['severity']}] {issue['type']} (라인 {issue['line']})")
    print()
    print(f"오버피팅 위험: {result['overfitting']['risk']}")
    print(f"오버피팅 점수: {result['overfitting']['score']}")
    for issue in result['overfitting']['issues']:
        print(f"  - [{issue['severity']}] {issue['type']} ({issue['count']}개)")
