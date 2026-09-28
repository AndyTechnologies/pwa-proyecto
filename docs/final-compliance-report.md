# Reporte final de cumplimiento contra la consigna

**Proyecto:** Task Manager — Programación Web Avanzada
**Fuente normativa:** `ProyectoFinalPWAvanzadav4.pdf` (8 requisitos funcionales, 4 cortes, dos restricciones duras)
**Fecha de auditoría:** cierre del corte Semana 9
**Método:** inspección del código, ejecución de la suite completa y verificación de las restricciones por búsqueda de texto sobre el repositorio.

## Resumen

| Métrica | Valor |
| --- | --- |
| Requisitos funcionales | 14 / 14 implementados y probados |
| Requisitos no funcionales | 12 / 12 cubiertos |
| Restricciones duras | 2 / 2 cumplidas |
| Pruebas automatizadas | 249, todas verdes |
| Vistas function-based | 0 |
| Referencias a DRF | 0 |
| Defectos encontrados | 7, los 7 con test de regresión |
| Requisitos en estado PARTIAL | 0 |
| Requisitos en estado FAIL | 0 |

## Los 8 requisitos de la consigna

### Requisito 1 — Diseño responsive basado en Bootstrap 5

**Estado: PASS**

Bootstrap 5.3.8 vendorizado en `static/css/` y `static/js/`, referenciado con
`{% static %}` y sin CDN. Navbar colapsable, listado con tabla en md+ y tarjetas
apiladas en móvil, grilla responsive en los listados públicos y compartidos.

Evidencia: `templates/base.html`, `templates/tasks/task_list.html`,
`templates/tasks/partials/task_card.html`, `docs/milestones/week-3.md`,
`docs/adr/007`. Verificado a 360 px, 768 px y 1440 px.

### Requisito 2 — CRUD con título, descripción, fecha de vencimiento y prioridad

**Estado: PASS**

Los cuatro campos exigidos existen con validación server-side. El borrado pide
confirmación. La eliminación es física (decisión documentada, no impuesta por la
consigna).

Evidencia: `tasks/models.py:105` (`Task`), `tasks/forms.py:28` (`TaskForm`),
`tasks/views.py:161` (`TaskCreateView`), `:178` (`TaskUpdateView`), `:197`
(`TaskDeleteView`). Tests: `test_forms::TaskFormRequiredFieldTests`,
`test_views::TaskCreateViewTests`, `test_views::TaskDeleteViewTests`.

### Requisito 3 — Lista ordenada por fecha o prioridad, filtrable por estado

**Estado: PASS**

Ordenación por `due_date` y `priority` mediante whitelist `ALLOWED_SORTS` con
desempate determinista `-pk`. Filtrado por `all` / `pending` / `completed` mediante
`STATUS_FILTERS`.

Evidencia: `tasks/views.py:23`, `:34`, `:65`. Tests: `test_filters::SortFilterTests`,
`test_filters::SortTieBreakerTests`, `test_filters::StatusFilterTests`.

### Requisito 4 — Etiquetas y búsqueda por etiqueta

**Estado: PASS**

Modelo `Tag` con relación M2M, reutilización insensible a mayúsculas y filtro por slug.

Evidencia: `tasks/models.py:49` (`Tag`), `:105` (`Task.tags`), `tasks/forms.py:38`
(`tags_input`), `tasks/views.py:88` (filtro). Tests: `test_models::TaskTagRelationTests`,
`test_forms::TaskFormTagsInputCleaningTests`, `test_filters::TagFilterTests`,
`docs/adr/006`.

### Requisito 5 — Registro, inicio de sesión y cierre de sesión

**Estado: PASS**

`RegisterView`, `LoginView` y `LogoutView`. El registro redirige al login sin abrir
sesión. El logout es POST-only, como exige Django 5+.

Evidencia: `config/urls.py:15-17`, `tasks/views.py:42`, `tasks/forms.py:17`.
Tests: `test_views::RegisterViewTests`, `test_views::LoginViewTests`,
`test_permissions::LogoutMethodPolicyTests`, `docs/adr/004`.

### Requisito 6 — CRUD solo por usuarios registrados y solo sobre tareas propias

**Estado: PASS — requisito de mayor riesgo, verificado con peticiones reales**

`LoginRequiredMixin` en las 6 vistas mutables, y resolución de objetos por
`Task.objects.owned_by(user)`. Un usuario que manipula el ID en la URL recibe 404, y
no 403, para no confirmar la existencia de tareas ajenas.

Evidencia: `tasks/models.py:80` (`owned_by`), `tasks/views.py:178`, `:197`, `:214`.
Tests: `test_permissions::NonOwnerWritePolicyTests`,
`test_permissions::AnonymousWritePolicyTests`, `test_permissions::ListScopingTests`,
`docs/adr/008`, `docs/security.md`.

### Requisito 7 — Visibilidad en solo lectura y pública

**Estado: PASS**

Enum `Visibility` con `PRIVATE`, `AUTHENTICATED` y `PUBLIC`. La política de lectura
`visible_to()` no otorga nunca escritura. `PublicTaskListView` accesible sin
autenticación; `SharedTaskListView` para tareas ajenas compartidas.

Evidencia: `tasks/models.py:27`, `:89` (`visible_to`), `tasks/views.py:109`, `:130`,
`:146`. Tests: 11 clases en `test_permissions.py` cubriendo la matriz completa,
`docs/adr/005`.

### Requisito 8 — Buenas prácticas: modelos, vistas, plantillas, formularios, validación y seguridad

**Estado: PASS**

Separación en capas, 249 pruebas, validación server-side sin depender de HTML5,
CSRF en toda mutación, escape automático de plantillas, control de acceso en tres
niveles (queryset, vista, acción) y nunca solo en la plantilla.

Evidencia: `docs/architecture.md`, `docs/testing.md`, `docs/security.md`,
`docs/data-model.md`, `docs/development.md`.

## Las 2 restricciones duras

### Restricción 9 — No se permite Django REST Framework

**Estado: PASS**

```
$ grep -rniE "rest_framework|serializers" --include="*.py" --include="*.txt" --include="*.toml" .
0 coincidencias
```

DRF no está en `pyproject.toml` ni en `requirements.txt`. No hay capa de API, lo que
implica que no hay clientes móviles ni integraciones de terceros: es una consecuencia
aceptada y documentada en `docs/adr/003`.

### Restricción 10 — Todas las vistas deben ser Class-Based Views

**Estado: PASS**

```
$ grep -rnE "^def [a-z_]+\(request" tasks/ config/ --include="*.py" | grep -v tests
0 coincidencias
```

9 CBVs en `tasks/views.py` más `LoginView` y `LogoutView` de `django.contrib.auth`, que
también son CBVs. `docs/adr/002` documenta la decisión y sus costos.

## Defectos encontrados durante el desarrollo

Siete. Todos corregidos y todos con test de regresión. La consigna (§38) exige que
cada vulnerabilidad descubierta se convierta en regresión.

| # | Defecto | Impacto | Regresión |
| --- | --- | --- | --- |
| 1 | `is_editable_by` como `@property` recibiendo un parámetro | `TypeError` en toda página de detalle | `test_regressions::IsEditableByRegressions` |
| 2 | `all_tags` consultaba `user.tasks` por un campo `name` inexistente | `FieldError` en el listado principal | `test_regressions::AllTagsContextRegressions` |
| 3 | Ruta `register` ausente | 500 en toda página anónima | `test_regressions::RegisterRouteRegressions` |
| 4 | `TaskUpdateView` sin `context_object_name` | El formulario de edición decía "Nueva tarea" | `test_regressions::UpdateViewContextRegressions` |
| 5 | Widgets sin clases Bootstrap | Formularios sin estilo | `test_regressions::BootstrapWidgetRegressions` |
| 6 | Colisión de slug en `Tag` (`Python 3` vs `python-3`) | `IntegrityError` → 500 | `test_regressions::TagSlugCollisionRegressions` |
| 7 | `tasks.urls` montado en `""` y no en `"tasks/"` | URLs de la consigna inexistentes | `test_regressions::UrlMountingRegressions` |

## Desviación declarada respecto de la consigna

**Corte Semana 3 entregado junto con el de Semana 7.** La consigna pide un prototipo
estático con datos mock en la semana 3. La capa de diseño Bootstrap se resolvió
directamente contra el modelo definitivo, en la misma entrega que el routing y las
vistas.

Razón: una maqueta estática con datos ficticios habría sido código desechable, y
mantener dos versiones del mismo HTML introduce una divergencia que nadie mantiene.
La capa de diseño entregada cumple el objetivo del corte — layout, jerarquía visual,
estados y responsive — y la desviación queda registrada en
`docs/milestones/week-3.md`.

Consecuencia para la evaluación: el commit del corte Semana 3 no existe como entrega
separada. El contenido del corte sí está documentado.

## Verificación de la suite

```
$ uv run python manage.py test tasks
Ran 249 tests
OK
```

Desglose: `test_models` 33, `test_forms` 56, `test_views` 53, `test_permissions` 45,
`test_filters` 34, `test_regressions` 28.

## Limitaciones honestas

Ninguna es un incumplimiento de la consigna; se declaran para no sobrevender el
alcance.

1. **No endurecido para producción.** `DEBUG=True` y `ALLOWED_HOSTS` vacío. SQLite no
   es un motor de producción. `docs/security.md` lo documenta.
2. **Sin rate limiting en el login.** Django no lo incluye y no se añadió porque la
   consigna no lo exige.
3. **Sin pruebas de carga ni E2E en navegador.** La suite es de integración sobre el
   test client de Django. La razón: agregar un navegador a la suite y las dependencias que arrastra no se justifican en el alcance (RNF-12).
4. **Responsive verificado por inspección, no por test automatizado.** Bootstrap
   garantiza el comportamiento; automatizarlo exigiría un navegador en la suite.
5. **La visibilidad no modela permisos por usuario.** Un campo enum no puede expresar
   concessiones individuales como sí haría una tabla ACL. Costo documentado en
   `docs/adr/005`.
6. **Sin paginación.** Decisión de simplicidad, registrada como no-objetivo en
   `docs/requirements.md`.
