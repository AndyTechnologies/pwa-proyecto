# Task Manager

Aplicación web de gestión de tareas personales y profesionales, construida con
**Django + SQLite + Bootstrap 5**. Cada usuario administra sus propias tareas y decide
su grado de exposición: privadas, compartidas en solo lectura con otros usuarios
registrados, o públicas para cualquier visitante.

**Proyecto final de Programación Web Avanzada** — Facultad de Ingeniería Informática,
CUJAE.

> Este README responde *cómo funciona el proyecto*. El *por qué* —las decisiones, las
> alternativas descartadas y sus costos— está en [`docs/decisions.md`](docs/decisions.md)
> y en el [paper académico](paper/paper.md).

## Características

- **Gestión de tareas** con título, descripción, fecha de vencimiento y prioridad
  (baja / media / alta), creación, edición, borrado con confirmación y marcado como
  completada o pendiente.
- **Autenticación**: registro, inicio de sesión y cierre de sesión.
- **Propiedad estricta**: las operaciones de creación, edición y borrado solo se permiten
  sobre las tareas del propio usuario, verificadas en el servidor.
- **Visibilidad de tres niveles**: privada, compartida con usuarios registrados y
  pública. La visibilidad concede **lectura**, nunca escritura.
- **Ordenamiento y filtrado** por fecha de vencimiento o prioridad, y por estado
  (todas, pendientes, completadas), con desempate determinista.
- **Etiquetas** reutilizables entre tareas, con búsqueda por etiqueta.
- **Interfaz responsive** con Bootstrap 5.3.8 vendorizado, sin depender de un CDN.
- **Administración de Django** configurada con búsqueda, filtros y autocompletado.
- **249 pruebas automatizadas**, todas en verde.

## Stack

| Componente    | Versión / elección                        |
| ------------- | ----------------------------------------- |
| Python        | >= 3.12                                   |
| Django        | 6.1.1                                     |
| Base de datos | SQLite (desarrollo)                       |
| UI            | Bootstrap 5.3.8 (vendorizado en el repo)  |
| Dependencias  | `uv` o `pip` + `venv`                     |
| Pruebas       | Runner nativo de Django (sin pytest)      |

Sin Django REST Framework, por restricción de la consigna. Sin dependencias de terceros
salvo Django: Bootstrap está vendorizado, no es una dependencia de Python.

## Requisitos

- Python 3.12 o superior en el `PATH`.
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) si se opta por el
  camino A. No es necesario en el camino B.

## Instalación

### Opción A — con `uv` (recomendado)

```bash
uv sync                                        # instala y crea .venv desde uv.lock
uv run python manage.py migrate                # crea db.sqlite3
uv run python manage.py createsuperuser        # usuario para /admin/
uv run python manage.py runserver              # http://127.0.0.1:8000
```

### Opción B — con `pip` + `venv`

```bash
python3 -m venv .venv
source .venv/bin/activate                      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Desactivar el entorno al terminar con `deactivate`.

Ambas opciones llevan al mismo servidor en <http://127.0.0.1:8000/>.

## Uso

1. Registrarse en `/register/`.
2. Iniciar sesión en `/login/`.
3. Crear una tarea en `/tasks/create/`.
4. Filtrar y ordenar desde `/tasks/` con los controles del listado.
5. Compartir: desde la edición de una tarea, elegir **Compartida con registradas**
   (cualquier usuario autenticado la ve) o **Pública** (también los visitantes
   anónimos).
6. Ver lo compartido con uno mismo en `/tasks/shared/` y lo público en `/tasks/public/`.

El cierre de sesión es un formulario `POST`, no un enlace: Django 5 eliminó el cierre por
`GET` por razones de seguridad.

## Administración

Con el superusuario creado en la instalación, `/admin/` permite listar, buscar, filtrar y
editar tareas y etiquetas.

## Pruebas

```bash
uv run python manage.py test tasks          # camino A
python manage.py test tasks                 # camino B, con el venv activo
```

**249 pruebas**, todas en verde. Desglose:

| Archivo             | Pruebas | Cubre                                              |
| ------------------- | ------: | -------------------------------------------------- |
| `test_models.py`    |      33 | Defaults, orden, *slug*, M2M, cascada             |
| `test_forms.py`     |      56 | Campos obligatorios, enums, etiquetas              |
| `test_views.py`     |      53 | CRUD completo, auth, mensajes                      |
| `test_permissions.py` |     45 | Matriz de autorización y defensa IDOR              |
| `test_filters.py`   |      34 | Listas blancas, orden determinista, inyección      |
| `test_regressions.py` |     28 | Un archivo por cada defecto corregido              |

## Estructura del proyecto

```
.
├── config/                  proyecto Django: settings, urls, wsgi, asgi
├── tasks/                   aplicación de dominio
│   ├── models.py            Task, Tag, Priority, Visibility, políticas de queryset
│   ├── views.py             9 Vistas Basadas en Clases
│   ├── forms.py             TaskForm, RegisterForm
│   ├── urls.py              rutas con nombre bajo el namespace `tasks`
│   ├── admin.py             registro en el sitio de administración
│   ├── tests/               249 pruebas
│   └── migrations/
├── templates/               base.html, registration/, tasks/
├── static/css|js/           Bootstrap 5.3.8 vendorizado
├── docs/                    documentación técnica, ADRs y milestones
│   ├── requirements.md  architecture.md  data-model.md
│   ├── security.md      testing.md        development.md
│   ├── decisions.md     traceability.md   final-compliance-report.md
│   ├── initial-audit.md
│   ├── adr/             8 registros de decisión
│   └── milestones/      un documento por corte
├── paper/                   paper académico y referencias
├── manage.py  pyproject.toml  uv.lock  requirements.txt
```

## Documentación

| Documento | Para qué |
| --- | --- |
| [`docs/requirements.md`](docs/requirements.md) | Requisitos funcionales, no funcionales y no-objetivos |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura, flujo de petición, diagramas |
| [`docs/data-model.md`](docs/data-model.md) | Diagrama ER, índices, normalización |
| [`docs/security.md`](docs/security.md) | Amenazas, IDOR, CSRF, inyección, límites |
| [`docs/testing.md`](docs/testing.md) | Estrategia y cobertura de las 249 pruebas |
| [`docs/development.md`](docs/development.md) | Guía de desarrollo y convenciones |
| [`docs/decisions.md`](docs/decisions.md) | Resumen de decisiones y ambigüedades resueltas |
| [`docs/traceability.md`](docs/traceability.md) | Requisito → implementación → test → documentación |
| [`docs/final-compliance-report.md`](docs/final-compliance-report.md) | Auditoría contra la consigna |
| [`docs/adr/`](docs/adr/) | 8 Architecture Decision Records |
| [`docs/milestones/`](docs/milestones/) | Qué entregó cada corte |
| [`paper/paper.md`](paper/paper.md) | Paper académico con el razonamiento técnico |

## Restricciones académicas

- **No se usa Django REST Framework**, por indicación expresa de la consigna. La
  aplicación es server-rendered y no expone API.
- **Todas las vistas son Vistas Basadas en Clases.** No existe ninguna vista basada en
  función.
- **SQLite** es la base de datos de desarrollo. No es apropiada para producción.
- **El proyecto no está endurecido para producción**: `DEBUG=True` y `ALLOWED_HOSTS`
  vacío. Ver [`docs/security.md`](docs/security.md).

## Añadir una dependencia

Mantener los dos caminos de instalación sincronizados:

```bash
uv add <paquete>              # actualiza pyproject.toml y uv.lock
uv pip freeze > requirements.txt
```

## Licencia

Bootstrap 5.3.8 se distribuye bajo licencia MIT e está incluido en `static/`.
