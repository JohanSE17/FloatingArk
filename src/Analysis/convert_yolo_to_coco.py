import os
import json
from PIL import Image

# Rutas
val_image_dir = 'H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/data/Aquarium-Combined-1/valid/images'
val_label_dir = 'H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/data/Aquarium-Combined-1/valid/labels'
output_json = 'H:/Johan/4to•Semestre/Sistema•Tsunamis/Floating Ark/data/Aquarium-Combined-1/valid/_annotations.json'

# Clases
classes = ['background', 'fish', 'jellyfish', 'penguin', 'puffin', 'shark', 'starfish', 'stingray',
        'ballena', 'delfin', 'foca_leopardo', 'gaviota', 'orca', 'petrel', 'mantaraya', 'tiburon',
        'Humano', 'foca', 'pezDorado Enano']

# Estructura inicial del archivo COCO JSON
coco_data = {
    "images": [],
    "annotations": [],
    "categories": [{"id": i, "name": cls} for i, cls in enumerate(classes, 1)]
}
image_id = 1
annotation_id = 1

# Procesar cada imagen en el directorio
for img_file in os.listdir(val_image_dir):
    if img_file.endswith(('.jpg', '.jpeg', '.png')):
        img_path = os.path.join(val_image_dir, img_file)
        try:
            img = Image.open(img_path)
            width, height = img.size
        except Exception as e:
            print(f"Error al abrir la imagen {img_file}: {e}")
            continue

        # Agregar información de la imagen al archivo COCO
        coco_data["images"].append({
            "id": image_id,
            "file_name": img_file,
            "width": width,
            "height": height
        })

        # Buscar el archivo de etiquetas correspondiente
        label_file = os.path.splitext(img_file)[0] + '.txt'
        label_path = os.path.join(val_label_dir, label_file)
        has_valid_annotations = False

        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line in f:
                    values = line.strip().split()
                    if len(values) < 5:
                        print(f"Advertencia: Línea mal formateada en {label_file}: {line.strip()}")
                        continue
                    try:
                        class_id, x_center, y_center, bbox_width, bbox_height = map(float, values[:5])
                        class_id = int(class_id) + 1  # Ajustar a 1-based (excluir background)

                        # Validar que las coordenadas estén en el rango [0, 1]
                        if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 < bbox_width <= 1 and 0 < bbox_height <= 1):
                            print(f"Advertencia: Coordenadas inválidas en {label_file}: {line.strip()}")
                            continue

                        # Convertir coordenadas YOLO (normalizadas) a coordenadas COCO (absolutas)
                        x_min = (x_center - bbox_width / 2) * width
                        y_min = (y_center - bbox_height / 2) * height
                        box_width = bbox_width * width
                        box_height = bbox_height * height

                        # Validar dimensiones positivas
                        if box_width <= 0 or box_height <= 0:
                            print(f"Advertencia: Caja con dimensiones inválidas en {label_file}: [x_min={x_min}, y_min={y_min}, width={box_width}, height={box_height}]")
                            continue

                        # Agregar anotación al archivo COCO
                        coco_data["annotations"].append({
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": class_id,
                            "bbox": [x_min, y_min, box_width, box_height],
                            "area": box_width * box_height,
                            "iscrowd": 0
                        })
                        annotation_id += 1
                        has_valid_annotations = True
                    except ValueError as e:
                        print(f"Error al procesar línea en {label_file}: {line.strip()}. Error: {e}")
                        continue

        # Solo incrementar image_id si hay anotaciones válidas
        if has_valid_annotations:
            image_id += 1

# Guardar el archivo COCO JSON
with open(output_json, 'w') as f:
    json.dump(coco_data, f, indent=4)

print(f"Archivo COCO JSON generado en {output_json}")