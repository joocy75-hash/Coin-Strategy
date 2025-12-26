"""
Pydantic 데이터 모델

TradingView 전략 연구소의 모든 데이터 모델 정의
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class StrategyModel(BaseModel):
    """전략 메타데이터 및 코드"""

    script_id: str = Field(..., description="TradingView 스크립트 고유 ID")
    title: str = Field(..., description="전략 제목")
    author: str = Field(..., description="작성자")
    likes: int = Field(default=0, description="좋아요 수")
    views: int = Field(default=0, description="조회수")

    # Pine Script 관련
    pine_code: Optional[str] = Field(default=None, description="Pine Script 원본 코드")
    pine_version: int = Field(default=5, description="Pine Script 버전")

    # 성과 및 분석
    performance: Optional[Dict[str, Any]] = Field(default=None, description="백테스트 성과 지표")
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="분석 결과")

    # 메타데이터
    script_url: str = Field(default="", description="스크립트 URL")
    description: str = Field(default="", description="전략 설명")
    is_open_source: bool = Field(default=False, description="오픈소스 여부")
    category: str = Field(default="strategy", description="카테고리")

    # 타임스탬프
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @field_validator('pine_code', mode='before')
    @classmethod
    def validate_pine_code(cls, v):
        if v and len(v) < 10:
            return None
        return v


class RepaintingAnalysisModel(BaseModel):
    """Repainting 분석 결과"""

    risk_level: str = Field(..., description="위험 수준: NONE, LOW, MEDIUM, HIGH, CRITICAL")
    score: float = Field(..., ge=0, le=100, description="점수 (0-100, 높을수록 안전)")
    issues: List[str] = Field(default_factory=list, description="발견된 문제점")
    safe_patterns: List[str] = Field(default_factory=list, description="안전한 패턴")
    confidence: float = Field(default=0.7, ge=0, le=1, description="분석 신뢰도")
    details: str = Field(default="", description="상세 설명")


class OverfittingAnalysisModel(BaseModel):
    """과적합 분석 결과"""

    score: float = Field(..., ge=0, le=100, description="과적합 위험 점수 (높을수록 위험)")
    risk_level: str = Field(..., description="위험 수준: low, medium, high, critical")
    parameter_count: int = Field(default=0, description="파라미터 개수")
    magic_numbers: List[str] = Field(default_factory=list, description="매직 넘버 목록")
    hardcoded_dates: List[str] = Field(default_factory=list, description="하드코딩된 날짜")
    concerns: List[str] = Field(default_factory=list, description="우려사항")
    recommendations: List[str] = Field(default_factory=list, description="권장사항")


class LLMAnalysisModel(BaseModel):
    """LLM 심층 분석 결과"""

    logic_score: int = Field(..., ge=1, le=10, description="로직 견고성 점수")
    risk_score: int = Field(..., ge=1, le=10, description="리스크 관리 점수")
    practical_score: int = Field(..., ge=1, le=10, description="실거래 적합성 점수")
    code_quality_score: int = Field(..., ge=1, le=10, description="코드 품질 점수")
    total_score: int = Field(..., ge=0, le=100, description="총점")

    recommendation: str = Field(..., description="추천 등급: PASS, REVIEW, REJECT")
    strengths: List[str] = Field(default_factory=list, description="강점")
    weaknesses: List[str] = Field(default_factory=list, description="약점")
    summary_kr: str = Field(default="", description="한국어 요약")
    conversion_notes: str = Field(default="", description="Python 변환 주의사항")


class AnalysisResultModel(BaseModel):
    """종합 분석 결과"""

    total_score: float = Field(..., ge=0, le=100, description="최종 점수")
    grade: str = Field(..., description="등급: A, B, C, D, F")
    status: str = Field(..., description="상태: passed, review, rejected")

    # 세부 분석
    repainting_analysis: Optional[RepaintingAnalysisModel] = None
    overfitting_analysis: Optional[OverfittingAnalysisModel] = None
    llm_analysis: Optional[LLMAnalysisModel] = None

    # 메타
    analyzed_at: datetime = Field(default_factory=datetime.now)
    analysis_version: str = Field(default="1.0", description="분석 버전")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConvertedStrategyModel(BaseModel):
    """변환된 Python 전략"""

    strategy_code: str = Field(..., description="전략 코드 (파일명 기반)")
    python_code: str = Field(..., description="생성된 Python 코드")
    template_type: str = Field(default="basic", description="사용된 템플릿: basic, ai, autonomous")

    # 원본 정보
    original_script_id: str = Field(..., description="원본 스크립트 ID")
    original_title: str = Field(..., description="원본 전략 제목")

    # 메타
    generated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[str] = Field(default=None, description="저장된 파일 경로")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchFilters(BaseModel):
    """데이터베이스 검색 필터"""

    min_likes: Optional[int] = Field(default=None, description="최소 좋아요 수")
    max_likes: Optional[int] = Field(default=None, description="최대 좋아요 수")

    min_score: Optional[float] = Field(default=None, ge=0, le=100, description="최소 점수")
    max_score: Optional[float] = Field(default=None, ge=0, le=100, description="최대 점수")

    grade: Optional[List[str]] = Field(default=None, description="등급 필터: ['A', 'B']")
    status: Optional[List[str]] = Field(default=None, description="상태 필터: ['passed', 'review']")

    keywords: Optional[List[str]] = Field(default=None, description="검색 키워드 (제목, 설명)")
    author: Optional[str] = Field(default=None, description="작성자 필터")

    has_pine_code: Optional[bool] = Field(default=None, description="Pine 코드 존재 여부")
    has_analysis: Optional[bool] = Field(default=None, description="분석 완료 여부")

    # 정렬
    order_by: str = Field(default="likes", description="정렬 기준: likes, score, created_at")
    order_desc: bool = Field(default=True, description="내림차순 여부")

    # 페이징
    limit: int = Field(default=100, ge=1, le=1000, description="최대 결과 수")
    offset: int = Field(default=0, ge=0, description="오프셋")


class DatabaseStats(BaseModel):
    """데이터베이스 통계"""

    total_strategies: int = Field(default=0, description="전체 전략 수")

    # Pine 코드
    with_pine_code: int = Field(default=0, description="Pine 코드 있는 전략 수")
    open_source_count: int = Field(default=0, description="오픈소스 전략 수")

    # 분석 상태
    analyzed_count: int = Field(default=0, description="분석 완료 전략 수")
    passed_count: int = Field(default=0, description="통과 전략 수")
    review_count: int = Field(default=0, description="검토 필요 전략 수")
    rejected_count: int = Field(default=0, description="거부 전략 수")

    # 등급 분포
    grade_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
        description="등급별 분포"
    )

    # 통계
    avg_likes: float = Field(default=0, description="평균 좋아요 수")
    avg_score: float = Field(default=0, description="평균 점수")

    # 최고 점수
    top_strategy: Optional[Dict[str, Any]] = Field(default=None, description="최고 점수 전략")

    # 타임스탬프
    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
