import zmq
import time
import random

# Set up ZMQ publisher
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://127.0.0.1:5555")  # Ensure this matches the port in your subscriber

context = zmq.Context()
socket_sub = context.socket(zmq.SUB)
socket_sub.connect("tcp://localhost:1137")
socket_sub.setsockopt_string(zmq.SUBSCRIBE, '')

def generate_random_data():
    """Generate random data for all fields."""
    message = socket_sub.recv_string()
    row_data = message.split("|")

    altitude = float(row_data[6])
    speed = float(row_data[7])

    egt_1 = float(row_data[83])
    egt_2 = float(row_data[81])
    egt_3 = float(row_data[79])
    egt_4 = float(row_data[77])
    egt_5 = float(row_data[75])
    egt_6 = float(row_data[73])

    cht_1 = float(row_data[82])
    cht_2 = float(row_data[80])
    cht_3 = float(row_data[78])
    cht_4 = float(row_data[76])
    cht_5 = float(row_data[74])
    cht_6 = float(row_data[72])

    time_rec = row_data[14]

    return {
        "speed": speed, #random.randint(0, 200),  # Speed in knots
        "elevation": altitude, #random.randint(0, 4000),  # Elevation in ft
        "egt_1": egt_1, #random.randint(1000, 2000), # 84
        "egt_2": egt_2, #random.randint(1000, 2000), # 82
        "egt_3": egt_3, #random.randint(1000, 2000), # 80
        "egt_4": egt_4, #random.randint(1000, 2000), # 78
        "egt_5": egt_5, #random.randint(1000, 2000), # 76
        "egt_6": egt_6, #random.randint(1000, 2000), # 74
        "cht_1": cht_1, #random.randint(500, 1000), # 83
        "cht_2": cht_2, #random.randint(500, 1000), # 81
        "cht_3": cht_3, #random.randint(500, 1000), # 79
        "cht_4": cht_4, #random.randint(500, 1000), # 77
        "cht_5": cht_5, #random.randint(500, 1000), # 75
        "cht_6": cht_6, #random.randint(500, 1000),  # 73
        "time":  time_rec, # time.strftime("%H:%M:%S", row_data[14])  #time.strftime("%H:%M:%S"),  # Current time   float(row_data[14])
    }

print("Publisher started...")

# Continuously send data
while True:
    data = generate_random_data()
    socket.send_json(data)
    # print(f"Sent data: {data}")
    print(data)
    time.sleep(0.1)  # Send data every second
