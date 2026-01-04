"""
Risk Management Patterns for C-Grade Strategy Enhancement

리스크 관리 패턴을 전략에 추가하는 모듈
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


class RiskManagementPatterns:
    """리스크 관리 패턴 집합"""

    @staticmethod
    def calculate_position_size_kelly(win_rate: float, profit_factor: float,
                                     capital: float, fraction: float = 0.25) -> float:
        """
        Kelly Criterion을 사용한 포지션 사이징

        Args:
            win_rate: 승률 (0-1)
            profit_factor: Profit Factor
            capital: 현재 자본
            fraction: Kelly fraction (기본 0.25 = Quarter Kelly)

        Returns:
            포지션 크기
        """
        if profit_factor <= 1.0:
            return capital * 0.02  # 최소 2%

        # Average win / Average loss
        avg_win_loss_ratio = (profit_factor - 1) if profit_factor > 1 else 1.0

        # Kelly percentage: (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
        kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio

        # Fraction Kelly (더 보수적)
        kelly_pct = kelly_pct * fraction

        # 최소 2%, 최대 10% 제한
        kelly_pct = max(0.02, min(0.10, kelly_pct))

        return capital * kelly_pct

    @staticmethod
    def calculate_stop_loss_fixed(entry_price: float, is_long: bool,
                                  percent: float = 5.0) -> float:
        """
        고정 비율 Stop Loss

        Args:
            entry_price: 진입 가격
            is_long: 롱 포지션 여부
            percent: 손절 비율 (기본 5%)

        Returns:
            Stop loss 가격
        """
        if is_long:
            return entry_price * (1 - percent / 100)
        else:
            return entry_price * (1 + percent / 100)

    @staticmethod
    def calculate_stop_loss_atr(entry_price: float, atr: float, is_long: bool,
                               multiplier: float = 2.0) -> float:
        """
        ATR 기반 Stop Loss

        Args:
            entry_price: 진입 가격
            atr: Average True Range
            is_long: 롱 포지션 여부
            multiplier: ATR 승수 (기본 2.0)

        Returns:
            Stop loss 가격
        """
        if is_long:
            return entry_price - (atr * multiplier)
        else:
            return entry_price + (atr * multiplier)

    @staticmethod
    def calculate_take_profit_rr(entry_price: float, stop_loss: float,
                                is_long: bool, reward_risk_ratio: float = 2.0) -> float:
        """
        Risk:Reward 비율 기반 Take Profit

        Args:
            entry_price: 진입 가격
            stop_loss: Stop loss 가격
            is_long: 롱 포지션 여부
            reward_risk_ratio: Risk:Reward 비율 (기본 1:2)

        Returns:
            Take profit 가격
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * reward_risk_ratio

        if is_long:
            return entry_price + reward
        else:
            return entry_price - reward

    @staticmethod
    def calculate_trailing_stop(entry_price: float, current_price: float,
                               highest_price: float, is_long: bool,
                               activation_percent: float = 5.0,
                               trailing_percent: float = 3.0) -> Optional[float]:
        """
        Trailing Stop Loss

        Args:
            entry_price: 진입 가격
            current_price: 현재 가격
            highest_price: 진입 이후 최고가 (롱) / 최저가 (숏)
            is_long: 롱 포지션 여부
            activation_percent: Trailing 활성화 수익률 (기본 5%)
            trailing_percent: Trailing 비율 (기본 3%)

        Returns:
            Trailing stop 가격 (또는 None)
        """
        if is_long:
            # 롱: 진입가 대비 activation_percent 이상 상승 시 활성화
            profit_pct = (highest_price - entry_price) / entry_price * 100

            if profit_pct >= activation_percent:
                # 최고가 대비 trailing_percent 하락 시 청산
                return highest_price * (1 - trailing_percent / 100)
        else:
            # 숏: 진입가 대비 activation_percent 이상 하락 시 활성화
            profit_pct = (entry_price - highest_price) / entry_price * 100

            if profit_pct >= activation_percent:
                # 최저가 대비 trailing_percent 상승 시 청산
                return highest_price * (1 + trailing_percent / 100)

        return None


class EnhancedRiskManagementMixin:
    """
    전략 클래스에 추가할 수 있는 리스크 관리 Mixin

    Usage:
        class MyStrategy(Strategy, EnhancedRiskManagementMixin):
            # 파라미터
            use_fixed_sl = True
            use_atr_sl = False
            use_rr_tp = True
            use_trailing_stop = True

            sl_percent = 5.0
            atr_sl_multiplier = 2.0
            rr_ratio = 2.0
            trailing_activation = 5.0
            trailing_percent = 3.0

            def init(self):
                self.init_risk_management()
                # ... 기존 init 로직

            def next(self):
                # ... 기존 next 로직
                self.manage_risk()
    """

    # Risk management parameters
    use_fixed_sl = True
    use_atr_sl = False
    use_rr_tp = True
    use_trailing_stop = True

    sl_percent = 5.0
    atr_sl_multiplier = 2.0
    rr_ratio = 2.0
    trailing_activation = 5.0
    trailing_percent = 3.0

    def init_risk_management(self):
        """리스크 관리 초기화"""
        self.rm_patterns = RiskManagementPatterns()
        self.position_highest = 0.0  # 포지션 진입 이후 최고가/최저가

    def manage_risk(self):
        """
        리스크 관리 로직 실행
        포지션이 있을 때만 실행
        """
        if not self.position or len(self.trades) == 0:
            return

        entry_price = self.trades[-1].entry_price
        current_price = self.data.Close[-1]
        is_long = self.position.is_long

        # 최고가/최저가 추적
        if is_long:
            self.position_highest = max(self.position_highest, current_price)
        else:
            if self.position_highest == 0:
                self.position_highest = current_price
            else:
                self.position_highest = min(self.position_highest, current_price)

        # 1. Stop Loss 체크
        stop_price = None

        if self.use_fixed_sl:
            stop_price = self.rm_patterns.calculate_stop_loss_fixed(
                entry_price, is_long, self.sl_percent
            )
        elif self.use_atr_sl and hasattr(self, 'atr'):
            atr_value = self.atr[-1]
            stop_price = self.rm_patterns.calculate_stop_loss_atr(
                entry_price, atr_value, is_long, self.atr_sl_multiplier
            )

        # Stop loss 체크
        if stop_price:
            if is_long and current_price <= stop_price:
                self.position.close()
                self.position_highest = 0.0
                return
            elif not is_long and current_price >= stop_price:
                self.position.close()
                self.position_highest = 0.0
                return

        # 2. Take Profit 체크 (Risk:Reward 비율)
        if self.use_rr_tp and stop_price:
            tp_price = self.rm_patterns.calculate_take_profit_rr(
                entry_price, stop_price, is_long, self.rr_ratio
            )

            if is_long and current_price >= tp_price:
                self.position.close()
                self.position_highest = 0.0
                return
            elif not is_long and current_price <= tp_price:
                self.position.close()
                self.position_highest = 0.0
                return

        # 3. Trailing Stop 체크
        if self.use_trailing_stop:
            trailing_price = self.rm_patterns.calculate_trailing_stop(
                entry_price, current_price, self.position_highest, is_long,
                self.trailing_activation, self.trailing_percent
            )

            if trailing_price:
                if is_long and current_price <= trailing_price:
                    self.position.close()
                    self.position_highest = 0.0
                    return
                elif not is_long and current_price >= trailing_price:
                    self.position.close()
                    self.position_highest = 0.0
                    return


def generate_risk_managed_code(original_code: str, strategy_name: str) -> str:
    """
    원본 전략 코드에 리스크 관리를 추가한 코드 생성

    Args:
        original_code: 원본 전략 Python 코드
        strategy_name: 전략 클래스 이름

    Returns:
        리스크 관리가 추가된 전략 코드
    """
    # Import 추가
    enhanced_code = original_code.replace(
        "from backtesting import Strategy",
        "from backtesting import Strategy\nfrom risk_management_patterns import EnhancedRiskManagementMixin"
    )

    # 클래스 선언에 Mixin 추가
    enhanced_code = enhanced_code.replace(
        f"class {strategy_name}(Strategy):",
        f"class {strategy_name}Enhanced(Strategy, EnhancedRiskManagementMixin):"
    )

    # init 메서드에 리스크 관리 초기화 추가
    if "def init(self):" in enhanced_code:
        enhanced_code = enhanced_code.replace(
            "def init(self):",
            """def init(self):
        \"\"\"Initialize indicators and risk management.\"\"\"
        self.init_risk_management()"""
        )

    # next 메서드 마지막에 리스크 관리 호출 추가
    # (단순 구현: return 전에 manage_risk() 호출)
    lines = enhanced_code.split('\n')
    new_lines = []
    in_next_method = False

    for i, line in enumerate(lines):
        new_lines.append(line)

        if 'def next(self):' in line:
            in_next_method = True

        # next 메서드 내 return 직전에 manage_risk() 추가
        if in_next_method and i < len(lines) - 1:
            next_line = lines[i + 1]
            if next_line.strip() == '' or (not next_line.startswith(' ' * 8) and next_line.strip()):
                # next 메서드 끝
                new_lines.insert(-1, '        self.manage_risk()')
                in_next_method = False

    return '\n'.join(new_lines)


if __name__ == "__main__":
    # 테스트
    rm = RiskManagementPatterns()

    # 예제: 롱 포지션
    entry = 50000
    atr = 1000

    print("Risk Management Pattern Examples")
    print("=" * 60)

    # Fixed Stop Loss
    sl_fixed = rm.calculate_stop_loss_fixed(entry, True, 5.0)
    print(f"Fixed SL (5%): ${sl_fixed:,.2f}")

    # ATR Stop Loss
    sl_atr = rm.calculate_stop_loss_atr(entry, atr, True, 2.0)
    print(f"ATR SL (2x): ${sl_atr:,.2f}")

    # Take Profit (1:2 RR)
    tp = rm.calculate_take_profit_rr(entry, sl_fixed, True, 2.0)
    print(f"Take Profit (1:2 RR): ${tp:,.2f}")

    # Trailing Stop
    current = 55000
    highest = 56000
    trailing = rm.calculate_trailing_stop(entry, current, highest, True, 5.0, 3.0)
    print(f"Trailing Stop: ${trailing:,.2f}" if trailing else "Trailing Stop: Not activated")

    print("\nRisk:Reward Ratio:")
    risk = abs(entry - sl_fixed)
    reward = abs(tp - entry)
    print(f"  Risk: ${risk:,.2f}")
    print(f"  Reward: ${reward:,.2f}")
    print(f"  Ratio: 1:{reward/risk:.2f}")
