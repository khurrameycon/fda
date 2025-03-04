import plotly.graph_objects as go
import math
import zmq
import numpy as np
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
import dash
from collections import deque

# Initialize Dash app
app = Dash(__name__)

# Constants
GLIDE_SLOPE_ANGLE = 3  # degrees
APPROACH_LENGTH = 0.4  # Length of the approach path
CORRIDOR_WIDTH = 0.05  # Width of the approach corridor
CORRIDOR_HEIGHT = 0.02  # Height of the approach corridor
TRAIL_LENGTH = 50  # Number of positions to keep in trail

# Runway constants
RUNWAY_TRUE_HEADING = 60  # Runway 60R heading
RUNWAY_LENGTH_METERS = 2700  # Actual runway length
RUNWAY_WIDTH_METERS = 45  # Actual runway width

# Base coordinates for Risalpur
BASE_LAT = 34.07079
BASE_LON = 71.976469

# Initialize position history
position_history = deque(maxlen=TRAIL_LENGTH)

# Initialize ZMQ subscriber
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:1137")
socket.setsockopt_string(zmq.SUBSCRIBE, "")


def create_ground_grid():
    """Create ground reference grid"""
    grid_size = 0.5
    grid_points = np.linspace(-grid_size, grid_size, 11)
    traces = []

    # Create grid lines
    for x in grid_points:
        traces.append(go.Scatter3d(
            x=[x, x],
            y=[-grid_size, grid_size],
            z=[0, 0],
            mode='lines',
            line=dict(color='lightgray', width=1),
            showlegend=False
        ))
    for y in grid_points:
        traces.append(go.Scatter3d(
            x=[-grid_size, grid_size],
            y=[y, y],
            z=[0, 0],
            mode='lines',
            line=dict(color='lightgray', width=1),
            showlegend=False
        ))

    return traces


def transform_coordinates(lat, lon, alt):
    """Transform coordinates with simple X alignment"""
    # Convert to local coordinates without rotation
    x = (lon - BASE_LON) * 5.0
    y = (lat - BASE_LAT) * 5.0
    z = alt * 0.0001

    return x, y, z

def create_runway():
    """Create runway as a straight line along X-axis"""
    traces = []
    runway_length = 0.4  # Total length
    runway_width = 0.05  # Width

    # Main runway surface - aligned with X-axis
    traces.append(go.Scatter3d(
        x=[-runway_length/2, runway_length/2],
        y=[0, 0],  # Centered at Y=0
        z=[0, 0],
        mode='lines',
        line=dict(color='gray', width=10),
        name='Runway 60R/27L'
    ))

    # Add runway designator positions
    traces.append(go.Scatter3d(
        x=[-runway_length/2, runway_length/2],
        y=[0, 0],
        z=[0.001, 0.001],  # Slightly above ground
        mode='text',
        text=['60R', '27L'],
        textposition='middle center',
        textfont=dict(size=12, color='white'),
        showlegend=False
    ))

    return traces

def create_approach_corridor():
    """Create approach corridor aligned with X-axis"""
    traces = []
    
    # Calculate heights based on glide slope
    distances = np.linspace(0, APPROACH_LENGTH, 50)
    heights = np.tan(math.radians(GLIDE_SLOPE_ANGLE)) * distances

    # Create corridor boundaries
    for y_offset in [-CORRIDOR_WIDTH/2, CORRIDOR_WIDTH/2]:
        for z_offset in [-CORRIDOR_HEIGHT/2, CORRIDOR_HEIGHT/2]:
            traces.append(go.Scatter3d(
                x=[-d for d in distances],  # Negative X for approach
                y=[y_offset] * len(distances),
                z=heights + z_offset,
                mode='lines',
                line=dict(color='blue', width=1),
                showlegend=False
            ))

    # Vertical lines
    num_verticals = 8
    for i in range(num_verticals):
        x = -APPROACH_LENGTH * i / (num_verticals - 1)
        h = np.tan(math.radians(GLIDE_SLOPE_ANGLE)) * abs(x)
        
        traces.append(go.Scatter3d(
            x=[x, x],
            y=[-CORRIDOR_WIDTH/2, CORRIDOR_WIDTH/2],
            z=[h - CORRIDOR_HEIGHT/2, h - CORRIDOR_HEIGHT/2],
            mode='lines',
            line=dict(color='blue', width=1),
            showlegend=False
        ))
        
        traces.append(go.Scatter3d(
            x=[x, x],
            y=[-CORRIDOR_WIDTH/2, CORRIDOR_WIDTH/2],
            z=[h + CORRIDOR_HEIGHT/2, h + CORRIDOR_HEIGHT/2],
            mode='lines',
            line=dict(color='blue', width=1),
            showlegend=False
        ))

        # Vertical corner lines
        for y in [-CORRIDOR_WIDTH/2, CORRIDOR_WIDTH/2]:
            traces.append(go.Scatter3d(
                x=[x, x],
                y=[y, y],
                z=[h - CORRIDOR_HEIGHT/2, h + CORRIDOR_HEIGHT/2],
                mode='lines',
                line=dict(color='blue', width=1),
                showlegend=False
            ))

    return traces


def create_glideslope():
    """Create 3-degree glideslope line aligned with X-axis"""
    x_points = np.linspace(-APPROACH_LENGTH, 0, 100)
    z_points = np.tan(math.radians(GLIDE_SLOPE_ANGLE)) * -x_points
    
    return go.Scatter3d(
        x=x_points,
        y=[0] * len(x_points),  # Centered at Y=0
        z=z_points,
        mode='lines',
        line=dict(color='yellow', width=3, dash='dot'),
        name='3° Glideslope'
    )


def create_aircraft(x, y, z, heading=0, ground_track=0, scale=0.02):
    """Create aircraft triangle with proper orientation"""
    points = np.array([
        [scale, 0, 0],  # nose
        [-scale, scale / 2, 0],  # left wing
        [-scale, -scale / 2, 0],  # right wing
    ])

    # Create rotation matrix for heading
    heading_rad = math.radians(heading - RUNWAY_TRUE_HEADING)  # Adjust heading relative to runway
    heading_matrix = np.array([
        [math.cos(heading_rad), -math.sin(heading_rad), 0],
        [math.sin(heading_rad), math.cos(heading_rad), 0],
        [0, 0, 1]
    ])

    # Apply rotation
    points = np.dot(points, heading_matrix)

    # Translate to position
    points = points + np.array([x, y, z])

    return go.Scatter3d(
        x=list(points[:, 0]) + [points[0, 0]],
        y=list(points[:, 1]) + [points[0, 1]],
        z=list(points[:, 2]) + [points[0, 2]],
        mode='lines',
        line=dict(color='red', width=5),
        name=f'Aircraft (Hdg: {heading:.1f}°, Track: {ground_track:.1f}°)'
    )


def create_trail():
    """Create trail from position history"""
    if not position_history:
        return []

    positions = list(position_history)
    return go.Scatter3d(
        x=[p[0] for p in positions],
        y=[p[1] for p in positions],
        z=[p[2] for p in positions],
        mode='lines',
        line=dict(color='cyan', width=2),
        name='Flight Path'
    )


def calculate_deviations(x, y, z):
    """Calculate localizer and glideslope deviations"""
    # Calculate localizer deviation (lateral)
    loc_deviation = y / (CORRIDOR_WIDTH / 2) * 100  # Percentage of max width

    # Calculate glideslope deviation
    expected_height = abs(x) * math.tan(math.radians(GLIDE_SLOPE_ANGLE))
    gs_deviation = (z - expected_height) / (CORRIDOR_HEIGHT / 2) * 100

    return loc_deviation, gs_deviation


def get_default_layout():
    """Get default layout with camera settings"""
    return dict(
        scene=dict(
            xaxis=dict(range=[-0.5, 0.5], title="Distance from Threshold"),
            yaxis=dict(range=[-0.5, 0.5], title="Lateral Distance"),
            zaxis=dict(range=[0, 0.3], title="Altitude"),
            aspectmode='manual',
            aspectratio=dict(x=2, y=1, z=1),
            camera=dict(
                eye=dict(x=-1.5, y=1.2, z=0.8),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            )
        ),
        title="Approach Visualization - Risalpur (60R/27L)",
        showlegend=True,
        height=800,
        width=1000,
        margin=dict(l=0, r=0, t=30, b=0)
    )


app.layout = html.Div([
    html.Div([
        # Data Display Panel
        html.Div([
            html.H3("Flight Data", style={'textAlign': 'center'}),
            html.Div(id='altitude-display', className='data-item'),
            html.Div(id='distance-display', className='data-item'),
            html.Div(id='heading-display', className='data-item'),
            html.Div(id='deviation-display', className='data-item'),
        ], style={
            'width': '20%',
            'padding': '10px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '5px',
            'marginRight': '20px'
        }),

        # Main visualization
        html.Div([
            html.Div([
                html.Button('Top View', id='btn-top', className='mr-1'),
                html.Button('Side View', id='btn-side', className='mr-1'),
                html.Button('Approach View', id='btn-approach', className='mr-1'),
            ], style={'marginBottom': '10px'}),

            dcc.Graph(
                id='basic-plot',
                style={'height': '85vh'},
                config={'scrollZoom': True}
            )
        ], style={'width': '80%'})
    ], style={
        'display': 'flex',
        'height': '95vh',
        'padding': '20px'
    }),

    dcc.Interval(
        id='interval-component',
        interval=5000,
        n_intervals=0
    ),
    dcc.Store(id='camera-position'),
    dcc.Store(id='flight-data')
])


@app.callback(
    [Output('basic-plot', 'figure'),
     Output('flight-data', 'data')],
    [Input('interval-component', 'n_intervals'),
     Input('btn-top', 'n_clicks'),
     Input('btn-side', 'n_clicks'),
     Input('btn-approach', 'n_clicks')],
    [State('basic-plot', 'figure'),
     State('camera-position', 'data')]
)
def update_figure(n, btn_top, btn_side, btn_approach, existing_figure, camera_pos):
    ctx = dash.callback_context
    traces = []
    flight_data = {}

    # Add basic elements
    traces.extend(create_ground_grid())
    traces.extend(create_runway())
    traces.extend(create_approach_corridor())
    traces.append(create_glideslope())

    try:
        message = socket.recv_string(flags=zmq.NOBLOCK)
        message_parts = message.split("|")
        if len(message_parts) >= 18:
            try:
                # Extract position parameters
                x, y, z = transform_coordinates(
                    float(message_parts[4]),  # latitude
                    float(message_parts[5]),  # longitude
                    float(message_parts[6])  # altitude
                )

                # Extract heading and ground track
                ground_track = float(message_parts[8])
                mag_heading = float(message_parts[17])

                # Store position in history
                position_history.append((x, y, z))

                # Add trail
                if len(position_history) > 1:
                    traces.append(create_trail())

                # Calculate deviations
                loc_dev, gs_dev = calculate_deviations(x, y, z)

                # Update flight data
                flight_data = {
                    'altitude': float(message_parts[6]),  # feet
                    'distance': abs(x) * 1000,  # approximate meters from threshold
                    'heading': mag_heading,
                    'track': ground_track,
                    'loc_deviation': loc_dev,
                    'gs_deviation': gs_dev
                }

                # Add aircraft
                aircraft = create_aircraft(x, y, z, mag_heading, ground_track)
                traces.append(aircraft)

            except ValueError as e:
                print(f"Invalid data format: {e}")
    except zmq.Again:
        aircraft = create_aircraft(-0.2, 0, 0.06, heading=0, ground_track=0)
        traces.append(aircraft)
    except Exception as e:
        print(f"Error: {e}")

    # Handle layout and camera
    if existing_figure and 'layout' in existing_figure:
        layout = existing_figure['layout']
    else:
        layout = get_default_layout()

    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'btn-top':
            layout['scene']['camera'] = dict(
                eye=dict(x=0, y=0, z=2),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=1, z=0)
            )
        elif button_id == 'btn-side':
            layout['scene']['camera'] = dict(
                eye=dict(x=-2, y=0, z=-0.3),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            )
        elif button_id == 'btn-approach':
            layout['scene']['camera'] = dict(
                eye=dict(x=-1.5, y=1.2, z=0),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            )
    elif camera_pos:
        layout['scene']['camera'] = camera_pos

    return {'data': traces, 'layout': layout}, flight_data


@app.callback(
    [Output('altitude-display', 'children'),
     Output('distance-display', 'children'),
     Output('heading-display', 'children'),
     Output('deviation-display', 'children')],
    Input('flight-data', 'data')
)
def update_data_display(flight_data):
    if not flight_data:
        return ["No data"] * 4

    altitude = html.Div([
        html.Strong("Altitude: "),
        f"{flight_data['altitude']:.0f} ft"
    ])

    distance = html.Div([
        html.Strong("Distance: "),
        f"{flight_data['distance']:.0f} m"
    ])

    heading = html.Div([
        html.Strong("Heading/Track: "),
        f"{flight_data['heading']:.1f}° / {flight_data['track']:.1f}°"
    ])

    deviation = html.Div([
        html.Strong("LOC/GS Dev: "),
        f"{flight_data['loc_deviation']:.1f}% / {flight_data['gs_deviation']:.1f}%"
    ])

    return altitude, distance, heading, deviation


@app.callback(
    Output('camera-position', 'data'),
    Input('basic-plot', 'relayoutData'),
    State('camera-position', 'data')
)
def store_camera_position(relayout_data, current_pos):
    if relayout_data and 'scene.camera' in relayout_data:
        return relayout_data['scene.camera']
    return current_pos


if __name__ == '__main__':
    app.run_server(port=8051, debug=True)