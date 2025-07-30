% Conectar a Supabase
run('connect_to_supabase.m');

% Lista de regiones
regions = {'choco', 'valle_del_cauca', 'cauca', 'narino', ...
           'la_guajira', 'magdalena', 'atlantico', 'bolivar', 'sucre', 'cordoba', ...
           'san_andres_y_providencia', 'archipielago_de_san_bernardo'};

imgDir = fullfile('src','webapp','static','img');
if ~exist(imgDir,'dir')
    mkdir(imgDir);
    disp(['📁 Directorio creado: ', imgDir]);
end

% Generar mapas por región y mes
for i = 1:length(regions)
    region = regions{i};
    
    % Consultar datos de avistamientos de ballenas
    query = sprintf('SELECT latitude, longitude, month FROM whale_sightings WHERE region = ''%s''', region);
    data = fetch(conn, query);
    
    % Extraer datos
    lat = data.latitude;
    lon = data.longitude;
    month = data.month;
    
    % Crear figura
    fig = figure('Visible','off');
    geoscatter(lat, lon, 20, months, 'filled');
    geobasemap('satellite');
    colorbar;
    title(sprintf('Avistamientos de Ballenas por Mes – %s', ...
        strrep(region,'_',' ')));
    %xlabel('Longitud');
    %ylabel('Latitud');
    
    % Guardar figura
    saveas(gcf, sprintf('src/webapp/static/img/whale_sightings_map_%s.png', region));
    disp(['Mapa de avistamientos de ballenas generado para ', region]);
endoutFile = fullfile(imgDir, ...
        sprintf('whale_sightings_map_%s.png', region));
    saveas(fig, outFile);
    close(fig);

    disp(['🐋 Mapa de avistamientos guardado para ', region]);
end