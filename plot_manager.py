# C:\Users\thhan\oceanocal_v2\plot_manager.py
# This file defines the PlotWindow (a single plot dialog)

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QMessageBox, QMenu, QFileDialog, QApplication # Added QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer, pyqtSlot, Qt 
from PyQt6.QtGui import QAction, QImage # Added QImage
import plotly.graph_objects as go
import plotly.io as pio
import os
import xarray as xr
import numpy as np
import pandas as pd 
import logging
import io # Added io

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
        self.data_var = None 
        self.ds = None 
        self.fig = None 

        self.browser = QWebEngineView()
        self.browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.browser.customContextMenuRequested.connect(self._create_web_context_menu)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        self.setLayout(layout)

        if self.filepath and self.var_name:
            self._load_data_and_plot()
        else:
            QMessageBox.critical(self, "초기화 오류", "플롯에 필요한 파일 경로 또는 변수 이름이 없습니다.")
            logging.error("PlotWindow initialized without filepath or var_name.")

        logging.info(f"PlotWindow for '{var_name}' initialized.")

    def _load_data_and_plot(self):
        try:
            self.ds = xr.open_dataset(self.filepath)
            self.data_var = self.ds[self.var_name]
            self.plot_data()
        except Exception as e:
            QMessageBox.critical(self, "데이터 로드 오류", f"데이터를 로드하는 중 오류 발생:\\n{e}")
            logging.error(f"PlotWindow data load error for {self.filepath}, {self.var_name}: {e}", exc_info=True)


    def _create_web_context_menu(self, pos):
        menu = QMenu(self)
        export_html_action = QAction("플롯 내보내기 (HTML)", self)
        export_html_action.triggered.connect(self.export_plot)
        menu.addAction(export_html_action)

        export_png_action = QAction("플롯 내보내기 (PNG)", self) 
        export_png_action.triggered.connect(self.export_as_png)
        menu.addAction(export_png_action)

        export_pdf_action = QAction("플롯 내보내기 (PDF)", self)
        export_pdf_action.triggered.connect(self.export_as_pdf)
        menu.addAction(export_pdf_action)

        export_csv_action = QAction("데이터 내보내기 (CSV)", self) 
        export_csv_action.triggered.connect(self.export_as_csv)
        menu.addAction(export_csv_action)

        menu.addSeparator() # Separator before clipboard actions

        copy_image_action = QAction("플롯 이미지 복사", self)
        copy_image_action.triggered.connect(self.copy_image_to_clipboard)
        menu.addAction(copy_image_action)

        copy_csv_action = QAction("데이터 (CSV) 복사", self)
        copy_csv_action.triggered.connect(self.copy_csv_to_clipboard)
        menu.addAction(copy_csv_action)

        menu.exec(self.browser.mapToGlobal(pos))

    def plot_data(self):
        if self.data_var is None:
            logging.warning("No data_var to plot in PlotWindow.")
            return

        self.fig = go.Figure() 
        dims = self.data_var.dims
        data_values = self.data_var.values

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
            self.fig.add_trace(go.Scatter(x=x_data, y=data_values, mode='lines+markers', name=self.var_name))
            self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
        elif self.plot_type == "1D_profile" and ('depth' in dims or 'pressure' in dims):
            x_data = data_values
            y_data = self.data_var['depth'].values if 'depth' in dims else self.data_var['pressure'].values
            self.fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines+markers', name=self.var_name))
            self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label, yaxis_autorange="reversed")
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
                self.fig.add_trace(go.Scattergeo(
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
                self.fig.update_layout(geo_scope='world')
            else: 
                self.fig.add_trace(go.Heatmap(
                    x=lon_data, y=lat_data, z=data_values,
                    colorscale=colorscale,
                    colorbar=dict(title=cbar_label)
                ))
                self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
                self.fig.update_yaxes(autorange="reversed") 

                for overlay_filename in self.settings_manager.get_active_overlays():
                    overlay_traces = get_overlay_traces(overlay_filename)
                    for trace in overlay_traces:
                        self.fig.add_trace(trace)

                self.fig.update_layout(geo_scope='world')
                self.fig.update_geos(
                    lataxis_range=[min(lat_data), max(lat_data)], 
                    lonaxis_range=[min(lon_data), max(lon_data)]  
                )
        
        elif self.plot_type == "2D_section" and len(dims) == 2:
            x_dim_name, y_dim_name = dims[0], dims[1] 
            x_data = self.data_var[x_dim_name].values
            y_data = self.data_var[y_dim_name].values

            if self.data_var.ndim > 2: 
                data_values = self.data_var.squeeze().values

            self.fig.add_trace(go.Heatmap(
                x=x_data, y=y_data, z=data_values,
                colorscale=colorscale,
                colorbar=dict(title=cbar_label)
            ))
            self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
            if 'depth' in y_dim_name.lower() or 'pressure' in y_dim_name.lower():
                self.fig.update_yaxes(autorange="reversed")
        
        elif self.plot_type in ["3D_time_map", "3D_depth_map", "3D_time_section", "3D_generic"]: 
            if len(dims) >= 3:
                slice_dim_name = None 
                if self.plot_type in ["3D_time_map", "3D_time_section"] and 'time' in dims:
                    slice_dim_name = 'time'
                elif self.plot_type == "3D_depth_map" and ('depth' in dims or 'pressure' in dims):
                    slice_dim_name = [d for d in dims if d == 'depth' or d == 'pressure'][0]
                elif len(dims) >=3: 
                    slice_dim_name = dims[0]

                if slice_dim_name and slice_dim_name in self.data_var.coords:
                    slice_coords = self.data_var[slice_dim_name].values
                    frames = []
                    max_slices_for_slider = min(len(slice_coords), 50) 

                    for i in range(max_slices_for_slider):
                        sliced_data_var = self.data_var.isel({slice_dim_name: i})
                        if len(sliced_data_var.dims) == 2:
                            frame_x_data = sliced_data_var[sliced_data_var.dims[0]].values
                            frame_y_data = sliced_data_var[sliced_data_var.dims[1]].values
                            frame_z_data = sliced_data_var.values
                            
                            frame_trace = go.Heatmap(x=frame_x_data, y=frame_y_data, z=frame_z_data, 
                                                     colorscale=colorscale, colorbar=dict(title=cbar_label))
                            frame_name = f"{slice_dim_name}={slice_coords[i]}"
                            frames.append(go.Frame(data=[frame_trace], name=frame_name))

                    if frames:
                        self.fig.frames = frames
                        self.fig.add_trace(frames[0].data[0])

                        sliders = [dict(
                            steps=[dict(method='animate',
                                        args=[[f.name], dict(mode='immediate', 
                                                             frame=dict(redraw=True, duration=0), 
                                                             transition=dict(duration=0))],
                                        label=str(slice_coords[idx])) for idx, f in enumerate(self.fig.frames)],
                            transition=dict(duration=0),
                            x=0.1, 
                            len=0.9, 
                            currentvalue=dict(font=dict(size=12), prefix=f"{slice_dim_name}: ", visible=True, xanchor='right'),
                        )]
                        self.fig.update_layout(sliders=sliders)
                        
                        initial_frame_dims = frames[0].data[0]
                        x_axis_title_frame = sliced_data_var.dims[0]
                        y_axis_title_frame = sliced_data_var.dims[1]
                        self.fig.update_layout(xaxis_title=x_axis_title_frame, yaxis_title=y_axis_title_frame)
                        if 'depth' in y_axis_title_frame.lower() or 'pressure' in y_axis_title_frame.lower():
                             self.fig.update_yaxes(autorange="reversed")
                    else: 
                        QMessageBox.warning(self, "플롯 오류", f"3D 변수 '{self.var_name}'에 대한 프레임을 생성할 수 없습니다.")
                        logging.warning(f"Could not create frames for 3D variable {self.var_name}.")
                        return
                else: 
                    QMessageBox.warning(self, "플롯 오류", f"3D 변수 '{self.var_name}'에 대한 슬라이스 차원을 결정할 수 없습니다.")
                    logging.warning(f"Could not determine slice dimension for 3D variable {self.var_name}.")
                    return
            else: 
                QMessageBox.warning(self, "플롯 오류", f"변수 '{self.var_name}'는 3D 플롯 유형에 대해 충분한 차원을 가지고 있지 않습니다.")
                logging.warning(f"Variable {self.var_name} does not have enough dimensions for 3D plot type.")
                return

        elif self.plot_type == "1D_generic":
            x_data = np.arange(len(data_values)) 
            if len(dims) > 0 and dims[0] in self.data_var.coords:
                x_data = self.data_var[dims[0]].values
            self.fig.add_trace(go.Scatter(x=x_data, y=data_values, mode='lines+markers', name=self.var_name))
            self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)

        elif self.plot_type == "2D_generic":
            if len(dims) == 2:
                x_data = self.data_var[dims[0]].values
                y_data = self.data_var[dims[1]].values
                self.fig.add_trace(go.Heatmap(
                    x=x_data, y=y_data, z=data_values,
                    colorscale=colorscale,
                    colorbar=dict(title=cbar_label)
                ))
                self.fig.update_layout(xaxis_title=xaxis_label, yaxis_title=yaxis_label)
            else:
                QMessageBox.warning(self, "플롯 오류", f"2D 변수 '{self.var_name}' 플롯에 실패했습니다. 차원: {dims}")
                logging.warning(f"Failed to plot 2D variable {self.var_name}. Dims: {dims}")
                return
        else:
            QMessageBox.warning(self, "플롯 오류", f"플롯 유형 '{self.plot_type}'을(를) 처리할 수 없습니다.")
            logging.warning(f"Unhandled plot type: {self.plot_type} for variable {self.var_name}.")
            return

        self.fig.update_layout(
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
        html = pio.to_html(self.fig, include_plotlyjs='cdn') 
        self.browser.setHtml(html)
        logging.info(f"Plot for '{self.var_name}' displayed successfully.")

    def get_current_plot_options(self):
        return self.options

    def update_plot_options(self, new_options):
        self.options.update(new_options)
        self.plot_data()
        logging.info(f"Plot options updated for '{self.var_name}'.")

    def export_as_png(self):
        if not self.fig:
            QMessageBox.warning(self, "Export Error", "No plot figure available to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Export as PNG", 
                                                   f"{self.var_name}_plot.png", 
                                                   "PNG Files (*.png);;All Files (*)")
        if file_name:
            try:
                pio.write_image(self.fig, file_name, format='png')
                QMessageBox.information(self, "Export Successful", f"Plot successfully exported to:\n{file_name}")
                logging.info(f"Plot '{self.var_name}' exported as PNG to {file_name}")
            except Exception as e:
                error_message = f"Error exporting plot to PNG:\n{e}"
                if "kaleido" in str(e).lower() : 
                    error_message += "\n\nPlease ensure 'python-kaleido' package is installed (`pip install kaleido`)."
                QMessageBox.critical(self, "Export Error", error_message)
                logging.error(f"Error exporting plot {self.var_name} to PNG: {e}", exc_info=True)

    def export_as_pdf(self):
        if not self.fig:
            QMessageBox.warning(self, "Export Error", "No plot figure available to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Export as PDF", 
                                                   f"{self.var_name}_plot.pdf", 
                                                   "PDF Files (*.pdf);;All Files (*)")
        if file_name:
            try:
                pio.write_image(self.fig, file_name, format='pdf')
                QMessageBox.information(self, "Export Successful", f"Plot successfully exported to:\n{file_name}")
                logging.info(f"Plot '{self.var_name}' exported as PDF to {file_name}")
            except Exception as e:
                error_message = f"Error exporting plot to PDF:\n{e}"
                if "kaleido" in str(e).lower() : 
                    error_message += "\n\nPlease ensure 'python-kaleido' package is installed (`pip install kaleido`)."
                QMessageBox.critical(self, "Export Error", error_message)
                logging.error(f"Error exporting plot {self.var_name} to PDF: {e}", exc_info=True)

    def export_as_csv(self):
        if self.data_var is None:
            QMessageBox.warning(self, "Export Error", "No data available to export as CSV.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Export as CSV", 
                                                   f"{self.var_name}_data.csv", 
                                                   "CSV Files (*.csv);;All Files (*)")
        if file_name:
            try:
                df = self.data_var.to_dataframe()
                if isinstance(df.index, pd.MultiIndex):
                    df = df.reset_index()
                df.to_csv(file_name, index=False, encoding='utf-8')
                QMessageBox.information(self, "Export Successful", f"Data successfully exported to CSV:\n{file_name}")
                logging.info(f"Data for '{self.var_name}' exported as CSV to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error exporting data to CSV:\n{e}")
                logging.error(f"Error exporting data for {self.var_name} to CSV: {e}", exc_info=True)

    def copy_image_to_clipboard(self):
        if not self.fig:
            QMessageBox.warning(self, "Clipboard Error", "No plot figure available to copy.")
            return
        try:
            img_bytes = pio.to_image(self.fig, format='png')
            q_image = QImage()
            q_image.loadFromData(img_bytes)
            
            if not q_image.isNull():
                QApplication.clipboard().setImage(q_image)
                QMessageBox.information(self, "Clipboard Success", "Plot image copied to clipboard.")
                logging.info(f"Plot image for '{self.var_name}' copied to clipboard.")
            else:
                QMessageBox.warning(self, "Clipboard Error", "Failed to convert plot image for clipboard.")
                logging.error(f"Failed to convert plot image to QImage for {self.var_name}.")
        except Exception as e:
            QMessageBox.critical(self, "Clipboard Error", f"Error copying plot image to clipboard:\n{e}")
            logging.error(f"Error copying plot image for {self.var_name} to clipboard: {e}", exc_info=True)

    def copy_csv_to_clipboard(self):
        if self.data_var is None:
            QMessageBox.warning(self, "Clipboard Error", "No data available to copy as CSV.")
            return
        try:
            df = self.data_var.to_dataframe()
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
            
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_string = csv_buffer.getvalue()
            
            QApplication.clipboard().setText(csv_string)
            QMessageBox.information(self, "Clipboard Success", "Data (CSV format) copied to clipboard.")
            logging.info(f"Data for '{self.var_name}' (CSV format) copied to clipboard.")
        except Exception as e:
            QMessageBox.critical(self, "Clipboard Error", f"Error copying CSV data to clipboard:\n{e}")
            logging.error(f"Error copying CSV data for {self.var_name} to clipboard: {e}", exc_info=True)

    def export_plot(self): 
        file_name, _ = QFileDialog.getSaveFileName(self, "플롯 내보내기", f"{self.var_name}_plot.html", "HTML Files (*.html)") 
        if file_name:
            try:
                self.browser.page().toHtml(lambda html_content: self._save_html_content(file_name, html_content))
                logging.info(f"Plot export initiated for {self.var_name} to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "내보내기 오류", f"플롯 내보내기 중 오류 발생:\\n{e}")
                logging.error(f"Error exporting plot: {e}", exc_info=True)

    @pyqtSlot(str)
    def _save_html_content(self, file_name, html_content):
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(html_content)
            QMessageBox.information(self, "내보내기 완료", f"플롯이 성공적으로 내보내졌습니다:\\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "내보내기 오류", f"파일 저장 중 오류 발생:\\n{e}")
            logging.error(f"Error saving exported plot HTML: {e}", exc_info=True)
