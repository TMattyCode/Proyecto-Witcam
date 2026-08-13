USE WitcamBD;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

/*
   Datos de prueba para la pantalla "Ingresos identificados".

   El script utiliza la primera cuenta disponible. Luego crea, si no
   existen, un grupo y una camara exclusivos para estas pruebas.

   Si hay varias cuentas, asigna a @id_cuenta el ID de la cuenta con la
   que iniciaras sesion. El endpoint solo muestra datos de esa cuenta.

   Si no existe ninguna cuenta, el script crea una cuenta de prueba. Esa
   cuenta no tendra un usuario para iniciar sesion hasta que se registre
   uno desde la aplicacion.

   MuestraFacial no se llena porque actualmente las muestras se guardan
   en carpetas locales y esa tabla esta reservada para una etapa futura.
*/

DECLARE @id_cuenta INT = NULL;
DECLARE @id_grupo_camara INT;
DECLARE @id_camara INT;

DECLARE @personas_insertadas TABLE (
    id_persona INT NOT NULL,
    nombre_persona VARCHAR(150) NOT NULL,
    fecha_registro DATETIME NOT NULL
);

BEGIN TRY
    BEGIN TRANSACTION;

    IF @id_cuenta IS NULL
    BEGIN
        SELECT TOP (1)
            @id_cuenta = id_cuenta
        FROM Cuenta
        ORDER BY id_cuenta;
    END;

    IF @id_cuenta IS NULL
    BEGIN
        INSERT INTO Cuenta (
            nombre_cuenta,
            fecha_registro
        )
        VALUES (
            'Cuenta pruebas de ingresos',
            GETDATE()
        );

        SET @id_cuenta = CONVERT(INT, SCOPE_IDENTITY());
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM Cuenta
        WHERE id_cuenta = @id_cuenta
    )
    BEGIN
        THROW 50001, 'El ID indicado en @id_cuenta no existe.', 1;
    END;

    SELECT
        @id_grupo_camara = id_grupo_camara
    FROM GrupoCamara
    WHERE id_cuenta = @id_cuenta
      AND nombre_grupo = 'Grupo pruebas de ingresos';

    IF @id_grupo_camara IS NULL
    BEGIN
        INSERT INTO GrupoCamara (
            id_cuenta,
            nombre_grupo,
            descripcion,
            activo,
            fecha_creacion
        )
        VALUES (
            @id_cuenta,
            'Grupo pruebas de ingresos',
            'Grupo creado por ingreso_personas.sql',
            1,
            GETDATE()
        );

        SET @id_grupo_camara = CONVERT(INT, SCOPE_IDENTITY());
    END;

    SELECT
        @id_camara = id_camara
    FROM Camara
    WHERE id_grupo_camara = @id_grupo_camara
      AND nombre_camara = 'Camara pruebas de ingresos';

    IF @id_camara IS NULL
    BEGIN
        INSERT INTO Camara (
            id_grupo_camara,
            nombre_camara,
            tipo_fuente,
            fuente_video,
            indice_dispositivo,
            escena_simulada,
            activa,
            fecha_registro
        )
        VALUES (
            @id_grupo_camara,
            'Camara pruebas de ingresos',
            'simulada',
            NULL,
            NULL,
            'entrada',
            1,
            GETDATE()
        );

        SET @id_camara = CONVERT(INT, SCOPE_IDENTITY());
    END;

    INSERT INTO Persona (
        id_cuenta,
        nombre_persona,
        fecha_registro
    )
    OUTPUT
        inserted.id_persona,
        inserted.nombre_persona,
        inserted.fecha_registro
    INTO @personas_insertadas (
        id_persona,
        nombre_persona,
        fecha_registro
    )
    VALUES
        (@id_cuenta, 'Persona prueba 01', DATEADD(MINUTE, -190, GETDATE())),
        (@id_cuenta, 'Persona prueba 02', DATEADD(MINUTE, -180, GETDATE())),
        (@id_cuenta, 'Persona prueba 03', DATEADD(MINUTE, -170, GETDATE())),
        (@id_cuenta, 'Persona prueba 04', DATEADD(MINUTE, -160, GETDATE())),
        (@id_cuenta, 'Persona prueba 05', DATEADD(MINUTE, -150, GETDATE())),
        (@id_cuenta, 'Persona prueba 06', DATEADD(MINUTE, -140, GETDATE())),
        (@id_cuenta, 'Persona prueba 07', DATEADD(MINUTE, -130, GETDATE())),
        (@id_cuenta, 'Persona prueba 08', DATEADD(MINUTE, -120, GETDATE())),
        (@id_cuenta, 'Persona prueba 09', DATEADD(MINUTE, -110, GETDATE())),
        (@id_cuenta, 'Persona prueba 10', DATEADD(MINUTE, -100, GETDATE())),
        (@id_cuenta, 'Persona prueba 11', DATEADD(MINUTE, -90, GETDATE())),
        (@id_cuenta, 'Persona prueba 12', DATEADD(MINUTE, -80, GETDATE())),
        (@id_cuenta, 'Persona prueba 13', DATEADD(MINUTE, -70, GETDATE())),
        (@id_cuenta, 'Persona prueba 14', DATEADD(MINUTE, -60, GETDATE())),
        (@id_cuenta, 'Persona prueba 15', DATEADD(MINUTE, -50, GETDATE())),
        (@id_cuenta, 'Persona prueba 16', DATEADD(MINUTE, -40, GETDATE())),
        (@id_cuenta, 'Persona prueba 17', DATEADD(MINUTE, -30, GETDATE())),
        (@id_cuenta, 'Persona prueba 18', DATEADD(MINUTE, -20, GETDATE())),
        (@id_cuenta, 'Persona prueba 19', DATEADD(MINUTE, -10, GETDATE())),
        (@id_cuenta, 'Persona prueba 20', GETDATE());

    ;WITH personas_numeradas AS (
        SELECT
            id_persona,
            nombre_persona,
            fecha_registro,
            ROW_NUMBER() OVER (ORDER BY id_persona) AS numero
        FROM @personas_insertadas
    )
    INSERT INTO Deteccion (
        id_camara,
        id_persona,
        fecha_hora,
        ruta_imagen_detectada,
        resultado,
        similitud
    )
    SELECT
        @id_camara,
        id_persona,
        fecha_registro,
        CONCAT(
            'referencias_pendientes/persona_',
            id_persona,
            '/deteccion_prueba.jpg'
        ),
        'Identificado',
        CAST(0.70 + (numero * 0.01) AS DECIMAL(6,5))
    FROM personas_numeradas;

    INSERT INTO Deteccion (
        id_camara,
        id_persona,
        fecha_hora,
        ruta_imagen_detectada,
        resultado,
        similitud
    )
    SELECT
        @id_camara,
        pi.id_persona,
        DATEADD(MINUTE, repeticion.minutos_atras, GETDATE()),
        CONCAT(
            'referencias_pendientes/persona_',
            pi.id_persona,
            '/deteccion_prueba_anterior.jpg'
        ),
        'Identificado',
        repeticion.similitud
    FROM @personas_insertadas AS pi
    INNER JOIN (
        VALUES
            ('Persona prueba 01', -290, CAST(0.81 AS DECIMAL(6,5))),
            ('Persona prueba 02', -280, CAST(0.82 AS DECIMAL(6,5))),
            ('Persona prueba 03', -270, CAST(0.83 AS DECIMAL(6,5))),
            ('Persona prueba 04', -260, CAST(0.84 AS DECIMAL(6,5))),
            ('Persona prueba 05', -250, CAST(0.85 AS DECIMAL(6,5))),
            ('Persona prueba 19', -210, CAST(0.89 AS DECIMAL(6,5)))
    ) AS repeticion(nombre_persona, minutos_atras, similitud)
        ON repeticion.nombre_persona = pi.nombre_persona;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;

SELECT
    d.id_deteccion,
    p.id_persona,
    p.nombre_persona,
    c.nombre_camara,
    d.fecha_hora,
    d.resultado,
    d.similitud,
    d.ruta_imagen_detectada
FROM @personas_insertadas AS pi
INNER JOIN Persona AS p
    ON p.id_persona = pi.id_persona
INNER JOIN Deteccion AS d
    ON d.id_persona = p.id_persona
INNER JOIN Camara AS c
    ON c.id_camara = d.id_camara
ORDER BY d.fecha_hora DESC;
GO
