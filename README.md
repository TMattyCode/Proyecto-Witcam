# Witcam - Reconocimiento facial y monitoreo de camaras

Witcam es una aplicacion de reconocimiento facial en tiempo real. Su motor de IA puede analizar una webcam, una fuente RTSP o un archivo de video local, detectar personas con YOLO26n, detectar y reconocer rostros con InsightFace/SCRFD, mantener IDs de seguimiento con ByteTrack y guardar capturas de personas desconocidas para revisarlas despues.

El repositorio tambien contiene la interfaz definitiva desarrollada con React y Vite, ademas del script inicial para la base de datos SQL Server. La integracion entre estos componentes sigue en desarrollo.

## Estado actual

- El backend modular v2 se inicia con `main.py`, procesa una fuente de video y expone una API HTTP local.
- La version estable anterior y su interfaz se conservan dentro de `interfaz_prueba/` como respaldo independiente.
- La interfaz final se encuentra en `frontend/` y usa React, Vite, React Router, rutas protegidas y restauracion de sesion.
- Registro, inicio, consulta y cierre de sesion consumen la API modular de Python. El backend evita cuentas activas duplicadas, restaura sesiones y actualiza el ultimo acceso.
- Cada administrador tiene su propia cuenta y recibe un `Grupo 1` inicial. Puede gestionar subusuarios y asignarles los permisos preestablecidos, mientras que los registros desactivados se conservan como historial.
- Los grupos y camaras se persisten por cuenta en SQL Server. La interfaz permite crear, editar, filtrar y desactivar camaras `webcam`, `RTSP`, `ONVIF` y simuladas, con un maximo visual actual de nueve camaras.
- La webcam local puede iniciarse y detenerse desde React con el pipeline de IA habilitado. Las fuentes RTSP y ONVIF ya se registran de forma segura, pero su conexion al motor de video por `id_camara` sigue pendiente; las camaras simuladas muestran una imagen estatica para probar la cuadricula.
- La vista de ingresos identificados consulta SQL Server, admite filtros acumulables y pagina 25 detecciones por vez. Por ahora se alimenta con datos de prueba: el pipeline de IA todavia no inserta automaticamente personas, muestras ni detecciones en la base de datos.
- En desarrollo local, SQL Server se conecta mediante memoria compartida (`lpc:localhost`) y autenticacion de Windows, sin exponer un puerto TCP.
- Actualmente el motor de IA procesa una sola fuente global configurable en `backend/config.py`. El siguiente paso de integracion es crear un motor por camara activa y vincular las fuentes guardadas en SQL Server con el reconocimiento y sus detecciones.

## Arquitectura actual y prevista

```text
Camaras IP (RTSP/ONVIF)
          |
          v
Backend Python (API + IA)
   |                 |
   v                 v
SQL Server      Frontend React
```

El NVR no es obligatorio para el reconocimiento. Python puede analizar directamente el stream secundario de una camara IP o tratar cada canal RTSP de un NVR como una fuente independiente. La conexion automatica de las camaras registradas al motor de IA todavia forma parte de la siguiente etapa.

MediaMTX se usa solamente durante las pruebas para publicar un video local como un stream RTSP simulado. Si una camara IP o un canal de NVR ya entrega una URL RTSP, el motor puede usar directamente esa direccion y MediaMTX no es necesario. Por ahora la URL debe pasarse al motor o configurarse en `backend/config.py`; registrarla desde React todavia no inicia esa transmision. La instalacion local puede mantenerse dentro de `MediaMTX/`; esa carpeta, sus ejecutables, certificados y videos no se versionan en Git.

### Backend modular v2

La v2 separa configuracion, dominio, inteligencia artificial, video, galerias, servicios y API. `backend/container.py` ensambla manualmente los componentes y expone `construir_aplicacion` junto con el alias `build_application`.

Solo los adaptadores de `backend/ia/adaptadores/` importan directamente InsightFace, Ultralytics y Supervision. El pipeline depende de contratos propios para `DetectorPersonas`, `DetectorRostros`, `ReconocedorFacial`, `RastreadorObjetos` y `AnalizadorFrame`. Esto permite probar las reglas con modelos falsos y cambiar proveedores sin reescribir el motor.

`RepositorioGalerias` comparte un `threading.RLock` entre la API y el motor. El bloqueo cubre listados, firmas, carga completa, escritura, movimiento, renombrado, rechazo y reconciliacion. De esta forma la IA no puede leer una galeria a medio modificar mientras la interfaz realiza una operacion.

La capa `backend/database/` encapsula la conexion local a SQL Server y los repositorios de usuarios, ingresos y camaras. El script `database/Tablas.sql` es la fuente unica para recrear `WitcamBD`, sus catalogos, relaciones, restricciones e indices durante esta etapa de desarrollo.

## Que usa

- `OpenCV`: lectura de webcam, procesamiento de frames, dibujo de cajas y generacion del video web.
- `YOLO26n`: deteccion de personas completas, incluso cuando el rostro no esta visible.
- `InsightFace`: deteccion de rostros y generacion de embeddings faciales.
- `SCRFD`: detector facial usado internamente por InsightFace.
- `ByteTrack`: dos trackers independientes, uno para personas detectadas por YOLO y otro para rostros detectados por SCRFD.
- `PyTorch` y `Ultralytics`: ejecucion e integracion del modelo YOLO26n.
- `NumPy`: calculo de similitud entre embeddings.
- `ThreadingHTTPServer`: servidor web local integrado en Python.
- `React`: interfaz de usuario final.
- `Vite`: servidor de desarrollo y compilacion del frontend React.
- `SQL Server`: persistencia local de cuentas, usuarios, roles, permisos, grupos de camaras, detecciones y alertas.

## Estructura del repositorio

```text
main.py                        Punto de entrada del backend modular v2
backend/config.py              Configuracion inmutable y rutas
backend/container.py           Composicion manual de dependencias
backend/dominio/               Modelos de datos del reconocimiento
backend/ia/                    Pipeline, identidad, desconocidos y adaptadores
backend/video/                 Captura, motor, renderizado y publicacion
backend/galerias/              Referencias, muestras y repositorio bloqueado
backend/aplicacion/            Servicios y ciclo de vida
backend/api/                   API HTTP, JSON, archivos y MJPEG
backend/database/              Conexion SQL Server y repositorios
tests/                         Pruebas automaticas con unittest
requirements.txt              Dependencias de Python
frontend/                      Interfaz final React/Vite
interfaz_prueba/               Version anterior autocontenida de respaldo
database/Tablas.sql           Creacion inicial de la base de datos SQL Server
database/ingreso_personas.sql Datos de prueba para personas y detecciones
referencias_reconocimiento/   Rostros aprobados (se crea automaticamente)
referencias_pendientes/       Capturas por revisar (se crea automaticamente)
```

Dentro de `frontend/src/` se encuentran las paginas de inicio de sesion, registro, resumen del sistema, camaras, ingresos identificados, lista de observacion y configuracion. React Router administra las rutas internas con `HashRouter`, adecuado para la futura ventana de escritorio. La lista de observacion y parte del resumen del sistema conservan contenido de interfaz pendiente de conectar al backend.

## Carpetas de reconocimiento

El programa crea automaticamente las carpetas necesarias si no existen.

```text
referencias_reconocimiento/
referencias_pendientes/
```

Cada persona se representa mediante una subcarpeta y puede contener varias muestras:

```text
referencias_reconocimiento/
  Matias/
    frontal.jpg
    perfil.jpg
referencias_pendientes/
  desconocido_track_8_20260724_192239/
    muestra_01.jpg
```

El nombre de la subcarpeta es la identidad mostrada en pantalla. InsightFace compara el rostro contra todas sus muestras. Las imagenes sueltas del formato anterior se migran automaticamente a galerias de una muestra al iniciar la app.

## Primer uso

La primera vez puedes ejecutar la app aunque no exista ninguna imagen de referencia. Si `referencias_reconocimiento/` esta vacia, el programa avisa por consola y sigue funcionando.

Cuando detecte un rostro desconocido valido, creara una galeria en `referencias_pendientes/`. Mientras siga observando esa identidad pendiente, puede agregar vistas diferentes hasta completar la galeria.

Antes de crear la galeria, el recorte se procesa una segunda vez con SCRFD. Si el propio modelo no puede volver a detectar ese rostro guardado, la captura se descarta y el motor espera un angulo reutilizable.

## Requisitos

Esta aplicacion fue desarrollada y probada con `Python 3.11.9`.

Requisitos recomendados en Windows:

- `Python 3.11.9`.
- `pip` actualizado.
- `Microsoft C++ Build Tools`, necesario para instalar algunas dependencias de `InsightFace` cuando `pip` necesita compilar paquetes nativos.
- El modelo facial `buffalo_l` de InsightFace disponible en su cache local.
- El archivo de pesos `yolo26n.pt` en la raiz del proyecto.
- `Node.js` y `npm`, necesarios para ejecutar la interfaz React/Vite.
- `SQL Server` y SQL Server Management Studio o Azure Data Studio, necesarios para crear y administrar la base de datos.
- Una webcam, URL RTSP o archivo de video local para usar como fuente.
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

Las dependencias de Node no se guardan en Git. Despues de descargar el proyecto, instalalas desde `frontend/`:

```powershell
cd frontend
npm install
```

### Base de datos

El archivo `database/Tablas.sql` esta escrito para SQL Server y es la fuente unica del esquema durante esta etapa de desarrollo. Puede ejecutarse desde SSMS, Azure Data Studio o una herramienta compatible con separadores `GO`.

Si `WitcamBD` ya existe, el script la elimina y vuelve a crearla con todas sus tablas, restricciones, catalogos e indices actualizados. Por lo tanto, se puede ejecutar repetidamente mientras el esquema siga en desarrollo, pero cada ejecucion borra todos los datos almacenados anteriormente.

`database/ingreso_personas.sql` es un apoyo temporal para probar la pantalla de ingresos identificados. Usa la primera cuenta disponible, o el `@id_cuenta` indicado manualmente, crea un grupo y una camara simulada si hacen falta e inserta 20 personas con sus detecciones. No llena `MuestraFacial`, porque las muestras siguen almacenandose en carpetas locales.

Antes de guardar una camara ONVIF, define una frase secreta local para cifrar sus credenciales. No agregues este valor al repositorio:

```powershell
$env:WITCAM_CAMERA_SECRET="una-frase-larga-y-privada"
python main.py
```

Las respuestas de la API nunca incluyen la contrasena de la camara. Una webcam o camara simulada no necesita esta variable.

Las acciones de eliminar camaras y grupos usan eliminacion logica: conservan las filas y cambian `Camara.activa` o `GrupoCamara.activo` a `0`. Un grupo no puede desactivarse si contiene camaras activas y cada cuenta debe conservar al menos un grupo activo. Esto mantiene validas las referencias de las detecciones historicas.

Una camara no puede editarse ni desactivarse mientras se encuentra transmitiendo. React bloquea ambas acciones y el backend vuelve a validar la regla usando el `cameraId` asociado al motor activo, de modo que una solicitud manipulada tambien se rechaza. Al iniciar, el backend comprueba ademas que la webcam esta activa, pertenece a la sesion y coincide con el indice solicitado. Primero se debe detener la transmision desde su tarjeta.

La unicidad de nombres considera solamente camaras, grupos y usuarios activos. Despues de desactivar un registro se puede crear otro con el mismo nombre sin eliminar el historial anterior. Los subusuarios desactivados se conservan como historial en SQL Server, pero no se listan ni se pueden reactivar desde la aplicacion.

La configuracion local predeterminada usa `ODBC Driver 17 for SQL Server`, autenticacion de Windows y `lpc:localhost`. De esta manera Python y SQL Server se comunican mediante memoria compartida sin habilitar TCP/IP ni abrir el puerto `1433`.

## Ejecucion durante el desarrollo

Inicia el backend desde la raiz, con el entorno virtual activado:

```powershell
python main.py
```

En otra terminal, inicia React:

```powershell
cd frontend
npm run dev
```

Vite mostrara la direccion local, normalmente:

```text
http://localhost:5173/
```

Durante el desarrollo, Python usa `http://localhost:8000/` y React usa normalmente `http://localhost:5173/`. El proxy de Vite dirige `/api` y `/video_feed` al backend. Las camaras y grupos se cargan desde SQL Server segun la cuenta autenticada; `localStorage` ya no se usa para persistirlos.

La version final se empaquetara como aplicacion de escritorio: React se compilara, Python servira sus archivos y una ventana nativa iniciara ambos componentes desde un unico ejecutable. El cliente no necesitara ejecutar Vite ni abrir el navegador manualmente.

La version anterior sigue disponible como respaldo independiente:

```powershell
cd interfaz_prueba
python app.py
```

Comandos adicionales del frontend:

```powershell
npm run lint
npm run build
npm run preview
```

## Frontend React actual

La interfaz de `frontend/` incluye actualmente:

- Registro de cuentas administradoras e inicio de sesion con rutas protegidas.
- Restauracion y cierre de sesion, nombre real de la cuenta y resumen de subusuarios activos.
- Creacion de subusuarios y administracion de sus permisos desde un unico panel, con buscador, filtros acumulables, paginacion y eliminacion logica con confirmacion propia. El administrador no puede modificar los datos personales ni la contrasena de un subusuario ya creado; esa edicion correspondera al propio usuario.
- Gestion por cuenta de grupos y camaras, incluyendo validacion para conservar al menos un grupo y para impedir desactivar grupos que aun contienen camaras activas.
- Registro de fuentes `webcam`, `RTSP`, `ONVIF` y simuladas, filtros por camara y grupo, seleccion de cuadricula y vista en pantalla completa.
- Visualizacion en vivo de una webcam local mediante el MJPEG procesado por YOLO, SCRFD, InsightFace y ByteTrack. RTSP y ONVIF muestran por ahora el estado de fuente registrada hasta completar su conexion al motor.
- Consulta paginada de ingresos identificados, con filtros por texto, fecha, hora y camara. Los botones para eliminar o enviar una persona a la lista de observacion siguen deshabilitados.
- Diseno adaptable y navegacion con `HashRouter`, pensado para empaquetarse posteriormente como aplicacion de escritorio.

La lista de observacion, las acciones sobre personas y varios datos del resumen general todavia son prototipos visuales o estan pendientes de integracion.

## Interfaz anterior de respaldo

La version conservada en `interfaz_prueba/` permite:

- Iniciar y detener la fuente de video.
- Ver el video procesado por Python.
- Ver la cantidad de personas reconocidas y pendientes.
- Ver el umbral real cargado desde `backend/config.py`.
- Recargar referencias manualmente con el boton `Recargar referencias`.
- Actualizar automaticamente la lista cuando aparecen nuevas capturas pendientes, sin interrumpir si estas renombrando una imagen.
- Ver la mejor muestra disponible como portada y la cantidad de muestras.
- Renombrar personas cambiando el nombre de su galeria.
- Mover galerias completas desde pendientes a referencias o viceversa.
- Eliminar galerias pendientes completas.

Para borrar una referencia oficial, primero debes moverla a pendientes y luego eliminarla desde ahi.

La app soporta mayusculas, minusculas y acentos en los nombres de persona. En Windows tambien maneja correctamente cambios solo de mayusculas/minusculas.

Las vistas previas incluyen una version basada en la fecha de modificacion y se sirven sin cache. Si una imagen se elimina y posteriormente otra reutiliza el mismo nombre, la interfaz muestra el archivo nuevo en lugar de una copia antigua guardada por el navegador.

## Flujo de reconocimiento

1. La interfaz web llama al servidor local de Python.
2. Python abre la webcam, URL RTSP o archivo de video configurado cuando presionas `Iniciar`.
3. YOLO26n detecta personas y un ByteTrack corporal mantiene sus IDs.
4. Si una persona no contiene una deteccion facial, se muestra como `sin rostro visible`.
5. SCRFD detecta los rostros y un segundo ByteTrack mantiene sus IDs.
6. InsightFace genera embeddings solamente cuando corresponde ejecutar reconocimiento.
7. Cada embedding se compara con todas las muestras de las galerias cargadas.
8. Si supera el umbral de similitud, se muestra como persona reconocida.
9. Si no se reconoce y permanece visible, se crea una galeria pendiente.
10. La interfaz recibe el video procesado desde `/video_feed`.
11. Si cambian las carpetas de referencias o pendientes, Python recarga las referencias automaticamente.

## API HTTP

La v2 conserva las rutas originales de la version estable y agrega los contratos utilizados por React:

- Video y galerias: `GET /`, `/video_feed`, `/placeholder`, `/api/status` y `/api/list`.
- Autenticacion: `GET /api/auth/session` y `POST /api/auth/register`, `/api/auth/login`, `/api/auth/logout`.
- Cuenta y subusuarios: `GET /api/cuenta/resumen`, `GET/POST /api/subusuarios`, `POST /api/subusuarios/editar` para administrar exclusivamente permisos y `POST /api/subusuarios/estado` para la eliminacion logica.
- Camaras y grupos: `GET /api/camaras`, `POST /api/camaras/crear`, `/api/camaras/editar`, `/api/camaras/eliminar` y `/api/grupos-camara/guardar`.
- Ingresos: `GET /api/ingresos` y `GET /api/ingresos/camaras`.
- Motor y galerias: `POST /api/start`, `/api/stop`, `/api/approve`, `/api/unapprove`, `/api/rename` y `/api/reject`.

`POST /api/start` acepta `source`, el booleano `analysis` y `cameraId`; React envia `analysis: true` y el ID de la webcam para cargar el pipeline de reconocimiento y proteger la camara activa frente a ediciones o eliminaciones. Las rutas de cuenta, subusuarios, camaras e ingresos validan la sesion y restringen las operaciones administrativas. El backend comprueba pertenencia a la cuenta para impedir consultar o modificar recursos de otro administrador. Las rutas originales de galerias mantienen los campos `file`, `newName` y `type`, junto con las respuestas `ok/error`.

Los errores esperados de validacion conservan mensajes especificos para el usuario. Las excepciones internas de SQL Server, video o IA se registran solamente en la consola del backend y la API devuelve un mensaje seguro. React traduce fallos de conexion o respuestas incompletas y, si la sesion vence, elimina el token, vuelve al inicio y solicita iniciar sesion nuevamente.

La interfaz anterior conserva sus archivos dentro de `interfaz_prueba/` y usa sus propias carpetas de galerias para no interferir con el backend modular.

## Pruebas automaticas

La suite de Python usa `unittest`, modelos falsos, galerias temporales y un servidor HTTP con puerto efimero. Cubre geometria, calidad facial, comparacion, reconciliacion, concurrencia, identidad, candidatos, pipeline, autenticacion, usuarios, camaras, ingresos y contratos HTTP/MJPEG. Las pruebas de Node verifican la validacion del registro, inicio de sesion y formularios de subusuarios.

```powershell
python -m compileall -q backend tests main.py
python -m unittest discover -s tests -v
cd frontend
npm test
```

Actualmente existen 63 pruebas automaticas de Python y 7 pruebas de Node. Tambien se completo una reproduccion real de diez minutos, 1920x1080 a 30 FPS, con InsightFace/SCRFD, YOLO y ByteTrack usando galerias temporales. El pipeline llego al final del video sin cortes y la firma de galerias permanecio valida. Webcam y RTSP quedan como pruebas manuales dependientes de tener esas fuentes disponibles.

## Oclusion

Si una persona ya fue reconocida y despues se tapa parte de la cara o gira la cabeza, la app no la marca inmediatamente como desconocida. Mantiene una memoria temporal por `tracker_id` y tambien puede recuperar la identidad si ByteTrack le asigna un ID nuevo, comparando el embedding y la ultima posicion conocida.

Parametros relacionados:

```python
ConfiguracionTracking.tolerancia_oclusion = 6.0
ConfiguracionTracking.similitud_posible_misma_persona = 0.30
ConfiguracionTracking.similitud_reidentificacion = 0.35
ConfiguracionTracking.iou_reidentificacion = 0.10
ConfiguracionRostro.ancho_minimo = 55
ConfiguracionRostro.alto_minimo = 55
ConfiguracionRostro.confianza_minima = 0.60
ConfiguracionRostro.simetria_minima = 0.25
ConfiguracionRostro.desviacion_maxima_nariz = 0.70
```

Esto ayuda a evitar que alguien conocido sea guardado como desconocido solo por taparse los ojos, girar un poco la cara, aparecer parcialmente cubierto o recibir un nuevo ID del tracker.

Antes de generar o comparar un embedding, Witcam comprueba que el rostro tenga tamano, confianza y simetria facial suficientes. Si la persona esta demasiado de perfil o no muestra informacion confiable, la caja indica `No evaluable` o conserva temporalmente la identidad anterior, pero no crea un nuevo desconocido ni guarda una captura hasta obtener un angulo mejor.

## Parametros importantes

La configuracion de la v2 se encuentra en las dataclasses inmutables de `backend/config.py`. Para cambiar la fuente se modifica `ConfiguracionVideo.fuente`; acepta un indice de webcam, una URL RTSP o una ruta de video local.

```python
ConfiguracionVideo.fuente
ConfiguracionVideo.ancho_analisis = 512
ConfiguracionVideo.alto_analisis = 384
ConfiguracionVideo.detectar_cada_n_frames = 1
ConfiguracionVideo.calidad_jpeg = 86
ConfiguracionVideo.fps_video_web = 12

ConfiguracionRostro.umbral_similitud = 0.45
ConfiguracionRostro.segunda_similitud_minima = 0.35
ConfiguracionRostro.umbral_galeria_una_muestra = 0.55
ConfiguracionRostro.reconocer_cada_n_detecciones = 6
ConfiguracionRostro.reconocer_cada_n_detecciones_sin_identidad = 3
ConfiguracionRostro.tamano_detector = 352

ConfiguracionYolo.habilitado = True
ConfiguracionYolo.tamano_imagen = 416
ConfiguracionYolo.confianza = 0.35
ConfiguracionYolo.detectar_cada_n_ciclos = 3

ConfiguracionTracking.tolerancia_identidad_corporal = 3.0
ConfiguracionTracking.confirmaciones_identidad_inicial = 2
ConfiguracionTracking.confirmaciones_cambio_identidad = 3
ConfiguracionTracking.tolerancia_oclusion = 6.0

ConfiguracionGalerias.max_muestras_por_persona = 6
ConfiguracionGalerias.similitud_evitar_duplicado = 0.40

ConfiguracionDesconocidos.tiempo_confirmacion = 1.5
ConfiguracionDesconocidos.muestras_minimas = 3
ConfiguracionDesconocidos.cooldown_captura = 15.0
```

`ConfiguracionVideo.fuente`: indice de webcam, URL RTSP de una camara IP o canal de NVR, o ruta de un video local. Los videos locales se reproducen segun sus FPS originales y vuelven al primer fotograma cada vez que se detiene e inicia el motor. En este modo no se necesitan MediaMTX ni FFmpeg.

`ConfiguracionRostro.umbral_similitud`: umbral para considerar una cara como reconocida. Mas alto es mas estricto; mas bajo reconoce mas facil, pero puede equivocarse mas.

Una galeria con varias muestras necesita que la mejor coincidencia supere `ConfiguracionRostro.umbral_similitud` y que una segunda muestra alcance `ConfiguracionRostro.segunda_similitud_minima`. Una coincidencia aislada ya no asigna el nombre. Las galerias de una sola foto usan el umbral mas estricto `ConfiguracionRostro.umbral_galeria_una_muestra`.

Si un desconocido se parece parcialmente a una identidad existente por encima de `ConfiguracionGalerias.similitud_evitar_duplicado`, el motor espera un angulo mejor en vez de crear inmediatamente otra galeria.

`ConfiguracionVideo.detectar_cada_n_frames`: controla cada cuantos frames SCRFD actualiza las cajas y ByteTrack. Un valor bajo mejora el seguimiento de movimiento, pero aumenta el uso de CPU.

`ConfiguracionRostro.reconocer_cada_n_detecciones`: controla cada cuantas actualizaciones del tracker InsightFace vuelve a generar embeddings cuando las personas visibles ya tienen identidad. Entre reconocimientos, la identidad confirmada permanece asociada al cuerpo y se muestra como `seguimiento`.

`ConfiguracionRostro.reconocer_cada_n_detecciones_sin_identidad`: usa una frecuencia temporalmente mas alta cuando YOLO detecta una persona que todavia no tiene identidad. Al confirmarla, el motor vuelve automaticamente al intervalo normal para reducir carga.

`ConfiguracionVideo.ancho_analisis`, `ConfiguracionVideo.alto_analisis` y `ConfiguracionRostro.tamano_detector`: controlan la carga del modelo. El video conserva su proporcion original dentro de esos limites para no deformar los rostros. Subirlos puede mejorar la deteccion de rostros pequenos, pero aumenta el lag. Los puntos faciales detectados se trasladan al frame original antes de generar el embedding, para aprovechar el detalle disponible en fuentes de alta resolucion.

`ConfiguracionYolo.habilitado`: activa YOLO26n para detectar cuerpos aunque SCRFD no encuentre un rostro. YOLO usa un ByteTrack independiente y muestra `Persona ID | sin rostro visible` cuando una persona permanece en escena sin una deteccion facial asociada.

`ConfiguracionYolo.tamano_imagen`, `ConfiguracionYolo.confianza` y `ConfiguracionYolo.detectar_cada_n_ciclos`: equilibran alcance, confianza y carga de CPU. YOLO se limita a la clase COCO `person` y se ejecuta con menor frecuencia que SCRFD. El archivo `yolo26n.pt` contiene los pesos del modelo y no se versiona en Git.

Cuando InsightFace confirma un rostro dentro de una caja corporal, la identidad queda vinculada temporalmente al `Persona ID` de YOLO/ByteTrack. La asignacion inicial exige varias confirmaciones y una similitud minima propia. Mientras ese cuerpo siga activo, un resultado facial diferente aislado no reemplaza el nombre. El cambio requiere `ConfiguracionTracking.confirmaciones_cambio_identidad` coincidencias consecutivas con una similitud minima configurada.

Una misma identidad no puede pertenecer a dos cuerpos activos. La ausencia temporal del rostro no permite transferir el nombre mientras el cuerpo propietario siga visible. Si ambos cuerpos estan activos, la nueva evidencia debe superar la similitud anterior por el margen de traspaso configurado, ademas de cumplir las confirmaciones y el minimo de similitud. La vinculacion caduca despues de `ConfiguracionTracking.tolerancia_identidad_corporal` sin observar el cuerpo.

La asociacion entre rostro y cuerpo tambien se conserva entre frames. Un rostro debe estar mayormente dentro de la zona superior de la caja corporal, y solo cambia a otro `Persona ID` cuando la nueva asociacion espacial es claramente mejor. Esto reduce los intercambios de identidad cuando dos personas se cruzan o sus cajas se superponen.

Si ByteTrack pierde brevemente un cuerpo y le entrega un nuevo `Persona ID`, el motor busca un track que haya desaparecido recientemente en la misma posicion. Cuando la superposicion supera `ConfiguracionTracking.iou_reasociacion_cuerpo`, transfiere la identidad y las asociaciones existentes al nuevo ID en vez de comenzar como una persona desconocida.

Cuando una galeria se renombra o se mueve entre pendientes y referencias, el motor reutiliza los embeddings de sus muestras. La identidad correspondiente se actualiza en los tracks activos sin borrar el seguimiento de las demas personas.

Las galerias pendientes admiten hasta `ConfiguracionGalerias.max_muestras_por_persona` vistas. Cada captura nueva debe mantener la similitud minima configurada con la primera imagen estable de la persona; esto evita contaminar la galeria cuando dos cajas corporales se cruzan. Una muestra demasiado parecida a otra se descarta. Cuando la galeria esta llena, una captura nueva solo reemplaza a la peor si supera la mejora de calidad configurada. Las galerias oficiales no se modifican automaticamente.

`ConfiguracionVideo.calidad_jpeg`: calidad del video enviado al navegador. Subirlo mejora imagen pero puede aumentar carga y lag.

`ConfiguracionVideo.fps_video_web`, `ConfiguracionVideo.ancho_maximo_web` y `ConfiguracionVideo.alto_maximo_web`: limitan la copia enviada al navegador para evitar codificar cada frame a 1080p. La IA sigue usando el frame original. La captura RTSP funciona en un hilo independiente y conserva solamente el frame mas reciente, evitando acumular video atrasado mientras trabaja la IA. Si la transmision se corta temporalmente, el capturador intenta reconectarse automaticamente.

`ConfiguracionDesconocidos.tiempo_confirmacion`: segundos minimos antes de guardar un desconocido. El tiempo acumulado se conserva durante frames intermedios y perdidas breves de calidad facial para no reiniciar el proceso mientras la persona camina.

`ConfiguracionDesconocidos.muestras_minimas`: cantidad minima de lecturas antes de guardar un desconocido.

`ConfiguracionDesconocidos.cooldown_captura`: segundos minimos antes de volver a guardar una captura del mismo desconocido.

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

Para completar la conexion de las camaras IP registradas, se recomienda usar modelos con RTSP y ONVIF, ademas de un stream secundario configurable. Analizar un stream secundario de menor resolucion y entre 10 y 15 FPS reduce la carga sin impedir que otro sistema grabe el stream principal en alta calidad.
