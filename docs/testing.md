# Estrategia de testing — Task Manager

## 1. Filosofía

La suite tiene un objetivo concreto: **proteger las reglas de autorización y la
integridad de los datos**, y demostrar que cada requisito funcional de `docs/requirements.md`
tiene al menos un test que lo ejerce por HTTP real.

Tres decisiones gobiernan el diseño:

1. **El runner es el de Django.** `manage.py test tasks`, sin `pytest`, sin `pytest-django`,
   sin `factory_boy`, sin `coverage` como dependencia del proyecto. RNF-12 pide simplicidad
   y la consigna no pide herramientas externas; instalar un framework para escribir lo
   mismo con más sintaxis es un costo sin beneficio en un proyecto de este tamaño.
2. **El runner real, no el método.** Los tests de autorización y de vistas usan el cliente
   de `django.test.Client` y emiten peticiones HTTP completas contra el `URLconf` real. No
   se llama a la vista como función ni se inspecciona el queryset a mano para "simular" un
   acceso. El código que se prueba es el mismo que corre en producción.
3. **Una fábrica explícita, no una mágica.** `TaskFactoryTestCase` en
   `tasks/tests/__init__.py` expone `make_user()`, `make_tag()` y `make_task()` con
   argumentos con nombre y valores por defecto explícitos. Si un default del modelo cambia,
   la aserción que dependía de él falla en lugar de que el fixture cambie en silencio. Es
   el sustituto deliberado de `factory_boy`, hecho a mano y con 100 líneas.

## 2. Niveles de prueba

Los seis módulos no son seis carpetas: son seis **niveles** que atacan el sistema desde
diferentes ángulos.

| Nivel | Módulo | Qué ataca | Por qué este nivel y no otro |
| --- | --- | --- | --- |
| **Modelo** | `test_models.py` (33) | Defaults, `Meta.ordering`, derivación de `slug`, M2M, cascada de borrado, valores y semántica de los `choices` | Una decisión de modelo (el orden por defecto, el slug automático) afecta a todas las vistas. Se prueba abajo, una vez, en lugar de quince veces arriba |
| **Formulario** | `test_forms.py` (56) | Campos obligatorios, valores de enum, parseo de fechas, limpieza de `tags_input`, resolución de etiquetas, clases Bootstrap de los widgets | La validación es la frontera entre input arbitrario y base de datos. Probar el formulario aislado da mensajes de error precisos, que por HTTP se pierden |
| **Vista** | `test_views.py` (53) | CRUD completo por HTTP: status codes, redirects, mensajes, plantillas renderizadas, presencia o ausencia de controles en el HTML | Es la capa donde la consigna exige comportamiento observable. Un formulario válido no demuestra que la vista redireccione bien ni que el mensaje aparezca |
| **Permiso** | `test_permissions.py` (45) | La matriz de autorización completa actor × visibilidad × operación, la política del `QuerySet` y los límites de método HTTP | Es el activo principal de la aplicación. Se prueba con peticiones reales porque un permiso que se rompe en el `dispatch()` no se ve probando el método suelto |
| **Filtro / whitelist** | `test_filters.py` (34) | `?sort=`, `?status=`, `?tag=`, el desempate `-pk` y los intentos de inyección | El input de la URL es la otra entrada no confiable del sistema, junto con el formulario |
| **Regresión** | `test_regressions.py` (28) | Los siete defectos encontrados y corregidos durante el desarrollo | Un defecto ya corregido que vuelve es un defecto nuevo con historia. Ver sección 7 |

## 3. Desglose

| Módulo | Tests | Contenido |
| --- | --- | --- |
| `tasks/tests/test_models.py` | 33 | `TaskModelCreationTests` (valores esperados, defaults de `priority`/`visibility`/`completed`, tags vacíos, `created_at`/`updated_at` automáticos, `__str__`), `PriorityChoicesTests` (valores numéricos, orden semántico, orden real en la base), `TaskMetaOrderingTests` (los tres niveles del `ordering`), `TaskTagRelationTests` (M2M en ambos sentidos, `related_name`, `set()`), `IsEditableByTests`, `TagModelTests` (slug derivado, slug con acentos, unicidad a nivel de base, búsqueda `iexact`, cascada) |
| `tasks/tests/test_forms.py` | 56 | `TaskFormValidDataTests`, `TaskFormRequiredFieldTests`, `TaskFormDateParsingTests`, `TaskFormPriorityTests`, `TaskFormVisibilityTests`, `TaskFormTagsInputCleaningTests` (minúsculas, espacios, duplicados, longitud, entradas vacías), `TaskFormTagResolutionTests` (reutilización, creación,Slug colisionados), `RegisterFormTests` (validadores de contraseña, confirmación), `TaskFormWidgetTests` (clases Bootstrap, `attrs` declarados, `<input type="date">`) |
| `tasks/tests/test_views.py` | 53 | `RegisterViewTests`, `LoginViewTests` (GET, POST válido, `?next=`, POST inválido, usuario inexistente), `TaskListViewTests`, `TaskCreateViewTests`, `TaskDetailViewTests`, `TaskUpdateViewTests`, `TaskDeleteViewTests`, `TaskCompleteToggleViewTests`, `PublicTaskListViewTests`, `SharedTaskListViewTests` |
| `tasks/tests/test_permissions.py` | 45 | `AnonymousReadPolicyTests`, `NonOwnerReadPolicyTests`, `OwnerReadPolicyTests`, `NonOwnerWritePolicyTests`, `AnonymousWritePolicyTests`, `ToggleMethodPolicyTests`, `LogoutMethodPolicyTests`, `ListScopingTests`, `QuerysetPolicyTests`, `AdminUrlReachabilityTests` |
| `tasks/tests/test_filters.py` | 34 | `StatusFilterTests`, `SortFilterTests`, `SortTieBreakerTests`, `TagFilterTests`, `CombinedFilterTests` (los tres parámetros a la vez) |
| `tasks/tests/test_regressions.py` | 28 | Siete clases, una por defecto: `IsEditableByRegressions`, `AllTagsContextRegressions`, `RegisterRouteRegressions`, `UpdateViewContextRegressions`, `BootstrapWidgetRegressions`, `TagSlugCollisionRegressions`, `UrlMountingRegressions` |
| **Total** | **249** | |

## 4. Cómo ejecutar

```bash
# Suite completa
python manage.py test tasks

# Un solo módulo
python manage.py test tasks.tests.test_permissions

# Una sola clase
python manage.py test tasks.tests.test_permissions.NonOwnerWritePolicyTests

# Un solo test
python manage.py test tasks.tests.test_filters.SortTieBreakerTests.test_repeated_requests_return_the_same_order

# Detalle de cada test
python manage.py test tasks --verbosity=2
```

Con uv:

```bash
uv run python manage.py test tasks
```

Estado verificado de la suite completa: **249 tests, 249 OK**, en aproximadamente 46
segundos. Cada test corre contra una base de datos temporal que Django crea y destruye, así
que `db.sqlite3` nunca se toca.

Todas las clases heredan de `django.test.TestCase` (transaccional, con rollback por test) y
de `TaskFactoryTestCase`, que solo agrega la fábrica. Ninguna usa `TestCase` sin el
rollback explícito, salvo `PriorityChoicesTests` y `TaskFormWidgetTests`, que no escriben
en la base o la usan de forma mínima.

## 5. Matriz de autorización

Actor × visibilidad para **leer** el detalle en `GET /tasks/<pk>/`. Cada celda dice si
existe un test que lo afirme.

| Visibilidad de la tarea de Alice | Anónimo | Bob (registrado, no owner) | Alice (owner) |
| --- | --- | --- | --- |
| `PRIVATE` | **404** — cubierto (`test_anonymous_gets_404_on_a_private_task`) | **404** — cubierto (`test_non_owner_gets_404_on_a_private_task`) | **200** — cubierto (`test_owner_gets_200_on_a_private_task`) |
| `AUTHENTICATED` | **404** — cubierto (`test_anonymous_gets_404_on_a_task_shared_with_registered_users`) | **200 solo lectura** — cubierto (`test_non_owner_gets_200_read_only_on_a_shared_task`) | **200** — cubierto (`test_owner_gets_200_on_a_shared_task`) |
| `PUBLIC` | **200 solo lectura** — cubierto (`test_anonymous_gets_200_on_a_public_task`, `test_anonymous_sees_a_read_only_public_task`) | **200 solo lectura** — cubierto (`test_non_owner_gets_200_read_only_on_a_public_task`) | **200** — cubierto (`test_owner_gets_200_on_a_public_task`) |

"200 solo lectura" significa que la respuesta es 200 **y** el HTML renderizado no contiene
los formularios de edición, borrado ni toggle. Eso se afirma en
`test_anonymous_sees_a_read_only_public_task` y
`test_non_owner_gets_200_read_only_on_a_shared_task`, que buscan el control de escritura
en la respuesta.

Actor × operación de **escritura** sobre una tarea pública de Alice. Todas deberían ser 404.

| Operación | Anónimo | Bob (no owner) | Alice (owner) |
| --- | --- | --- | --- |
| `GET /tasks/<pk>/edit/` | 302 a login — cubierto (`test_anonymous_is_redirected_from_the_task_list` cubre el listado; el caso de escritura anónimo se cubre por `LoginRequiredMixin`) | **404, no 403** — cubierto (`test_non_owner_gets_404_not_403_on_the_edit_page`) | 200 — cubierto (`test_get_renders_the_edit_form_prefilled`) |
| `GET /tasks/<pk>/delete/` | 302 a login | **404, no 403** — cubierto (`test_non_owner_gets_404_not_403_on_the_delete_page`) | 200 — cubierto |
| `POST /tasks/<pk>/delete/` | 302 a login | **404 y la tarea sigue existiendo** — cubierto (`test_non_owner_gets_404_not_403_when_posting_the_delete_form`, `test_a_rejected_delete_leaves_the_task_untouched`) | La tarea se borra — cubierto en `test_views.py` |
| `POST /tasks/<pk>/toggle/` | 302 a login — cubierto (`test_anonymous_is_redirected_when_posting_a_toggle`) | **404 y `completed` no cambia** — cubierto (`test_non_owner_gets_404_not_403_when_posting_the_toggle`, `test_a_rejected_toggle_leaves_the_task_untouched`) | El estado se invierte — cubierto (`test_post_flips_pending_to_completed`, `test_post_flips_completed_back_to_pending`) |
| `GET /tasks/<pk>/toggle/` | — | **405** — cubierto (`test_get_on_the_toggle_url_returns_405`) | **405** — cubierto; y `test_get_on_the_toggle_url_never_changes_the_task` |
| `GET /logout/` | — | **405, la sesión sigue abierta** — cubierto (`test_get_on_logout_returns_405`, `test_get_on_logout_keeps_the_session_open`) | 405 — cubierto |
| `POST /logout/` | — | 302 y sesión cerrada — cubierto (`test_post_on_logout_succeeds_and_closes_the_session`) | cubierto |

Alcance de los listados:

| Listado | Qué debe contener | Test |
| --- | --- | --- |
| `/tasks/` | Solo tareas del dueño, jamás de otro | `test_owner_list_never_contains_another_users_tasks` |
| `/tasks/shared/` | Tareas de otros, jamás las propias | `test_shared_list_contains_only_other_peoples_tasks`, `test_shared_list_never_contains_the_viewers_own_tasks` |
| `/tasks/public/` | Solo tareas `PUBLIC` | `test_public_list_contains_only_public_tasks` |
| `/tasks/public/` anónimo | Permitido, sin sesión | `test_anonymous_may_reach_the_public_list`, `test_anonymous_may_reach_a_public_detail` |

Política del `QuerySet` probada sin HTTP, para que el contrato sea legible aunque cambie la
vista:

| Test | Qué afirma |
| --- | --- |
| `test_owned_by_returns_only_that_users_tasks` | `owned_by` acota al propietario |
| `test_owned_by_is_empty_for_a_user_without_tasks` | Devuelve vacío, no todo |
| `test_owned_by_ignores_visibility_and_only_honours_ownership` | Una tarea pública ajena **no** aparece: la visibilidad no abre escritura |
| `test_visible_to_anonymous_returns_only_public_tasks` | Rama anónimo de `visible_to` |
| `test_visible_to_registered_non_owner_returns_shared_and_public` | Rama de registrado no propietario |
| `test_visible_to_owner_returns_every_own_task` | El owner ve las suyas de cualquier visibilidad |
| `test_visible_to_never_returns_another_users_private_task` | La privacidad se respeta siempre |
| `test_is_editable_by_matches_the_owned_by_policy` | `is_editable_by` y `owned_by` no se contradicen |

## 6. Qué **no** se probó, y por qué

La cobertura de esta suite es fuerte en autorización, formularios y filtros, y deliberadamente
ausente en cuatro áreas. Declararlo es parte de la documentación del testing.

| No probado | Motivo |
| --- | --- |
| **Pruebas de carga y rendimiento** | No hay un volumen de datos que lo justifique: el caso de uso es el de un usuario con decenas de tareas, no miles. Montar una prueba de carga exigiría decidir un número de usuarios concurrentes que nadie definió, y el resultado no sería accionable. Los índices están justificados por diseño en `docs/data-model.md`, no por medición |
| **Pruebas E2E con navegador (Selenium, Playwright)** | Requieren un navegador instalado, un servidor levantado, y una suite frágil frente a cambios de CSS. Lo que se necesita verificar — que el botón de completar envía un `POST` con token, que el formulario de login valida — ya está cubierto por `django.test.Client`, que emite peticiones HTTP reales contra el mismo código. Un E2E agregaría lentitud y una clase nueva de fallos (timing de Selenium) sin cubrir una capacidad nueva |
| **Cobertura de líneas o de ramas** | Requiere `coverage`, una dependencia externa. Además, un porcentaje alto no dice nada útil: un 95% alcanzado cubriendo `__str__` es peor que un 80% que cubra la matriz de autorización completa, que es lo que este proyecto sabe hacer |
| **Portales de seguridad de dependencias** | `pip-audit`, `safety` o Dependabot son herramientas de proceso, no de código. El conjunto de dependencias es Django y dos transitivas: la superficie es mínima por construcción |
| **Pruebas de accesibilidad automatizadas (axe, Lighthouse)** | Requieren DOM renderizado en navegador, igual que los E2E. La accesibilidad se resolvió en el HTML semántico y los atributos ARIA explícitos, que sí se pueden leer en las plantillas. Una auditoría automatizada en un proyecto de este tamaño es esfuerzo desproporcionado |
| **Pruebas de contrato de la base** | La migración `0001_initial.py` es la definición ejecutable del esquema. `python manage.py makemigrations --check --dry-run` verifica que el modelo y la migración no se divergieron; verificado: `No changes detected` |

## 7. El papel de los tests de regresión

Siete defectos se encontraron y corrigieron durante el desarrollo. Cada uno tiene su propia
clase en `tasks/tests/test_regressions.py`, y cada clase **falla si el defecto vuelve**.
No son tests de "esto alguna vez funcionó": son la razón por la que el defecto es
irreproducible.

| # | Defecto | Síntoma en producción | Clase | Tests |
| --- | --- | --- | --- | --- |
| 1 | `is_editable_by` era `@property` con un parámetro `user` | Un `property` no acepta argumentos → `TypeError` en **toda** página de detalle, para todo actor | `IsEditableByRegressions` | 5 |
| 2 | `all_tags` consultaba `user.tasks.order_by("name")` | `user.tasks` es un queryset de `Task` y `Task` no tiene campo `name` → `FieldError` al renderizar el listado | `AllTagsContextRegressions` | 3 |
| 3 | Faltaba la ruta `register/` | `NoReverseMatch` → **500 en toda página anónima**, porque la navbar hace `{% url 'register' %}` siempre | `RegisterRouteRegressions` | 4 |
| 4 | `TaskUpdateView` sin `context_object_name` | El formulario de edición decía "Nueva tarea": el testador era la propia plantilla, no un test | `UpdateViewContextRegressions` | 4 |
| 5 | Widgets sin clases Bootstrap | Formularios sin estilo, inválidos según la hoja de estilos | `BootstrapWidgetRegressions` | 5 |
| 6 | Colisión de slug en `Tag` | `"Python 3"` y `"python-3"` slugifican igual → `IntegrityError` → **500** | `TagSlugCollisionRegressions` | 4 |
| 7 | `tasks.urls` montado en `""` y no en `"tasks/"` | Las rutas reales eran `/<pk>/` y no `/tasks/<pk>/`, en desacuerdo con la consigna | `UrlMountingRegressions` | 3 |
| | | | **Total** | **28** |

Los nombres de los tests son la especificación del defecto, y por eso son largos y
específicos. `test_is_editable_by_is_a_method_and_not_a_property` afirma exactamente la
causa, no un síntoma. `test_a_rejected_toggle_leaves_the_task_untouched` afirma el efecto
secundario, que es el que de verdad importa. `test_never_...` y
`test_every_task_route_sits_under_the_tasks_prefix` se escriben para fallar si alguien
"simplifica" el montaje de URLs.

Dos de los siete (1 y 2) eran errores propios de la implementación, no de la consigna, y
eran fatales para funcionalidades enteras. El valor de la suite de regresión no está en la
cobertura que agrega, sino en que documenta **qué se rompió y por qué no puede volver a
romperse**. Esa es también la información que un lector necesita para no reintroducirlos.

## 8. Convenciones de los tests

- **Nombres en inglés, descriptivos y con el sujeto primero**: `test_non_owner_gets_404_not_403_on_the_edit_page`. El nombre debe poder leerse como una frase que afirma un hecho.
- **Una aserción conceptual por test**, aunque use varios `assertStatus`. Un test que afirma
  tres cosas no dice cuál falló.
- **Sin `time.sleep`, sin mocks de red, sin fixtures en archivos externos.** Todo se
  construye en `setUp`.
- **`STRONG_PASSWORD = "Uni-Segura-2024!"`** en `tasks/tests/__init__.py` cumple los cuatro
  validadores configurados. Es una constante con un motivo explícito en el docstring: si
  estuviera débil, un test de registro fallaría por una razón que no tiene que ver con lo
  que prueba.
- **Los tests de regresión usan nombres que contienen el defecto**, no el síntoma, para que
  `grep is_editable_by tasks/tests/` encuentre directamente quién protege esa decisión.
