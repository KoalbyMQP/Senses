import depthai as dai
import cv2
import numpy as np
from ultralytics import YOLO

from corners import (
    predict_corners,
    get_corner_coordinates,
    transform_image_corners,
)
from pieces import (
    detect_pieces,
    extract_boxes_labels,
    get_sampled_points,
    get_mapped_pieces,
)
from grid import (
    correct_orientation,
    map_grid_to_coordinates,
    place_pieces_on_board,
    generate_fen,
)

def image_to_fen_pipeline(image, corner_model, piece_model, grid_model, confidence=None):
    # Corner detection
    corner_conf = confidence.get('corner_conf',0.1) if confidence else 0.1
    corner_iou = confidence.get('corner_iou',0.35) if confidence else 0.35
    corners_results = corners.predict_corners(corner_model, image, confidence_threshold=corner_conf, iou_threshold=corner_iou)
    corners = get_corner_coordinates(corners_results)

    # Prospective transform
    warped_image, M = transform_image_corners(image, corners)

        # if model thinks board is upside down, rotate it
    if correct_orientation(warped_image):
        warped_image = cv2.rotate(warped_image, cv2.ROTATE_180)

    # Apply grid to transformed image
    grid_map = map_grid_to_coordinates(warped_image)

    # Piece detection (on non-warped, og image)
    piece_conf = confidence.get('piece_conf',0.5) if confidence else 0.5
    piece_iou = confidence.get('piece_iou',0.35) if confidence else 0.35

    piece_detec_results = detect_pieces(piece_model, image, confidence_threshold=piece_conf, iou_threshold=piece_iou)
    boxes, labels = extract_boxes_labels(piece_detec_results)
    samples = get_sampled_points(boxes, labels)

    # Map pieces to grid
    mapped_pieces = get_mapped_pieces(samples, M)

    # Place and create FEN
    board = [[""]*8 for _ in range(8)]
    place_pieces_on_board(board, mapped_pieces, grid_map)
    fen = generate_fen(board)

    return fen

def main_loop():
    #Load models
    corner_model = YOLO("corners.pt")
    piece_model = YOLO("pieces.pt")
    grid_model = YOLO("grid.pt")

    #Initialize camera
    pipeline = dai.Pipeline()
    cam = pipeline.createColorCamera()
    cam.setBoardSocket(dai.CameraBoardSocket.RGB)
    cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    cam.setInterleaved(False)
    cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

    xout = pipeline.createXLinkOut()
    xout.setStreamName("chess_vision")
    cam.video.link(xout.input)

    with dai.Device(pipeline) as device:
        q = device.getOutputQueue(name="chess_vision", maxSize=4, blocking=False)

        game_over = False
        print("Press 'q' to quit the application.")

        while not game_over:
            cmd = input("Hit 'enter' when your turn is over :)\n")
            if cmd.lower() == 'q':
                print("Exiting the application.")
                game_over = True
                continue

            #Grab snapshot of board
            picture = q.get().getCvFrame()

            #Get FEN from image
            try:
                fen = image_to_fen_pipeline(picture, corner_model, piece_model, grid_model)
                print(f"FEN: {fen}")
            except Exception as e:
                print(f"Error processing image: {e}")
                continue

            #FEN to chess algorithm, determine if game is over, if not suggest next move
            # TODO: determine the chess algorithm to use
            # TODO: determine if game is over
            # game_over = chess_algorithm.is_game_over(fen)
            # if not game_over:
            #     move = chess_algorithm.get_move_from_fen(fen)
            #     print(f"Suggested move: {move}")

        cv2.destroyAllWindows()

if __name__ == "__main__":
    main_loop()