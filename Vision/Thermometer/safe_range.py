from HandFaceTracker import HandFaceTracker
from HandFaceRenderer import HandFaceRenderer
import argparse
import numpy as np
import time
import sys
import os
import cv2
import math

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

tracker = HandFaceTracker(
        input_src=args.input, 
        double_face=args.double_face,
        use_face_pose=args.use_face_pose,
        use_gesture=args.gesture,
        xyz=True,
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
# We're no longer using this landmark index since we're using face.xyz directly
# FOREHEAD_LANDMARK_INDEX = 10  # Forehead landmark (approximate, may need adjustment)
MIN_SAMPLES = 50  # Minimum number of samples before sending coordinates 
MAX_SAMPLES = 200  # Maximum number of samples to collect 

MAX_REACH = 406.4 # Maximum reach in mm (16 inches)

print("Starting face tracking for temperature sensing...")
print("Position face in front of camera. Press 'q' to exit.")

def isInRange(y, z, camera_intersect):
    if z > MAX_REACH:
        return False
    if y < camera_intersect:
        return False
    return True
    
def intersectFinder(img_height, camera_pitch):
    # Calculate the camera intersection point based on the camera pitch
    delta_z = -165.1  # Distance from camera to robot arm in mm
    delta_x = 406.4   # Maximum reach of the robot arm in mm
    VFOV = 69.0       # Vertical field of view in degrees

    phi = math.degrees(math.atan2(delta_z, delta_x)) + camera_pitch
    y_norm = (VFOV / 2.0 - phi) / VFOV

    return y_norm * img_height


while True:
    frame, faces, hands = tracker.next_frame()
    if frame is None: break
    img_height, img_width = frame.shape[:2]

    camera_intersect = intersectFinder(img_height, 0)

    # Draw the camera intersection line on the frame
    cv2.line(frame, (0, camera_intersect), (img_width, camera_intersect), (255, 0, 0), 2)

    
    # Process face data to extract forehead coordinates
    if faces and len(faces) > 0 and tracker.xyz:
        face = faces[0]  # Use the first detected face
        
        # Check if we have xyz coordinates available
        if hasattr(face, 'xyz') and face.xyz is not None:
            # Use face.xyz directly - these already contain the optimized forehead coordinates
            # calculated in HandFaceTracker.py using the adjusted forehead point
            forehead_x, forehead_y, forehead_z = face.xyz
            
            # Check for NaN values which can occur if depth calculation fails
            if np.isnan(forehead_x) or np.isnan(forehead_y) or np.isnan(forehead_z):
                # Get the 2D forehead point for display
                forehead_point = face.landmarks[9,:2].copy()
                forehead_point[1] -= 30  # Move up 30 pixels
                
                # Display warning about NaN values
                cv2.putText(frame, "Depth data unavailable - move closer to camera",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.circle(frame, (int(forehead_point[0]), int(forehead_point[1])), 5, (0, 0, 255), -1)
                
                # Show number of samples (will not increase with NaN values)
                cv2.putText(frame, f"Samples: {len(forehead_coordinates)}/{MIN_SAMPLES}",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                point_color = (0, 255, 0)  # Green for valid points by default

                # Check if the forehead point is within the valid range
                if not isInRange(forehead_y, forehead_z, camera_intersect):
                    point_color = (0, 0, 255)  # Red for out of range points
                else:
                    # Store the coordinates
                    forehead_coordinates.append({
                        'position': {
                            'x': float(forehead_x),
                            'y': float(forehead_y),
                            'z': float(forehead_z)
                        }
                    })
                
                # Display forehead position on frame
                # For display, we need to get the 2D coordinates where the forehead point is shown
                # This is the same calculation as in HandFaceTracker.py
                forehead_point = face.landmarks[9,:2].copy()
                forehead_point[1] -= 30  # Move up 30 pixels
                
                cv2.circle(frame, (int(forehead_point[0]), int(forehead_point[1])), 5, point_color, -1)
                
                # Display the 3D coordinates - divided by 10 to show in cm like in the renderer
                cv2.putText(frame, f"Forehead: ({forehead_x/10:.2f}, {forehead_y/10:.2f}, {forehead_z/10:.2f}) cm",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Show number of samples collected
                cv2.putText(frame, f"Samples: {len(forehead_coordinates)}/{MIN_SAMPLES}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # If we have collected enough samples, calculate average and send to robot
    if len(forehead_coordinates) >= MIN_SAMPLES:
        # First, ensure there are no NaN values in the collected coordinates
        valid_coordinates = []
        for coord in forehead_coordinates:
            x, y, z = coord['position']['x'], coord['position']['y'], coord['position']['z']
            if not (np.isnan(x) or np.isnan(y) or np.isnan(z)):
                valid_coordinates.append(coord)
        
        # If we don't have enough valid coordinates, continue collecting
        if len(valid_coordinates) < MIN_SAMPLES:
            cv2.putText(frame, f"Need more valid samples: {len(valid_coordinates)}/{MIN_SAMPLES}",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            continue
        
        # Apply IQR filtering if we have enough samples
        filtered_coordinates = valid_coordinates
        if len(valid_coordinates) >= MAX_SAMPLES:           
            # Extract data for IQR filtering
            x_coords = [m['position']['x'] for m in valid_coordinates]
            y_coords = [m['position']['y'] for m in valid_coordinates]
            z_coords = [m['position']['z'] for m in valid_coordinates]
            
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
            for coord in valid_coordinates:
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

        # Draw face and hands
        frame = renderer.draw(frame, faces, hands)
        key = renderer.waitKey(delay=1)

    if key == 27 or key == ord('q'):
        renderer.exit()
        cv2.destroyAllWindows()
        tracker.exit()
        print("Exiting...")
        break