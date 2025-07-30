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

% Generar gráficos por región
for i = 1:length(regions)
    region = regions{i};
    
    % Consultar datos meteorológicos
    query = sprintf('SELECT fecha, velocidad_viento, temperatura FROM meteorological_data WHERE region = ''%s''', region);
    data = fetch(conn, query);
    
    % Extraer datos y calcular mes
        times = datetime(data.fecha, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    dv    = datevec(times);
    months = dv(:,2);
    
     wind_speed  = data.velocidad_viento;
    temperature = data.temperatura;

    % 4.3 Calcular promedio mensual
    wind_monthly = accumarray(months, wind_speed, [12,1], @mean, NaN);
    temp_monthly = accumarray(months, temperature, [12,1], @mean, NaN);
    m = (1:12)';

    % 4.4 Crear figura oculta
    fig = figure('Visible','off');
    
    % Viento
    subplot(2,1,1);
    plot(m, wind_monthly, '-o');
    title(sprintf('Velocidad Promedio del Viento – %s', strrep(region,'_',' ')));
    xlabel('Mes');
    ylabel('Velocidad (km/h)');
    xlim([1 12]);
    
    % Temperatura
    subplot(2,1,2);
    plot(m, temp_monthly, '-o');
    title(sprintf('Temperatura Promedio – %s', strrep(region,'_',' ')));
    xlabel('Mes');
    ylabel('Temperatura (°C)');
    xlim([1 12]);

    % 4.5 Guardar y cerrar
    outFile = fullfile(imgDir, sprintf('meteorological_analysis_%s.png', region));
    saveas(fig, outFile);
    close(fig);

    disp(['🌦️ Análisis meteorológico guardado para ', region]);
end
