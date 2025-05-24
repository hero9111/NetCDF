# plot_option_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton

class PlotOptionDialog(QDialog):
    def __init__(self, current_title, current_xlabel, current_ylabel, current_fontsize, colorbar_list, current_palette, parent=None):
        super().__init__(parent)
        self.setWindowTitle("플롯 옵션")
        layout = QVBoxLayout(self)

        # 제목
        hl_title = QHBoxLayout()
        hl_title.addWidget(QLabel("제목:"))
        self.title_edit = QLineEdit(current_title)
        hl_title.addWidget(self.title_edit)
        layout.addLayout(hl_title)

        # x/y 라벨
        hl_x = QHBoxLayout()
        hl_x.addWidget(QLabel("X축 라벨:"))
        self.xlabel_edit = QLineEdit(current_xlabel)
        hl_x.addWidget(self.xlabel_edit)
        layout.addLayout(hl_x)

        hl_y = QHBoxLayout()
        hl_y.addWidget(QLabel("Y축 라벨:"))
        self.ylabel_edit = QLineEdit(current_ylabel)
        hl_y.addWidget(self.ylabel_edit)
        layout.addWidget(self.ylabel_edit)
        layout.addLayout(hl_y)

        # 폰트 크기
        hl_font = QHBoxLayout()
        hl_font.addWidget(QLabel("폰트 크기:"))
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(6, 32)
        self.fontsize_spin.setValue(current_fontsize)
        hl_font.addWidget(self.fontsize_spin)
        layout.addLayout(hl_font)

        # 컬러바(팔레트) 선택
        hl_palette = QHBoxLayout()
        hl_palette.addWidget(QLabel("컬러바:"))
        self.palette_combo = QComboBox()
        self.palette_combo.addItems(colorbar_list)
        idx = colorbar_list.index(current_palette) if current_palette in colorbar_list else 0
        self.palette_combo.setCurrentIndex(idx)
        hl_palette.addWidget(self.palette_combo)
        layout.addLayout(hl_palette)

        # 확인/취소 버튼
        hl_btn = QHBoxLayout()
        ok_btn = QPushButton("확인")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        hl_btn.addWidget(ok_btn)
        hl_btn.addWidget(cancel_btn)
        layout.addLayout(hl_btn)

    def get_options(self):
        return {
            "title": self.title_edit.text(),
            "xlabel": self.xlabel_edit.text(),
            "ylabel": self.ylabel_edit.text(),
            "fontsize": self.fontsize_spin.value(),
            "palette": self.palette_combo.currentText()
        }
