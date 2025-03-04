import pandas as pd
import zmq
from durable.lang import ruleset, when_all, assert_fact, m
from durable.engine import MessageNotHandledException
from time import time
rule_engine_name = 'dynamic_rules'+str(time())
# Load the rules from a CSV file
def load_rules(file_path):
    try:
        data = pd.read_csv(file_path, encoding='utf-8-sig')
        data.columns = data.columns.str.strip().str.replace(' ', '_')
        return data
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return None


# Create rules dynamically based on the CSV file
def create_dynamic_rules(data):
    if data is None:
        print("No rules data available. Exiting rule creation.")
        return

    # Initialize ZMQ publisher
    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind("tcp://*:5556")  # Replace with appropriate port

    # Ensure ruleset exists
    with ruleset(rule_engine_name):
        for index, row in data.iterrows():
            try:
                rule_name = row['Rule_Name']
                altitude_limit = int(row['Altitude_Limit'])
                speed_limit = int(row['Speed_Limit'])

                print(f"Registering {rule_name}: Altitude <= {altitude_limit}, Speed <= {speed_limit}")

                @when_all(
                    (m.Altitude > altitude_limit) & (m.Speed > speed_limit)
                )
                def dynamic_rule(c):
                    alert_message = f"Alert: {rule_name} matched."
                    print(alert_message)
                    pub_socket.send_string(alert_message)

            except ValueError as ve:
                print(f"Error processing rule {rule_name}: {ve}")

# Listen for data on a ZMQ port and evaluate against rules
def evaluate_data(zmq_port):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(zmq_port)
    socket.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all messages

    print("Listening for real-time data on ZMQ port...")

    while True:
        try:
            # Receive JSON data from ZMQ
            message = socket.recv_string()
            row_data = message.split("|")
            system_time = int(time())
            altitude = float(row_data[6])
            speed = float(row_data[7])
            # Normalize fields and add timestamp
            data = {
                'Timestamp': system_time,  # Add unique timestamp
                'Altitude': altitude,
                'Speed': speed
            }
            print(f"Received data: {data}")

            try:
                assert_fact(rule_engine_name, data)
            except MessageNotHandledException:
                print(f"No rule matched for data: {data}")
            except Exception as e:
                print(f"Error processing data {data}: {e}")

        except KeyboardInterrupt:
            print("Stopping ZMQ listener.")
            break
        except Exception as e:
            print(f"Error receiving data: {e}")


# Main execution
if __name__ == "__main__":
    # Filepath to the CSV file containing rules
    rules_file = r"D:\ad_tewa0.8_stable\FDA\rules.csv"
    rules_data = load_rules(rules_file)

    # Create the rules based on the CSV file
    create_dynamic_rules(rules_data)

    # ZMQ port for receiving data
    zmq_port = "tcp://localhost:1137"  # Update to your ZMQ port

    # Start evaluating data
    evaluate_data(zmq_port)
