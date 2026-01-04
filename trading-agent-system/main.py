"""
Trading Agent System - Main Entry Point

Pine Script 전략을 Python으로 변환하고 대규모 백테스트를 실행하는
AI 에이전트 시스템의 메인 진입점

Usage:
    python main.py                    # 대화형 모드
    python main.py --pine FILE        # Pine Script 파일 변환
    python main.py --backtest FILE    # 전략 백테스트
    python main.py --collect SYMBOL   # 데이터 수집
"""

import asyncio
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def check_api_key() -> bool:
    """Anthropic API 키 확인"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("  1. .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 추가")
        print("  2. 또는 export ANTHROPIC_API_KEY=sk-ant-...")
        return False
    return True


async def run_strategy_architect(pine_file: str) -> None:
    """Strategy Architect 에이전트 실행"""
    from claude_agent_sdk import query, ClaudeAgentOptions
    from src.agents.strategy_architect import StrategyArchitectAgent
    from src.tools.mcp_tools import create_trading_tools_server

    agent = StrategyArchitectAgent()
    pine_path = Path(pine_file)

    if not pine_path.exists():
        print(f"Error: 파일을 찾을 수 없습니다: {pine_file}")
        return

    pine_code = pine_path.read_text(encoding="utf-8")
    prompt = agent.create_conversion_prompt(pine_code)

    print(f"Pine Script 변환 시작: {pine_file}")
    print("-" * 50)

    # MCP 서버 및 옵션 설정
    trading_server = create_trading_tools_server()
    options = ClaudeAgentOptions(
        system_prompt=agent.definition.prompt,
        mcp_servers={"trading-tools": trading_server},
        allowed_tools=agent.definition.tools,
    )

    # 스트리밍 응답 처리
    async for message in query(prompt=prompt, options=options):
        print(message, end="", flush=True)
    print()  # 마지막 줄바꿈


async def run_backtest(strategy_file: str, symbol: str = "BTCUSDT") -> None:
    """백테스트 실행"""
    from src.backtest import BacktestEngine
    from src.data import BinanceDataCollector

    strategy_path = Path(strategy_file)
    if not strategy_path.exists():
        print(f"Error: 전략 파일을 찾을 수 없습니다: {strategy_file}")
        return

    print(f"데이터 수집 중: {symbol}")
    collector = BinanceDataCollector()

    try:
        data = await collector.fetch_klines(
            symbol=symbol,
            interval="1h",
            start_date="2024-01-01"
        )
    except Exception as e:
        print(f"데이터 수집 실패: {e}")
        print("저장된 데이터셋 확인 중...")

        try:
            data = collector.load_dataset(symbol, "1h")
        except FileNotFoundError:
            print("저장된 데이터셋이 없습니다. 먼저 데이터를 수집하세요.")
            return

    print(f"백테스트 실행 중: {strategy_file}")
    engine = BacktestEngine()

    try:
        metrics = engine.run_from_file(
            strategy_file=strategy_file,
            data=data,
            symbol=symbol,
            interval="1h"
        )

        print("\n" + "=" * 50)
        print("백테스트 결과")
        print("=" * 50)
        print(f"전략: {metrics.strategy_name}")
        print(f"심볼: {metrics.symbol}")
        print(f"기간: {metrics.start_date} ~ {metrics.end_date}")
        print("-" * 50)
        print(f"총 수익률: {metrics.total_return:.2f}%")
        print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"Sortino Ratio: {metrics.sortino_ratio:.2f}")
        print(f"Max Drawdown: {metrics.max_drawdown:.2f}%")
        print(f"Win Rate: {metrics.win_rate:.2f}%")
        print(f"Profit Factor: {metrics.profit_factor:.2f}")
        print(f"총 거래 수: {metrics.total_trades}")
        print("=" * 50)

        # 결과 저장
        result_path = engine.save_results(metrics)
        print(f"\n결과 저장됨: {result_path}")

    except Exception as e:
        print(f"백테스트 실패: {e}")


async def collect_data(
    symbol: str,
    interval: str = "1h",
    start_date: str = "2023-01-01"
) -> None:
    """Binance 데이터 수집"""
    from src.data import BinanceDataCollector

    print(f"데이터 수집 시작: {symbol} ({interval})")
    print(f"시작일: {start_date}")

    collector = BinanceDataCollector()

    try:
        info = await collector.download_dataset(
            symbol=symbol,
            interval=interval,
            start_date=start_date
        )

        print(f"\n수집 완료!")
        print(f"  심볼: {info.symbol}")
        print(f"  기간: {info.start_date} ~ {info.end_date}")
        print(f"  행 수: {info.rows:,}")
        print(f"  저장 위치: {info.file_path}")

    except Exception as e:
        print(f"데이터 수집 실패: {e}")


async def interactive_mode() -> None:
    """대화형 모드"""
    from claude_agent_sdk import query, ClaudeAgentOptions
    from src.agents.strategy_architect import STRATEGY_ARCHITECT_DEFINITION
    from src.agents.variation_generator import VARIATION_GENERATOR_DEFINITION
    from src.agents.backtest_runner import BACKTEST_RUNNER_DEFINITION
    from src.agents.result_analyzer import RESULT_ANALYZER_DEFINITION
    from src.tools.mcp_tools import create_trading_tools_server

    print("=" * 60)
    print("Trading Agent System - 대화형 모드")
    print("=" * 60)
    print()
    print("사용 가능한 명령:")
    print("  /convert <pine_file>  - Pine Script를 Python으로 변환")
    print("  /backtest <strategy>  - 전략 백테스트 실행")
    print("  /collect <symbol>     - Binance 데이터 수집")
    print("  /analyze <results>    - 백테스트 결과 분석")
    print("  /quit                 - 종료")
    print()
    print("또는 자연어로 질문하세요.")
    print("-" * 60)

    system_prompt = """당신은 트레이딩 전략 연구 전문가입니다.

## 역할
- Pine Script를 Python 백테스트 전략으로 변환
- 전략 변형 생성 및 최적화
- 대규모 백테스트 실행 및 결과 분석
- 데이터 기반 전략 선별

## 사용 가능한 에이전트
1. Strategy Architect: Pine → Python 변환
2. Variation Generator: 전략 변형 생성
3. Backtest Runner: 대규모 백테스트
4. Result Analyzer: 결과 분석 및 선별

## Moon Dev 기준
- 최소 25개 이상 데이터셋 테스트
- Sharpe Ratio > 1.5
- Profit Factor > 1.5
- Max Drawdown < 30%
- Win Rate > 40%

사용자의 요청에 맞게 적절한 에이전트를 활용하세요."""

    # MCP 서버 및 서브에이전트 등록
    trading_server = create_trading_tools_server()
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"trading-tools": trading_server},
        agents={
            "strategy-architect": STRATEGY_ARCHITECT_DEFINITION,
            "variation-generator": VARIATION_GENERATOR_DEFINITION,
            "backtest-runner": BACKTEST_RUNNER_DEFINITION,
            "result-analyzer": RESULT_ANALYZER_DEFINITION,
        },
        allowed_tools=["Task"],  # Task 도구로 서브에이전트 호출 가능
    )

    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/quit", "/exit", "quit", "exit"]:
                print("종료합니다.")
                break

            # 명령어 처리
            if user_input.startswith("/convert "):
                pine_file = user_input[9:].strip()
                await run_strategy_architect(pine_file)
                continue

            if user_input.startswith("/backtest "):
                strategy_file = user_input[10:].strip()
                await run_backtest(strategy_file)
                continue

            if user_input.startswith("/collect "):
                symbol = user_input[9:].strip().upper()
                await collect_data(symbol)
                continue

            # 일반 대화 - 스트리밍 응답
            print()
            async for message in query(prompt=user_input, options=options):
                print(message, end="", flush=True)
            print()

        except KeyboardInterrupt:
            print("\n종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Trading Agent System - AI 기반 트레이딩 전략 연구 시스템"
    )
    parser.add_argument(
        "--pine",
        type=str,
        help="Pine Script 파일을 Python으로 변환"
    )
    parser.add_argument(
        "--backtest",
        type=str,
        help="전략 파일 백테스트 실행"
    )
    parser.add_argument(
        "--collect",
        type=str,
        help="Binance에서 심볼 데이터 수집"
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1h",
        help="데이터 수집 타임프레임 (기본: 1h)"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2023-01-01",
        help="데이터 수집 시작일 (기본: 2023-01-01)"
    )

    args = parser.parse_args()

    # API 키 확인
    if not check_api_key():
        return

    # 명령어 실행
    if args.pine:
        asyncio.run(run_strategy_architect(args.pine))
    elif args.backtest:
        asyncio.run(run_backtest(args.backtest))
    elif args.collect:
        asyncio.run(collect_data(args.collect, args.interval, args.start))
    else:
        # 대화형 모드
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
