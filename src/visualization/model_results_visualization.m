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

% Visualizar curvas de aprendizaje del LSTM por región
for i = 1:length(regions)
    region = regions{i};
    
    % Cargar datos del modelo LSTM (simulamos que los datos de pérdida están disponibles)
    % En un caso real, estos datos se cargarían desde un archivo o base de datos
    epochs   = (1:50)';
    loss     = 1 ./ (1 + exp(-(epochs-25)/5));
    val_loss = loss * 1.2;

    % 4.2 Gráfico oculto
    fig = figure('Visible','off');
    plot(epochs, loss,   '-o', 'DisplayName','Pérdida Entrenamiento');
    hold on;
    plot(epochs, val_loss,'-s','DisplayName','Pérdida Validación');
    title(sprintf('Curva de Aprendizaje LSTM – %s', strrep(region,'_',' ')));
    xlabel('Época');
    ylabel('Pérdida (MSE)');
    legend('Location','northeast');
    grid on;

    % 4.3 Guardar y cerrar
    outFile = fullfile(imgDir, sprintf('lstm_learning_curve_%s.png', region));
    saveas(fig, outFile);
    close(fig);
    disp(['📈 LSTM curve guardada para ', region]);
end

%% 5. Mapas Reales vs Sintéticos VAE
for i = 1:numel(regions)
    region = regions{i};

    % 5.1 Traer datos reales
    query_real = sprintf( ...
      "SELECT latitude, longitude FROM whale_sightings WHERE region = '%s'", ...
      region);
    data_real = fetch(conn, query_real);
    lat_real  = data_real.latitude;
    lon_real  = data_real.longitude;

    % 5.2 Simular datos sintéticos (reemplaza con tus salidas VAE)
    lat_syn = lat_real + randn(size(lat_real)) * 0.05;
    lon_syn = lon_real + randn(size(lon_real)) * 0.05;

    % 5.3 Crear figura oculta
    fig = figure('Visible','off');
    geoscatter(lat_real, lon_real, 20, 'b', 'filled', 'DisplayName','Reales');
    hold on;
    geoscatter(lat_syn, lon_syn, 20, 'r', 'filled', 'DisplayName','Sintéticos');
    geobasemap('satellite');
    title(sprintf('Reales vs Sintéticos – %s', strrep(region,'_',' ')));
    legend('Location','best');

    % 5.4 Guardar y cerrar
    outFile = fullfile(imgDir, sprintf('vae_synthetic_map_%s.png', region));
    saveas(fig, outFile);
    close(fig);
    disp(['🗺️ VAE map guardado para ', region]);
end