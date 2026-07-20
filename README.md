# Witcam - Reconocimiento facial y monitoreo de camaras

Witcam es una aplicacion de reconocimiento facial en tiempo real. Actualmente puede analizar una webcam local, detectar rostros con InsightFace/SCRFD, mantener IDs de seguimiento con ByteTrack y guardar capturas de personas desconocidas para revisarlas despues.

El repositorio tambien contiene la interfaz definitiva desarrollada con React y Vite, ademas del script inicial para la base de datos SQL Server. La integracion entre estos componentes sigue en desarrollo.

## Estado actual

- El backend de IA en `app.py` funciona con una fuente de video y expone una API HTTP local.
- La interfaz de prueba formada por `index.html`, `app.js` y `styles.css` esta conectada al backend Python.
- La interfaz React se encuentra en `witcam/` y contiene las pantallas de la aplicacion final, pero todavia no consume la API de `app.py`.
- El script `database/Tablas.sql` crea la base de datos inicial en SQL Server, pero todavia no esta conectado al backend.
- Actualmente el backend procesa una fuente configurable mediante `CAMARA`, que puede ser el indice de una webcam o una URL RTSP. La version final debera registrar una cantidad variable de camaras y canales de NVR.

## Arquitectura prevista

```text
Camaras IP (RTSP/ONVIF)
          |
          v
Backend Python (API + IA)
   |                 |
   v                 v
SQL Server      Frontend React
```

El NVR no es obligatorio para el reconocimiento. Python puede analizar directamente el stream secundario de cada camara IP. Un NVR podria incorporarse posteriormente si se necesita grabacion continua o reproduccion de video historico.

## Que usa

- `OpenCV`: lectura de webcam, procesamiento de frames, dibujo de cajas y generacion del video web.
- `InsightFace`: deteccion de rostros y generacion de embeddings faciales.
- `SCRFD`: detector facial usado internamente por InsightFace.
- `ByteTrack`: seguimiento de rostros para mantener un ID estable por persona.
- `NumPy`: calculo de similitud entre embeddings.
- `ThreadingHTTPServer`: servidor web local integrado en Python.
- `React`: interfaz de usuario final.
- `Vite`: servidor de desarrollo y compilacion del frontend React.
- `SQL Server`: base de datos prevista para usuarios, roles, permisos, empresas, locales y suscripciones.

## Estructura del repositorio

```text
app.py                         Backend, API local y motor de reconocimiento
requirements.txt              Dependencias de Python
index.html                    Interfaz de prueba conectada a Python
app.js
styles.css
witcam/                       Interfaz final React/Vite
database/Tablas.sql           Creacion inicial de la base de datos SQL Server
referencias_reconocimiento/   Rostros aprobados (se crea automaticamente)
referencias_pendientes/       Capturas por revisar (se crea automaticamente)
```

Dentro de `witcam/src/` se encuentran las paginas de inicio de sesion, registro, resumen del sistema, camaras, ingresos identificados, lista de observacion y configuracion. Los componentes compartidos, contextos, estilos e imagenes tambien se mantienen dentro de esa carpeta.

## Carpetas de reconocimiento

El programa crea automaticamente las carpetas necesarias si no existen.

```text
referencias_reconocimiento/
referencias_pendientes/
```

`referencias_reconocimiento/` contiene las imagenes oficiales que la app debe reconocer. Puedes poner ahi fotos tuyas o de otras personas autorizadas. El nombre del archivo se usa como nombre en pantalla, por ejemplo `matias.jpg` se mostrara como `matias`.

`referencias_pendientes/` contiene capturas generadas automaticamente cuando aparece una persona desconocida durante algunos segundos. Luego puedes revisar esas imagenes desde la interfaz y mover las que quieras aprobar a `referencias_reconocimiento/`.

## Primer uso

La primera vez puedes ejecutar la app aunque no exista ninguna imagen de referencia. Si `referencias_reconocimiento/` esta vacia, el programa avisa por consola y sigue funcionando.

Cuando detecte un rostro desconocido valido por varios segundos, guardara una captura en `referencias_pendientes/`. Despues puedes revisar esa captura en la pagina y pasarla a `referencias_reconocimiento/` si quieres que esa persona quede como reconocida.

## Requisitos

Esta aplicacion fue desarrollada y probada con `Python 3.11.9`.

Requisitos recomendados en Windows:

- `Python 3.11.9`.
- `pip` actualizado.
- `Microsoft C++ Build Tools`, necesario para instalar algunas dependencias de `InsightFace` cuando `pip` necesita compilar paquetes nativos.
- `Node.js` y `npm`, necesarios para ejecutar la interfaz React/Vite.
- `SQL Server` y SQL Server Management Studio o Azure Data Studio, necesarios para crear y administrar la base de datos.
- Webcam funcional.
- Chrome u otro navegador moderno.

Para instalar `Microsoft C++ Build Tools`, descarga el instalador desde Visual Studio Build Tools y marca la carga de trabajo `Desktop development with C++`. Esto instala el compilador de C++ que puede pedir `InsightFace` durante la instalacion.

### Backend Python

Crea un entorno virtual e instala las dependencias desde la raiz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si la instalacion de `insightface` falla con errores de compilacion, casi siempre significa que falta `Microsoft C++ Build Tools` o que no se reinicio la terminal despues de instalarlo.

### Frontend React

Las dependencias de Node no se guardan en Git. Despues de descargar el proyecto, instalalas desde la carpeta `witcam`:

```powershell
cd witcam
npm install
```

### Base de datos

El archivo `database/Tablas.sql` esta escrito para SQL Server. En su estado actual debe ejecutarse una sola vez desde SSMS, Azure Data Studio o una herramienta compatible con separadores `GO`. El script crea la base de datos `WitcamBD` y sus tablas iniciales.

Si `WitcamBD` ya existe, volver a ejecutar el script completo producira errores porque todavia no es un script idempotente.

## Ejecucion del prototipo funcional

Desde la raiz del repositorio, con el entorno virtual activado:

```powershell
python app.py
```

Luego abre en Chrome:

```text
http://localhost:8000/
```

Desde la interfaz web puedes iniciar o detener la webcam. El video mostrado en la pagina viene desde Python, ya procesado por Witcam.

No es necesario ejecutar `php -S`. Si ya hay un servidor PHP usando el puerto `8000`, cierralo con `Ctrl+C` antes de iniciar `app.py`.

Para cerrar el servidor, vuelve a la terminal y presiona `Ctrl+C`.

## Ejecucion de React

En otra terminal:

```powershell
cd witcam
npm run dev
```

Vite mostrara la direccion local, normalmente:

```text
http://localhost:5173/
```

El backend Python usa `http://localhost:8000/` y React usa normalmente `http://localhost:5173/`. Por ahora son aplicaciones separadas. Para completar la integracion se debera configurar el proxy de Vite o CORS y hacer que React consuma los endpoints de `app.py`.

Comandos adicionales del frontend:

```powershell
npm run lint
npm run build
npm run preview
```

## Interfaz web de prueba

La pagina permite:

- Iniciar y detener la webcam.
- Ver el video procesado por Python.
- Ver la cantidad de referencias y capturas pendientes.
- Ver el umbral real cargado desde `app.py`.
- Recargar referencias manualmente con el boton `Recargar referencias`.
- Actualizar automaticamente la lista cuando aparecen nuevas capturas pendientes, sin interrumpir si estas renombrando una imagen.
- Renombrar imagenes manteniendo fija la extension (`.jpg`, `.png`, `.webp`, etc.).
- Mover imagenes desde pendientes a referencias.
- Mover imagenes desde referencias a pendientes.
- Eliminar imagenes pendientes.

Para borrar una referencia oficial, primero debes moverla a pendientes y luego eliminarla desde ahi.

La app soporta nombres con mayusculas, minusculas y acentos en los archivos de referencia. En Windows tambien maneja correctamente cambios solo de mayusculas/minusculas, por ejemplo pasar de `matias.jpg` a `MATIAS.jpg`.

## Flujo de reconocimiento

1. La interfaz web llama al servidor local de Python.
2. Python abre la webcam cuando presionas `Iniciar`.
3. Cada cierto numero de frames, la app reduce la imagen para analizarla mas rapido.
4. InsightFace/SCRFD detecta los rostros y genera embeddings.
5. ByteTrack asigna un `ID` estable a cada rostro detectado.
6. Cada embedding se compara con las referencias cargadas.
7. Si supera el umbral de similitud, se muestra como persona reconocida.
8. Si no se reconoce y permanece visible, se guarda una captura en `referencias_pendientes/`.
9. La interfaz recibe el video procesado desde `/video_feed`.
10. Si cambian las carpetas de referencias o pendientes, Python recarga las referencias automaticamente.

## Oclusion

Si una persona ya fue reconocida y despues se tapa parte de la cara o gira la cabeza, la app no la marca inmediatamente como desconocida. Mantiene una memoria temporal por `tracker_id` y tambien puede recuperar la identidad si ByteTrack le asigna un ID nuevo, comparando el embedding y la ultima posicion conocida.

Parametros relacionados:

```python
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30
MIN_SIMILITUD_REIDENTIFICACION = 0.35
MIN_IOU_REIDENTIFICACION = 0.10
MIN_CONFIANZA_ROSTRO_ANALIZABLE = 0.60
MIN_SIMETRIA_ROSTRO_ANALIZABLE = 0.45
MAX_DESVIACION_NARIZ_ANALIZABLE = 0.35
```

Esto ayuda a evitar que alguien conocido sea guardado como desconocido solo por taparse los ojos, girar un poco la cara, aparecer parcialmente cubierto o recibir un nuevo ID del tracker.

Antes de generar o comparar un embedding, Witcam comprueba que el rostro tenga tamano, confianza y simetria facial suficientes. Si la persona esta demasiado de perfil o no muestra informacion confiable, la caja indica `No evaluable` o conserva temporalmente la identidad anterior, pero no crea un nuevo desconocido ni guarda una captura hasta obtener un angulo mejor.

## Parametros importantes

Estos valores estan al inicio de `app.py`.

```python
CAMARA = 0  # O una URL como "rtsp://IP:8554/camara1"
UMBRAL_SIMILITUD = 0.45
ANCHO_ANALISIS = 512
ALTO_ANALISIS = 384
DETECTAR_CADA_N_FRAMES = 2
RECONOCER_CADA_N_DETECCIONES = 3
DET_SIZE = 320
JPEG_QUALITY = 86
FPS_VIDEO_WEB = 12
ANCHO_MAX_VIDEO_WEB = 1280
ALTO_MAX_VIDEO_WEB = 720
TIEMPO_CONFIRMACION_DESCONOCIDO = 3.0
MIN_MUESTRAS_DESCONOCIDO = 4
COOLDOWN_CAPTURA = 15
```

`CAMARA`: indice de webcam o URL RTSP de una camara IP o canal de NVR.

`UMBRAL_SIMILITUD`: umbral para considerar una cara como reconocida. Mas alto es mas estricto; mas bajo reconoce mas facil, pero puede equivocarse mas.

`DETECTAR_CADA_N_FRAMES`: controla cada cuantos frames SCRFD actualiza las cajas y ByteTrack. Un valor bajo mejora el seguimiento de movimiento, pero aumenta el uso de CPU.

`RECONOCER_CADA_N_DETECCIONES`: controla cada cuantas actualizaciones del tracker InsightFace vuelve a generar embeddings. Entre reconocimientos, la identidad confirmada permanece asociada al track y se muestra como `seguimiento`.

`ANCHO_ANALISIS`, `ALTO_ANALISIS` y `DET_SIZE`: controlan la carga del modelo. El video conserva su proporcion original dentro de esos limites para no deformar los rostros. Subirlos puede mejorar la deteccion de rostros pequenos, pero aumenta el lag.

`JPEG_QUALITY`: calidad del video enviado al navegador. Subirlo mejora imagen pero puede aumentar carga y lag.

`FPS_VIDEO_WEB`, `ANCHO_MAX_VIDEO_WEB` y `ALTO_MAX_VIDEO_WEB`: limitan la copia enviada al navegador para evitar codificar cada frame a 1080p. La IA sigue usando el frame original. La captura RTSP funciona en un hilo independiente y conserva solamente el frame mas reciente, evitando acumular video atrasado mientras trabaja la IA. Si la transmision se corta temporalmente, el capturador intenta reconectarse automaticamente.

`TIEMPO_CONFIRMACION_DESCONOCIDO`: segundos minimos antes de guardar un desconocido.

`MIN_MUESTRAS_DESCONOCIDO`: cantidad minima de lecturas antes de guardar un desconocido.

`COOLDOWN_CAPTURA`: segundos minimos antes de volver a guardar una captura del mismo desconocido.

## Colores en pantalla

- Verde: persona reconocida desde `referencias_reconocimiento/`.
- Amarillo: persona detectada desde `referencias_pendientes/`.
- Rojo: persona desconocida.
- Naranjo/celeste: persona conocida con posible oclusion.

## Privacidad

Las carpetas con imagenes personales estan ignoradas por git en `.gitignore`:

```text
referencias_reconocimiento/
referencias_pendientes/
```

Esto evita subir fotos privadas al repositorio por accidente.

## Notas

La app esta configurada para CPU. Si el equipo tiene GPU compatible con ONNX Runtime/CUDA, se puede mejorar el rendimiento agregando deteccion automatica de `CUDAExecutionProvider`.

Para la futura conexion de camaras IP, se recomienda que cada modelo soporte RTSP y ONVIF, ademas de un stream secundario configurable. Analizar un stream secundario de menor resolucion y entre 10 y 15 FPS reduce la carga sin impedir que otro sistema grabe el stream principal en alta calidad.
