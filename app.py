import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for
from flask_socketio import SocketIO
import xarray as xr
import os
import folium
from roboflow import Roboflow
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
import plotly.express as px
import pandas as pd
import numpy as np
import logging
import torch
from torchvision import transforms
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from PIL import Image
import io
import base64
from video_detection import process_youtube, process_uploaded_video
import cv2
from ultralytics import YOLO
import eventlet
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry
from pytube import YouTube
import time
from cachetools import TTLCache
from datetime import datetime
import copernicusmarine

# Cargar variables de entorno desde .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
POOLER_URL = os.getenv("POOLER_URL")
COPERNICUS_USERNAME = os.getenv("COPERNICUS_USERNAME")
COPERNICUS_PASSWORD = os.getenv("COPERNICUS_PASSWORD")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar el modelo de Roboflow
rf = Roboflow(api_key="sVQEtU8ri6zmZ8eJltVA")
project = rf.workspace().project("floating-ark-marine-animals")
roboflow_model = project.version("1").model

app = Flask(__name__)
app.template_folder = 'src/webapp/templates'
app.static_folder = 'src/webapp/static'
socketio = SocketIO(app, async_mode='eventlet')

# Caché para datos de APIs (expira en 10 minutos)
api_cache = TTLCache(maxsize=100, ttl=600)

connection_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=POOLER_URL,
    sslmode='require'
)

# Cargar modelo YOLOv8
model_yolo = YOLO('H:/Johan/4to_Semestre/Sistema_Tsunamis/Floating Ark/src/Analysis/runs/yolov8_aquarium_with_marine_animals/weights/best.pt')

# Definir clases actualizadas
classes = ['background', 'fish', 'jellyfish', 'penguin', 'puffin', 'shark', 'starfish', 'stingray',
        'ballena', 'delfin', 'foca_leopardo', 'gaviota', 'orca', 'petrel', 'mantaraya', 'tiburon',
        'Humano', 'foca', 'pezDorado Enano']

# Cargar modelo Faster R-CNN
device = torch.device('cpu')
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(in_features, len(classes))
model.load_state_dict(torch.load(os.path.join(app.root_path, 'src/analysis/marine_animal_detection_model_with_whales.pth'), map_location=torch.device('cpu')))
model.to(device)
model.eval()
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Parámetros para estimación de distancia
FOCAL_LENGTH = 1000
KNOWN_WIDTH = {
    'fish': 0.3, 'jellyfish': 0.5, 'penguin': 0.7, 'puffin': 0.4,
    'shark': 2.0, 'starfish': 0.2, 'stingray': 1.5, 'mantaraya': 1.5,
    'ballena': 3.0, 'delfin': 1.5, 'foca_leopardo': 1.8, 'gaviota': 0.6,
    'orca': 2.5, 'petrel': 0.5, 'tiburon': 2.0, 'Humano': 1.8, 'foca': 1.2,
    'pezDorado Enano': 0.1
}

def estimate_distance(box_width, class_name):
    known_width = KNOWN_WIDTH.get(class_name, 1.0)
    return (known_width * FOCAL_LENGTH) / box_width

def get_connection():
    try:
        logger.info("Obteniendo conexión del pool...")
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"Error al obtener conexión del pool: {e}")
        raise Exception("No se pudo establecer conexión con POOLER_URL")

def release_connection(conn):
    try:
        connection_pool.putconn(conn)
        logger.info("Conexión devuelta al pool")
    except Exception as e:
        logger.error(f"Error al devolver conexión al pool: {e}")

def prioritize_region(wave_height, wind_speed, whale_presence):
    # Normalizar los valores para calcular una puntuación (0 a 1)
    wave_score = min(wave_height / 5.0, 1.0)  # Normalizamos respecto a un máximo de 5m
    wind_score = min(wind_speed / 20.0, 1.0)  # Normalizamos respecto a un máximo de 20 m/s
    whale_score = whale_presence  # Ya está normalizado entre 0 y 1

    # Ponderación: 40% altura de ola, 30% velocidad del viento, 30% presencia de ballenas
    total_score = (0.4 * wave_score) + (0.3 * wind_score) + (0.3 * whale_score)

    # Determinar prioridad según la puntuación
    if total_score >= 0.7:
        priority = "Alta prioridad"
    elif total_score >= 0.4:
        priority = "Prioridad media"
    else:
        priority = "Baja prioridad"

    # Evaluar viabilidad para energía eólica offshore (basado en viento y baja presencia de ballenas)
    offshore_viability = "Alta" if wind_speed > 10 and whale_presence < 0.3 else "Media" if wind_speed > 5 else "Baja"

    return priority, offshore_viability

def fetch_openmeteo_data(latitude, longitude, variable):
    try:
        # Validate coordinates
        latitude = max(min(latitude, 90), -90)
        longitude = max(min(longitude, 180), -180)

        # Define the time range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        # Initialize session with retries
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # Fetch wave_height from Marine API
        if variable == "wave_height":
            url = f"https://marine-api.open-meteo.com/v1/marine?latitude={latitude}&longitude={longitude}&hourly=wave_height&start_date={start_date}&end_date={end_date}&timezone=America/Bogota"
            response = session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            hourly = data.get("hourly", {})
            if "wave_height" in hourly and hourly["wave_height"]:
                return hourly["wave_height"][-1]
            logger.warning(f"No se encontraron datos para wave_height en Open-Meteo")
            return 2.0

        # Fetch wind_speed_10m from Weather Forecast API
        elif variable == "wind_speed":
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=wind_speed_10m&start_date={start_date}&end_date={end_date}&timezone=America/Bogota"
            response = session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            hourly = data.get("hourly", {})
            if "wind_speed_10m" in hourly and hourly["wind_speed_10m"]:
                return hourly["wind_speed_10m"][-1]
            logger.warning(f"No se encontraron datos para wind_speed_10m en Open-Meteo")
            return 5.0

        else:
            logger.error(f"Variable no soportada por Open-Meteo: {variable}")
            return 2.0 if variable == "wave_height" else 5.0

    except Exception as e:
        logger.error(f"Error al obtener datos de Open-Meteo: {e}")
        return 2.0 if variable == "wave_height" else 5.0

def fetch_copernicus_data(region, latitude, longitude, variable):
    cache_key = f"copernicus_{region}_{variable}"
    if cache_key in api_cache:
        logger.info(f"Usando caché para Copernicus: {region} - {variable}")
        return api_cache[cache_key]
    try:
        if variable == "wave_height":
            dataset_id = "cmems_mod_glo_wav_my_0.2deg_PT3H-i"
            var_name = "VHM0"
        else:
            logger.info("Copernicus no soporta esta variable, intentando con Open-Meteo...")
            return fetch_openmeteo_data(latitude, longitude, variable)

        # Use current date range
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        if variable == "wave_height":
            df = copernicusmarine.read_dataframe(
                dataset_id=dataset_id,
                variables=[var_name],
                minimum_longitude=longitude - 0.1,
                maximum_longitude=longitude + 0.1,
                minimum_latitude=latitude - 0.1,
                maximum_latitude=latitude + 0.1,
                start_datetime=start_date,
                end_datetime=end_date,
                username=COPERNICUS_USERNAME,
                password=COPERNICUS_PASSWORD
            )
            value = float(df[var_name].iloc[-1]) if not df.empty and not np.isnan(df[var_name].iloc[-1]) else None
            if value is None:
                logger.warning(f"Datos no disponibles para {region}, usando Open-Meteo como fallback")
                return fetch_openmeteo_data(latitude, longitude, variable)
            return value
        else:
            return fetch_openmeteo_data(latitude, longitude, variable)

        api_cache[cache_key] = value

        # Clean up temporary files
        for file in os.listdir():
            if file.startswith("cmems_mod_") and file.endswith(".nc"):
                try:
                    os.remove(file)
                    logger.info(f"Archivo temporal eliminado: {file}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el archivo {file}: {e}")

        return value
    except Exception as e:
        logger.error(f"Error al obtener datos de Copernicus: {e}")
        logger.info("Intentando con Open-Meteo...")
        return fetch_openmeteo_data(latitude, longitude, variable)

def fetch_data_for_region(region_data, timeout=60):
    region, lat, lon = region_data
    try:
        wave_height = fetch_copernicus_data(region, lat, lon, 'VHM0') or 2.0
        wind_speed = fetch_copernicus_data(region, lat, lon, 'wind_speed') or 5.0
        return region, wave_height, wind_speed
    except Exception as e:
        logger.error(f"Error al obtener datos para {region}: {e}")
        return region, 2.0, 5.0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map():
    try:
        regions = [
            ('choco', 5.7, -76.6),
            ('valle_del_cauca', 3.4, -76.5),
            ('cauca', 3.0, -76.6),
            ('narino', 1.8, -78.8),
            ('la_guajira', 11.5, -72.9),
            ('magdalena', 11.2, -74.2),
            ('atlantico', 10.9, -74.8),
            ('bolivar', 10.4, -75.5),
            ('sucre', 9.3, -75.4),
            ('cordoba', 8.8, -75.9),
            ('san_andres_y_providencia', 12.5, -81.7),
            ('archipielago_de_san_bernardo', 9.7, -75.9),
            ('tumaco', 1.8, -78.8),
            ('mosquera', 2.50923, -78.451284),
            ('francisco_pizarro', 2.06433, -78.6115),
            ('gorgona', 2.9667, -78.1833),
        ]
        recommendations = {}
        for region, lat, lon in regions:
            wave_height = fetch_copernicus_data(region, lat, lon, 'wave_height')
            wind_speed = fetch_openmeteo_data(lat, lon, 'wind_speed')
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM whale_sightings WHERE region = %s", (region,))
                result = cursor.fetchone()
                whale_count = result[0] if result else 0
                whale_presence = whale_count / 1035 if whale_count else 0
                logger.info(f"Procesando región {region}: wave_height={wave_height}, wind_speed={wind_speed}, whale_presence={whale_presence}")
                priority, offshore_viability = prioritize_region(wave_height, wind_speed, whale_presence)
                alert = "Riesgo Alto" if wave_height > 3 or wind_speed > 15 else "Riesgo Bajo"
                recommendations[region] = {
                    'wave_height': wave_height,
                    'wind_speed': wind_speed,
                    'whale_presence': whale_presence,
                    'priority': priority,
                    'offshore_viability': offshore_viability,
                    'alert': alert
                }
            finally:
                cursor.close()
                release_connection(conn)
        return render_template('map.html', recommendations=recommendations)
    except Exception as e:
        logger.error(f"Error en /map: {e}")
        return "Error al procesar la solicitud", 500

@app.route('/dashboard')
def dashboard():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT label, COUNT(*) FROM detections GROUP BY label")
            detection_stats = dict(cursor.fetchall())
            cursor.close()
            conn.close()
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        detection_stats = {
            'fish': 20, 'jellyfish': 3, 'penguin': 7, 'puffin': 4, 'shark': 10,
            'starfish': 2, 'stingray': 5, 'ballena': 2, 'delfin': 1, 'foca_leopardo': 1,
            'gaviota': 3, 'orca': 1, 'petrel': 2, 'tiburon': 4, 'mantaraya': 5, 'Humano': 1,
            'foca': 2, 'pezDorado Enano': 1
        }
    return render_template('dashboard.html', detection_stats=detection_stats, update_time="2025-05-22 14:00:00")

@app.route('/static/img/<path:filename>')
def serve_img(filename):
    return send_from_directory(os.path.join(app.root_path, 'src/webapp/static/img'), filename)

@app.route('/safety')
def safety():
    return render_template('safety.html')

@app.route('/recommendations')
def recommendations():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            regions = [
                ('choco', 5.7, -76.6),
                ('valle_del_cauca', 3.4, -76.5),
                ('cauca', 3.0, -76.6),
                ('narino', 1.8, -78.8),
                ('la_guajira', 11.5, -72.9),
                ('magdalena', 11.2, -74.2),
                ('atlantico', 10.9, -74.8),
                ('bolivar', 10.4, -75.5),
                ('sucre', 9.3, -75.4),
                ('cordoba', 8.8, -75.9),
                ('san_andres_y_providencia', 12.5, -81.7),
                ('archipielago_de_san_bernardo', 9.7, -75.9),
                ('tumaco', 1.8, -78.8),
                ('mosquera', 2.50923, -78.451284),
                ('francisco_pizarro', 2.06433, -78.6115),
                ('gorgona', 2.9667, -78.1833),
            ]
            recommendations = {}
            alerts = []
            for region, lat, lon in regions:
                wave_height = fetch_copernicus_data(region, lat, lon, 'VHM0')
                wind_speed = fetch_copernicus_data(region, lat, lon, 'V10')
                cursor.execute("SELECT COUNT(*) FROM whale_sightings WHERE region = %s", (region,))
                result = cursor.fetchone()
                whale_count = result[0] if result else 0
                whale_presence = whale_count / 1035 if whale_count else 0
                priority, offshore_viability = prioritize_region(wave_height, wind_speed, whale_presence)
                if wave_height > 3 or wind_speed > 15:
                    alerts.append(f"¡Alerta en {region.replace('_', ' ').title()}! Riesgo de tsunami o tormenta.")
                recommendations[region] = {
                    'wave_height': wave_height,
                    'wind_speed': wind_speed,
                    'whale_presence': whale_presence,
                    'priority': priority,
                    'offshore_viability': offshore_viability
                }
                cursor.close()
                conn.close()

        # Generar gráfico con Plotly
        df = pd.DataFrame([
            {
                'Región': region.replace('_', ' ').title(),
                'Altura de Ola (m)': data['wave_height'],
                'Velocidad del Viento (m/s)': data['wind_speed'],
                'Prioridad': data['priority'],
                'Viabilidad Eólica Offshore': data['offshore_viability']
            }
            for region, data in recommendations.items()
        ])
        fig = px.bar(df, x='Región', y=['Altura de Ola (m)', 'Velocidad del Viento (m/s)'],
                    barmode='group', color='Prioridad', title="Condiciones por Región",
                    color_discrete_map={
                        'Alta prioridad': '#FF0000',
                        'Prioridad media': '#FFA500',
                        'Baja prioridad': '#008000'
                    })
        graph_json = fig.to_json()

        return render_template('recommendations.html', recommendations=recommendations, graph_json=graph_json, alerts=alerts)
    except Exception as e:
        logger.error(f"Error en /recommendations: {e}")
        return jsonify({'error': 'Error al obtener recomendaciones'}), 500

@app.route('/simulation/<region>')
def simulation(region):
    try:
        coordinates = {
            'choco': (5.7, -76.6),
            'valle_del_cauca': (3.4, -76.5),
            'cauca': (3.0, -76.6),
            'narino': (1.8, -78.8),
            'la_guajira': (11.5, -72.9),
            'magdalena': (11.2, -74.2),
            'atlantico': (10.9, -74.8),
            'bolivar': (10.4, -75.5),
            'sucre': (9.3, -75.4),
            'cordoba': (8.8, -75.9),
            'san_andres_y_providencia': (12.5, -81.7),
            'archipielago_de_san_bernardo': (9.7, -75.9),
            'tumaco': (1.8, -78.8),
            'mosquera': (2.50923, -78.451284),
            'francisco_pizarro': (2.06433, -78.6115),
        }
        if region not in coordinates:
            return jsonify({'error': 'Región no encontrada'}), 404
        lat, lon = coordinates[region]
        base_wave_height = fetch_copernicus_data(region, lat, lon, 'VHM0')
        base_wind_speed = fetch_copernicus_data(region, lat, lon, 'V10')
        time = pd.date_range(start=datetime.now() - pd.Timedelta(hours=24), periods=24, freq='h')
        wave_heights = np.random.normal(loc=base_wave_height, scale=0.2, size=24)
        wind_speeds = np.random.normal(loc=base_wind_speed, scale=0.5, size=24)
        df = pd.DataFrame({
            'time': time,
            'wave_height': wave_heights,
            'wind_speed': wind_speeds
        })
        fig = px.line(df, x='time', y=['wave_height', 'wind_speed'], title=f"Simulación de Altura de Olas y Velocidad del Viento - {region.title()}")
        graph_json = fig.to_json()
        return render_template('simulation.html', region=region, graph_json=graph_json)
    except Exception as e:
        logger.error(f"Error en /simulation: {e}")
        return jsonify({'error': 'Error al generar simulación'}), 500

@app.route('/segmentation')
def segmentation():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT region, wave_height, fauna_presence, flood_risk, classification, usage FROM sea_segmentation")
            segmentation_data = [
                {
                    'Región': row[0],
                    'Altura Media de Ola (m)': row[1],
                    'Presencia de Fauna': row[2],
                    'Riesgo de Inundación': row[3],
                    'Clasificación': row[4],
                    'Uso Recomendado': row[5].split(' | ')[0] if '|' in row[5] else row[5],
                    'Caso de Uso': row[5].split(' | ')[1] if '|' in row[5] else None,
                    'Viabilidad Hidráulica (Pueblos SMART)': 'Alta' if row[1] > 1.5 and row[2] < 0.3 else 'Media' if row[1] > 1.0 else 'Baja',
                    'Viabilidad Hidráulica (Recolección)': 'Alta' if row[1] > 1.0 and row[2] < 0.5 else 'Media' if row[1] > 0.5 else 'Baja'
                }
                for row in cursor.fetchall()
            ]
            cursor.close()
            conn.close()

        # Generar gráfico con Plotly
        df = pd.DataFrame(segmentation_data)
        fig = px.bar(df, x='Región', y='Altura Media de Ola (m)', color='Clasificación', title="Segmentación por Altura de Olas")
        graph_json = fig.to_json()

        return render_template('segmentation.html', segmentation_data=segmentation_data, graph_json=graph_json)
    except Exception as e:
        logger.error(f"Error en /segmentation: {e}")
        try:
            csv_path = os.path.join(app.root_path, 'data/processed/sea_segmentation.csv')
            if not os.path.exists(csv_path):
                logger.error(f"Archivo CSV no encontrado: {csv_path}")
                return jsonify({'error': 'Datos de segmentación no disponibles'}), 500
            df = pd.read_csv(csv_path, sep=',')
            segmentation_data = [
                {
                    'Región': row['region'],
                    'Altura Media de Ola (m)': row['wave_height'],
                    'Presencia de Fauna': row['fauna_presence'],
                    'Riesgo de Inundación': row['flood_risk'],
                    'Clasificación': row['classification'],
                    'Uso Recomendado': row['usage'].split(' | ')[0] if '|' in row['usage'] else row['usage'],
                    'Caso de Uso': row['usage'].split(' | ')[1] if '|' in row['usage'] else None,
                    'Viabilidad Hidráulica (Pueblos SMART)': 'Alta' if row['wave_height'] > 1.5 and row['fauna_presence'] < 0.3 else 'Media' if row['wave_height'] > 1.0 else 'Baja',
                    'Viabilidad Hidráulica (Recolección)': 'Alta' if row['wave_height'] > 1.0 and row['fauna_presence'] < 0.5 else 'Media' if row['wave_height'] > 0.5 else 'Baja'
                }
                for _, row in df.iterrows()
            ]
            fig = px.bar(df, x='region', y='wave_height', color='classification', title="Segmentación por Altura de Olas")
            graph_json = fig.to_json()
            return render_template('segmentation.html', segmentation_data=segmentation_data, graph_json=graph_json)
        except Exception as e2:
            logger.error(f"Error en fallback CSV: {e2}")
            return jsonify({'error': 'Error al obtener segmentación'}), 500

@app.route('/detect', methods=['GET', 'POST'])
def detect():
    try:
        if request.method == 'POST':
            # Procesar imágenes subidas o URLs
            if 'file' in request.files and request.files['file'].filename != '':
                file = request.files['file']
                filename = file.filename
                upload_dir = os.path.join(app.root_path, 'Uploads')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
            elif 'image_url' in request.form and request.form['image_url']:
                image_url = request.form['image_url']
                response = requests.get(image_url)
                if response.status_code != 200:
                    return jsonify({'error': 'No se pudo descargar la imagen'}), 400
                filename = 'temp_image.jpg'
                upload_dir = os.path.join(app.root_path, 'Uploads')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                filepath = os.path.join(upload_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
            else:
                logger.info("No file part or URL in request")
                return jsonify({'error': 'No file or URL provided'}), 400

            # Procesar imagen
            if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
                logger.info("Processing image")
                image = Image.open(filepath).convert('RGB')
                image_tensor = transform(image).unsqueeze(0).to(device)
                with torch.no_grad():
                    prediction = model(image_tensor)[0]
                conf_threshold = 0.5
                mask = prediction['scores'] >= conf_threshold
                boxes = prediction['boxes'][mask].cpu().numpy()
                labels = prediction['labels'][mask].cpu().numpy()
                scores = prediction['scores'][mask].cpu().numpy()
                detections = [
                    {
                        'label': classes[label],
                        'score': float(score),
                        'box': [float(b) for b in box],
                        'distance': estimate_distance(box[2] - box[0], classes[label])
                    }
                    for box, label, score in zip(boxes, labels, scores)
                ]
                # Emitir alerta si se detectan ballenas u orcas
                alert = any(detection['label'] in ['ballena', 'orca'] for detection in detections)
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

                # Guardar detecciones en Supabase
                try:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                    for detection in detections:
                        cursor.execute(
                            "INSERT INTO detections (label, score, distance, latitude, longitude, timestamp) VALUES (%s, %s, %s, %s, %s, NOW())",
                            (detection['label'], detection['score'], detection['distance'], 12.5, -81.7)
                        )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error al guardar en Supabase: {e}")

                os.remove(filepath)
                return render_template('detection.html', detections=detections, image_data=img_str, frames=None, is_video=False, alert=alert)

            # Procesar video
            elif filename.lower().endswith('.mp4'):
                logger.info("Processing video")
                try:
                    detections, processed_frames = process_uploaded_video(filepath, model_yolo, classes, KNOWN_WIDTH, FOCAL_LENGTH)
                    frames = []
                    for frame in processed_frames[:10]:  # Limitar a 10 frames para renderizado
                        _, buffer = cv2.imencode('.png', frame)
                        frames.append(base64.b64encode(buffer).decode('utf-8'))

                    # Emitir alerta si se detectan ballenas u orcas
                    alert = any(detection['label'] in ['ballena', 'orca'] for detection in detections)

                    # Guardar detecciones en Supabase
                    try:
                        with get_connection() as conn:
                            cursor = conn.cursor()
                        for detection in detections:
                            cursor.execute(
                                "INSERT INTO detections (label, score, distance, latitude, longitude, timestamp) VALUES (%s, %s, %s, %s, %s, NOW())",
                                (detection['label'], detection['score'], detection['distance'], 12.5, -81.7)
                            )
                        conn.commit()
                        cursor.close()
                        conn.close()
                    except Exception as e:
                        logger.error(f"Error al guardar en Supabase: {e}")

                    os.remove(filepath)
                    return render_template('detection.html', detections=detections, image_data=None, frames=frames, is_video=True, alert=alert)
                except Exception as e:
                    logger.error(f"Error al procesar video: {e}")
                    os.remove(filepath)
                    return jsonify({'error': 'Error al procesar el video'}), 500

            else:
                logger.info("Formato de archivo no soportado")
                os.remove(filepath)
                return jsonify({'error': 'Formato de archivo no soportado'}), 400

        # Manejo de solicitud GET
        return render_template('detection.html', detections=None, image_data=None, frames=None, is_video=False)

    except Exception as e:
        logger.error(f"Error en /detect: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/detect_youtube', methods=['POST'])
def detect_youtube():
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url')
        if not youtube_url:
            return jsonify({'error': 'No YouTube URL provided'}), 400

        # Procesar video con YOLO (descarga completa)
        detections, processed_frames = process_youtube(youtube_url, model_yolo, classes, KNOWN_WIDTH, FOCAL_LENGTH)
        frames = []
        for frame in processed_frames[:10]:  # Limitar a 10 frames para renderizado
            _, buffer = cv2.imencode('.jpg', frame)
            frames.append(base64.b64encode(buffer).decode('utf-8'))

        # Guardar detecciones en Supabase
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
            for detection in detections:
                cursor.execute(
                    "INSERT INTO detections (label, score, distance, latitude, longitude, timestamp) VALUES (%s, %s, %s, %s, %s, NOW())",
                    (detection['label'], detection['score'], detection['distance'], 12.5, -81.7)
                )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error al guardar en Supabase: {e}")

        return render_template('detection.html', detections=detections, image_data=None, frames=frames, is_video=True)
    except Exception as e:
        logger.error(f"Error en /detect_youtube: {e}")
        return jsonify({'error': 'Error al procesar el video de YouTube'}), 500

@app.route('/detect_youtube_iframe', methods=['POST'])
def detect_youtube_iframe():
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url')
        if not youtube_url:
            return jsonify({'error': 'No YouTube URL provided'}), 400
        # Solo devolvemos la URL para que el frontend la use con el iframe
        return jsonify({'youtube_url': youtube_url})
    except Exception as e:
        logger.error(f"Error en /detect_youtube_iframe: {e}")
        return jsonify({'error': 'Error al procesar la solicitud de YouTube'}), 500

def estimate_distance(box_width, class_name, known_widths, focal_length):
    known_width = known_widths.get(class_name, 1.0)
    return (known_width * focal_length) / box_width

@app.route('/detect_frame', methods=['POST'])
def detect_frame():
    try:
        data = request.get_json()
        image_data = data.get('image')
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
        # Decodificar la imagen desde base64
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Procesar con YOLOv8
        results = model_yolo(frame)
        detections = []
        for result in results:
            for box in result.boxes:
                class_name = classes[int(box.cls)]
                score = float(box.conf.cpu().numpy())
                box_coords = box.xyxy[0].cpu().numpy()
                box_width = box_coords[2] - box_coords[0]
                distance = estimate_distance(box_width, class_name)
                detections.append({
                    'label': class_name,
                    'score': score,
                    'distance': distance
                })
        return jsonify(detections)
    except Exception as e:
        logger.error(f"Error en /detect_frame: {e}")
        return jsonify({'error': 'Error al procesar el frame'}), 500

@app.route('/get_detections')
def get_detections():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT latitude, longitude, label, score, distance, timestamp FROM detections")
            detections = [
            {'latitude': row[0], 'longitude': row[1], 'label': row[2], 'score': row[3], 'distance': row[4], 'timestamp': row[5]}
            for row in cursor.fetchall()
        ]
            cursor.close()
            conn.close()
        return jsonify(detections)
    except Exception as e:
        logger.error(f"Error al obtener detecciones: {e}")
        return jsonify([])

streaming = False

def generate_stream():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model_yolo(frame)
        annotated_frame = results[0].plot()
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('stream_frame', {'frame': frame_base64})
        socketio.sleep(0.03)
    cap.release()

@socketio.on('start_stream')
def start_stream():
    global streaming
    streaming = True
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("No se pudo abrir la cámara")
            socketio.emit('stream_error', {'error': 'No se pudo abrir la cámara'})
            streaming = False
            return
        while streaming:
            ret, frame = cap.read()
            if not ret:
                logger.error("No se pudo capturar frame")
                break
            results = model_yolo(frame)
            annotated_frame = results[0].plot()
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('stream_frame', {'frame': frame_base64})
            socketio.sleep(0.1)
        cap.release()
    except Exception as e:
        logger.error(f"Error en streaming: {e}")
        socketio.emit('stream_error', {'error': 'Error en streaming'})
    finally:
        streaming = False

@socketio.on('stop_stream')
def handle_stop_stream():
    global streaming
    streaming = False
    logger.info("Streaming detenido")

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)