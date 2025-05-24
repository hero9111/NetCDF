# C:\Users\thhan\oceanocal_v2\main_window.py

import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFileDialog, QMenu, QStatusBar, QWidget, QHBoxLayout, QMessageBox, QStyleFactory
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QPoint, QSize

# 중요: PlotWindowManager, DatasetManager, PlotHandler, SettingsManager, MainPanel
#       등의 클래스들이 각각의 파일에서 올바르게 임포트되었는지 확인하세요.
from .plot_window_manager import PlotWindowManager
from .log_config import setup_logger
import logging
from .dataset_manager import DatasetManager
from .handlers.plot_handler import PlotHandler
from .settings_manager import SettingsManager
from .main_panel import MainPanel

setup_logger()
logger = logging.getLogger(__name__) # MainWindow 클래스 내에서 로깅 사용

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(BASE_DIR, "resources", "icons")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")
SAMPLE_FILE = os.path.join(BASE_DIR, "sample_data", "20220920_235414_spec02.nc")

def icon(filename):
    path = os.path.join(ICON_DIR, filename)
    return QIcon(path) if os.path.exists(path) else QIcon()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OceanoCal NetCDF Viewer")
        self.setWindowIcon(icon('app_icon.png'))

        self.settings_manager = SettingsManager(SETTINGS_PATH) 
        self.dataset_manager = DatasetManager(status_callback=self.update_status_bar)
        self.plot_manager = PlotWindowManager(self, self.settings_manager, status_callback=self.update_status_bar) # PlotWindowManager 초기화
        self.plot_handler = PlotHandler(self, self.dataset_manager, self.plot_manager, self.settings_manager) # PlotHandler 초기화

        self._apply_dark_theme()
        self._load_window_state() 

        self._setup_ui()
        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()

        logger.info("MainWindow 초기화 완료.")

    def _setup_ui(self):
        self.main_panel = MainPanel(parent=self,
                                    dataset_manager=self.dataset_manager,
                                    plot_handler=self.plot_handler,
                                    plot_manager=self.plot_manager,
                                    settings_manager=self.settings_manager,
                                    update_status_bar_callback=self.update_status_bar)
        self.setCentralWidget(self.main_panel)
        logger.info("MainPanel 설정 완료.")

    def _create_actions(self):
        # File Actions
        self.open_action = QAction(icon('folder_open.png'), "&파일 열기...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setStatusTip("NetCDF 파일을 엽니다.")
        self.open_action.triggered.connect(self._open_file_dialog)

        self.close_action = QAction(icon('close.png'), "&파일 닫기", self)
        self.close_action.setShortcut("Ctrl+W")
        self.close_action.setStatusTip("현재 파일을 닫습니다.")
        self.close_action.triggered.connect(self.main_panel.close_current_file)

        self.exit_action = QAction(icon('exit.png'), "&종료", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.setStatusTip("애플리케이션을 종료합니다.")
        self.exit_action.triggered.connect(self.close)

        # Edit Actions
        self.settings_action = QAction(icon('settings.png'), "&설정", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.setStatusTip("애플리케이션 설정을 변경합니다.")
        # 변경: MainWindow의 show_settings_dialog 메서드에 연결
        self.settings_action.triggered.connect(self.show_settings_dialog) 

        # View Actions
        self.refresh_plot_action = QAction(icon('refresh.png'), "&플롯 새로고침", self)
        self.refresh_plot_action.setShortcut("F5")
        self.refresh_plot_action.setStatusTip("현재 활성화된 플롯을 새로고침합니다.")
        self.refresh_plot_action.triggered.connect(self.plot_handler.refresh_active_plot) # plot_handler에 연결

        self.plot_options_action = QAction(icon('tune.png'), "&플롯 옵션...", self)
        self.plot_options_action.setStatusTip("현재 플롯의 옵션을 수정합니다.")
        self.plot_options_action.triggered.connect(self.plot_handler.show_plot_options_dialog) # PlotHandler의 올바른 메서드 연결

        # Plot Actions (from main_panel)
        self.open_plot_action = QAction(icon('chart.png'), "플롯 열기", self)
        self.open_plot_action.setStatusTip("선택된 변수로 새 플롯을 엽니다.")
        self.open_plot_action.triggered.connect(self.main_panel.open_plot_window)

        self.export_plot_action = QAction(icon('export.png'), "현재 플롯 내보내기", self)
        self.export_plot_action.setStatusTip("현재 활성화된 플롯을 이미지로 내보냅니다.")
        self.export_plot_action.triggered.connect(self.plot_manager.export_current_plot) # plot_manager에 연결

        self.close_all_plots_action = QAction(icon('close_all.png'), "모든 플롯 닫기", self)
        self.close_all_plots_action.setStatusTip("모든 플롯 창을 닫습니다.")
        self.close_all_plots_action.triggered.connect(self.plot_manager.close_all_plot_windows) # plot_manager에 연결

        # Help Actions
        self.about_action = QAction(icon('info.png'), "&정보", self)
        self.about_action.setStatusTip("OceanoCal 정보 표시")
        self.about_action.triggered.connect(self.show_about_dialog)

        logger.info("액션 생성 완료.")

    def _create_menus(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&파일")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.close_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("&편집")
        edit_menu.addAction(self.settings_action)

        plot_menu = menu_bar.addMenu("&플롯")
        plot_menu.addAction(self.open_plot_action)
        plot_menu.addAction(self.refresh_plot_action)
        plot_menu.addAction(self.plot_options_action)
        plot_menu.addAction(self.export_plot_action)
        plot_menu.addSeparator()
        plot_menu.addAction(self.close_all_plots_action)

        help_menu = menu_bar.addMenu("&도움말")
        help_menu.addAction(self.about_action)

        logger.info("메뉴 생성 완료.")

    def _create_toolbars(self):
        file_toolbar = self.addToolBar("파일")
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.close_action)
        file_toolbar.addAction(self.exit_action)
        file_toolbar.setMovable(False)

        plot_toolbar = self.addToolBar("플롯")
        plot_toolbar.addAction(self.open_plot_action)
        plot_toolbar.addAction(self.refresh_plot_action)
        plot_toolbar.addAction(self.plot_options_action)
        plot_toolbar.addAction(self.export_plot_action)
        plot_toolbar.setMovable(False)

        logger.info("툴바 생성 완료.")

    def _create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("준비", 2000)
        logger.info("상태바 생성 완료.")

    def update_status_bar(self, message, timeout=0):
        """상태바 메시지를 업데이트합니다."""
        if hasattr(self, 'statusBar') and self.statusBar is not None:
            self.statusBar.showMessage(message, timeout)
            logger.debug(f"상태바 업데이트: {message}")
        else:
            logger.warning(f"상태바가 초기화되지 않았습니다. 메시지: {message}")

    def _open_file_dialog(self):
        # settings_manager에서 마지막으로 열었던 디렉토리를 가져옵니다.
        # 변경: get_setting -> get_app_setting
        last_dir = self.settings_manager.get_app_setting('last_opened_directory', os.path.expanduser('~'))
        
        filepath, _ = QFileDialog.getOpenFileName(self, "NetCDF 파일 열기", last_dir,
                                                  "NetCDF 파일 (*.nc *.nc4);;모든 파일 (*.*)")
        if filepath:
            self.dataset_manager.current_file_path = filepath # DatasetManager에 현재 파일 경로 설정
            self.main_panel.load_file_into_tree(filepath)
            # 마지막으로 열었던 디렉토리를 저장합니다.
            # 변경: set_setting -> set_app_setting
            self.settings_manager.set_app_setting('last_opened_directory', os.path.dirname(filepath))
            logger.info(f"파일 다이얼로그를 통해 파일 열림: {filepath}")
        else:
            logger.info("파일 열기 취소됨.")

    def _load_window_state(self):
        # 변경: load_settings -> load_app_settings
        settings = self.settings_manager.load_app_settings()
        # settings가 None일 경우 빈 사전으로 초기화하여 TypeError 방지
        if settings is None:
            settings = {}
        
        if 'window_geometry' in settings and 'window_state' in settings:
            self.restoreGeometry(settings['window_geometry'])
            self.restoreState(settings['window_state'])
            logger.info("이전 윈도우 상태 로드됨.")
        else:
            self.resize(1000, 700) # 기본 크기 설정
            self.move(100, 100) # 기본 위치 설정
            logger.info("이전 윈도우 상태를 찾을 수 없어 기본 값으로 설정됨.")

    def _save_window_state(self):
        # 변경: load_settings -> load_app_settings
        settings = self.settings_manager.load_app_settings()
        # settings가 None일 경우 빈 사전으로 초기화하여 TypeError 방지
        if settings is None:
            settings = {}

        settings['window_geometry'] = self.saveGeometry()
        settings['window_state'] = self.saveState()
        # 변경: save_settings -> save_app_settings
        self.settings_manager.save_app_settings(settings)
        logger.info("현재 윈도우 상태 저장됨.")
    
    def _apply_dark_theme(self):
        # 스타일 설정
        QApplication.setStyle(QStyleFactory.create('Fusion'))

        # 팔레트 설정
        dark_palette = QApplication.palette()
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Window, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Window, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Base, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Base, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.AlternateBase, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.AlternateBase, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Button, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Button, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Link, Qt.GlobalColor.cyan)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Link, Qt.GlobalColor.cyan)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.Highlight, Qt.GlobalColor.blue)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.Highlight, Qt.GlobalColor.blue)
        dark_palette.setColor(dark_palette.ColorGroup.Active, dark_palette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        dark_palette.setColor(dark_palette.ColorGroup.Inactive, dark_palette.ColorRole.HighlightedText, Qt.GlobalColor.black)

        dark_palette.setColor(dark_palette.ColorGroup.Disabled, dark_palette.ColorRole.Text, Qt.GlobalColor.darkGray)
        dark_palette.setColor(dark_palette.ColorGroup.Disabled, dark_palette.ColorRole.ButtonText, Qt.GlobalColor.darkGray)

        QApplication.setPalette(dark_palette)

        # QSS를 통한 추가 스타일링
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QMenuBar { background-color: #333; color: #EEE; }
            QMenuBar::item:selected { background: #555; }
            QMenu { background-color: #333; color: #EEE; border: 1px solid #555; }
            QMenu::item:selected { background: #555; }
            QToolBar { background-color: #3a3a3a; border: none; padding: 2px; }
            QToolButton { background-color: #3a3a3a; color: #EEE; border: 1px solid #444; padding: 5px; }
            QToolButton:hover { background-color: #555; }
            QToolButton:pressed { background-color: #666; border: 1px solid #777; }
            QStatusBar { background-color: #3a3a3a; color: #EEE; }
            QTreeWidget {
                background-color: #333;
                color: #EEE;
                border: 1px solid #444;
                alternate-background-color: #3a3a3a;
                selection-background-color: #0078d7; /* Windows Blue */
                selection-color: #FFF;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #0078d7;
            }
            QTextEdit {
                background-color: #333;
                color: #EEE;
                border: 1px solid #444;
                padding: 5px;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QSplitter::handle:hover {
                background-color: #777;
            }
            /* Scrollbar styling */
            QScrollBar:vertical {
                border: 1px solid #444;
                background: #3a3a3a;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:horizontal {
                border: 1px solid #444;
                background: #3a3a3a;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #555;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            QTabBar::tab {
                background: #444;
                color: #EEE;
                border: 1px solid #555;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                padding: 5px 10px;
            }
            QTabBar::tab:selected { background: #666; }
            QDialog { background-color: #333; color: #EEE; }
            QLabel { color: #EEE; }
            QCheckBox { color: #EEE; }
            QGroupBox { color: #EEE; }
            QComboBox { background-color: #555; color: #EEE; border: 1px solid #666; }
            QComboBox::drop-down { border-left: 1px solid #666; }
            QComboBox::down-arrow { image: url(resources/icons/arrow_down_white.png); } /* Ensure you have a white arrow icon */
            QDoubleSpinBox { background-color: #555; color: #EEE; border: 1px solid #666; }
            QLineEdit { background-color: #555; color: #EEE; border: 1px solid #666; }
        """)

    def show_about_dialog(self):
        QMessageBox.about(self, "OceanoCal 정보",
                          "<h2>OceanoCal NetCDF Viewer</h2>"
                          "<p>버전: 2.0</p>"
                          "<p>개발자: Your Name</p>"
                          "<p>NetCDF 파일을 탐색하고 플롯하기 위한 도구입니다.</p>")
        logger.info("정보 다이얼로그 표시.")

    def show_settings_dialog(self):
        """
        설정 다이얼로그를 표시합니다.
        현재는 플레이스홀더 메시지를 표시하며, 향후 SettingsDialog 클래스와 연동될 수 있습니다.
        """
        QMessageBox.information(self, "설정", "설정 다이얼로그 기능은 아직 구현되지 않았습니다.")
        logger.info("설정 다이얼로그 호출 (미구현).")

    def closeEvent(self, event):
        # 윈도우 상태 저장
        self._save_window_state()
        # 모든 플롯 창 닫기
        if self.plot_manager:
            self.plot_manager.close_all_plot_windows()
        event.accept()
        logger.info("애플리케이션 종료.")