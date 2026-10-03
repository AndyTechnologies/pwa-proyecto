# E2E tests con Playwright (pytest + live_server)

**Feature**: `e2e-playwright-tests`
**Rama**: `feat/e2e-playwright-tests`
**Objetivo**: tests end-to-end reales contra un servidor Django real, cubriendo
los contratos visuales que la suite unitaria sólo puede verificar en el
código fuente: navbar, gate del link de admin, y carga de páginas.

## Decisiones de arquitectura

- **`live_server` de pytest-django en vez del dev server**: los tests levantan
  su propio servidor contra la **BD de test**. Nunca tocan la BD real del
  proyecto ni dependen de `./run.sh`. Nada de credenciales de la BD dev.
- **Usuarios creados vía ORM en la BD de test**: staff y no-staff con
  contraseña conocida, dentro del fixture. El login se hace por la UI
  (formulario real), no por `client.login` — eso es lo que hace que sea E2E.
- **Firefox** como browser: el CDN de Playwright devuelve 403 geográfico para
  Chrome (`Access denied ... not available in your location`); Firefox descarga
  OK desde otro endpoint.
- **`DJANGO_SETTINGS_MODULE` en `[tool.pytest.ini_options]`**: pytest-django
  necesita settings para `live_server` y `django_user_model`.
- **Sin `playwright.config.ts`**: esa config es para el runner TS de
  Playwright; aquí se usa pytest, el archivo sería ruido.

## Tasks

- [x] 1. Preparar entorno: rama, `pytest-django`, config pytest en `pyproject.toml`.
- [x] 2. Escribir `tests-e2e/auth_test.py`: home carga, navbar visible, staff
      ve "Administrar sitio", no-staff y anónimo no lo ven (con login real por UI).
- [x] 3. Ejecutar: E2E verdes con Firefox + suite Django completa (330) verdes.
- [x] 4. Evidencia en este doc + commit conventional.

## Evidencia (commits)

| Commit | Task | Outcome |
| --- | --- | --- |
| `ea9004b` | 1–4 | E2E 6/6 con Firefox; suite Django 330 verdes; control negativo verificado. |

## Contenido de los tests (6)

| Test | Contrato |
| --- | --- |
| `test_home_page_loads` | La home carga y el nav está visible |
| `test_navigation_has_session_controls` | Anónimo ve "Iniciar sesión" en el nav |
| `test_anonymous_does_not_see_admin_link` | `/tasks/` redirige a login y no muestra el link |
| `test_staff_user_sees_the_admin_link` | Staff logueado por UI ve "Administrar sitio" |
| `test_non_staff_user_does_not_see_it` | No-staff logueado no lo ve (+ control positivo del nav) |
| `test_the_admin_link_points_at_the_admin` | El href apunta a `/admin/` |

## Defectos encontrados durante el setup

1. **`ScopeMismatch` por pisar `base_url`**: mi fixture function-scoped
   chocaba con la session-scoped de `pytest-base-url`. Renombrada a `server_url`.
2. **`SynchronousOnlyOperation` en el setup de la BD**: la sync API de
   Playwright deja su event loop "running" en el thread principal durante toda
   la sesión (arquitectura greenlet: `run_until_complete` nunca retorna porque
   el main greenlet sale por callback). Django interpreta eso como contexto
   async y bloquea `create_test_db` y los fixtures de usuario. Falso positivo:
   todo lo aquí es síncrono y el live server corre en su propio thread.
   Solución: `DJANGO_ALLOW_ASYNC_UNSAFE=1` en `conftest.py` (documentado por
   Django para este caso). Verificado con un probe aislado: sin la variable,
   todo errora en setup; con ella, todo pasa.
3. **`conftest.py` pisaba `django_db_setup`/`django_db_blocker`** de
   pytest-django — fixtures que `live_server` necesita. El conftest se vació a
   documentación + la variable de entorno.
4. **Strict mode en locators**: `get_by_text("Mis tareas")` matcheaba el link
   del nav y el `h1` de la misma página. Corregido a `get_by_role("link", ...)`.

## Control negativo (obligatorio)

Gate `{% if user.is_staff %}` eliminado de `base.html` a mano →
`test_non_staff_user_does_not_see_it` **falla**. Restaurado → 6/6 verdes.
El test anónimo no falló en ese experimento y es correcto: el link vive dentro
de la rama `{% if user.is_authenticated %}` del bloque de sesión, así que un
anónimo no lo ve ni siquiera con el gate eliminado.

## Cómo correr

```bash
./run.sh   # no hace falta; los tests levantan su propio server
uv run python -m pytest tests-e2e/ --browser firefox
```

Chromium no está instalado (bloqueo geográfico del CDN): el fixture
parametrizado `[chromium]` no corre hasta que `playwright install chromium`
funcione desde esta red.

## Riesgos / pendientes

- La suite E2E depende de `DJANGO_ALLOW_ASYNC_UNSAFE`; si en el futuro se
  migra a la async API de Playwright, revisar la variable.
- El parámetro `[chromium]` queda coleccionado pero no ejecutable sin el
  binario; usar siempre `--browser firefox` mientras siga el bloqueo.
