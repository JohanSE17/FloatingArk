function conn = connect_to_supabase()
    % Ruta fija al archivo JDBC
    jarPath = 'H:\Johan\MatLabs\java\jarext\postgresql-42.7.5.jar';

    % Verificar si el archivo .jar existe
    if exist(jarPath, 'file') ~= 2
        error('❌ No se encontró el archivo JDBC en la ruta especificada: %s', jarPath);
    end

    % Agregar el .jar al classpath dinámicamente
    javaaddpath(jarPath);
    disp(['✅ Driver JDBC agregado desde: ', jarPath]);

    % Datos de conexión (POOLER, compatible con IPv4)
    dbname = 'postgres';
    username = 'postgres.tscpomsatywbfbhvzpsu';
    password = 'Johan2001space117*';
    host = 'aws-0-us-east-2.pooler.supabase.com';
    port = '6543';

    % Crear la conexión
    conn = database(dbname, username, password, ...
        'Vendor', 'PostgreSQL', ...
        'Server', host, ...
        'PortNumber', str2double(port));

    % Verificar la conexión
    if isopen(conn)
        disp('✅ Conexión a Supabase exitosa.');
    else
        error('❌ No se pudo conectar a Supabase: %s', conn.Message);
    end

    % Asegurar el cierre automático al salir del contexto
    % cleanup = onCleanup(@() close(conn));
end
