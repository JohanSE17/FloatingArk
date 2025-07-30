import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.ops import box_iou
import os
from PIL import Image
import json
import numpy as np
from sklearn.metrics import precision_recall_curve, average_precision_score

# Definir clases de animales marinos
classes = ['background', 'fish', 'jellyfish', 'penguin', 'puffin', 'shark', 'starfish', 'stingray',
        'ballena', 'delfin', 'foca_leopardo', 'gaviota', 'orca', 'petrel', 'mantaraya', 'tiburon',
        'Humano', 'foca', 'pezDorado Enano']
num_classes = len(classes)

# Dataset personalizado para imágenes con anotaciones COCO
class MarineAnimalDataset(Dataset):
    def __init__(self, image_dir, annotation_file, transform=None):
        self.image_dir = image_dir
        self.transform = transform
        if not os.path.exists(annotation_file):
            raise FileNotFoundError(f"El archivo {annotation_file} no existe. Asegúrate de generar las anotaciones COCO con convert_yolo_to_coco.py.")
        with open(annotation_file, 'r') as f:
            self.annotations = json.load(f)
        self.images = {img['id']: img['file_name'] for img in self.annotations['images']}
        self.categories = {cat['id']: cat['name'] for cat in self.annotations['categories']}

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_id = list(self.images.keys())[idx]
        img_path = os.path.join(self.image_dir, self.images[img_id])
        image = Image.open(img_path).convert('RGB')

        # Obtener anotaciones para la imagen
        anns = [ann for ann in self.annotations['annotations'] if ann['image_id'] == img_id]
        boxes = []
        labels = []
        for ann in anns:
            x, y, w, h = ann['bbox']
            if w > 0 and h > 0:  # Solo incluir cajas con dimensiones positivas
                boxes.append([x, y, x + w, y + h])
                category_name = self.categories[ann['category_id']]
                label_idx = classes.index(category_name)
                labels.append(label_idx)

        if len(boxes) == 0:  # Si no hay anotaciones válidas, omitir la imagen
            return None, None

        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)

        target = {}
        target['boxes'] = boxes
        target['labels'] = labels

        if self.transform:
            image = self.transform(image)

        return image, target

# Transformaciones para imágenes
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Crear dataset y dataloader
train_image_dir = 'H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/data/Aquarium-Combined-1/train/images'
train_annotation_file = 'H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/data/Aquarium-Combined-1/train/_annotations.json'
val_image_dir = 'H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/data/Aquarium-Combined-1/valid/images'
val_annotation_file = 'H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/data/Aquarium-Combined-1/valid/_annotations.json'

try:
    train_dataset = MarineAnimalDataset(train_image_dir, train_annotation_file, transform=transform)
    val_dataset = MarineAnimalDataset(val_image_dir, val_annotation_file, transform=transform)
except FileNotFoundError as e:
    print(e)
    print("Por favor, ejecuta convert_yolo_to_coco.py para generar las anotaciones COCO.")
    exit(1)

# Filtrar imágenes sin anotaciones válidas
train_dataset = [item for item in train_dataset if item[0] is not None]
val_dataset = [item for item in val_dataset if item[0] is not None]

train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True, collate_fn=lambda x: tuple(zip(*[i for i in x if i[0] is not None])))
val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, collate_fn=lambda x: tuple(zip(*[i for i in x if i[0] is not None])))

# Definir modelo Faster R-CNN
def get_model(num_classes):
    model = models.detection.fasterrcnn_resnet50_fpn(weights='DEFAULT')
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    return model

# Configurar dispositivo
device = torch.device('cpu')  # Ajustado a CPU por hardware limitado (8 GB RAM)

# Inicializar modelo
model = get_model(num_classes)
model.to(device)

# Definir optimizador
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)

# Entrenamiento
num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for images, targets in train_loader:
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        optimizer.zero_grad()
        losses.backward()
        optimizer.step()
        running_loss += losses.item()
    print(f'Epoca {epoch+1}, Pérdida: {running_loss / len(train_loader)}')

# Evaluación con mAP
def compute_ap(gt_boxes, gt_labels, pred_boxes, pred_labels, pred_scores, iou_threshold=0.5):
    aps = []
    for label in range(1, num_classes):  # Ignorar background (label 0)
        true_positives = []
        scores = []
        num_gt = 0

        gt_mask = gt_labels == label
        pred_mask = pred_labels == label

        if gt_mask.sum() == 0:
            continue

        num_gt = gt_mask.sum().item()
        gt_b = gt_boxes[gt_mask]
        pred_b = pred_boxes[pred_mask]
        pred_s = pred_scores[pred_mask]

        if len(pred_b) == 0:
            aps.append(0)
            continue

        sorted_indices = torch.argsort(pred_s, descending=True)
        pred_b = pred_b[sorted_indices]
        pred_s = pred_s[sorted_indices]

        ious = box_iou(pred_b, gt_b)
        used = torch.zeros(gt_b.shape[0], dtype=torch.bool)

        tp = 0
        fp = 0
        for i in range(len(pred_b)):
            if used.all():
                fp += 1
                true_positives.append(0)
                scores.append(pred_s[i].item())
                continue

            max_iou, max_idx = ious[i].max(dim=0)
            if max_iou >= iou_threshold and not used[max_idx]:
                tp += 1
                used[max_idx] = 1
                true_positives.append(1)
            else:
                fp += 1
                true_positives.append(0)
            scores.append(pred_s[i].item())

        true_positives = np.array(true_positives)
        scores = np.array(scores)
        indices = np.argsort(-scores)
        true_positives = true_positives[indices]
        cum_tp = np.cumsum(true_positives)
        cum_fp = np.cumsum(1 - true_positives)
        recall = cum_tp / num_gt if num_gt > 0 else np.zeros_like(cum_tp)
        precision = cum_tp / (cum_tp + cum_fp + 1e-10)
        ap = average_precision_score(true_positives, scores)
        aps.append(ap)

    return np.mean(aps) if aps else 0

# Evaluación
model.eval()
all_maps = []
with torch.no_grad():
    for images, targets in val_loader:
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        predictions = model(images)

        for pred, target in zip(predictions, targets):
            pred_boxes = pred['boxes']
            pred_labels = pred['labels']
            pred_scores = pred['scores']
            gt_boxes = target['boxes']
            gt_labels = target['labels']

            conf_threshold = 0.5
            mask = pred_scores >= conf_threshold
            pred_boxes = pred_boxes[mask]
            pred_labels = pred_labels[mask]
            pred_scores = pred_scores[mask]

            ap = compute_ap(gt_boxes, gt_labels, pred_boxes, pred_labels, pred_scores)
            all_maps.append(ap)

mean_ap = np.mean(all_maps)
print(f'mAP@0.5: {mean_ap:.4f}')

# Guardar modelo
output_path = 'H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/src/analysis/marine_animal_detection_model_with_whales.pth'
torch.save(model.state_dict(), output_path)
print(f"Modelo CNN guardado en {output_path}")