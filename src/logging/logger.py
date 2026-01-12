#!/usr/bin/env python3
"""
Logger - 통합 로깅 시스템

Features:
- 파일 및 콘솔 로깅
- 로그 로테이션
- JSON 포맷 지원
- 컬러 콘솔 출력
- 모듈별 로거 관리
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogConfig:
    """로깅 설정"""
    # 기본 설정
    level: LogLevel = LogLevel.INFO
    log_dir: str = "logs"
    
    # 파일 로깅
    file_logging: bool = True
    file_name: str = "app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # 콘솔 로깅
    console_logging: bool = True
    console_color: bool = True
    
    # JSON 로깅
    json_logging: bool = False
    json_file_name: str = "app.json.log"
    
    # 포맷
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


class ColorFormatter(logging.Formatter):
    """컬러 콘솔 포맷터"""
    
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON 포맷터"""
    
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
        
        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # 추가 필드
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
            
        return json.dumps(log_data, ensure_ascii=False)


class LoggerManager:
    """로거 관리자 (싱글톤)"""
    
    _instance: Optional["LoggerManager"] = None
    _loggers: Dict[str, logging.Logger] = {}
    _config: Optional[LogConfig] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def setup(self, config: Optional[LogConfig] = None):
        """로깅 시스템 초기화"""
        if self._initialized:
            return
            
        self._config = config or LogConfig()
        
        # 로그 디렉토리 생성
        log_dir = Path(self._config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(self._config.level.value)
        
        # 기존 핸들러 제거
        root_logger.handlers.clear()
        
        # 콘솔 핸들러
        if self._config.console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._config.level.value)
            
            if self._config.console_color:
                formatter = ColorFormatter(
                    self._config.log_format,
                    datefmt=self._config.date_format
                )
            else:
                formatter = logging.Formatter(
                    self._config.log_format,
                    datefmt=self._config.date_format
                )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # 파일 핸들러
        if self._config.file_logging:
            file_path = log_dir / self._config.file_name
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=self._config.max_file_size,
                backupCount=self._config.backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(self._config.level.value)
            file_handler.setFormatter(logging.Formatter(
                self._config.log_format,
                datefmt=self._config.date_format
            ))
            root_logger.addHandler(file_handler)
        
        # JSON 파일 핸들러
        if self._config.json_logging:
            json_path = log_dir / self._config.json_file_name
            json_handler = RotatingFileHandler(
                json_path,
                maxBytes=self._config.max_file_size,
                backupCount=self._config.backup_count,
                encoding="utf-8"
            )
            json_handler.setLevel(self._config.level.value)
            json_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(json_handler)
        
        self._initialized = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """모듈별 로거 반환"""
        if not self._initialized:
            self.setup()
            
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
            
        return self._loggers[name]


# 전역 함수
def setup_logging(config: Optional[LogConfig] = None):
    """로깅 시스템 초기화"""
    manager = LoggerManager()
    manager.setup(config)


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 반환"""
    manager = LoggerManager()
    return manager.get_logger(name)


# API 서버용 로거 설정
def setup_api_logging():
    """API 서버용 로깅 설정"""
    config = LogConfig(
        level=LogLevel.INFO,
        log_dir="logs",
        file_name="api.log",
        json_logging=True,
        json_file_name="api.json.log",
    )
    setup_logging(config)
    return get_logger("api")


# 트레이딩 봇용 로거 설정
def setup_trading_logging():
    """트레이딩 봇용 로깅 설정"""
    config = LogConfig(
        level=LogLevel.DEBUG,
        log_dir="logs",
        file_name="trading.log",
        json_logging=True,
        json_file_name="trading.json.log",
    )
    setup_logging(config)
    return get_logger("trading")


# 수집기용 로거 설정
def setup_collector_logging():
    """수집기용 로깅 설정"""
    config = LogConfig(
        level=LogLevel.INFO,
        log_dir="logs",
        file_name="collector.log",
    )
    setup_logging(config)
    return get_logger("collector")


if __name__ == "__main__":
    # 테스트
    setup_logging(LogConfig(
        level=LogLevel.DEBUG,
        console_color=True,
        json_logging=True,
    ))
    
    logger = get_logger("test")
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        logger.exception("Exception occurred")
