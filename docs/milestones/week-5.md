# Corte Semana 5 — Proyecto Django configurado, modelos y Admin

**Objetivo del corte (consigna):** *"Proyecto de Django debidamente configurado. Los
modelos creados y registrados en el Sitio de Administración de Django."*

## Qué se entregó

### Configuración del proyecto

- Proyecto Django operativo sobre el esqueleto preexistente, con la app de dominio
  `tasks` registrada en `INSTALLED_APPS`.
- `TEMPLATES['DIRS']` y `STATICFILES_DIRS` apuntando a la raíz del proyecto.
- `LANGUAGE_CODE = 'es'` y `STATIC_ROOT` declarado.
- Base de datos SQLite, sin configuración adicional.
- Migraciones del proyecto aplicadas y consistentes.

### Modelos de dominio

`tasks/models.py` define tres piezas:

**`Priority`** — `IntegerChoices` con `LOW=1`, `MEDIUM=2`, `HIGH=3`.
Se almacena como entero para que el orden semántico coincida con el orden de la base de
datos sin tablas delookup adicionales.

**`Visibility`** — `TextChoices` con `PRIVATE`, `AUTHENTICATED`, `PUBLIC`.
Cadena en lugar de entero porque es un valor de dominio legible en la base de datos y
en las URLs de depuración.

**`Tag`** — `name` único, `slug` único derivado automáticamente, `created_at`.
La reutilización de etiquetas se resuelve insensible a mayúsculas con
`Tag.objects.matching()`.

**`Task`** — `owner` (FK a `AUTH_USER_MODEL`, `on_delete=CASCADE`), `title`,
`description`, `due_date`, `priority`, `completed`, `visibility`, `tags` (M2M),
`created_at`, `updated_at`.

Índices compuestos en `(owner, due_date)` y `(visibility)`, que son los dos accesos
dominantes del sistema: el listado del propietario y el filtro de lectura pública.

### Políticas de autorización en el queryset

`TaskQuerySet` expone dos métodos que concentran toda la lógica de acceso:

| Método | Política | Uso |
| --- | --- | --- |
| `owned_by(user)` | **Escritura.** Solo tareas del usuario. | Vistas mutables |
| `visible_to(user)` | **Lectura.** Anónimo → `PUBLIC`; registrado → `AUTHENTICATED` + `PUBLIC`; owner → todas las propias. | Vistas de detalle y listados compartidos |

Centralizar la política aquí —y no en cada vista— es la decisión que evita que una vista
nueva reimagine las reglas por su cuenta. Se documenta en ADR-008.

### Django Admin

Ambos modelos registrados y configurados para ser útiles, no solo accesibles:

- `TaskAdmin`: `list_display` con título, propietario, vencimiento, prioridad, estado,
  visibilidad y etiquetas; `list_filter` por estado, visibilidad, prioridad y fecha;
  `search_fields` sobre título, descripción y nombre de usuario; `date_hierarchy`;
  `autocomplete_fields` para las etiquetas; `fieldsets` que separan datos de tarea,
  privacidad y auditoría; `created_at`/`updated_at` como solo lectura.
- `TagAdmin`: búsqueda por nombre, `prepopulated_fields` para el slug y un contador de
  tareas asociadas.

## Verificación del corte

| Comprobación | Resultado |
| --- | --- |
| `manage.py check` | Sin problemas |
| `makemigrations tasks` | `0001_initial` con `Task` y `Tag` |
| `migrate` | Aplicada sin errores |
| Modelos en `admin.site._registry` | `Task: True`, `Tag: True` |
| `/admin/`, `/admin/tasks/task/`, `/admin/tasks/tag/` | Responden (redirección a login, esperado sin sesión) |

## Fuera de alcance en este corte

El routing y las vistas se entregan en el corte de Semana 7, según la consigna. En este
commit `tasks/urls.py` y `tasks/views.py` están deliberadamente vacíos.
