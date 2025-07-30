import torch
from ultralytics import YOLO

# Cargar el modelo preentrenado
model = YOLO("H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/data/yolov8n.pt")

# Entrenar el modelo con el dataset actualizado
model.train(
    data="H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/data/Aquarium-Combined-1/data.yaml",
    epochs=50,
    imgsz=640,
    batch=4,  # Reducido para adaptarse a 8 GB de RAM
    device="cpu",  # Forzado a CPU por falta de GPU
    project="H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/src/analysis/runs",
    name="yolov8_aquarium_with_marine_animals",
    workers=0  # Desactiva trabajadores adicionales para evitar problemas de memoria
)

print("Entrenamiento completado. Pesos guardados en runs/yolov8_aquarium_with_marine_animals/weights/best.pt")