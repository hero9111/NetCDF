# oceanocal_v2/log_config.py

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"oceanocal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def setup_logger():
    # 로거 생성
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 포매터 생성
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # 파일 핸들러 생성 (DEBUG 레벨)
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 생성 (INFO 레벨)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 기존 핸들러 중복 방지 (run_app이 여러번 호출될 경우)
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    logging.info(f"로그 파일 생성됨: {LOG_FILE}")