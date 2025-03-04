#!/usr/bin/env python3

from HandFaceTracker import HandFaceTracker
from HandFaceRenderer import HandFaceRenderer
import argparse
import zmq
import numpy as np
import time
import sys
import os
import cv2

parser = argparse.ArgumentParser()
parser_tracker = parser.add_argument_group("Tracker arguments")
parser_tracker.add_argument('-i', '--input', type=str, 
                    help="Path to video or image file to use as input (if not specified, use OAK color camera)")
parser_tracker.add_argument("-a", "--with_attention", action="store_true",
                    help="Use face landmark with attention model")
parser_tracker.add_argument('-p', "--use_face_pose", action="store_true", 
                    help="Calculate the face pose tranformation matrix and metric landmarks")
parser_tracker.add_argument('-2', "--double_face", action="store_true", 
                    help="EXPERIMENTAL. Run a 2nd occurence of the face landmark Neural Network to improve fps. Hand tracking is disabled.")
parser_tracker.add_argument('-n', '--nb_hands', type=int, choices=[0,1,2], default=2, 
                    help="Number of hands tracked (default=%(default)i)")                    
parser_tracker.add_argument('-xyz', "--xyz", action="store_true", 
                    help="Enable spatial location measure of hands and face")
parser_tracker.add_argument('-g', '--gesture', action="store_true", 
                    help="Enable gesture recognition")
parser_tracker.add_argument('-f', '--internal_fps', type=int, 
                    help="Fps of internal color camera. Too high value lower NN fps (default= depends on the model)")                    
parser_tracker.add_argument('--internal_frame_height', type=int,                                                                                 
                    help="Internal color camera frame height in pixels")   
parser_tracker.add_argument('-t', '--trace', type=int, nargs="?", const=1, default=0, 
                    help="Print some debug infos. The type of info depends on the optional argument.")                
parser_renderer = parser.add_argument_group("Renderer arguments")
parser_renderer.add_argument('-o', '--output', 
                    help="Path to output video file")
args = parser.parse_args()
dargs = vars(args)
tracker_args = {a:dargs[a] for a in ['internal_fps', 'internal_frame_height'] if dargs[a] is not None}

# Set up ZMQ for sending coordinates
print("Setting up ZMQ for sending forehead coordinates on port 5560...")
context = zmq.Context()
socket = context.socket(zmq.PUB)
try:
    socket.bind("tcp://*:5560")
    print("ZMQ socket bound to port 5560 for sending forehead coordinates")
except zmq.error.ZMQError as e:
    print(f"Failed to bind ZMQ socket: {e}")
    socket.close()
    context.term()
    sys.exit(1)

tracker = HandFaceTracker(
        input_src=args.input, 
        double_face=args.double_face,
        use_face_pose=args.use_face_pose,
        use_gesture=args.gesture,
        xyz=args.xyz,
        with_attention=args.with_attention,
        nb_hands=args.nb_hands,
        trace=args.trace,
        **tracker_args
        )

renderer = HandFaceRenderer(
        tracker=tracker,
        output=args.output)

# Store forehead coordinates
forehead_coordinates = []
FOREHEAD_LANDMARK_INDEX = 10  # Forehead landmark (approximate, may need adjustment)
MIN_SAMPLES = 30  # Minimum number of samples before sending coordinates
MAX_SAMPLES = 100  # Maximum number of samples to collect

print("Starting face tracking for temperature sensing...")
print("Position face in front of camera. Press 'q' to exit.")

while True:
    frame, faces, hands = tracker.next_frame()
    if frame is None: break
    
    # Process face data to extract forehead coordinates
    if faces and len(faces) > 0 and tracker.xyz:
        face = faces[0]  # Use the first detected face
        
        # Check if we have 3D landmarks with depth data
        if hasattr(face, 'landmarks') and face.landmarks is not None and face.landmarks.shape[1] >= 3:
            # Extract forehead landmark coordinates (using landmark index 10 as approximation)
            # The landmark structure is a numpy array with shape (num_landmarks, 3) where each row is [x, y, z]
            forehead_landmark = face.landmarks[FOREHEAD_LANDMARK_INDEX]
            
            # Store the coordinates
            forehead_coordinates.append({
                'position': {
                    'x': float(forehead_landmark[0]),
                    'y': float(forehead_landmark[1]),
                    'z': float(forehead_landmark[2])
                }
            })
            
            # Display forehead position on frame
            cv2.circle(frame, (int(forehead_landmark[0]), int(forehead_landmark[1])), 5, (0, 255, 0), -1)
            cv2.putText(frame, f"Forehead: ({forehead_landmark[0]:.2f}, {forehead_landmark[1]:.2f}, {forehead_landmark[2]:.2f})",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Show number of samples collected
            cv2.putText(frame, f"Samples: {len(forehead_coordinates)}/{MIN_SAMPLES}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
    # Draw face and hands
    frame = renderer.draw(frame, faces, hands)
    key = renderer.waitKey(delay=1)
    if key == 27 or key == ord('q'):
        break
    
    # If we have collected enough samples, calculate average and send to robot
    if len(forehead_coordinates) >= MIN_SAMPLES:
        # Apply IQR filtering if we have enough samples
        filtered_coordinates = forehead_coordinates
        if len(forehead_coordinates) >= MAX_SAMPLES:
            # Extract data for IQR filtering
            x_coords = [m['position']['x'] for m in forehead_coordinates]
            y_coords = [m['position']['y'] for m in forehead_coordinates]
            z_coords = [m['position']['z'] for m in forehead_coordinates]
            
            # Calculate IQR bounds
            Q1_x, Q3_x = np.percentile(x_coords, [25, 75])
            IQR_x = Q3_x - Q1_x
            x_lower, x_upper = Q1_x - 1.5 * IQR_x, Q3_x + 1.5 * IQR_x
            
            Q1_y, Q3_y = np.percentile(y_coords, [25, 75])
            IQR_y = Q3_y - Q1_y
            y_lower, y_upper = Q1_y - 1.5 * IQR_y, Q3_y + 1.5 * IQR_y
            
            Q1_z, Q3_z = np.percentile(z_coords, [25, 75])
            IQR_z = Q3_z - Q1_z
            z_lower, z_upper = Q1_z - 1.5 * IQR_z, Q3_z + 1.5 * IQR_z
            
            # Filter outliers
            filtered_coordinates = []
            for coord in forehead_coordinates:
                x, y, z = coord['position']['x'], coord['position']['y'], coord['position']['z']
                if (x_lower <= x <= x_upper and 
                    y_lower <= y <= y_upper and 
                    z_lower <= z <= z_upper):
                    filtered_coordinates.append(coord)
        
        # Calculate average position
        avg_x = np.mean([m['position']['x'] for m in filtered_coordinates])
        avg_y = np.mean([m['position']['y'] for m in filtered_coordinates])
        avg_z = np.mean([m['position']['z'] for m in filtered_coordinates])
        
        # Convert from millimeters to meters for the robot system
        avg_x_meters = avg_x / 1000.0
        avg_y_meters = avg_y / 1000.0
        avg_z_meters = avg_z / 1000.0
        
        # Send the coordinates (in meters)
        print(f"Sending average forehead coordinates (mm): ({avg_x:.4f}, {avg_y:.4f}, {avg_z:.4f})")
        print(f"Sending average forehead coordinates (m): ({avg_x_meters:.6f}, {avg_y_meters:.6f}, {avg_z_meters:.6f})")
        coordinates_str = f"{avg_x_meters:.6f},{avg_y_meters:.6f},{avg_z_meters:.6f}"
        try:
            # Sleep briefly to ensure the subscriber has time to connect
            print("Waiting for subscriber connection...")
            time.sleep(1)
            
            # Send the coordinates multiple times 
            for i in range(5):
                socket.send_string(coordinates_str)
                print(f"Sent coordinates attempt {i+1}: {coordinates_str}")
                time.sleep(0.5) 
            
            print("Coordinates sent successfully!")
            
            # Keep the window open briefly to show success message
            cv2.putText(frame, "Coordinates sent successfully!", 
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("Thermometer", frame)
            cv2.waitKey(2000)  # Wait for 2 seconds
            break  # Exit after sending coordinates
        except Exception as e:
            print(f"Error sending coordinates: {e}")
            import traceback
            traceback.print_exc()
        
renderer.exit()
tracker.exit()

# Clean up ZMQ resources
socket.close()
context.term()
print("Demo complete. Coordinates sent to robot.")
