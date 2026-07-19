# Witcam - Frontend React

Interfaz web de Witcam desarrollada con React y Vite. Esta carpeta contiene las pantallas de inicio de sesion, registro, resumen del sistema, camaras, ingresos identificados, lista de observacion y configuracion.

## Estado actual

La navegacion entre pantallas se administra mediante `NavegacionContext`. La interfaz todavia no esta conectada a la API del backend Python ni a SQL Server, por lo que algunos datos y acciones son demostrativos.

El backend se encuentra en `../app.py` y actualmente escucha en `http://localhost:8000`. Durante el desarrollo, Vite sirve esta interfaz normalmente desde `http://localhost:5173`.

## Requisitos

- Node.js compatible con Vite 8.
- npm.

## Instalacion

Desde esta carpeta:

```powershell
npm install
```

La carpeta `node_modules/` no se guarda en Git y se genera localmente con este comando.

## Ejecucion

```powershell
npm run dev
```

Abre la direccion que muestre Vite, normalmente:

```text
http://localhost:5173/
```

## Comandos disponibles

```powershell
npm run dev
npm run lint
npm run build
npm run preview
```

## Estructura principal

```text
src/
  assets/       Imagenes, logos e iconos
  componentes/  Componentes reutilizables y layout
  contextos/    Estado de navegacion compartido
  paginas/      Pantallas principales de la aplicacion
  App.jsx       Seleccion y navegacion de paginas
  main.jsx      Punto de entrada de React
public/         Archivos publicos
```

## Integracion pendiente

Para conectar este frontend con Witcam se debera configurar un proxy de Vite o CORS y reemplazar los datos demostrativos por solicitudes a los endpoints de `app.py`. El video procesado se obtiene actualmente desde `/video_feed`, mientras que el estado y las operaciones se exponen mediante rutas bajo `/api/`.

Consulta el `README.md` de la raiz del repositorio para la instalacion completa del backend Python, la IA y la base de datos.
