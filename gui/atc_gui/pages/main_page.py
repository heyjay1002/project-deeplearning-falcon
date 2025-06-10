from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QSizePolicy
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os
from pages.object_detail_dialog import ObjectDetailDialog
from models.sample_object_data import sample_object_data
from widgets.marker_overlay_widget import MarkerOverlayWidget

class MainPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), '../ui/main_page.ui')
        uic.loadUi(ui_path, self)

        # 이미지 경로
        base_dir = os.path.dirname(__file__)
        self.map_path = os.path.join(base_dir, '../resources/images/map.png')
        self.marker_icon_path = os.path.join(base_dir, '../resources/images/bird.png')
        self.cctv_path = os.path.join(base_dir, '../resources/images/cctv_sample.png')

        # 원본 이미지 저장
        self.map_pixmap = QPixmap(self.map_path)
        self.cctv_pixmap = QPixmap(self.cctv_path)
        
        # # CCTV 레이블 크기 정책 설정
        # for label in [self.label_map, self.label_cctv_1, self.label_cctv_2, self.label_cctv_3]:
        #     label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #     label.setMinimumSize(600, 400)  # 최소 크기 설정
        #     label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 초기 이미지 설정
        self.update_images()

        # 샘플 데이터 테이블에 추가
        self.table_object_list.setRowCount(len(sample_object_data))
        for row, obj in enumerate(sample_object_data):
            self.table_object_list.setItem(row, 0, QTableWidgetItem(obj['id']))
            self.table_object_list.setItem(row, 1, QTableWidgetItem(obj['location']))
            self.table_object_list.setItem(row, 2, QTableWidgetItem(obj['type']))

        self.table_object_list.setSelectionBehavior(self.table_object_list.SelectionBehavior.SelectRows)

        # 마커 오버레이 연동
        self.marker_overlay = MarkerOverlayWidget(self.map_overlay_frame)
        layout = self.map_overlay_frame.layout()
        idx = layout.indexOf(self.marker_overlay_placeholder)
        layout.removeWidget(self.marker_overlay_placeholder)
        self.marker_overlay_placeholder.deleteLater()
        layout.addWidget(self.marker_overlay, 0, 0)  # row 0, column 0에 추가

        # 마커 추가
        self.marker_overlay.add_marker(400, 200, self.marker_icon_path, 0, self.select_table_row)

        # 지도/영상 전환 버튼 연결
        self.btn_show_map.clicked.connect(self.show_map)
        self.btn_show_cctv.clicked.connect(self.show_cctv)

        # 상세보기 페이지: ObjectDetailDialog 동적 추가
        self.object_detail_dialog = ObjectDetailDialog(self)
        self.object_area.addWidget(self.object_detail_dialog)
        self.btn_detail.clicked.connect(self.show_detail)
        self.object_detail_dialog.btn_back.clicked.connect(self.show_table)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_images()

    def update_images(self):
        # 지도 이미지 업데이트
        if not self.map_pixmap.isNull():
            self.label_map.setPixmap(self.map_pixmap.scaled(
                self.label_map.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        # CCTV 이미지 업데이트 (CCTV 1에만 샘플 이미지 표시)
        if not self.cctv_pixmap.isNull():
            # CCTV 1에만 샘플 이미지 표시
            self.label_cctv_1.setPixmap(self.cctv_pixmap.scaled(
                self.label_map.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

            # CCTV 2, 3는 비워둠
            self.label_cctv_2.clear()
            self.label_cctv_3.clear()

    def select_table_row(self, row_idx):
        self.table_object_list.selectRow(row_idx)

    def show_map(self):
        self.map_cctv_stack.setCurrentIndex(0)

    def show_cctv(self):
        idx = self.combo_cctv.currentIndex()
        self.map_cctv_stack.setCurrentIndex(idx + 1)

    def show_table(self):
        self.object_area.setCurrentIndex(0)

    def show_detail(self):
        row = self.table_object_list.currentRow()
        if row < 0:
            return
        id_ = self.table_object_list.item(row, 0).text()
        loc = self.table_object_list.item(row, 1).text()
        kind = self.table_object_list.item(row, 2).text()
        # 예시 정보
        info = f"객체 ID : {id_}\n종류 : {kind}\n위치 : {loc}\n발견 시각 : 2025-02-23 18:00:00"
        self.object_detail_dialog.detail_info.setText(info)
        detail_img_path = os.path.join(os.path.dirname(__file__), '../resources/images/bird.png')
        self.object_detail_dialog.detail_img.setPixmap(
            QPixmap(detail_img_path).scaled(
                self.object_detail_dialog.detail_img.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        self.object_area.setCurrentIndex(2)