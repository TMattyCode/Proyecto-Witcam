# Witcam - Reconocimiento facial local

Aplicacion local de reconocimiento facial en tiempo real usando webcam. Detecta rostros con InsightFace/SCRFD, mantiene IDs de seguimiento con ByteTrack y guarda capturas de personas desconocidas para revisarlas despues.

## Que usa

- `OpenCV`: lectura de webcam, procesamiento de frames, dibujo de cajas y generacion del video web.
- `InsightFace`: deteccion de rostros y generacion de embeddings faciales.
- `SCRFD`: detector facial usado internamente por InsightFace.
- `ByteTrack`: seguimiento de rostros para mantener un ID estable por persona.
- `NumPy`: calculo de similitud entre embeddings.
- `ThreadingHTTPServer`: servidor web local integrado en Python.

## Estructura de carpetas

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

## Instalacion

Esta aplicacion fue desarrollada y probada con `Python 3.11.9`.

Requisitos recomendados en Windows:

- `Python 3.11.9`.
- `pip` actualizado.
- `Microsoft C++ Build Tools`, necesario para instalar algunas dependencias de `InsightFace` cuando `pip` necesita compilar paquetes nativos.
- Webcam funcional.
- Chrome u otro navegador moderno.

Para instalar `Microsoft C++ Build Tools`, descarga el instalador desde Visual Studio Build Tools y marca la carga de trabajo `Desktop development with C++`. Esto instala el compilador de C++ que puede pedir `InsightFace` durante la instalacion.

Despues, crea un entorno virtual e instala las dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si la instalacion de `insightface` falla con errores de compilacion, casi siempre significa que falta `Microsoft C++ Build Tools` o que no se reinicio la terminal despues de instalarlo.

## Ejecucion

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

## Interfaz web

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

Si una persona ya fue reconocida y despues se tapa parte de la cara, la app no la marca inmediatamente como desconocida. Mantiene una memoria temporal por `tracker_id`.

Parametros relacionados:

```python
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30
```

Esto ayuda a evitar que alguien conocido sea guardado como desconocido solo por taparse los ojos, girar un poco la cara o aparecer parcialmente cubierto.

## Parametros importantes

Estos valores estan al inicio de `app.py`.

```python
CAMARA = 0
UMBRAL_SIMILITUD = 0.45
ANCHO_ANALISIS = 416
ALTO_ANALISIS = 312
ANALIZAR_CADA_N_FRAMES = 10
DET_SIZE = 256
JPEG_QUALITY = 82
TIEMPO_CONFIRMACION_DESCONOCIDO = 3.0
MIN_MUESTRAS_DESCONOCIDO = 4
COOLDOWN_CAPTURA = 15
```

`CAMARA`: indice de la webcam. Si no abre, prueba `1` o `2`.

`UMBRAL_SIMILITUD`: umbral para considerar una cara como reconocida. Mas alto es mas estricto; mas bajo reconoce mas facil, pero puede equivocarse mas.

`ANALIZAR_CADA_N_FRAMES`: mientras mas alto, menos lag pero menos actualizacion de reconocimiento. Mientras mas bajo, mas fluido el reconocimiento pero mas pesado.

`ANCHO_ANALISIS`, `ALTO_ANALISIS` y `DET_SIZE`: controlan la carga del modelo. Subirlos puede mejorar deteccion de rostros pequenos, pero aumenta el lag.

`JPEG_QUALITY`: calidad del video enviado al navegador. Subirlo mejora imagen pero puede aumentar carga y lag.

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
