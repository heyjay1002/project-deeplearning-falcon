# DB 구조 가이드

## 1. 개요

이 문서는 현재 데이터베이스 관련 코드(`db/`)의 구조를 분석하고, 유지보수성 및 재사용성을 높이기 위한 개선 방안을 제안합니다.

---

## 2. 현재 구조 및 문제점

현재 `db/` 폴더는 다음과 같은 파일들로 구성되어 있습니다.

- **`migration.py`**: DB 테이블 생성 및 초기 데이터 삽입을 담당합니다.
- **`db_connection.py`**: `DBConnection` 싱글톤 클래스를 통해 DB 연결을 관리합니다.
- **`repository.py`**: `DetectionRepository` 클래스를 통해 실제 데이터 CRUD 로직을 수행합니다.

이 구조는 각 파일이 특정 역할을 맡고 있다는 점에서 명확하지만, 몇 가지 문제점을 가지고 있습니다.

1.  **DB 연결 로직 중복**:
    - `db_connection.py`의 `DBConnection` 클래스가 DB 연결을 관리하지만, `repository.py`의 `DetectionRepository` 클래스 내에도 별도의 DB 연결/해제 로직(`connect`, `close`)이 존재합니다.
    - `migration.py` 또한 자체적으로 DB 연결을 수행합니다.
    - 이로 인해 DB 설정 정보(`config.py`)가 여러 곳에서 중복으로 사용되며, 연결 관리가 분산되어 있어 일관성이 떨어집니다.

2.  **낮은 응집도**:
    - DB 연결, 데이터 조작, 스키마 마이그레이션 기능이 서로 다른 파일에 분리되어 있어 전체적인 DB 로직을 파악하기 어렵습니다.
    - 기능적으로 매우 밀접한 코드들이 분산되어 있어 함께 수정해야 할 때 불편함이 따릅니다.

---

## 3. 개선 방안: `DBManager`로 통합

DB 관련 로직을 하나의 파일(`db/db_manager.py`)로 통합하여 응집도를 높이고 역할과 책임을 명확히 하는 구조를 제안합니다.

### 3.1 제안 구조

```
db/
├── __init__.py
└── db_manager.py  <-- (신규) DB 관련 클래스 통합 관리
```

`db_manager.py` 파일은 다음 세 개의 클래스를 포함합니다.

1.  **`DBManager`**:
    - **역할**: 데이터베이스 연결 및 트랜잭션 관리를 전담하는 **싱글톤** 클래스.
    - **기능**:
        - DB 연결, 재연결, 종료 로직을 중앙에서 관리합니다.
        - `execute_query`, `execute_update` 등 범용 쿼리 실행 메서드를 제공합니다.
    - **기대 효과**: DB 연결 로직의 중복을 제거하고, 일관된 연결 상태를 보장합니다.

2.  **`Repository`**:
    - **역할**: 모든 데이터베이스 CRUD 작업을 담당합니다.
    - **기능**:
        - `DBManager` 인스턴스를 주입받아 DB에 접근합니다.
        - `save_detection_event`, `get_areas` 등 실제 비즈니스 로직과 관련된 쿼리를 수행합니다.
    - **기대 효과**: 데이터 접근 로직을 한 곳에 모아 관리의 용이성을 높입니다.

3.  **`Migration`**:
    - **역할**: 테이블 생성 및 초기 데이터 삽입 등 DB 스키마 마이그레이션을 담당합니다.
    - **기능**:
        - `DBManager` 인스턴스를 주입받아 테이블 생성/초기 데이터 삽입 쿼리를 실행합니다.
    - **기대 효과**: 스키마 관련 작업을 명확하게 분리합니다.

### 3.2 통합 코드 예시 (`db_manager.py`)

```python
# db/db_manager.py

import logging
import mysql.connector
from typing import Optional, Dict, List, Any, Tuple, Callable
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

class DBManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.config = {
            'host': DB_HOST, 'port': DB_PORT, 'user': DB_USER, 
            'password': DB_PASSWORD, 'database': DB_NAME
        }
        self.connection = None
        self._initialized = True
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.config)
            logger.info(f"데이터베이스 '{self.config['database']}'에 연결됨")
        except mysql.connector.Error as e:
            logger.error(f"DB 연결 오류: {e}")
            self.connection = None

    def ensure_connection(self):
        if self.connection is None or not self.connection.is_connected():
            self.connect()
        return self.connection is not None

    def execute_query(self, query: str, params: Tuple = None, dictionary: bool = False) -> Optional[List[Any]]:
        if not self.ensure_connection(): return None
        try:
            with self.connection.cursor(dictionary=dictionary) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except mysql.connector.Error as e:
            logger.error(f"쿼리 실행 실패: {e}")
            return None

    def execute_update(self, query: str, params: Tuple = None, many: bool = False) -> int:
        if not self.ensure_connection(): return 0
        try:
            with self.connection.cursor() as cursor:
                if many: cursor.executemany(query, params)
                else: cursor.execute(query, params)
                self.connection.commit()
                return cursor.rowcount
        except mysql.connector.Error as e:
            logger.error(f"업데이트 실행 실패: {e}")
            self.connection.rollback()
            return 0

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

class Repository:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        # ... 리포지토리 관련 메서드들 ...

class Migration:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def migrate(self):
        self.create_tables()
        self.insert_initial_data()
        
    def create_tables(self):
        # ... 테이블 생성 쿼리 실행 ...
        pass
        
    def insert_initial_data(self):
        # ... 초기 데이터 삽입 쿼리 실행 ...
        pass

# 사용 예시
if __name__ == '__main__':
    db_manager = DBManager()
    migration = Migration(db_manager)
    migration.migrate()
    db_manager.close()
```

---

## 4. 결론

제안된 구조는 DB 관련 코드의 **응집도**를 높이고, **역할과 책임(SRP)**을 명확히 분리하여 코드의 가독성과 유지보수성을 향상시킬 수 있습니다. `DBManager`를 통해 DB 연결을 중앙에서 관리함으로써 중복 코드를 제거하고 애플리케이션 전체의 안정성을 높일 수 있습니다. 