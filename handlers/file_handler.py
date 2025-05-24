# oceanocal_v2/handlers/file_handler.py

import netCDF4
import os
import logging

class NetCDFFileHandler:
    def __init__(self):
        self.dataset = None
        logging.info("NetCDFFileHandler 초기화.")

    def load_file(self, filepath):
        """
        NetCDF 파일을 로드하고 그룹 및 변수 구조를 재귀적으로 파싱합니다.
        Xarray로의 전환으로 인해 이 핸들러는 더 이상 사용되지 않을 수 있습니다.
        DatasetManager가 대신 xarray를 사용하여 파일을 관리합니다.
        """
        logging.warning("NetCDFFileHandler.load_file은 DatasetManager로 대체되었을 수 있습니다.")
        try:
            self.dataset = netCDF4.Dataset(filepath)
            return self._parse_group(self.dataset)
        except Exception as e:
            logging.error(f"NetCDF 파일 로드 오류: {e}", exc_info=True)
            self.dataset = None
            raise

    def _parse_group(self, group):
        """
        NetCDF4 그룹의 내부 구조를 재귀적으로 파싱합니다.
        """
        tree = []
        # 그룹
        for name, subgroup in getattr(group, 'groups', {}).items():
            tree.append({
                'name': name,
                'type': 'group',
                'children': self._parse_group(subgroup)
            })
        # 변수
        for name, var in getattr(group, 'variables', {}).items():
            attrs = {attr: str(getattr(var, attr)) for attr in var.ncattrs()}
            tree.append({
                'name': name,
                'type': 'variable',
                'dimensions': list(var.dimensions),
                'shape': var.shape,
                'dtype': str(var.dtype),
                'attributes': attrs,
                'children': [{'name': f"[속성] {attr}: {value}"} for attr, value in attrs.items()]
            })
        return tree

    def get_variable_path(self, item):
        """
        QTreeWidgetItem에서 변수 경로 추출 (루트 ~ 리프 경로)
        """
        path = []
        while item:
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data and item_data.get('type') in ['variable', 'group']:
                path.insert(0, item.text(0))
            item = item.parent()
        # Join path components, skipping the file root (if it's just the file name)
        if len(path) > 1 and path[0].endswith(('.nc', '.netcdf')):
            return '/' + '/'.join(path[1:])
        return '/' + '/'.join(path) if path else ''

    def get_variable_by_path(self, var_path):
        """
        변수 경로를 사용하여 NetCDF4 Dataset에서 변수 객체를 가져옵니다.
        """
        if not self.dataset:
            logging.error("데이터셋이 로드되지 않았습니다.")
            return None

        parts = var_path.strip('/').split('/')
        current_group = self.dataset
        try:
            for i, part in enumerate(parts):
                if i == len(parts) - 1: # 마지막 부분은 변수 이름
                    return current_group.variables.get(part)
                else: # 그룹 이름
                    current_group = current_group.groups.get(part)
                    if not current_group:
                        logging.warning(f"경로에 그룹을 찾을 수 없습니다: {var_path}")
                        return None
            return None
        except Exception as e:
            logging.error(f"변수 경로 '{var_path}'로 변수를 가져오는 중 오류 발생: {e}", exc_info=True)
            return None

    def close_file(self):
        if self.dataset:
            try:
                self.dataset.close()
                logging.info("NetCDF 파일 닫힘.")
            except Exception as e:
                logging.error(f"NetCDF 파일을 닫는 중 오류 발생: {e}", exc_info=True)
            finally:
                self.dataset = None