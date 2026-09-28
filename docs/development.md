# Guía de desarrollo — Task Manager

## 1. Prerrequisitos

| Requisito | Versión | Cómo verificarlo |
| --- | --- | --- |
| Python | **>= 3.12** (el proyecto se verificó en desarrollo con 3.12) | `python3 --version` |
| uv | cualquiera (opcional) | `uv --version` |
| Git | cualquiera | `git --version` |

No hace falta Node, ni gestor de paquetes de JavaScript, ni servidor de base de datos.
Bootstrap 5.3.8 está **vendorizado** en `static/`, así que no hay descarga en tiempo de
ejecución ni `npm install`.

### Rutas de instalación

El proyecto declara sus dependencias dos veces, con el mismo conjunto:

| Ruta | Archivos | Cuándo usarla |
| --- | --- | --- |
| **uv** | `pyproject.toml` + `uv.lock` | Recomendada. Resuelve rápido y `uv.lock` fija versiones exactas de la cadena completa |
| **pip + venv** | `requirements.txt` | Cuando el entorno ya tiene un venv creado a mano o la consigna pide un `pip install` convencional |

Ambas instalan **exactamente** las mismas tres paquetes: `django==6.1.1`, `asgiref==3.12.1`
y `sqlparse==0.6.0`. Bootstrap no figura en ninguna de las dos porque no es un paquete
Python: son dos archivos vendorizados en `static/css/` y `static/js/`.

## 2. Ruta de instalación con uv

```bash
# 1. Instalar dependencias y crear el entorno virtual .venv
uv sync

# 2. Aplicar migraciones (crea db.sqlite3 con las tablas de auth y de tasks)
uv run python manage.py migrate

# 3. Crear un usuario administrador para entrar a /admin/
uv run python manage.py createsuperuser

# 4. Levantar el servidor de desarrollo
uv run python manage.py runserver
```

`uv sync` lee `pyproject.toml` y respeta `uv.lock`. El entorno queda en `.venv/`, que ya
está en `.gitignore`.

El servidor queda en `http://127.0.0.1:8000/`.

### Atajos con uv

```bash
uv run python manage.py test tasks
uv run python manage.py makemigrations
uv run python manage.py shell
uv run python manage.py createsuperuser
```

## 3. Ruta de instalación con pip + venv

```bash
# 1. Crear el entorno virtual
python3 -m venv .venv

# 2. Activarlo
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell / CMD

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear un usuario administrador
python manage.py createsuperuser

# 6. Levantar el servidor
python manage.py runserver
```

Con el venv activado, `python` ya apunta al intérprete correcto y no hace falta escribir
`.venv/bin/python` en cada comando.

## 4. Migraciones

`tasks/migrations/0001_initial.py` es la única migración del proyecto y crea `Task` y
`Tag`. El resto de tablas (`auth_user`, `django_session`, `django_content_type`, etc.)
pertenecen a `django.contrib` y se crean con el mismo `migrate`.

```bash
# Ver el estado
python manage.py showmigrations

# Generar una migración tras cambiar models.py
python manage.py makemigrations

# Aplicar
python manage.py migrate

# Revertir la última migración del proyecto
python manage.py migrate tasks 0001     # o el nombre de la migración anterior
```

**Regla de la casa:** toda cambio en `tasks/models.py` va acompañado de su migración en el
mismo commit, y `python manage.py makemigrations --check --dry-run` debe devolver
`No changes detected` antes de dar por cerrado el trabajo. Estado actual: verificado, sin
migraciones pendientes.

Si se cambia un modelo en un entorno de desarrollo y la migración ya se aplicó a una base
con datos que no importan, `rm db.sqlite3 && python manage.py migrate` la reconstruye. La base
es descartable en desarrollo.

## 5. Superusuario

```bash
python manage.py createsuperuser
```

Pide nombre de usuario, correo y contraseña. La contraseña se valida con los cuatro
validadores de `AUTH_PASSWORD_VALIDATORS`, así que una contraseña trivial es rechazada.

El superusuario sirve para dos cosas:

1. Entrar a `/admin/`.
2. Crear usuarios de prueba sin pasar por `/register/`.

## 6. Ejecutar los tests

```bash
python manage.py test tasks                  # los 249
python manage.py test tasks.tests.test_permissions
python manage.py test tasks --verbosity=2    # ver cada nombre
```

Estado verificado: **249 tests, OK**, ~46 s. La base de datos de test se crea y se destruye
sola; `db.sqlite3` no se toca.

## 7. Servidor de desarrollo

```bash
python manage.py runserver
```

| URL | Qué hay |
| --- | --- |
| `/` | No existe como ruta. Django responde 404 con `APPEND_SLASH` activo |
| `/tasks/` | El listado del propietario. Redirige al login si no hay sesión |
| `/tasks/public/` | La única página de contenido abierta a anónimos |
| `/register/` | Alta de cuenta |
| `/login/` | Inicio de sesión |
| `/admin/` | Panel de administración |

Para ver las tres visibilidades hace falta más de una identidad en el mismo navegador. La
forma más simple es usar dos navegadores o una ventana incógnito, oSessiones en dos
navegadores distintos.

```bash
# Puerto distinto, útil si 8000 ya está ocupado
python manage.py runserver 8001
```

Con `DEBUG = True`, cualquier error muestra la página de traceback de Django con la
petición, la consulta SQL y el contexto. Es la herramienta de desarrollo principal, y la
razón por la que esta configuración no es aceptable en producción (`docs/security.md`, L1).

## 8. Django Admin

`/admin/` requiere `is_staff`. Solo un superusuario (o un usuario elevado con
`python manage.py shell`) entra.

Está configurado para ser útil de inspección, no una lista pelada:

**TaskAdmin**

| Elemento | Configuración |
| --- | --- |
| Columnas | `title`, `owner`, `due_date`, `priority`, `completed`, `visibility`, `tag_list` |
| Filtros | `completed`, `visibility`, `priority`, `due_date` |
| Búsqueda | `title`, `description`, `owner__username` |
| Jerarquía de fechas | `date_hierarchy = "due_date"` |
| Etiquetas | `autocomplete_fields`, que requiere `search_fields` en `TagAdmin` |
| Secciones | `fieldsets` separan tarea, estado y privacidad, etiquetas y auditoría |
| Solo lectura | `created_at` y `updated_at` |
| Paginación | 25 filas |

`tag_list` es un `@admin.display` que concatena los nombres de las etiquetas de la tarea.

**TagAdmin**

| Elemento | Configuración |
| --- | --- |
| Columnas | `name`, `slug`, `created_at`, `task_count` |
| Búsqueda | `name` — necesaria para que funcione el `autocomplete_fields` de `TaskAdmin` |
| Slug | `prepopulated_fields = {"slug": ("name",)}` |
| Orden | por `name` |
| `task_count` | `@admin.display` con `tag.tasks.count()` |

El admin es la herramienta de inspección y moderación. **No es una superficie de usuario
final**: un superusuario ve todas las tareas, incluidas las privadas de otros, sin pasar
por `TaskQuerySet.visible_to`. Es una excepción deliberada al modelo de autorización, y
está declarada en `docs/security.md` (L11).

Para crear un usuario no superusuario con acceso al admin:

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.create_user("revisor", password="Uni-Segura-2024!")
>>> user.is_staff = True
>>> user.save()
```

## 9. Agregar una dependencia

Las dos rutas de instalación deben quedar siempre sincronizadas. El flujo es:

```bash
# 1. Declarar y resolver con uv (actualiza pyproject.toml y uv.lock)
uv add requests

# 2. Regenerar requirements.txt desde el lock para que pip + venv instale lo mismo
uv pip freeze > requirements.txt
```

La segunda etapa es obligatoria: sin ella, quien use `pip install -r requirements.txt` no tendrá
el paquete y obtendrá un `ModuleNotFoundError`.

Al terminar, ambos archivos deben estar en el mismo commit y revisar el diff de
`requirements.txt`: si cambió algo que no debería (por ejemplo una versión de `django`),
significa que el entorno quedó desalineado.

**Antes de agregar cualquier paquete**, responder por escrito estas tres preguntas:

1. ¿Lo resuelve Django con lo que ya hay? Es la respuesta correcta en la enorme mayoría de
   los casos de este proyecto.
2. ¿Lo justifica un requisito de la consigna, o es conveniencia propia?
3. ¿Cuánto cuesta en la tasa de actualización? Cada dependencia es una deuda permanente.

Dependencias actuales: **Django y dos transitivas**. Bootstrap es un asset vendorizado, no
una dependencia. `pytest`, `factory_boy`, `coverage` y `django-widget-tweaks` están
deliberadamente ausentes (RNF-12).

## 10. Convenciones del proyecto

| Convención | Regla | Ejemplo |
| --- | --- | --- |
| **Copy de la interfaz** | Español | `"Tarea creada correctamente."`, `"Cerrar sesión"` |
| **Identificadores de código** | Inglés | `TaskCreateView`, `owned_by`, `ALLOWED_SORTS`, `tags_input` |
| **Nombres de test** | Inglés, con el sujeto primero y afirmativos | `test_non_owner_gets_404_not_403_on_the_edit_page` |
| **Mensajes de validación** | Español, dentro del `ValidationError` | `f"La etiqueta «{name}» supera los 50 caracteres."` |
| **Docstrings** | Inglés, con la referencia al ADR o al RF que justifican la decisión | `"""Write policy: only tasks owned by ``user``."""` |
| **Comentarios de plantilla** | Español | Los de `task_card.html` explican por qué el toggle es un form y no un enlace |
| **Dependencias de test** | Ninguna externa | Solo `django.test` y `manage.py test` |
| **Vistas** | Siempre CBV | Ninguna función-vista, ni para un caso trivial |
| **Autorización** | Siempre en `TaskQuerySet` | Nunca en la vista, nunca en la plantilla |
| **Acceso a datos** | ORM y `QuerySet`, nunca SQL crudo | `filter(tags__slug=slugify(tag))` |
| **Rutas en plantillas** | `{% url %}` siempre | Nunca `href="/tasks/{{ pk }}/"` a mano |
| **Assets** | Vendorizados en `static/`, nunca CDN | Bootstrap va en el repositorio a propósito |
| **Commits** | Conventional Commits, en inglés | `feat(tasks): ...`, `test(tasks): ...`, `chore: ...`, `docs: ...` |
| **Un concern por commit** | | Un fix de modelo no viaja con un cambio de plantilla |

### Añadir un campo nuevo: el recorrido completo

1. Modificar `tasks/models.py`.
2. `python manage.py makemigrations`.
3. Agregar el campo a `TaskForm.Meta.fields` si debe ser editable, y a
   `TaskForm.Meta.widgets` si necesita widget.
4. Agregar la etiqueta del `label` a español en `TaskForm.__init__` si es una elección.
5. Agregar los tests en `test_models.py` (default) y en `test_forms.py` (validación).
6. `python manage.py test tasks`.
7. Si es visible, actualizar `TaskAdmin.fieldsets` y la plantilla.
8. Commit único con el modelo, la migración, el formulario, los tests y la plantilla.

## 11. Plan de entrega en cortes

Los cuatro cortes que define la consigna y el commit que entregó cada uno.

| Corte | Objetivo de la consigna | Commit | Qué lo entrega |
| --- | --- | --- | --- |
| **Semana 3** | "Sitio web estático basado en Bootstrap 5 como prototipo de diseño" | `fbbb453` (`chore: initialize Django project with dual install paths`) y `b9565c6` (capa de diseño) | Bootstrap 5.3.8 vendorizado, jerarquía de plantillas, responsive, estados de interfaz, accesibilidad y codificación visual del dominio |
| **Semana 5** | "Proyecto de Django debidamente configurado. Los modelos creados y registrados en el Sitio de Administración de Django" | `4c851a6` (auditoría y reestructura `core` → `tasks`) y `96813bf` (`feat(tasks): domain model, migrations and Django Admin`) | `config/settings.py` operativo, `Task` y `Tag`, `0001_initial.py`, `TaskQuerySet` con las dos políticas, `TaskAdmin` y `TagAdmin` |
| **Semana 7** | "Enrutamientos, vistas y autenticación. El sitio ya debe ser funcional, pero con plantillas muy básicas" | `b9565c6` (`feat(tasks): auth, CRUD, visibility, sorting, filtering and Bootstrap UI`) | Las 8 rutas, las 9 CBVs, `LoginView`/`LogoutView`, autorización a nivel de queryset, orden y filtro con whitelist, y los siete defectos corregidos |
| **Semana 9** | Cierre y evaluación | `e9f1041` (`test(tasks): 249 automated tests across models, forms, views, permissions and filters`) | 249 tests verdes y esta documentación |

### Desviación declarada en el corte de Semana 3

La consigna separa la maqueta visual estática de la aplicación funcional. Este proyecto
entregó la capa de diseño **junto con el corte de Semana 7**, no como un incremento
separado con datos ficticios.

El motivo está en `docs/milestones/week-3.md` y se resume aquí: una maqueta estática
separada habría sido código desechable. Django Templates renderiza sin datos reales, así
que la capa de diseño (estructura, jerarquía visual, estados) se resolvió directamente
contra el modelo definitivo. Las decisiones de diseño son las mismas que se habrían tomado
en la maqueta; lo que se evitó fue mantener dos versiones del HTML que divergen con el
tiempo.

La desviación está registrada, no oculta.

## 12. Solución de problemas

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'django'` | El venv no está activado o las dependencias no se instalaron | `source .venv/bin/activate` y `pip install -r requirements.txt` (o `uv sync`) |
| `no such table: tasks_task` | Faltan migraciones | `python manage.py migrate` |
| `You have N unapplied migration(s)` | El modelo cambió sin migrar | `python manage.py makemigrations && python manage.py migrate` |
| La navbar se ve sin estilos | Falta `collectstatic` o el servidor no sirve `static/` | `python manage.py runserver` ya sirve los estáticos en desarrollo; en producción, `collectstatic` |
| `Too many fields to hash` al migrar desde otro SQLite | Cambió el esquema de una base vieja | Recrear la base: `rm db.sqlite3 && python manage.py migrate` |
| `no changes detected` al hacer `makemigrations` | El modelo y las migraciones ya coinciden, que es el estado deseado | Nada que hacer |
| Un test falla solo con `DEBUG=False` | Hay código que depende del traceback de Django | Revisar el test, no la configuración |
| `fixture 'db.sqlite3' not found` | La ruta se ejecutó desde otro directorio | `manage.py` asume que la CWD es la raíz del proyecto |
