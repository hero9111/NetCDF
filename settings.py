# settings.py

import json
import os

class SettingsManager:
    def __init__(self, config_path="settings.json"):
        self.config_path = config_path
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"recent_files": []}

    def save_settings(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def get_recent_files(self):
        return self.settings.get("recent_files", [])

    def add_recent_file(self, filepath):
        recent = self.get_recent_files()
        if filepath not in recent:
            recent.append(filepath)
            self.settings["recent_files"] = recent[-10:]  # 10개만 유지
            self.save_settings()
