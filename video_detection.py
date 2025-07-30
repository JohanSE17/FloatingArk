import cv2
from ultralytics import YOLO
from pytube import YouTube
import base64
import os

# Asegúrate de que el modelo YOLO esté cargado (puedes pasarlo como argumento o cargarlo aquí)
model = YOLO('H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/src/analysis/runs/yolov8_aquarium_with_marine_animals/weights/best.pt')

# Parámetros para estimación de distancia
FOCAL_LENGTH = 1000
KNOWN_WIDTH = {
    'fish': 0.3, 'jellyfish': 0.5, 'penguin': 0.7, 'puffin': 0.4,
    'shark': 2.0, 'starfish': 0.2, 'stingray': 1.5,
    'ballena': 3.0, 'delfin': 1.5, 'foca_leopardo': 1.8, 'gaviota': 0.6,
    'orca': 2.5, 'petrel': 0.5, 'tiburon': 2.0
}

def estimate_distance(box_width, class_name):
    known_width = KNOWN_WIDTH.get(class_name, 1.0)
    return (known_width * FOCAL_LENGTH) / box_width

def process_stream():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)
        annotated_frame = results[0].plot()
        for result in results:
            for box in result.boxes:
                class_name = result.names[int(box.cls)]
                box_coords = box.xyxy[0].cpu().numpy()
                box_width = box_coords[2] - box_coords[0]
                distance = estimate_distance(box_width, class_name)
                cv2.putText(annotated_frame, f'Dist: {distance:.2f}m', (int(box_coords[0]), int(box_coords[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow('Detección en Tiempo Real', annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

def process_youtube(url, model, classes, known_widths, focal_length):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').first()
    temp_video = 'temp_video.mp4'
    stream.download(output_path='.', filename=temp_video)
    cap = cv2.VideoCapture(temp_video)
    frames = []
    detections = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)
        annotated_frame = results[0].plot()
        for result in results:
            for box in result.boxes:
                class_name = classes[int(box.cls)]
                box_coords = box.xyxy[0].cpu().numpy()
                box_width = box_coords[2] - box_coords[0]
                distance = estimate_distance(box_width, class_name, known_widths, focal_length)
                cv2.putText(annotated_frame, f'Dist: {distance:.2f}m', (int(box_coords[0]), int(box_coords[1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                detections.append({
                    'label': class_name,
                    'score': float(box.conf.cpu().numpy()),
                    'distance': distance
                })
        frames.append(annotated_frame)
    cap.release()
    os.remove(temp_video)
    return detections, frames

def process_uploaded_video(filename, model, classes, known_widths, focal_length):
    cap = cv2.VideoCapture(filename)
    frames = []
    detections = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)
        annotated_frame = results[0].plot()
        for result in results:
            for box in result.boxes:
                class_name = classes[int(box.cls)]
                box_coords = box.xyxy[0].cpu().numpy()
                box_width = box_coords[2] - box_coords[0]
                distance = estimate_distance(box_width, class_name, known_widths, focal_length)
                detections.append({
                    'label': class_name,
                    'score': float(box.conf.cpu().numpy()),
                    'distance': distance
                })
        frames.append(annotated_frame)
    cap.release()
    return detections, frames

if __name__ == "__main__":
    process_stream()