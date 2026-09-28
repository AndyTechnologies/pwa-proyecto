# ADR-007 — Bootstrap 5.3.8, con los assets vendorizados en el repositorio

Estado: aceptada.

## Contexto

La consigna del trabajo final **exige Bootstrap 5** como base del diseño
("sitio web estático basado en Bootstrap 5 como prototipo de diseño"). La versión
fijada en el proyecto es 5.3.8, con licencia MIT.

Los archivos están **vendorizados localmente**: `static/css/bootstrap.min.css` y
`static/js/bootstrap.bundle.min.js`. `STATICFILES_DIRS` apunta a `BASE_DIR /
'static'`, y las plantillas los referencian con `{% static %}`. No hay ninguna
referencia a un CDN en las plantillas.

Decisión de subcosto asociada: Bootstrap **no** figura en `requirements.txt` ni en
`pyproject.toml`, porque es un asset estático y no una dependencia de Python; su
actualización es una sustitución manual de archivos.

## Problema

Hay dos decisiones que tomar y conviene no mezclarlas. La primera es qué
librería de estilos y componentes usar, es decir el diseño. La segunda es de dónde
servir sus archivos: el propio repositorio o un CDN. La primera está impuesta por
la consigna; la segunda es abierta y tiene consecuencias de funcionamiento,
privacidad y mantenimiento.

También hay una consecuencia técnica de usar Bootstrap con formularios de Django que
conviene documentar aquí, porque proviene directamente de esta decisión: las clases
CSS del widget se asignan en `TaskForm.__init__`.

## Opciones consideradas

1. **Bootstrap 5.3.8, con los assets vendorizados en `static/`** (opción
   adoptada; incluye la sub-decisión de no usar CDN).
2. **CSS propio**, escrito a medida para el proyecto, sin framework.
3. **Tailwind CSS** u otro framework utility-first.
4. **Materialize** u otra biblioteca de componentes con su propio lenguaje visual.

Para la sub-decisión de servido: **CDN** frente a **vendorizado local**.

## Decisión

Se adopta la **opción 1: Bootstrap 5.3.8, assets vendorizados localmente**.

**Motivo normativo.** La consigna exige Bootstrap 5. La decisión está cerrada, y
las opciones 2, 3 y 4 no compiten en igualdad de condiciones: son incumplimientos
del enunciado. Se documentan igualmente porque el proyecto debe poder explicar
por qué la elección no es casual.

**Motivo complementario.** Bootstrap resuelve de forma inmediata los componentes
que las plantillas necesitan —barra de navegación, formularios, tarjetas, alertas
para los mensajes del sistema, tablas y utilidades responsivas de la rejilla— con
un lenguaje visual único y con clases de accesibilidad ya resueltas. Escribir eso a
mano o elegir otro framework significa reimplementar o volver a aprender un sistema
completo de componentes.

### Sub-decisión: vendorizar los assets en lugar de usar un CDN

Los archivos de Bootstrap se guardan en `static/` y se sirven desde la propia
aplicación.

**Beneficios**

- La aplicación funciona sin conexión: no depende de la disponibilidad de un
  tercero para renderizar la interfaz.
- No hay peticiones a terceros desde el navegador, lo que evita filtrar la IP del
  visitante a un proveedor externo y elimina una dependencia de red del recorrido
  de usuario.
- El comportamiento es idéntico en las dos rutas de instalación soportadas
  (`pip` y `uv`): ninguna necesita acceso a Internet en un paso que la otra no
  necesite, y lo que se ve en desarrollo es lo que se ve en la entrega.
- La versión queda fijada y explícita en el repositorio: no se depende de lo que
  sirva el CDN ese día.

**Costos**

- Los archivos vendorizados hay que **actualizar manualmente**: una nueva versión
  de Bootstrap no llega por `pip` ni por `uv`, y requiere descargar y sustituir los
  archivos por alguien. El riesgo de desincronización entre la versión de los
  assets y la documentada es real si nadie lo recuerda.
- Los archivos vendorizados aumentan el tamaño del repositorio y aparecen en
  cualquier revisión o diff, aunque los cambios sean del framework y no del
  proyecto.
- No se puede aprovechar una mejora del CDN sin cambiar el repositorio.
- El proyecto queda atado a una versión concreta (5.3.8) y a esa versión hay que
  declararla en la documentación.

### Consecuencia sobre los formularios: las clases se asignan en Python

Bootstrap no se aplica a un widget de Django por sí solo. La solución del proyecto
es `TaskForm.__init__`, que recorre `self.fields.values()` y asigna `form-control`
a los widgets de texto, `form-select` a los `Select` y `form-check-input` a los
`CheckboxInput`, conservando las clases que el widget ya tuviera.

Se hace así, y no desde la plantilla, por dos razones concretas:

1. **Django no ofrece una forma de fijar atributos de un widget desde una
   plantilla.** Un widget se renderiza con sus atributos definidos en el
   formulario; escribir `class="form-control"` en el HTML de la plantilla no
   reemplaza los atributos del campo renderizado, produce HTML duplicado o
   inválido, y no es un mecanismo soportado.
2. **`django-widget-tweaks` se evaluó y se descartó** como dependencia no
   justificada: resuelve exactamente este problema con un `tag` en la plantilla,
   pero añade una dependencia, una forma nueva de escribir formularios y una
   superficie que mantener a cambio de un recorrido de unas pocas líneas en el
   propio `ModelForm`.

Esta asignación centralizada tiene un efecto secundario favorable: la apariencia
de los formularios es uniforme por construcción, y no depende de que cada
plantilla se acuerde de añadir la clase.

## Consecuencias

**Beneficios**

- Requisito de la consigna cumplido, con la versión declarada.
- Interfaz completa sin código de estilos propio: no hay CSS propio que mantener.
- Componentes accesibles de fábrica y un lenguaje visual consistente en todas las
  plantillas.
- La interfaz funciona sin conexión y sin peticiones a terceros.
- Comportamiento idéntico entre las dos rutas de instalación del proyecto.
- Las clases de los widgets se aplican en un único sitio, por lo que los
  formularios son uniformes y no dependen de cada plantilla.
- Cero dependencias de Python asociadas al diseño.

**Costos**

- **La actualización de Bootstrap es manual** y no llega por el gestor de
  paquetes. Si no se recuerda, la versión de los assets puede divergir de la
  documentada.
- Los archivos vendorizados añaden peso al repositorio y ensucian revisiones.
- Sin CDN no se aprovechan correcciones servidas por el proveedor ni degradaciones
  controladas de forma externa.
- **La dependencia visual es total.** Personalizar el aspecto implica apartarse de
  las clases de Bootstrap o sobrescribir CSS, lo que suma mantenimiento sobre un
  sistema que no se diseñó para eso.
- La apariencia de los formularios depende de Python, no de las plantillas. Quien
  solo lea `templates/` no ve de dónde salen las clases, y un cambio de estilo
  exige tocar el formulario, no solo la plantilla.
- Las clases se asignan por tipo de widget en el `__init__`; un widget nuevo
  recibe la clase por defecto sin que nadie lo revise, y ese es el punto donde una
  inconsistencia visual podría colarse sin aviso.

## Alternativas descartadas

**CSS propio (opción 2).** Se descarta por dos razones concretas. La primera es
normativa: la consigna exige Bootstrap. La segunda es de coste: un sistema visual
completo (rejilla responsiva, componentes de formulario, navegación, alertas,
estados de foco y validación) es una cantidad de trabajo de CSS y de
mantenimiento que este proyecto no puede justificar, sobre todo cuando la
alternativa exigida ya existe y es estable. La consecuencia sería peor que
ausencia de framework: estilos propios que habría que revisar y mantener por su
cuenta, con menos componentes resueltos.

**Tailwind CSS (opción 3).** Se descarta por el mismo motivo normativo y por uno
técnico concreto: Tailwind resuelve el estilo desde el HTML con clases
utility-first, lo que es incompatible con el criterio de la consigna de usar las
clases de Bootstrap 5 y con la reutilización de sus componentes. Además exigiría
integrar un paso de compilación de assets en el proyecto, que hoy tiene una ruta de
instalación de Python y un servidor de estáticos de Django sin paso de compilación. La
ventaja real de Tailwind —cero CSS propio por escribir— es irrelevante en un
proyecto que no quiere escribir CSS propio sino usar un framework prescrito.

**Materialize u otra biblioteca de componentes (opción 4).** Se descarta por la
misma razón normativa y porque introducir una segunda biblioteca de componentes
introduciría además un conflicto de vocabulario visual: reglas de Bootstrap y de
Materialize conviviendo en las mismas plantillas, con resultados distintos según
qué componente se use. Entre dos bibliotecas competidoras, la consigna ya designó
cuál.

**Servir Bootstrap desde un CDN (sub-decisión).** Se descarta porque cambia
condiciones que en este proyecto importan. Una instalación en una red sin salida
a Internet, o el uso de la aplicación sin conexión, dejarían la interfaz sin
estilos; las dos rutas de instalación dejarían de ser equivalentes; y cada carga
de página añadiría una petición a un tercero, con la huella de red del visitante
que eso implica. El beneficio que sí aporta —recibir actualizaciones sin tocar el
repositorio— es menor que el de no depender de un tercero para que la aplicación
se vea, y el coste de perderlo está contenido: actualizar los assets es una
operación manual acotada.
