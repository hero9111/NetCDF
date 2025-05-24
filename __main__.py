# oceanocal_v2/__main__.py

import sys
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow
from .log_config import setup_logger
import logging

def run_app():
    setup_logger()
    logging.info("애플리케이션 시작.")
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()