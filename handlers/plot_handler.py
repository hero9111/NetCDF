# oceanocal_v2/handlers/plot_handler.py

from PyQt6.QtWidgets import QMessageBox
from ..plot_label_dialog import PlotLabelDialog # 이 파일이 있다면 유지
import re
import logging
import os # os.path.basename 사용을 위해 추가

logger = logging.getLogger(__name__)

class PlotHandler:
    def __init__(self, main_window, dataset_manager, plot_manager, settings_manager):
        self.main_window = main_window # MainWindow 인스턴스를 통해 상태바 접근
        self.dataset_manager = dataset_manager
        self.plot_manager = plot_manager # This is now PlotWindowManager
        self.settings_manager = settings_manager
        logger.info("PlotHandler 초기화.")

    def _report_status(self, message, timeout=2000):
        if hasattr(self.main_window, 'update_status_bar'):
            self.main_window.update_status_bar(message, timeout)
        else:
            logger.warning(f"update_status_bar_callback이 설정되지 않았거나 호출할 수 없습니다: {message}")

    def _is_latitude(self, var_info):
        if not var_info: return False
        name = var_info.get("name", "").lower()
        attrs = var_info.get("attributes", {})
        units = attrs.get("units", "").lower()
        std_name = attrs.get("standard_name", "").lower()
        long_name = attrs.get("long_name", "").lower()

        if "lat" in name or "latitude" in name or \
           "degrees_north" in units or "degree_n" in units or \
           "latitude" in std_name or "latitude" in long_name:
            return True
        return False

    def _is_longitude(self, var_info):
        if not var_info: return False
        name = var_info.get("name", "").lower()
        attrs = var_info.get("attributes", {})
        units = attrs.get("units", "").lower()
        std_name = attrs.get("standard_name", "").lower()
        long_name = attrs.get("long_name", "").lower()

        if "lon" in name or "longitude" in name or \
           "degrees_east" in units or "degree_e" in units or \
           "longitude" in std_name or "longitude" in long_name:
            return True
        return False

    def _is_depth(self, var_info):
        if not var_info: return False
        name = var_info.get("name", "").lower()
        attrs = var_info.get("attributes", {})
        units = attrs.get("units", "").lower()
        std_name = attrs.get("standard_name", "").lower()
        long_name = attrs.get("long_name", "").lower()

        if "depth" in name or "pressure" in name or "altitude" in name or \
           "dbar" in units or "m" in units or "pressure" in std_name or \
           "depth" in std_name or "depth" in long_name:
            return True
        return False

    def _is_time(self, var_info):
        if not var_info: return False
        name = var_info.get("name", "").lower()
        attrs = var_info.get("attributes", {})
        std_name = attrs.get("standard_name", "").lower()
        long_name = attrs.get("long_name", "").lower()

        if "time" in name or "time" in std_name or "time" in long_name:
            return True
        return False

    def create_or_update_plot_window(self, file_path: str, variable_name: str):
        """
        MainPanel에서 호출되는 메서드.
        주어진 파일 경로와 변수 이름으로 플롯 창을 생성하거나 업데이트합니다.
        적절한 플롯 타입을 결정하고 PlotWindowManager에 요청합니다.
        """
        dataset = self.dataset_manager.get_dataset(file_path)
        if not dataset:
            msg = f"파일 '{file_path}'에 대한 데이터셋을 찾을 수 없습니다."
            QMessageBox.warning(self.main_window, "데이터셋 오류", msg)
            self._report_status(msg, 3000)
            logger.warning(f"PlotHandler: 데이터셋을 찾을 수 없음: {file_path}")
            return

        if variable_name not in dataset.data_vars and variable_name not in dataset.coords:
            msg = f"데이터셋에 변수 '{variable_name}'가 없습니다."
            QMessageBox.warning(self.main_window, "변수 오류", msg)
            self._report_status(msg, 3000)
            logger.warning(f"PlotHandler: 변수 '{variable_name}'가 데이터셋에 없음.")
            return
        
        var_info = self.dataset_manager.get_variable_info_from_dataset(file_path, variable_name)
        
        plot_type = "unknown"
        if var_info:
            dims = var_info.get("dimensions", [])
            
            # 1D plot: Time series or profile
            if len(dims) == 1:
                if self._is_time(self.dataset_manager.get_variable_info_from_dataset(file_path, dims[0])):
                    plot_type = "time_series"
                elif self._is_depth(self.dataset_manager.get_variable_info_from_dataset(file_path, dims[0])):
                    plot_type = "profile"
                else:
                    plot_type = "1d_generic" # 기타 1D 플롯
            # 2D plot: Map or time-depth
            elif len(dims) == 2:
                dim1_info = self.dataset_manager.get_variable_info_from_dataset(file_path, dims[0])
                dim2_info = self.dataset_manager.get_variable_info_from_dataset(file_path, dims[1])

                if self._is_time(dim1_info) and self._is_depth(dim2_info):
                    plot_type = "time_depth_heatmap"
                elif self._is_time(dim2_info) and self._is_depth(dim1_info):
                    plot_type = "time_depth_heatmap" # 순서 바뀌어도 동일
                elif (self._is_latitude(dim1_info) or self._is_longitude(dim1_info)) and \
                     (self._is_latitude(dim2_info) or self._is_longitude(dim2_info)):
                    plot_type = "map_2d" # 위도/경도 맵
                else:
                    plot_type = "2d_heatmap" # 기타 2D 플롯
            elif len(dims) == 0:
                plot_type = "scalar" # 스칼라 값

        # 기본 플롯 옵션 설정
        default_options = {
            'plot_type': plot_type,
            'filepath': file_path,
            'var_name': variable_name,
            'title': f"{os.path.basename(file_path)} - {variable_name}",
            'xlabel': self._get_label_from_dim(dataset, dims[0]) if dims else 'Index',
            'ylabel': self._get_label_from_dim(dataset, dims[1]) if len(dims) > 1 else 'Value',
            'zlabel': '', # 2D 플롯의 값 축 레이블
            'cmap': 'viridis',
            'vmin': None,
            'vmax': None,
            'aspect': 'auto',
            'interpolation': 'nearest',
            'levels': None, # Contour levels
            'log_scale': False, # Log scale for colorbar
            'time_format': '%Y-%m-%d %H:%M',
            'grid': True,
            'colorbar_label': var_info.get('attributes', {}).get('long_name', variable_name) # 컬러바 레이블
        }
        
        # PlotWindowManager에 플롯 요청
        self.plot_manager.create_new_plot_window(
            plot_id=f"{file_path}::{variable_name}", # 고유 ID
            title=default_options['title'],
            dataset_manager=self.dataset_manager,
            file_path=file_path,
            variable_name=variable_name,
            plot_type=plot_type,
            options=default_options,
            update_status_bar_callback=self._report_status # PlotHandler의 상태바 콜백 전달
        )
        self._report_status(f"'{variable_name}' 플롯 창 요청됨.", 2000)
        logger.info(f"PlotHandler: 플롯 요청: {variable_name} from {file_path}, Type: {plot_type}")


    def _get_label_from_dim(self, dataset, dim_name):
        """차원 이름에 해당하는 변수의 long_name 또는 units를 사용하여 레이블을 생성합니다."""
        if dim_name in dataset.coords:
            coord_var = dataset.coords[dim_name]
            label = coord_var.attrs.get('long_name', dim_name)
            if 'units' in coord_var.attrs:
                label += f" ({coord_var.attrs['units']})"
            return label
        return dim_name


    def refresh_active_plot(self):
        """
        현재 활성화된 플롯 창을 새로고침합니다.
        """
        active_plot_window = self.plot_manager.get_active_plot_window()
        if active_plot_window:
            active_plot_window.refresh_plot()
            logger.info(f"PlotHandler: 플롯 창 새로고침: {active_plot_window.windowTitle()}")
            self._report_status(f"플롯 '{active_plot_window.windowTitle()}' 새로고침 완료.", 2000)
        else:
            logger.info("PlotHandler: 활성화된 플롯 창이 없어 새로고침할 수 없습니다.")
            self._report_status("활성화된 플롯 없음.", 2000)

    def show_plot_options_dialog(self):
        """
        현재 활성화된 플롯의 옵션을 수정하기 위한 다이얼로그를 표시합니다.
        """
        # PlotWindowManager가 가장 최근에 열린 플롯 창의 옵션을 제공한다고 가정합니다.
        # 즉, PlotWindowManager 내부에 get_current_plot_options 메서드가 있어야 합니다.
        current_options = self.plot_manager.get_current_plot_options()
        if not current_options:
            msg = "수정할 플롯의 옵션을 찾을 수 없습니다. 열려 있는 플롯 창이 없습니다."
            QMessageBox.warning(self.main_window, "오류", msg)
            self._report_status(msg, 3000)
            logging.warning("플롯 옵션 업데이트 요청 - 열려 있는 플롯 창 없음.")
            return

        dialog = PlotLabelDialog(self.main_window,
                                 current_options=current_options.copy(), # Pass a copy to avoid direct modification
                                 settings_manager=self.settings_manager)
        if dialog.exec():
            new_options = dialog.get_options()
            # Ensure plot_type, var_name, filepath are preserved as they are not set in the dialog
            new_options['plot_type'] = current_options.get('plot_type')
            new_options['filepath'] = current_options.get('filepath')
            new_options['var_name'] = current_options.get('var_name')
            new_options['xlabel'] = new_options.get('xlabel', current_options.get('xlabel')) # Fallback to current if not set
            new_options['ylabel'] = new_options.get('ylabel', current_options.get('ylabel'))
            new_options['title'] = new_options.get('title', current_options.get('title'))
            new_options['colorbar_label'] = new_options.get('colorbar_label', current_options.get('colorbar_label'))
            new_options['grid'] = new_options.get('grid', current_options.get('grid'))
            new_options['log_scale'] = new_options.get('log_scale', current_options.get('log_scale'))
            new_options['cmap'] = new_options.get('cmap', current_options.get('cmap'))
            new_options['vmin'] = new_options.get('vmin', current_options.get('vmin'))
            new_options['vmax'] = new_options.get('vmax', current_options.get('vmax'))


            # Now update the plot via PlotWindowManager
            self.plot_manager.update_plot_options(new_options)
            self._report_status("플롯 옵션 업데이트 완료.", 2000)
            logging.info(f"플롯 옵션 업데이트됨: {new_options.get('var_name')}")
        else:
            self._report_status("플롯 옵션 수정 취소.", 1000)
            logging.info("플롯 옵션 수정 취소됨.")