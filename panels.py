# C:\Users\thhan\oceanocal_v2\panels.py

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
# from .plot_manager import PlotWindow # This import is not needed here
import logging

class MainPanel(QWidget):
    def __init__(self, mainwin=None):
        super().__init__(mainwin)
        self.mainwin = mainwin
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("파일/변수")
        splitter.addWidget(self.tree_widget)

        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        splitter.addWidget(self.info_panel)

        # Revert splitter sizes for two panels (tree and info), no plot_viewer here
        splitter.setSizes([600, 1000])

        layout.addWidget(splitter)
        self.setLayout(layout)

        # 이벤트
        self.tree_widget.itemClicked.connect(self.show_variable_info)
        self.tree_widget.itemDoubleClicked.connect(self.open_plot_window)

        self.current_file = None
        self.current_dataset = None
        self.dataset_manager = None
        self.plot_handler = None

    def set_managers(self, dataset_manager, plot_handler):
        """Sets the dataset and plot managers for the panel."""
        self.dataset_manager = dataset_manager
        self.plot_handler = plot_handler

    def load_tree(self, ds, fname):
        self.tree_widget.clear()
        self.current_file = fname
        self.current_dataset = ds

        def add_items(parent, data):
            for item_data in data:
                item = QTreeWidgetItem(parent, [item_data['name']])
                if 'children' in item_data:
                    add_items(item, item_data['children'])
                if item_data.get('type') == 'variable':
                    item.setForeground(0, Qt.GlobalColor.blue)

        file_item = QTreeWidgetItem(self.tree_widget, [os.path.basename(fname)])
        if hasattr(ds, 'groups') and ds.groups:
            add_items(file_item, [{'name': g_name, 'children': self._parse_group(ds.groups[g_name])} for g_name in ds.groups])
        for var_name in ds.variables:
            add_items(file_item, [{'name': var_name, 'type': 'variable'}])

        self.tree_widget.expandToDepth(0)
        logging.info(f"파일 '{fname}'의 트리 뷰 로드 완료.")

    def _parse_group(self, group):
        children = []
        if hasattr(group, 'variables'):
            for var_name in group.variables:
                children.append({'name': var_name, 'type': 'variable'})
        if hasattr(group, 'groups'):
            for g_name in group.groups:
                children.append({'name': g_name, 'children': self._parse_group(group.groups[g_name])})
        return children

    def show_variable_info(self, item, column):
        path_list = []
        current = item
        while current:
            path_list.insert(0, current.text(0))
            current = current.parent()

        if not path_list:
            self.info_panel.setPlainText("파일 또는 변수를 선택하세요.")
            return

        if len(path_list) == 1:
            file_path = self.current_file
            if not file_path:
                self.info_panel.setPlainText("파일 정보 없음.")
                return
            try:
                ds = self.dataset_manager.open_file(file_path)
                info = f"파일: {os.path.basename(file_path)}\n"
                info += "---------------------\n"
                info += "글로벌 속성 (Global Attributes):\n"
                if hasattr(ds, 'attrs') and ds.attrs:
                    for attr, value in ds.attrs.items():
                        info += f"  {attr}: {value}\n"
                else:
                    info += "  없음\n"
                info += "\n변수 목록 (Variables):\n"
                for var_name in ds.variables:
                    try:
                        var_detail = self.dataset_manager.get_variable_info(file_path, var_name)
                        info += f"  - {var_name} (Shape: {var_detail.get('shape', 'N/A')}, DType: {var_detail.get('dtype', 'N/A')})\n"
                    except Exception as var_e:
                        info += f"  - {var_name} (정보 로드 오류: {var_e})\n"
                self.info_panel.setPlainText(info)
                logging.info(f"파일 '{os.path.basename(file_path)}' 정보 표시 완료.")
            except Exception as e:
                self.info_panel.setPlainText(f"파일 정보 로드 중 오류: {e}")
                logging.error(f"파일 '{os.path.basename(file_path)}' 정보 로드 오류: {e}", exc_info=True)
            return

        var_path = "/".join(path_list[1:])

        if not self.dataset_manager or not self.current_file:
            self.info_panel.setPlainText("데이터셋 매니저 또는 현재 파일이 설정되지 않았습니다.")
            return

        try:
            var_info = self.dataset_manager.get_variable_info(self.current_file, var_path)
            if not var_info:
                self.info_panel.setPlainText("변수 정보를 찾을 수 없습니다.")
                return

            info = f"[{var_path}] Variable Info:\n"
            info += f" - Name: {var_info.get('name', 'N/A')}\n"
            info += f" - Dimensions: {var_info.get('dimensions', 'N/A')}\n"
            info += f" - Shape: {var_info.get('shape', 'N/A')}\n"
            info += f" - Data Type: {var_info.get('dtype', 'N/A')}\n"
            if 'units' in var_info.get('attributes', {}):
                info += f" - Units: {var_info['attributes']['units']}\n"
            if 'long_name' in var_info.get('attributes', {}):
                info += f" - Long Name: {var_info['attributes']['long_name']}\n"
            info += "\nAttributes:\n"
            if var_info.get('attributes'):
                for attr, value in var_info['attributes'].items():
                    info += f"   {attr}: {value}\n"
            else:
                info += "   (No attributes)\n"

            if 'sample_data' in var_info and var_info['sample_data'] is not None:
                info += f"\nSample Data:\n{var_info['sample_data']}\n"
            else:
                info += "\nSample Data: Not available or empty.\n"

            self.info_panel.setPlainText(info)
            logging.info(f"변수 '{var_path}' 정보 표시 완료.")

        except KeyError:
            self.info_panel.setPlainText(f"오류: 변수 '{var_path}'를 찾을 수 없습니다.")
            logging.warning(f"변수 '{var_path}'를 찾을 수 없음.")
        except Exception as e:
            self.info_panel.setPlainText(f"변수 정보 로드 중 오류: {e}")
            logging.error(f"변수 '{var_path}' 정보 로드 오류: {e}", exc_info=True)

    def open_plot_window(self, item, column):
        path_list = []
        current = item
        while current:
            path_list.insert(0, current.text(0))
            current = current.parent()
        if len(path_list) < 2:
            QMessageBox.warning(self, "경고", "변수 항목을 선택해 주세요.")
            return
        var_path = "/".join(path_list[1:])
        if not self.current_file or not var_path:
            QMessageBox.warning(self, "경고", "파일 또는 변수가 선택되지 않았습니다.")
            return
        if not self.dataset_manager or not self.plot_handler:
            QMessageBox.critical(self, "초기화 오류", "Dataset Manager 또는 Plot Handler가 초기화되지 않았습니다.")
            return

        self.plot_handler.request_plot(self.current_file, var_path)