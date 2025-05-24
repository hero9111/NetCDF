import xarray as xr
import os
import logging
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class DatasetManager:
    def __init__(self, status_callback=None):
        self.open_datasets = {}  # {filepath: xarray.Dataset}
        self.current_file_path = None # 현재 활성화된 파일 경로 추가
        self.status_callback = status_callback
        logger.info("DatasetManager 초기화.")

    def _report_status(self, message, timeout=2000):
        if self.status_callback:
            self.status_callback(message, timeout)

    def open_file(self, filepath):
        """
        주어진 NetCDF 파일을 열고 현재 활성화된 파일로 설정합니다.
        """
        if not os.path.exists(filepath):
            msg = f"파일을 찾을 수 없습니다: {filepath}"
            self._report_status(msg, 5000)
            logger.error(msg)
            raise FileNotFoundError(msg)

        if filepath in self.open_datasets:
            self._report_status(f"'{os.path.basename(filepath)}' 파일이 이미 열려 있습니다.", 2000)
            self.current_file_path = filepath # 이미 열려있어도 현재 파일로 설정
            return self.open_datasets[filepath]

        try:
            ds = xr.open_dataset(filepath)
            self.open_datasets[filepath] = ds
            self.current_file_path = filepath # 새로 열었을 때 현재 파일로 설정
            self._report_status(f"'{os.path.basename(filepath)}' 파일 열림.", 2000)
            logger.info(f"파일 열림: {filepath}")
            return ds
        except Exception as e:
            msg = f"파일 로드 중 오류 발생: {e}"
            self._report_status(msg, 5000)
            logger.error(msg)
            raise IOError(msg)

    def close_file(self, filepath=None):
        """
        주어진 경로의 파일을 닫거나, filepath가 None이면 현재 활성화된 파일을 닫습니다.
        """
        target_filepath = filepath if filepath else self.current_file_path

        if target_filepath and target_filepath in self.open_datasets:
            try:
                self.open_datasets[target_filepath].close()
                del self.open_datasets[target_filepath]
                logger.info(f"파일 닫기 성공: {target_filepath}")
                self._report_status(f"파일 닫힘: {os.path.basename(target_filepath)}", 2000)
                
                if self.current_file_path == target_filepath:
                    self.current_file_path = None # 현재 활성화된 파일이 닫혔다면 초기화
                    
            except Exception as e:
                logger.error(f"파일 닫기 중 오류 발생: {e}")
                self._report_status(f"파일 닫기 중 오류 발생: {e}", 5000)
        else:
            logger.info("닫을 파일이 없습니다.")
            # self._report_status("닫을 파일이 없습니다.", 2000) # 주석 처리 또는 위와 같이 변경

    def get_dataset(self, filepath=None):
        """
        주어진 경로의 데이터셋을 반환하거나, filepath가 None이면 현재 활성화된 데이터셋을 반환합니다.
        """
        if filepath:
            return self.open_datasets.get(filepath)
        elif self.current_file_path:
            return self.open_datasets.get(self.current_file_path)
        return None

    def get_current_file_path(self):
        """
        현재 활성화된 파일의 경로를 반환합니다.
        """
        return self.current_file_path

    def get_variable_data_from_file(self, filepath, var_name):
        """
        주어진 파일 경로에서 특정 변수의 데이터를 가져옵니다.
        """
        ds = self.get_dataset(filepath)
        if ds and var_name in ds.variables:
            return ds.variables[var_name]
        elif ds and var_name in ds.coords: # 코디네이트도 변수로 취급
            return ds.coords[var_name]
        return None

    def get_variable_info_from_dataset(self, dataset_path, var_name):
        """
        Gets variable info assuming var_name might be a coordinate or a data variable.
        Used by plot_handler for dimension analysis.
        """
        ds = self.open_datasets.get(dataset_path)
        if not ds:
            try:
                ds = self.open_file(dataset_path) # 필요시 파일을 엽니다.
            except (FileNotFoundError, IOError):
                return None

        if var_name in ds.variables:
            var = ds.variables[var_name]
            return {
                "name": var_name,
                "dimensions": list(var.dims),
                "attributes": {attr: str(getattr(var, attr)) for attr in var.attrs},
                "dtype": str(var.dtype)
            }
        elif var_name in ds.coords: # Also check coordinates
            var = ds.coords[var_name]
            return {
                "name": var_name,
                "dimensions": list(var.dims),
                "attributes": {attr: str(getattr(var, attr)) for attr in var.attrs},
                "dtype": str(var.dtype)
            }
        else:
            logger.warning(f"데이터셋 '{dataset_path}'에 변수 '{var_name}'가 없습니다.")
            return None

    def get_file_list(self):
        """현재 열려있는 파일들의 경로 리스트를 반환합니다."""
        return list(self.open_datasets.keys())