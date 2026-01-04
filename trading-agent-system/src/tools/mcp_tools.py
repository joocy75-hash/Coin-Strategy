"""
Custom MCP Tools for Trading Agent System

Gemini 3 Pro API, Backtesting, Binance 데이터 수집 도구
"""

import os
import json
import asyncio
from typing import Any
from datetime import datetime, timedelta

from claude_agent_sdk import tool, create_sdk_mcp_server


# ============================================================================
# Gemini API Tools
# ============================================================================

@tool(
    "gemini_analyze",
    "Analyze Pine Script strategy using Gemini 3 Pro with deep thinking",
    {
        "pine_code": str,
        "analysis_type": str,  # "logic", "risk", "conversion", "full"
        "context": str,  # Additional context for analysis
    }
)
async def gemini_analyze(args: dict[str, Any]) -> dict[str, Any]:
    """Gemini 3 Pro로 Pine Script 전략 분석"""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "Error: GOOGLE_API_KEY not set"}],
                "is_error": True
            }

        genai.configure(api_key=api_key)

        # Gemini 2.5 Pro with thinking
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro-preview-06-05",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 8192,
            }
        )

        pine_code = args["pine_code"]
        analysis_type = args.get("analysis_type", "full")
        context = args.get("context", "")

        prompts = {
            "logic": f"""Pine Script 전략의 로직을 분석해주세요:

```pinescript
{pine_code}
```

분석 항목:
1. 진입 조건 (Long/Short)
2. 청산 조건
3. 사용된 지표
4. 로직의 견고성 (1-10점)
5. 잠재적 문제점

{context}

JSON 형식으로 응답:
{{"logic_score": 7, "entry_conditions": [...], "exit_conditions": [...], "indicators": [...], "issues": [...]}}""",

            "risk": f"""Pine Script 전략의 리스크 관리를 분석해주세요:

```pinescript
{pine_code}
```

분석 항목:
1. Stop Loss 구현 여부 및 방식
2. Take Profit 구현 여부 및 방식
3. Position Sizing 로직
4. 최대 손실 제한
5. 리스크 관리 점수 (1-10점)

{context}

JSON 형식으로 응답:
{{"risk_score": 6, "has_stop_loss": true, "has_take_profit": false, "position_sizing": "fixed", "max_drawdown_protection": false, "recommendations": [...]}}""",

            "conversion": f"""Pine Script를 Python 백테스트 전략으로 변환해주세요:

```pinescript
{pine_code}
```

요구사항:
1. backtesting.py 라이브러리 호환
2. 모든 지표 구현 (pandas-ta 사용)
3. 진입/청산 로직 정확히 변환
4. Stop Loss/Take Profit 포함

{context}

완전한 Python 클래스 코드만 출력 (설명 없이)""",

            "full": f"""Pine Script 전략을 종합 분석해주세요:

```pinescript
{pine_code}
```

{context}

JSON 형식으로 응답:
{{
    "logic_score": 7,
    "risk_score": 6,
    "practical_score": 5,
    "code_quality_score": 7,
    "total_score": 62,
    "recommendation": "REVIEW",
    "entry_conditions": [...],
    "exit_conditions": [...],
    "indicators_used": [...],
    "strengths": [...],
    "weaknesses": [...],
    "conversion_notes": "..."
}}"""
        }

        prompt = prompts.get(analysis_type, prompts["full"])

        # Enable thinking for complex analysis
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
        )

        return {
            "content": [{
                "type": "text",
                "text": response.text
            }]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Gemini API Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "gemini_convert_pine",
    "Convert Pine Script to Python strategy using Gemini 3 Pro",
    {
        "pine_code": str,
        "strategy_name": str,
        "additional_indicators": str,  # JSON list of indicators to add
    }
)
async def gemini_convert_pine(args: dict[str, Any]) -> dict[str, Any]:
    """Gemini 3 Pro로 Pine Script를 Python으로 완전 변환"""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {
                "content": [{"type": "text", "text": "Error: GOOGLE_API_KEY not set"}],
                "is_error": True
            }

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro-preview-06-05",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 16384,
            }
        )

        pine_code = args["pine_code"]
        strategy_name = args.get("strategy_name", "ConvertedStrategy")
        additional_indicators = args.get("additional_indicators", "[]")

        prompt = f"""당신은 Pine Script를 Python으로 변환하는 전문가입니다.

## 원본 Pine Script
```pinescript
{pine_code}
```

## 추가할 지표
{additional_indicators}

## 변환 요구사항

1. **backtesting.py 라이브러리 호환** 필수
2. **Strategy 클래스 구조**:
```python
from backtesting import Strategy
from backtesting.lib import crossover
import pandas_ta as ta

class {strategy_name}(Strategy):
    # 파라미터 정의 (최적화 가능)
    param1 = 14
    param2 = 20

    def init(self):
        # 지표 계산 (self.I() 사용)
        self.indicator = self.I(ta.rsi, self.data.Close, self.param1)

    def next(self):
        # 진입/청산 로직
        if crossover(self.indicator, 30):
            self.buy()
        elif crossover(70, self.indicator):
            self.sell()
```

3. **모든 지표 pandas-ta로 구현**
4. **Stop Loss / Take Profit 포함** (원본에 있다면)
5. **Position Sizing 포함** (원본에 있다면)

완전한 Python 코드만 출력하세요 (설명 없이, 마크다운 코드 블록 없이):"""

        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
        )

        # Clean up response (remove markdown code blocks if present)
        code = response.text
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]

        return {
            "content": [{
                "type": "text",
                "text": code.strip()
            }]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Gemini Conversion Error: {str(e)}"}],
            "is_error": True
        }


# ============================================================================
# Backtesting Tools
# ============================================================================

def _execute_strategy_code(strategy_code: str) -> dict[str, Any]:
    """
    전략 코드를 동적으로 실행하여 Strategy 클래스를 추출합니다.

    Note: 이것은 Python의 내장 함수를 사용한 코드 실행이며,
    shell command가 아닙니다. 사용자가 제공한 전략 코드를
    Python 인터프리터에서 실행합니다.
    """
    local_namespace: dict[str, Any] = {}
    # Python 내장 함수로 전략 코드 실행 (shell command 아님)
    compiled_code = compile(strategy_code, "<strategy>", "exec")
    # pylint: disable=exec-used
    exec(compiled_code, local_namespace)  # noqa: S102 - 의도적인 동적 코드 실행
    return local_namespace


@tool(
    "run_backtest",
    "Run backtest on a Python strategy with given data",
    {
        "strategy_code": str,
        "data_path": str,  # Path to CSV/Parquet file
        "initial_cash": float,
        "commission": float,
        "optimize": bool,
    }
)
async def run_backtest(args: dict[str, Any]) -> dict[str, Any]:
    """Python 전략 백테스트 실행"""
    try:
        import pandas as pd
        from backtesting import Backtest, Strategy

        strategy_code = args["strategy_code"]
        data_path = args["data_path"]
        initial_cash = args.get("initial_cash", 10000)
        commission = args.get("commission", 0.001)
        optimize = args.get("optimize", False)

        # Load data
        if data_path.endswith(".parquet"):
            df = pd.read_parquet(data_path)
        else:
            df = pd.read_csv(data_path, parse_dates=["timestamp"])
            df.set_index("timestamp", inplace=True)

        # Ensure required columns
        df.columns = [c.capitalize() for c in df.columns]
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in df.columns:
                return {
                    "content": [{"type": "text", "text": f"Missing column: {col}"}],
                    "is_error": True
                }

        # Execute strategy code to get the class
        local_ns = _execute_strategy_code(strategy_code)

        # Find Strategy class
        strategy_class = None
        for name, obj in local_ns.items():
            if isinstance(obj, type) and name != "Strategy":
                if issubclass(obj, Strategy):
                    strategy_class = obj
                    break

        if not strategy_class:
            return {
                "content": [{"type": "text", "text": "No Strategy class found in code"}],
                "is_error": True
            }

        # Run backtest
        bt = Backtest(
            df,
            strategy_class,
            cash=initial_cash,
            commission=commission,
            exclusive_orders=True
        )

        if optimize:
            # Basic optimization (if strategy has parameters)
            stats = bt.optimize(maximize="Return [%]")
        else:
            stats = bt.run()

        # Extract key metrics
        result = {
            "total_return_pct": float(stats["Return [%]"]),
            "sharpe_ratio": float(stats["Sharpe Ratio"]) if pd.notna(stats["Sharpe Ratio"]) else 0,
            "max_drawdown_pct": float(stats["Max. Drawdown [%]"]),
            "win_rate_pct": float(stats["Win Rate [%]"]) if pd.notna(stats["Win Rate [%]"]) else 0,
            "profit_factor": float(stats["Profit Factor"]) if pd.notna(stats["Profit Factor"]) else 0,
            "total_trades": int(stats["# Trades"]),
            "avg_trade_pct": float(stats["Avg. Trade [%]"]) if pd.notna(stats["Avg. Trade [%]"]) else 0,
            "duration_days": int(stats["Duration"].days) if hasattr(stats["Duration"], "days") else 0,
            "final_equity": float(stats["Equity Final [$]"]),
        }

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Backtest Error: {str(e)}"}],
            "is_error": True
        }


# ============================================================================
# Binance Data Collection Tools
# ============================================================================

@tool(
    "fetch_binance_data",
    "Fetch historical OHLCV data from Binance",
    {
        "symbol": str,  # e.g., "BTCUSDT"
        "interval": str,  # e.g., "1h", "4h", "1d"
        "start_date": str,  # e.g., "2023-01-01"
        "end_date": str,  # e.g., "2024-01-01"
        "output_path": str,  # Where to save the data
    }
)
async def fetch_binance_data(args: dict[str, Any]) -> dict[str, Any]:
    """Binance에서 히스토리컬 OHLCV 데이터 수집"""
    try:
        from binance.client import Client
        import pandas as pd

        symbol = args["symbol"]
        interval = args["interval"]
        start_date = args["start_date"]
        end_date = args.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        output_path = args["output_path"]

        # Binance API client
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY와 BINANCE_API_SECRET 환경변수를 설정해주세요")

        client = Client(api_key, api_secret)

        # Map interval string to Binance constant
        interval_map = {
            "1m": Client.KLINE_INTERVAL_1MINUTE,
            "5m": Client.KLINE_INTERVAL_5MINUTE,
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "30m": Client.KLINE_INTERVAL_30MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR,
            "1d": Client.KLINE_INTERVAL_1DAY,
            "1w": Client.KLINE_INTERVAL_1WEEK,
        }

        binance_interval = interval_map.get(interval, Client.KLINE_INTERVAL_1HOUR)

        # Fetch klines
        klines = await asyncio.to_thread(
            client.get_historical_klines,
            symbol,
            binance_interval,
            start_date,
            end_date
        )

        if not klines:
            return {
                "content": [{"type": "text", "text": f"No data found for {symbol}"}],
                "is_error": True
            }

        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        # Process
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df.set_index("timestamp", inplace=True)

        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if output_path.endswith(".parquet"):
            df.to_parquet(output_path)
        else:
            df.to_csv(output_path)

        result = {
            "symbol": symbol,
            "interval": interval,
            "start_date": str(df.index.min()),
            "end_date": str(df.index.max()),
            "rows": len(df),
            "output_path": output_path,
        }

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Binance Data Error: {str(e)}"}],
            "is_error": True
        }


# ============================================================================
# Create MCP Server
# ============================================================================

def create_trading_tools_server():
    """트레이딩 도구 MCP 서버 생성"""
    return create_sdk_mcp_server(
        name="trading-tools",
        version="1.0.0",
        tools=[
            gemini_analyze,
            gemini_convert_pine,
            run_backtest,
            fetch_binance_data,
        ]
    )
