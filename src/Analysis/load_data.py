# Cargar datos de olas
try:
    ds_waves = xr.open_dataset('data/raw/wave_data.nc')
    logger.info("Datos de olas cargados correctamente.")
except Exception as e:
    logger.error(f"Error al cargar datos de olas: {e}")
    sys.exit(1)

# Definir regiones, incluyendo el Archipiélago de San Bernardo
regions = {
    # Pacífico
    "Choco": {"lon_min": -77.5, "lon_max": -76.0, "lat_min": 5.0, "lat_max": 8.7},
    "Valle del Cauca": {"lon_min": -77.5, "lon_max": -76.5, "lat_min": 3.5, "lat_max": 5.0},
    "Cauca": {"lon_min": -77.5, "lon_max": -76.5, "lat_min": 2.0, "lat_max": 3.5},
    "Narino": {"lon_min": -79.0, "lon_max": -78.5, "lat_min": 1.0, "lat_max": 2.0},
    # Caribe
    "La Guajira": {"lon_min": -72.5, "lon_max": -71.0, "lat_min": 11.0, "lat_max": 12.5},
    "Magdalena": {"lon_min": -74.5, "lon_max": -73.5, "lat_min": 10.0, "lat_max": 11.5},
    "Atlantico": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 10.5, "lat_max": 11.0},
    "Bolivar": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 9.5, "lat_max": 10.5},
    "Sucre": {"lon_min": -75.5, "lon_max": -74.5, "lat_min": 9.0, "lat_max": 10.0},
    "Cordoba": {"lon_min": -76.5, "lon_max": -75.5, "lat_min": 8.5, "lat_max": 9.5},
    # Caribe Insular
    "San Andres y Providencia": {"lon_min": -82.0, "lon_max": -81.0, "lat_min": 12.2, "lat_max": 14.0},
    "Archipielago de San Bernardo": {"lon_min": -75.8, "lon_max": -75.5, "lat_min": 9.7, "lat_max": 10.0},
}

# Seleccionar subregiones y calcular energía de olas
wave_energy_dict = {}
for region, coords in regions.items():
    subset = ds_waves.sel(
        longitude=slice(coords["lon_min"], coords["lon_max"]),
        latitude=slice(coords["lat_min"], coords["lat_max"])
    )
    subset = subset.fillna(0)
    wave_energy = 0.5 * subset['VHM0']**2 * subset['VTM10']
    wave_energy_dict[region] = wave_energy.to_dataframe(name='energy').reset_index()

# Cargar datos de ballenas (puntos y trayectorias)
try:
    whale_points = pd.read_csv('data/raw/whale_sightings_1035_points.csv')
    whale_lines = pd.read_csv('data/raw/whale_sightings_1035_lines.csv')
    logger.info("Datos de ballenas (puntos y trayectorias) cargados correctamente.")
except Exception as e:
    logger.error(f"Error al cargar datos de ballenas: {e}")
    sys.exit(1)

# Combinar puntos y trayectorias usando dataset_id y fechas
whale_points['date'] = pd.to_datetime(whale_points['date'], errors='coerce')
whale_lines['date'] = pd.to_datetime(whale_lines['date'], errors='coerce')
whale_data = pd.merge(
    whale_points,
    whale_lines,
    on=['dataset_id', 'date'],
    how='left',
    suffixes=('_point', '_line')
)
whale_data = whale_data.dropna(subset=['date'])
whale_data['month'] = whale_data['date'].dt.month
whale_data['year'] = whale_data['date'].dt.year

# Filtrar datos de ballenas por región
whale_regions = {}
for region, coords in regions.items():
    whale_subset = whale_data[
        (whale_data['longitude_point'] >= coords["lon_min"]) & (whale_data['longitude_point'] <= coords["lon_max"]) &
        (whale_data['latitude_point'] >= coords["lat_min"]) & (whale_data['latitude_point'] <= coords["lat_max"])
    ]
    whale_regions[region] = whale_subset

# Cargar datos meteorológicos
try:
    meteo_data = pd.read_csv('data/raw/meteorological_data.csv')
    logger.info("Datos meteorológicos cargados correctamente.")
except Exception as e:
    logger.error(f"Error al cargar datos meteorológicos: {e}")
    sys.exit(1)

# Filtrar datos meteorológicos por región y correlacionar con avistamientos
meteo_regions = {}
for region, coords in regions.items():
    meteo_subset = meteo_data[
        (meteo_data['Latitud'] >= coords["lat_min"]) & (meteo_data['Latitud'] <= coords["lat_max"]) &
        (meteo_data['Longitud'] >= coords["lon_min"]) & (meteo_data['Longitud'] <= coords["lon_max"])
    ]
    meteo_subset['Fecha'] = pd.to_datetime(meteo_subset['Fecha'])
    meteo_regions[region] = meteo_subset

# Correlacionar datos meteorológicos con avistamientos de ballenas
for region, whale_subset in whale_regions.items():
    meteo_subset = meteo_regions.get(region, pd.DataFrame())
    if not meteo_subset.empty and not whale_subset.empty:
        whale_subset = whale_subset.merge(
            meteo_subset[['Fecha', 'VelocidadViento', 'Temperatura']],
            left_on='date',
            right_on='Fecha',
            how='left'
        )
        whale_regions[region] = whale_subset