"""
수집 단계 품질 점수 시스템

전략을 분석하기 전에 수집 단계에서 품질이 좋은 전략만 선별합니다.

품질 점수 구성:
1. 인기도 점수 (40%): 좋아요, 조회수
2. 작성자 신뢰도 (30%): 팔로워 수, 총 스크립트 수, 평판
3. 최신성 점수 (15%): Pine 버전, 업데이트 주기
4. 커뮤니티 반응 (15%): 댓글 수, 공유 수
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import re


@dataclass
class QualityMetrics:
    """수집 단계 품질 지표"""
    # 기본 정보
    script_id: str
    title: str
    author: str
    script_url: str

    # 인기도 지표
    likes: int = 0
    views: int = 0
    comments: int = 0
    shares: int = 0

    # 작성자 정보
    author_followers: int = 0
    author_scripts_count: int = 0
    author_reputation: int = 0
    is_verified: bool = False
    is_premium: bool = False

    # 전략 정보
    pine_version: int = 5
    is_open_source: bool = True
    publish_date: Optional[str] = None
    update_date: Optional[str] = None

    # 계산된 점수
    popularity_score: float = 0.0
    author_score: float = 0.0
    freshness_score: float = 0.0
    community_score: float = 0.0
    total_quality_score: float = 0.0

    def calculate_scores(self) -> float:
        """품질 점수 계산"""
        self._calculate_popularity_score()
        self._calculate_author_score()
        self._calculate_freshness_score()
        self._calculate_community_score()

        # 가중 평균
        self.total_quality_score = (
            self.popularity_score * 0.40 +
            self.author_score * 0.30 +
            self.freshness_score * 0.15 +
            self.community_score * 0.15
        )

        return self.total_quality_score

    def _calculate_popularity_score(self):
        """인기도 점수 (0-100)"""
        # 좋아요 기준 (로그 스케일)
        # 100+ = 40, 500+ = 60, 1000+ = 80, 5000+ = 100
        if self.likes >= 5000:
            likes_score = 100
        elif self.likes >= 1000:
            likes_score = 80 + (self.likes - 1000) / 200
        elif self.likes >= 500:
            likes_score = 60 + (self.likes - 500) / 25
        elif self.likes >= 100:
            likes_score = 40 + (self.likes - 100) / 20
        elif self.likes >= 50:
            likes_score = 20 + (self.likes - 50) / 2.5
        else:
            likes_score = self.likes * 0.4

        # 조회수 기준 (보조 지표)
        # 10K+ = 20점 추가
        views_bonus = min(20, self.views / 500)

        self.popularity_score = min(100, likes_score + views_bonus)

    def _calculate_author_score(self):
        """작성자 신뢰도 점수 (0-100)"""
        score = 0

        # 팔로워 수
        if self.author_followers >= 10000:
            score += 40
        elif self.author_followers >= 1000:
            score += 30
        elif self.author_followers >= 100:
            score += 20
        elif self.author_followers >= 10:
            score += 10

        # 스크립트 수 (경험 지표)
        if self.author_scripts_count >= 50:
            score += 30
        elif self.author_scripts_count >= 20:
            score += 25
        elif self.author_scripts_count >= 10:
            score += 20
        elif self.author_scripts_count >= 5:
            score += 15
        elif self.author_scripts_count >= 1:
            score += 10

        # 인증/프리미엄 여부
        if self.is_verified:
            score += 20
        if self.is_premium:
            score += 10

        self.author_score = min(100, score)

    def _calculate_freshness_score(self):
        """최신성 점수 (0-100)"""
        score = 0

        # Pine Script 버전 (최신일수록 좋음)
        if self.pine_version >= 5:
            score += 50
        elif self.pine_version == 4:
            score += 30
        elif self.pine_version == 3:
            score += 10
        else:
            score += 0

        # 오픈소스 여부 (코드 검증 가능)
        if self.is_open_source:
            score += 50
        else:
            score += 0  # protected 스크립트는 검증 불가

        self.freshness_score = min(100, score)

    def _calculate_community_score(self):
        """커뮤니티 반응 점수 (0-100)"""
        score = 0

        # 댓글 수 (활발한 토론 = 좋은 신호)
        if self.comments >= 100:
            score += 50
        elif self.comments >= 50:
            score += 40
        elif self.comments >= 20:
            score += 30
        elif self.comments >= 10:
            score += 20
        elif self.comments >= 5:
            score += 10

        # 좋아요 대비 댓글 비율 (참여도)
        if self.likes > 0:
            engagement_ratio = self.comments / self.likes
            if engagement_ratio >= 0.1:  # 10% 이상이면 활발
                score += 30
            elif engagement_ratio >= 0.05:
                score += 20
            elif engagement_ratio >= 0.02:
                score += 10

        # 공유 수
        if self.shares >= 10:
            score += 20
        elif self.shares >= 5:
            score += 10

        self.community_score = min(100, score)

    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            "script_id": self.script_id,
            "title": self.title,
            "author": self.author,
            "script_url": self.script_url,
            "likes": self.likes,
            "views": self.views,
            "comments": self.comments,
            "author_followers": self.author_followers,
            "author_scripts_count": self.author_scripts_count,
            "pine_version": self.pine_version,
            "is_open_source": self.is_open_source,
            "popularity_score": round(self.popularity_score, 1),
            "author_score": round(self.author_score, 1),
            "freshness_score": round(self.freshness_score, 1),
            "community_score": round(self.community_score, 1),
            "total_quality_score": round(self.total_quality_score, 1)
        }


class PreCollectionFilter:
    """수집 전 품질 필터"""

    def __init__(
        self,
        min_quality_score: float = 50.0,
        min_likes: int = 100,
        require_open_source: bool = True,
        min_pine_version: int = 4
    ):
        self.min_quality_score = min_quality_score
        self.min_likes = min_likes
        self.require_open_source = require_open_source
        self.min_pine_version = min_pine_version

    def should_collect(self, metrics: QualityMetrics) -> tuple[bool, List[str]]:
        """
        수집 여부 결정

        Returns:
            (수집 여부, 탈락 사유 목록)
        """
        reasons = []

        # 필수 조건
        if metrics.likes < self.min_likes:
            reasons.append(f"좋아요 부족: {metrics.likes} < {self.min_likes}")

        if self.require_open_source and not metrics.is_open_source:
            reasons.append("오픈소스 아님 (코드 검증 불가)")

        if metrics.pine_version < self.min_pine_version:
            reasons.append(f"Pine 버전 낮음: v{metrics.pine_version}")

        # 품질 점수
        metrics.calculate_scores()
        if metrics.total_quality_score < self.min_quality_score:
            reasons.append(f"품질 점수 미달: {metrics.total_quality_score:.1f} < {self.min_quality_score}")

        return len(reasons) == 0, reasons

    def filter_strategies(self, strategies: List[QualityMetrics]) -> List[QualityMetrics]:
        """전략 목록 필터링"""
        passed = []
        for s in strategies:
            should_collect, reasons = self.should_collect(s)
            if should_collect:
                passed.append(s)

        # 품질 점수순 정렬
        passed.sort(key=lambda x: x.total_quality_score, reverse=True)
        return passed


# 알려진 신뢰할 수 있는 작성자 목록
TRUSTED_AUTHORS = {
    "LuxAlgo": {"followers": 100000, "verified": True},
    "QuantNomad": {"followers": 50000, "verified": True},
    "TradingView": {"followers": 500000, "verified": True},
    "ChartPrime": {"followers": 30000, "verified": True},
    "BigBeluga": {"followers": 20000, "verified": True},
    "QuantEdgeB": {"followers": 10000, "verified": True},
    "BackQuant": {"followers": 5000, "verified": False},
    # 추가 가능
}


def get_author_trust_score(author: str) -> tuple[int, bool]:
    """
    알려진 작성자인 경우 신뢰도 정보 반환

    Returns:
        (예상 팔로워 수, 인증 여부)
    """
    if author in TRUSTED_AUTHORS:
        info = TRUSTED_AUTHORS[author]
        return info["followers"], info["verified"]
    return 0, False
