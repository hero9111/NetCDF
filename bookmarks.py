# oceanocal_v2/bookmarks.py

import json
import os
from PyQt6.QtCore import QStandardPaths
import logging

BOOKMARKS_FILE_NAME = "oceanocal_bookmarks.json"

# Store bookmarks in a standard application data location
try:
    APP_DATA_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not APP_DATA_DIR: # Fallback if system path is not found
        APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".oceanocal_v2")
except Exception: # Fallback for non-Qt environments or errors
    APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".oceanocal_v2")

if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR, exist_ok=True)
BOOKMARKS_FILE_PATH = os.path.join(APP_DATA_DIR, BOOKMARKS_FILE_NAME)


class BookmarkManager:
    def __init__(self):
        self.bookmarks = []
        self.load()

    def load(self):
        if os.path.exists(BOOKMARKS_FILE_PATH):
            try:
                with open(BOOKMARKS_FILE_PATH, "r", encoding="utf-8") as f:
                    self.bookmarks = json.load(f)
            except json.JSONDecodeError:
                logging.error(f"Error: Could not decode bookmarks file: {BOOKMARKS_FILE_PATH}. Initializing empty list.", exc_info=True)
                self.bookmarks = [] # Initialize with empty list if file is corrupt
            except Exception as e:
                logging.error(f"Error loading bookmarks: {e}. Initializing empty list.", exc_info=True)
                self.bookmarks = []
        else:
            self.bookmarks = []
        logging.info(f"북마크 로드 완료: {BOOKMARKS_FILE_PATH}")

    def save(self):
        try:
            with open(BOOKMARKS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
            logging.info(f"북마크 저장 완료: {BOOKMARKS_FILE_PATH}")
        except Exception as e:
            logging.error(f"Error saving bookmarks: {e}", exc_info=True)

    def add(self, filepath):
        if filepath and filepath not in self.bookmarks:
            self.bookmarks.append(filepath)
            self.save()
            logging.info(f"북마크 추가됨: {filepath}")
            return True
        return False

    def remove(self, filepath):
        if filepath in self.bookmarks:
            self.bookmarks.remove(filepath)
            self.save()
            logging.info(f"북마크 제거됨: {filepath}")
            return True
        return False

    def get_all(self):
        return list(self.bookmarks)