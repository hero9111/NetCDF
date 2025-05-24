# C:\Users\thhan\oceanocal_v2\plot_manager.py
# This file defines the PlotWindow (a single plot dialog)

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QMessageBox, QMenu
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer, pyqtSlot, Qt # Import Qt for context menu policy
from PyQt6.QtGui import QAction
import plotly.graph_objects as go
import plotly.io as pio
import os
import xarray as xr
import numpy as np
import logging

from .handlers.colorbar_handler import get_colormap
from .handlers.overlay_handler import get_overlay_traces

class PlotWindow(QDialog):
    def __init__(self, parent=None, settings_manager=None, var_name=None, plot_type=None, options=None, filepath=None):
        super().__init__(parent)
        self.setWindowTitle(f"Plot: {var_name}")
        self.settings_manager = settings_manager
        self.filepath = filepath
        self.var_name = var_name
        self.plot_type = plot_type
        self.options = options if options is not None else {}
        self.data_var = None # xarray DataArray for the current variable
        self.ds = None # xarray Dataset for the current file

        self.browser = QWebEngineView()
        self.browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.browser.customContextMenuRequested.connect(self._create_web_context_menu)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        self.setLayout(layout)

        # Load data and plot only if essential parameters are provided
        if self.filepath and self.var_name:
            self._load_data_and_plot()
        else:
            QMessageBox.critical(self, "초기화 오류", "플롯에 필요한 파일 경로 또는 변수 이름이 없습니다.")
            logging.error("PlotWindow initialized without filepath or var_name.")

        logging.info(f"PlotWindow for '{var_name}' initialized.")

    def _load_data_and_plot(self):
        try:
            # Re-open the dataset to ensure it's available for this PlotWindow
            # Or, better, DatasetManager should provide a way to get already open dataset
            # For simplicity, for now, let's assume direct xarray load in this window.
            # In a full application, pass the DatasetManager instance to PlotWindowManager,
            # and then to PlotWindow, so it can use already opened datasets.
            # For now, this will open the file again for each plot window.
            self.ds = xr.open_dataset(self.filepath)
            self.data_var = self.ds[self.var_name]
            self.plot_data()
        except Exception as e:
            QMessageBox.critical(self, "데이터 로드 오류", f"데이터를 로드하는 중 오류 발생:\\n{e}")
            logging.error(f"PlotWindow data load error for {self.filepath}, {self.var_name}: {e}", exc_info=True)


    def _create_web_context_menu(self, pos):
        menu = QMenu(self)
        export_action = QAction("플롯 내보내기 (HTML)", self)
        export_action.triggered.connect(self.export_plot)
        menu.addAction(export_action)
        menu.exec(self.browser.mapToGlobal(pos))

    def plot_data(self):
        if self.data_var is None:
            logging.warning("No data_var to plot in PlotWindow.")
            return

        fig = go.Figure()
        dims = self.data_var.dims
        data_values = self.data_var.values

        # Get default plot options from settings if not explicitly provided
        default_plot_options = self.settings_manager.get_default_plot_options() if self.settings_manager else {}
        current_options = {**default_plot_options, **self.options}

        title_text = current_options.get('title_text', f"{self.var_name} Plot")
        xaxis_label = current_options.get('xaxis_label', dims[0] if len(dims) > 0 else "")
        yaxis_label = current_options.get('yaxis_label', dims[1] if len(dims) > 1 else "")
        cbar_label = current_options.get('cbar_label', self.data_var.attrs.get('units', ''))
        plot_font_family = current_options.get('plot_font_family', 'Arial')
        plot_font_size = current_options.get('plot_font_size', 12)
        cmap_name = current_options.get('cmap', 'jet')
        colorscale = get_colormap(cmap_name)

        if self.plot_type == "1D_time_series" and 'time' in dims:
            x_data = self.data_var['time'].values
            fig.add_trace(go.Scatter(x=x_data, y=data_values, mode='lines+markers', name=self.var_name))
            fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
        elif self.plot_type == "1D_profile" and ('depth' in dims or 'pressure' in dims):
            x_data = data_values
            y_data = self.data_var['depth'].values if 'depth' in dims else self.data_var['pressure'].values
            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines+markers', name=self.var_name))
            fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label, yaxis_autorange="reversed")
        elif self.plot_type == "2D_map" and 'lat' in dims and 'lon' in dims:
            lat_data = self.data_var['lat'].values
            lon_data = self.data_var['lon'].values

            if self.data_var.ndim > 2:
                slice_dim = [d for d in dims if d not in ['lat', 'lon']]
                if slice_dim:
                    data_values = self.data_var.isel({slice_dim[0]: 0}).values
                else:
                    data_values = self.data_var.squeeze().values

            if self.data_var.ndim == 1 and 'lat' in self.data_var.coords and 'lon' in self.data_var.coords:
                fig.add_trace(go.Scattergeo(
                    lat=self.data_var['lat'].values,
                    lon=self.data_var['lon'].values,
                    mode='markers',
                    marker=dict(
                        color=data_values,
                        colorscale=colorscale,
                        cmin=np.nanmin(data_values),
                        cmax=np.nanmax(data_values),
                        colorbar=dict(title=cbar_label)
                    ),
                    name=self.var_name
                ))
                fig.update_layout(geo_scope='world')
                html = pio.to_html(fig, include_plotlyjs='cdn')
                self.browser.setHtml(html)
                return

            fig.add_trace(go.Heatmap(
                x=lon_data, y=lat_data, z=data_values,
                colorscale=colorscale,
                colorbar=dict(title=cbar_label)
            ))
            fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
            fig.update_yaxes(autorange="reversed")

            for overlay_filename in self.settings_manager.get_active_overlays():
                overlay_traces = get_overlay_traces(overlay_filename)
                for trace in overlay_traces:
                    fig.add_trace(trace)

            fig.update_layout(geo_scope='world')
            fig.update_geos(
                lataxis_range=[min(lat_data), max(lat_data)],
                lonaxis_range=[min(lon_data), max(lon_data)]
            )

        elif self.plot_type == "2D_section" and len(dims) == 2:
            x_dim, y_dim = dims[0], dims[1]
            x_data = self.data_var[x_dim].values
            y_data = self.data_var[y_dim].values

            if self.data_var.ndim > 2:
                data_values = self.data_var.squeeze().values

            fig.add_trace(go.Heatmap(
                x=x_data, y=y_data, z=data_values,
                colorscale=colorscale,
                colorbar=dict(title=cbar_label)
            ))
            fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
            if 'depth' in y_dim.lower() or 'pressure' in y_dim.lower():
                fig.update_yaxes(autorange="reversed")
        elif self.plot_type == "3D_time_map" or self.plot_type == "3D_depth_map" or self.plot_type == "3D_time_section" or self.plot_type == "3D_generic":
            if len(dims) >= 3:
                slice_dim = None
                if self.plot_type in ["3D_time_map", "3D_time_section"] and 'time' in dims:
                    slice_dim = 'time'
                elif self.plot_type == "3D_depth_map" and ('depth' in dims or 'pressure' in dims):
                    slice_dim = [d for d in dims if d == 'depth' or d == 'pressure'][0]
                elif len(dims) >=3:
                    slice_dim = dims[0]

                if slice_dim and slice_dim in self.data_var.coords:
                    slice_coords = self.data_var[slice_dim].values

                    frames = []
                    buttons = []
                    max_slices_for_buttons = min(len(slice_coords), 50)

                    for i in range(max_slices_for_buttons):
                        sliced_data_var = self.data_var.isel({slice_dim: i})
                        if len(sliced_data_var.dims) == 2:
                            if 'lat' in sliced_data_var.dims and 'lon' in sliced_data_var.dims:
                                x_data = sliced_data_var['lon'].values
                                y_data = sliced_data_var['lat'].values
                                z_data = sliced_data_var.values
                                frame_trace = go.Heatmap(x=x_data, y=y_data, z=z_data, colorscale=colorscale,
                                                         colorbar=dict(title=cbar_label))
                                frame_name = f"{slice_dim}={slice_coords[i]}"
                                frames.append(go.Frame(data=[frame_trace], name=frame_name))
                                buttons.append(dict(label=str(slice_coords[i]),
                                                    method="animate",
                                                    args=[[frame_name], {"mode": "immediate", "frame": {"redraw": True, "duration": 0}, "transition": {"duration": 0}}]))
                            elif len(sliced_data_var.dims) == 2:
                                x_data = sliced_data_var[sliced_data_var.dims[0]].values
                                y_data = sliced_data_var[sliced_data_var.dims[1]].values
                                z_data = sliced_data_var.values
                                frame_trace = go.Heatmap(x=x_data, y=y_data, z=z_data, colorscale=colorscale,
                                                         colorbar=dict(title=cbar_label))
                                frame_name = f"{slice_dim}={slice_coords[i]}"
                                frames.append(go.Frame(data=[frame_trace], name=frame_name))
                                buttons.append(dict(label=str(slice_coords[i]),
                                                    method="animate",
                                                    args=[[frame_name], {"mode": "immediate", "frame": {"redraw": True, "duration": 0}, "transition": {"duration": 0}}]))
                                if 'depth' in sliced_data_var.dims[1].lower() or 'pressure' in sliced_data_var.dims[1].lower():
                                    fig.update_yaxes(autorange="reversed")

                    if frames:
                        fig.frames = frames
                        sliders = [dict(
                            steps=[dict(method='animate',
                                        args=[[f.name], dict(mode='immediate', frame=dict(redraw=True, duration=0), transition=dict(duration=0))],
                                        label=f.name.split('=')[-1]) for f in fig.frames],
                            transition=dict(duration=0),
                            x=0.1,
                            len=0.9,
                            currentvalue=dict(font=dict(size=12), prefix=f"{slice_dim}: ", xanchor='right'),
                            yanchor='top'
                        )]
                        fig.update_layout(sliders=sliders)
                        if frames:
                            fig.add_trace(frames[0].data[0])
                        if len(dims) >= 2:
                            fig.update_layout(xaxis_title=dims[0], yaxis_title=dims[1])
            else:
                QMessageBox.warning(self, "플롯 오류", f"3D 변수 '{self.var_name}'에 대한 슬라이스를 생성할 수 없습니다.")
                logging.warning(f"Could not create slices for 3D variable {self.var_name}.")
                return

        elif self.plot_type == "1D_generic":
            x_data = np.arange(len(data_values))
            if len(dims) > 0:
                try:
                    x_data = self.data_var[dims[0]].values
                except KeyError:
                    pass
            fig.add_trace(go.Scatter(x=x_data, y=data_values, mode='lines+markers', name=self.var_name))
            fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)

        elif self.plot_type == "2D_generic":
            if len(dims) == 2:
                x_data = self.data_var[dims[0]].values
                y_data = self.data_var[dims[1]].values
                fig.add_trace(go.Heatmap(
                    x=x_data, y=y_data, z=data_values,
                    colorscale=colorscale,
                    colorbar=dict(title=cbar_label)
                ))
                fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
            else:
                QMessageBox.warning(self, "플롯 오류", f"2D 변수 '{self.var_name}' 플롯에 실패했습니다. 차원: {dims}")
                logging.warning(f"Failed to plot 2D variable {self.var_name}. Dims: {dims}")
                return

        else:
            QMessageBox.warning(self, "플롯 오류", f"플롯 유형 '{self.plot_type}'을(를) 처리할 수 없습니다.")
            logging.warning(f"Unhandled plot type: {self.plot_type} for variable {self.var_name}.")
            return

        fig.update_layout(
            title=title_text,
            title_font_family=current_options.get('title_font_family', 'Arial'),
            title_font_size=current_options.get('title_font_size', 16),
            font=dict(
                family=plot_font_family,
                size=plot_font_size,
                color="black" if self.settings_manager.get_app_setting('theme') != 'dark' else "white"
            ),
            hovermode="closest",
            template="plotly_white" if self.settings_manager.get_app_setting('theme') != 'dark' else "plotly_dark"
        )
        html = pio.to_html(fig, include_plotlyjs='cdn')
        self.browser.setHtml(html)
        logging.info(f"Plot for '{self.var_name}' displayed successfully.")

    def get_current_plot_options(self):
        return self.options

    def update_plot_options(self, new_options):
        self.options.update(new_options)
        self.plot_data()
        logging.info(f"Plot options updated for '{self.var_name}'.")

    def export_plot(self):
        file_name, _ = QMessageBox.getSaveFileName(self, "플롯 내보내기", f"{self.var_name}_plot.html", "HTML Files (*.html)")
        if file_name:
            try:
                # Get the current HTML content from the QWebEngineView page
                self.browser.page().toHtml(lambda html_content: self._save_html_content(file_name, html_content))
                logging.info(f"Plot export initiated for {self.var_name} to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "내보내기 오류", f"플롯 내보내기 중 오류 발생:\\n{e}")
                logging.error(f"Error exporting plot: {e}", exc_info=True)

    @pyqtSlot(str)
    def _save_html_content(self, file_name, html_content):
        """Callback to save HTML content after it's retrieved from QWebEngineView."""
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(html_content)
            QMessageBox.information(self, "내보내기 완료", f"플롯이 성공적으로 내보내졌습니다:\\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "내보내기 오류", f"파일 저장 중 오류 발생:\\n{e}")
            logging.error(f"Error saving exported plot HTML: {e}", exc_info=True)