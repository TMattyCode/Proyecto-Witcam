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
    nombre_rol VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(250) NULL
);
GO

INSERT INTO Rol (nombre_rol, descripcion)
VALUES
    ('Administrador', 'Administrador principal de la cuenta'),
    ('Subusuario', 'Usuario dependiente de una cuenta administradora');
GO


CREATE TABLE Permiso (
    id_permiso INT IDENTITY(1,1) PRIMARY KEY,

    codigo_permiso VARCHAR(50) NOT NULL UNIQUE,
    nombre_permiso VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(250) NULL
);
GO

INSERT INTO Permiso (codigo_permiso, nombre_permiso, descripcion)
VALUES
    ('ver', 'Ver', 'Permite visualizar información'),
    ('anadir', 'Añadir', 'Permite añadir registros'),
    ('editar', 'Editar', 'Permite modificar registros'),
    ('eliminar', 'Eliminar', 'Permite eliminar o desactivar registros'),
    ('configuracion', 'Configuración', 'Permite ingresar y realizar cambios en configuración');
GO


/* =========================================================
   CUENTA PRINCIPAL O USUARIO_GRUPO
   ========================================================= */


CREATE TABLE Usuario_grupo (
    id_usuario_grupo INT IDENTITY(1,1) PRIMARY KEY,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE()

);
GO


/* =========================================================
   PLANES Y SUSCRIPCIONES
   ========================================================= */

CREATE TABLE Plan_Suscripcion (
    id_plan INT IDENTITY(1,1) PRIMARY KEY,

    nombre_plan VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(500) NULL,

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


CREATE TABLE Estado_Suscripcion (
    id_estado_suscripcion INT IDENTITY(1,1) PRIMARY KEY,
    nombre_estado VARCHAR(100) NOT NULL UNIQUE
);
GO

INSERT INTO Estado_Suscripcion (nombre_estado)
VALUES
    ('Activa'),
    ('Vencida'),
    ('Cancelada'),
    ('Suspendida');
GO


CREATE TABLE Suscripcion (
    id_suscripcion INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario_grupo INT NOT NULL,
    id_plan INT NOT NULL,
    id_estado_suscripcion INT NOT NULL DEFAULT 1,

    fecha_inicio DATETIME NOT NULL,
    fecha_vencimiento DATETIME NOT NULL,

    renovacion_automatica BIT NOT NULL DEFAULT 1,

    fecha_cancelacion DATETIME NULL,

    CONSTRAINT FK_Suscripcion_UsuarioGrupo
        FOREIGN KEY (id_usuario_grupo)
        REFERENCES Usuario_grupo(id_usuario_grupo),

    CONSTRAINT FK_Suscripcion_Plan
        FOREIGN KEY (id_plan)
        REFERENCES Plan_Suscripcion(id_plan),

    CONSTRAINT FK_Suscripcion_Estado
        FOREIGN KEY (id_estado_suscripcion)
        REFERENCES Estado_Suscripcion(id_estado_suscripcion),

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

CREATE TABLE Estado_Usuario (
    id_estado_usuario INT IDENTITY(1,1) PRIMARY KEY,
    nombre_estado VARCHAR(100) NOT NULL UNIQUE
);
GO

INSERT INTO Estado_Usuario (nombre_estado)
VALUES
    ('Activo'),
    ('Inactivo');
GO


CREATE TABLE Usuario (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario_grupo INT NOT NULL,
    id_rol INT NOT NULL,

    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,

    nombre_usuario VARCHAR(100) NOT NULL UNIQUE,
    correo VARCHAR(250) NOT NULL UNIQUE,

    telefono VARCHAR(20) NULL,

    password_hash VARCHAR(255) NOT NULL,

    estado_usuario INT NOT NULL DEFAULT 1,

    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    ultimo_acceso DATETIME NULL,

    CONSTRAINT FK_Usuario_UsuarioGrupo
        FOREIGN KEY (id_usuario_grupo)
        REFERENCES Usuario_grupo(id_usuario_grupo),

    CONSTRAINT FK_Usuario_Rol
        FOREIGN KEY (id_rol)
        REFERENCES Rol(id_rol),

    CONSTRAINT FK_Usuario_EstadoUsuario
        FOREIGN KEY (estado_usuario)
        REFERENCES Estado_Usuario(id_estado_usuario)
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
   Cada grupo pertenece exclusivamente a un Usuario_grupo.
   El nombre puede repetirse entre cuentas distintas.
   ========================================================= */

CREATE TABLE Grupo_Camara (
    id_grupo_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario_grupo INT NOT NULL,

    nombre_grupo VARCHAR(150) NOT NULL,
    descripcion VARCHAR(250) NULL,

    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_GrupoCamara_UsuarioGrupo
        FOREIGN KEY (id_usuario_grupo)
        REFERENCES Usuario_grupo(id_usuario_grupo),

    CONSTRAINT UQ_GrupoCamara_UsuarioGrupo_Nombre
        UNIQUE (id_usuario_grupo, nombre_grupo)
);
GO


/* =========================================================
   GRUPOS AUTORIZADOS PARA CADA SUBUSUARIO
   ========================================================= */

CREATE TABLE Usuario_Grupo_Camara (
    id_usuario_grupo_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario INT NOT NULL,
    id_grupo_camara INT NOT NULL,

    fecha_asignacion DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_UsuarioGrupoCamara_Usuario
        FOREIGN KEY (id_usuario)
        REFERENCES Usuario(id_usuario),

    CONSTRAINT FK_UsuarioGrupoCamara_GrupoCamara
        FOREIGN KEY (id_grupo_camara)
        REFERENCES Grupo_Camara(id_grupo_camara),

    CONSTRAINT UQ_UsuarioGrupoCamara
        UNIQUE (id_usuario, id_grupo_camara)
);
GO


/* =========================================================
   CÁMARAS
   No se guarda Conectada/Desconectada.
   Ese estado se calculará desde el backend.
   El campo activa es administrativo.
   ========================================================= */

CREATE TABLE Camara (
    id_camara INT IDENTITY(1,1) PRIMARY KEY,

    id_grupo_camara INT NOT NULL,

    nombre_camara VARCHAR(150) NOT NULL,

    direccion_ip VARCHAR(45) NOT NULL,
    puerto INT NOT NULL,

    usuario_conexion VARCHAR(150) NULL,
    password_conexion_hash VARCHAR(255) NULL,

    ruta_stream VARCHAR(500) NULL,
    protocolo VARCHAR(50) NOT NULL DEFAULT 'ONVIF',

    activa BIT NOT NULL DEFAULT 1,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Camara_GrupoCamara
        FOREIGN KEY (id_grupo_camara)
        REFERENCES Grupo_Camara(id_grupo_camara),

    CONSTRAINT UQ_Camara_Grupo_Nombre
        UNIQUE (id_grupo_camara, nombre_camara),

    CONSTRAINT CK_Camara_Puerto
        CHECK (puerto BETWEEN 1 AND 65535)
);
GO


/* =========================================================
   CLIENTES O PERSONAS IDENTIFICADAS
   El código se presenta en frontend como ID CLIENTE.
   Ejemplo: CLI-00001
   ========================================================= */

CREATE TABLE Cliente (
    id_cliente INT IDENTITY(1,1) PRIMARY KEY,

    id_usuario_grupo INT NOT NULL,

    codigo_cliente VARCHAR(50) NOT NULL,

    imagen_referencia VARCHAR(500) NULL,

    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Cliente_UsuarioGrupo
        FOREIGN KEY (id_usuario_grupo)
        REFERENCES Usuario_grupo(id_usuario_grupo),

    CONSTRAINT UQ_Cliente_UsuarioGrupo_Codigo
        UNIQUE (id_usuario_grupo, codigo_cliente)
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
    id_cliente INT NULL,

    fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),

    imagen_detectada VARCHAR(500) NULL,

    resultado VARCHAR(100) NOT NULL,

    porcentaje_coincidencia DECIMAL(5,2) NULL,

    CONSTRAINT FK_Deteccion_Camara
        FOREIGN KEY (id_camara)
        REFERENCES Camara(id_camara),

    CONSTRAINT FK_Deteccion_Cliente
        FOREIGN KEY (id_cliente)
        REFERENCES Cliente(id_cliente),

    CONSTRAINT CK_Deteccion_Coincidencia
        CHECK (
            porcentaje_coincidencia IS NULL
            OR porcentaje_coincidencia BETWEEN 0 AND 100
        )
);
GO


/* =========================================================
   LISTA DE OBSERVACIÓN
   ========================================================= */

CREATE TABLE Lista_Observacion (
    id_lista_observacion INT IDENTITY(1,1) PRIMARY KEY,

    id_cliente INT NOT NULL,

    /*
       Usuario administrador o subusuario que agregó al cliente.
    */
    id_usuario_registro INT NOT NULL,

    motivo VARCHAR(500) NOT NULL,

    fecha_incidente DATETIME NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),

    activa BIT NOT NULL DEFAULT 1,

    CONSTRAINT FK_ListaObservacion_Cliente
        FOREIGN KEY (id_cliente)
        REFERENCES Cliente(id_cliente),

    CONSTRAINT FK_ListaObservacion_Usuario
        FOREIGN KEY (id_usuario_registro)
        REFERENCES Usuario(id_usuario),

    CONSTRAINT UQ_ListaObservacion_Cliente
        UNIQUE (id_cliente)
);
GO


/* =========================================================
   ALERTAS
   Se genera cuando una detección coincide con un cliente
   activo en la lista de observación.
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
        REFERENCES Lista_Observacion(id_lista_observacion),

    CONSTRAINT UQ_Alerta_Deteccion
        UNIQUE (id_deteccion)
);
GO


/* =========================================================
   ÍNDICES PARA CONSULTAS FRECUENTES
   ========================================================= */

CREATE INDEX IX_GrupoCamara_UsuarioGrupo
ON Grupo_Camara(id_usuario_grupo);
GO

CREATE INDEX IX_UsuarioGrupoCamara_Usuario
ON Usuario_Grupo_Camara(id_usuario);
GO

CREATE INDEX IX_Camara_GrupoCamara
ON Camara(id_grupo_camara);
GO

CREATE INDEX IX_Cliente_UsuarioGrupo
ON Cliente(id_usuario_grupo);
GO

CREATE INDEX IX_Deteccion_Camara_Fecha
ON Deteccion(id_camara, fecha_hora DESC);
GO

CREATE INDEX IX_Deteccion_Cliente
ON Deteccion(id_cliente);
GO

CREATE INDEX IX_ListaObservacion_Cliente
ON Lista_Observacion(id_cliente);
GO

CREATE INDEX IX_Alerta_Fecha
ON Alerta(fecha_hora DESC);
GO