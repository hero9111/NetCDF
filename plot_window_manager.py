# oceanocal_v2/plot_window_manager.py

import logging
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QMessageBox, QFileDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import xarray as xr
import numpy as np
import os
from datetime import datetime # 시간 포맷팅을 위해 추가

logger = logging.getLogger(__name__)

# MainPanel이나 PlotHandler에서 DatasetManager와 PlotWindowManager를 임포트할 때
# 상위 디렉토리에서 임포트하므로 . 대신 ..을 사용합니다.
from .dataset_manager import DatasetManager

class PlotWindow(QMainWindow):
    """
    개별 플롯을 표시하는 윈도우 클래스.
    """
    def __init__(self, plot_id: str, title: str, 
                 dataset_manager: DatasetManager, 
                 file_path: str, variable_name: str, plot_type: str, options: dict, 
                 update_status_bar_callback=None, parent=None):
        super().__init__(parent)
        self.plot_id = plot_id
        self.dataset_manager = dataset_manager
        self.file_path = file_path
        self.variable_name = variable_name
        self.plot_type = plot_type
        self.options = options # 플롯 옵션 저장
        self.update_status_bar_callback = update_status_bar_callback
        
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 800, 600)

        self._setup_ui()
        self.refresh_plot() # 초기 플롯 그리기
        logger.info(f"PlotWindow '{title}' 생성 완료. ID: {plot_id}")

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.figure, self.ax = plt.subplots(figsize=(10, 6)) # Figure size for better resolution
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        logger.debug("PlotWindow UI 설정 완료.")

    def refresh_plot(self):
        """
        현재 설정된 변수와 옵션을 사용하여 플롯을 새로 그립니다.
        """
        self.ax.clear()
        
        dataset = self.dataset_manager.get_dataset(self.file_path)
        if not dataset:
            self._display_error_message("데이터셋을 찾을 수 없습니다.")
            logger.warning(f"PlotWindow: 데이터셋을 찾을 수 없어 플롯 새로고침 실패. File: {self.file_path}")
            return

        if self.variable_name not in dataset.data_vars and self.variable_name not in dataset.coords:
            self._display_error_message(f"변수 '{self.variable_name}'를 찾을 수 없습니다.")
            logger.warning(f"PlotWindow: 변수 '{self.variable_name}'를 찾을 수 없어 플롯 새로고침 실패. File: {self.file_path}")
            return
        
        variable = dataset[self.variable_name]
        
        # 공통 옵션 적용
        title = self.options.get('title', self.variable_name)
        xlabel = self.options.get('xlabel', 'X-axis')
        ylabel = self.options.get('ylabel', 'Y-axis')
        zlabel = self.options.get('colorbar_label', self.variable_name) # 2D 플롯의 값 축 레이블
        grid = self.options.get('grid', True)
        cmap = self.options.get('cmap', 'viridis')
        vmin = self.options.get('vmin')
        vmax = self.options.get('vmax')
        log_scale = self.options.get('log_scale', False)
        time_format = self.options.get('time_format', '%Y-%m-%d %H:%M')

        # 플롯 타입에 따른 로직 분기
        if self.plot_type == "time_series" or self.plot_type == "1d_generic":
            # 1D 데이터 플롯 (시간 또는 일반 1D)
            x_data = None
            if 'time' in variable.dims and 'time' in dataset.coords:
                x_data = dataset['time'].values
                if len(x_data) != len(variable.values):
                     x_data = np.arange(len(variable.values)) # 길이가 다르면 인덱스 사용
                     xlabel = 'Index'
                else:
                    xlabel = 'Time'
                    self.figure.autofmt_xdate() # 시간 축 레이블 회전
            else:
                x_data = np.arange(len(variable.values))
                xlabel = 'Index'
            
            self.ax.plot(x_data, variable.values)
            self.ax.set_title(title)
            self.ax.set_xlabel(xlabel)
            self.ax.set_ylabel(ylabel)
            self.ax.grid(grid)

        elif self.plot_type == "profile":
            # 1D 프로파일 플롯 (깊이 vs 값)
            if 'depth' in variable.dims and 'depth' in dataset.coords:
                y_data = dataset['depth'].values
                if len(y_data) != len(variable.values):
                    y_data = np.arange(len(variable.values))
                    ylabel = 'Index'
                else:
                    ylabel = 'Depth'
                self.ax.plot(variable.values, y_data) # 값 vs 깊이
                self.ax.set_xlabel(xlabel) # 보통 값
                self.ax.set_ylabel(ylabel)
                self.ax.invert_yaxis() # 깊이 플롯은 Y축을 반전하는 경우가 많음
                self.ax.set_title(title)
                self.ax.grid(grid)
            else:
                self._display_error_message(f"프로파일 플롯을 위한 'depth' 차원을 찾을 수 없습니다.")
                logger.warning(f"PlotWindow: 'depth' 차원 없음 for profile plot of {self.variable_name}.")

        elif self.plot_type == "time_depth_heatmap" or self.plot_type == "2d_heatmap" or self.plot_type == "map_2d":
            # 2D 데이터 플롯 (시간-깊이, 일반 2D 히트맵, 지도)
            if variable.ndim < 2:
                self._display_error_message(f"2D 플롯을 위한 차원 수가 부족합니다: {variable.ndim}D")
                logger.warning(f"PlotWindow: 2D 플롯을 위한 차원 수 부족 ({variable.ndim}) for {self.variable_name}.")
                self.canvas.draw()
                return

            dim1_name, dim2_name = variable.dims[0], variable.dims[1]
            x_coords = dataset.coords.get(dim2_name)
            y_coords = dataset.coords.get(dim1_name)

            if x_coords is None or y_coords is None:
                self._display_error_message(f"2D 플롯을 위한 좌표 변수 '{dim1_name}' 또는 '{dim2_name}'를 찾을 수 없습니다.")
                logger.warning(f"PlotWindow: 2D 플롯 좌표 변수 없음 for {self.variable_name}.")
                self.ax.imshow(variable.values, aspect='auto', origin='lower', cmap=cmap, vmin=vmin, vmax=vmax, interpolation=self.options.get('interpolation', 'nearest'))
                self.ax.set_xlabel('Dimension 2 Index')
                self.ax.set_ylabel('Dimension 1 Index')
            else:
                x_data = x_coords.values
                y_data = y_coords.values

                # 시간 축 처리
                if np.issubdtype(x_data.dtype, np.datetime64):
                    self.figure.autofmt_xdate()
                    
                # 깊이 축 처리 (y축이 깊이일 경우 반전)
                if 'depth' in dim1_name.lower() or 'pressure' in dim1_name.lower():
                     self.ax.invert_yaxis()

                # Pcolormesh를 사용하여 더 유연하게 플롯
                try:
                    pcm = self.ax.pcolormesh(x_data, y_data, variable.values, 
                                            cmap=cmap, vmin=vmin, vmax=vmax, shading='auto')
                except ValueError as ve:
                    # 'shading'이 'auto'일 때 발생하는 오류 처리 (데이터/좌표 불일치)
                    logger.error(f"Pcolormesh 오류 발생 (shading='auto' 문제): {ve}. shading='flat'으로 재시도.")
                    try:
                        pcm = self.ax.pcolormesh(x_data, y_data, variable.values, 
                                                cmap=cmap, vmin=vmin, vmax=vmax, shading='flat')
                    except Exception as e:
                        self._display_error_message(f"플롯 오류 (2D): {e}")
                        logger.error(f"2D 플롯 최종 실패: {e}")
                        self.canvas.draw()
                        return


                cb = self.figure.colorbar(pcm, ax=self.ax, label=zlabel)
                if log_scale:
                    cb.ax.set_yscale('log')

                self.ax.set_xlabel(xlabel)
                self.ax.set_ylabel(ylabel)
                self.ax.set_title(title)
                self.ax.grid(grid)

        elif self.plot_type == "scalar":
            self._display_error_message(f"스칼라 변수 '{self.variable_name}'는 그래프로 표시할 수 없습니다.")
            logger.info(f"PlotWindow: 스칼라 변수 {self.variable_name}는 플롯할 수 없음.")
        else:
            self._display_error_message(f"알 수 없거나 지원되지 않는 플롯 유형: {self.plot_type}")
            logger.warning(f"PlotWindow: 알 수 없는 플롯 유형 '{self.plot_type}' for {self.variable_name}.")

        self.canvas.draw()
        self.figure.tight_layout() # 레이아웃 조정
        logger.info(f"PlotWindow '{self.windowTitle()}' 플롯 새로고침 완료. Type: {self.plot_type}")

    def _display_error_message(self, message: str):
        """플롯 영역에 오류 메시지를 표시합니다."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, message,
                     horizontalalignment='center', verticalalignment='center',
                     transform=self.ax.transAxes, color='red', fontsize=12, wrap=True)
        self.canvas.draw()


    def get_current_plot_options(self) -> dict:
        """현재 플롯의 옵션을 반환합니다."""
        return self.options

    def update_plot_options(self, new_options: dict):
        """
        새로운 옵션으로 플롯을 업데이트하고 새로고침합니다.
        """
        self.options.update(new_options)
        self.refresh_plot()
        logger.info(f"PlotWindow '{self.windowTitle()}' 옵션 업데이트 및 새로고침 완료.")

    def export_plot(self):
        """
        현재 플롯을 이미지 파일로 내보냅니다.
        """
        default_filename = f"{self.variable_name}_plot.png"
        filepath, _ = QFileDialog.getSaveFileName(self, "플롯 저장", default_filename,
                                                  "PNG 이미지 (*.png);;JPEG 이미지 (*.jpg);;모든 파일 (*.*)")
        if filepath:
            try:
                self.figure.savefig(filepath, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "내보내기 성공", f"플롯을 '{filepath}'에 저장했습니다.")
                self._report_status(f"플롯 '{os.path.basename(filepath)}' 저장 완료.", 2000)
                logger.info(f"플롯 내보내기 성공: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "내보내기 오류", f"플롯 저장 중 오류 발생: {e}")
                self._report_status(f"플롯 내보내기 오류: {e}", 5000)
                logger.error(f"플롯 내보내기 실패: {e}")

    def closeEvent(self, event):
        """윈도우가 닫힐 때 Matplotlib figure를 닫아 메모리 누수를 방지합니다."""
        plt.close(self.figure)
        logger.info(f"PlotWindow '{self.windowTitle()}' 닫힘. ID: {self.plot_id}")
        super().closeEvent(event)


class PlotWindowManager:
    """
    Manages instances of PlotWindow dialogs.
    """
    def __init__(self, main_window, settings_manager, status_callback):
        self.main_window = main_window # 부모 윈도우 참조
        self.settings_manager = settings_manager
        self.status_callback = status_callback # 상태바 업데이트 콜백
        self.open_plot_windows = {} # {plot_id: PlotWindow instance}
        self.active_plot_window = None # 현재 활성화된 플롯 창 (가장 최근에 상호작용한 창)
        logger.info("PlotWindowManager 초기화.")

    def _report_status(self, message, timeout=2000):
        if self.status_callback:
            self.status_callback(message, timeout)
        else:
            logger.warning(f"PlotWindowManager: status_callback이 설정되지 않았습니다: {message}")


    def create_new_plot_window(self, plot_id: str, title: str, 
                               dataset_manager: DatasetManager, 
                               file_path: str, variable_name: str, plot_type: str, options: dict,
                               update_status_bar_callback=None):
        """
        새로운 플롯 창을 생성하거나, 이미 열려 있는 경우 해당 창을 활성화하고 데이터를 새로고침합니다.
        """
        if plot_id in self.open_plot_windows and self.open_plot_windows[plot_id].isVisible():
            plot_window = self.open_plot_windows[plot_id]
            plot_window.setWindowTitle(title) # 타이틀 업데이트 (선택 사항)
            plot_window.plot_type = plot_type # 플롯 타입 업데이트
            plot_window.options = options # 옵션 업데이트
            plot_window.refresh_plot() # 데이터 새로고침
            plot_window.activateWindow()
            plot_window.raise_()
            self.set_active_plot_window(plot_window)
            self._report_status(f"기존 플롯 창 '{title}' 활성화 및 새로고침.", 2000)
            logger.info(f"PlotWindowManager: 기존 플롯 창 '{title}' 활성화 및 새로고침.")
        else:
            plot_window = PlotWindow(
                plot_id, title, 
                dataset_manager, file_path, variable_name, plot_type, options, 
                update_status_bar_callback, parent=self.main_window # parent 설정
            )
            self.open_plot_windows[plot_id] = plot_window
            plot_window.show()
            plot_window.raise_()
            self.set_active_plot_window(plot_window)
            
            # 윈도우가 닫힐 때 딕셔너리에서 제거되도록 연결
            # lambda 함수를 사용하여 plot_id를 캡처
            plot_window.destroyed.connect(lambda: self._remove_plot_window(plot_id))
            self._report_status(f"새 플롯 창 '{title}' 생성 및 표시.", 2000)
            logger.info(f"PlotWindowManager: 새 플롯 창 '{title}' 생성 및 표시.")


    def _remove_plot_window(self, plot_id: str):
        """플롯 창이 닫힐 때 딕셔너리에서 제거합니다."""
        if plot_id in self.open_plot_windows:
            del self.open_plot_windows[plot_id]
            logger.info(f"PlotWindowManager: 플롯 창 '{plot_id}' 제거됨.")
            # 만약 닫힌 창이 활성화된 창이었다면 활성화된 창을 None으로 설정
            if self.active_plot_window and self.active_plot_window.plot_id == plot_id:
                self.active_plot_window = None


    def set_active_plot_window(self, window: QMainWindow):
        """현재 활성화된 플롯 창을 설정합니다."""
        self.active_plot_window = window
        logger.debug(f"PlotWindowManager: 활성화된 플롯 창 설정: {window.windowTitle()}")

    def get_active_plot_window(self):
        """현재 활성화된 플롯 창을 반환합니다."""
        if self.active_plot_window and self.active_plot_window.isVisible():
            return self.active_plot_window
        return None

    def close_all_plot_windows(self):
        """모든 열린 플롯 창을 닫습니다."""
        for plot_id in list(self.open_plot_windows.keys()):
            if plot_id in self.open_plot_windows: # 닫는 과정에서 제거될 수 있으므로 다시 확인
                self.open_plot_windows[plot_id].close()
        self.open_plot_windows.clear()
        self.active_plot_window = None
        self._report_status("모든 플롯 창 닫힘.", 2000)
        logger.info("PlotWindowManager: 모든 플롯 창 닫힘.")

    def get_current_plot_options(self):
        """
        현재 활성화된 플롯 창의 옵션을 반환합니다.
        """
        active_window = self.get_active_plot_window()
        if active_window:
            return active_window.get_current_plot_options()
        return None

    def update_plot_options(self, options):
        """
        현재 활성화된 플롯 창의 옵션을 업데이트하고 새로고침합니다.
        """
        active_window = self.get_active_plot_window()
        if active_window:
            active_window.update_plot_options(options)
            self._report_status(f"플롯 '{active_window.windowTitle()}' 옵션 업데이트 완료.", 2000)
        else:
            self._report_status("옵션을 업데이트할 활성화된 플롯 창이 없습니다.", 3000)
            logger.warning("PlotWindowManager: 옵션을 업데이트할 활성화된 플롯 창이 없습니다.")

    def export_current_plot(self):
        """
        현재 활성화된 플롯 창의 플롯을 이미지 파일로 내보냅니다.
        """
        active_window = self.get_active_plot_window()
        if active_window:
            active_window.export_plot()
        else:
            self._report_status("내보낼 플롯 창이 없습니다.", 3000)
            logger.warning("PlotWindowManager: 내보낼 플롯 창이 없습니다.")

    def current_tab_index(self):
        # 이 메서드는 PlotWindowManager가 QTabWidget을 관리하지 않으므로 의미가 없습니다.
        # 기존 코드에 남아있다면 제거하거나 경고를 로그합니다.
        logger.warning("PlotWindowManager: 'current_tab_index'는 QTabWidget 기반이 아니므로 사용되지 않습니다.")
        return -1 # 유효하지 않은 값 반환