import sys
# import zmq
# from consts import *

import pandas as pd
import zmq
from datetime import datetime
from qgis.core import *
from qgis.utils import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
from PyQt5 import QtTest, QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

# from PyQt5.QtWidgets import (
#     QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog,
#     QSlider, QComboBox, QTableWidget, QTableWidgetItem
# )
# from PyQt5.QtCore import QTimer, Qt
# import pandas as pd



class ZMQPlayer(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize ZMQ context
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://127.0.0.1:1137")

        self.subscriber_socket = self.context.socket(zmq.SUB)
        self.subscriber_socket.connect("tcp://127.0.0.1:1137")
        self.subscriber_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # Define global variables
        self.is_playing = False
        self.is_stopped = False
        self.current_speed = 1.0
        self.current_position = 0

        self.data_df = pd.DataFrame()

        # Setup UI
        self.init_ui()

        # Setup timer for playback and subscriber
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.stream_data)

        self.subscriber_timer = QTimer()
        self.subscriber_timer.timeout.connect(self.receive_data)
        self.subscriber_timer.start(100)

    def init_ui(self):
        layout = QVBoxLayout()

        # File selection button
        self.file_button = QPushButton("Select File")
        self.file_button.clicked.connect(self.load_file)
        layout.addWidget(self.file_button)

        # Play, Pause, Stop buttons
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play)
        layout.addWidget(self.play_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause)
        layout.addWidget(self.pause_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        layout.addWidget(self.stop_button)

        # Slider for seeking
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.seek)
        layout.addWidget(self.slider)

        # Dropdown for playback speed
        self.speed_dropdown = QComboBox()
        self.speed_dropdown.addItems(["0.25x", "0.5x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_dropdown.setCurrentText("1x")
        self.speed_dropdown.currentTextChanged.connect(self.set_speed)
        layout.addWidget(self.speed_dropdown)

        # Subscriber Output Table
        self.subscriber_table = QTableWidget()
        layout.addWidget(self.subscriber_table)

        self.setLayout(layout)
        self.setWindowTitle("ZMQ Player")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.data_df = pd.read_csv(file_path)

            # Use GPS Date & Time as the timestamp
            self.data_df["GPS Date & Time"] = pd.to_datetime(self.data_df["GPS Date & Time"], errors='coerce')
            self.data_df = self.data_df.dropna(subset=["GPS Date & Time"])
            self.data_df["unix_time"] = self.data_df["GPS Date & Time"].apply(lambda x: int(x.timestamp()))

            self.slider.setMaximum(len(self.data_df) - 1)

            # Update subscriber table to match CSV columns
            self.subscriber_table.setColumnCount(len(self.data_df.columns))
            self.subscriber_table.setHorizontalHeaderLabels(self.data_df.columns)

    def play(self):
        self.is_playing = True
        self.is_stopped = False
        self.playback_timer.start(int(1000 / self.current_speed))

    def pause(self):
        self.is_playing = False
        self.playback_timer.stop()

    def stop(self):
        self.is_playing = False
        self.is_stopped = True
        self.playback_timer.stop()
        self.current_position = 0
        self.slider.setValue(0)

    def seek(self):
        self.current_position = self.slider.value()

    def set_speed(self, speed_text):
        self.current_speed = float(speed_text.replace("x", ""))
        if self.is_playing:
            self.playback_timer.start(int(10 / self.current_speed))

    def stream_data(self):
        if self.is_playing and self.current_position < len(self.data_df):
            row = self.data_df.iloc[self.current_position]
            message = "|".join(str(row[col]) for col in self.data_df.columns)
            self.socket.send_string(message)
            self.current_position += 1
            self.slider.setValue(self.current_position)
        elif self.current_position >= len(self.data_df):
            self.stop()

    def receive_data(self):
        try:
            while True:
                message = self.subscriber_socket.recv_string(flags=zmq.NOBLOCK)
                row_data = message.split("|")
                row_count = self.subscriber_table.rowCount()
                self.subscriber_table.insertRow(row_count)
                for col_index, value in enumerate(row_data):
                    self.subscriber_table.setItem(row_count, col_index, QTableWidgetItem(value))
        except zmq.Again:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = ZMQPlayer()
    player.show()
    sys.exit(app.exec_())
