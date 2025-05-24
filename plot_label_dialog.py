# oceanocal_v2/plot_label_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QColorDialog, QFontDialog, QGroupBox, QGridLayout, QComboBox, QDoubleSpinBox,
    QMessageBox
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
import logging

class PlotLabelDialog(QDialog):
    def __init__(self, parent=None, current_options=None, settings_manager=None):
        super().__init__(parent)
        self.setWindowTitle("플롯 옵션 설정")
        self.setGeometry(100, 100, 500, 400)
        self.current_options = current_options if current_options is not None else {}
        self.settings_manager = settings_manager
        self.init_ui()
        self.load_current_options()
        logging.info("PlotLabelDialog 초기화.")

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Title and Labels Group
        labels_group = QGroupBox("제목 및 축 레이블")
        labels_layout = QGridLayout()
        labels_layout.addWidget(QLabel("제목:"), 0, 0)
        self.title_edit = QLineEdit()
        labels_layout.addWidget(self.title_edit, 0, 1)

        labels_layout.addWidget(QLabel("X축 레이블:"), 1, 0)
        self.xaxis_label_edit = QLineEdit()
        labels_layout.addWidget(self.xaxis_label_edit, 1, 1)

        labels_layout.addWidget(QLabel("Y축 레이블:"), 2, 0)
        self.yaxis_label_edit = QLineEdit()
        labels_layout.addWidget(self.yaxis_label_edit, 2, 1)

        labels_layout.addWidget(QLabel("컬러바 레이블:"), 3, 0)
        self.cbar_label_edit = QLineEdit()
        labels_layout.addWidget(self.cbar_label_edit, 3, 1)
        labels_group.setLayout(labels_layout)
        main_layout.addWidget(labels_group)

        # Font Settings Group
        font_group = QGroupBox("글꼴 설정")
        font_layout = QGridLayout()
        font_layout.addWidget(QLabel("전체 글꼴:"), 0, 0)
        self.font_button = QPushButton("글꼴 선택...")
        self.font_button.clicked.connect(self._select_font)
        font_layout.addWidget(self.font_button, 0, 1)
        font_group.setLayout(font_layout)
        main_layout.addWidget(font_group)

        # Colorbar and Theme Settings Group
        style_group = QGroupBox("스타일 설정")
        style_layout = QGridLayout()

        style_layout.addWidget(QLabel("컬러맵:"), 0, 0)
        self.cmap_combo = QComboBox()
        self._populate_colormaps()
        style_layout.addWidget(self.cmap_combo, 0, 1)

        style_layout.addWidget(QLabel("테마:"), 1, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        style_layout.addWidget(self.theme_combo, 1, 1)

        style_group.setLayout(style_layout)
        main_layout.addWidget(style_group)

        # Buttons
        button_box = QHBoxLayout()
        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        button_box.addStretch(1)
        button_box.addWidget(self.ok_button)
        button_box.addWidget(self.cancel_button)
        main_layout.addLayout(button_box)

    def _populate_colormaps(self):
        # List .pal files in resources/colorbars
        colorbar_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "colorbars")
        if os.path.exists(colorbar_dir):
            colormaps = [f.split('.')[0] for f in os.listdir(colorbar_dir) if f.endswith('.pal')]
            self.cmap_combo.addItems(sorted(colormaps))
        else:
            self.cmap_combo.addItems(["jet", "viridis", "plasma", "inferno", "magma", "cividis"]) # Fallback
            logging.warning(f"컬러바 디렉토리를 찾을 수 없습니다: {colorbar_dir}. 기본 컬러맵 사용.")

    def _select_font(self):
        initial_font = QFont(self.current_options.get('plot_font_family', 'Arial'),
                             self.current_options.get('plot_font_size', 12))
        font, ok = QFontDialog.getFont(initial_font, self)
        if ok:
            self.current_options['plot_font_family'] = font.family()
            self.current_options['plot_font_size'] = font.pointSize()
            logging.info(f"글꼴 선택됨: {font.family()}, {font.pointSize()}")

    def load_current_options(self):
        self.title_edit.setText(self.current_options.get('title_text', ''))
        self.xaxis_label_edit.setText(self.current_options.get('xaxis_label', ''))
        self.yaxis_label_edit.setText(self.current_options.get('yaxis_label', ''))
        self.cbar_label_edit.setText(self.current_options.get('cbar_label', ''))

        cmap_name = self.current_options.get('cmap', 'jet')
        index = self.cmap_combo.findText(cmap_name, Qt.MatchFlag.MatchExactly)
        if index != -1:
            self.cmap_combo.setCurrentIndex(index)

        theme_name = self.current_options.get('theme', 'Light') # Plotly theme, not app theme
        index = self.theme_combo.findText(theme_name, Qt.MatchFlag.MatchExactly)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)

    def get_options(self):
        # Get options from dialog and return
        options = {
            'title_text': self.title_edit.text(),
            'xaxis_label': self.xaxis_label_edit.text(),
            'yaxis_label': self.yaxis_label_edit.text(),
            'cbar_label': self.cbar_label_edit.text(),
            'cmap': self.cmap_combo.currentText(),
            'theme': self.theme_combo.currentText(),
            # Font settings are updated directly in self.current_options by _select_font
            'plot_font_family': self.current_options.get('plot_font_family', 'Arial'),
            'plot_font_size': self.current_options.get('plot_font_size', 12)
        }
        logging.debug(f"Plot options retrieved from dialog: {options}")
        return options