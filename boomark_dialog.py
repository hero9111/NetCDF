# oceanocal_v2/bookmark_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QMessageBox, QLabel)
from PyQt6.QtCore import Qt
import os

class BookmarkDialog(QDialog):
    def __init__(self, parent=None, bookmark_manager=None):
        super().__init__(parent)
        self.setWindowTitle("북마크 관리")
        self.setMinimumSize(400, 300)
        self.bookmark_manager = bookmark_manager
        self.selected_file = None # 선택된 파일 경로를 반환하기 위함

        main_layout = QVBoxLayout(self)

        main_layout.addWidget(QLabel("저장된 북마크:"))
        self.bookmark_list_widget = QListWidget()
        self.load_bookmarks()
        main_layout.addWidget(self.bookmark_list_widget)

        button_layout = QHBoxLayout()
        self.open_button = QPushButton("열기")
        self.open_button.clicked.connect(self.open_selected_bookmark)
        self.open_button.setEnabled(False) # 처음에는 비활성화

        self.remove_button = QPushButton("삭제")
        self.remove_button.clicked.connect(self.remove_selected_bookmark)
        self.remove_button.setEnabled(False) # 처음에는 비활성화

        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.close)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        self.bookmark_list_widget.itemSelectionChanged.connect(self.update_button_states)
        self.bookmark_list_widget.itemDoubleClicked.connect(self.open_selected_bookmark)

    def load_bookmarks(self):
        self.bookmark_list_widget.clear()
        if self.bookmark_manager:
            for bookmark in self.bookmark_manager.get_all():
                item = QListWidgetItem(os.path.basename(bookmark))
                item.setData(Qt.ItemDataRole.UserRole, bookmark) # 실제 경로를 UserRole에 저장
                self.bookmark_list_widget.addItem(item)
        self.update_button_states()

    def update_button_states(self):
        has_selection = self.bookmark_list_widget.currentItem() is not None
        self.open_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def open_selected_bookmark(self):
        selected_item = self.bookmark_list_widget.currentItem()
        if selected_item:
            self.selected_file = selected_item.data(Qt.ItemDataRole.UserRole)
            if not os.path.exists(self.selected_file):
                QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다: {self.selected_file}\n북마크에서 제거합니다.")
                self.bookmark_manager.remove(self.selected_file)
                self.load_bookmarks()
                self.selected_file = None # 선택 초기화
            else:
                self.accept() # 다이얼로그 닫고 선택된 파일 반환

    def remove_selected_bookmark(self):
        selected_item = self.bookmark_list_widget.currentItem()
        if selected_item:
            filepath = selected_item.data(Qt.ItemDataRole.UserRole)
            if QMessageBox.question(self, "북마크 삭제", f"'{os.path.basename(filepath)}' 북마크를 삭제하시겠습니까?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.bookmark_manager.remove(filepath)
                self.load_bookmarks()
                QMessageBox.information(self, "삭제 완료", "북마크가 삭제되었습니다.")

    def get_selected_file(self):
        return self.selected_file