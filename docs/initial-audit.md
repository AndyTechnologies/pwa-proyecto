# Auditoría inicial del repositorio

**Proyecto:** Task Manager — Proyecto Final de Programación Web Avanzada
**Fecha:** Fase 0, previa a cualquier modificación de código
**Método:** inspección del árbol de archivos, lectura de la configuración, ejecución de
`manage.py check` y verificación del lockfile.

## 1. Estado de partida

El repositorio **no estaba vacío** al iniciar el proyecto académico. Contiene un
esqueleto Django funcional creado previamente como base de la asignatura, con un único
commit (`fbbb453`).

| Componente | Estado encontrado |
| --- | --- |
| Proyecto Django | Presente y operativo (`config/`, `manage.py`) |
| Aplicación | Una sola: `core` |
| Modelos de dominio | **Ninguno** (`core/models.py` vacío) |
| Formularios | **Ninguno** |
| Vistas | Una sola, `core.views.home` (function-based) |
| Plantillas | 2 (`core/base.html`, `core/home.html`) |
| Estáticos | Bootstrap 5.3.8 vendorizado en `core/static/core/` (reubicado después a `static/css/` y `static/js/`, ver §6) |
| Tests | **Ninguno** (`core/tests.py` vacío) |
| Documentación | Solo `README.md` del esqueleto |
| Autenticación | No enrutada; solo `admin/` expuesto |
| Migraciones | Solo las de apps de Django (`contenttypes`, `auth`, `sessions`, `admin`) |

## 2. Configuración detectada

- `INSTALLED_APPS`: las 6 apps de Django más `core`.
- `DATABASES`: SQLite en `db.sqlite3` (base local, sin configuración externa).
- `AUTH_PASSWORD_VALIDATORS`: los 4 validadores por defecto de Django activos.
- `MIDDLEWARE`: la pila estándar completa, **incluido `CsrfViewMiddleware`**.
- `TEMPLATES`: `APP_DIRS: True` y `DIRS: []` — las plantillas solo se resuelven desde
  dentro de las apps.
- `LANGUAGE_CODE = 'en-us'`, `TIME_ZONE = 'UTC'`.
- `STATIC_URL = 'static/'` **sin `STATIC_ROOT`**.
- `DEBUG = True` y `ALLOWED_HOSTS` vacío (valores por defecto de desarrollo).

## 3. Dependencias

`pyproject.toml` + `uv.lock` fijan exclusivamente:

```
django==6.1.1
asgiref==3.12.1
sqlparse==0.6.0
```

`requirements.txt` replica el mismo conjunto para el camino `pip` + `venv`.
**No hay Django REST Framework**, y no hay que agregarlo: la consigna lo prohíbe.

## 4. Contraste con la consigna

| Requisito de la consigna | Estado inicial | Brecha |
| --- | --- | --- |
| 1. Responsive + Bootstrap 5 | Parcial | Bootstrap vendorizado, pero una sola vista sin UI real |
| 2. CRUD de tareas con título/descripción/fecha/prioridad | Ausente | Sin modelos ni vistas |
| 3. Lista ordenada por fecha/prioridad + filtro de estado | Ausente | — |
| 4. Etiquetas y búsqueda por etiqueta | Ausente | — |
| 5. Registro, login, logout | Ausente | No enrutado |
| 6. CRUD solo sobre tareas propias | Ausente | — |
| 7. Visibilidad solo lectura / pública | Ausente | — |
| 8. Buenas prácticas (modelos, vistas, formularios, validación, seguridad) | Ausente | — |
| Sin DRF | **Cumplido** | — |
| Todas las vistas CBV | **Incumplido** | `core.views.home` es function-based |

## 5. Brecha architectural principal

La única vista existente es **function-based**, lo que viola directamente la restricción
más dura de la consigna ("todas las vistas tienen que ser del tipo Vistas Basadas en
Clases"). No es un detalle recuperable: obliga a reescribir esa vista.

## 6. Decisiones de reestructuración y su justificación

La consigna propone una estructura de referencia con una app `tasks/` y `templates/` y
`static/` en la raíz del proyecto. La estructura existente usa una app `core` con sus
propios `templates/` y `static/`.

**Decisión:** migrar de `core` a `tasks`, con `templates/` y `static/` en la raíz.

**Justificación:**

1. `core` no contiene lógica de dominio: es un marcador de posición con una sola vista
   de saludo. No hay ningún activo real que conservar ni historial que preservar (el
   repositorio tiene un único commit).
2. `tasks` comunica el dominio de la consigna, lo que ayuda a la evaluación académica.
3. `templates/` y `static/` en la raíz evitan colisiones de nombres entre apps y siguen
   la convención que un profesor esperaría en un proyecto de este tamaño.

Se conserva todo el trabajo real existente: el proyecto `config`, `manage.py`, el
`README.md` (actualizado) y los assets de Bootstrap 5.3.8, que se reubican en
`static/css/` y `static/js/`. Se registra como **ADR-007**.

## 7. Riesgos identificados

| Riesgo | Mitigación |
| --- | --- |
| IDOR: acceso a tareas ajenas por URL directa | Política de queryset por propietario + tests de regresión |
| Autorización implementada solo en plantillas | Verificación server-side en cada CBV mutable |
| Parámetros de ordenamiento/filtrado inyectando campos arbitrarios | Whitelist en servidor |
| Plantillas piramidales con lógica de autorización | Plantilla solo presenta; el servidor autoriza |
| Passwords o secretos en el repositorio | `.gitignore` cubre `.env`; sin secretos en el código |

## 8. Conclusión

El punto de partida es un esqueleto limpio y sin deuda técnica. No hay código previo que
migrar ni preservar salvo la view function-based, que debe reemplazarse por una CBV de
todos modos. La brecha principal es de dominio: prácticamente todos los requisitos
funcionales están por construir desde cero.
