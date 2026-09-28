# ADR-006 — Etiquetas con relación `ManyToMany` a un modelo `Tag`

Estado: aceptada.

## Contexto

Cada tarea puede llevar etiquetas de texto libre. La interfaz de captura es un
único campo de texto con nombres separados por comas (`tags_input` en
`TaskForm`), no un multiselect, porque el usuario debe poder reutilizar etiquetas
existentes e inventar nuevas en el mismo gesto.

El modelo declarado es:

- `Tag`: `name` (`CharField`, `max_length=50`, `unique=True`), `slug`
  (`SlugField`, `max_length=50`, `unique=True`, derivado con `slugify` en
  `save()`), `created_at` (`auto_now_add`), `Meta.ordering = ["name"]`, y un
  `TagQuerySet` con el método `matching(name)` que busca por `name__iexact`.
- `Task.tags`: `ManyToManyField(Tag, related_name="tasks", blank=True)`.

La resolución de nombres a instancias ocurre en `TaskForm._resolve_tags`, en el
momento del `save(commit=True)`, porque un `ModelForm` no puede persistir un
`ManyToMany` a partir de un `CharField`.

## Problema

Hay que decidir cómo se relacionan las tareas con sus etiquetas, y con ella
decidir la política de identidad del `Tag`: si dos personas escriben "Django" y
"django", ¿son la misma etiqueta? Si escriben "Python 3" y "python-3", ¿colisionan?
La estructura de datos elegida determina la respuesta a esas dos preguntas, y la
estrategia de resolución tiene que ser consistente con las restricciones de
unicidad de la base de datos, no solo con lo que espera el usuario.

## Opciones consideradas

1. **`ManyToMany` a un modelo `Tag`** con `name` único y `slug` único derivado.
2. **Campo de texto libre en `Task`**: los nombres de las etiquetas guardados como
   una cadena separada por comas, sin entidad `Tag`.
3. **Copia de la etiqueta por tarea**: cada tarea tiene sus propias filas de
   etiqueta, sin modelo `Tag` compartido.

## Decisión

Se adopta la **opción 1: `ManyToMany` a un modelo `Tag` compartido**.

La razón es que la etiqueta tiene identidad propia en el dominio. No es texto
adicional de la tarea: es un objeto que la tarea referencia, y la interfaz exige
poder reutilizar una etiqueta existente. Eso descarta de entrada la opción 2: sin
entidad `Tag` no hay nada que reutilizar ni nada a lo que filtrar, y la única
búsqueda posible sería un `LIKE` sobre una columna de texto, que no puede
devolver "las tareas con la etiqueta X" de forma indexada ni distinguir mayúsculas de
minúsculas con garantías.

La opción 3 tiene el mismo defecto de identidad y un coste adicional: el conjunto
de etiquetas distintas del sistema sería igual a la suma de las de cada tarea, y
filtrar por etiqueta exigiría comparar textos, no seguir una relación.

### Identidad del `Tag`: nombre único, slug único, reutilización sin distinguir
mayúsculas

`name` es `unique=True`, lo que da una garantía a nivel de base de datos de que
no haya dos etiquetas con el mismo nombre exacto. Como el usuario escribe sin
controlar mayúsculas, la unicidad exacta no alcanza: "Django" y "django" no
colisionarían en la base pero serían la misma etiqueta para el usuario. La
solución es que la **búsqueda** sea insensible a mayúsculas mediante
`TagQuerySet.matching()` (`name__iexact`), y no que la columna pierda su
restricción. Se conserva la restricción en la base y se flexibiliza la consulta.

El `slug` cumple la segunda función: ser una clave estable y apta para URL y para
el filtro `?tag=` de `TaskListView`, que aplica `filter(tags__slug=slugify(...))`.
Que sea `unique=True` es lo que obliga a considerar el defecto siguiente.

### El defecto de colisión de `slug` y cómo lo resuelve `_resolve_tags`

Durante el desarrollo se detectó un defecto real: **dos nombres distintos pueden
producir el mismo `slug`**. `"Python 3"` y `"python-3"` se normalizan ambos a
`python-3`. Si el usuario tenía `"Python 3"` y escribía `"python-3"`, la
resolución por nombre no encontraba nada, se creaba un `Tag` nuevo con un `slug`
ya ocupado y la restricción `unique` de `Tag.slug` hacía saltar un
`IntegrityError`, convirtiendo un envío de formulario válido en un error 500.

La corrección está en `TaskForm._resolve_tags`, que para cada nombre busca en dos
pasos:

1. `Tag.objects.matching(name).first()` — reutilización por nombre, insensible a
   mayúsculas.
2. Si no hay coincididencia, `Tag.objects.filter(slug=slug).first()` — reutilización
   por `slug`, que es la que absorbe la colisión.

Solo si ambos fallan se crea un `Tag` nuevo. La segunda consulta convierte un
error de integridad en la semántica correcta: `"python-3"` y `"Python 3"` son la
misma etiqueta. La limpia previa en `clean_tags_input` completa el panorama:
divide por comas, aplica `strip`, descarta vacíos, pasa a minúsculas, elimina
duplicados dentro del mismo envío y rechaza nombres de más de 50 caracteres, que es
el límite de `Tag.name`.

## Consecuencias

**Beneficios**

- La identidad de la etiqueta existe en la base de datos y es reutilizable entre
  tareas y entre usuarios.
- Filtrar por etiqueta es una relación de la base (`filter(tags__slug=...)`), no
  una búsqueda de texto; `TaskListView` lo expone como parámetro `?tag=`.
- El menú lateral de etiquetas del usuario (`all_tags`) se obtiene con
  `Tag.objects.filter(tasks__owner=...)` y `distinct()`, es decir, solo las
  etiquetas que ese usuario usa realmente.
- Las restricciones `unique` de `name` y `slug` previenen duplicados a nivel de
  base, no solo en la capa de aplicación.
- La duplicación dentro de un mismo envío se descarta antes de tocar la base, lo
  que evita errores por lote.
- El `slug` queda disponible como clave estable para URLs y parámetros, sin
  depender del texto visible.

**Costos**

- **Una consulta de más por etiqueta resuelta.** La reutilización por nombre y,
  si falla, por `slug` implican hasta dos búsquedas por nombre. Para el volumen del
  proyecto es irrelevante, pero es trabajo extra que una etiqueta como texto
  libre no tendría.
- **La resolución es heurística y depende de `slugify`.** La regla "mismo `slug`
  significa misma etiqueta" tiene una consecuencia visible: si dos usuarios
  escriben nombres distintos que se normalizan igual, el segundo reutiliza la
  etiqueta del primero en lugar de crear la suya. Es el comportamiento deseado
  aquí, pero es una decisión semántica que hay que conocer para no interpretarla
  como un bug.
- **La restricción de 50 caracteres de `name` se filtra en el formulario y no en
  el modelo de dominio.** Un `Tag` creado por consola, por el admin o por código
  podría tener un nombre que el formulario nunca aceptaría, y el `slug` se
  trunca a 50 caracteres en `save()`, lo que reintroduce una fuente potencial de
  colisión para nombres largos con prefijo común. La base de datos protege la
  integridad, pero la coherencia entre el flujo de formulario y el resto del
  sistema depende de esa validación.
- **Un `ModelForm` no puede persistir un `ManyToMany`.** Por eso la resolución
  vive en `save()` y no en un `clean_*` estándar, lo que significa que el
  `TaskForm` tiene un comportamiento de guardado que no es el estándar de un
  formulario de modelo y que hay que conocer para no esperar lo habitual.
- La escritura del `ManyToMany` ocurre en una operación separada del `INSERT` de
  la tarea, de modo que guardar una tarea con etiquetas son dos accesos al banco
  dentro de la misma unidad de trabajo.

## Alternativas descartadas

**Campo de texto libre en `Task` (opción 2).** Se descarta por la pérdida
concreta de identidad y capacidad de consulta. Con un campo de texto no existe el
concepto de "la etiqueta django": solo hay cadenas que empiezan o contienen esa
palabra. Consecuencias directas: el filtro por etiqueta pasa a ser un `LIKE` sobre
una columna sin índice, con la sensibilidad a mayúsculas y acentos del motor a
cargo del lector; el menú de etiquetas del usuario no se puede construir sin
recorrer todas sus tareas y parsear cadenas; y renombrar o reutilizar una
etiqueta deja de ser una operación posible. También obliga a elegir un
delimitador y a decidir qué pasa con una etiqueta que lo contenga.

**Copia de la etiqueta por tarea (opción 3).** Se descarta porque duplica datos y
convierte la reutilización en un problema de deduplicación. Dos tareas con la
etiqueta "django" almacenaría dos filas distintas, así que el conjunto global de etiquetas
deja de estar definido y la búsqueda por etiqueta tiene que consolidar en cada
consulta. La consecuencia más grave es la que la consigna exige: el usuario
debe poder usar una etiqueta ya existente, y con copias por tarea no hay forma de
saber si ya existe sin implementar a mano la deduplicación que el modelo `Tag`
ya resuelve con una restricción `unique`.

**Campo de texto con lista normalizada como JSON o texto delimitado, en vez de
texto libre (variante de la opción 2).** Se descarta por la misma razón de
consulta: cualquier representación que no tenga entidad propia impide un `JOIN`
y devuelve el filtrado a comparaciones de texto sobre cada fila. Además, esa
variante no evita ninguno de los problemas de la opción 2 y agrega el
mantenimiento de un formato.
