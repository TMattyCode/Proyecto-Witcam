# Witcam - Reconocimiento facial local

Aplicacion local de reconocimiento facial en tiempo real usando webcam. Detecta rostros con InsightFace/SCRFD, mantiene IDs de seguimiento con ByteTrack y guarda capturas de personas desconocidas para revisarlas despues.

## Que usa

- `OpenCV`: lectura de webcam, dibujo de cajas y ventana de video.
- `InsightFace`: deteccion de rostros y generacion de embeddings faciales.
- `SCRFD`: detector facial usado internamente por InsightFace.
- `ByteTrack`: seguimiento de rostros para mantener un ID estable por persona.
- `NumPy`: calculo de similitud entre embeddings.

## Estructura de carpetas

El programa crea automaticamente las carpetas necesarias si no existen.

```text
referencias_reconocimiento/
referencias_pendientes/
```

`referencias_reconocimiento/` contiene las imagenes oficiales que la app debe reconocer. Puedes poner ahi fotos tuyas o de otras personas autorizadas. El nombre del archivo se usa como nombre en pantalla, por ejemplo `matias.jpg` se mostrara como `matias`.

`referencias_pendientes/` contiene capturas generadas automaticamente cuando aparece una persona desconocida durante algunos segundos. Luego puedes revisar esas imagenes y mover/copiar las que quieras aprobar a `referencias_reconocimiento/`.

## Primer uso

La primera vez puedes ejecutar la app aunque no exista ninguna imagen de referencia. Si `referencias_reconocimiento/` esta vacia, el programa avisa por consola y sigue funcionando.

Cuando detecte un rostro desconocido valido por varios segundos, guardara una captura en `referencias_pendientes/`. Despues puedes revisar esa captura y pasarla manualmente a `referencias_reconocimiento/` si quieres que esa persona quede como reconocida.

## Instalacion

Se recomienda usar un entorno virtual.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecucion

```powershell
python webcam_reconocimiento.py
```

Para salir, presiona `Q` en la ventana de video.

## Flujo de reconocimiento

1. La webcam captura frames en vivo.
2. Cada cierto numero de frames, la app reduce la imagen para analizarla mas rapido.
3. InsightFace/SCRFD detecta los rostros y genera embeddings.
4. ByteTrack asigna un `ID` estable a cada rostro detectado.
5. Cada embedding se compara con las referencias cargadas.
6. Si supera el umbral de similitud, se muestra como persona reconocida.
7. Si no se reconoce y permanece visible, se guarda una captura en `referencias_pendientes/`.

## Oclusion

Si una persona ya fue reconocida y despues se tapa parte de la cara, la app no la marca inmediatamente como desconocida. Mantiene una memoria temporal por `tracker_id`.

Parametros relacionados:

```python
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30
```

Esto ayuda a evitar que alguien conocido sea guardado como desconocido solo por taparse los ojos, girar un poco la cara o aparecer parcialmente cubierto.

## Parametros importantes

Estos valores estan al inicio de `webcam_reconocimiento.py`.

```python
CAMARA = 0
UMBRAL_SIMILITUD = 0.45
ANCHO_ANALISIS = 416
ALTO_ANALISIS = 312
ANALIZAR_CADA_N_FRAMES = 10
DET_SIZE = 256
TIEMPO_CONFIRMACION_DESCONOCIDO = 3.0
MIN_MUESTRAS_DESCONOCIDO = 4
```

`CAMARA`: indice de la webcam. Si no abre, prueba `1` o `2`.

`UMBRAL_SIMILITUD`: umbral para considerar una cara como reconocida. Mas alto es mas estricto; mas bajo reconoce mas facil, pero puede equivocarse mas.

`ANALIZAR_CADA_N_FRAMES`: mientras mas alto, menos lag pero menos actualizacion de reconocimiento. Mientras mas bajo, mas fluido el reconocimiento pero mas pesado.

`ANCHO_ANALISIS`, `ALTO_ANALISIS` y `DET_SIZE`: controlan la carga del modelo. Subirlos puede mejorar deteccion de rostros pequenos, pero aumenta el lag.

`TIEMPO_CONFIRMACION_DESCONOCIDO`: segundos minimos antes de guardar un desconocido.

`MIN_MUESTRAS_DESCONOCIDO`: cantidad minima de lecturas antes de guardar un desconocido.

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
