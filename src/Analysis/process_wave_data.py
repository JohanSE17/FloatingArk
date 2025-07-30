import xarray as xr
import pandas as pd
import numpy as np
import os

# Define regiones con sus coordenadas
regions = {
    "choco": {"lon_min": -77.5, "lon_max": -76.0, "lat_min": 5.0, "lat_max": 8.7},
    "valle_del_cauca": {"lon_min": -77.5, "lon_max": -76.5, "lat_min": 3.5, "lat_max": 5.0},
    "cauca": {"lon_min": -77.5, "lon_max": -76.5, "lat_min": 2.0, "lat_max": 3.5},
    "narino": {"lon_min": -79.0, "lon_max": -78.5, "lat_min": 1.0, "lat_max": 2.0},
    "la_guajira": {"lon_min": -72.5, "lon_max": -71.0, "lat_min": 11.0, "lat_max": 12.5},
    "magdalena": {"lon_min": -74.5, "lon_max": -73.5, "lat_min": 10.0, "lat_max": 11.5},
    "atlantico": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 10.5, "lat_max": 11.0},
    "bolivar": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 9.5, "lat_max": 10.5},
    "sucre": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 9.0, "lat_max": 10.0},
    "cordoba": {"lon_min": -76.5, "lon_max": -75.5, "lat_min": 8.5, "lat_max": 9.5},
    "san_andres_y_providencia": {"lon_min": -82.0, "lon_max": -81.0, "lat_min": 12.2, "lat_max": 14.0},
    "archipielago_de_san_bernardo": {"lon_min": -75.8, "lon_max": -75.5, "lat_min": 9.7, "lat_max": 10.0},
}

# Define the directory for input and output (H:\Johan to avoid special characters)
working_dir = r"H:\Johan"

# Define paths to the input and output files
input_file = os.path.join(working_dir, "wave_data.nc")
output_file = os.path.join(working_dir, "sea_segmentation.csv")

# Debug: Print the paths to verify
print(f"Ruta del directorio de trabajo: {working_dir}")
print(f"Ruta del archivo de entrada: {input_file}")
print(f"Ruta del archivo de salida: {output_file}")

# Check if input file exists
if not os.path.exists(input_file):
    print(f"Error: El archivo {input_file} no existe.")
    print("Asegúrate de haber movido 'wave_data.nc' a H:\\Johan.")
    exit(1)

try:
    # Load the wave data
    print("Cargando datos de olas...")
    ds = xr.open_dataset(input_file)

    # Initialize dictionary for average wave heights
    avg_wave_heights = {}

    for region, coords in regions.items():
        try:
            # Select subset for the region
            subset = ds.sel(longitude=slice(coords["lon_min"], coords["lon_max"]),
                        latitude=slice(coords["lat_min"], coords["lat_max"]))

            # Calculate average wave height (VHM0)
            mean_wave_height = subset['VHM0'].mean().item()
            avg_wave_heights[region] = mean_wave_height
        except Exception as e:
            print(f"Error procesando región {region}: {str(e)}")
            avg_wave_heights[region] = np.nan

    # Classify regions based on average wave height
    classification = {}
    for region, avg_height in avg_wave_heights.items():
        if pd.isna(avg_height):
            classification[region] = {"Clasificación": "Sin datos", "Uso Recomendado": "No aplicable"}
        elif avg_height >= 2.5:
            classification[region] = {"Clasificación": "Zona de alto impacto", "Uso Recomendado": "Generación de energía"}
        elif avg_height >= 1.0:
            classification[region] = {"Clasificación": "Zona de impacto medio", "Uso Recomendado": "Plataformas habitacionales"}
        else:
            classification[region] = {"Clasificación": "Zona de bajo impacto", "Uso Recomendado": "Plataformas habitacionales"}

    # Save classification to a CSV file
    df = pd.DataFrame([
        {"Región": region, "Altura Media de Ola (m)": avg_wave_heights[region],
        "Clasificación": data["Clasificación"], "Uso Recomendado": data["Uso Recomendado"]}
        for region, data in classification.items()
    ])
    df.to_csv(output_file, index=False)

    print(f"Segmentación del mar completada y guardada en '{output_file}'.")
    print("Por favor, mueve el archivo 'sea_segmentation.csv' de vuelta a 'H:\\Johan\\4to•Semestre\\Sistema•Tsunamis\\Floating Ark\\data\\processed'.")
except Exception as e:
    print(f"Error al procesar los datos: {str(e)}")