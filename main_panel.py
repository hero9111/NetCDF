import logging
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QFileDialog, QSplitter
)
from PyQt6.QtCore import Qt

# 필요한 매니저 클래스 임포트 확인 (상대 경로가 맞는지 중요)
from .dataset_manager import DatasetManager
from .handlers.plot_handler import PlotHandler
from .plot_window_manager import PlotWindowManager
from .settings_manager import SettingsManager

logger = logging.getLogger(__name__)

class MainPanel(QWidget):
    def __init__(self, parent=None,
                 dataset_manager=None,
                 plot_handler=None,
                 plot_manager=None,
                 settings_manager=None,
                 update_status_bar_callback=None):
        super().__init__(parent)

        self.dataset_manager = dataset_manager
        self.plot_handler = plot_handler
        self.plot_manager = plot_manager
        self.settings_manager = settings_manager
        self.update_status_bar_callback = update_status_bar_callback

        self._setup_ui()
        self._connect_signals()

        logger.info("MainPanel 초기화 완료.")

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["파일/변수"])
        main_splitter.addWidget(self.tree_widget)

        self.info_text_edit = QTextEdit("파일을 열어 데이터를 확인하세요.")
        self.info_text_edit.setReadOnly(True)
        
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(self.info_text_edit)

        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_panel_layout)
        main_splitter.addWidget(right_panel_widget)

        if self.parent():
            parent_width = self.parent().width()
            main_splitter.setSizes([int(parent_width * 0.3), int(parent_width * 0.7)])
        else:
            main_splitter.setSizes([300, 700])

        layout = QVBoxLayout(self)
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        logger.info("MainPanel UI 설정 완료.")

    def _connect_signals(self):
        self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        logger.info("MainPanel 시그널 연결 완료.")

    def _on_tree_item_clicked(self, item, column):
        """
        트리 위젯의 아이템이 클릭될 때 해당 항목의 정보를 info_text_edit에 표시합니다.
        """
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        item_value = item.text(0)
        
        info_str = f"선택된 항목: {item_value}\n유형: {item_type}\n\n"

        current_file_path = self.dataset_manager.get_current_file_path()
        dataset = self.dataset_manager.get_dataset(current_file_path)

        if dataset:
            if item_type == "file":
                info_str += "--- 파일 전역 속성 ---\n"
                for attr, val in dataset.attrs.items():
                    if attr != 'filepath':
                        info_str += f"{attr}: {val}\n"
            elif item_type == "dimension":
                dim_name = item_value.split(':')[0].strip()
                info_str += f"차원 크기: {dataset.dims.get(dim_name, 'N/A')}\n"
            elif item_type == "coordinate" or item_type == "data_variable":
                var_name = item_value
                if var_name in dataset.coords or var_name in dataset.data_vars:
                    variable = dataset[var_name]
                    info_str += f"데이터 타입: {variable.dtype}\n"
                    info_str += f"크기: {variable.shape}\n"
                    info_str += f"차원: {list(variable.dims)}\n\n"
                    info_str += "--- 속성 ---\n"
                    for attr, val in variable.attrs.items():
                        info_str += f"{attr}: {val}\n"
                else:
                    info_str += "변수 정보를 찾을 수 없습니다.\n"
            elif item_type == "attribute":
                info_str += f"속성 값: {item_value}\n"
            else:
                info_str += "알 수 없는 항목 유형.\n"
        else:
            info_str += "현재 로드된 데이터셋이 없습니다."

        self.info_text_edit.setText(info_str)

    def load_file_into_tree(self, file_path):
        """
        주어진 파일 경로의 데이터를 로드하여 트리 위젯에 표시합니다.
        """
        if self.dataset_manager:
            try:
                self.dataset_manager.open_file(file_path) # 'load_file'을 'open_file'로 변경
                self._update_tree_widget()
                if self.update_status_bar_callback:
                    self.update_status_bar_callback(f"'{os.path.basename(file_path)}' 로드 완료.", 2000)
                logger.info(f"파일 '{file_path}' 트리 위젯에 로드 완료.")
            except Exception as e:
                QMessageBox.critical(self, "파일 로드 오류", f"파일을 로드할 수 없습니다: {e}")
                if self.update_status_bar_callback:
                    self.update_status_bar_callback(f"파일 로드 오류: {e}", 5000)
                logger.error(f"파일 '{file_path}' 로드 중 오류 발생: {e}")
        else:
            logger.warning("DatasetManager가 MainPanel에 설정되지 않았습니다.")
            QMessageBox.warning(self, "오류", "데이터셋 매니저가 초기화되지 않았습니다. 애플리케이션 설정을 확인하세요.")

    def _update_tree_widget(self):
        """
        DatasetManager에서 현재 활성화된 데이터를 기반으로 트리 위젯을 업데이트하고
        각 아이템에 사용자 정의 데이터(타입)를 저장합니다.
        """
        self.tree_widget.clear()
        self.info_text_edit.clear()

        current_file_path = self.dataset_manager.get_current_file_path()
        dataset = self.dataset_manager.get_dataset(current_file_path)

        if dataset:
            file_name = os.path.basename(current_file_path if current_file_path else 'Unknown File')
            file_item = QTreeWidgetItem(self.tree_widget, [file_name])
            file_item.setData(0, Qt.ItemDataRole.UserRole, "file")
            file_item.setExpanded(True)

            # Dimensions
            dims_item = QTreeWidgetItem(file_item, ["Dimensions"])
            for dim, size in dataset.dims.items():
                dim_sub_item = QTreeWidgetItem(dims_item, [f"{dim}: {size}"])
                dim_sub_item.setData(0, Qt.ItemDataRole.UserRole, "dimension")
            dims_item.setExpanded(True)

            # Coordinates
            coords_item = QTreeWidgetItem(file_item, ["Coordinates"])
            for coord in dataset.coords:
                var_item = QTreeWidgetItem(coords_item, [coord])
                var_item.setData(0, Qt.ItemDataRole.UserRole, "coordinate")
                attrs_item = QTreeWidgetItem(var_item, ["Attributes"])
                for attr, value in dataset[coord].attrs.items():
                    attr_sub_item = QTreeWidgetItem(attrs_item, [f"{attr}: {value}"])
                    attr_sub_item.setData(0, Qt.ItemDataRole.UserRole, "attribute")
                attrs_item.setExpanded(False)
            coords_item.setExpanded(True)

            # Data Variables
            data_vars_item = QTreeWidgetItem(file_item, ["Data Variables"])
            for var in dataset.data_vars:
                var_item = QTreeWidgetItem(data_vars_item, [var])
                var_item.setData(0, Qt.ItemDataRole.UserRole, "data_variable")
                attrs_item = QTreeWidgetItem(var_item, ["Attributes"])
                for attr, value in dataset[var].attrs.items():
                    attr_sub_item = QTreeWidgetItem(attrs_item, [f"{attr}: {value}"])
                    attr_sub_item.setData(0, Qt.ItemDataRole.UserRole, "attribute")
                attrs_item.setExpanded(False)
            data_vars_item.setExpanded(True)

            # Global Attributes
            global_attrs_item = QTreeWidgetItem(file_item, ["Global Attributes"])
            for attr, value in dataset.attrs.items():
                if attr != 'filepath':
                    attr_sub_item = QTreeWidgetItem(global_attrs_item, [f"{attr}: {value}"])
                    attr_sub_item.setData(0, Qt.ItemDataRole.UserRole, "attribute")
            global_attrs_item.setExpanded(True)
        logger.info("트리 위젯 업데이트 완료.")

    def close_current_file(self):
        """
        현재 로드된 파일을 닫고 트리 위젯을 비웁니다.
        """
        if self.dataset_manager:
            current_file_path = self.dataset_manager.get_current_file_path()
            if current_file_path:
                self.dataset_manager.close_file(current_file_path)
                self.tree_widget.clear()
                self.info_text_edit.clear()
                if self.update_status_bar_callback:
                    self.update_status_bar_callback("파일 닫힘.", 2000)
                logger.info("현재 파일 닫힘.")
            else:
                logger.info("닫을 파일이 없습니다.")
                if self.update_status_bar_callback:
                    self.update_status_bar_callback("닫을 파일이 없습니다.", 2000)
        else:
            logger.warning("DatasetManager가 MainPanel에 설정되지 않았습니다.")

    def open_plot_window(self):
        """
        선택된 데이터 변수에 대해 플롯 창을 열도록 plot_handler에 요청합니다.
        """
        if self.plot_handler and self.dataset_manager:
            selected_item = self.tree_widget.currentItem()
            if selected_item:
                item_type = selected_item.data(0, Qt.ItemDataRole.UserRole)
                if item_type == "data_variable":
                    variable_name = selected_item.text(0)
                    
                    current_file_path = self.dataset_manager.get_current_file_path()
                    dataset = self.dataset_manager.get_dataset(current_file_path)

                    if dataset and (variable_name in dataset.data_vars or variable_name in dataset.coords):
                        self.plot_handler.create_or_update_plot_window(current_file_path, variable_name) # 파일 경로도 함께 전달
                        if self.update_status_bar_callback:
                            self.update_status_bar_callback(f"'{variable_name}' 플롯 생성 요청.", 2000)
                        logger.info(f"플롯 요청: {variable_name} from {current_file_path}")
                    else:
                        QMessageBox.warning(self, "플롯 오류", f"선택된 '{variable_name}'는 데이터 변수가 아니거나 데이터셋에서 찾을 수 없습니다.")
                        logger.warning(f"플롯 오류: '{variable_name}'는 데이터 변수가 아니거나 찾을 수 없음.")
                else:
                    QMessageBox.warning(self, "플롯 오류", "데이터 변수를 선택해야 합니다.")
                    logger.warning("플롯 오류: 데이터 변수 선택 안됨.")
            else:
                QMessageBox.warning(self, "플롯 오류", "플롯할 변수를 선택해주세요.")
                logger.warning("플롯 오류: 변수 선택 안됨.")
        else:
            logger.warning("PlotHandler 또는 DatasetManager가 MainPanel에 설정되지 않았거나 데이터셋이 로드되지 않았습니다.")
            QMessageBox.warning(self, "오류", "플롯을 위한 준비가 완료되지 않았습니다. 데이터를 로드했는지 확인하세요.")

    def add_data(self):
        """
        데이터 추가 기능을 위한 플레이스홀더 메소드.
        MainWindow의 add_data_action에 연결됩니다.
        """
        QMessageBox.information(self, "기능 미구현", "데이터 추가 기능은 아직 구현되지 않았습니다.")
        logger.info("MainPanel: 데이터 추가 기능 호출 (미구현).")

    def export_data(self):
        """
        데이터 내보내기 기능을 위한 플레이스홀더 메소드.
        MainWindow의 export_action에 연결됩니다.
        """
        QMessageBox.information(self, "기능 미구현", "데이터 내보내기 기능은 아직 구현되지 않았습니다.")
        logger.info("MainPanel: 데이터 내보내기 기능 호출 (미구현).")

    def refresh_plot(self):
        """
        플롯 새로고침 기능을 위한 플레이스홀더 메소드.
        MainWindow의 refresh_plot_action에 연결됩니다.
        실제 플롯 새로고침 로직은 plot_handler를 통해 구현될 수 있습니다.
        """
        if self.plot_handler:
            self.plot_handler.refresh_active_plot()
            if self.update_status_bar_callback:
                self.update_status_bar_callback("플롯 새로고침 완료.", 2000)
            logger.info("MainPanel: 플롯 새로고침.")
        else:
            logger.warning("MainPanel: PlotHandler가 설정되지 않았습니다.")