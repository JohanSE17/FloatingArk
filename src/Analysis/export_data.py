# Exportar datos de energía de olas por región
for region, df in wave_energy_dict.items():
    df.to_csv(f'data/processed/wave_energy_{region.replace(" ", "_").lower()}.csv', index=False)
    sio.savemat(f'data/processed/wave_energy_{region.replace(" ", "_").lower()}.mat', {
        'energy': df['energy'].values,
        'latitude': df['latitude'].values,
        'longitude': df['longitude'].values,
        'time': df['time'].astype(str).values
    })

# Exportar datos de avistamientos de ballenas por región
for region, df in whale_regions.items():
    df.to_csv(f'data/processed/whale_sightings_{region.replace(" ", "_").lower()}.csv', index=False)
    sio.savemat(f'data/processed/whale_sightings_{region.replace(" ", "_").lower()}.mat', {
        'latitude': df['latitude_point'].values,
        'longitude': df['longitude_point'].values,
        'month': df['month'].values,
        'year': df['year'].values
    })

logger.info("Datos exportados correctamente a CSV y .mat para todas las regiones.")