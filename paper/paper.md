# Task Manager: una aplicación web de gestión de tareas con control de visibilidad y propiedad, construida sobre Django y Bootstrap 5

## Resumen

Este trabajo presenta el diseño y la implementación de una aplicación web de gestión
de tareas personales y profesionales, developed sobre Django 6.1.1 con Django
Templates, el ORM de Django y Bootstrap 5.3.8 como sistema visual, sobre SQLite como
base de datos de desarrollo.

El problema central no era la gestión de tareas en sí, sino el control de acceso a
ellas. Una aplicación de tareas típica permite que cada usuario gestione lo suyo, pero
la consigna académica exigía además un modelo de visibilidad de tres niveles —privada,
compartida con usuarios registrados y pública— sin que la visibilidad otorgara jamás
permisos de escritura. Este requirement es el queorganiza la arquitectura completa.

La decisión estructural del proyecto fue centralizar las dos políticas de autorización
—lectura y escritura— en el `QuerySet` del modelo `Task`, en lugar de distribuirlas
entre las vistas. Ninguna vista puede reinterpretar las reglas porque todas consultan el
mismo método, y una tarea ajena nunca llega a cargarse en memoria: responde 404 y no
403, de modo que el sistema tampoco confirma indirectamente que esa tarea existe.

El proyecto se entrega con 249 pruebas automatizadas, todas en verde, que cubren la
matriz completa de autorización actor por visibilidad, las listas blancas de
ordenamiento y filtrado frente a intentos de inyección, y siete pruebas de regresión
derivadas de defectos reales detectados durante el desarrollo. Se documentan ocho
decisiones arquitectónicas en sus registros correspondientes.

## Palabras clave

django, aplicación web, control de acceso, visibilidad, vistas basadas en clases, bootstrap 5, pruebas automatizadas, arquitectura mvt

## 1. Introducción

### 1.1 Contexto

La gestión de tareas es, probablemente, el caso de uso másinctamente repetido en los
proyectos de programación web de introductory. Almost todas las herramientas de gestión
de tareas que se usan a diario —un tablero de trabajo, una lista de pendientes, un
calendario de entregas— comparten una misma estructura conceptual: un conjunto de
elementos con un título, una descripción, una fecha y una importancia relativa, que
pertenece a alguien y que puede completarse.

Lo que distingue a una aplicación de gestión de tareas de un simple ejercicio de
formulario es la pregunta de **quién puede ver y quién puede tocar cada elemento**. En
un contexto individual, esa pregunta es trivial: todo es mío. En cuanto aparecen otros
usuarios, la pregunta deja de ser trivial, y las respuestas posibles se multiplican.
¿Puede un usuario ver la tarea de otro? ¿Puede verla pero no modificarla? ¿Puede un
visitante que ni siquiera tiene cuenta ver algo? ¿Qué debería pasar cuando alguien
intenta adivinar una dirección de una tarea que no le pertenece?

### 1.2 Problema

El trabajo parte de una consigna académica que especifica ocho requisitos funcionales y
dos restricciones duras. Los requisitos cubren la gestión de tareas, el diseño
responsive, la ordenación, el filtrado, las etiquetas, la autenticación, la propiedad de
los datos y la visibilidad. Las restricciones son dos: no puede utilizarse Django REST
Framework, y todas las vistas deben ser clases.

Entre los ocho requisitos, el séptimo es el que concentra la dificultad real:

> El usuario puede hacer visible sus tareas (solo lectura) a otros usuarios o de manera
> pública (usuario anónimo).

Este requisito introduce un modelo de acceso que no es el habitual. En la mayoría de
las aplicaciones, la visibilidad es un interruptor binario: privada o pública. Aquí la
consigna pide un modelo de tres niveles, y —esto es lo que suele pasarse por alto— pide
además que compartir una tarea no implique poder modificarla. Un usuario externo puede
leer una tarea compartida, pero no puede editarla, borrarla, completarla ni cambiarle
las etiquetas.

Las restricciones duras no son un obstáculo administrativo. La prohibición de Django
REST Framework elimina la tentación de construir una API y, con ella, la tentación de
duplicar la validación que el sistema de formularios ya resuelve. La exigencia de vistas
basadas en clases elimina la de resolver cada vista como mejor parezca y obliga
a un diseño de composición coherente.

### 1.3 Objetivos

**Objetivo general.** Construir una aplicación web de gestión de tareas que permita a
cada usuario administrar sus propias tareas y decidir su grado de exposición, sobre una
arquitectura que haga las reglas de acceso explícitas, verificables y demostrables.

**Objetivos específicos.**

1. Modelar el dominio de tareas y etiquetas con integridad referencial correcta.
2. Implementar un modelo de visibilidad de tres niveles en el que la visibilidad nunca
   otorgue permisos de escritura.
3. Centralizar la autorización en un único lugar del código, de modo que ninguna vista
   pueda implementar su propia interpretación de las reglas.
4. Proteger el sistema frente a la manipulación de identificadores y de parámetros de
   consulta, verificándolo con pruebas automatizadas y no con argumentos.
5. Entregar una interfaz responsive que funcione de manera aceptable desde un teléfono
   de 360 píxeles hasta una pantalla de escritorio.
6. Documentar las decisiones arquitectónicas, incluidas las alternativas descartadas y
   los costos asumidos.

### 1.4 Alcance

El alcance cubre el ciclo completo de vida de una tarea —creación, edición, borrado y
completado—, su consulta con ordenamiento y filtrado, su etiquetado, su exposición a
terceros y la administración por el sitio de administración de Django.

Quedan explícitamente fuera del alcance, por decisión propia y no por omisión: una API
programática, el envío de notificaciones por correo, la paginación de listados, el
borrado lógico, la restricción de fechas de vencimiento en el pasado, la
internacionalización de la interfaz y el modo oscuro. Estas omisiones se justifican
en la sección 12.

## 2. Requisitos del sistema

### 2.1 Requisitos funcionales

| ID | Requisito | Origen en la consigna |
| --- | --- | --- |
| RF-01 | Un visitante puede registrarse con nombre de usuario, contraseña y su confirmación. | Requisito 5 |
| RF-02 | Existen inicio de sesión y cierre de sesión. Las áreas privadas exigen autenticación. | Requisito 5, 6 |
| RF-03 | Un usuario autenticado crea tareas con título, descripción, fecha de vencimiento y prioridad. | Requisito 2 |
| RF-04 | El propietario edita exclusivamente sus propias tareas. | Requisito 2, 6 |
| RF-05 | El propietario elimina exclusivamente sus propias tareas. | Requisito 2, 6 |
| RF-06 | El propietario marca una tarea como completa o la devuelve a pendiente. | Requisito 2 |
| RF-07 | El propietario ve un listado de sus tareas con título, descripción resumida, fecha, prioridad, estado, etiquetas y visibilidad. | Requisito 2, 3 |
| RF-08 | El listado puede ordenarse por fecha de vencimiento o por prioridad. | Requisito 3 |
| RF-09 | El listado puede filtrarse por estado: todas, pendientes o completadas. | Requisito 3 |
| RF-10 | Una tarea admite cero, una o varias etiquetas; una etiqueta se reutiliza entre tareas. | Requisito 4 |
| RF-11 | El usuario localiza tareas por etiqueta. | Requisito 4 |
| RF-12 | Cada tarea tiene un nivel de visibilidad: privada, compartida o pública. | Requisito 7 |
| RF-13 | Un visitante anónimo puede ver una tarea pública, solo en lectura. | Requisito 7 |
| RF-14 | Un usuario autenticado que no es propietario puede ver una tarea compartida, solo en lectura. | Requisito 7 |

### 2.2 Requisitos no funcionales

La consigna no enumera una sección de requisitos no funcionales, pero se deducen de sus
exigencias de diseño responsive, buenas prácticas, validación y seguridad.

| ID | Requisito | Verificación |
| --- | --- | --- |
| RNF-01 | La aplicación es usable en móvil, tablet y escritorio. | Inspección a 360, 768 y 1440 px |
| RNF-02 | La navegación es clara y las acciones disponibles son discoveribles. | Inspección |
| RNF-03 | Los recursos privados no quedan expuestos. | 45 pruebas de permisos |
| RNF-04 | Los datos se validan en el servidor antes de persistirse. | 56 pruebas de formularios |
| RNF-05 | La arquitectura separa modelos, vistas, formularios, plantillas, estáticos y pruebas. | Estructura del repositorio |
| RNF-06 | Las reglas críticas son comprobables automáticamente. | 249 pruebas |
| RNF-07 | Bootstrap 5 provee un sistema visual coherente. | Inspección |
| RNF-08 | HTML semántico, etiquetas asociadas a los campos y contraste razonable. | Inspección |
| RNF-09 | Las contraseñas nunca se almacenan en texto plano. | Validadores de Django |
| RNF-10 | Cada requisito funcional se puede relating con su implementación y su prueba. | `docs/traceability.md` |
| RNF-11 | La arquitectura y las decisiones relevantes están documentadas. | `docs/`, 8 ADR |
| RNF-12 | No se introducen componentes ni dependencias innecesarias. | Auditoría de dependencias |

### 2.3 Restricciones

1. **No se permite Django REST Framework.** La aplicación es server-rendered; no existe
   capa de API.
2. **Todas las vistas deben ser Vistas Basadas en Clases.** No hay ni una sola vista
   basada en función.
3. **El trabajo se entrega en cuatro cortes**: prototipo estático con Bootstrap en la
   semana 3, proyecto configurado con modelos y administración en la semana 5,
   enrutamientos, vistas y autenticación en la semana 7, y entrega final con plantillas
   y formularios propios en la semana 9.
4. **Bootstrap 5** es obligatorio como base del diseño visual.

## 3. Análisis del problema

### 3.1 Actores

El sistema contempla cuatro actores, que se distinguen por su relación con una tarea
concreta más que por sus permisos globales.

**El visitante anónimo** es quien no ha iniciado sesión. No puede crear ni modificar
nada. Su única capacidad es leer tareas públicas. Es un actor de primera clase, no una
excepción: la consigna exige que el acceso público exista, y la aplicación debe ser
usable sin obligar a registrarse.

**El usuario autenticado** ha demonstrated su identidad pero no es necesariamente el
dueño de la tarea que está mirando. Este es el actor que suele olvidarse en el diseño,
y es la fuente habitual de las vulnerabilidades de referencia directa a objeto
inseguro. Puede crear sus propias tareas, gestionarlas, y leer las tareas que otros le
compartieron.

**El propietario** es el usuario autenticado respecto de una tarea propia. Solo él
puede modificarla. Ningún otro rol, por privileged que sea, cambia esta regla: el
administrador del sitio de administración de Django es un concepto distinto y separado.

**El no propietario** es la intersección de los dos anteriores: está autenticado y está
viendo la tarea de otro. Su capacidad es estrictamente de lectura. Este rol es el que
da sentido a la palabra "solo lectura" del requisito 7.

### 3.2 Ejemplo trabajado

Supongamos dos usuarios, Ana y Bruno, y tres tareas de Ana.

Ana tiene una tarea **privada** —el borrador de un informe—, una tarea **compartida** —
el plan de una reunión de equipo— y una tarea **pública** —una lista de lecturas
recomendadas—.

- Ana ve las tres, y sobre las tres puede leer, editar, completar, eliminar y cambiar su
  visibilidad.
- Bruno, que está autenticado, ve la compartida y la pública. Sobre ambas puede
  únicamente leer. Si escribe a mano la dirección de la tarea privada de Ana en la barra
  de direcciones, obtiene una respuesta 404: el sistema no le dice que la tarea existe ni
  que le está prohibiting el acceso; simplemente no encuentra nada.
- Un visitante anónimo ve únicamente la pública, y solo puede leerla.

Lo que este ejemplo revela es la propiedad estructural del diseño: **la visibilidad es
una propiedad de la lectura, nunca de la escritura**. El mismo usuario, en el mismo
instante, puede tener permiso de lectura y no tenerlo de escritura sobre el mismo objeto.
Esa asimetría es exactamente lo que el requisito 7 pide y lo que una única bandera
"público" no puede expresar.

### 3.3 Entidades

**Usuario.** No se define un modelo propio: se utiliza el modelo de usuario de
`django.contrib.auth`. La consigna no pide datos de perfil adicionales, y crear un modelo
propio obligaría a duplicar mechanisms de autenticación que Django ya resuelve y prueba.

**Tarea.** Es la entidad central. Se deservingreno exactamente un propietario y
tiene cuatro campos exigidos por la consigna —título, descripción, fecha de vencimiento
y prioridad— más los que el dominio necesita para funcionar: propietario, estado de
completado, nivel de visibilidad, etiquetas, y dos marcas temporales de creación y
actualización.

**Etiqueta.** Es una etiqueta de texto libre que puede compartirse entre muchas tareas.
No tiene propietario, porque una tarea compartida necesita mostrar sus etiquetas a quien
la lee, y una etiqueta con dueño impediría eso.

### 3.4 Autenticación y autorización como conceptos distintos

Conviene separar dos conceptos que a menudo se confunden.

La **autenticación** responde a "¿quién sos?". La **autorización** responde a
"¿qué podés hacer con esto?". Son independientes: un usuario puede estar perfectamente
autenticado y, aun así, no tener permiso sobre un recurso concreto.

La consigna exige autenticación en el punto 5 y control de propiedad en el punto 6, y
son problemas de naturaleza distinta. Confundirlos —por ejemplo, confiar en que "ya está
autenticado, entonces puede editar"— es exactamente el error que produce una
vulnerabilidad de referencia directa a objeto inseguro.

## 4. Arquitectura

### 4.1 Por qué Django

Django fue elegido por dos razones que conviene distinguir, porque a menudo se confunden.

La primera es normativa: la consigna exige explícitamente trabajar con Django. Cualquier
otra consideración es secundaria frente a este hecho.

La segunda es técnica, e independiente de la primera. Django resuelve de forma integrada
cinco problemas que este proyecto necesita: el mapeo objeto-relacional, la autenticación
con almacenamiento seguro de contraseñas, el sistema de formularios con validación, el
sitio de administración, y el renderizado en el servidor. Cruzar esos cinco problemas con
bibliotecas separadas habría producido una aplicación donde buena parte del esfuerzo
se dedicaría a hacer que las piezas se entendieran entre sí. La integración es lo que
permite que el núcleo del proyecto —la lógica de autorización— ocupe una proporción
razonable del código.

También es importante decir por qué Django **no** fue la elección natural para todo. La
combinación de la restricción contra Django REST Framework con el perfil server-rendered
de la aplicación es deliberada: sin capa de API, el sistema tiene una única forma de
entrada y, en consecuencia, un único lugar donde la autorización debe aplicarse.

### 4.2 Qué significa MVT/MTV

Django sigue un patrón derivado del modelo de vista-controlador, con una sustitución
del controlador por un enrutador con ciclo de vida gestionado. En la práctica:

- **Model**: la capa de datos. Describe qué es una tarea, qué campos tiene, qué
  relaciones la unen a otras entidades y qué reglas se garantizan a nivel de base de
  datos.
- **View**: la capa de lógica de petición. Recibe una petición, decide qué hacer, y
  entrega un contexto.
- **Template**: la capa de presentación. Describe cómo se ve, nunca qué está permitido.

La distinción relevante para este proyecto es que **template y view no comparten
responsabilidades sobre la seguridad**. Un template decide qué botones dibujar; una view
decide si la operación procede. La plantilla no es un mecanismo de control.

### 4.3 Monolito modular

```mermaid
graph TD
    Browser[Navegador] -->|petición HTTP| URLs
    subgraph config[config — proyecto Django]
        URLs[config/urls.py — enrutado]
    end
    subgraph tasks[tasks — aplicación de dominio]
        Views[tasks/views.py<br/>9 Vistas Basadas en Clases]
        Forms[tasks/forms.py<br/>TaskForm, RegisterForm]
        Models[tasks/models.py<br/>Task, Tag]
        QS[TaskQuerySet<br/>owned_by / visible_to]
        Admin[tasks/admin.py]
    end
    URLs --> Views
    Views --> Forms
    Views --> Models
    Models --> QS
    Views -->|render| Tpl[templates/]
    Tpl -->|HTML| Browser
    Admin --> Models
    Models --> DB[(SQLite)]
```

El proyecto es un **monolito modular**: un único proceso y una única base de datos,
divididos internamente en módulos con responsabilidades delimitadas. La alternativa
—microservicios— fue descartada. Un microservicio resuelve problemas de escalado
independiente y de despliegue independiente, y este sistema no tiene ninguno de los dos:
su carga es la de una aplicación de aula, y su dominio es una sola operación coherente
—gestionar tareas— que no gana nada al partirse. La architectónicamente correcta para
este problema es un monolito.

También se descartaron CQRS y Event Sourcing, que introducen complejidad de
consistencia eventual y de versionado de eventos a cambio de beneficios de auditoría y
escalado que este proyecto no necesita. Y se descartó una aplicación de "arquitectura
limpia" con capas y puertos que, en un proyecto de este tamaño, habría separado el
código de la lógica real sin aportar Testabilidad adicional: la lógica ya es testeable
porque está concentrada y sin dependencias de infraestructura.

### 4.4 Ciclo de vida de una petición

```mermaid
sequenceDiagram
    participant U as Usuario
    participant U_ as config/urls.py
    participant V as TaskListView
    participant Q as TaskQuerySet
    participant DB as Base de datos
    participant T as task_list.html

    U->>U_: GET /tasks/?status=pending&sort=priority
    U_->V: dispatch() con LoginRequiredMixin
    alt no autenticado
        V-->>U: 302 a /login/
    else autenticado
        V->>V: get_queryset()
        V->>Q: owned_by(request.user)
        Q->>DB: SELECT ... WHERE owner = ?
        DB-->>Q: filas
        V->>V: filtro de estado contra STATUS_FILTERS
        V->>V: filtro de etiqueta si ?tag= es válido
        V->>V: orden contra ALLOWED_SORTS + desempate -pk
        V->>T: render(context)
        T-->>U: HTML 200
    end
```

El recorrido de `GET /tasks/?status=pending&sort=priority` es el siguiente:

1. **Enrutado.** `config/urls.py` incluye `tasks.urls` bajo el prefijo `/tasks/`, y el
   enrutador resuelve el patrón hacia `TaskListView`.
2. **Autenticación.** `LoginRequiredMixin` intercepta la petición antes de ejecutar
   nada. Si no hay sesión, redirige a la pantalla de inicio de sesión. La comprobación
   ocurre en este punto, no al final.
3. **Restricción de propiedad.** `get_queryset()` comienza siempre por
   `Task.objects.owned_by(self.request.user)`. Esta es la primera línea del método y no
   es opcional: garantiza que ninguna tarea ajena entre en la cadena de procesamiento.
4. **Filtrado por estado.** El valor de `?status=` se busca como clave en
   `STATUS_FILTERS`. Si no está en el diccionario, se sustituye por el valor por defecto.
   El valor crudo del usuario nunca se entrega al ORM.
5. **Filtrado por etiqueta.** Si `?tag=` está presente, se convierte a slug y se filtra
   por `tags__slug`.
6. **Ordenamiento.** El valor de `?sort=` se busca como clave en `ALLOWED_SORTS`, que
   devuelve una lista de campos del ORM, no un nombre de campo tomado del input. A todo
   ordenamiento se le añade `-pk` como criterio secundario.
7. **Renderizado.** El contexto incluye las tareas y los tres parámetros activos, para
   que la plantilla pueda mostrar qué filtros están aplicados.

El orden de los pasos importa. La restricción de propiedad es la primera porque es la
única que no admite excepción; el ordenamiento es el último porque opera sobre un
conjunto ya acotado.

## 5. Diseño del dominio

### 5.1 Modelo de datos

```mermaid
erDiagram
    User ||--o{ Task : "posee (1:N)"
    Task }o--o{ Tag : "etiquetada con (N:M)"

    User {
        int id PK
        string username
        string password "hash, nunca texto plano"
    }

    Task {
        int id PK
        int owner_id FK
        string title
        text description
        date due_date
        int priority "1=Baja 2=Media 3=Alta"
        boolean completed
        string visibility "private|authenticated|public"
        datetime created_at
        datetime updated_at
    }

    Tag {
        int id PK
        string name UK
        string slug UK
        datetime created_at
    }
```

### 5.2 Cardinalidades y propiedad

La relación entre usuario y tarea es de uno a muchos: un usuario puede tener muchas
tareas, y una tarea pertenece **exactamente** a un usuario. Esa Cardinalidad no es
decorativa; es la que hace que la propiedad sea una propiedad y no un atributo opcional.
No existe el caso "tarea sin dueño", porque el campo es obligatorio y la base de datos lo
garantiza.

La relación entre tarea y etiqueta es de muchos a muchos: una tarea puede tener varias
etiquetas, y una etiqueta puede estar asociada a muchas tareas. Se implementa con el
campo `ManyToManyField`, que Django materializa como una tabla intermedia.

### 5.3 Elección de tipos

**Prioridad: entero.** La prioridad tiene tres niveles con un orden semántico
—baja, media, alta— y ese orden debe coincidir con el orden de la base de datos. Al
almacenarla como entero, `ORDER BY priority` ya devuelve el orden correcto, sin tabla
auxiliar de equivalencias y sin función de ordenación en Python. Si se almacenara como
cadena, el orden alfabético de las etiquetas no coincidiría con el orden semántico y
habría que corregirlo en cada consulta.

**Visibilidad: cadena.** La visibilidad no tiene orden, tiene identidad semántica. El
valor `"private"` es más legible en una consola de administración de base de datos, en
un registro de errores y en una URL de depuración que el valor `1`. Además, permite
añadir un nuevo nivel sin migrar los datos existentes, siempre que la longitud del campo
lo admita.

### 5.4 Índices

Se definieron dos índices compuestos:

- **`(owner, due_date)`** porque la consulta dominante del sistema es "mis tareas
  ordenadas por vencimiento", que filtra por propietario y ordena por fecha. Un índice
  compuesto cubre el filtro y evita el ordenamiento en memoria.
- **`(visibility)`** porque las lecturas públicas filtran por ese campo sobre el
  conjunto completo, sin restricción de propietario.

Añadir índices es un compromiso: aceleran las lecturas y ralentizan las escrituras, y
ocupan espacio. Se añadieron únicamente los que corresponden a las dos consultas que el
sistema ejecuta de verdad, no índices preventivos.

### 5.5 Ordenamiento determinista

El ordenamiento por fecha de vencimiento tiene una ambigüedad natural: dos tareas pueden
compartir la misma fecha. Si el ordenamiento quedara indefinido, el resultado de la misma
consulta podría cambiar entre peticiones, lo que se manifiesta como tareas que "saltan"
de posición al recargar.

La solución es añadir un criterio secundario. En este proyecto, el orden por defecto es
`["due_date", "priority", "-pk"]` y todo ordenamiento solicitado por el usuario se le
concatena `-pk`. Como la clave primaria es única, la combinación de fecha, prioridad y
clave primaria no puede tener empates, y el resultado es estable.

Este detalle parece menor y no lo es: sin él, cualquier prueba de ordenamiento que
comparara listas completas sería intermitente, y la propia interfaz mostraría un
comportamiento que nadie podría reproducir.

### 5.6 Las políticas como invariantes del dominio

Las dos reglas de acceso del sistema están expresadas como métodos del `QuerySet` del
modelo, no como condiciones dispersas en las vistas:

- **`owned_by(user)`** — política de escritura. Devuelve únicamente las tareas cuyo
  propietario es el usuario dado.
- **`visible_to(user)`** — política de lectura. Devuelve las tareas que el usuario puede
  abrir: para un anónimo, solo las públicas; para un autenticado que no es propietario,
  las compartidas y las públicas; para el propietario, todas las suyas.

La razón de que vivan aquí, y no en las vistas, es que una vista no puede entonces
implementar su propia idea de quién puede ver qué. Si las reglas estuvieran escritas en
cada vista, cada vista nueva sería una nueva oportunidad de equivocarse, y nadie podría
auditar la corrección del sistema leyéndolas todas.

## 6. Seguridad

La seguridad es un requisito de primer nivel de la consigna, y en este proyecto se
concentra en un problema: **impedir que un usuario alcance un recurso que no le
pertenece**.

### 6.1 Referencia directa a objeto inseguro

El ataque más relevante contra una aplicación de este tipo se conoce como *Insecure
Direct Object Reference*, o IDOR. Consiste en Replace un parámetro de la URL.

La aplicación expone rutas como `/tasks/14/edit/`. El número `14` es un identificador
consecutivo, y un atacante que adivine o enumere números puede intentar abrir rutas
ajenas. El nombre completo de esta vulnerabilidad es engañoso: la referencia no es
directa en un sentido estricto; lo relevante es que el servidor confía en un
identificador que el cliente controla y no comprueba a quién pertenece.

La defensa se aplica en dos niveles.

**En el queryset.** Las vistas mutables no preguntan "¿cuál es la tarea con este
identificador?", sino "¿cuál es la tarea con este identificificador **y este
propietario**?":

```python
def get_queryset(self):
    return Task.objects.owned_by(self.request.user)
```

Como la restricción forma parte de la consulta, una tarea ajena simplemente no aparece
en el conjunto de resultados. La vista no llega a construir el objeto, y por lo tanto no
llega a procesarlo.

**En la vista.** Las vistas que usan `get_object_or_404` con un queryset ya restringido
heredan la misma protección sin trabajo adicional. La clase `TaskCompleteToggleView`, que
alterna el estado de completitud, lo hace explícito:

```python
task = get_object_or_404(Task.objects.owned_by(request.user), pk=pk)
```

### 6.2 Por qué 404 y no 403

Cuando un usuario solicita un recurso que existe pero sobre el que no tiene permiso, hay
dos respuestas razonables: `403 Forbidden`, que significa "existe pero no te lo
permitimos", y `404 Not Found`, que significa "no hay nada aquí".

Este sistema devuelve **404 deliberadamente**, y la razón es la fuga de información.
Con un 403, un atacante que recorre identificadores obtiene una señal valiosísima: sabe
que la tarea 14 existe aunque no pueda leerla. La densidad y el rango de tareas de cada
usuario se convierten en información observable. Con un 404, el atacante no puede
distinguir entre un identificador que no existe y uno que existe pero no le pertenece, y
el sistema no confirma nada.

El costo de esta decisión es que se pierde una distinción útil para depurar: un
desarrollador que pruebe una URL incorrecta verá un 404 idéntico al de un problema de
permisos. Es un costo aceptable, y está registrado como tal en el registro de decisión
correspondiente.

### 6.3 Separación entre lectura y escritura

El sistema no asocia "visible" con "editable". Son dos ejes independientes, y el modelo
los separa de forma explícita: `visible_to()` gobierna la lectura, `owned_by()` gobierna
la escritura, y ninguna ruta de escritura consulta `visible_to()`.

Una consecuencia práctica: una tarea pública sigue siendo editable **solo** por su
propietario. Que un desconocido pueda verla no le acerca un milímetro a poder modificarla.

### 6.4 Protección CSRF y métodos POST

La protección contra falsificación de peticiones entre sitios es una de las
características de seguridad incorporadas de Django, y su activación es automática
porque el middleware correspondiente forma parte de la pila por defecto.

Lo relevante en este proyecto es una consecuencia de la evolución del framework. Desde
Django 5, el cierre de sesión solo responde a peticiones `POST`; el cierre por `GET` fue
eliminado. Esto no es un detalle menor: un cierre de sesión por `GET` permitiría que
cualquier sitio incluyera una imagen con esa dirección y cerrara la sesión del usuario
que visitara la página.

Por la misma razón, alternar el estado de completitud de una tarea es una operación
`POST` y no un enlace. Un enlace puede ser recuperado por un rastreador, generado por un
marcador de página, o disparar un formulario `GET` implícito, como ocurre con
algunos buscadores internos. La clase declara `http_method_names = ["post"]` de
modo que cualquier otro verbo recibe `405 Method Not Allowed`.

La propia prueba de la matriz de autorización incluye una aserción explícita de que un
`GET` al conmutador devuelve 405, y de que un `GET` al cierre de sesión también.

### 6.5 Inyección a través de parámetros de consulta

El ordenamiento y el filtrado reciben su criterio del usuario, a través de la cadena de
consulta. Entregar ese valor directamente al ORM sería un error: el nombre de un campo
no es solo un dato, es una instrucción.

La defensa es una lista blanca. `ALLOWED_SORTS` es un diccionario cuyas claves son
literales aceptados y cuyos valores son las listas de campos que se entregan al ORM. El
input del usuario se usa **como clave de búsqueda**, nunca como valor:

```python
ALLOWED_SORTS = {
    "due_date": ["due_date"],
    "priority": ["priority"],
}
```

Si la clave no está en el diccionario, el ordenamiento cae al valor por defecto. No se
produce un error ni una consulta alternativa: simplemente no se reconoce el criterio. El
mismo mecanismo protege el filtrado por estado.

Comprobado durante la verificación: `?sort=owner; DROP TABLE tasks--`,
`?sort=' or 1=1--` y `?status=INJECTED` devuelven la página con el valor por defecto y no
producen ningún error. La base de datos permanece intacta.

### 6.6 Validación en el servidor

El HTML5 ofrece validación en el navegador que mejora la experiencia de uso, pero es
una comodidad, no un control. El usuario puede desactivar el JavaScript, usar un cliente
HTTP directo o manipular la petición. Toda la validación crítica ocurre en el servidor, en
el formulario y en los validadores de contraseña de Django.

Las contraseñas nunca se almacenan en texto plano: Django aplica una función de
derivación con sal, y además valida la robustez mediante cuatro validadores —longitud
mínima, similitud con otros atributos de la cuenta, contraseña común y ausencia de
componente puramente numérico—.

### 6.7 Escape automático de plantillas

Django escapa por defecto el contenido interpolado en las plantillas. Esto neutraliza la
inyección de HTML y de JavaScript en los datos que el usuario almacena, incluidos los
títulos de tareas y los nombres de etiqueta. La comodidad de escribir
`{{ task.title }}` en lugar de una llamada a una función de escape es, en realidad, una
decisión de seguridad.

### 6.8 Limitaciones de seguridad

Con honestidad, el proyecto no está endurecido para producción:

- `DEBUG = True` expone detalles internos ante un error. En producción debe ser
  `False` con un gestor de registros estático.
- `ALLOWED_HOSTS` está vacío, lo que es cómodo en desarrollo y peligroso en producción.
- No hay limitación de intentos de inicio de sesión, por lo que el sistema admite fuerza
  bruta. Django no lo incluye y no se añadió porque la consigna no lo exige.
- No hay configuración de HTTPS, cookies seguras ni endurecimiento de sesión más allá de
  los valores por defecto.
- SQLite no es un motor adecuado para producción con concurrencia.

Ninguno de estos puntos incumple la consigna; todos están documentados en
`docs/security.md`.

## 7. Diseño de interfaz

### 7.1 Bootstrap 5 como sistema visual

Bootstrap 5 fue impuesto por la consigna, y la elección técnica consistente fue
**vendorizar sus archivos** en lugar de referenciar una red de distribución de contenido.
La aplicación renderiza completa sin conexión a internet, no realiza peticiones a
terceros en tiempo de carga y se comporta igual por los dos caminos de instalación. El
costo es que los archivos deben actualizarse manualmente cuando sale una versión nueva.

La decisión de aplicar las clases de Bootstrap a los campos de formulario merece una
explicación, porque tiene una restricción real: Django no expone forma de modificar los
atributos de un widget desde una plantilla. La solución idiomática sería añadir
`django-widget-tweaks`, que es justamente la clase de dependencia que este proyecto
decidió evitar. Las clases se aplican entonces en el `__init__` del formulario, con una
comprobación del tipo de widget para elegir entre la clase de selector, la de casilla o
la de campo de texto.

### 7.2 Responsive: tabla en escritorio, tarjetas en móvil

La decisión de diseño más discutible del proyecto fue cómo representar el listado de
tareas, que muestra siete datos por elemento.

Una tabla de siete columnas en un teléfono de 360 píxeles obliga a desplazamiento
horizontal, que es la peor experiencia posible en la pantalla más pequeña y la que más
usuarios encuentran. La alternativa descartada fue reducir el número de columnas en móvil,
que obliga al usuario a discover qué dato se ocultó.

La solución adoptada muestra **ambos formatos a la vez, uno visible a la vez**: una
tabla con las clases que la ocultan por debajo de 768 píxeles, y una grilla de tarjetas
que la oculta por encima. En un teléfono se ven tarjetas apiladas, con toda la
información disponible y sin desplazamiento lateral; en un escritorio se ve la tabla,
que comparte mejor las columnas y resulta más eficiente para comparar tareas.

### 7.3 Jerarquía visual y estados

El color codifica el dominio, no decora:

- **Prioridad**: gris para baja, ámbar para media, rojo para alta.
- **Estado**: las tareas completadas se muestran tachadas y atenuadas, para que el
  listado se pueda leer de un vistazo.
- **Vencimiento**: una tarea pendiente cuya fecha ya pasó muestra una alerta roja
  distinta de las demás, que es la información accionable del listado.
- **Visibilidad**: cada tarea muestra su nivel con una etiqueta textual, para que el
  propietario no olvide que está compartiendo algo.

Se cubren todos los estados de interfaz que la consigna requiere: listado vacío, listado
con contenido, listado filtrado sin resultados, formulario nuevo, formulario de
edición, formulario con errores, confirmación de borrado, vista de solo lectura para
quien no es propietario y pantalla de sesión cerrada.

### 7.4 Accesibilidad

Se usa HTML semántico —`nav`, `main`, tablas con encabezado—, cada campo tiene su
etiqueta asociada, los errores se comunican con texto y no únicamente con color, y las
acciones destructivas piden confirmación. La navegación por teclado y el contraste
razonable provienen de Bootstrap.

### 7.5 Mensajes y realimentación

Tras cada operación —crear, editar, completar, eliminar, registrarse— la aplicación
muestra un mensaje de resultado. Los mensajes de éxito y error tienen estilos distintos,
de modo que el usuario sabe si la operación ocurrió.

