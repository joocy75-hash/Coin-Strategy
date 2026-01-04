"""
Binance 데이터셋 수집 스크립트

25개 이상의 데이터셋을 수집하여 백테스트 인프라 완성
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from data.binance_collector import BinanceDataCollector


async def main():
    """메인 실행 함수"""

    print("=" * 80)
    print("🚀 Binance 데이터셋 수집 시작")
    print("=" * 80)
    print()

    # 데이터 수집기 초기화 (API 키 불필요 - 공개 데이터)
    collector = BinanceDataCollector(
        data_dir=str(project_root / "data" / "datasets")
    )

    # 수집할 심볼 목록 (25개 이상)
    symbols = [
        # Major 암호화폐
        "BTCUSDT", "ETHUSDT", "BNBUSDT",

        # Large Cap
        "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",

        # Mid Cap
        "DOTUSDT", "MATICUSDT", "AVAXUSDT", "LINKUSDT",
        "ATOMUSDT", "UNIUSDT", "LTCUSDT", "NEARUSDT",

        # DeFi & Layer 2
        "ARBUSDT", "OPUSDT", "APTUSDT", "SUIUSDT",

        # Meme & Others
        "SHIBUSDT", "PEPEUSDT", "WLDUSDT", "FETUSDT",
        "INJUSDT", "THETAUSDT"
    ]

    # 수집할 타임프레임 (다양성 확보)
    intervals = [
        "1h",   # 단기 (1시간봉)
        "4h",   # 중기 (4시간봉)
        "1d",   # 장기 (1일봉)
    ]

    # 수집 기간
    start_date = "2023-01-01"  # 2023년부터 (충분한 데이터)

    print(f"📊 수집 설정:")
    print(f"  - 심볼: {len(symbols)}개")
    print(f"  - 타임프레임: {intervals}")
    print(f"  - 기간: {start_date} ~ 현재")
    print(f"  - 예상 데이터셋 수: {len(symbols) * len(intervals)}개")
    print()

    # 데이터셋 수집 시작
    results = await collector.download_all_datasets(
        symbols=symbols,
        intervals=intervals,
        start_date=start_date,
        end_date=None  # 현재까지
    )

    print()
    print("=" * 80)
    print("✅ 데이터 수집 완료!")
    print("=" * 80)
    print()

    # 결과 요약
    print(f"📈 수집 결과:")
    print(f"  - 성공: {len(results)}개 데이터셋")
    print(f"  - 실패: {len(symbols) * len(intervals) - len(results)}개")
    print()

    # 저장된 데이터셋 목록 확인
    datasets = collector.list_datasets()
    print(f"💾 저장된 데이터셋: {len(datasets)}개")
    print()

    # 심볼별 통계
    symbol_stats = {}
    for ds in datasets:
        symbol = ds["symbol"]
        if symbol not in symbol_stats:
            symbol_stats[symbol] = []
        symbol_stats[symbol].append(ds["interval"])

    print("📋 심볼별 데이터셋:")
    for symbol, intervals_collected in sorted(symbol_stats.items()):
        print(f"  {symbol:12s}: {', '.join(sorted(intervals_collected))}")

    print()
    print(f"✨ 데이터 저장 위치: {collector.data_dir}")
    print()

    # 샘플 데이터 확인
    if results:
        sample = results[0]
        print(f"📊 샘플 데이터 ({sample.symbol} {sample.interval}):")
        print(f"  - 기간: {sample.start_date} ~ {sample.end_date}")
        print(f"  - 행 수: {sample.rows:,} rows")
        print(f"  - 파일: {sample.file_path}")

        # 실제 데이터 로드 테스트
        df = collector.load_dataset(sample.symbol, sample.interval)
        print(f"\n  데이터 미리보기:")
        print(df.head(3).to_string())
        print(f"\n  컬럼: {list(df.columns)}")
        print(f"  인덱스: {df.index.name}")

    print()
    print("=" * 80)
    print("🎉 백테스트 데이터 인프라 준비 완료!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
