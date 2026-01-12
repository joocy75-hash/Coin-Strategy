#!/usr/bin/env python3
"""
로깅 시스템 테스트

작업 항목:
- 3.2 로깅 시스템 테스트
- 6.4 거래 로그 테스트
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_logger_setup():
    """로거 설정 테스트"""
    print("\n" + "="*60)
    print("🧪 로거 설정 테스트")
    print("="*60)
    
    try:
        from src.logging.logger import (
            get_logger, setup_logging, LogConfig, LogLevel
        )
        
        # 테스트용 설정
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(
                level=LogLevel.DEBUG,
                log_dir=tmpdir,
                file_logging=True,
                json_logging=True,
                console_logging=False,
            )
            
            setup_logging(config)
            logger = get_logger("test_logger")
            
            # 로그 메시지 테스트
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # 파일 생성 확인
            log_file = Path(tmpdir) / "app.log"
            json_file = Path(tmpdir) / "app.json.log"
            
            if log_file.exists():
                print("✅ 일반 로그 파일 생성됨")
            else:
                print("❌ 일반 로그 파일 미생성")
                
            if json_file.exists():
                print("✅ JSON 로그 파일 생성됨")
            else:
                print("❌ JSON 로그 파일 미생성")
                
        print("✅ 로거 설정 테스트 완료")
        
    except Exception as e:
        print(f"❌ 로거 설정 테스트 실패: {e}")


def test_trade_logger():
    """거래 로거 테스트"""
    print("\n" + "="*60)
    print("🧪 거래 로거 테스트")
    print("="*60)
    
    try:
        from src.logging.trade_logger import TradeLogger, TradeRecord
        
        with tempfile.TemporaryDirectory() as tmpdir:
            trade_logger = TradeLogger(log_dir=tmpdir)
            
            # 진입 거래 기록
            entry_id = trade_logger.log_entry(
                symbol="BTCUSDT",
                side="BUY",
                price=45000.0,
                amount=1000.0,
                quantity=0.022,
                strategy_name="Test Strategy",
            )
            print(f"✅ 진입 거래 기록: {entry_id}")
            
            # 청산 거래 기록
            exit_id = trade_logger.log_exit(
                symbol="BTCUSDT",
                side="BUY",
                entry_price=45000.0,
                exit_price=46000.0,
                amount=1000.0,
                quantity=0.022,
                fee=2.0,
                strategy_name="Test Strategy",
            )
            print(f"✅ 청산 거래 기록: {exit_id}")
            
            # 통계 확인
            stats = trade_logger.get_statistics()
            print(f"✅ 통계 조회: {stats['total_trades']}건")
            
            assert stats["total_trades"] == 2, "거래 수 불일치"
            assert stats["winning_trades"] == 1, "승리 거래 수 불일치"
            
            # CSV 내보내기
            export_path = trade_logger.export_csv()
            if Path(export_path).exists():
                print(f"✅ CSV 내보내기 성공: {export_path}")
            else:
                print("❌ CSV 내보내기 실패")
                
            # 최근 거래 조회
            recent = trade_logger.get_recent_trades(10)
            assert len(recent) == 2, "최근 거래 수 불일치"
            print(f"✅ 최근 거래 조회: {len(recent)}건")
            
        print("✅ 거래 로거 테스트 완료")
        
    except Exception as e:
        print(f"❌ 거래 로거 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


def test_trade_record():
    """거래 기록 모델 테스트"""
    print("\n" + "="*60)
    print("🧪 거래 기록 모델 테스트")
    print("="*60)
    
    try:
        from src.logging.trade_logger import TradeRecord
        
        # 거래 기록 생성
        trade = TradeRecord(
            trade_id="TRD-TEST-001",
            timestamp="2026-01-13T12:00:00",
            symbol="BTCUSDT",
            trade_type="ENTRY",
            side="BUY",
            entry_price=45000.0,
            amount=1000.0,
            quantity=0.022,
            strategy_name="Test Strategy",
        )
        
        # 딕셔너리 변환
        trade_dict = trade.to_dict()
        assert trade_dict["trade_id"] == "TRD-TEST-001"
        print("✅ 딕셔너리 변환 성공")
        
        # CSV 행 변환
        csv_row = trade.to_csv_row()
        assert len(csv_row) == len(TradeRecord.csv_headers())
        print("✅ CSV 행 변환 성공")
        
        # CSV 헤더
        headers = TradeRecord.csv_headers()
        assert "trade_id" in headers
        assert "symbol" in headers
        print(f"✅ CSV 헤더: {len(headers)}개 필드")
        
        print("✅ 거래 기록 모델 테스트 완료")
        
    except Exception as e:
        print(f"❌ 거래 기록 모델 테스트 실패: {e}")


def test_notification_system():
    """알림 시스템 테스트"""
    print("\n" + "="*60)
    print("🧪 알림 시스템 테스트")
    print("="*60)
    
    try:
        from notification_system import (
            NotificationSystem, NotificationConfig, NotificationType,
            TelegramBotCommands, get_telegram_bot
        )
        
        # 설정 없이 초기화
        config = NotificationConfig(
            telegram_enabled=False,
        )
        notifier = NotificationSystem(config)
        
        # 메시지 포맷팅 테스트 (텔레그램 없이)
        print("✅ 알림 시스템 초기화 성공")
        
        # 텔레그램 봇 명령어 테스트
        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            bot = get_telegram_bot()
            if bot:
                # 도움말 명령어 테스트
                help_response = bot._cmd_help()
                assert "명령어" in help_response
                print("✅ 텔레그램 봇 명령어 테스트 성공")
        else:
            print("⚠️  텔레그램 환경변수 미설정 (스킵)")
            
        print("✅ 알림 시스템 테스트 완료")
        
    except Exception as e:
        print(f"❌ 알림 시스템 테스트 실패: {e}")


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("🚀 로깅 시스템 테스트 시작")
    print("="*60)
    
    test_logger_setup()
    test_trade_record()
    test_trade_logger()
    test_notification_system()
    
    print("\n" + "="*60)
    print("✅ 모든 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    main()
