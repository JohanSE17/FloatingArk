% master_visualizations.m

% 1. Conecta a Supabase y guarda el objeto conn
conn = connect_to_supabase();

% 2. Ejecuta tus scripts de visualización
%run('wave_energy_maps.m');          % Mapas de energía de olas
%run('wave_energy_boxplots.m');      % Boxplots de energía
%run('whale_sightings_maps.m');      % Mapas de avistamientos
%run('meteorological_analysis.m');   % Análisis meteorológico
%run('model_results_visualization.m');% Resultados de modelos

% 3. Cierra la conexión al final
close(conn);
disp('🔒 Conexión a Supabase cerrada.');
