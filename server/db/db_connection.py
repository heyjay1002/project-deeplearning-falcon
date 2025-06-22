import logging
import os
import sys
from typing import Optional, Dict, List, Any, Tuple

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    logging.warning("MySQL 라이브러리를 가져올 수 없습니다. 'pip install mysql-connector-python' 명령어로 설치하세요.")
    MYSQL_AVAILABLE = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

class DBConnection:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DBConnection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.host = DB_HOST
        self.port = DB_PORT
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.database = DB_NAME
        logger.info(f"DB 설정: {self.host}:{self.port}/{self.database}")
        self.connection = None
        self.connected = False
        if MYSQL_AVAILABLE:
            self.connect()
        else:
            logger.warning("MySQL 라이브러리가 설치되어 있지 않습니다.")
        self._initialized = True

    def connect(self) -> bool:
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.connected = True
            logger.info(f"데이터베이스 '{self.database}'에 연결됨")
            return True
        except Exception as e:
            logger.error(f"DB 연결 오류: {e}")
            self.connected = False
            return False

    def ensure_connection(self) -> bool:
        if not MYSQL_AVAILABLE:
            return False
        try:
            if not self.connection:
                logger.debug("DB 연결 객체가 없음. 새로 연결합니다.")
                return self.connect()
            if not self.connection.is_connected():
                logger.debug("DB 연결이 끊어짐. 재연결합니다.")
                try:
                    self.connection.close()
                except:
                    pass
                return self.connect()
            return True
        except Exception as e:
            logger.error(f"DB 연결 확인 오류: {str(e)}")
            return self.connect()

    def execute_query(self, query: str, params: Tuple = None) -> Optional[List[Tuple]]:
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 쿼리 실행 불가")
            return None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)} | 쿼리: {query}, 파라미터: {params}")
            raise

    def execute_dict_query(self, query: str, params: Tuple = None) -> Optional[List[Dict]]:
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 쿼리 실행 불가")
            return None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"쿼리 실행 실패: {str(e)} | 쿼리: {query}, 파라미터: {params}")
            raise

    def execute_update(self, query: str, params: Tuple = None) -> int:
        if not self.ensure_connection():
            logger.warning("DB 연결 없음 - 업데이트 실행 불가")
            return 0
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            logger.error(f"업데이트 실행 실패: {str(e)} | 쿼리: {query}, 파라미터: {params}")
            self.connection.rollback()
            raise

    def close(self):
        if self.connection and self.connected:
            try:
                self.connection.close()
                logger.info("데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"데이터베이스 연결 종료 오류: {str(e)}")
        self.connected = False
        self.connection = None

    # 예시: 이벤트 삽입
    def insert_event(self, event_type_id: int, object_id: int, object_type_id: int, map_x: float, map_y: float, area_id: int, timestamp: str, img_path: str):
        cur = self.connection.cursor()
        cur.execute('''
            INSERT INTO DETECT_EVENT (event_type_id, object_id, object_type_id, map_x, map_y, area_id, timestamp, img_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_type_id, object_id, object_type_id, map_x, map_y, area_id, timestamp, img_path))
        self.connection.commit()
        return cur.lastrowid 