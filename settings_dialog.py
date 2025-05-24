# oceanocal_v2/settings_dialog.py

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QGridLayout, QLabel, QLineEdit, QPushButton,
    QColorDialog, QFontDialog, QComboBox, QCheckBox, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
import logging

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(100, 100, 600, 500)
        self.settings_manager = settings_manager
        self._temp_plot_options = self.settings_manager.get_default_plot_options().copy() # Copy for temporary edits
        self.init_ui()
        self.load_settings_to_ui()
        logging.info("SettingsDialog 초기화.")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        # General Tab
        self.general_tab = QWidget()
        self._setup_general_tab()
        self.tab_widget.addTab(self.general_tab, "일반")

        # Plot Tab
        self.plot_tab = QWidget()
        self._setup_plot_tab()
        self.tab_widget.addTab(self.plot_tab, "플롯")

        # Overlay Tab
        self.overlay_tab = QWidget()
        self._setup_overlay_tab()
        self.tab_widget.addTab(self.overlay_tab, "오버레이")

        main_layout.addWidget(self.tab_widget)

        # Buttons
        button_box = QHBoxLayout()
        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.accept_settings)
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        button_box.addStretch(1)
        button_box.addWidget(self.ok_button)
        button_box.addWidget(self.cancel_button)
        main_layout.addLayout(button_box)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        general_group = QGroupBox("애플리케이션 테마")
        general_layout = QGridLayout()

        general_layout.addWidget(QLabel("테마:"), 0, 0)
        self.app_theme_combo = QComboBox()
        self.app_theme_combo.addItems(["light", "dark", "fusion"]) # 'fusion' is a Qt style
        general_layout.addWidget(self.app_theme_combo, 0, 1)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        layout.addStretch(1)

    def _setup_plot_tab(self):
        layout = QVBoxLayout(self.plot_tab)

        # Labels Group
        labels_group = QGroupBox("기본 제목 및 축 레이블")
        labels_layout = QGridLayout()
        labels_layout.addWidget(QLabel("제목:"), 0, 0)
        self.default_title_edit = QLineEdit()
        labels_layout.addWidget(self.default_title_edit, 0, 1)

        labels_layout.addWidget(QLabel("X축 레이블:"), 1, 0)
        self.default_xaxis_label_edit = QLineEdit()
        labels_layout.addWidget(self.default_xaxis_label_edit, 1, 1)

        labels_layout.addWidget(QLabel("Y축 레이블:"), 2, 0)
        self.default_yaxis_label_edit = QLineEdit()
        labels_layout.addWidget(self.default_yaxis_label_edit, 2, 1)

        labels_layout.addWidget(QLabel("컬러바 레이블:"), 3, 0)
        self.default_cbar_label_edit = QLineEdit()
        labels_layout.addWidget(self.default_cbar_label_edit, 3, 1)
        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)

        # Font Settings Group
        font_group = QGroupBox("기본 글꼴 설정")
        font_layout = QGridLayout()
        font_layout.addWidget(QLabel("플롯 글꼴:"), 0, 0)
        self.default_font_button = QPushButton("글꼴 선택...")
        self.default_font_button.clicked.connect(self._select_default_font)
        font_layout.addWidget(self.default_font_button, 0, 1)
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Colorbar and Theme Settings Group
        style_group = QGroupBox("기본 스타일 설정")
        style_layout = QGridLayout()

        style_layout.addWidget(QLabel("컬러맵:"), 0, 0)
        self.default_cmap_combo = QComboBox()
        self._populate_colormaps(self.default_cmap_combo)
        style_layout.addWidget(self.default_cmap_combo, 0, 1)

        style_layout.addWidget(QLabel("플롯 테마:"), 1, 0) # This is for Plotly theme (light/dark)
        self.default_plotly_theme_combo = QComboBox()
        self.default_plotly_theme_combo.addItems(["Light", "Dark"]) # Plotly templates
        style_layout.addWidget(self.default_plotly_theme_combo, 1, 1)

        style_group.setLayout(style_layout)
        layout.addWidget(style_group)

        layout.addStretch(1)

    def _setup_overlay_tab(self):
        layout = QVBoxLayout(self.overlay_tab)
        overlay_group = QGroupBox("맵 오버레이 파일")
        overlay_layout = QVBoxLayout()

        self.overlay_list_widget = QListWidget()
        self.overlay_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        overlay_layout.addWidget(self.overlay_list_widget)

        overlay_buttons_layout = QHBoxLayout()
        self.add_overlay_button = QPushButton("오버레이 추가...")
        self.add_overlay_button.clicked.connect(self._add_overlay_file)
        self.remove_overlay_button = QPushButton("선택 항목 제거")
        self.remove_overlay_button.clicked.connect(self._remove_selected_overlays)

        overlay_buttons_layout.addWidget(self.add_overlay_button)
        overlay_buttons_layout.addWidget(self.remove_overlay_button)
        overlay_layout.addLayout(overlay_buttons_layout)

        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)
        layout.addStretch(1)

    def _populate_colormaps(self, combo_box):
        colorbar_dir = os.path.join(self.settings_manager.BASE_DIR, "resources", "colorbars")
        if os.path.exists(colorbar_dir):
            colormaps = [f.split('.')[0] for f in os.listdir(colorbar_dir) if f.endswith('.pal')]
            combo_box.addItems(sorted(colormaps))
        else:
            combo_box.addItems(["jet", "viridis", "plasma", "inferno", "magma", "cividis"]) # Fallback
            logging.warning(f"컬러바 디렉토리를 찾을 수 없습니다: {colorbar_dir}. 기본 컬러맵 사용.")

    def _select_default_font(self):
        initial_font = QFont(self._temp_plot_options.get('plot_font_family', 'Arial'),
                             self._temp_plot_options.get('plot_font_size', 12))
        font, ok = QFontDialog.getFont(initial_font, self)
        if ok:
            self._temp_plot_options['plot_font_family'] = font.family()
            self._temp_plot_options['plot_font_size'] = font.pointSize()
            logging.info(f"기본 플롯 글꼴 선택됨: {font.family()}, {font.pointSize()}")

    def _add_overlay_file(self):
        overlay_dir = os.path.join(self.settings_manager.BASE_DIR, "resources", "overlays")
        os.makedirs(overlay_dir, exist_ok=True) # Ensure directory exists

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "오버레이 파일 추가", overlay_dir, "GeoJSON Files (*.geojson *.json);;ASCII/CSV Files (*.txt *.csv);;All Files (*)"
        )
        if file_paths:
            added_count = 0
            for src_path in file_paths:
                file_name = os.path.basename(src_path)
                dest_path = os.path.join(overlay_dir, file_name)
                try:
                    # Copy file to resources/overlays if it's not already there
                    if not os.path.exists(dest_path) or os.path.samefile(src_path, dest_path):
                        # If file already exists at destination, skip copy unless it's the same file
                        if not os.path.exists(dest_path):
                            import shutil
                            shutil.copy2(src_path, dest_path)
                            logging.info(f"오버레이 파일 복사됨: {src_path} -> {dest_path}")
                        else:
                            logging.info(f"오버레이 파일 이미 존재: {file_name}")

                        # Add to list widget if not already present
                        found = False
                        for i in range(self.overlay_list_widget.count()):
                            if self.overlay_list_widget.item(i).text() == file_name:
                                found = True
                                break
                        if not found:
                            item = QListWidgetItem(file_name)
                            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            item.setCheckState(Qt.CheckState.Unchecked) # Start unchecked by default
                            self.overlay_list_widget.addItem(item)
                            added_count += 1
                    else:
                        QMessageBox.warning(self, "파일 복사 오류", f"'{file_name}' 이름의 파일이 이미 오버레이 폴더에 있지만 다른 파일입니다. 이름을 변경하거나 기존 파일을 제거하십시오.")

                except Exception as e:
                    QMessageBox.warning(self, "파일 복사 오류", f"오버레이 파일 '{file_name}'을(를) 복사하는 중 오류 발생: {e}")
                    logging.error(f"오버레이 파일 복사 오류: {e}", exc_info=True)
            if added_count > 0:
                QMessageBox.information(self, "오버레이 추가", f"{added_count}개의 오버레이 파일이 추가되었습니다.")
            logging.info(f"{added_count}개의 오버레이 파일이 추가됨.")

    def _remove_selected_overlays(self):
        items_to_remove = self.overlay_list_widget.selectedItems()
        if not items_to_remove:
            QMessageBox.warning(self, "오버레이 제거", "제거할 오버레이를 선택해주세요.")
            return

        reply = QMessageBox.question(self, "오버레이 제거 확인",
                                     f"선택한 {len(items_to_remove)}개의 오버레이 파일을 제거하시겠습니까? (파일은 디스크에서 삭제되지 않습니다.)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for item in items_to_remove:
                row = self.overlay_list_widget.row(item)
                self.overlay_list_widget.takeItem(row)
                logging.info(f"오버레이 '{item.text()}' 목록에서 제거됨.")
            QMessageBox.information(self, "오버레이 제거", "선택한 오버레이가 목록에서 제거되었습니다.")

    def load_settings_to_ui(self):
        # General Tab
        app_theme = self.settings_manager.get_app_setting('theme', 'light')
        index = self.app_theme_combo.findText(app_theme, Qt.MatchFlag.MatchExactly)
        if index != -1:
            self.app_theme_combo.setCurrentIndex(index)

        # Plot Tab
        self.default_title_edit.setText(self._temp_plot_options.get('title_text', ''))
        self.default_xaxis_label_edit.setText(self._temp_plot_options.get('xaxis_label', ''))
        self.default_yaxis_label_edit.setText(self._temp_plot_options.get('yaxis_label', ''))
        self.default_cbar_label_edit.setText(self._temp_plot_options.get('cbar_label', ''))

        cmap_name = self._temp_plot_options.get('cmap', 'jet')
        index = self.default_cmap_combo.findText(cmap_name, Qt.MatchFlag.MatchExactly)
        if index != -1:
            self.default_cmap_combo.setCurrentIndex(index)

        plotly_theme = self._temp_plot_options.get('theme', 'Light')
        index = self.default_plotly_theme_combo.findText(plotly_theme, Qt.MatchFlag.MatchExactly)
        if index != -1:
            self.default_plotly_theme_combo.setCurrentIndex(index)

        # Overlay Tab
        overlay_dir = os.path.join(self.settings_manager.BASE_DIR, "resources", "overlays")
        if os.path.exists(overlay_dir):
            available_overlays = [f for f in os.listdir(overlay_dir) if f.endswith(('.geojson', '.json', '.txt', '.csv'))]
            active_overlays = self.settings_manager.get_active_overlays()
            for overlay_name in available_overlays:
                item = QListWidgetItem(overlay_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if overlay_name in active_overlays:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.overlay_list_widget.addItem(item)
        logging.info("UI에 설정 로드 완료.")

    def accept_settings(self):
        # General Tab
        self.settings_manager.save_app_setting('theme', self.app_theme_combo.currentText())

        # Plot Tab
        self.settings_manager.save_plot_option('title_text', self.default_title_edit.text())
        self.settings_manager.save_plot_option('xaxis_label', self.default_xaxis_label_edit.text())
        self.settings_manager.save_plot_option('yaxis_label', self.default_yaxis_label_edit.text())
        self.settings_manager.save_plot_option('cbar_label', self.default_cbar_label_edit.text())
        self.settings_manager.save_plot_option('cmap', self.default_cmap_combo.currentText())
        self.settings_manager.save_plot_option('theme', self.default_plotly_theme_combo.currentText())
        self.settings_manager.save_plot_option('plot_font_family', self._temp_plot_options.get('plot_font_family', 'Arial'))
        self.settings_manager.save_plot_option('plot_font_size', self._temp_plot_options.get('plot_font_size', 12))

        # Overlay Tab
        active_overlays = []
        for i in range(self.overlay_list_widget.count()):
            item = self.overlay_list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                active_overlays.append(item.text())
        self.settings_manager.set_active_overlays(active_overlays)

        self.accept()
        logging.info("설정 저장 및 다이얼로그 닫힘.")