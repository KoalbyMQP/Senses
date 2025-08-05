from ultralytics import YOLO


def train_yolo(model, file_path, output_name, epochs=3, batch_size=5):
    model = YOLO(model)
    result = model.train(
        data = "Datasets/"+file_path+"/data.yaml",
        epochs = epochs,
        batch = batch_size,
        name = output_name,
        save = True
    )

    # Evaluate the model's performance on the validation set
    metrics = model.val()
    print(metrics.box.map)

    # Save the trained model
    model.save("f{output_name}.pt")

    return result, metrics

# Example usage
train_yolo("yolov5s.pt", "ox_real", "oximiter_digits", epochs=200, batch_size=32)