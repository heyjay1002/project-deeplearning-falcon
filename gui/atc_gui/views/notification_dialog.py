import os
import datetime
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QStyle
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage
from utils.logger import logger

class NotificationDialog(QDialog):
    """알림 다이얼로그"""

    def __init__(self, notification_type: str, data: any, parent=None):
        super().__init__(parent)
        self.setWindowTitle("알림")
        self.notification_type = notification_type
        self.data = data

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(300, 300)

        self.init_ui()
        
        # 초기 위치 설정
        if parent:
            self.adjust_position()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 1px solid #AAAAAA;
            }
            QLabel {
                color: #222222;
                font-size: 18px;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 제목과 아이콘을 가로로 배치할 레이아웃
        title_layout = QHBoxLayout()
        
        # 아이콘 추가
        icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'resources/images/warning_red.png')

        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            icon_label.setPixmap(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # 파일이 없으면 표준 아이콘으로 대체
            fallback_icon_type = QStyle.StandardPixmap.SP_MessageBoxWarning if self.notification_type in ['object', 'violation_access'] else QStyle.StandardPixmap.SP_MessageBoxInformation
            icon = self.style().standardIcon(fallback_icon_type)
            icon_label.setPixmap(icon.pixmap(QSize(50, 50)))
            if icon_path:
                logger.warning(f"Icon file not found: {icon_path}. Using default icon.")
        
        title_layout.addWidget(icon_label)

        # 제목 레이블 추가
        title_label = QLabel(self.get_title())
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        title_layout.addWidget(title_label)

        title_layout.addStretch() # 아이콘과 제목을 좌측으로 밀어 정렬
        
        # 메인 레이아웃에 제목 레이아웃 추가
        main_layout.addLayout(title_layout)

        # 본문 영역
        if self.notification_type in ['object', 'violation_access']:
            # 객체 감지 이벤트: 이미지 + 정보를 좌우로 배치
            content_layout = QHBoxLayout()
            content_layout.setSpacing(15)

            # 이미지 영역 (왼쪽)
            if hasattr(self.data, 'image_data') and self.data.image_data:
                try:
                    image = QImage.fromData(self.data.image_data)
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        image_label = QLabel()
                        image_label.setPixmap(pixmap.scaled(120, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        image_label.setFixedSize(120, 100)
                        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        image_label.setStyleSheet("border: 1px solid #ccc;")
                        content_layout.addWidget(image_label)
                except Exception as e:
                    logger.error(f"이미지 처리 오류: {str(e)}")

            # 정보 영역 (오른쪽)
            info_layout = QFormLayout()
            info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            info_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            info_layout.setHorizontalSpacing(10)
            info_layout.setVerticalSpacing(8)

            info_layout.addRow("ID:", QLabel(str(self.data.object_id)))
            info_layout.addRow("종류:", QLabel(str(self.data.object_type.value)))
            info_layout.addRow("구역:", QLabel(str(self.data.zone.value)))
            
            if hasattr(self.data, 'timestamp'):
                ts = self.data.timestamp
                if isinstance(ts, (datetime.datetime,)):
                    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    ts_str = str(ts)
                info_layout.addRow("발견 시각:", QLabel(ts_str))
            
            if hasattr(self.data, 'extra_info') and self.data.extra_info:
                value = self.data.extra_info.value if hasattr(self.data.extra_info, 'value') else str(self.data.extra_info)
                info_layout.addRow("상태:", QLabel(value))

            content_layout.addLayout(info_layout)
            main_layout.addLayout(content_layout)
            
        else:
            # 다른 이벤트: 정보만 표시
            info_layout = QFormLayout()
            info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            info_layout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
            info_layout.setHorizontalSpacing(10)
            info_layout.setVerticalSpacing(8)

            if self.notification_type in ['bird', 'runway_a_risk', 'runway_b_risk']:
                info_layout.addRow("위험 등급:", QLabel(str(self.data.value)))

            main_layout.addLayout(info_layout)

        # 버튼 (중앙 정렬)
        button = QPushButton("확인")
        button.clicked.connect(self.close)
        main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def get_title(self) -> str:
        return {
            'object': '이상 객체 감지',
            'bird': '조류 충돌 위험 변화',
            'runway_a_risk': '활주로 A 위험도 변화',
            'runway_b_risk': '활주로 B 위험도 변화',
            'violation_access': '접근 위반'
        }.get(self.notification_type, '알림')

    def adjust_position(self):
        """부모 창 내부에 알림창을 상대적으로 위치시킵니다."""
        if not self.parent():
            return

        parent_widget = self.parent()
        
        # MainWindow인 경우 현재 활성 페이지를 찾아서 부모로 사용
        if hasattr(parent_widget, 'centralWidget'):
            central_widget = parent_widget.centralWidget()
            if central_widget:
                # QTabWidget이 있는 경우 현재 탭 페이지를 부모로 사용
                if hasattr(central_widget, 'currentWidget'):
                    current_page = central_widget.currentWidget()
                    if current_page:
                        parent_widget = current_page
                # 또는 QStackedWidget인 경우
                elif hasattr(central_widget, 'currentWidget'):
                    current_page = central_widget.currentWidget()
                    if current_page:
                        parent_widget = current_page
                else:
                    parent_widget = central_widget
        
        # 실제 사용할 부모 위젯의 클라이언트 영역
        parent_rect = parent_widget.rect()
        parent_width = parent_rect.width()
        parent_height = parent_rect.height()
        
        # 다이얼로그 크기
        dialog_width = self.width()
        dialog_height = self.height()
        
        # 여백
        margin = 20
        
        # 페이지 내 우하단 상대 위치 계산
        x = parent_width - dialog_width - margin
        y = parent_height - dialog_height - margin
        
        # 페이지 경계를 벗어나지 않도록 제한
        max_x = parent_width - dialog_width - margin
        max_y = parent_height - dialog_height - margin
        
        x = min(x, max_x)
        y = min(y, max_y)
        
        # 최소값 보정 (음수 방지)
        x = max(margin, x)
        y = max(margin, y)
        
        # 페이지가 너무 작은 경우 중앙 정렬
        if dialog_width + 2 * margin > parent_width or dialog_height + 2 * margin > parent_height:
            x = max(0, (parent_width - dialog_width) // 2)
            y = max(0, (parent_height - dialog_height) // 2)
        
        # 페이지 기준 글로벌 좌표 변환
        global_pos = parent_widget.mapToGlobal(parent_rect.topLeft())
        self.move(global_pos.x() + x, global_pos.y() + y)

    def mousePressEvent(self, event):
        self.close()

    def showEvent(self, event):
        """다이얼로그가 표시될 때 위치 조정"""
        super().showEvent(event)
        # 레이아웃이 완전히 적용될 때까지 잠시 기다린 후 위치 조정
        QTimer.singleShot(0, self.adjust_position)
        
    def resizeEvent(self, event):
        """다이얼로그 크기가 변경될 때 위치 재조정"""
        super().resizeEvent(event)
        if self.isVisible():
            self.adjust_position()