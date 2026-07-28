# Inteligencia artificial y seguimiento en Witcam

Este documento explica los modelos y algoritmos utilizados por Witcam, por
que fueron elegidos y como colaboran durante el reconocimiento. La
implementacion modular se encuentra principalmente en `backend/ia/`.

## Objetivo del sistema

Witcam necesita resolver varias preguntas distintas sobre cada frame:

1. Hay una persona en la imagen?
2. Donde esta su cuerpo?
3. Hay un rostro visible?
4. El rostro tiene calidad suficiente para analizarlo?
5. A quien se parece dentro de las galerias?
6. Es la misma persona que aparecia en frames anteriores?
7. Debe mantenerse, cambiarse o suspenderse la identidad mostrada?

Ningun modelo actual responde correctamente todas esas preguntas por si solo.
Por eso Witcam combina deteccion corporal, deteccion facial, reconocimiento,
tracking y reglas temporales.

## Resumen de componentes

| Componente | Funcion principal | Resultado |
| --- | --- | --- |
| YOLO26n | Detectar personas completas | Caja corporal y confianza |
| SCRFD | Detectar rostros y puntos faciales | Caja facial, confianza y landmarks |
| InsightFace | Representar y comparar identidades | Embedding facial |
| ByteTrack corporal | Seguir cajas de YOLO | `Persona ID` temporal |
| ByteTrack facial | Seguir cajas de SCRFD | `Rostro ID` temporal |
| Reglas de Witcam | Asociar, confirmar y corregir | Identidad visual final |

ByteTrack es un algoritmo de seguimiento, no un modelo de reconocimiento
biometrico. Tampoco conoce nombres. Los nombres provienen exclusivamente de
la comparacion facial realizada con InsightFace.

## YOLO26n

### Que hace

YOLO es un detector de objetos. Witcam lo limita a la clase COCO `person`, por
lo que actualmente solo busca personas completas:

```text
Frame
  |
  v
YOLO26n
  |
  +-- Caja de Persona 1
  +-- Caja de Persona 2
  +-- Caja de Persona 3
```

Cada deteccion contiene una caja `x1, y1, x2, y2` y una confianza. YOLO no
determina el nombre, no genera embeddings faciales y no decide si dos cuerpos
pertenecen a la misma identidad.

### Por que se eligio

- Puede detectar una persona aunque su rostro no sea visible.
- Permite conservar contexto corporal durante giros y oclusiones faciales.
- La variante `n` es pequena y adecuada para realizar pruebas con CPU.
- Se integra facilmente mediante Ultralytics.
- Permite ampliar el proyecto con nuevas clases en el futuro.

### Como se utiliza

El adaptador esta en:

```text
backend/ia/adaptadores/yolo.py
```

La configuracion actual usa:

```python
ConfiguracionYolo.tamano_imagen = 416
ConfiguracionYolo.confianza = 0.35
ConfiguracionYolo.detectar_cada_n_ciclos = 3
```

YOLO no se ejecuta en todos los ciclos. Witcam reutiliza los cuerpos seguidos
por ByteTrack entre ejecuciones para reducir carga.

### Limitaciones

- Detectar una persona no significa conocer su identidad.
- Una caja corporal puede superponerse con otra cuando hay aglomeraciones.
- Un cambio fuerte de posicion puede provocar un nuevo `Persona ID`.
- El modelo actual no distingue automaticamente entre una persona normal y
  una persona encapuchada.

## SCRFD

### Que hace

SCRFD es el detector facial utilizado dentro de la sesion de InsightFace.
Busca rostros y devuelve:

- Caja facial.
- Confianza de deteccion.
- Cinco puntos faciales: dos ojos, nariz y dos extremos de la boca.

```text
Rostro detectado

  ojo              ojo
    *                *

           * nariz

      *           * boca
```

Los landmarks permiten evaluar si el rostro tiene una geometria util antes de
generar un embedding.

### Por que se eligio

- Forma parte del ecosistema de InsightFace.
- Entrega landmarks compatibles con el alineamiento del reconocedor.
- Tiene una buena relacion entre velocidad y calidad.
- Puede ejecutarse mediante ONNX Runtime en CPU.
- Evita mantener un detector facial adicional incompatible con InsightFace.

### Como se utiliza

El adaptador esta en:

```text
backend/ia/adaptadores/insightface.py
```

Antes de aceptar una deteccion, Witcam evalua:

- Ancho y alto minimos.
- Confianza.
- Distancia visible entre los ojos.
- Posicion de nariz y boca.
- Simetria.
- Inclinacion y angulo facial.

Si la informacion no es suficiente, el rostro aparece como `No evaluable` y
no se genera inmediatamente una identidad desconocida.

### Limitaciones

- Puede perder rostros pequenos, borrosos, cubiertos o con angulos extremos.
- Detectar un patron facial parcial no garantiza que sea util para reconocer.
- SCRFD detecta el rostro, pero no sabe quien es.
- No es un detector especializado de capuchas ni mascaras.

## InsightFace

### Que hace

InsightFace alinea el rostro mediante los landmarks de SCRFD y genera un
embedding: un vector numerico que representa caracteristicas faciales.

```text
Rostro alineado
      |
      v
InsightFace
      |
      v
[0.12, -0.08, 0.31, ...]
```

Witcam normaliza los embeddings y calcula similitud mediante producto punto.
Al estar normalizados, esta operacion equivale a comparar su similitud
coseno.

### Por que se eligio

- Esta especializado en reconocimiento facial.
- Incluye deteccion y reconocimiento compatibles en una misma sesion.
- Produce embeddings reutilizables para multiples muestras.
- Permite comparar referencias sin volver a entrenar el modelo.
- Funciona con ONNX Runtime y puede ejecutarse en CPU.

Witcam carga `buffalo_l` solo con los modulos de deteccion y reconocimiento.
No carga edad, genero ni landmarks adicionales porque no son necesarios para
el proyecto.

### Galerias y comparacion

Las referencias se organizan por persona:

```text
referencias_reconocimiento/
  Matias/
    frontal.jpg
    perfil.jpg
```

Cada imagen genera un embedding. Para reconocer una identidad con varias
muestras, Witcam exige consenso:

- La mejor similitud debe superar el umbral principal.
- Una segunda muestra independiente debe superar un umbral secundario.

Una galeria con una sola muestra utiliza un umbral mas estricto. Esto reduce
la posibilidad de asignar un nombre por una unica coincidencia accidental.

### Frecuencia de reconocimiento

Generar embeddings es mas costoso que mantener una caja. Por eso InsightFace
no vuelve a reconocer en todos los ciclos:

```python
ConfiguracionRostro.reconocer_cada_n_detecciones = 6
ConfiguracionRostro.reconocer_cada_n_detecciones_sin_identidad = 3
```

Cuando existe un cuerpo sin identidad, Witcam reconoce con mayor frecuencia.
Cuando todos tienen identidad, reduce la frecuencia para ahorrar CPU.

### Limitaciones

- La similitud no es una certeza absoluta.
- Cambios de angulo, distancia, luz y resolucion afectan el embedding.
- Un rostro cubierto puede producir informacion insuficiente o incorrecta.
- InsightFace no reconoce correctamente a una persona si nunca tuvo una
  referencia facial valida.
- No debe utilizarse como unica evidencia para decisiones de alto impacto.

## ByteTrack

### Que hace

ByteTrack recibe cajas detectadas y mantiene IDs temporales entre frames:

```text
Frame 1: Persona ID 4
Frame 2: Persona ID 4
Frame 3: Persona ID 4
```

Witcam utiliza dos instancias independientes:

1. ByteTrack corporal sigue cajas producidas por YOLO.
2. ByteTrack facial sigue cajas producidas por SCRFD.

### Por que se eligio

- Es mas economico que ejecutar reconocimiento completo en cada frame.
- Mantiene continuidad mientras una persona se desplaza.
- Se integra con las detecciones de YOLO y SCRFD mediante Supervision.
- Tolera perdidas breves de deteccion.
- Permite asociar historial, candidatos e identidades a un ID temporal.

### Que no hace

ByteTrack no reconoce personas. Si alguien sale de escena y vuelve, puede
recibir un ID diferente. Witcam intenta recuperar continuidad usando:

- Posicion anterior.
- IoU entre cajas.
- Embedding facial.
- Tiempo desde la ultima observacion.
- Asociacion anterior entre rostro y cuerpo.

## Como interactuan YOLO y SCRFD

YOLO y SCRFD reciben el mismo frame, pero se ejecutan de forma independiente:

```text
                         +--> YOLO --> cajas corporales
Frame de la camara ------+
                         +--> SCRFD -> cajas faciales
```

La implementacion actual no usa la caja de YOLO para recortar el frame antes
de ejecutar SCRFD. La colaboracion ocurre despues de ambas detecciones.

Witcam intenta introducir cada caja facial dentro de una caja corporal. Para
aceptar la asociacion comprueba que:

- El centro del rostro este dentro del cuerpo.
- El rostro se encuentre en la zona superior del cuerpo.
- Una proporcion suficiente del rostro quede dentro de la caja corporal.
- La nueva asociacion sea claramente mejor antes de cambiar la anterior.

El resultado es una relacion temporal:

```text
Rostro ID 8 -> Persona ID 3
```

Si InsightFace reconoce `Rostro ID 8` como `Matias`, Witcam puede vincular:

```text
Persona ID 3 -> Matias
```

De esta forma, si SCRFD pierde momentaneamente la cara, YOLO y ByteTrack
corporal todavia pueden conservar la continuidad de `Persona ID 3`.

## Flujo completo de un frame

```text
1. Captura de video
        |
        v
2. YOLO detecta cuerpos cuando corresponde
        |
        v
3. ByteTrack corporal actualiza Persona ID
        |
        +----------------------------+
        |                            |
        v                            v
4. SCRFD detecta rostros      Persona sin rostro visible
        |
        v
5. Filtro de calidad facial
        |
        +--> No evaluable: esperar mejor observacion
        |
        v
6. ByteTrack facial actualiza Rostro ID
        |
        v
7. Asociacion Rostro ID -> Persona ID
        |
        v
8. InsightFace genera embedding cuando corresponde
        |
        v
9. Comparacion con galerias
        |
        +--> Oficial
        +--> Pendiente
        +--> Desconocido
        |
        v
10. Reglas de identidad, contradiccion y transferencia
        |
        v
11. Cajas, nombres, eventos y posibles capturas
```

## Identidad corporal y contradicciones

Una coincidencia facial aislada no asigna inmediatamente el nombre a un
cuerpo nuevo. Witcam exige confirmaciones y una similitud minima.

Cuando un cuerpo ya tiene nombre:

- Una observacion facial diferente aislada no reemplaza la identidad.
- Varias contradicciones pueden suspender temporalmente el nombre.
- La identidad no se transfiere a otro cuerpo activo sin evidencia
  suficientemente fuerte.
- Dos cuerpos activos no deben mostrar simultaneamente la misma identidad.

Estas reglas se encuentran en:

```text
backend/ia/identidades.py
```

## Oclusion

La oclusion se maneja como continuidad temporal, no como reconocimiento de
ropa o capuchas.

Si una persona ya fue reconocida y despues gira o cubre parte de su rostro,
Witcam puede mantener su identidad durante algunos segundos usando:

- ID corporal.
- ID facial.
- Ultima posicion.
- Ultimo embedding confiable.
- Historial de asociaciones.

Esto no permite identificar a alguien que entra por primera vez con el rostro
completamente cubierto. En ese caso YOLO puede detectar que existe una
persona, pero InsightFace no dispone de informacion suficiente para saber
quien es.

## Registro de desconocidos

Witcam no guarda un desconocido con una unica deteccion. Mantiene un candidato
temporal y exige:

- Tiempo minimo visible.
- Cantidad minima de observaciones.
- Tamano y calidad suficientes.
- Consistencia con el embedding semilla.
- Validacion final de SCRFD sobre el recorte.
- Ausencia de una coincidencia suficiente con galerias existentes.

Si el candidato esta asociado a un `Persona ID`, puede sobrevivir a cambios
del tracker facial. Las reglas se encuentran en:

```text
backend/ia/desconocidos.py
```

Las galerias pendientes admiten varias muestras. Una observacion nueva puede
agregarse si aporta una vista diferente, y puede reemplazar la peor muestra
cuando la galeria esta llena y su calidad es claramente superior.

## Por que no se utiliza un solo modelo

Utilizar solamente InsightFace provocaria perdida de contexto cada vez que no
se vea una cara. Utilizar solamente YOLO permitiria saber que hay personas,
pero no quienes son. Utilizar trackers sin detectores conservaria cajas, pero
no podria iniciar nuevas detecciones.

La division actual permite:

- YOLO: localizar personas.
- SCRFD: localizar rostros.
- InsightFace: comparar identidades.
- ByteTrack: mantener continuidad.
- Witcam: aplicar reglas de negocio y seguridad temporal.

Esta separacion tambien permite cambiar un proveedor sin reescribir todo el
sistema.

## Rendimiento

Los principales controles de carga son:

- Resolucion usada por SCRFD.
- Tamano de entrada de YOLO.
- Frecuencia de deteccion corporal.
- Frecuencia de generacion de embeddings.
- Resolucion y FPS enviados a la interfaz.
- Descarte de frames recibidos mientras la IA esta ocupada.

La IA analiza el frame disponible mas reciente. No intenta procesar una cola
completa de frames atrasados, porque eso produciria retraso acumulado.

## MobileNetV3-Small como posible extension

MobileNetV3-Small no esta implementada actualmente. Se ha propuesto como una
capa futura para clasificar la zona superior de una persona:

```text
rostro_visible
rostro_parcialmente_cubierto
rostro_cubierto
```

Necesitaria pesos entrenados o ajustados para esas categorias. El modelo
preentrenado generico no distingue encapuchados de forma confiable.

Una integracion segura seria:

```text
YOLO -> Persona ID -> recorte superior -> MobileNetV3-Small
                                      |
                                      +--> visible: permitir analisis facial
                                      +--> cubierto: marcar alerta
```

Inicialmente deberia funcionar solo como alerta y mediante una configuracion
opcional. No deberia cambiar ni borrar una identidad confirmada por una unica
clasificacion.

## Ubicacion del codigo

| Responsabilidad | Archivo |
| --- | --- |
| Configuracion y umbrales | `backend/config.py` |
| Protocolos de modelos | `backend/ia/interfaces.py` |
| Adaptador InsightFace/SCRFD | `backend/ia/adaptadores/insightface.py` |
| Adaptador YOLO | `backend/ia/adaptadores/yolo.py` |
| Adaptador ByteTrack | `backend/ia/adaptadores/bytetrack.py` |
| Pipeline completo | `backend/ia/pipeline.py` |
| Identidades corporales | `backend/ia/identidades.py` |
| Candidatos desconocidos | `backend/ia/desconocidos.py` |
| Referencias faciales | `backend/galerias/referencias.py` |
| Muestras de galerias | `backend/galerias/muestras.py` |
| Coordinacion de video | `backend/video/motor.py` |

## Resumen

Witcam combina modelos especializados en lugar de pedirle todo a una sola IA:

```text
YOLO + ByteTrack corporal = donde esta la persona
SCRFD + ByteTrack facial  = donde esta su rostro
InsightFace               = a quien se parece
Reglas de Witcam          = que identidad es seguro mostrar
```

El reconocimiento final no depende solamente de una similitud facial. Tambien
considera calidad, tiempo, posicion, continuidad corporal, contradicciones y
estado de las galerias.
