import copernicusmarine as cm
import os

# Define the dataset IDs and temporal extents
datasets = [
    {
        "dataset_id": "cmems_mod_glo_wav_my_0.2deg_PT3H-i",
        "start_date": "2020-01-01",
        "end_date": "2023-04-30",
        "output_filename": "wave_data_my.nc"
    },
    {
        "dataset_id": "cmems_mod_glo_wav_myint_0.2deg_PT3H-i",
        "start_date": "2023-05-01",
        "end_date": "2025-04-26",
        "output_filename": "wave_data_myint.nc"
    }
]

# Define the spatial extent
lon_min = -82.0
lon_max = -71.0
lat_min = 1.0
lat_max = 14.0

# Define the variables to download
variables = ["VHM0"]

# Get the base directory (two levels up from this script)
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Absolute path to the output directory
output_dir = os.path.join(base_dir, "data", "raw")
output_path = os.path.join(output_dir, "wave_data.nc")

# Create directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Check if the final combined file already exists
if not os.path.exists(output_path):
    try:
        # Download data for each dataset
        downloaded_files = []
        for dataset in datasets:
            output_file_path = os.path.join(output_dir, dataset["output_filename"])
            if not os.path.exists(output_file_path):
                cm.subset(
                    dataset_id=dataset["dataset_id"],
                    variables=variables,
                    minimum_longitude=lon_min,
                    maximum_longitude=lon_max,
                    minimum_latitude=lat_min,
                    maximum_latitude=lat_max,
                    start_datetime=dataset["start_date"],
                    end_datetime=dataset["end_date"],
                    output_directory=output_dir,
                    output_filename=dataset["output_filename"]
                )
                # Check the actual filename created (since copernicusmarine might rename)
                expected_file = dataset["output_filename"]
                actual_file = expected_file
                for f in os.listdir(output_dir):
                    if f.startswith("wave_data_0.2deg") and f not in downloaded_files:
                        actual_file = f
                        break
                downloaded_files.append(actual_file)
                print(f"Datos descargados: {actual_file}")
            else:
                downloaded_files.append(dataset["output_filename"])
                print(f"El archivo {dataset['output_filename']} ya existe.")
        print("Datos de olas descargados exitosamente en archivos separados.")
        print(f"Archivos generados: {', '.join(downloaded_files)}")
        print("Nota: Puedes combinar estos archivos en un solo archivo usando xarray si es necesario.")
    except Exception as e:
        print(f"Error al descargar datos de olas: {str(e)}")
        print("Por favor, verifica los dataset IDs en https://data.marine.copernicus.eu/ o ajusta las fechas.")
else:
    print("El archivo de datos de olas ya existe.")