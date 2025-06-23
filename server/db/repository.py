from .db_connection import DBConnection
from typing import List, Optional, Dict, Any
import logging
import mysql.connector
from datetime import datetime, timezone, timedelta
from config import AUTO_DELETE_DB_ON_START, DEBUG_OBJECT_ID_START

logger = logging.getLogger(__name__)

class ObjectEventRepository:
    def __init__(self, db: Optional[DBConnection] = None):
        self.db = db or DBConnection()

    def add_event(self, event: Dict[str, Any]) -> int:
        query = '''
            INSERT INTO DETECT_EVENT (event_type_id, object_id, object_type_id, map_x, map_y, area_id, timestamp, img_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = (
            event['event_type_id'], event['object_id'], event['object_type_id'],
            event['map_x'], event['map_y'], event['area_id'],
            event['timestamp'], event['img_path']
        )
        return self.db.execute_update(query, params)

    def get_event(self, event_id: int) -> Optional[Dict]:
        query = 'SELECT * FROM DETECT_EVENT WHERE event_id = %s'
        rows = self.db.execute_dict_query(query, (event_id,))
        return rows[0] if rows else None

    def list_events(self, limit: int = 100) -> List[Dict]:
        query = 'SELECT * FROM DETECT_EVENT ORDER BY timestamp DESC LIMIT %s'
        rows = self.db.execute_dict_query(query, (limit,))
        return rows or []

    # 기타 테이블에 대한 CRUD도 유사하게 구현 가능 (예시)
    # def add_object_type(self, ...): ...
    # def get_area(self, ...): ...

class DetectionRepository:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
        self.conn = None
        if DEBUG_OBJECT_ID_START:
            self.max_object_id = 999  # 디버그 모드: 1000부터 시작
        else:
            self.max_object_id = None  # 운영 모드: DB 상황에 따라
        self.on_save_complete = None  # DB 저장 완료 콜백 함수

    def set_save_complete_callback(self, callback):
        """DB 저장 완료 시 호출될 콜백 함수 설정
        Args:
            callback: 콜백 함수 (detections, img_id, crop_imgs) 매개변수 받음
        """
        self.on_save_complete = callback

    def connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = mysql.connector.connect(**self.config)
            logger.info(f"데이터베이스 '{self.config['database']}'에 연결됨")
            cur = self.conn.cursor()

            # config 값에 따라 테이블 초기화 실행
            if AUTO_DELETE_DB_ON_START:
                logger.warning("AUTO_DELETE_DB_ON_START 설정이 True이므로 DB의 탐지 이벤트를 초기화합니다.")
                # 개발/테스트용: 부팅 시 테이블 초기화
                cur.execute("DELETE FROM DETECT_EVENT")
                cur.execute("DELETE FROM DETECTED_OBJECT")
                self.conn.commit()
                logger.info("DETECT_EVENT 및 DETECTED_OBJECT 테이블 초기화 완료")

            # 서버 시작 시 기존 object_id의 최대값을 읽어와 저장
            if not DEBUG_OBJECT_ID_START:
                cur.execute("SELECT MAX(object_id) FROM DETECTED_OBJECT")
                result = cur.fetchone()
                self.max_object_id = result[0] if result and result[0] is not None else None
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {str(e)}")
            raise

    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def save_detection_event(self, camera_id: str, img_id: int, detections: List[Dict], crop_imgs: list) -> bool:
        """객체 감지 이벤트 저장
        Args:
            camera_id: 카메라 ID
            img_id: 이미지 ID
            detections: 감지된 객체 목록 (이미 최초 감지 확인 완료)
            crop_imgs: 각 detection에 대응하는 crop된 이미지 바이너리(jpg)
        Returns:
            bool: 저장 성공 여부
        """
        if not self.conn:
            self.connect()

        cur = self.conn.cursor()
        try:
            print(f"[DEBUG] DB 저장 시작: {len(detections)}개 객체, img_id={img_id}")
            
            # 기존 트랜잭션이 있으면 롤백
            if self.conn.in_transaction:
                print("[DEBUG] 기존 트랜잭션 롤백")
                self.conn.rollback()
            
            self.conn.start_transaction()
            print("[DEBUG] 새 트랜잭션 시작")
            
            for i, detection in enumerate(detections):
                object_id = detection['object_id']
                class_name = detection['class']
                print(f"[DEBUG] 객체 {i+1}/{len(detections)}: object_id={object_id}, class={class_name}")
                
                object_type_id = self._get_object_type_id(class_name)
                print(f"[DEBUG] object_type_id 조회 결과: {object_type_id}")
                
                if object_type_id is None:
                    print(f"[ERROR] 알 수 없는 객체 타입: {class_name}")
                    logger.warning(f"알 수 없는 객체 타입: {class_name}")
                    continue
                
                # KST (UTC+9) 시간으로 이벤트 시간 기록
                kst = timezone(timedelta(hours=9))
                event_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[DEBUG] DETECTED_OBJECT 삽입: object_id={object_id}, object_type_id={object_type_id}")
                
                cur.execute(
                    "INSERT INTO DETECTED_OBJECT (object_id, object_type_id) VALUES (%s, %s)",
                    (object_id, object_type_id)
                )
                
                map_x = detection.get('map_x')
                map_y = detection.get('map_y')
                area_id = detection.get('area_id')
                event_type_id = self._determine_event_type(class_name)
                
                print(f"[DEBUG] 좌표 정보: map_x={map_x}, map_y={map_y}, area_id={area_id}")
                print(f"[DEBUG] 이벤트 타입: {event_type_id}")
                
                cur.execute("""
                    INSERT INTO DETECT_EVENT 
                    (event_type_id, object_id, object_type_id, map_x, map_y, 
                     area_id, timestamp, img_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_type_id,
                    object_id,
                    object_type_id,
                    map_x,
                    map_y,
                    area_id,
                    event_time,
                    f"img/img_{object_id}.jpg"
                ))
                
                # max_object_id 갱신 로직
                if self.max_object_id is None:
                    self.max_object_id = object_id
                elif object_id > self.max_object_id:
                    self.max_object_id = object_id

                print(f"[DEBUG] 객체 {object_id} 저장 완료")
            
            print("[DEBUG] 트랜잭션 커밋 시도")
            self.conn.commit()
            print(f"[INFO] DB 저장 성공: {len(detections)}개 객체")
            
            if self.on_save_complete:
                print("[DEBUG] 콜백 함수 호출")
                self.on_save_complete(detections, crop_imgs)
            return True
            
        except Exception as e:
            print(f"[ERROR] DB 저장 실패: {str(e)}")
            print(f"[ERROR] 에러 타입: {type(e).__name__}")
            if self.conn.in_transaction:
                print("[DEBUG] 트랜잭션 롤백")
                self.conn.rollback()
            logger.error(f"이벤트 저장 중 오류: {str(e)}")
            return False

    def get_event_by_object_id(self, object_id: int) -> Optional[Dict[str, Any]]:
        """object_id로 가장 최근의 DETECT_EVENT 정보 조회
        Args:
            object_id: 객체 ID
        Returns:
            Optional[Dict]: 이벤트 정보 딕셔너리
        """
        if not self.conn:
            self.connect()

        query = """
            SELECT
                de.object_id,
                ot.object_type_name AS class,
                de.map_x,
                de.map_y,
                a.area_name AS zone,
                de.timestamp,
                de.img_path
            FROM DETECT_EVENT de
            JOIN OBJECT_TYPE ot ON de.object_type_id = ot.object_type_id
            LEFT JOIN AREA a ON de.area_id = a.area_id
            WHERE de.object_id = %s
            ORDER BY de.timestamp DESC
            LIMIT 1
        """
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(query, (object_id,))
            result = cur.fetchone()
            return result
        except Exception as e:
            logger.error(f"object_id로 이벤트 조회 중 오류: {e}")
            return None
        finally:
            cur.close()

    def _get_object_type_id(self, class_name: str) -> Optional[int]:
        """객체 타입 ID 조회
        Args:
            class_name: 객체 클래스 이름
        Returns:
            Optional[int]: 객체 타입 ID
        """
        cur = self.conn.cursor()
        try:
            print(f"[DEBUG] 객체 타입 조회: class_name='{class_name}' -> '{class_name.upper()}'")
            cur.execute(
                "SELECT object_type_id FROM OBJECT_TYPE WHERE object_type_name = %s",
                (class_name.upper(),)
            )
            result = cur.fetchone()
            object_type_id = result[0] if result else None
            print(f"[DEBUG] 조회 결과: {object_type_id}")
            
            # 사용 가능한 객체 타입들도 출력 (디버깅용)
            if object_type_id is None:
                print("[DEBUG] 사용 가능한 객체 타입들:")
                cur.execute("SELECT object_type_id, object_type_name FROM OBJECT_TYPE")
                available_types = cur.fetchall()
                for obj_id, obj_name in available_types:
                    print(f"[DEBUG]   {obj_id}: {obj_name}")
            
            return object_type_id
        except Exception as e:
            print(f"[ERROR] 객체 타입 조회 중 오류: {str(e)}")
            logger.error(f"객체 타입 조회 중 오류: {str(e)}")
            return None

    def _determine_event_type(self, class_name: str) -> int:
        """이벤트 타입 결정
        Args:
            class_name: 객체 클래스 이름
        Returns:
            int: 이벤트 타입 ID
        """
        class_name_upper = class_name.upper()
        
        # 클래스에 따른 이벤트 타입 결정
        if class_name_upper in ['PERSON', 'WORK_PERSON']:
            return 2  # UNAUTH
        elif class_name_upper in ['BIRD', 'ANIMAL']:
            return 3  # RESCUE
        elif class_name_upper in ['CAR', 'TRUCK', 'BUS', 'VEHICLE', 'WORK_VEHICLE']:
            return 1  # HAZARD
        elif class_name_upper in ['FOD', 'FIRE']:
            return 1  # HAZARD
        elif class_name_upper == 'AIRPLANE':
            return 1  # HAZARD
        else:
            return 1  # 기본값: HAZARD 