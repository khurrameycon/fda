import zmq
import math
import time
from datetime import datetime

# Initialize ZMQ publisher
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:1137")

# Constants
GLIDE_SLOPE_ANGLE = 3  # degrees
RUNWAY_TRUE_HEADING = 60  # degrees
START_DISTANCE = 15000  # 15km in meters
APPROACH_SPEED = 70  # m/s (about 136 knots)
UPDATE_RATE = 1  # seconds between updates

# Base coordinates for Risalpur
BASE_LAT = 34.07079
BASE_LON = 71.976469
START_ALT = START_DISTANCE * math.tan(math.radians(GLIDE_SLOPE_ANGLE)) -200   # meters + 25m buffer

def calculate_position(distance_from_threshold):
    """Calculate lat/lon/alt for a given distance along perfect glide slope"""
    # Calculate altitude on glide slope
    altitude = distance_from_threshold * math.tan(math.radians(GLIDE_SLOPE_ANGLE)) - 400
    
    # Convert distance to lat/lon change - modified to keep aircraft on centerline
    heading_rad = math.radians(RUNWAY_TRUE_HEADING)
    
    # Only move along x-axis relative to runway heading
    dx = -distance_from_threshold * math.cos(heading_rad)
    dy = 0  # Set to 0 to keep aircraft on centerline
    
    # Convert to lat/lon (approximate conversion)
    delta_lon = dx / 111320 / math.cos(math.radians(BASE_LAT))  # longitude correction for latitude
    delta_lat = dy / 110540  # Will be 0 since dy is 0
    
    lon = BASE_LON + delta_lon
    lat = BASE_LAT + delta_lat
    
    return lat, lon, altitude

def create_message(lat, lon, alt, ground_track):
    """Create properly formatted message string"""
    # Create dummy values for unused fields
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    msg_parts = [
        timestamp,          # field 0
        "SIM",             # field 1
        "PERFECT",         # field 2
        "APP",             # field 3
        f"{lat:.6f}",      # field 4 - latitude
        f"{lon:.6f}",      # field 5 - longitude
        f"{alt:.1f}",      # field 6 - altitude
        "0",               # field 7
        f"{ground_track:.1f}", # field 8 - ground track
        "0",               # field 9
        "0",               # field 10
        "0",               # field 11
        "0",               # field 12
        "0",               # field 13
        "0",               # field 14
        "0",               # field 15
        "0",               # field 16
        f"{RUNWAY_TRUE_HEADING:.1f}"  # field 17 - magnetic heading
    ]
    return "|".join(msg_parts)

def main():
    print("Starting perfect approach data publisher...")
    current_distance = START_DISTANCE
    
    try:
        while current_distance > 0:
            # Calculate current position
            lat, lon, alt = calculate_position(current_distance)
            
            # Create and send message
            msg = create_message(lat, lon, alt, RUNWAY_TRUE_HEADING)
            socket.send_string(msg)
            print(f"Published position: distance={current_distance:.1f}m, altitude={alt:.1f}m")
            
            # Move aircraft forward
            current_distance -= APPROACH_SPEED * UPDATE_RATE
            
            # Wait for next update
            time.sleep(UPDATE_RATE)
            
        # Send final position at threshold
        msg = create_message(BASE_LAT, BASE_LON, 0, RUNWAY_TRUE_HEADING)
        socket.send_string(msg)
        print("Aircraft reached runway threshold")
        
    except KeyboardInterrupt:
        print("\nPublisher stopped by user")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()