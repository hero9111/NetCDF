# oceanocal_v2/settings_manager.py

import json
import os
import logging

class SettingsManager:
    def __init__(self, settings_path=None):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SETTINGS_PATH = settings_path if settings_path else os.path.join(self.BASE_DIR, "settings.json")
        self._settings = {}
        self._default_plot_options = {
            'title_text': 'Variable Plot',
            'xaxis_label': 'X-Axis',
            'yaxis_label': 'Y-Axis',
            'cbar_label': 'Colorbar',
            'cmap': 'jet',
            'theme': 'Light', # Plotly theme
            'plot_font_family': 'Arial',
            'plot_font_size': 12
        }
        self.load_settings()
        logging.info("SettingsManager 초기화.")

    def load_settings(self):
        try:
            if os.path.exists(self.SETTINGS_PATH):
                with open(self.SETTINGS_PATH, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
                logging.info(f"설정 파일 로드됨: {self.SETTINGS_PATH}")
            else:
                self._settings = {}
                logging.info("설정 파일이 존재하지 않습니다. 기본 설정 사용.")
        except json.JSONDecodeError as e:
            logging.error(f"설정 파일을 읽는 중 오류 발생 (JSON 형식 오류): {e}", exc_info=True)
            self._settings = {} # Reset to empty settings on error
        except Exception as e:
            logging.error(f"설정 파일을 로드하는 중 알 수 없는 오류 발생: {e}", exc_info=True)
            self._settings = {}

    def save_settings(self):
        try:
            with open(self.SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            logging.info(f"설정 파일 저장됨: {self.SETTINGS_PATH}")
        except Exception as e:
            logging.error(f"설정 파일을 저장하는 중 오류 발생: {e}", exc_info=True)

    def get_app_setting(self, key, default=None):
        return self._settings.get("app_settings", {}).get(key, default)

    def save_app_setting(self, key, value):
        if "app_settings" not in self._settings:
            self._settings["app_settings"] = {}
        self._settings["app_settings"][key] = value
        self.save_settings()

    def get_plot_option(self, key, default=None):
        return self._settings.get("plot_options", {}).get(key, self._default_plot_options.get(key, default))

    def get_default_plot_options(self):
        """
        Returns a dictionary of all default plot options, merged with any saved settings.
        """
        saved_plot_options = self._settings.get("plot_options", {})
        return {**self._default_plot_options, **saved_plot_options}

    def save_plot_option(self, key, value):
        if "plot_options" not in self._settings:
            self._settings["plot_options"] = {}
        self._settings["plot_options"][key] = value
        self.save_settings()

    def get_active_overlays(self):
        return self._settings.get("active_overlays", [])

    def set_active_overlays(self, overlays):
        self._settings["active_overlays"] = overlays
        self.save_settings()