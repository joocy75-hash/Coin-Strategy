#!/usr/bin/env python3
"""
Trade Logger - 거래 로그 및 감사 추적

모든 거래 기록을 보관하고 CSV 내보내기를 지원합니다.
법적/세금 목적으로 사용됩니다.
"""

import os
import csv
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .logger import get_logger

logger = get_logger("trade_logger")


class TradeType(Enum):
    """거래 유형"""
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


class TradeStatus(Enum):
    """거래 상태"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


@dataclass
class TradeRecord:
    """거래 기록"""
    # 기본 정보
    trade_id: str
    timestamp: str
    
    # 거래 정보
    symbol: str
    trade_type: str
    side: str  # BUY or SELL
    
    # 가격 정보
    entry_price: float
    exit_price: Optional[float] = None
    amount: float = 0.0
    quantity: float = 0.0
    
    # 수수료
    fee: float = 0.0
    fee_currency: str = "USDT"
    
    # 손익
    pnl: float = 0.0
    pnl_percent: float = 0.0
    
    # 상태
    status: str = "EXECUTED"
    
    # 전략 정보
    strategy_name: str = ""
    strategy_id: str = ""
    
    # 추가 정보
    exchange: str = "binance"
    order_id: str = ""
    notes: str = ""
    
    # 메타데이터
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    def to_csv_row(self) -> List[str]:
        """CSV 행으로 변환"""
        return [
            self.trade_id,
            self.timestamp,
            self.symbol,
            self.trade_type,
            self.side,
            str(self.entry_price),
            str(self.exit_price or ""),
            str(self.amount),
            str(self.quantity),
            str(self.fee),
            self.fee_currency,
            str(self.pnl),
            str(self.pnl_percent),
            self.status,
            self.strategy_name,
            self.exchange,
            self.order_id,
            self.notes,
        ]
    
    @staticmethod
    def csv_headers() -> List[str]:
        """CSV 헤더"""
        return [
            "trade_id", "timestamp", "symbol", "trade_type", "side",
            "entry_price", "exit_price", "amount", "quantity",
            "fee", "fee_currency", "pnl", "pnl_percent",
            "status", "strategy_name", "exchange", "order_id", "notes"
        ]


class TradeLogger:
    """
    거래 로거
    
    Features:
    - 모든 거래 기록 저장
    - JSON 및 CSV 형식 지원
    - 일별/월별 로그 파일
    - CSV 내보내기 (세금 신고용)
    - 거래 통계 계산
    """
    
    def __init__(
        self,
        log_dir: str = "logs/trades",
        json_logging: bool = True,
        csv_logging: bool = True,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.json_logging = json_logging
        self.csv_logging = csv_logging
        
        self._trades: List[TradeRecord] = []
        self._trade_count = 0
        
        # 오늘 날짜 파일
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._init_daily_files()
    
    def _init_daily_files(self):
        """일별 로그 파일 초기화"""
        if self.csv_logging:
            csv_path = self.log_dir / f"trades_{self._current_date}.csv"
            if not csv_path.exists():
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(TradeRecord.csv_headers())
    
    def _check_date_change(self):
        """날짜 변경 체크"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._current_date:
            self._current_date = today
            self._init_daily_files()
    
    def _generate_trade_id(self) -> str:
        """거래 ID 생성"""
        self._trade_count += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"TRD-{timestamp}-{self._trade_count:04d}"
    
    def log_trade(self, trade: TradeRecord) -> str:
        """거래 기록"""
        self._check_date_change()
        
        # 거래 ID 생성 (없는 경우)
        if not trade.trade_id:
            trade.trade_id = self._generate_trade_id()
        
        # 메모리에 저장
        self._trades.append(trade)
        
        # JSON 로깅
        if self.json_logging:
            json_path = self.log_dir / f"trades_{self._current_date}.json"
            with open(json_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trade.to_dict(), ensure_ascii=False) + "\n")
        
        # CSV 로깅
        if self.csv_logging:
            csv_path = self.log_dir / f"trades_{self._current_date}.csv"
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(trade.to_csv_row())
        
        logger.info(
            f"Trade logged: {trade.trade_id} | {trade.symbol} | "
            f"{trade.side} | {trade.amount} @ {trade.entry_price} | "
            f"PnL: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)"
        )
        
        return trade.trade_id
    
    def log_entry(
        self,
        symbol: str,
        side: str,
        price: float,
        amount: float,
        quantity: float,
        strategy_name: str = "",
        exchange: str = "binance",
        order_id: str = "",
        notes: str = "",
    ) -> str:
        """진입 거래 기록"""
        trade = TradeRecord(
            trade_id=self._generate_trade_id(),
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            trade_type="ENTRY",
            side=side,
            entry_price=price,
            amount=amount,
            quantity=quantity,
            strategy_name=strategy_name,
            exchange=exchange,
            order_id=order_id,
            notes=notes,
        )
        return self.log_trade(trade)
    
    def log_exit(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        amount: float,
        quantity: float,
        fee: float = 0.0,
        strategy_name: str = "",
        exchange: str = "binance",
        order_id: str = "",
        notes: str = "",
    ) -> str:
        """청산 거래 기록"""
        # PnL 계산
        if side.upper() == "BUY":
            pnl = (exit_price - entry_price) * quantity - fee
        else:
            pnl = (entry_price - exit_price) * quantity - fee
        
        pnl_percent = (pnl / amount) * 100 if amount > 0 else 0
        
        trade = TradeRecord(
            trade_id=self._generate_trade_id(),
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            trade_type="EXIT",
            side="SELL" if side.upper() == "BUY" else "BUY",
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            quantity=quantity,
            fee=fee,
            pnl=pnl,
            pnl_percent=pnl_percent,
            strategy_name=strategy_name,
            exchange=exchange,
            order_id=order_id,
            notes=notes,
        )
        return self.log_trade(trade)
    
    def export_csv(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """CSV 내보내기 (세금 신고용)"""
        # 기본 출력 경로
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.log_dir / f"trades_export_{timestamp}.csv")
        
        # 날짜 범위 설정
        if not start_date:
            start_date = "2020-01-01"
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 모든 거래 파일 수집
        all_trades = []
        
        for csv_file in sorted(self.log_dir.glob("trades_*.csv")):
            # 날짜 추출
            file_date = csv_file.stem.replace("trades_", "")
            if file_date.startswith("export"):
                continue
                
            if start_date <= file_date <= end_date:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader)  # 헤더 스킵
                    all_trades.extend(list(reader))
        
        # 내보내기
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(TradeRecord.csv_headers())
            writer.writerows(all_trades)
        
        logger.info(f"Exported {len(all_trades)} trades to {output_path}")
        return output_path
    
    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """거래 통계"""
        trades = self._trades
        
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
                "profit_factor": 0.0,
            }
        
        # 통계 계산
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(trades) * 100) if trades else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
            "max_win": round(max((t.pnl for t in trades), default=0), 2),
            "max_loss": round(min((t.pnl for t in trades), default=0), 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 거래 조회"""
        return [t.to_dict() for t in self._trades[-limit:]]


# 싱글톤 인스턴스
_trade_logger: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    """TradeLogger 싱글톤 인스턴스 반환"""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger


if __name__ == "__main__":
    # 테스트
    trade_logger = get_trade_logger()
    
    # 진입 거래 기록
    entry_id = trade_logger.log_entry(
        symbol="BTCUSDT",
        side="BUY",
        price=45000.0,
        amount=1000.0,
        quantity=0.022,
        strategy_name="PMax Strategy",
        notes="Test entry"
    )
    print(f"Entry logged: {entry_id}")
    
    # 청산 거래 기록
    exit_id = trade_logger.log_exit(
        symbol="BTCUSDT",
        side="BUY",
        entry_price=45000.0,
        exit_price=46000.0,
        amount=1000.0,
        quantity=0.022,
        fee=2.0,
        strategy_name="PMax Strategy",
        notes="Test exit - profit"
    )
    print(f"Exit logged: {exit_id}")
    
    # 통계 출력
    stats = trade_logger.get_statistics()
    print(f"\nStatistics: {json.dumps(stats, indent=2)}")
    
    # CSV 내보내기
    export_path = trade_logger.export_csv()
    print(f"\nExported to: {export_path}")
