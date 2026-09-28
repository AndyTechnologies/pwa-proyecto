# ADR-008 — Autorización centralizada en `TaskQuerySet`

Estado: aceptada.

## Contexto

El dominio tiene dos políticas de acceso distintas sobre la misma entidad, y la
distinción es deliberada:

- **Política de escritura.** Solo el propietario modifica una tarea: editar
  (`TaskUpdateView`), eliminar (`TaskDeleteView`) y alternar el estado de
  completada (`TaskCompleteToggleView`). Se implementa en
  `TaskQuerySet.owned_by(user)`, que devuelve `filter(owner=user)`.
- **Política de lectura.** Un anónimo ve tareas `PUBLIC`; un usuario registrado
  que no es el propietario ve `AUTHENTICATED` y `PUBLIC`; el propietario ve todas
  las suyas. Se implementa en `TaskQuerySet.visible_to(user)`, que combina
  `Q(owner=user)` con `Q(visibility__in=[AUTHENTICATED, PUBLIC])` y trata el caso
  anónimo por separado.

Ambas viven en el `QuerySet` de `Task`, no en las vistas ni en las plantillas. Las
vistas las invocan desde `get_queryset()` o desde `get_object_or_404`.

Cuando una tarea no está autorizada, la respuesta es **404, no 403**: la tarea no
se trae de la base, de modo que el servidor nunca confirma que existe. Además, los
parámetros de orden y filtro no se traducen a campos arbitrarios:
`ALLOWED_SORTS` y `STATUS_FILTERS` son whitelists, y un valor no reconocido cae en
el valor por defecto en lugar de llegar al ORM.

## Problema

La autorización es la parte del sistema donde un error no produce un error visible
sino una filtración de datos. La pregunta central es **dónde** se decide quién ve
y quién escribe, porque cada respuesta deja un hueco donde una vista futura puede
interpretar las reglas por su cuenta.

Si cada vista implementa su propio filtro, el sistema tiene tantas copias de la
política como vistas mutables, y cada copia es una oportunidad de que una de ellas
se olvide de un caso. Si la decisión se toma en la plantilla, la seguridad depende
de que el botón se haya ocultado. La propiedad `is_editable_by` existe, pero es
una pista de presentación: incluso con un bug en la plantilla, el servidor debe
seguir negando la escritura.

La decisión a documentar es, entonces, dónde vive la regla y qué se sacrifica a
cambio de que haya un solo lugar donde vive.

## Opciones consideradas

1. **Filtrado a nivel de queryset, centralizado en `TaskQuerySet`** (opción
   adoptada).
2. **`UserPassesTestMixin`** por vista, con un test de permiso explícito en cada
   clase.
3. **Chequeos por vista con decoradores**, escritos a medida para el proyecto.
4. **Framework de permisos propio**, con objetos de permiso, roles y una capa
   configurable de autorización.

## Decisión

Se adopta la **opción 1: el filtrado a nivel de queryset, centralizado en
`TaskQuerySet`**.

El argumento es que la política se decide donde se cumple. Una vista no *decide*
qué puede ver el usuario: pide un conjunto de tareas y recibe el conjunto correcto
o ninguno. La diferencia es de fondo:

- Con la política en el queryset, la escritura de la regla existe una vez. Una
  vista nueva no puede "reinterpretar" las reglas porque no las contiene: o llama
  a `owned_by`, o no está usando la política y eso se ve en la lectura del código.
- Con la política en la vista, cada vista reescribe la regla. Hoy hay tres vistas
  mutables y una de lectura; mañana habría cinco, y la divergencia entre ellas es
  la forma habitual en que aparece un fallo de autorización.

La formulación concreta: `owned_by` es la política de escritura y se usa en las
tres vistas que mutan; `visible_to` es la política de lectura y se usa en
`TaskDetailView` y `SharedTaskListView`. El filtro va en `get_queryset()`, de modo
que la vista nunca llega a tener un objeto no autorizado en las manos.

### 404 en lugar de 403

Cuando `get_object_or_404` no encuentra la tarea porque el filtro la excluyó, la
respuesta es 404. Es una elección deliberada y no un descuido: un 403 confirmaría
que la tarea existe y que solo se le niega el acceso, lo que convierte el sistema en
un oráculo de existencia de identificadores para tareas ajenas. Con 404, la
respuesta es idéntica para "no existe" y "existe pero no es tuya", y no hay nada que
extraer de ella.

### Enforcement en tres niveles

La autorización del lado servidor existe en tres puntos, y ninguno sustituye a los
otros:

- **Nivel de queryset**: `owned_by` y `visible_to` definen el conjunto de objetos
  que la vista puede siquiera obtener. Es el nivel principal.
- **Nivel de vista**: `LoginRequiredMixin` exige sesión antes de que exista un
  usuario contra el que evaluar, y `TaskCompleteToggleView` restringe
  `http_method_names` a `post` para que el estado no se pueda cambiar siguiendo un
  enlace o una precarga de URL.
- **Nivel de acción**: los parámetros de orden y filtro se validan contra
  whitelists (`ALLOWED_SORTS`, `STATUS_FILTERS`) antes de tocar el ORM, de modo que
  la entrada del usuario nunca se convierte en un nombre de campo.

### Lo que las plantillas no hacen

Ocultar el botón de editar cuando `is_editable_by` devuelve falso es **presentación,
nunca control**. El control es `get_queryset()` con `owned_by`: si la plantilla
muestra el botón por un error, la escritura sigue siendo rechazada. La propiedad
existe para que la interfaz no ofrezca acciones imposibles, no para hacerlas
posibles o impedirlas.

## Consecuencias

**Beneficios**

- Una sola implementación de la política de acceso, en `TaskQuerySet`, legible y
  con tests propios.
- Impossible que una vista se salte el filtro por descuido: si pide objetos, pide
  un conjunto ya filtrado.
- El riesgo de fuga por enumeración de identificadores desaparece: la respuesta es
  404 tanto si la tarea no existe como si pertenece a otro usuario.
- `TaskUpdateView` y `TaskDeleteView` resuelven objetos con la misma expresión, sin
  filtros duplicados.
- Las vistas quedan más simples: describen qué mostrar, no a quién se lo muestran.
- Los parámetros del usuario nunca se convierten en campos del ORM, porque las
  whitelists lo impiden antes de la consulta.
- Un usuario anónimo puede navegar las tareas públicas sin sesión, sin complicar
  la firma de `visible_to` con un caso especial de `None`.

**Costos**

- **404 en lugar de 403 borra una distinción útil para depurar.** La respuesta es
  idéntica en dos causas muy diferentes —"no existe" y "existe pero no te
  corresponde"— y eso es precisamente lo que se busca en producción y lo que
  dificulta el diagnóstico durante el desarrollo. Un `403` con un mensaje que
  distinguiera los casos sería más cómodo en la mesa de trabajo, a costa de
  filtrar información. Es el intercambio correcto para este dominio, pero es un
  coste, no una gratuidad.
- **Indirección.** Para entender por qué una vista no muestra nada hay que mirar el
  `QuerySet`, no la vista. Es un coste de comprensión, aceptado a cambio de la
  unicidad de la política.
- **Requiere disciplina para mantenerla.** La seguridad depende de que toda vista
  nueva pase por `owned_by` o `visible_to`. El diseño no lo impone por completo:
  una vista que use `Task.objects.filter(...)` directamente no pasaría por la
  política, y eso solo se detecta leyendo el código.
- **La distinción entre lectura y escritura es implícita en el nombre.** Que
  `owned_by` sea la política de escritura y `visible_to` la de lectura no está
  expresada en tipos ni forzada por el sistema; está en la docstring y en el uso.
- **Los permisos de tipo "permisos" del admin siguen existiendo.** `owned_by` no
  reemplaza el sistema de permisos de Django: el admin tiene su propio modelo de
  permisos, y ambos conviviendo son dos mapas de autorización en el proyecto. Para
  el alcance actual es aceptable, y el admin no es el punto de entrada del
  usuario final.

## Alternativas descartadas

**`UserPassesTestMixin` por vista (opción 2).** Se descarta porque traslada la
política a cada vista, que es exactamente lo que se quiere evitar. Con
`UserPassesTestMixin` cada clase declara su propio test de permiso, y ese test
tiene que volver a razonar sobre propiedad, visibilidad y tipo de operación: es la
misma regla escrita tres veces, con la posibilidad de que una de las tres quede
desactualizada. Además, el objeto ya está cargado cuando el test corre, lo que
significa que la comprobación ocurre *después* de traer el dato: el sistema depende
de que el test devuelva `False` y no de que el objeto no llegue a existir. El
beneficio real del mixin —un punto de extensión declarativo— lo aporta igual
`LoginRequiredMixin`, que sí se usa, pero para exigir sesión, que es una condición
de entrada y no una regla de dominio.

**Chequeos por vista con decoradores (opción 3).** Se descarta por las mismas
razones que la opción 2, con un coste adicional: un decorador se aplica a la
función que resuelve la petición, de modo que es fácil olvidar aplicarlo en una
vista nueva, y el olvido no produce ningún error visible. La comprobación queda
además en el punto de entrada, no en la fuente de datos, de modo que cualquier
consulta futura feita desde otro punto —el admin, un comando de gestión, un
script— no queda cubierta por el decorador. Centralizar en el `QuerySet` cubre
todos los caminos que pasan por el manager, no solo el HTTP.

**Framework de permisos propio (opción 4).** Se descarta porque supondría
construir la capa que Django ya ofrece parcialmente y que el dominio no necesita
en esa forma. Un framework de permisos implica definir roles, permisos, objetos
de permiso y un punto de integración, más su configuración. El dominio tiene dos
reglas, y una de ellas es "solo el propietario escribe", que es una relación ya
presente en el modelo (`owner`). Modelar eso como un sistema de roles sería
sustituir una clave foránea ya correcta por una capa de indirección, con su
coste de configuración y su superficie de errores. `django.contrib.auth` sigue
proporcionando el sistema de permisos estándar para el admin; para las vistas del
proyecto, el `QuerySet` es el punto de control suficiente y verificable.
