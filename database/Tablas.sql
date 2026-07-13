create database WitcamBD
go
use WitcamBD
go

create table Rol (
	id_rol int identity(1,1) primary key,
	nombre_rol varchar(100) not null unique,
	descripcion varchar(250)
)
insert into Rol (nombre_rol) values ('Administrador')

create table Permiso (
	id_permiso int identity(1,1) primary key,
	nombre_permiso varchar(100) not null unique,
	descripcion varchar(250)
)

create table Rol_Permiso (
	id_rol_permiso int identity(1,1) primary key,
	id_rol int not null foreign key references Rol(id_rol),
	id_permiso int not null foreign key references Permiso(id_permiso)
)

create table Estado_Servicio (
	id_estado_servicio int identity(1,1) primary key,
	nombre_estado varchar(100) not null unique
)
insert into Estado_Servicio (nombre_estado) values ('Activo')
insert into Estado_Servicio (nombre_estado) values ('Inactivo')

create table Empresa (
	id_empresa int identity(1,1) primary key,
	nombre_empresa varchar(150) not null,
	rut_empresa varchar(20) not null unique,
	telefono_contacto varchar(20) not null,
	correo_contacto varchar(150) not null,
	estado_servicio int not null default 1 foreign key references Estado_Servicio(id_estado_servicio),
	fecha_registro datetime not null default getdate()
)

create table Estado_Plan (
	id_estado_plan int identity(1,1) primary key,
	nombre_estado varchar(100) not null unique
)
insert into Estado_Plan (nombre_estado) values ('Activo')
insert into Estado_Plan (nombre_estado) values ('Inactivo')

create table Plan_Suscripcion (
	id_plan int identity(1,1) primary key,
	nombre_plan varchar(100) not null unique,
	descripcion varchar(500),
	precio_mensual int not null,
	max_usuarios int not null,
	max_camaras int not null,
	dias_historial int,
	estado_plan int not null default 1 foreign key references Estado_Plan(id_estado_plan)
)

create table Estado_Suscripcion (
	id_estado_suscripcion int identity(1,1) primary key,
	nombre_estado varchar(100) not null unique
)
insert into Estado_Suscripcion (nombre_estado) values ('Activa')
insert into Estado_Suscripcion (nombre_estado) values ('Inactiva')

create table Suscripcion (
	id_suscripcion int identity(1,1) primary key,
	id_empresa int not null foreign key references Empresa(id_empresa),
	id_plan int not null foreign key references Plan_Suscripcion(id_plan),
	fecha_inicio datetime not null,
	fecha_vencimiento datetime not null,
	renovacion_automatica bit not null default 1,
	estado_suscripcion int not null default 1 foreign key references Estado_Suscripcion(id_estado_suscripcion),
	fecha_cancelacion datetime
)

create table Estado_Local (
	id_estado_local int identity(1,1) primary key,
	nombre_estado varchar(100) not null unique
)
insert into Estado_Local (nombre_estado) values ('Activo')
insert into Estado_Local (nombre_estado) values ('Inactivo')

create table Local (
	id_local int identity(1,1) primary key,
	id_empresa int not null foreign key references Empresa(id_empresa),
	nombre_local varchar(150) not null,
	direccion varchar(250) not null,
	comuna varchar(100) not null,
	telefono varchar(20) not null,
	horario_apertura time,
	horario_cierre time,
	estado_local int not null default 1 foreign key references Estado_Local(id_estado_local)
)

create table Estado_Usuario (
	id_estado_usuario int identity(1,1) primary key,
	nombre_estado varchar(100) not null unique
)
insert into Estado_Usuario (nombre_estado) values ('Activo')
insert into Estado_Usuario (nombre_estado) values ('Inactivo')

create table Usuario (
	id_usuario int identity(1,1) primary key,
	id_empresa int not null foreign key references Empresa(id_empresa),
	id_local int not null foreign key references Local(id_local),
	id_rol int not null foreign key references Rol(id_rol),
	nombre varchar(100) not null,
	apellido varchar(100) not null,
	nombre_usuario varchar(100) not null unique,
	correo varchar(250) not null unique,
	password_hash varchar(255) not null,
	estado_usuario int not null default 1 foreign key references Estado_Usuario(id_estado_usuario),
	fecha_creacion datetime not null default getdate(),
	ultimo_acceso datetime
)