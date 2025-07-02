import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import mysql.connector
from mysql.connector import Error
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DatabaseMigration:
    def __init__(self):
        self.config = {
            'host': DB_HOST,
            'port': DB_PORT,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME
        }
        self.conn = None

    def connect(self):
        self.conn = mysql.connector.connect(**self.config)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        cur = self.conn.cursor()
        try:
            # 1. 객체 감지 및 이벤트 기록
            cur.execute('''CREATE TABLE IF NOT EXISTS OBJECT_TYPE (
                object_type_id INT PRIMARY KEY,
                object_type_name VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS EVENT_TYPE (
                event_type_id INT PRIMARY KEY,
                event_type_name VARCHAR(32) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS AREA (
                area_id INT PRIMARY KEY,
                area_name VARCHAR(16) NOT NULL,
                x1 FLOAT, y1 FLOAT, x2 FLOAT, y2 FLOAT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS DETECTED_OBJECT (
                object_id BIGINT PRIMARY KEY,
                object_type_id INT,
                FOREIGN KEY(object_type_id) REFERENCES OBJECT_TYPE(object_type_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS DETECT_EVENT (
                event_id INT AUTO_INCREMENT PRIMARY KEY,
                event_type_id INT,
                object_id BIGINT,
                object_type_id INT,
                map_x FLOAT,
                map_y FLOAT,
                area_id INT,
                timestamp DATETIME,
                img_path VARCHAR(256),
                FOREIGN KEY(event_type_id) REFERENCES EVENT_TYPE(event_type_id),
                FOREIGN KEY(object_id) REFERENCES DETECTED_OBJECT(object_id),
                FOREIGN KEY(object_type_id) REFERENCES OBJECT_TYPE(object_type_id),
                FOREIGN KEY(area_id) REFERENCES AREA(area_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS AUTHORITY_LEVEL (
                level_id INT PRIMARY KEY,
                level_name VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS ACCESS_CONDITIONS (
                area_id INT,
                authority_level_id INT,
                FOREIGN KEY(area_id) REFERENCES AREA(area_id),
                FOREIGN KEY(authority_level_id) REFERENCES AUTHORITY_LEVEL(level_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

            # 2. 조류 위험도 분석
            cur.execute('''CREATE TABLE IF NOT EXISTS BIRD_RISK_LEVEL (
                id INT PRIMARY KEY,
                name VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS BIRD_RISK_LOG (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bird_risk_level_id INT,
                timestamp DATETIME,
                FOREIGN KEY(bird_risk_level_id) REFERENCES BIRD_RISK_LEVEL(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

            # 3. 조종사 음성 요청 자동 응답
            cur.execute('''CREATE TABLE IF NOT EXISTS REQUEST_TYPE (
                request_id INT PRIMARY KEY,
                request_code VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS RESPONSE_TYPE (
                response_id INT PRIMARY KEY,
                response_code VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS INTERACTION_STATUS (
                status_id INT PRIMARY KEY,
                status_code VARCHAR(16) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS INTERACTION_LOG (
                id INT AUTO_INCREMENT PRIMARY KEY,
                request_id INT,
                response_id INT,
                request_time DATETIME,
                response_time DATETIME,
                status_id INT,
                FOREIGN KEY(request_id) REFERENCES REQUEST_TYPE(request_id),
                FOREIGN KEY(response_id) REFERENCES RESPONSE_TYPE(response_id),
                FOREIGN KEY(status_id) REFERENCES INTERACTION_STATUS(status_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            self.conn.commit()
            logger.info('모든 테이블 생성 완료: %s', self.config['database'])
        except Exception as e:
            logger.error('테이블 생성 중 오류: %s', str(e))
            self.conn.rollback()
            raise

    def insert_initial_data(self):
        cur = self.conn.cursor()
        try:
            # EVENT_TYPE
            cur.executemany('INSERT IGNORE INTO EVENT_TYPE (event_type_id, event_type_name) VALUES (%s, %s)', [
                (1, 'HAZARD'), (2, 'UNAUTH'), (3, 'RESCUE')
            ])
            # OBJECT_TYPE
            cur.executemany('INSERT IGNORE INTO OBJECT_TYPE (object_type_id, object_type_name) VALUES (%s, %s)', [
                (0, 'BIRD'),
                (1, 'FOD'),
                (2, 'PERSON'),
                (3, 'ANIMAL'),
                (4, 'AIRPLANE'),
                (5, 'VEHICLE'),
                (6, 'WORK_PERSON'),
                (7, 'WORK_VEHICLE')
            ])
            # AUTHORITY_LEVEL
            cur.executemany('INSERT IGNORE INTO AUTHORITY_LEVEL (level_id, level_name) VALUES (%s, %s)', [
                (1, 'OPEN'), (2, 'AUTH_ONLY'), (3, 'NO_ENTRY')
            ])
            # REQUEST_TYPE
            cur.executemany('INSERT IGNORE INTO REQUEST_TYPE (request_id, request_code) VALUES (%s, %s)', [
                (1, 'BR_INQ'), (2, 'RWY_A_STATUS'), (3, 'RWY_B_STATUS'), (4, 'RWY_AVAIL_IN')
            ])
            # RESPONSE_TYPE
            cur.executemany('INSERT IGNORE INTO RESPONSE_TYPE (response_id, response_code) VALUES (%s, %s)', [
                (1, 'BR_HIGH'), (2, 'BR_MEDIUM'), (3, 'BR_LOW'), (4, 'CLEAR'), (5, 'BLOCKED'), (6, 'ALL'), (7, 'A_ONLY'), (8, 'B_ONLY'), (9, 'NONE')
            ])
            # INTERACTION_STATUS
            cur.executemany('INSERT IGNORE INTO INTERACTION_STATUS (status_id, status_code) VALUES (%s, %s)', [
                (1, 'SUCCESS'), (2, 'ERROR')
            ])
            # BIRD_RISK_LEVEL
            cur.executemany('INSERT IGNORE INTO BIRD_RISK_LEVEL (id, name) VALUES (%s, %s)', [
                (1, 'BR_HIGH'), (2, 'BR_MEDIUM'), (3, 'BR_LOW')
            ])
            # AREA
            cur.executemany('INSERT IGNORE INTO AREA (area_id, area_name, x1, y1, x2, y2) VALUES (%s, %s, %s, %s, %s, %s)', [
                (1, 'TWY_A', 0.00, 0.23, 0.19, 0.52),
                (2, 'TWY_B', 0.81, 0.23, 1.00, 0.52),
                (3, 'TWY_C', 0.00, 0.73, 0.19, 1.00),
                (4, 'TWY_D', 0.81, 0.73, 1.00, 1.00),
                (5, 'RWY_A', 0.00, 0.00, 1.00, 0.23),
                (6, 'RWY_B', 0.00, 0.52, 1.00, 0.73),
                (7, 'GRASS_A', 0.19, 0.23, 0.81, 0.52),
                (8, 'GRASS_B', 0.19, 0.73, 0.81, 1.00)
            ])
            # ACCESS_CONDITIONS
            cur.executemany('INSERT IGNORE INTO ACCESS_CONDITIONS (area_id, authority_level_id) VALUES (%s, %s)', [
                (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2)
            ])
            self.conn.commit()
            logger.info('초기 마스터 데이터 삽입 완료')
        except Exception as e:
            logger.error('초기 데이터 삽입 중 오류: %s', str(e))
            self.conn.rollback()
            raise

    def migrate(self):
        logger.info('DB 마이그레이션 시작...')
        self.connect()
        try:
            self.create_tables()
            self.insert_initial_data()
        finally:
            self.close()

if __name__ == '__main__':
    DatabaseMigration().migrate() 