import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
POOLER_URL   = os.getenv("POOLER_URL")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    try:
        logger.info("Intentando conexión DIRECTA...")
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        logger.warning(f"Conexión directa falló: {e}")
        if POOLER_URL:
            logger.info("Intentando conexión vía POOLER IPv4...")
            return psycopg2.connect(POOLER_URL, sslmode='require')
        raise e

# Intentar conectar
conn = get_connection()
cursor = conn.cursor()

# Lista de regiones
regions = [
    "choco", "valle_del_cauca", "cauca", "narino",
    "la_guajira", "magdalena", "atlantico", "bolivar", "sucre", "cordoba",
    "san_andres_y_providencia", "archipielago_de_san_bernardo"
]

# Cargar datos de energía de olas
for region in regions:
    df = pd.read_csv(f'data/processed/wave_energy_{region}.csv')
    data = [
        (region, row['latitude'], row['longitude'], row['time'], row['energy'],
        f'SRID=4326;POINT({row["longitude"]} {row["latitude"]})')
        for _, row in df.iterrows()
    ]
    query = """
        INSERT INTO wave_energy (region, latitude, longitude, time, energy, geom)
        VALUES %s
    """
    execute_values(cursor, query, data)
    logger.info(f"Datos de energía de olas para {region} cargados en Supabase.")

# Cargar datos de avistamientos de ballenas
for region in regions:
    df = pd.read_csv(f'data/processed/whale_sightings_{region}.csv')
    data = [
        (region, row['latitude_point'], row['longitude_point'],
        int(row['month']), int(row['year']),
        f'SRID=4326;POINT({row["longitude_point"]} {row["latitude_point"]})')
        for _, row in df.iterrows()
    ]
    query = """
        INSERT INTO whale_sightings (region, latitude, longitude, month, year, geom)
        VALUES %s
    """
    execute_values(cursor, query, data)
    logger.info(f"Datos de avistamientos de ballenas para {region} cargados en Supabase.")

# Cargar datos meteorológicos
for region in regions:
    df = pd.read_csv(f'data/processed/meteorological_data_{region}.csv', errors='ignore')
    data = [
        (region, row['latitude'], row['longitude'], row['fecha'],
        row['velocidad_viento'], row['temperatura'],
        f'SRID=4326;POINT({row["longitude"]} {row["latitude"]})')
        for _, row in df.iterrows()
    ]
    query = """
        INSERT INTO meteorological_data (region, latitude, longitude, fecha, velocidad_viento, temperatura, geom)
        VALUES %s
    """
    execute_values(cursor, query, data)
    logger.info(f"Datos meteorológicos para {region} cargados en Supabase.")

# Confirmar cambios y cerrar conexión
conn.commit()
cursor.close()
conn.close()
logger.info("Datos cargados exitosamente en Supabase.")
