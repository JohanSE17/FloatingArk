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

% Generar boxplots por región
for i = 1:length(regions)
    region = regions{i};
    
    % Consultar datos de energía de olas
    query = sprintf('SELECT time, energy FROM wave_energy WHERE region = ''%s''', region);
    data = fetch(conn, query);
    
    % Extraer datos y calcular mes
    %energy = data.energy;
    times   = datetime(data.time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    energies = data.energy;

    dv     = datevec(times);
    months = dv(:,2);

    % 4.4 Crear figura oculta y boxplot
    fig = figure('Visible','off');
    boxplot(energies, months);
    title(sprintf('Variabilidad Mensual de Energía de Olas – %s', ...
          strrep(region,'_',' ')));
    xlabel('Mes');
    ylabel('Energía (kW/m)');

    % 4.5 Guardar y cerrar
    outFile = fullfile(imgDir, ...
        sprintf('wave_energy_boxplot_%s.png', region));
    saveas(fig, outFile);
    close(fig);

    disp(['📊 Boxplot generado y guardado para ', region]);
end