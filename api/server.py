#!/usr/bin/env python3
"""
Strategy Research Lab REST API

TradingView 전략 분석 결과를 제공하는 FastAPI 서버
"""

import json
import sqlite3
import logging
import traceback
from pathlib import Path
from typing import Optional, List, Any
from datetime import datetime

import os
import sys
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import re

# ============================================================
# Logging Setup
# ============================================================

# 로깅 설정
LOG_DIR = Path(os.getenv("LOGS_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 로거 설정
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# 콘솔 핸들러
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 파일 핸들러
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(
    LOG_DIR / "api.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)

# JSON 로그 핸들러 (구조화된 로깅)
json_handler = RotatingFileHandler(
    LOG_DIR / "api.json.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
json_handler.setLevel(logging.INFO)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


json_handler.setFormatter(JSONFormatter())
logger.addHandler(json_handler)


# ============================================================
# Input Validation & Sanitization
# ============================================================

def sanitize_input(value: str, max_length: int = 200) -> str:
    """입력값 sanitize - SQL Injection 및 XSS 방지"""
    if not value:
        return ""
    # 길이 제한
    value = value[:max_length]
    # 위험한 문자 제거 (SQL injection, XSS 방지)
    value = re.sub(r'[<>"\';\\]', '', value)
    return value.strip()


def validate_script_id(script_id: str) -> str:
    """script_id 검증 - 영숫자와 하이픈, 언더스코어만 허용"""
    if not script_id:
        raise HTTPException(status_code=400, detail="script_id is required")
    # 영숫자, 하이픈, 언더스코어만 허용 (최대 100자)
    if not re.match(r'^[a-zA-Z0-9_-]{1,100}$', script_id):
        raise HTTPException(status_code=400, detail="Invalid script_id format")
    return script_id


# ============================================================
# Pydantic Models
# ============================================================


class StatsResponse(BaseModel):
    """통계 정보 응답"""

    total_strategies: int = Field(..., description="총 전략 수")
    analyzed_count: int = Field(..., description="분석 완료 수")
    passed_count: int = Field(..., description="권장 전략 수 (A, B 등급)")
    avg_score: float = Field(..., description="평균 점수")


class StrategyItem(BaseModel):
    """전략 목록 아이템"""

    script_id: str
    title: str
    author: str
    likes: int
    total_score: Optional[float] = None
    grade: Optional[str] = None
    repainting_score: Optional[float] = None
    overfitting_score: Optional[float] = None


class StrategyDetail(BaseModel):
    """전략 상세 정보"""

    script_id: str
    title: str
    author: str
    likes: int
    total_score: Optional[float] = None
    grade: Optional[str] = None
    repainting_score: Optional[float] = None
    overfitting_score: Optional[float] = None
    pine_code: Optional[str] = None
    pine_version: Optional[int] = None
    performance: Optional[dict] = None
    analysis: Optional[dict] = None
    created_at: Optional[str] = None


# ============================================================
# FastAPI App
# ============================================================

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Strategy Research Lab API",
    description="TradingView 전략 분석 결과 API - Hetzner 자동 배포",
    version="1.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Rate Limiter 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================
# Global Error Handlers
# ============================================================

class ErrorResponse(BaseModel):
    """표준 에러 응답"""
    success: bool = False
    error: str
    error_code: str
    timestamp: str
    request_id: Optional[str] = None


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} | "
        f"Path: {request.url.path} | Request ID: {request_id}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러"""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"Unhandled exception: {str(exc)} | "
        f"Path: {request.url.path} | Request ID: {request_id}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }
    )


# ============================================================
# Request Logging Middleware
# ============================================================

import uuid
import time


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청 로깅 미들웨어"""
    # 요청 ID 생성
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    # 시작 시간
    start_time = time.time()
    
    # 요청 로깅
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Client: {request.client.host if request.client else 'unknown'} | "
        f"Request ID: {request_id}"
    )
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 응답 로깅
    logger.info(
        f"Response: {response.status_code} | "
        f"Time: {process_time:.3f}s | "
        f"Request ID: {request_id}"
    )
    
    # 응답 헤더에 요청 ID 추가
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    
    return response

# CORS 설정 - 보안 강화
# 프로덕션에서는 특정 도메인만 허용
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "http://141.164.55.245",
    "http://141.164.55.245:8081",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # 쿠키/인증 정보 전송 비활성화
    allow_methods=["GET", "POST", "OPTIONS"],  # 필요한 메서드만 허용
    allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만 허용
)

# 경로 설정 (Docker 컨테이너 환경 기준)
BASE_DIR = Path(os.getenv("APP_BASE_DIR", "/app"))
DB_PATH = BASE_DIR / "data" / "strategies.db"
DATA_DIR = BASE_DIR / "data"


def init_db():
    """데이터베이스 초기화 (파일이 없는 경우)"""
    if not DB_PATH.exists():
        print(f"Initializing database at {DB_PATH}")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                script_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                pine_code TEXT,
                pine_version INTEGER DEFAULT 5,
                performance_json TEXT,
                analysis_json TEXT,
                script_url TEXT,
                description TEXT,
                is_open_source BOOLEAN DEFAULT 0,
                category TEXT DEFAULT 'strategy',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_likes ON strategies(likes DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_author ON strategies(author)")
        conn.commit()
        conn.close()


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    init_db()


def get_db():
    """데이터베이스 연결"""
    if not DB_PATH.exists():
        init_db()

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection error: {str(e)}"
        )


def parse_json_field(value: Any) -> Optional[dict]:
    """JSON 필드 파싱"""
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def extract_analysis_data(analysis_json: str) -> dict:
    """analysis_json에서 점수 및 등급 추출"""
    analysis = parse_json_field(analysis_json)
    if not analysis:
        return {
            "total_score": None,
            "grade": None,
            "repainting_score": None,
            "overfitting_score": None,
        }

    return {
        "total_score": analysis.get("total_score"),
        "grade": analysis.get("grade"),
        "repainting_score": analysis.get("repainting_score"),
        "overfitting_score": analysis.get("overfitting_score"),
    }


# ============================================================
# API Endpoints
# ============================================================


@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_exists": DB_PATH.exists(),
    }


@app.get("/api/stats", response_model=StatsResponse)
@limiter.limit("30/minute")
async def get_stats(request: Request):
    """통계 정보 조회"""
    try:
        conn = get_db()
        cur = conn.cursor()

        # 총 전략 수
        cur.execute("SELECT COUNT(*) FROM strategies")
        total = cur.fetchone()[0]

        # analysis_json이 있는 항목 수 (분석 완료)
        cur.execute(
            "SELECT COUNT(*) FROM strategies WHERE analysis_json IS NOT NULL AND analysis_json != ''"
        )
        analyzed = cur.fetchone()[0]

        # 모든 분석된 전략의 analysis_json 가져와서 통계 계산
        cur.execute(
            "SELECT analysis_json FROM strategies WHERE analysis_json IS NOT NULL AND analysis_json != ''"
        )
        rows = cur.fetchall()
        conn.close()

        passed = 0
        total_score_sum = 0
        score_count = 0

        for row in rows:
            data = extract_analysis_data(row[0])
            grade = data.get("grade")
            score = data.get("total_score")

            if grade in ("A", "B"):
                passed += 1
            if score is not None:
                total_score_sum += score
                score_count += 1

        avg_score = total_score_sum / score_count if score_count > 0 else 0

        return StatsResponse(
            total_strategies=total,
            analyzed_count=analyzed,
            passed_count=passed,
            avg_score=round(avg_score, 1),
        )

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/strategies", response_model=List[StrategyItem])
@limiter.limit("30/minute")
async def get_strategies(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="조회 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    min_score: float = Query(0, ge=0, le=100, description="최소 점수"),
    grade: Optional[str] = Query(None, description="등급 필터 (A, B, C, D, F)"),
    search: Optional[str] = Query(None, description="검색어 (제목, 작성자)"),
    sort_by: str = Query("likes", description="정렬 기준 (likes, title)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
):
    """전략 목록 조회"""
    try:
        conn = get_db()
        cur = conn.cursor()

        # 기본 쿼리 - analysis_json이 있는 전략만
        query = """
            SELECT script_id, title, author, likes, analysis_json
            FROM strategies
            WHERE analysis_json IS NOT NULL AND analysis_json != ''
        """
        params: List = []

        # 검색 (입력값 sanitize 적용)
        if search:
            sanitized_search = sanitize_input(search, max_length=100)
            if sanitized_search:
                query += " AND (title LIKE ? OR author LIKE ?)"
                params.extend([f"%{sanitized_search}%", f"%{sanitized_search}%"])

        # 정렬 (DB 컬럼 기준)
        valid_columns = ["likes", "title", "created_at"]
        if sort_by not in valid_columns:
            sort_by = "likes"
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {order}"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        # 결과 가공 (JSON 파싱 + 필터링)
        results = []
        for row in rows:
            data = extract_analysis_data(row["analysis_json"])
            total_score = data.get("total_score") or 0
            strategy_grade = data.get("grade")

            # 필터 적용
            if total_score < min_score:
                continue
            if grade and strategy_grade != grade:
                continue

            results.append(
                StrategyItem(
                    script_id=row["script_id"],
                    title=row["title"] or "",
                    author=row["author"] or "",
                    likes=row["likes"] or 0,
                    total_score=data.get("total_score"),
                    grade=strategy_grade,
                    repainting_score=data.get("repainting_score"),
                    overfitting_score=data.get("overfitting_score"),
                )
            )

        # 점수 기준 정렬 (클라이언트 요청 시)
        if sort_by == "score" or sort_by == "total_score":
            results.sort(
                key=lambda x: x.total_score or 0, reverse=(sort_order.lower() == "desc")
            )

        # 페이징
        return results[offset : offset + limit]

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/strategy/{script_id}", response_model=StrategyDetail)
@limiter.limit("30/minute")
async def get_strategy_detail(request: Request, script_id: str):
    """전략 상세 정보 조회"""
    # script_id 검증
    script_id = validate_script_id(script_id)
    
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM strategies WHERE script_id = ?", [script_id])
        row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # JSON 필드 파싱
        performance = parse_json_field(row["performance_json"])
        analysis = parse_json_field(row["analysis_json"])
        analysis_data = extract_analysis_data(row["analysis_json"])

        return StrategyDetail(
            script_id=row["script_id"],
            title=row["title"] or "",
            author=row["author"] or "",
            likes=row["likes"] or 0,
            total_score=analysis_data.get("total_score"),
            grade=analysis_data.get("grade"),
            repainting_score=analysis_data.get("repainting_score"),
            overfitting_score=analysis_data.get("overfitting_score"),
            pine_code=row["pine_code"],
            pine_version=row["pine_version"],
            performance=performance,
            analysis=analysis,
            created_at=row["created_at"],
        )

    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================
# Static Files & Main Page
# ============================================================


@app.get("/")
async def serve_index():
    """메인 페이지 (초보자 리포트)"""
    html_file = DATA_DIR / "beginner_report.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Welcome to Strategy Research Lab API", "docs": "/api/docs"}


@app.get("/live")
async def serve_live_dashboard():
    """실전매매 모니터링 대시보드"""
    # Docker 환경 (/app/data)
    html_file = DATA_DIR / "live_trading_dashboard.html"
    if html_file.exists():
        return FileResponse(html_file)
    
    # templates 폴더
    templates_file = BASE_DIR / "templates" / "live_trading_dashboard.html"
    if templates_file.exists():
        return FileResponse(templates_file)
    
    raise HTTPException(status_code=404, detail="Live trading dashboard not found")


@app.get("/report.html")
async def serve_report():
    """일반 리포트"""
    html_file = DATA_DIR / "report.html"
    if html_file.exists():
        return FileResponse(html_file)
    raise HTTPException(status_code=404, detail="Report not found")


@app.get("/backtest/{strategy_name}")
async def serve_backtest_chart(strategy_name: str):
    """백테스트 결과 차트 (Bokeh HTML)"""
    # 프로젝트 루트에서 찾기
    chart_file = BASE_DIR.parent / f"{strategy_name}_backtest_result.html"
    if chart_file.exists():
        return FileResponse(chart_file)
    
    # data 디렉토리에서 찾기
    chart_file = DATA_DIR / f"{strategy_name}_backtest_result.html"
    if chart_file.exists():
        return FileResponse(chart_file)
    
    raise HTTPException(status_code=404, detail=f"Backtest chart for '{strategy_name}' not found")


@app.get("/api/backtest-charts")
async def list_backtest_charts():
    """사용 가능한 백테스트 차트 목록"""
    charts = []
    
    # 프로젝트 루트에서 찾기
    root_dir = BASE_DIR.parent
    for f in root_dir.glob("*_backtest_result.html"):
        strategy_name = f.stem.replace("_backtest_result", "")
        charts.append({
            "strategy": strategy_name,
            "url": f"/backtest/{strategy_name}",
            "filename": f.name
        })
    
    # data 디렉토리에서 찾기
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*_backtest_result.html"):
            strategy_name = f.stem.replace("_backtest_result", "")
            if not any(c["strategy"] == strategy_name for c in charts):
                charts.append({
                    "strategy": strategy_name,
                    "url": f"/backtest/{strategy_name}",
                    "filename": f.name
                })
    
    return {"charts": charts, "count": len(charts)}


# ============================================================
# Backtest Endpoints
# ============================================================


class BacktestRequest(BaseModel):
    """백테스트 요청"""

    script_id: str = Field(..., description="전략 ID")
    symbol: str = Field("BTC/USDT", description="거래쌍")
    timeframe: str = Field("1h", description="시간프레임")
    start_date: str = Field("2024-01-01", description="시작일")
    end_date: str = Field("2024-12-01", description="종료일")
    initial_capital: float = Field(10000.0, description="초기 자본")


class BacktestResponse(BaseModel):
    """백테스트 응답"""

    success: bool
    script_id: str
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    backtest: Optional[dict] = None
    error: Optional[str] = None
    tested_at: Optional[str] = None


@app.post("/api/backtest", response_model=BacktestResponse)
@limiter.limit("10/minute")  # 백테스트는 리소스 소모가 크므로 더 제한
async def run_backtest(request: Request, backtest_request: BacktestRequest):
    """
    전략 백테스트 실행

    Pine Script 전략을 Python으로 변환하고 과거 데이터로 백테스트합니다.
    """
    import sys

    sys.path.insert(0, str(BASE_DIR / "src"))

    try:
        from backtester import StrategyTester

        tester = StrategyTester(str(DB_PATH))

        result = await tester.test_strategy(
            script_id=backtest_request.script_id,
            symbol=backtest_request.symbol,
            timeframe=backtest_request.timeframe,
            start_date=backtest_request.start_date,
            end_date=backtest_request.end_date,
            initial_capital=backtest_request.initial_capital,
        )

        if result.get("error"):
            return BacktestResponse(
                success=False, script_id=backtest_request.script_id, error=result["error"]
            )

        return BacktestResponse(
            success=True,
            script_id=backtest_request.script_id,
            symbol=backtest_request.symbol,
            timeframe=backtest_request.timeframe,
            backtest=result.get("backtest"),
            tested_at=result.get("tested_at"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")


@app.post("/api/backtest/all")
@limiter.limit("5/minute")  # 전체 백테스트는 매우 제한적으로
async def run_all_backtests(
    request: Request,
    limit: int = Query(5, ge=1, le=50, description="테스트할 전략 수"),
    symbol: str = Query("BTC/USDT", description="거래쌍"),
    timeframe: str = Query("1h", description="시간프레임"),
    start_date: str = Query("2024-01-01", description="시작일"),
    end_date: str = Query("2024-06-01", description="종료일"),
):
    """
    모든 전략 백테스트 (상위 N개)

    Pine Script 코드가 있는 전략을 좋아요 순으로 정렬하여 백테스트합니다.
    """
    import sys

    sys.path.insert(0, str(BASE_DIR / "src"))

    try:
        from backtester import StrategyTester

        tester = StrategyTester(str(DB_PATH))

        results = await tester.test_all_strategies(
            limit=limit,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        # 요약 통계
        successful = [r for r in results if r.get("backtest", {}).get("success")]
        total_return_sum = (
            sum(r["backtest"]["total_return"] for r in successful) if successful else 0
        )
        avg_return = total_return_sum / len(successful) if successful else 0

        return {
            "total_tested": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "avg_return": round(avg_return, 2),
            "results": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")


@app.get("/api/strategy/{script_id}/backtest")
@limiter.limit("30/minute")
async def get_backtest_result(request: Request, script_id: str):
    """전략의 저장된 백테스트 결과 조회"""
    # script_id 검증
    script_id = validate_script_id(script_id)
    
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT analysis_json FROM strategies WHERE script_id = ?", [script_id]
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Strategy not found")

        analysis = parse_json_field(row[0])

        if not analysis or "backtest_result" not in analysis:
            return {
                "script_id": script_id,
                "has_backtest": False,
                "message": "No backtest result available. Run /api/backtest first.",
            }

        return {
            "script_id": script_id,
            "has_backtest": True,
            "backtest_result": analysis["backtest_result"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================
# Live Trading Endpoints (긴급 정지, 상태 조회)
# ============================================================

# API 인증 키 (환경변수에서 로드)
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")


def verify_api_key(api_key: str = Query(None, alias="api_key")) -> bool:
    """API 키 검증"""
    if not API_SECRET_KEY:
        # API_SECRET_KEY가 설정되지 않으면 인증 비활성화 (개발용)
        return True
    if not api_key or api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.get("/api/live/status")
@limiter.limit("30/minute")
async def get_live_trading_status(request: Request):
    """실전매매 상태 조회"""
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        
        from src.trading.live_safeguards import get_safeguards
        
        safeguards = get_safeguards()
        status = safeguards.get_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "status": status,
        }
        
    except ImportError:
        return {
            "success": False,
            "error": "Live trading safeguards not available",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


class EmergencyStopRequest(BaseModel):
    """긴급 정지 요청"""
    reason: str = Field("Manual emergency stop", description="정지 사유")
    api_key: str = Field(..., description="API 인증 키")


@app.post("/api/emergency-stop")
@limiter.limit("10/minute")
async def emergency_stop(request: Request, stop_request: EmergencyStopRequest):
    """
    긴급 정지 API
    
    실전매매 봇을 즉시 정지시킵니다.
    인증 필수: api_key 파라미터 필요
    """
    # API 키 검증
    if API_SECRET_KEY and stop_request.api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        
        from src.trading.live_safeguards import get_safeguards
        
        safeguards = get_safeguards()
        safeguards.emergency_stop(stop_request.reason)
        
        return {
            "success": True,
            "message": f"Emergency stop activated: {stop_request.reason}",
            "timestamp": datetime.now().isoformat(),
            "status": safeguards.get_status(),
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Live trading safeguards not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


class ResetEmergencyRequest(BaseModel):
    """긴급 정지 해제 요청"""
    api_key: str = Field(..., description="API 인증 키")


@app.post("/api/emergency-stop/reset")
@limiter.limit("10/minute")
async def reset_emergency_stop(request: Request, reset_request: ResetEmergencyRequest):
    """
    긴급 정지 해제 API
    
    긴급 정지 상태를 해제합니다.
    인증 필수: api_key 파라미터 필요
    """
    # API 키 검증
    if API_SECRET_KEY and reset_request.api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        import sys
        sys.path.insert(0, str(BASE_DIR))
        
        from src.trading.live_safeguards import get_safeguards
        
        safeguards = get_safeguards()
        safeguards.reset_emergency_stop()
        
        return {
            "success": True,
            "message": "Emergency stop reset. Call start() to resume trading.",
            "timestamp": datetime.now().isoformat(),
            "status": safeguards.get_status(),
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Live trading safeguards not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# 정적 파일 마운트 (맨 마지막에 배치)
if DATA_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")


# ============================================================
# Trade Log Endpoints (6.4)
# ============================================================

@app.get("/api/trades/recent")
@limiter.limit("30/minute")
async def get_recent_trades(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="조회 개수"),
):
    """최근 거래 기록 조회"""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.logging.trade_logger import get_trade_logger
        
        trade_logger = get_trade_logger()
        trades = trade_logger.get_recent_trades(limit)
        
        return {
            "success": True,
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.now().isoformat(),
        }
        
    except ImportError:
        logger.warning("Trade logger not available")
        return {
            "success": False,
            "error": "Trade logger not available",
            "trades": [],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/trades/statistics")
@limiter.limit("30/minute")
async def get_trade_statistics(request: Request):
    """거래 통계 조회"""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.logging.trade_logger import get_trade_logger
        
        trade_logger = get_trade_logger()
        stats = trade_logger.get_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat(),
        }
        
    except ImportError:
        logger.warning("Trade logger not available")
        return {
            "success": False,
            "error": "Trade logger not available",
            "statistics": {},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


class TradeExportRequest(BaseModel):
    """거래 내보내기 요청"""
    start_date: Optional[str] = Field(None, description="시작일 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="종료일 (YYYY-MM-DD)")
    api_key: str = Field(..., description="API 인증 키")


@app.post("/api/trades/export")
@limiter.limit("5/minute")
async def export_trades(request: Request, export_request: TradeExportRequest):
    """
    거래 기록 CSV 내보내기 (세금 신고용)
    
    인증 필수: api_key 파라미터 필요
    """
    # API 키 검증
    if API_SECRET_KEY and export_request.api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.logging.trade_logger import get_trade_logger
        
        trade_logger = get_trade_logger()
        export_path = trade_logger.export_csv(
            start_date=export_request.start_date,
            end_date=export_request.end_date,
        )
        
        logger.info(f"Trades exported to: {export_path}")
        
        return FileResponse(
            export_path,
            media_type="text/csv",
            filename=Path(export_path).name,
        )
        
    except ImportError:
        logger.warning("Trade logger not available")
        raise HTTPException(status_code=500, detail="Trade logger not available")
    except Exception as e:
        logger.error(f"Error exporting trades: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
