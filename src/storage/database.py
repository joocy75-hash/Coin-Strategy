"""
SQLite 비동기 데이터베이스 관리

aiosqlite를 사용한 전략 데이터 저장 및 조회
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import asdict, is_dataclass


def json_serializer(obj):
    """datetime 등 직렬화 불가능한 객체 처리"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

if TYPE_CHECKING:
    from typing import Any

import aiosqlite

from .models import (
    StrategyModel,
    AnalysisResultModel,
    SearchFilters,
    DatabaseStats,
)

logger = logging.getLogger(__name__)


class StrategyDatabase:
    """
    전략 데이터베이스 관리 클래스

    테이블 구조:
    - strategies: 전략 메타데이터 및 코드
    """

    def __init__(self, db_path: str = "data/strategies.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.init_db()
        return self

    async def __aexit__(self, *args):
        """비동기 컨텍스트 매니저 종료"""
        pass

    async def init_db(self):
        """데이터베이스 초기화 및 테이블 생성"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    script_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,

                    -- Pine Script
                    pine_code TEXT,
                    pine_version INTEGER DEFAULT 5,

                    -- 성과 및 분석 (JSON)
                    performance_json TEXT,
                    analysis_json TEXT,

                    -- 메타데이터
                    script_url TEXT,
                    description TEXT,
                    is_open_source BOOLEAN DEFAULT 0,
                    category TEXT DEFAULT 'strategy',

                    -- 타임스탬프
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # 인덱스 생성
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_likes ON strategies(likes DESC)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_author ON strategies(author)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON strategies(created_at DESC)"
            )

            await db.commit()
            logger.info(f"Database initialized: {self.db_path}")

    async def upsert_strategy(self, strategy: Dict[str, Any]) -> bool:
        """
        전략 삽입 또는 업데이트

        Args:
            strategy: 전략 데이터 딕셔너리

        Returns:
            성공 여부
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # performance와 analysis를 JSON 문자열로 변환
                performance_json = (
                    json.dumps(strategy.get("performance"), ensure_ascii=False, default=json_serializer)
                    if strategy.get("performance")
                    else None
                )
                analysis_json = (
                    json.dumps(strategy.get("analysis"), ensure_ascii=False, default=json_serializer)
                    if strategy.get("analysis")
                    else None
                )

                await db.execute(
                    """
                    INSERT INTO strategies (
                        script_id, title, author, likes, views,
                        pine_code, pine_version,
                        performance_json, analysis_json,
                        script_url, description, is_open_source, category,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(script_id) DO UPDATE SET
                        title = excluded.title,
                        author = excluded.author,
                        likes = excluded.likes,
                        views = excluded.views,
                        pine_code = COALESCE(excluded.pine_code, pine_code),
                        pine_version = excluded.pine_version,
                        performance_json = COALESCE(excluded.performance_json, performance_json),
                        analysis_json = COALESCE(excluded.analysis_json, analysis_json),
                        script_url = excluded.script_url,
                        description = excluded.description,
                        is_open_source = excluded.is_open_source,
                        category = excluded.category,
                        updated_at = excluded.updated_at
                    """,
                    (
                        strategy["script_id"],
                        strategy["title"],
                        strategy["author"],
                        strategy.get("likes", 0),
                        strategy.get("views", 0),
                        strategy.get("pine_code"),
                        strategy.get("pine_version", 5),
                        performance_json,
                        analysis_json,
                        strategy.get("script_url", ""),
                        strategy.get("description", ""),
                        strategy.get("is_open_source", False),
                        strategy.get("category", "strategy"),
                        strategy.get("created_at", datetime.now().isoformat()),
                        datetime.now().isoformat(),
                    ),
                )

                await db.commit()
                logger.debug(f"Upserted strategy: {strategy['script_id']}")
                return True

        except Exception as e:
            logger.error(f"Error upserting strategy {strategy.get('script_id')}: {e}")
            return False

    async def save_analysis(self, script_id: str, analysis: Dict[str, Any]) -> bool:
        """
        분석 결과 저장

        Args:
            script_id: 스크립트 ID
            analysis: 분석 결과 딕셔너리

        Returns:
            성공 여부
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                analysis_json = json.dumps(analysis, ensure_ascii=False, default=json_serializer)

                await db.execute(
                    """
                    UPDATE strategies
                    SET analysis_json = ?, updated_at = ?
                    WHERE script_id = ?
                    """,
                    (analysis_json, datetime.now().isoformat(), script_id),
                )

                await db.commit()
                logger.debug(f"Saved analysis for: {script_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving analysis for {script_id}: {e}")
            return False

    async def get_strategy(self, script_id: str) -> Optional[StrategyModel]:
        """
        전략 조회

        Args:
            script_id: 스크립트 ID

        Returns:
            StrategyModel 또는 None
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute(
                    "SELECT * FROM strategies WHERE script_id = ?", (script_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                    if not row:
                        return None

                    return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Error getting strategy {script_id}: {e}")
            return None

    async def search_strategies(
        self, filters: Optional[SearchFilters] = None
    ) -> List[StrategyModel]:
        """
        전략 검색

        Args:
            filters: 검색 필터

        Returns:
            StrategyModel 리스트
        """
        if filters is None:
            filters = SearchFilters()

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # 쿼리 빌드
                query = "SELECT * FROM strategies WHERE 1=1"
                params = []

                # 좋아요 필터
                if filters.min_likes is not None:
                    query += " AND likes >= ?"
                    params.append(filters.min_likes)

                if filters.max_likes is not None:
                    query += " AND likes <= ?"
                    params.append(filters.max_likes)

                # Pine 코드 존재 여부
                if filters.has_pine_code is not None:
                    if filters.has_pine_code:
                        query += " AND pine_code IS NOT NULL AND pine_code != ''"
                    else:
                        query += " AND (pine_code IS NULL OR pine_code = '')"

                # 분석 완료 여부
                if filters.has_analysis is not None:
                    if filters.has_analysis:
                        query += " AND analysis_json IS NOT NULL"
                    else:
                        query += " AND analysis_json IS NULL"

                # 작성자 필터
                if filters.author:
                    query += " AND author = ?"
                    params.append(filters.author)

                # 키워드 검색
                if filters.keywords:
                    keyword_conditions = []
                    for keyword in filters.keywords:
                        keyword_conditions.append(
                            "(title LIKE ? OR description LIKE ?)"
                        )
                        params.append(f"%{keyword}%")
                        params.append(f"%{keyword}%")
                    query += f" AND ({' OR '.join(keyword_conditions)})"

                # 정렬
                order_by_map = {
                    "likes": "likes",
                    "score": "likes",  # score는 analysis_json 파싱 필요, 임시로 likes
                    "created_at": "created_at",
                }
                order_col = order_by_map.get(filters.order_by, "likes")
                order_dir = "DESC" if filters.order_desc else "ASC"
                query += f" ORDER BY {order_col} {order_dir}"

                # 페이징
                query += " LIMIT ? OFFSET ?"
                params.append(filters.limit)
                params.append(filters.offset)

                # 실행
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()

                    results = []
                    for row in rows:
                        model = self._row_to_model(row)

                        # 추가 필터 (분석 결과 기반)
                        if filters.min_score or filters.max_score or filters.grade or filters.status:
                            if not model.analysis:
                                continue

                            analysis = model.analysis

                            # 점수 필터
                            total_score = analysis.get("total_score", 0)
                            if filters.min_score and total_score < filters.min_score:
                                continue
                            if filters.max_score and total_score > filters.max_score:
                                continue

                            # 등급 필터
                            if filters.grade:
                                grade = analysis.get("grade", "")
                                if grade not in filters.grade:
                                    continue

                            # 상태 필터
                            if filters.status:
                                status = analysis.get("status", "")
                                if status not in filters.status:
                                    continue

                        results.append(model)

                    logger.debug(f"Search returned {len(results)} strategies")
                    return results

        except Exception as e:
            logger.error(f"Error searching strategies: {e}")
            return []

    async def get_stats(self) -> DatabaseStats:
        """
        데이터베이스 통계 조회

        Returns:
            DatabaseStats
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # 기본 통계
                async with db.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN pine_code IS NOT NULL AND pine_code != '' THEN 1 ELSE 0 END) as with_code,
                        SUM(CASE WHEN is_open_source = 1 THEN 1 ELSE 0 END) as open_source,
                        SUM(CASE WHEN analysis_json IS NOT NULL THEN 1 ELSE 0 END) as analyzed,
                        AVG(likes) as avg_likes
                    FROM strategies
                    """
                ) as cursor:
                    row = await cursor.fetchone()

                    total = row["total"] or 0
                    with_code = row["with_code"] or 0
                    open_source = row["open_source"] or 0
                    analyzed = row["analyzed"] or 0
                    avg_likes = row["avg_likes"] or 0

                # 분석 상태 통계
                passed = 0
                review = 0
                rejected = 0
                grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
                total_score_sum = 0
                score_count = 0
                top_strategy = None
                top_score = 0

                async with db.execute(
                    "SELECT script_id, title, author, likes, analysis_json FROM strategies WHERE analysis_json IS NOT NULL"
                ) as cursor:
                    async for row in cursor:
                        try:
                            analysis = json.loads(row["analysis_json"])

                            # 상태 카운트
                            status = analysis.get("status", "")
                            if status == "passed":
                                passed += 1
                            elif status == "review":
                                review += 1
                            elif status == "rejected":
                                rejected += 1

                            # 등급 분포
                            grade = analysis.get("grade", "F")
                            if grade in grade_dist:
                                grade_dist[grade] += 1

                            # 점수 평균
                            total_score = analysis.get("total_score", 0)
                            total_score_sum += total_score
                            score_count += 1

                            # 최고 점수 전략
                            if total_score > top_score:
                                top_score = total_score
                                top_strategy = {
                                    "script_id": row["script_id"],
                                    "title": row["title"],
                                    "author": row["author"],
                                    "likes": row["likes"],
                                    "score": total_score,
                                    "grade": grade,
                                }

                        except Exception:
                            continue

                avg_score = total_score_sum / score_count if score_count > 0 else 0

                return DatabaseStats(
                    total_strategies=total,
                    with_pine_code=with_code,
                    open_source_count=open_source,
                    analyzed_count=analyzed,
                    passed_count=passed,
                    review_count=review,
                    rejected_count=rejected,
                    grade_distribution=grade_dist,
                    avg_likes=round(avg_likes, 1),
                    avg_score=round(avg_score, 1),
                    top_strategy=top_strategy,
                    generated_at=datetime.now(),
                )

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return DatabaseStats()

    def _row_to_model(self, row: aiosqlite.Row) -> StrategyModel:
        """
        DB Row를 StrategyModel로 변환

        Args:
            row: aiosqlite Row

        Returns:
            StrategyModel
        """
        # performance, analysis JSON 파싱
        performance = None
        if row["performance_json"]:
            try:
                performance = json.loads(row["performance_json"])
            except Exception:
                pass

        analysis = None
        if row["analysis_json"]:
            try:
                analysis = json.loads(row["analysis_json"])
            except Exception:
                pass

        return StrategyModel(
            script_id=row["script_id"],
            title=row["title"],
            author=row["author"],
            likes=row["likes"],
            views=row["views"],
            pine_code=row["pine_code"],
            pine_version=row["pine_version"],
            performance=performance,
            analysis=analysis,
            script_url=row["script_url"],
            description=row["description"],
            is_open_source=bool(row["is_open_source"]),
            category=row["category"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            updated_at=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else None,
        )

    async def delete_strategy(self, script_id: str) -> bool:
        """
        전략 삭제

        Args:
            script_id: 스크립트 ID

        Returns:
            성공 여부
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM strategies WHERE script_id = ?", (script_id,)
                )
                await db.commit()
                logger.info(f"Deleted strategy: {script_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting strategy {script_id}: {e}")
            return False

    async def get_all_script_ids(self) -> List[str]:
        """
        모든 스크립트 ID 조회

        Returns:
            스크립트 ID 리스트
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT script_id FROM strategies") as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Error getting all script IDs: {e}")
            return []

    async def save_strategy(
        self,
        meta: Any,
        pine_code: str,
        analysis: Any
    ) -> bool:
        """
        전략 및 분석 결과 저장

        Args:
            meta: StrategyMeta 객체
            pine_code: Pine Script 소스 코드
            analysis: 분석 결과 객체

        Returns:
            성공 여부
        """
        try:
            # 분석 결과를 딕셔너리로 변환
            analysis_dict = None
            if analysis:
                if hasattr(analysis, 'model_dump'):
                    analysis_dict = analysis.model_dump()
                elif hasattr(analysis, 'dict'):
                    analysis_dict = analysis.dict()
                elif hasattr(analysis, '__dict__'):
                    analysis_dict = vars(analysis)

            strategy_data = {
                "script_id": meta.script_id,
                "title": meta.title,
                "author": meta.author,
                "likes": meta.likes,
                "views": getattr(meta, 'views', 0),
                "pine_code": pine_code,
                "pine_version": getattr(meta, 'pine_version', 5),
                "script_url": getattr(meta, 'script_url', ''),
                "description": getattr(meta, 'description', ''),
                "is_open_source": getattr(meta, 'is_open_source', False),
                "category": getattr(meta, 'category', 'strategy'),
                "analysis": analysis_dict,
            }

            return await self.upsert_strategy(strategy_data)

        except Exception as e:
            logger.error(f"Error saving strategy: {e}")
            return False

    async def update_converted_path(
        self,
        script_id: str,
        converted_path: str
    ) -> bool:
        """
        변환된 Python 파일 경로 업데이트

        Args:
            script_id: 스크립트 ID
            converted_path: 변환된 파일 경로

        Returns:
            성공 여부
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # analysis_json에 converted_path 추가
                async with db.execute(
                    "SELECT analysis_json FROM strategies WHERE script_id = ?",
                    (script_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                    analysis = {}
                    if row and row[0]:
                        try:
                            analysis = json.loads(row[0])
                        except Exception:
                            pass

                    analysis["converted_path"] = converted_path
                    analysis["converted_at"] = datetime.now().isoformat()

                await db.execute(
                    """
                    UPDATE strategies
                    SET analysis_json = ?, updated_at = ?
                    WHERE script_id = ?
                    """,
                    (json.dumps(analysis, ensure_ascii=False, default=json_serializer),
                     datetime.now().isoformat(),
                     script_id)
                )

                await db.commit()
                logger.debug(f"Updated converted path for: {script_id}")
                return True

        except Exception as e:
            logger.error(f"Error updating converted path for {script_id}: {e}")
            return False

    async def close(self):
        """데이터베이스 연결 정리 (placeholder)"""
        # aiosqlite는 각 작업마다 연결을 열고 닫으므로
        # 별도의 close 작업이 필요 없음
        pass
