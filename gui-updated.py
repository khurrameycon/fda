from sys import flags

# TODO Speed player changed 1000, and current time

import zmq
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import *
import pandas as pd
import io
import sys
import os
from qgis.PyQt.QtGui import QImage, QPainter
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pickle
from qgis.core import QgsMarkerSymbol

HEADING_2 = 0.0


def update_angle(new_angle):
    global HEADING_2
    HEADING_2 = new_angle


class MyDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # Add QgsMessageBar at the top left
        self.bar = QgsMessageBar()
        self.bar.setFixedSize(600, 30)
        self.layout().addWidget(self.bar, 0, 0, 1, 2)

        # Add QDialogButtonBox at the top right
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonbox.button(QDialogButtonBox.Ok).setFixedSize(60, 30)
        self.buttonbox.accepted.connect(self.run)
        self.layout().addWidget(self.buttonbox, 0, 1, 1, 1)

        # Set style sheet for buttonbox
        self.buttonbox.setStyleSheet("background: black; color: white; border: 1px solid red;")

        # Create QTimer for blinking text
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.blinkText)
        self.blink_state = False  # Initial state of the text
        self.timer.start(500)  # Milliseconds between toggling visibility
        self.listen_for_alerts()

    def blinkText(self):
        self.blink_state = not self.blink_state  # Toggle the state
        if self.blink_state:
            self.buttonbox.button(QDialogButtonBox.Ok).setText("Alert")
        else:
            self.buttonbox.button(QDialogButtonBox.Ok).setText("")

    def listen_for_alerts(self):
        self.context = zmq.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect("tcp://localhost:5556")  # Replace with appropriate port
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self.check_for_alerts)
        self.alert_timer.start(500)  # Check every 500ms

    def check_for_alerts(self):
        try:
            message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
            self.bar.pushMessage("Alert: ", message, level=Qgis.Critical, duration=5)
        except zmq.Again:
            pass  # No message received

    def run(self):
        self.bar.pushMessage("Alert: ", "Altitude rule violation ", level=Qgis.Critical, duration=5)


def plot_points(random_points, point_layer, canvas):
    feats = []
    feat = QgsFeature(point_layer.fields())
    feat.setAttribute('Longitude', random_points[1])
    feat.setAttribute('Latitude', random_points[0])
    feat.setAttribute('Identity', random_points[2])
    feat.setAttribute('Time', random_points[3])
    point = QgsGeometry.fromPointXY(QgsPointXY(random_points[1], random_points[0]))
    feat.setGeometry(point)
    feats.append(feat)
    point_layer.dataProvider().addFeatures(feats)


def update_canvas(point_layer, canvas):
    feature_ids = [feature.id() for feature in point_layer.getFeatures()]
    point_layer.dataProvider().deleteFeatures(feature_ids)
    global HEADING_2
    try:
        message = socket.recv_string(flags=zmq.NOBLOCK)
        row_data = message.split("|")
        system_time = 112233
        longitude = float(row_data[4])
        latitude = float(row_data[5])
        update_angle(float(row_data[17]))
        print("Updated HEADING_2:", HEADING_2)
        random_points = [longitude, latitude, 90, system_time]
        plot_points(random_points, point_layer, canvas)

        # Reapply the symbol with the updated angle
        style = QgsStyle.defaultStyle()
        style_angle = style.symbol('topo airport')
        style_angle.setAngle(HEADING_2)
        style_angle.setColor(Qt.green)
        point_layer.renderer().setSymbol(style_angle)

        # Refresh the layer and canvas
        point_layer.triggerRepaint()
        canvas.refresh()

    except zmq.Again:
        print('No data on the port... Waiting ....')


if __name__ == '__main__':
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:1137")
    socket.subscribe(b"")
    socket.setsockopt(zmq.RCVTIMEO, 1000)
    QGIS_PATH = r'C:\Program Files\QGIS 3.22.3\apps\qgis'
    QgsApplication.setPrefixPath(QGIS_PATH, True)
    app = QApplication(sys.argv)
    QgsApplication.initQgis()

    canvas = QgsMapCanvas()
    canvas.setCanvasColor(Qt.black)
    canvas.show()
    canvas.showMaximized()

    # Existing vector layers (shapefiles)
    vlayer_path = r'D:\ad_tewa0.8_stable\adTEWA-TSC\bases and layer files\Layers\PakistanIBPolyline.shp'
    vlayer = QgsVectorLayer(vlayer_path, "Shape File", "ogr")
    vlayer.renderer().symbol().setColor(Qt.green)

    fda_area1 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_1.shp'
    fda1 = QgsVectorLayer(fda_area1, "area File", "ogr")
    fda1.renderer().symbol().setColor(Qt.yellow)

    fda_area2 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_2.shp'
    fda2 = QgsVectorLayer(fda_area2, "area File", "ogr")
    fda2.renderer().symbol().setColor(Qt.yellow)

    fda_area3 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_3.shp'
    fda3 = QgsVectorLayer(fda_area3, "area File", "ogr")
    fda3.renderer().symbol().setColor(Qt.yellow)

    fda_area4 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_4.shp'
    fda4 = QgsVectorLayer(fda_area4, "area File", "ogr")
    fda4.renderer().symbol().setColor(Qt.yellow)

    fda_area5 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_5.shp'
    fda5 = QgsVectorLayer(fda_area5, "area File", "ogr")
    fda5.renderer().symbol().setColor(Qt.yellow)

    fda_area6 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_6.shp'
    fda6 = QgsVectorLayer(fda_area6, "area File", "ogr")
    fda6.renderer().symbol().setColor(Qt.yellow)

    fda_area7 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_7.shp'
    fda7 = QgsVectorLayer(fda_area7, "area File", "ogr")
    fda7.renderer().symbol().setColor(Qt.yellow)

    fda_area8 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_8.shp'
    fda8 = QgsVectorLayer(fda_area8, "area File", "ogr")
    fda8.renderer().symbol().setColor(Qt.yellow)

    fda_area9 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_9.shp'
    fda9 = QgsVectorLayer(fda_area9, "area File", "ogr")
    fda9.renderer().symbol().setColor(Qt.yellow)

    fda_area10 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_10.shp'
    fda10 = QgsVectorLayer(fda_area10, "area File", "ogr")
    fda10.renderer().symbol().setColor(Qt.yellow)

    fda_area11 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_11.shp'
    fda11 = QgsVectorLayer(fda_area11, "area File", "ogr")
    fda11.renderer().symbol().setColor(Qt.yellow)

    fda_area12 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_12.shp'
    fda12 = QgsVectorLayer(fda_area12, "area File", "ogr")
    fda12.renderer().symbol().setColor(Qt.yellow)

    fda_area13 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_13.shp'
    fda13 = QgsVectorLayer(fda_area13, "area File", "ogr")
    fda13.renderer().symbol().setColor(Qt.yellow)

    fda_area14 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_14.shp'
    fda14 = QgsVectorLayer(fda_area14, "area File", "ogr")
    fda14.renderer().symbol().setColor(Qt.yellow)

    fda_area15 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_15.shp'
    fda15 = QgsVectorLayer(fda_area15, "area File", "ogr")
    fda15.renderer().symbol().setColor(Qt.yellow)

    fda_area16 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_16.shp'
    fda16 = QgsVectorLayer(fda_area16, "area File", "ogr")
    fda16.renderer().symbol().setColor(Qt.yellow)

    fda_area17 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_17.shp'
    fda17 = QgsVectorLayer(fda_area17, "area File", "ogr")
    fda17.renderer().symbol().setColor(Qt.yellow)

    fda_area18 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_18.shp'
    fda18 = QgsVectorLayer(fda_area18, "area File", "ogr")
    fda18.renderer().symbol().setColor(Qt.yellow)

    fda_area19 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_19.shp'
    fda19 = QgsVectorLayer(fda_area19, "area File", "ogr")
    fda19.renderer().symbol().setColor(Qt.yellow)

    fda_area20 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_20.shp'
    fda20 = QgsVectorLayer(fda_area20, "area File", "ogr")
    fda20.renderer().symbol().setColor(Qt.yellow)

    fda_area21 = r'D:\ad_tewa0.8_stable\FDA\fda area\area_21.shp'
    fda21 = QgsVectorLayer(fda_area21, "area File", "ogr")
    fda21.renderer().symbol().setColor(Qt.yellow)

    # ===== Add ECW raster layers instead of TIFF =====
    # 50000 Scale Map
    map_50k_path = r'D:\ECW\50000 SCALE IMAGE MAP.ecw'  # Update with actual path
    map_50k = QgsRasterLayer(map_50k_path, "50K Scale Map")
    if not map_50k.isValid():
        print("50K Scale Map failed to load!")
    else:
        map_50k.setOpacity(0.3)  # Adjust opacity

    # 125000 Scale Map
    map_125k_path = r'D:\ECW\125000 SCALE MAP.ecw'  # Update with actual path
    map_125k = QgsRasterLayer(map_125k_path, "125K Scale Map")
    if not map_125k.isValid():
        print("125K Scale Map failed to load!")
    else:
        map_125k.setOpacity(0.3)

    # 2M Scale Map
    map_2m_path = r'D:\ECW\2M IMAGE MAP.ecw'  # Update with actual path
    map_2m = QgsRasterLayer(map_2m_path, "2M Scale Map")
    if not map_2m.isValid():
        print("2M Scale Map failed to load!")
    else:
        map_2m.setOpacity(0.3)

    # 16M Scale Map
    map_16m_path = r'D:\ECW\16M SCALE IMAGE MAP.ecw'  # Update with actual path
    map_16m = QgsRasterLayer(map_16m_path, "16M Scale Map")
    if not map_16m.isValid():
        print("16M Scale Map failed to load!")
    else:
        map_16m.setOpacity(0.3)

    # 250000 Scale Map
    map_250k_path = r'D:\ECW\250000 SCALE MAP.ecw'  # Update with actual path
    map_250k = QgsRasterLayer(map_250k_path, "250K Scale Map")
    if not map_250k.isValid():
        print("250K Scale Map failed to load!")
    else:
        map_250k.setOpacity(0.3)
    # ===================================

    # Add layer selection combobox for raster layers
    raster_layers = {
        "50K Scale Map": map_50k,
        "125K Scale Map": map_125k,
        "2M Scale Map": map_2m,
        "16M Scale Map": map_16m,
        "250K Scale Map": map_250k
    }

    # Create the point layer for moving objects
    point_layer = QgsVectorLayer("Point?crs=EPSG:4326",
                                 "Moving Points",
                                 "memory")
    provider = point_layer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("Longitude", QVariant.Double))
    fields.append(QgsField("Latitude", QVariant.Double))
    fields.append(QgsField("Identity", QVariant.Int))
    fields.append(QgsField("Time", QVariant.Int))
    provider.addAttributes(fields)
    point_layer.updateFields()

    style = QgsStyle.defaultStyle()
    style_angle = style.symbol('topo airport')
    style_angle.setAngle(HEADING_2)
    style_angle.setColor(Qt.green)
    point_layer.renderer().setSymbol(style_angle)

    # Set the layer order for the canvas.
    # Here, we add the ECW layers at the bottom (as base layers), then the vector layers, then the point layer on top.
    # By default, we'll display the 2M map (you can change this to whichever map you prefer as the default)
    canvas.setLayers([map_2m, vlayer, fda1, fda2, fda3, fda4, fda5,
                      fda6, fda7, fda8, fda9, fda10, fda11, fda12, fda16, fda17, fda18,
                      fda19, fda20, fda21, point_layer])
    canvas.setExtent(vlayer.extent())
    canvas.refresh()

    # Create a map layer selection widget
    map_selector = QComboBox()
    map_selector.addItems(raster_layers.keys())
    map_selector.setCurrentText("2M Scale Map")  # Default map


    # Function to switch base map layer
    def switch_base_map(map_name):
        # Get current layers
        current_layers = canvas.layers()
        # Remove the current base map (first layer)
        current_layers.pop(0)
        # Add the new base map at the beginning
        current_layers.insert(0, raster_layers[map_name])
        # Update the canvas layers
        canvas.setLayers(current_layers)
        canvas.refresh()


    # Connect the combo box
    map_selector.currentTextChanged.connect(switch_base_map)

    # Add the selector to a toolbar
    toolbar = QToolBar("Map Selection")
    toolbar.addWidget(QLabel("Select Map: "))
    toolbar.addWidget(map_selector)

    # Create a main window to hold the canvas and toolbar
    main_window = QMainWindow()
    main_window.addToolBar(toolbar)
    main_window.setCentralWidget(canvas)
    main_window.showMaximized()

    myDlg = MyDialog()
    canvas_layout = QVBoxLayout()
    canvas_layout.addWidget(myDlg)
    canvas_layout.setAlignment(Qt.AlignTop)
    canvas.setLayout(canvas_layout)

    timer = QTimer()
    timer.timeout.connect(lambda: update_canvas(point_layer, canvas))
    timer.start(100)

    sys.exit(app.exec_())