import sys
import os
import json
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QMenuBar, QMenu, QAction,
                            QFileDialog, QComboBox, QLabel, QGroupBox, QSpinBox,
                            QDoubleSpinBox, QTabWidget, QTextEdit, QMessageBox,
                            QStatusBar, QGridLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pspython.pspyinstruments as pspyinstruments
import pspython.pspymethods as pspymethods

class ParameterGroup(QGroupBox):
    def __init__(self, title, parameters):
        super().__init__(title)
        self.parameters = {}
        layout = QGridLayout()
        
        row = 0
        for param, (min_val, max_val, default, step) in parameters.items():
            label = QLabel(param)
            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setValue(default)
            spinbox.setSingleStep(step)
            
            layout.addWidget(label, row, 0)
            layout.addWidget(spinbox, row, 1)
            self.parameters[param] = spinbox
            row += 1
            
        self.setLayout(layout)
    
    def get_values(self):
        return {param: widget.value() for param, widget in self.parameters.items()}

class ElectrochemicalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Electrochemical Sensor Interface")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize data storage
        self.current_data = {'voltage': [], 'current': []}
        self.all_measurements = []
        
        # Initialize instrument manager
        self.manager = pspyinstruments.InstrumentManager(new_data_callback=self.new_data_callback)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create left panel
        left_panel = self.create_left_panel()
        
        # Create right panel with tabs
        right_panel = self.create_right_panel()
        
        # Add panels to main layout
        layout.addWidget(left_panel, stretch=1)
        layout.addWidget(right_panel, stretch=3)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Data", self)
        open_action.triggered.connect(self.open_data)
        
        save_action = QAction("Save Data", self)
        save_action.triggered.connect(self.save_data)
        
        export_action = QAction("Export Plot", self)
        export_action.triggered.connect(self.export_plot)
        
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(export_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        calibrate_action = QAction("Calibrate", self)
        calibrate_action.triggered.connect(self.calibrate)
        
        analyze_action = QAction("Analyze Data", self)
        analyze_action.triggered.connect(self.analyze_data)
        
        tools_menu.addAction(calibrate_action)
        tools_menu.addAction(analyze_action)
        
    def create_left_panel(self):
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Device connection
        connection_group = QGroupBox("Device Connection")
        connection_layout = QVBoxLayout()
        self.connect_btn = QPushButton("Connect Device")
        self.connect_btn.clicked.connect(self.connect_device)
        connection_layout.addWidget(self.connect_btn)
        connection_group.setLayout(connection_layout)
        
        # Technique selection
        technique_group = QGroupBox("Measurement Technique")
        technique_layout = QVBoxLayout()
        self.technique_combo = QComboBox()
        self.technique_combo.addItems(["DPV", "CV", "SWV"])
        self.technique_combo.currentTextChanged.connect(self.update_parameters)
        technique_layout.addWidget(self.technique_combo)
        technique_group.setLayout(technique_layout)
        
        # Parameters
        self.parameters_group = self.create_parameter_groups()
        
        # Control buttons
        control_group = QGroupBox("Control")
        control_layout = QVBoxLayout()
        self.start_btn = QPushButton("Start Measurement")
        self.start_btn.clicked.connect(self.start_measurement)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_measurement)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_group.setLayout(control_layout)
        
        # Add all groups to left panel
        left_layout.addWidget(connection_group)
        left_layout.addWidget(technique_group)
        left_layout.addWidget(self.parameters_group)
        left_layout.addWidget(control_group)
        left_layout.addStretch()
        
        return left_panel
    
    def create_right_panel(self):
        tab_widget = QTabWidget()
        
        # Plot tab
        plot_tab = QWidget()
        plot_layout = QVBoxLayout()
        
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_tab.setLayout(plot_layout)
        
        # Data tab
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        data_layout.addWidget(self.data_text)
        data_tab.setLayout(data_layout)
        
        # Results tab
        results_tab = QWidget()
        results_layout = QVBoxLayout()
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        results_tab.setLayout(results_layout)
        
        # Add tabs
        tab_widget.addTab(plot_tab, "Plot")
        tab_widget.addTab(data_tab, "Data")
        tab_widget.addTab(results_tab, "Results")
        
        return tab_widget
    def create_parameter_groups(self):
        parameters = {
            "DPV": {
                "Start Potential (V)": (-2.0, 2.0, -0.5, 0.1),
                "End Potential (V)": (-2.0, 2.0, 0.5, 0.1),
                "Step Potential (V)": (0.001, 0.1, 0.005, 0.001),
                "Pulse Amplitude (V)": (0.001, 0.25, 0.05, 0.001),
                "Pulse Width (s)": (0.001, 1.0, 0.05, 0.001),
                "Scan Rate (V/s)": (0.01, 1.0, 0.05, 0.01)
            },
            "CV": {
                "Start Potential (V)": (-2.0, 2.0, -0.5, 0.1),
                "First Vertex Potential (V)": (-2.0, 2.0, 0.5, 0.1),
                "Second Vertex Potential (V)": (-2.0, 2.0, -0.5, 0.1),
                "Step Potential (V)": (0.001, 0.1, 0.01, 0.001),
                "Scan Rate (V/s)": (0.01, 10.0, 0.1, 0.01),
                "Number of Scans": (1, 10, 1, 1)
            },
            "SWV": {
                "Start Potential (V)": (-2.0, 2.0, -0.5, 0.1),
                "End Potential (V)": (-2.0, 2.0, 0.5, 0.1),
                "Step Potential (V)": (0.001, 0.1, 0.004, 0.001),
                "Amplitude (V)": (0.001, 0.25, 0.02, 0.001),
                "Frequency (Hz)": (1, 1000, 25, 1)
            }
        }
        
        self.param_widgets = {}
        for technique in parameters:
            self.param_widgets[technique] = ParameterGroup(f"{technique} Parameters", 
                                                         parameters[technique])
            self.param_widgets[technique].hide()
            
        # Show default technique parameters
        self.param_widgets[self.technique_combo.currentText()].show()
        return self.param_widgets[self.technique_combo.currentText()]

    def update_parameters(self, technique):
        self.parameters_group.hide()
        self.parameters_group = self.param_widgets[technique]
        self.parameters_group.show()
        
    def new_data_callback(self, new_data):
        try:
            # Update data storage
            for type, value in new_data.items():
                if 'potential' in type.lower():
                    self.current_data['voltage'].append(value)
                elif 'current' in type.lower():
                    self.current_data['current'].append(value)
            
            # Update plot
            self.update_plot()
            
            # Update data display
            self.update_data_display()
            
        except Exception as e:
            self.statusBar.showMessage(f"Error in data callback: {str(e)}")

    def update_plot(self):
        try:
            self.ax.clear()
            self.ax.plot(self.current_data['voltage'], self.current_data['current'])
            self.ax.set_xlabel('Potential (V)')
            self.ax.set_ylabel('Current (A)')
            self.ax.grid(True)
            self.canvas.draw()
        except Exception as e:
            self.statusBar.showMessage(f"Error updating plot: {str(e)}")

    def update_data_display(self):
        try:
            data_text = "Voltage (V)\tCurrent (A)\n"
            for v, i in zip(self.current_data['voltage'], self.current_data['current']):
                data_text += f"{v:.6f}\t{i:.6e}\n"
            self.data_text.setText(data_text)
        except Exception as e:
            self.statusBar.showMessage(f"Error updating data display: {str(e)}")

    def connect_device(self):
        try:
            if self.connect_btn.text() == "Connect Device":
                available_instruments = self.manager.discover_instruments()
                if available_instruments:
                    success = self.manager.connect(available_instruments[0])
                    if success == 1:
                        self.connect_btn.setText("Disconnect")
                        self.statusBar.showMessage("Connected to device")
                    else:
                        self.statusBar.showMessage("Connection failed")
                else:
                    self.statusBar.showMessage("No devices found")
            else:
                success = self.manager.disconnect()
                if success == 1:
                    self.connect_btn.setText("Connect Device")
                    self.statusBar.showMessage("Disconnected from device")
                else:
                    self.statusBar.showMessage("Error disconnecting")
        except Exception as e:
            self.statusBar.showMessage(f"Connection error: {str(e)}")

    def start_measurement(self):
        try:
            technique = self.technique_combo.currentText()
            params = self.param_widgets[technique].get_values()
            
            if technique == "DPV":
                # Create DPV method
                method = pspymethods.DPV()
                method.e_begin = params["Start Potential (V)"]
                method.e_end = params["End Potential (V)"]
                method.e_step = params["Step Potential (V)"]
                method.pulse_height = params["Pulse Amplitude (V)"]
                method.pulse_width = params["Pulse Width (s)"]
                method.scan_rate = params["Scan Rate (V/s)"]
                
            elif technique == "CV":
                # Create CV method
                method = pspymethods.CV()
                method.e_begin = params["Start Potential (V)"]
                method.e_vertex1 = params["First Vertex Potential (V)"]
                method.e_vertex2 = params["Second Vertex Potential (V)"]
                method.e_step = params["Step Potential (V)"]
                method.scan_rate = params["Scan Rate (V/s)"]
                method.n_scans = int(params["Number of Scans"])
                
            elif technique == "SWV":
                # Create SWV method
                method = pspymethods.SWV()
                method.e_begin = params["Start Potential (V)"]
                method.e_end = params["End Potential (V)"]
                method.e_step = params["Step Potential (V)"]
                method.e_amplitude = params["Amplitude (V)"]
                method.frequency = params["Frequency (Hz)"]
                
            # Clear previous data
            self.current_data = {'voltage': [], 'current': []}
            
            # Start measurement
            if self.manager.is_connected():
                measurement = self.manager.measure(method)
                if measurement is not None:
                    self.statusBar.showMessage("Measurement started")
                else:
                    self.statusBar.showMessage("Failed to start measurement")
            else:
                self.statusBar.showMessage("No device connected")
                
        except Exception as e:
            self.statusBar.showMessage(f"Error starting measurement: {str(e)}")

    def stop_measurement(self):
        try:
            self.manager.stop_measurement()
            self.statusBar.showMessage("Measurement stopped")
        except Exception as e:
            self.statusBar.showMessage(f"Error stopping measurement: {str(e)}")

    def connect_device(self):
        try:
            if self.connect_btn.text() == "Connect Device":
                available_instruments = self.manager.discover_instruments()
                if available_instruments:
                    # Get the first available device
                    device = available_instruments[0]
                    # Try to connect to the device
                    if self.manager.connect(device):
                        self.connect_btn.setText("Disconnect")
                        self.statusBar.showMessage(f"Connected to {device}")
                        # Enable measurement controls
                        self.start_btn.setEnabled(True)
                    else:
                        self.statusBar.showMessage("Failed to connect to device")
                else:
                    self.statusBar.showMessage("No devices found")
            else:
                # Disconnect from device
                if self.manager.disconnect():
                    self.connect_btn.setText("Connect Device")
                    self.statusBar.showMessage("Disconnected from device")
                    # Disable measurement controls
                    self.start_btn.setEnabled(False)
                else:
                    self.statusBar.showMessage("Error disconnecting")
        except Exception as e:
            self.statusBar.showMessage(f"Connection error: {str(e)}")
    def save_data(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Data", "", "CSV files (*.csv);;All Files (*)"
            )
            if filename:
                # Create a DataFrame and save the current data
                df = pd.DataFrame(self.current_data)
                df.to_csv(filename, index=False)
                self.statusBar.showMessage(f"Data saved to {filename}")
        except Exception as e:
            self.statusBar.showMessage(f"Error saving data: {str(e)}")
        
            

    def open_data(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Open Data", "", 
                                                    "CSV files (*.csv);;All Files (*)")
            if filename:
                df = pd.read_csv(filename)
                self.current_data = df.to_dict('list')
                self.update_plot()
                self.update_data_display()
                self.statusBar.showMessage(f"Data loaded from {filename}")
        except Exception as e:
            self.statusBar.showMessage(f"Error loading data: {str(e)}")

    def export_plot(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(self, "Export Plot", "", 
                                                    "PNG files (*.png);;PDF files (*.pdf);;All Files (*)")
            if filename:
                self.figure.savefig(filename, dpi=300, bbox_inches='tight')
                self.statusBar.showMessage(f"Plot exported to {filename}")
        except Exception as e:
            self.statusBar.showMessage(f"Error exporting plot: {str(e)}")

    def calibrate(self):
        try:
            # Add your calibration routine here
            calibration_dialog = QMessageBox()
            calibration_dialog.setWindowTitle("Calibration")
            calibration_dialog.setText("Running calibration...")
            calibration_dialog.exec_()
            
            # Example calibration result
            self.results_text.append("Calibration Results:\n")
            self.results_text.append("Sensitivity: 1.23 µA/mM\n")
            self.results_text.append("R² = 0.999\n")
            
        except Exception as e:
            self.statusBar.showMessage(f"Calibration error: {str(e)}")

    def analyze_data(self):
        try:
            if not self.current_data['voltage'] or not self.current_data['current']:
                self.statusBar.showMessage("No data to analyze")
                return

            # Basic analysis example
            current_array = np.array(self.current_data['current'])
            voltage_array = np.array(self.current_data['voltage'])
            
            peak_current = np.max(np.abs(current_array))
            peak_voltage = voltage_array[np.argmax(np.abs(current_array))]
            
            analysis_results = (
                "Analysis Results:\n"
                f"Peak Current: {peak_current:.2e} A\n"
                f"Peak Voltage: {peak_voltage:.3f} V\n"
                f"Data Points: {len(current_array)}\n"
                "------------------------\n"
            )
            
            self.results_text.append(analysis_results)
            
        except Exception as e:
            self.statusBar.showMessage(f"Analysis error: {str(e)}")

    def closeEvent(self, event):
        try:
            if hasattr(self, 'manager'):
                if self.connect_btn.text() == "Disconnect":
                    self.manager.disconnect()
            event.accept()
        except Exception as e:
            print(f"Error during shutdown: {str(e)}")
            event.accept()


def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # Modern look across platforms
        
        # Set application-wide stylesheet
        stylesheet = """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px;
                min-height: 25px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
        """
        app.setStyleSheet(stylesheet)
        
        window = ElectrochemicalApp()
        window.show()
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()