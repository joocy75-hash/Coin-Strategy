"""
Platform Integration Module

TradingView 전략을 플랫폼에 등록하고 배포하는 모듈
"""

from .strategy_registrar import StrategyRegistrar
from .deployer import StrategyDeployer

__all__ = [
    'StrategyRegistrar',
    'StrategyDeployer',
]

__version__ = '1.0.0'
