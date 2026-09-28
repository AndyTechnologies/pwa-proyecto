# Matriz de trazabilidad

Cada requisito funcional de la consigna se enlaza con su implementación, el archivo
que la contiene, la prueba automatizada que la verifica y la documentación que la
explica. Ningún requisito queda sin implementar o sin probar.

Convención de nombres usada en la columna de tests:
`tasks/tests/<archivo>.py::<Clase>`

## Requisitos funcionales

| Requisito | Implementación | Archivo | Test | Documentación |
| --- | --- | --- | --- | --- |
| RF-01 Registro | `RegisterView(CreateView)` + `RegisterForm` | `tasks/views.py:42`<br>`tasks/forms.py:17` | `test_views::RegisterViewTests`<br>`test_forms::RegisterFormTests`<br>`test_regressions::RegisterRouteRegressions` | `docs/requirements.md`<br>`docs/adr/004` |
| RF-02 Login / Logout | `auth_views.LoginView`, `auth_views.LogoutView` (POST-only) | `config/urls.py:15-16` | `test_views::LoginViewTests`<br>`test_permissions::LogoutMethodPolicyTests` | `docs/adr/004`<br>`docs/security.md` |
| RF-03 Crear tarea | `TaskCreateView(CreateView+LoginRequiredMixin)` + `TaskForm` | `tasks/views.py:161`<br>`tasks/forms.py:28` | `test_views::TaskCreateViewTests`<br>`test_forms::TaskFormValidDataTests` | `docs/requirements.md` |
| RF-04 Editar tarea | `TaskUpdateView(UpdateView+LoginRequiredMixin)`, `get_queryset()` → `owned_by()` | `tasks/views.py:178` | `test_views::TaskUpdateViewTests`<br>`test_permissions::NonOwnerWritePolicyTests` | `docs/adr/008`<br>`docs/security.md` |
| RF-05 Eliminar tarea | `TaskDeleteView(DeleteView+LoginRequiredMixin)`, `get_queryset()` → `owned_by()` | `tasks/views.py:197` | `test_views::TaskDeleteViewTests`<br>`test_permissions::NonOwnerWritePolicyTests` | `docs/adr/008` |
| RF-06 Completar tarea | `TaskCompleteToggleView(View+LoginRequiredMixin)`, POST-only | `tasks/views.py:214` | `test_views::TaskCompleteToggleViewTests`<br>`test_permissions::ToggleMethodPolicyTests` | `docs/requirements.md` |
| RF-07 Listado | `TaskListView(ListView+LoginRequiredMixin)` | `tasks/views.py:65` | `test_views::TaskListViewTests`<br>`test_permissions::ListScopingTests` | `docs/architecture.md` |
| RF-08 Ordenación | `ALLOWED_SORTS` + desempate `-pk` | `tasks/views.py:23` | `test_filters::SortFilterTests`<br>`test_filters::SortTieBreakerTests` | `docs/adr/008` |
| RF-09 Filtrar por estado | `STATUS_FILTERS` | `tasks/views.py:34` | `test_filters::StatusFilterTests` | `docs/requirements.md` |
| RF-10 Etiquetas | `Tag` + `Task.tags` (M2M) + `TaskForm.tags_input` | `tasks/models.py:49`<br>`tasks/forms.py:38` | `test_models::TaskTagRelationTests`<br>`test_forms::TaskFormTagsInputCleaningTests` | `docs/adr/006`<br>`docs/data-model.md` |
| RF-11 Buscar por etiqueta | `TaskListView.get_queryset()` → `filter(tags__slug=...)` | `tasks/views.py:88` | `test_filters::TagFilterTests` | `docs/data-model.md` |
| RF-12 Privacidad | `Visibility` enum + `TaskQuerySet.visible_to()` / `owned_by()` | `tasks/models.py:27`<br>`tasks/models.py:73` | `test_permissions::*` (11 clases) | `docs/adr/005`<br>`docs/security.md` |
| RF-13 Vista pública | `PublicTaskListView` + `visible_to()` para anónimos | `tasks/views.py:146` | `test_views::PublicTaskListViewTests`<br>`test_permissions::AnonymousReadPolicyTests` | `docs/adr/005` |
| RF-14 Compartido con registrados | `SharedTaskListView` + `visible_to()` | `tasks/views.py:130` | `test_views::SharedTaskListViewTests`<br>`test_permissions::NonOwnerReadPolicyTests` | `docs/adr/005` |

## Requisitos no funcionales

| Requisito | Implementación | Test | Documentación |
| --- | --- | --- | --- |
| RNF-01 Responsive | Tabla `d-none d-md-block` + tarjetas `d-md-none`; navbar colapsable | Inspección a 360/768/1440 px | `docs/milestones/week-3.md` |
| RNF-02 Usabilidad | Filtros en un único formulario GET; mensajes Django | `test_views::*` (mensajes) | `docs/requirements.md` |
| RNF-03 Seguridad | `owned_by()` / `visible_to()` en cada vista mutable | `test_permissions::*` (45) | `docs/security.md` |
| RNF-04 Integridad | `TaskForm` + `clean_tags_input()` + validación de enum | `test_forms::*` (56) | `docs/requirements.md` |
| RNF-05 Mantenibilidad | `models` / `views` / `forms` / `templates` / `static` / `tests` separados | Verificable por estructura | `docs/architecture.md` |
| RNF-06 Testabilidad | 249 pruebas con el runner nativo | Las 249 | `docs/testing.md` |
| RNF-07 Consistencia visual | Bootstrap 5.3.8 vendorizado | Inspección visual | `docs/adr/007` |
| RNF-08 Accesibilidad | HTML semántico, `<label>` asociados, `invalid-feedback` | `test_regressions::BootstrapWidgetRegressions` | `docs/milestones/week-3.md` |
| RNF-09 Credenciales | `AUTH_PASSWORD_VALIDATORS` (4) + `UserCreationForm` | `test_forms::RegisterFormTests` | `docs/security.md` |
| RNF-10 Trazabilidad | Este documento | — | — |
| RNF-11 Documentación | 6 documentos técnicos + 8 ADRs + 4 milestones | — | `docs/` |
| RNF-12 Simplicidad | Sin DRF, sin pytest, sin widget-tweaks, sin `completed_at` | `test_regressions::BootstrapWidgetRegressions` verifica que `widget_tweaks` no está instalado | `docs/adr/003` |

## Restricciones duras de la consigna

| Restricción | Verificación | Resultado |
| --- | --- | --- |
| No usar Django REST Framework | `grep -rniE "rest_framework\|serializers" --include="*.py"` sobre el repositorio | **0 coincidencias** |
| Todas las vistas son CBV | `grep -rnE "^def \w+\(request" tasks/ config/` excluyendo tests | **0 coincidencias**; 9 CBVs en `tasks/views.py` |

## Matriz de autorización cubierta por pruebas

Cada celda de la matriz de la consigna tiene al menos un test que la ejercita.

| Actor | Tarea privada | Tarea compartida | Tarea pública |
| --- | --- | --- | --- |
| Anónimo | 404 — `AnonymousReadPolicyTests` | 404 — `AnonymousReadPolicyTests` | 200 solo lectura — `AnonymousReadPolicyTests` |
| Registrado no propietario | 404 — `NonOwnerReadPolicyTests` | 200 solo lectura — `NonOwnerReadPolicyTests` | 200 solo lectura — `NonOwnerReadPolicyTests` |
| Propietario | CRUD — `OwnerReadPolicyTests`, `NonOwnerWritePolicyTests` | CRUD — `OwnerReadPolicyTests` | CRUD — `OwnerReadPolicyTests` |

Escritura denegada al no propietario, afirmada explícitamente como **404 y no 403**:
`test_permissions::NonOwnerWritePolicyTests`.

## Defectos convertidos en regresión

Cada defecto encontrado durante el desarrollo tiene su archivo de test y su clase.

| # | Defecto | Regresión |
| --- | --- | --- |
| 1 | `is_editable_by` como `@property` con parámetro → `TypeError` | `test_regressions::IsEditableByRegressions` |
| 2 | `all_tags` consultando `user.tasks` por campo inexistente → `FieldError` | `test_regressions::AllTagsContextRegressions` |
| 3 | Ruta `register` ausente → `NoReverseMatch` 500 en páginas anónimas | `test_regressions::RegisterRouteRegressions` |
| 4 | `TaskUpdateView` sin `context_object_name` | `test_regressions::UpdateViewContextRegressions` |
| 5 | Widgets sin clases Bootstrap | `test_regressions::BootstrapWidgetRegressions` |
| 6 | Colisión de slug en `Tag` → `IntegrityError` 500 | `test_regressions::TagSlugCollisionRegressions` |
| 7 | `tasks.urls` montado en `""` y no en `"tasks/"` | `test_regressions::UrlMountingRegressions` |

## Cobertura de la suite

| Archivo | Tests | Responsabilidad |
| --- | --- | --- |
| `test_models.py` | 33 | Defaults, `Meta.ordering`, slug de `Tag`, M2M, cascada |
| `test_forms.py` | 56 | Campos obligatorios, enums, parseo y resolución de etiquetas |
| `test_views.py` | 53 | CRUD completo, auth, mensajes, ausencia de controles de escritura |
| `test_permissions.py` | 45 | Matriz de autorización, IDOR, políticas de queryset |
| `test_filters.py` | 34 | Whitelists, orden determinista, intentos de inyección |
| `test_regressions.py` | 28 | Un archivo por defecto corregido |
| **Total** | **249** | Todas verdes |
