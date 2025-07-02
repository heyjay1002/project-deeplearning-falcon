import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import threading

class Logger:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
             with self._lock:
                if not self._initialized:
                    self.setup_logger()
                    self._initialized = True

    def setup_logger(self):
        """로거 설정"""
        # 로그 디렉토리 생성
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # 로그 파일 경로 - 실행 시간까지 포함하여 매번 새 파일 생성
        log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

        # 로거 설정
        self.logger = logging.getLogger('ATC_GUI')
        self.logger.setLevel(logging.DEBUG)
        
        # 핸들러 중복 추가 방지
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # 파일 핸들러 설정 (최대 10MB, 최대 5개 파일)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        """디버그 레벨 로그"""
        self.logger.debug(message)

    def info(self, message: str):
        """정보 레벨 로그"""
        self.logger.info(message)

    def warning(self, message: str):
        """경고 레벨 로그"""
        self.logger.warning(message)

    def error(self, message: str):
        """에러 레벨 로그"""
        self.logger.error(message)

    def critical(self, message: str):
        """치명적 에러 레벨 로그"""
        self.logger.critical(message)

# 싱글톤 인스턴스 생성
logger = Logger() 