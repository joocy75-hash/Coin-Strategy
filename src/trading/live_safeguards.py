#!/usr/bin/env python3
"""
Live Trading Safeguards - 실전매매 안전장치

실전 매매 시 필수적인 안전장치를 제공합니다.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum


class TradingState(Enum):
    """트레이딩 상태"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class SafeguardConfig:
    """안전장치 설정"""
    # 포지션 제한
    max_position_size_percent: float = 10.0  # 자본의 최대 10%
    max_total_exposure_percent: float = 30.0  # 총 노출 최대 30%
    
    # 손실 제한
    daily_loss_limit_percent: float = 5.0  # 일일 최대 손실 5%
    max_drawdown_percent: float = 15.0  # 최대 드로다운 15%
    
    # 연속 손실 제한
    max_consecutive_losses: int = 5  # 연속 5회 손실 시 정지
    
    # 슬리피지
    max_slippage_percent: float = 1.0  # 최대 슬리피지 1%
    
    # 거래 제한
    max_trades_per_day: int = 50  # 일일 최대 거래 수
    min_trade_interval_seconds: int = 60  # 최소 거래 간격 (초)
    
    # 긴급 정지
    emergency_stop_enabled: bool = True


@dataclass
class TradingMetrics:
    """트레이딩 메트릭"""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    daily_pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    peak_balance: float = 0.0
    current_balance: float = 0.0
    last_trade_time: Optional[datetime] = None


class LiveTradingSafeguards:
    """
    실전매매 안전장치
    
    Features:
    - 최대 포지션 크기 제한
    - 일일 최대 손실 제한
    - 연속 손실 시 자동 정지
    - 슬리피지 체크
    - 긴급 정지 플래그
    - 거래 로깅
    """
    
    def __init__(
        self,
        config: Optional[SafeguardConfig] = None,
        initial_balance: float = 10000.0,
        state_file: str = ".trading_state.json",
    ):
        self.config = config or SafeguardConfig()
        self.initial_balance = initial_balance
        self.state_file = Path(state_file)
        
        self.state = TradingState.STOPPED
        self.metrics = TradingMetrics(
            peak_balance=initial_balance,
            current_balance=initial_balance,
        )
        
        self._emergency_stop_flag = False
        self._load_state()
    
    def _load_state(self):
        """상태 파일 로드"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    
                # 오늘 날짜가 아니면 메트릭 리셋
                if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                    self._reset_daily_metrics()
                else:
                    self.metrics.total_trades = data.get("total_trades", 0)
                    self.metrics.daily_pnl = data.get("daily_pnl", 0.0)
                    self.metrics.consecutive_losses = data.get("consecutive_losses", 0)
                    
                self._emergency_stop_flag = data.get("emergency_stop", False)
                
            except Exception as e:
                print(f"Error loading state: {e}")
    
    def _save_state(self):
        """상태 파일 저장"""
        try:
            data = {
                "date": self.metrics.date,
                "total_trades": self.metrics.total_trades,
                "daily_pnl": self.metrics.daily_pnl,
                "consecutive_losses": self.metrics.consecutive_losses,
                "emergency_stop": self._emergency_stop_flag,
                "state": self.state.value,
                "updated_at": datetime.now().isoformat(),
            }
            
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def _reset_daily_metrics(self):
        """일일 메트릭 리셋"""
        self.metrics = TradingMetrics(
            peak_balance=self.metrics.current_balance,
            current_balance=self.metrics.current_balance,
        )
    
    # ============================================================
    # 안전장치 체크
    # ============================================================
    
    def can_trade(self) -> tuple[bool, str]:
        """거래 가능 여부 체크"""
        # 긴급 정지 체크
        if self._emergency_stop_flag:
            return False, "Emergency stop activated"
            
        # 상태 체크
        if self.state != TradingState.RUNNING:
            return False, f"Trading state is {self.state.value}"
            
        # 일일 거래 수 체크
        if self.metrics.total_trades >= self.config.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.config.max_trades_per_day})"
            
        # 일일 손실 체크
        if self.metrics.daily_pnl_percent <= -self.config.daily_loss_limit_percent:
            return False, f"Daily loss limit reached ({self.config.daily_loss_limit_percent}%)"
            
        # 연속 손실 체크
        if self.metrics.consecutive_losses >= self.config.max_consecutive_losses:
            return False, f"Consecutive loss limit reached ({self.config.max_consecutive_losses})"
            
        # 최대 드로다운 체크
        if self.metrics.max_drawdown >= self.config.max_drawdown_percent:
            return False, f"Max drawdown reached ({self.config.max_drawdown_percent}%)"
            
        # 최소 거래 간격 체크
        if self.metrics.last_trade_time:
            elapsed = (datetime.now() - self.metrics.last_trade_time).total_seconds()
            if elapsed < self.config.min_trade_interval_seconds:
                return False, f"Min trade interval not met ({self.config.min_trade_interval_seconds}s)"
                
        return True, "OK"
    
    def check_position_size(self, amount: float, price: float) -> tuple[bool, str, float]:
        """
        포지션 크기 체크
        
        Returns:
            (is_valid, message, adjusted_amount)
        """
        position_value = amount * price
        max_position_value = self.metrics.current_balance * (self.config.max_position_size_percent / 100)
        
        if position_value > max_position_value:
            adjusted_amount = max_position_value / price
            return False, f"Position size exceeds limit. Adjusted to {adjusted_amount:.4f}", adjusted_amount
            
        return True, "OK", amount
    
    def check_slippage(self, expected_price: float, actual_price: float, side: str) -> tuple[bool, str]:
        """슬리피지 체크"""
        if side.lower() == "buy":
            slippage = ((actual_price - expected_price) / expected_price) * 100
        else:
            slippage = ((expected_price - actual_price) / expected_price) * 100
            
        if slippage > self.config.max_slippage_percent:
            return False, f"Slippage too high: {slippage:.2f}% (max: {self.config.max_slippage_percent}%)"
            
        return True, f"Slippage OK: {slippage:.2f}%"
    
    # ============================================================
    # 거래 기록
    # ============================================================
    
    def record_trade(self, pnl: float, is_win: bool):
        """거래 결과 기록"""
        self.metrics.total_trades += 1
        self.metrics.daily_pnl += pnl
        self.metrics.current_balance += pnl
        
        # 승/패 기록
        if is_win:
            self.metrics.winning_trades += 1
            self.metrics.consecutive_losses = 0
        else:
            self.metrics.losing_trades += 1
            self.metrics.consecutive_losses += 1
            
        # 일일 PnL 퍼센트 계산
        self.metrics.daily_pnl_percent = (self.metrics.daily_pnl / self.initial_balance) * 100
        
        # 피크 밸런스 업데이트
        if self.metrics.current_balance > self.metrics.peak_balance:
            self.metrics.peak_balance = self.metrics.current_balance
            
        # 드로다운 계산
        drawdown = ((self.metrics.peak_balance - self.metrics.current_balance) / self.metrics.peak_balance) * 100
        if drawdown > self.metrics.max_drawdown:
            self.metrics.max_drawdown = drawdown
            
        self.metrics.last_trade_time = datetime.now()
        self._save_state()
        
        # 자동 정지 체크
        self._check_auto_stop()
    
    def _check_auto_stop(self):
        """자동 정지 조건 체크"""
        reasons = []
        
        if self.metrics.daily_pnl_percent <= -self.config.daily_loss_limit_percent:
            reasons.append(f"Daily loss limit ({self.config.daily_loss_limit_percent}%)")
            
        if self.metrics.consecutive_losses >= self.config.max_consecutive_losses:
            reasons.append(f"Consecutive losses ({self.config.max_consecutive_losses})")
            
        if self.metrics.max_drawdown >= self.config.max_drawdown_percent:
            reasons.append(f"Max drawdown ({self.config.max_drawdown_percent}%)")
            
        if reasons:
            self.pause(f"Auto-stopped: {', '.join(reasons)}")
    
    # ============================================================
    # 상태 관리
    # ============================================================
    
    def start(self):
        """트레이딩 시작"""
        if self._emergency_stop_flag:
            print("Cannot start: Emergency stop is active. Call reset_emergency_stop() first.")
            return False
            
        self.state = TradingState.RUNNING
        self._save_state()
        return True
    
    def pause(self, reason: str = "Manual pause"):
        """트레이딩 일시 정지"""
        self.state = TradingState.PAUSED
        print(f"Trading paused: {reason}")
        self._save_state()
    
    def stop(self):
        """트레이딩 정지"""
        self.state = TradingState.STOPPED
        self._save_state()
    
    def emergency_stop(self, reason: str = "Emergency"):
        """긴급 정지"""
        self._emergency_stop_flag = True
        self.state = TradingState.EMERGENCY_STOP
        print(f"🚨 EMERGENCY STOP: {reason}")
        self._save_state()
    
    def reset_emergency_stop(self):
        """긴급 정지 해제"""
        self._emergency_stop_flag = False
        self.state = TradingState.STOPPED
        self._save_state()
        print("Emergency stop reset. Call start() to resume trading.")
    
    # ============================================================
    # 상태 조회
    # ============================================================
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 조회"""
        can_trade, reason = self.can_trade()
        
        return {
            "state": self.state.value,
            "can_trade": can_trade,
            "reason": reason,
            "emergency_stop": self._emergency_stop_flag,
            "metrics": {
                "date": self.metrics.date,
                "total_trades": self.metrics.total_trades,
                "winning_trades": self.metrics.winning_trades,
                "losing_trades": self.metrics.losing_trades,
                "win_rate": (self.metrics.winning_trades / self.metrics.total_trades * 100) if self.metrics.total_trades > 0 else 0,
                "consecutive_losses": self.metrics.consecutive_losses,
                "daily_pnl": round(self.metrics.daily_pnl, 2),
                "daily_pnl_percent": round(self.metrics.daily_pnl_percent, 2),
                "max_drawdown": round(self.metrics.max_drawdown, 2),
                "current_balance": round(self.metrics.current_balance, 2),
            },
            "limits": {
                "max_position_size_percent": self.config.max_position_size_percent,
                "daily_loss_limit_percent": self.config.daily_loss_limit_percent,
                "max_consecutive_losses": self.config.max_consecutive_losses,
                "max_drawdown_percent": self.config.max_drawdown_percent,
                "max_trades_per_day": self.config.max_trades_per_day,
            },
        }


# 싱글톤 인스턴스
_safeguards: Optional[LiveTradingSafeguards] = None


def get_safeguards(initial_balance: float = 10000.0) -> LiveTradingSafeguards:
    """Safeguards 싱글톤 인스턴스 반환"""
    global _safeguards
    if _safeguards is None:
        _safeguards = LiveTradingSafeguards(initial_balance=initial_balance)
    return _safeguards


if __name__ == "__main__":
    # 테스트
    safeguards = LiveTradingSafeguards(initial_balance=10000.0)
    
    print("=== Live Trading Safeguards Test ===\n")
    
    # 시작
    safeguards.start()
    print(f"State: {safeguards.state.value}")
    
    # 거래 가능 체크
    can_trade, reason = safeguards.can_trade()
    print(f"Can trade: {can_trade} ({reason})")
    
    # 포지션 크기 체크
    is_valid, msg, adjusted = safeguards.check_position_size(amount=0.5, price=50000)
    print(f"Position check: {is_valid} - {msg}")
    
    # 거래 기록 (승리)
    safeguards.record_trade(pnl=100, is_win=True)
    print(f"After win: Balance=${safeguards.metrics.current_balance}")
    
    # 거래 기록 (패배)
    safeguards.record_trade(pnl=-50, is_win=False)
    print(f"After loss: Balance=${safeguards.metrics.current_balance}")
    
    # 상태 조회
    print("\n=== Status ===")
    status = safeguards.get_status()
    print(json.dumps(status, indent=2))
    
    # 긴급 정지 테스트
    print("\n=== Emergency Stop Test ===")
    safeguards.emergency_stop("Test emergency")
    can_trade, reason = safeguards.can_trade()
    print(f"Can trade after emergency: {can_trade} ({reason})")
    
    # 정리
    safeguards.reset_emergency_stop()
    print("Emergency stop reset")
