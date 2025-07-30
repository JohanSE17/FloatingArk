# Histogramas de energía de olas por región
for region, subset in wave_energy_dict.items():
    plt.figure(figsize=(10, 6))
    sns.histplot(subset['energy'], bins=30, kde=True)
    plt.title(f'Distribución de la Energía de Olas - {region}')
    plt.xlabel('Energía (kW/m)')
    plt.ylabel('Frecuencia')
    plt.savefig(f'data/processed/wave_energy_histogram_{region.replace(" ", "_").lower()}.png')
    logger.info(f"Histograma de energía de olas ({region}) generado.")

# Avistamientos de ballenas por mes y región
for region, whale_subset in whale_regions.items():
    whale_monthly = whale_subset['month'].value_counts().sort_index()
    plt.figure(figsize=(10, 6))
    whale_monthly.plot(kind='bar')
    plt.title(f'Avistamientos de Ballenas por Mes - {region}')
    plt.xlabel('Mes')
    plt.ylabel('Número de Avistamientos')
    plt.savefig(f'data/processed/whale_sightings_bar_{region.replace(" ", "_").lower()}.png')
    logger.info(f"Gráfico de avistamientos de ballenas por mes ({region}) generado.")

# Correlación entre velocidad del viento y avistamientos
for region, whale_subset in whale_regions.items():
    if 'VelocidadViento' in whale_subset.columns:
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x=whale_subset['VelocidadViento'], y=whale_subset['month'], size=whale_subset['month'])
        plt.title(f'Correlación entre Velocidad del Viento y Avistamientos - {region}')
        plt.xlabel('Velocidad del Viento (km/h)')
        plt.ylabel('Mes')
        plt.savefig(f'data/processed/wind_whale_correlation_{region.replace(" ", "_").lower()}.png')
        logger.info(f"Gráfico de correlación viento-avistamientos ({region}) generado.")

# Análisis estacional de viento por región
for region, meteo_subset in meteo_regions.items():
    if not meteo_subset.empty:
        meteo_subset['Mes'] = meteo_subset['Fecha'].dt.month
        wind_monthly = meteo_subset.groupby('Mes')['VelocidadViento'].mean()
        plt.figure(figsize=(10, 6))
        wind_monthly.plot(kind='line')
        plt.title(f'Velocidad Promedio del Viento por Mes - {region}')
        plt.xlabel('Mes')
        plt.ylabel('Velocidad (km/h)')
        plt.savefig(f'data/processed/wind_monthly_{region.replace(" ", "_").lower()}.png')
        logger.info(f"Gráfico de velocidad del viento ({region}) generado.")