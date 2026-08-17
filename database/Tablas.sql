USE master;
GO

/* =========================================================
   RECREAR BASE DE DATOS
   ADVERTENCIA: este bloque elimina toda la información previa
   ========================================================= */

IF DB_ID('WitcamBD') IS NOT NULL
BEGIN
    ALTER DATABASE WitcamBD
    SET SINGLE_USER
    WITH ROLLBACK IMMEDIATE;

    DROP DATABASE WitcamBD;
END
GO

CREATE DATABASE WitcamBD;
GO

USE WitcamBD;
GO


/* =========================================================
   ROLES Y PERMISOS
   ========================================================= */

CREATE TABLE Rol (
    id_rol INT IDENTITY(1,1) PRIMARY KEY,
    nombre_rol NVARCHAR(100) NOT NULL UNIQUE,
    descripcion NVARCHAR(250) NULL
);
GO

INSERT INTO Rol (nombre_rol, descripcion)
VALUES
    (N'Administrador', N'Administrador principal de la cuenta'),
    (N'Subusuario', N'Usuario dependiente de una cuenta administradora');
GO


CREATE TABLE Permiso (
    id_permiso INT IDENTITY(1,1) PRIMARY KEY,

    codigo_permiso NVARCHAR(50) NOT NULL UNIQUE,
    nombre_permiso NVARCHAR(100) NOT NULL UNIQUE,
    descripcion NVARCHAR(250) NULL
);
GO

INSERT INTO Permiso (codigo_permiso, nombre_permiso, descripcion)
VALUES
    (N'ver', N'Ver', N'Permite visualizar información'),
    (N'anadir', N'Añadir', N'Permite añadir registros'),
    (N'editar', N'Editar', N'Permite modificar registros'),
    (N'eliminar', N'Eliminar', N'Permite eliminar o desactivar registros'),
    (N'configuracion', N'Configuración', N'Permite ingresar y realizar cambios en configuración');
GO


/* =========================================================
   CUENTA PRINCIPAL DEL CLIENTE
   ========================================================= */


CREATE TABLE Cuenta (
    id_cuenta INT IDENTITY(1,1) PRIMARY KEY,
    nombre_cuenta NVARCHAR(150) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE()

);
GO


/* =========================================================
   PLANES Y SUSCRIPCIONES
   ========================================================= */

CREATE TABLE PlanSuscripcion (
    id_plan INT IDENTITY(1,1) PRIMARY KEY,

    nombre_plan NVARCHAR(100) NOT NULL UNIQUE,
    descripcion NVARCHAR(500) NULL,

    precio_mensual INT NOT NULL,
    max_usuarios INT NOT NULL,
    max_camaras INT NOT NULL,
    dias_historial INT NULL,

    plan_activo BIT NOT NULL DEFAULT 1,

    CONSTRAINT CK_PlanSuscripcion_Precio
        CHECK (precio_mensual >= 0),

    CONSTRAINT CK_PlanSuscripcion_MaxUsuarios
        CHECK (max_usuarios > 0),

    CONSTRAINT CK_PlanSuscripcion_MaxCamaras
        CHECK (max_camaras > 0),

    CONSTRAINT CK_PlanSuscripcion_DiasHistorial
        CHECK (
            dias_historial IS NULL
            OR dias_historial >= 0
        )
);
GO


CREATE TABLE EstadoSuscripcion (
    id_estado_suscripcion INT IDENTITY(1,1) PRIMARY KEY,
    nombre_estado NVARCHAR(100) NOT NULL UNIQUE
);
GO

INSERT INTO EstadoSuscripcion (nombre_estado)
VALUES
    (N'Activa'),
    (N'Vencida'),
    (N'Cancelada'),
    (N'Suspendida');
GO


CREATE TABLE Suscripcion (
    id_suscripcion INT IDENTITY(1,1) PRIMARY KEY,

    id_cuenta INT NOT NULL,
    id_plan INT NOT NULL,
    id_estado_suscripcion INT NOT NULL DEFAULT 1,

    fecha_inicio DATETIME NOT NULL,
    fecha_vencimiento DATETIME NOT NULL,

    renovacion_automatica BIT NOT NULL DEFAULT 1,

    fecha_cancelacion DATETIME NULL,

    CONSTRAINT FK_Suscripcion_Cuenta
        FOREIGN KEY (id_cuenta)
        REFERENCES Cuenta(id_cuenta),

    CONSTRAINT FK_Suscripcion_Plan
        FOREIGN KEY (id_plan)
        REFERENCES PlanSuscripcion(id_plan),

    CONSTRAINT FK_Suscripcion_Estado
        FOREIGN KEY (id_estado_suscripcion)
        REFERENCES EstadoSuscripcion(id_estado_suscripcion),

    CONSTRAINT CK_Suscripcion_Fechas
        CHECK (fecha_vencimiento >= fecha_inicio),

    CONSTRAINT CK_Suscripcion_FechaCancelacion
        CHECK (
            fecha_cancelacion IS NULL
            OR fecha_cancelacion >= fecha_inicio
        )
);
GO


/* =========================================================
   USUARIOS
   ========================================================= */

CREATE TABLE EstadoUsuario (
    id_estado_usuario INT IDENTITY(1,1) PRIMARY KEY,
    nombre_estado NVARCHAR(100) NOT NULL UNIQUE
);
GO

INSERT INTO EstadoUsuario (nombre_estado)
VALUES
    (N'Activo'),
    (N'Inactivo');
GO


CREATE TABLE Usuario (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,

    id_cuenta INT NOT NULL,
    id_rol INT NOT NULL,

    nombre NVARCHAR(100) NOT NULL,
    apellido NVARCHAR(100) NOT NULL,

    nombre_usuario NVARCHAR(100) NOT NULL,
    correo NVARCHAR(250) NOT NULL,

    telefono NVARCHAR(20) NULL,

    password_hash NVARCHAR(255) NOT NULL,

    id_estado_usuario INT NOT NULL DEFAULT 1,

    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    ultimo_acceso DATETIME NULL,

    CONSTRAINT FK_Usuario_Cuenta
        FOREIGN KEY (id_cuenta)
        REFERENCES Cuenta(id_cuenta),

    CONSTRAINT FK_Usuario_Rol
        FOREIGN KEY (id_rol)
        REFERENCES Rol(id_rol),

    CONSTRAINT FK_Usuario_EstadoUsuario
        FOREIGN KEY (id_estado_usuario)
        REFERENCES EstadoUsuario(id_estado_usuario)
);
GO

/* =========================================================
   PERMISOS INDIVIDUALES DE USUARIOS
   Se utiliza principalmente para subusuarios.
   El administrador tiene acceso completo por su rol.
   ========================================================= */

CREATE TABLE Usuario_Permiso (
    id_usuario_permiso INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario INT NOT NULL,
    id_permiso INT NOT NULL,

    permitido BIT NOT NULL DEFAULT 0,

    fecha_asignacion DATETIME NOT NULL DEFAULT GETDATE(),
    fecha_actualizacion DATETIME NULL,

    CONSTRAINT FK_UsuarioPermiso_Usuario
        FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario),

    CONSTRAINT FK_UsuarioPermiso_Permiso
        FOREIGN KEY (id_permiso)
        REFERENCES Permiso(id_permiso),

    CONSTRAINT UQ_UsuarioPermiso
        UNIQUE (id_usuario, id_permiso)
);
GO


/* =========================================================
   GRUPOS DE CÁMARAS
   Cada grupo pertenece exclusivamente a una cuenta.
   El nombre puede repetirse entre cuentas distintas.
   ========================================================= */

CREATE TABLE GrupoCamara (
    id_grupo_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_cuenta INT NOT NULL,

    nombre_grupo NVARCHAR(150) NOT NULL,
    descripcion NVARCHAR(250) NULL,

    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_GrupoCamara_Cuenta
        FOREIGN KEY (id_cuenta)
        REFERENCES Cuenta(id_cuenta)
);
GO


/* =========================================================
   GRUPOS AUTORIZADOS PARA CADA SUBUSUARIO
   ========================================================= */

CREATE TABLE Usuario_GrupoCamara (
    id_usuario_grupo_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario INT NOT NULL,
    id_grupo_camara INT NOT NULL,

    fecha_asignacion DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_UsuarioGrupoCamara_Usuario
        FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario),

    CONSTRAINT FK_UsuarioGrupoCamara_GrupoCamara
        FOREIGN KEY (id_grupo_camara)
        REFERENCES GrupoCamara(id_grupo_camara),

    CONSTRAINT UQ_UsuarioGrupoCamara
        UNIQUE (id_usuario, id_grupo_camara)
);
GO


/* =========================================================
   CÁMARAS
   Datos necesarios para registrar cámaras ONVIF.
   El estado conectado/desconectado se determina en tiempo real.
   ========================================================= */

CREATE TABLE Camara (
    id_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_grupo_camara INT NOT NULL,

    nombre_camara NVARCHAR(150) NOT NULL,

    tipo_fuente NVARCHAR(20) NOT NULL,

    direccion_ip NVARCHAR(255) NULL,

    puerto_onvif INT NULL,

    usuario_conexion NVARCHAR(150) NULL,

    password_conexion_cifrada VARBINARY(512) NULL,

    indice_dispositivo INT NULL,

    escena_simulada NVARCHAR(30) NULL,

    /*
       Esta dirección puede obtenerse posteriormente
       mediante ONVIF y utilizarse para abrir el stream.
    */
    fuente_video NVARCHAR(1000) NULL,

    activa BIT NOT NULL DEFAULT 1,

    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Camara_GrupoCamara
        FOREIGN KEY (id_grupo_camara)
        REFERENCES GrupoCamara(id_grupo_camara),

    CONSTRAINT CK_Camara_PuertoONVIF
        CHECK (
            puerto_onvif IS NULL
            OR puerto_onvif BETWEEN 1 AND 65535
        ),

    CONSTRAINT CK_Camara_TipoFuente
        CHECK (tipo_fuente IN (N'webcam', N'onvif', N'rtsp', N'simulada')),

    CONSTRAINT CK_Camara_DatosTipo
        CHECK (
            (
                tipo_fuente = N'webcam'
                AND indice_dispositivo IS NOT NULL
                AND direccion_ip IS NULL
                AND puerto_onvif IS NULL
                AND usuario_conexion IS NULL
                AND password_conexion_cifrada IS NULL
                AND escena_simulada IS NULL
                AND fuente_video IS NULL
            )
            OR (
                tipo_fuente = N'onvif'
                AND direccion_ip IS NOT NULL
                AND puerto_onvif IS NOT NULL
                AND usuario_conexion IS NOT NULL
                AND password_conexion_cifrada IS NOT NULL
                AND indice_dispositivo IS NULL
                AND escena_simulada IS NULL
            )
            OR (
                tipo_fuente = N'rtsp'
                AND fuente_video IS NOT NULL
                AND LTRIM(RTRIM(fuente_video)) <> N''
                AND direccion_ip IS NULL
                AND puerto_onvif IS NULL
                AND usuario_conexion IS NULL
                AND password_conexion_cifrada IS NULL
                AND indice_dispositivo IS NULL
                AND escena_simulada IS NULL
            )
            OR (
                tipo_fuente = N'simulada'
                AND escena_simulada IS NOT NULL
                AND direccion_ip IS NULL
                AND puerto_onvif IS NULL
                AND usuario_conexion IS NULL
                AND password_conexion_cifrada IS NULL
                AND indice_dispositivo IS NULL
                AND fuente_video IS NULL
            )
        )
);
GO


/* =========================================================
   PERSONAS IDENTIFICADAS POR EL SISTEMA
   id_persona es el identificador estable de la persona.
   También se utiliza para nombrar su carpeta local.
   Ejemplo: persona_15
   ========================================================= */

CREATE TABLE Persona (
    id_persona INT IDENTITY(1,1) PRIMARY KEY,

    id_cuenta INT NOT NULL,

    nombre_persona NVARCHAR(150) NOT NULL,

    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Persona_Cuenta
        FOREIGN KEY (id_cuenta)
        REFERENCES Cuenta(id_cuenta)
);
GO


/* =========================================================
   MUESTRAS FACIALES DE PERSONAS
   Tabla reservada para una etapa futura.
   Actualmente las muestras se conservan en carpetas locales
   y no es necesario registrar filas en esta tabla.
   ========================================================= */

CREATE TABLE MuestraFacial (
    id_muestra_facial INT IDENTITY(1,1) PRIMARY KEY,

    id_persona INT NOT NULL,

    /*
       Ruta relativa del archivo local o del almacenamiento externo.
       Ejemplo local:
       personas/persona_15/rostro_003.jpg
    */
    ruta_archivo NVARCHAR(500) NOT NULL,

    calidad DECIMAL(5,4) NULL,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_MuestraFacial_Persona
        FOREIGN KEY (id_persona)
        REFERENCES Persona(id_persona),

    CONSTRAINT UQ_MuestraFacial_RutaArchivo
        UNIQUE (ruta_archivo),

    CONSTRAINT CK_MuestraFacial_Calidad
        CHECK (
            calidad IS NULL
            OR calidad BETWEEN 0 AND 1
        )
);
GO


/* =========================================================
   DETECCIONES
   Alimenta:
   - Historial de detecciones
   - Ingresos identificados
   - Tarjeta de personas detectadas
   ========================================================= */

CREATE TABLE Deteccion (
    id_deteccion INT IDENTITY(1,1) PRIMARY KEY,

    id_camara INT NOT NULL,
    id_persona INT NULL,

    fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),

    ruta_imagen_detectada NVARCHAR(500) NULL,

    resultado NVARCHAR(100) NOT NULL,

    /*
       Similitud facial en la escala nativa de la IA: 0 a 1.
       El frontend puede multiplicarla por 100 para mostrar porcentaje.
    */
    similitud DECIMAL(6,5) NULL,

    CONSTRAINT FK_Deteccion_Camara
        FOREIGN KEY (id_camara)
        REFERENCES Camara(id_camara),

    CONSTRAINT FK_Deteccion_Persona
        FOREIGN KEY (id_persona)
        REFERENCES Persona(id_persona),

    CONSTRAINT CK_Deteccion_Similitud
        CHECK (
            similitud IS NULL
            OR similitud BETWEEN 0 AND 1
        )
);
GO


/* =========================================================
   LISTA DE OBSERVACIÓN
   ========================================================= */

CREATE TABLE ListaObservacion (
    id_lista_observacion INT IDENTITY(1,1) PRIMARY KEY,

    id_persona INT NOT NULL,

    /*
       Usuario administrador o subusuario que agregó a la persona.
    */
    id_usuario_registro INT NOT NULL,

    motivo NVARCHAR(500) NOT NULL,

    fecha_ingreso_lista DATETIME NOT NULL DEFAULT GETDATE(),

    activa BIT NOT NULL DEFAULT 1,

    CONSTRAINT FK_ListaObservacion_Persona
        FOREIGN KEY (id_persona)
        REFERENCES Persona(id_persona),

    CONSTRAINT FK_ListaObservacion_Usuario
        FOREIGN KEY (id_usuario_registro)
        REFERENCES Usuario(id_usuario),

    CONSTRAINT UQ_ListaObservacion_Persona
        UNIQUE (id_persona)
);
GO


/* =========================================================
   ALERTAS
   Se genera cuando una detección coincide con una persona
   activa en la lista de observación.
   ========================================================= */

CREATE TABLE Alerta (
    id_alerta INT IDENTITY(1,1) PRIMARY KEY,

    id_deteccion INT NOT NULL,
    id_lista_observacion INT NOT NULL,

    fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),

    atendida BIT NOT NULL DEFAULT 0,
    fecha_atencion DATETIME NULL,

    CONSTRAINT FK_Alerta_Deteccion
        FOREIGN KEY (id_deteccion)
        REFERENCES Deteccion(id_deteccion),

    CONSTRAINT FK_Alerta_ListaObservacion
        FOREIGN KEY (id_lista_observacion)
        REFERENCES ListaObservacion(id_lista_observacion),

    CONSTRAINT UQ_Alerta_Deteccion
        UNIQUE (id_deteccion)
);
GO


/* =========================================================
   ÍNDICES PARA CONSULTAS FRECUENTES
   ========================================================= */

CREATE INDEX IX_GrupoCamara_Cuenta
ON GrupoCamara(id_cuenta);
GO

CREATE UNIQUE INDEX UX_GrupoCamara_Cuenta_Nombre_Activo
ON GrupoCamara(id_cuenta, nombre_grupo)
WHERE activo = 1;
GO

CREATE INDEX IX_UsuarioGrupoCamara_Usuario
ON Usuario_GrupoCamara(id_usuario);
GO

CREATE INDEX IX_Camara_GrupoCamara
ON Camara(id_grupo_camara);
GO

CREATE UNIQUE INDEX UX_Camara_Grupo_Nombre_Activa
ON Camara(id_grupo_camara, nombre_camara)
WHERE activa = 1;
GO

CREATE INDEX IX_Persona_Cuenta_Nombre
ON Persona(id_cuenta, nombre_persona)
INCLUDE (fecha_registro);
GO

CREATE INDEX IX_MuestraFacial_Persona_Calidad
ON MuestraFacial(id_persona, calidad DESC);
GO

CREATE INDEX IX_Deteccion_Camara_Fecha
ON Deteccion(id_camara, fecha_hora DESC);
GO

CREATE INDEX IX_Deteccion_Persona_Fecha
ON Deteccion(id_persona, fecha_hora DESC);
GO

CREATE INDEX IX_Deteccion_Identificados_Fecha
ON Deteccion(fecha_hora DESC)
INCLUDE (
    id_camara,
    id_persona,
    resultado,
    similitud,
    ruta_imagen_detectada
)
WHERE id_persona IS NOT NULL;
GO

CREATE INDEX IX_ListaObservacion_Persona
ON ListaObservacion(id_persona);
GO

CREATE INDEX IX_Alerta_Fecha
ON Alerta(fecha_hora DESC);
GO

CREATE INDEX IX_Usuario_Cuenta_Estado_Fecha
ON Usuario(id_cuenta, id_estado_usuario, fecha_creacion DESC)
INCLUDE (id_rol, nombre_usuario, correo, ultimo_acceso);
GO

CREATE UNIQUE INDEX UX_Usuario_Nombre_Activo
ON Usuario(nombre_usuario)
WHERE id_estado_usuario = 1;
GO

CREATE UNIQUE INDEX UX_Usuario_Correo_Activo
ON Usuario(correo)
WHERE id_estado_usuario = 1;
GO

CREATE INDEX IX_Usuario_Cuenta_UltimoAcceso
ON Usuario(id_cuenta, ultimo_acceso)
INCLUDE (id_estado_usuario, id_rol, nombre_usuario);
GO

CREATE INDEX IX_UsuarioPermiso_Permiso_Usuario
ON Usuario_Permiso(id_permiso, id_usuario)
INCLUDE (permitido);
GO
