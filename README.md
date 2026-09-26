# pwa-proyecto

Esqueleto de proyecto Django mínimo y funcional: **Django + SQLite + Bootstrap 5**.

Dos caminos de instalación soportados — [`uv`](https://docs.astral.sh/uv/) (recomendado) y `pip` + `venv` — ambos fijados al mismo conjunto de dependencias.

## Stack

| Componente    | Versión / elección                            |
| ------------- | --------------------------------------------- |
| Python        | >= 3.12                                       |
| Django        | 6.1.1                                         |
| Base de datos | SQLite (valor por defecto en desarrollo)      |
| UI            | Bootstrap 5.3.8 (vendorizado, sin CDN)        |
| Dependencias  | `uv` (`pyproject.toml` + `uv.lock`) o `pip` (`requirements.txt`) |

## Estructura

```
.
├── config/                  # Proyecto Django (settings, urls, wsgi, asgi)
├── core/                    # App principal: vistas, plantillas, estáticos
│   ├── static/core/         # Bootstrap 5.3.8 vendorizado (css/ + js/)
│   └── templates/core/      # base.html + home.html
├── manage.py
├── pyproject.toml           # Camino uv
├── uv.lock
└── requirements.txt         # Camino pip + venv
```

---

## Opción A — con `uv` (recomendado)

Requiere [`uv`](https://docs.astral.sh/uv/getting-started/installation/).
`uv` se encarga del entorno virtual, el lockfile y las dependencias.

```bash
# 1. Instalar dependencias (crea .venv/ automáticamente desde uv.lock)
uv sync

# 2. Aplicar las migraciones de la base de datos (crea db.sqlite3)
uv run python manage.py migrate

# 3. Crear un usuario admin (opcional, para /admin/)
uv run python manage.py createsuperuser

# 4. Levantar el servidor de desarrollo en http://127.0.0.1:8000
uv run python manage.py runserver
```

Abrir <http://127.0.0.1:8000/>.

Comandos habituales:

```bash
uv run python manage.py test        # ejecutar los tests
uv run python manage.py check       # verificaciones del sistema
uv add <paquete>                    # agregar una dependencia (actualiza pyproject.toml + uv.lock)
```

## Opción B — con `pip` + `venv`

No hace falta `uv`. Requiere Python 3.12+ en el `PATH`.

```bash
# 1. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar las migraciones de la base de datos (crea db.sqlite3)
python manage.py migrate

# 4. Crear un usuario admin (opcional, para /admin/)
python manage.py createsuperuser

# 5. Levantar el servidor de desarrollo en http://127.0.0.1:8000
python manage.py runserver
```

Desactivar el entorno al terminar:

```bash
deactivate
```

> A partir de ahí, cada llamada `python manage.py ...` dentro del entorno
> virtual activado funciona igual que las llamadas `uv run python manage.py ...`.

---

## Mantener ambos caminos sincronizados

`requirements.txt` se genera desde el lockfile de `uv`. Después de cambiar
dependencias con `uv add`, regenerarlo:

```bash
uv pip freeze > requirements.txt
```

## Notas

- **Bootstrap está vendorizado.** `core/static/core/css/bootstrap.min.css` y
  `core/static/core/js/bootstrap.bundle.min.js` son Bootstrap 5.3.8 (MIT),
  incluidos en el repositorio. La aplicación renderiza y funciona sin acceso a
  red y sin depender de un CDN. Las plantillas los referencian mediante la
  etiqueta `{% static %}` de Django.
- **SQLite es el valor por defecto en desarrollo.** `config/settings.py` no
  necesita configuración de base de datos para trabajar en local; `db.sqlite3`
  lo crea `migrate` y está en `.gitignore`.
- **Sin hardening para producción.** `DEBUG=True` y el `ALLOWED_HOSTS` por
  defecto son marcadores de posición: ajustarlos antes de cualquier despliegue
  real.
- `core/tests.py` está vacío a propósito; agregar los tests ahí o en
  `core/tests/`.
