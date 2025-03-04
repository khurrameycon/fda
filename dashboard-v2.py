import time
import zmq
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_daq as daq
from datetime import datetime
import plotly.graph_objs as go

# Initialize Dash
app = dash.Dash(__name__)

# Initialize ZMQ
context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://127.0.0.1:5555")
socket.setsockopt_string(zmq.SUBSCRIBE, "")
socket.RCVTIMEO = 100

# Constants for alerts
ALERT_THRESHOLDS = {
    'egt': {'warning': 1600, 'critical': 1800},
    'speed': {'warning': 150, 'critical': 180},
    'elevation': {'warning': 3500, 'critical': 3800}
}

# Available parameters for plotting
AVAILABLE_PARAMETERS = [
    {'label': 'Speed', 'value': 'speed'},
    {'label': 'Elevation', 'value': 'elevation'},
    {'label': 'EGT 1', 'value': 'egt_1'},
    {'label': 'EGT 2', 'value': 'egt_2'},
    {'label': 'EGT 3', 'value': 'egt_3'},
    {'label': 'EGT 4', 'value': 'egt_4'},
    {'label': 'EGT 5', 'value': 'egt_5'},
    {'label': 'EGT 6', 'value': 'egt_6'},
    {'label': 'Time', 'value': 'time'},
]

app.layout = html.Div([
    # Stores and intervals
    dcc.Store(id='data-store', data={'values': []}),
    dcc.Interval(id='interval-component', interval=500),

    # Header
    html.Div([
        html.H1("FDA - SMK Dashboard",
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '20px'})
    ]),

    # Main content container
    html.Div([
        # Left panel - Graph and controls
        html.Div([
            # Parameter selection
            html.Div([
                html.Label("Select Parameters to Display:",
                           style={'marginBottom': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='parameter-selector',
                    options=AVAILABLE_PARAMETERS,
                    value=['speed', 'egt_1'],  # Default selected parameters
                    multi=True,
                    style={'backgroundColor': '#f8f9fa'}
                )
            ], style={'marginBottom': '20px'}),

            # Main graph
            dcc.Graph(id='live-graph',
                      style={'height': '50vh'})
        ], style={'width': '60%', 'display': 'inline-block', 'padding': '20px'}),

        # Right panel - Gauges and alerts
        html.Div([
            # Speed and Elevation gauges
            html.Div([
                daq.Gauge(
                    id='speed-gauge',
                    label="Speed",
                    value=0,
                    max=200,
                    min=0,
                    color={'gradient': True,
                           'ranges': {'green': [0, 150],
                                      'yellow': [150, 180],
                                      'red': [180, 200]}}
                ),
                daq.Tank(
                    id='elevation-tank',
                    label="Elevation",
                    value=0,
                    max=10000,
                    min=0,
                    style={'margin': '20px 0'}
                )
            ]),

            # EGT Panel
            html.Div([
                html.H3("EGT Temperatures",
                        style={'textAlign': 'center', 'marginBottom': '15px'}),
                html.Div([
                    html.Div([
                        daq.GraduatedBar(
                            id=f'egt-{i}',
                            label=f'EGT {i}',
                            value=0,
                            max=2000,
                            step=100,
                            color={'gradient': True,
                                   'ranges': {'green': [0, 1600],
                                              'yellow': [1600, 1800],
                                              'red': [1800, 2000]}}
                        ),
                        html.Div(id=f'egt-{i}-value',
                                 style={'textAlign': 'center', 'marginTop': '5px'})
                    ], style={'width': '30%', 'margin': '10px'})
                    for i in range(1, 7)
                ], style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center'})
            ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '10px'}),

            # Alerts panel
            html.Div(id='alerts-panel',
                     style={'marginTop': '20px', 'padding': '10px',
                            'borderRadius': '5px', 'backgroundColor': '#f8f9fa'})
        ], style={'width': '35%', 'display': 'inline-block', 'verticalAlign': 'top',
                  'padding': '20px'})
    ], style={'display': 'flex', 'justifyContent': 'space-between'}),

    # Debug info (collapsed by default)
    html.Details([
        html.Summary("Debug Information"),
        html.Div(id='debug-info'),
        html.Div(id='last-update-time')
    ], style={'marginTop': '20px'})
], style={'padding': '20px', 'backgroundColor': '#ffffff'})


def check_alerts(data):
    alerts = []
    if not data:
        return []

    # Check EGTs
    for i in range(1, 7):
        egt_value = data.get(f'egt_{i}', 0)
        if egt_value >= ALERT_THRESHOLDS['egt']['critical']:
            alerts.append(f"CRITICAL: EGT {i} temperature ({egt_value}°F) exceeds critical threshold!")
        elif egt_value >= ALERT_THRESHOLDS['egt']['warning']:
            alerts.append(f"WARNING: EGT {i} temperature ({egt_value}°F) exceeds warning threshold")

    # Check speed
    speed = data.get('speed', 0)
    if speed >= ALERT_THRESHOLDS['speed']['critical']:
        alerts.append(f"CRITICAL: Speed ({speed} knots) exceeds critical threshold!")
    elif speed >= ALERT_THRESHOLDS['speed']['warning']:
        alerts.append(f"WARNING: Speed ({speed} knots) exceeds warning threshold")

    return alerts


@app.callback(
    [
        Output('data-store', 'data'),
        Output('live-graph', 'figure'),
        Output('speed-gauge', 'value'),
        Output('elevation-tank', 'value'),
        Output('alerts-panel', 'children'),
        Output('debug-info', 'children'),
        Output('last-update-time', 'children')
    ] + [Output(f'egt-{i}', 'value') for i in range(1, 7)] +
    [Output(f'egt-{i}-value', 'children') for i in range(1, 7)],
    [Input('interval-component', 'n_intervals'),
     Input('parameter-selector', 'value')],
    [State('data-store', 'data')]
)
def update_metrics(n_intervals, selected_parameters, stored_data):
    try:
        try:
            message = socket.recv_json(flags=zmq.NOBLOCK)
            debug_msg = "Successfully received ZMQ message"
        except zmq.Again:
            message = None
            debug_msg = "No new ZMQ message"
        except Exception as e:
            message = None
            debug_msg = f"ZMQ Error: {str(e)}"

        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if message:
            # Update stored data
            stored_data['values'].append({
                'time': message.get('time', 0), #time, #current_time,
                'speed': message.get('speed', 0),
                'elevation': message.get('elevation', 0),
                **{f'egt_{i}': message.get(f'egt_{i}', 0) for i in range(1, 7)}
            })
            stored_data['values'] = stored_data['values'][-120:]

            # Get latest values
            latest_data = message
        else:
            latest_data = stored_data['values'][-1] if stored_data['values'] else {
                'speed': 0, 'elevation': 0,
                **{f'egt_{i}': 0 for i in range(1, 7)}
            }

        # Create graph traces for selected parameters
        traces = []
        for param in selected_parameters:
            values = [item[param] for item in stored_data['values']]
            times = [item['time'] for item in stored_data['values']]
            traces.append(go.Scatter(
                x=times,
                y=values,
                name=param.upper(),
                mode='lines+markers'
            ))

        figure = {
            'data': traces,
            'layout': {
                'title': 'Selected Parameters Over Time',
                'xaxis': {'title': 'Time'},
                'yaxis': {'title': 'Value'},
                'plot_bgcolor': '#f8f9fa',
                'paper_bgcolor': '#f8f9fa',
                'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40}
            }
        }

        # Generate alerts
        alerts = check_alerts(latest_data)
        alerts_panel = [
            html.H3("Active Alerts"),
            html.Div([
                html.Div(alert,
                         style={'color': 'red' if 'CRITICAL' in alert else 'orange',
                                'margin': '5px 0'})
                for alert in alerts
            ]) if alerts else html.Div("No active alerts",
                                       style={'color': 'green'})
        ]

        # Get EGT values
        egt_values = [latest_data.get(f'egt_{i}', 0) for i in range(1, 7)]
        egt_displays = [f"Temperature: {val}°F" for val in egt_values]

        return (
            stored_data,  # data-store
            figure,  # live-graph
            latest_data.get('speed', 0),  # speed-gauge
            latest_data.get('elevation', 0),  # elevation-tank
            alerts_panel,  # alerts-panel
            f"Debug: {debug_msg}",  # debug-info
            f"Last Update: {current_time}",  # last-update-time
            *egt_values,  # egt-1 through egt-6 values
            *egt_displays  # egt-1-value through egt-6-value displays
        )

    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return dash.no_update


if __name__ == '__main__':
    app.run_server(debug=True)