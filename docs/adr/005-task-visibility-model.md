# ADR-005 — Visibilidad como campo enum en `Task`

Estado: aceptada.

## Contexto

Una tarea pertenece a un único usuario: `Task.owner` es un `ForeignKey` a
`settings.AUTH_USER_MODEL` con `on_delete=models.CASCADE` y
`related_name="tasks"`. La escritura es exclusiva del propietario y así está
garantizado en el servidor por `TaskQuerySet.owned_by` (ADR-008).

Sobre la **lectura**, el dominio exige tres niveles de compartición:

- `PRIVATE`: solo el propietario.
- `AUTHENTICATED`: el propietario y cualquier usuario registrado.
- `PUBLIC`: cualquiera, incluidos visitantes anónimos.

El campo está declarado como `CharField` con `choices=Visibility.choices`,
`max_length=20` y `default=Visibility.PRIVATE`, sobre el enum de texto
`Visibility(TextChoices)` con valores `"private"`, `"authenticated"` y
`"public"`.

La decisión de lectura vive en `TaskQuerySet.visible_to(user)`: un anónimo solo
ve `PUBLIC`; un usuario registrado que no es el propietario ve `AUTHENTICATED` y
`PUBLIC`; el propietario ve todas las suyas sea cual sea la visibilidad. El
modelo declara además un índice sobre `visibility`, porque la lista pública
filtra por ese campo.

## Problema

Hay que decidir dónde se expresa la regla "quién puede leer esta tarea". La
estructura de datos que la exprese se convierte en parte del dominio: es lo que
se migra, lo que se indexa y lo que hay que consultar en cada listado. Elegir la
estructura equivocada obliga a rehacer migraciones y consultas; elegir la
estructura más simple pero insuficiente obliga a otra igual.

El proyecto necesita cubrir tres niveles de compartición ahora, y conviene que
la decisión sea honesta sobre lo que ese modelo no puede expresar en el futuro.

## Opciones consideradas

1. **Campo enum `visibility` en `Task`**, con `choices` sobre `TextChoices` y
   lectura centralizada en `TaskQuerySet.visible_to`.
2. **Tabla de permisos/ACL separada** (`TaskPermission` con `task`, `user` y
   permiso), que exprese la compartición como filas.
3. **Listas de usuarios por tarea** (campo `ManyToMany` de usuarios
   compartidos, más un booleano de público).
4. **Preferencia global por usuario** (campo `TaskVisibilitySetting` o similar en
   el perfil, que aplique a todas sus tareas).

## Decisión

Se adopta la **opción 1: campo enum `visibility` en `Task`**.

La razón principal es que el dominio real **no es arbitrario**. La compartición
es una taxonomía cerrada y enumerable: el usuario elige entre tres niveles
significativos, y el nombre del nivel es el valor. Un campo con `choices`
expresa exactamente eso, y hace el dominio legible en el modelo, en el formulario
y en el admin sin ninguna tabla adicional.

La segunda razón es operativa: con un campo, el listado público es
`filter(visibility=Visibility.PUBLIC)`, un filtro sobre una columna indexada. Con
una tabla ACL, el mismo listado exige resolver "tareas que no tienen ninguna fila
de permisos y cuya visibilidad global es pública", es decir un anti-join sobre una
tabla que crece con cada compartición, y la consulta pasa de ser un filtro de
columna a ser una subconsulta correlacionada. Para el volumen de este proyecto
eso no es un problema de rendimiento medible, pero sí es una complejidad de
consulta permanente y gratuita de evitar.

La tercera es la coherencia con el resto del modelo. `Task` ya usa
`IntegerChoices` para `priority` con el mismo patrón (valor almacenado, etiqueta
traducida), de modo que `visibility` introduce un segundo ejemplo del mismo
contrato en lugar de un patrón nuevo. Y la regla de lectura, como en el resto del
dominio, se evalúa en un único sitio: `visible_to`.

### Dos restricciones explícitas de este modelo

- **La visibilidad nunca otorga escritura.** `AUTHENTICATED` y `PUBLIC` amplían
  únicamente la lectura. Editar, eliminar o alternar el estado completo requiere
  ser el propietario, y eso lo garantiza `owned_by` en el servidor
  (`TaskUpdateView`, `TaskDeleteView`, `TaskCompleteToggleView`). El enum está
  definido con esa intención en su docstring y `is_editable_by` existe solo como
  pista de presentación para ocultar botones (ADR-008).
- **La lista pública no se mezcla con la lista del propietario.**
  `PublicTaskListView` devuelve únicamente tareas `PUBLIC`, con su propia ruta y
  su propia plantilla, y no se combina con la del usuario. La razón es de
  coherencia mental y de alcance: la lista del propietario es el espacio de
  trabajo con filtros, orden y acciones; la lista pública es un catálogo de
  consulta. Mezclarlas obligaría al usuario a filtrar constantemente para
  distinguir "mías" de "de otros", y expondría en la misma pantalla controles de
  edición que no aplican a la mayoría de las filas. `SharedTaskListView` resuelve
  el caso intermedio —tareas de otros visibles para el usuario, en solo lectura—
  con su propia consulta (`visible_to` más `exclude(owner=...)`) y su propia
  plantilla.

## Consecuencias

**Beneficios**

- Modelo legible: la regla de compartición se lee en la definición del campo.
- Una sola columna indexada sostiene los tres listados; no hay tablas de unión
  que mantener ni filas que se desincronicen.
- El valor por defecto es el más restrictivo (`PRIVATE`), de modo que una tarea
  creada sin especificar visibilidad no queda expuesta por accidente.
- La consulta de lectura es una expresión declarativa única en
  `TaskQuerySet.visible_to`, reutilizada por `TaskDetailView`,
  `SharedTaskListView` y `PublicTaskListView`.
- El admin y los formularios obtienen las opciones y las etiquetas desde el mismo
  `TextChoices`, sin listas duplicadas.
- Los tres niveles se distinguen de forma explícita en la interfaz y en las
  plantillas, y las reglas derivadas de ellos (por ejemplo, que solo el
  propietario puede modificarla) se leen sin ambigüedad.

**Costos**

- **Cambiar el modelo de compartición más adelante exige una migración.** Si
  mañana se quisiera "compartir con estas tres personas concretas" o un permiso
  por usuario, habría que añadir una tabla ACL y migrar los datos existentes
  desde el enum, decidiendo cómo se traduce una tarea `AUTHENTICATED` a filas.
  Con una tabla ACL desde el principio, ese cambio no habría costado migración.
- **Un campo no expresa garantías arbitrarias por usuario.** La opción 2
  (ACL) permitiría "esta tarea la puede ver y editar Ana pero no Carlos". El
  campo enum no tiene forma de expresar eso: solo conoce tres estados globales.
  Si el requisito de compartición por usuario apareciera, esta decisión sería
  insuficiente.
- **Combinar niveles requiere condiciones OR.** "Registrados o públicos" es un
  `Q` con dos ramas, y crece de forma no trivial si se añade un nivel más
  (`visible_to` ya lo escribe con `Q`).
- **El valor por defecto puede sorprender.** Una tarea sin visibilidad explícita
  queda privada; es la opción segura, pero si un usuario esperase que "crear una
  tarea" la hiciera visible para otros, la interfaz debe comunicar con claridad el
  valor por defecto, y eso es responsabilidad de la plantilla, no del modelo.
- El enum es un compromiso cerrado: `max_length=20` y tres valores fijos
  significan que cualquier nivel futuro requiere cambiar el enum y migrar.

## Alternativas descartadas

**Tabla de permisos/ACL separada (opción 2).** Se descarta porque resuelve un
problema que el dominio no tiene y a un coste alto en la operación diaria. Con una
ACL, crear una tarea compartida exige resolver por defecto quién es visible la
tarea: ¿cualquiera autenticado o una lista explícita? Esa decisión tiene que estar
codificada en la UI, y el usuario elegiría entre "nadie más" y "todos los
registrados" escribiendo filas repetidas. El resultado es el mismo comportamiento
con una tabla que crece por cada compartición, más la necesidad de decidir y
limpiar permisos revocados, más consultas de listado que deben subconsultar esa
tabla. Se descarta además por el coste de la respuesta a "quién puede leer esto":
con el campo enum se responde leyendo el campo; con la ACL hay que contar filas.

**Listas de usuarios por tarea (opción 3).** Se descarta porque es el caso
particular más débil de la ACL: obliga al usuario a elegir nombres de usuario
uno por uno en un formulario, en lugar de declarar un nivel. El proyecto no pide
compartir con personas concretas: pide tres niveles de compartición. Esta opción
convierte una decisión de una constante en un flujo de selección de usuarios, y
suma el problema de resolver qué usuario escribe "an" y otro escribe "Ana".

**Preferencia global por usuario (opción 4).** Se descarta porque contradice el
dominio, no porque sea más costosa. La consigna describe la compartición como
una decisión por tarea, y una preferencia global no puede expresar un caso
real: el mismo usuario necesita que su tarea de la universidad sea privada y la
de trabajo pública. Obligaría a modelar la visibilidad como una propiedad de la
cuenta en lugar de la tarea, y una tarea compartida o creada por otro usuario
heredaría una regla que el usuario no eligió para esa tarea concreta.
