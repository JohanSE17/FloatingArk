% Conectar a Supabase
run('connect_to_supabase.m');

% Lista de regiones
regions = {'choco', 'valle_del_cauca', 'cauca', 'narino', ...
           'la_guajira', 'magdalena', 'atlantico', 'bolivar', 'sucre', 'cordoba', ...
           'san_andres_y_providencia', 'archipielago_de_san_bernardo'};

% Directorio donde se guardarán las imágenes
imgDir = fullfile('src','webapp','static','img');
if ~exist(imgDir, 'dir')
    mkdir(imgDir);
    disp(['📁 Directorio creado: ', imgDir]);
end

% Generar un mapa por región
for i = 1:length(regions)
    region = regions{i};
    
    % Consultar datos de energía de olas
    query = sprintf('SELECT latitude, longitude, energy FROM wave_energy WHERE region = ''%s''', region);
    data = fetch(conn, query);
    
    % Extraer datos
    lat = data.latitude;
    lon = data.longitude;
    energy = data.energy;
    
    % Crear figura
    figure;
    geoscatter(lat, lon, 20, energy, 'filled');
    geobasemap('satellite');
    colorbar;
    title(sprintf('Distribución de Energía de Olas - %s', strrep(region, '_', ' ')));
    %xlabel('Longitud');
    %ylabel('Latitud');
    
    % Guardar figura
    saveas(gcf, sprintf('src/webapp/static/img/wave_energy_map_%s.png', region));
    % Construir ruta completa y guardar
    outFile = fullfile(imgDir, sprintf('wave_energy_map_%s.png', region));
    saveas(gcf, outFile);
    disp(['Mapa de energía de olas generado para ', region]);
end