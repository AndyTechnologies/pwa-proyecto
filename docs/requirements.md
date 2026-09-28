# Requisitos — Task Manager

Gestor de tareas web en Django 6.1. Cada requisito funcional se identifica como
`RF-nn` y cada requisito no funcional como `RNF-nn`. Los identificadores son estables:
el código los referencia en docstrings (`tasks/views.py`, `tasks/forms.py`).

## 1. Requisitos funcionales

| ID | Requisito | Descripción | Implementación |
| --- | --- | --- | --- |
| RF-01 | Registro de usuario | Cualquier visitante crea su propia cuenta con `username` y confirmación de contraseña. No se inicia sesión automáticamente. | `RegisterView` (CBV `CreateView`) + `RegisterForm` en `tasks/forms.py`; ruta `register` en `config/urls.py` |
| RF-02 | Inicio y cierre de sesión | El usuario autenticado entra con credenciales y cierra sesión. El cierre es exclusivamente por `POST`. | `django.contrib.auth.views.LoginView` / `LogoutView` declaradas explícitamente en `config/urls.py`; `LOGOUT_REDIRECT_URL = 'login'` |
| RF-03 | Crear tarea | El usuario registrado crea una tarea con título, descripción, fecha de vencimiento, prioridad y etiquetas. El propietario se asigna desde la sesión, nunca desde el formulario. | `TaskCreateView` (`CreateView` + `LoginRequiredMixin`); `form.instance.owner = self.request.user` en `form_valid` |
| RF-04 | Editar tarea | El propietario modifica su tarea. Un usuario que no es propietario no alcanza el formulario. | `TaskUpdateView` (`UpdateView` + `LoginRequiredMixin`); `get_queryset()` devuelve `Task.objects.owned_by(self.request.user)` |
| RF-05 | Eliminar tarea | El propietario elimina su tarea, previa confirmación explícita en pantalla. | `TaskDeleteView` (`DeleteView` + `LoginRequiredMixin`); plantilla `tasks/task_confirm_delete.html` |
| RF-06 | Marcar como completada / pendiente | Acción de un clic que invierte el estado `completed`. `POST` exclusivamente. | `TaskCompleteToggleView` (`View` + `LoginRequiredMixin`); `http_method_names = ["post"]` |
| RF-07 | Listar mis tareas | El propietario ve exclusivamente sus propias tareas, ordenadas de forma determinista. | `TaskListView` (`ListView` + `LoginRequiredMixin`); `Task.Meta.ordering = ["due_date", "priority", "-pk"]` |
| RF-08 | Ordenar por fecha o por prioridad | El usuario elige el criterio de orden desde la interfaz; el valor viaja en `?sort=`. | `ALLOWED_SORTS = {"due_date": ["due_date"], "priority": ["priority"]}` más `SORT_TIE_BREAKER = ["-pk"]` en `tasks/views.py` |
| RF-09 | Filtrar por estado (todas / pendientes / completadas) | El usuario acota el listado por `completed`; el valor viaja en `?status=`. | `STATUS_FILTERS = {"all": None, "pending": False, "completed": True}` y `DEFAULT_STATUS = "all"` |
| RF-10 | Etiquetar tareas | El usuario asigna etiquetas separando nombres por comas. Las existentes se reutilizan sin distinguir mayúsculas y minúsculas; las nuevas se crean. | `TaskForm.tags_input` + `TaskForm.clean_tags_input` + `TaskForm._resolve_tags`; `Task.tags` (`ManyToManyField`) |
| RF-11 | Buscar por etiqueta | El listado se acota por etiqueta escribiendo un nombre o un slug; las etiquetas usadas por el usuario se ofrecen como accesos directos. | `?tag=` en `TaskListView.get_queryset()` vía `slugify`; `context["all_tags"]` alimenta la barra de filtros |
| RF-12 | Visibilidad por tarea | Cada tarea declara quién puede leerla: `private`, `authenticated` o `public`. La visibilidad nunca otorga escritura. | `Task.visibility` (`TextChoices`); `TaskQuerySet.visible_to(user)` |
| RF-13 | Acceso público a tareas públicas | Un visitante anónimo recorre `/tasks/public/` y abre el detalle de toda tarea `public`, en solo lectura. | `PublicTaskListView` (`ListView`, sin mixin de autenticación); rama anónima de `visible_to` |
| RF-14 | Acceso a tareas compartidas con el usuario | Un usuario registrado recorre `/tasks/shared/` y abre en solo lectura las tareas `authenticated` y `public` de otras personas. | `SharedTaskListView` (`ListView` + `LoginRequiredMixin`); `.exclude(owner=self.request.user)` sobre `visible_to` |

### Notas de alcance sobre los requisitos funcionales

- RF-01 y RF-02 no usan el panel de administración: el registro es autoservicio. El
  administrador solo se crea con `createsuperuser`.
- RF-06 no ofrece un endpoint para el estado "en progreso" ni un porcentaje de avance: el
  dominio solo distingue `completed` booleano.
- RF-11 busca por **una** etiqueta por petición. No hay búsqueda de texto libre sobre
  título o descripción.

## 2. Requisitos no funcionales

| ID | Requisito | Cómo se cumple en el código |
| --- | --- | --- |
| RNF-01 | Interfaz responsive | Bootstrap 5.3.8 vendored en `static/css/bootstrap.min.css` y `static/js/bootstrap.bundle.min.js`; navbar colapsable con `data-bs-toggle`; tabla en `md+` y tarjetas apiladas en móvil |
| RNF-02 | Usabilidad | Estados vacíos diferenciados (lista sin tareas vs. filtro sin resultados), mensajes de éxito con `django.contrib.messages`, confirmación previa al borrado, `help_text` en el campo de etiquetas |
| RNF-03 | Seguridad | `CsrfViewMiddleware` activo y `{% csrf_token %}` en todo formulario que muta estado; autorización resuelta en el queryset, nunca en la plantilla; escapado automático de plantillas |
| RNF-04 | Integridad de datos | `unique=True` en `Tag.name` y `Tag.slug`; `blank=True` en la M2M; validación de longitud de etiquetas contra `max_length` del campo; los parámetros de orden y filtro se validan contra whitelist |
| RNF-05 | Mantenibilidad | Layout MVT estricto (`config/` proyecto, `tasks/` app), dos rutas de instalación documentadas, sin dependencias fuera de Django en runtime |
| RNF-06 | Testabilidad | Suite de 249 pruebas con el runner nativo (`manage.py test tasks`); políticas de autorización aisladas en `TaskQuerySet` y verificables sin HTTP |
| RNF-07 | Consistencia visual | Un único `base.html` del que heredan las 9 plantillas; clases Bootstrap aplicadas desde `TaskForm.__init__` para que el formulario no dependa de una librería extra |
| RNF-08 | Accesibilidad | HTML semántico (`nav`, `main`, `table` con `th scope`), `label` asociado a cada input, errores con `invalid-feedback` y no solo color, `aria-label` en botones de cierre |
| RNF-09 | Seguridad de credenciales | Los 4 validadores de contraseña por defecto de Django activos en `AUTH_PASSWORD_VALIDATORS`; las contraseñas nunca se registran ni se exponen en plantillas |
| RNF-10 | Trazabilidad | Cada RF se referencia desde el docstring de la vista o del formulario que lo implementa |
| RNF-11 | Documentación | Documentación técnica en `docs/` y decisiones de arquitectura en `docs/adr/` con formato ADR |
| RNF-12 | Simplicidad | Cero vistas function-based y cero dependencias de test externas (ni `pytest` ni `factory_boy`); Bootstrap se aplica sin `django-widget-tweaks` |

## 3. Restricciones explícitas de la consigna

Estas restricciones provienen de la consigna académica y no son preferencias del equipo.

| Restricción | Cómo se verifica en el código |
| --- | --- |
| **Prohibido Django REST Framework** | DRF no figura en `pyproject.toml` ni en `requirements.txt`; no existe ninguna `APIView`, `ViewSet` ni `rest_framework` en el árbol |
| **Todas las vistas deben ser Class-Based Views** | Las 9 vistas de `tasks/views.py` heredan de `CreateView`, `ListView`, `DetailView`, `UpdateView`, `DeleteView` o `View`. Autenticación mediante `auth_views.LoginView` / `auth_views.LogoutView`, también CBVs |
| **Corte Semana 3: prototipo visual Bootstrap 5** | Capa de diseño y Bootstrap 5.3.8 vendored. Entregado junto con el corte de Semana 7; ver `docs/milestones/week-3.md` para la desviación declarada |
| **Corte Semana 5: modelos y Django Admin** | `Task` y `Tag` registrados en `tasks/admin.py` con `list_display`, `list_filter`, `search_fields` y `fieldsets` |
| **Corte Semana 7: enrutamiento, vistas y autenticación** | `config/urls.py` + `tasks/urls.py` con las 8 rutas del dominio y 9 CBVs |
| **Corte Semana 9: cierre** | Suite de 249 pruebas verdes y documentación técnica |

## 4. Fuera de alcance

Funciones consideradas pero deliberadamente **no** implementadas, con su motivo.

| No implementado | Motivo |
| --- | --- |
| **Paginación** | El volumen de tareas de un usuario académico no justifica el estado extra que `Paginator` introduce en la vista. Agregar `paginate_by` a `TaskListView` es un cambio de una línea, pero mientras no haya un caso de uso verificado se evita mantenerla |
| **API REST** | Prohibida por la consigna (ADR-003). Sin API, no hay versionado de contrato ni clientes móviles ni integraciones de terceros |
| **Recordatorios por correo** | Exige un backend de correo, un planificador (Celery, cron) y un modelo de tokens. `settings.py` define `MAILERS` con el backend de consola, que no envía nada, pero no se construyó ninguna funcionalidad de notificación |
| **Borrado lógico (soft delete)** | La consigna pide CRUD. Un campo `deleted_at` obligaría a filtrar en los dos querysets de política y a ocultar acciones en cuatro plantillas, a cambio de una funcionalidad que nadie pidió. El borrado es físico y en cascada lo resuelve la base |
| **Restricción de fecha de vencimiento en el pasado** | `TaskForm` acepta cualquier fecha. La plantilla sí marca "Vencida" una tarea pendiente con `due_date` anterior a hoy, que es información, no validación. Impedir la carga cargaría al usuario con una regla que el dominio no necesita |
| **Interruptor de modo oscuro** | `data-bs-theme` permite themeswap sin JavaScript adicional, pero no se agregó el control: el sitio usa la paleta clara por defecto de Bootstrap 5.3.8 y no se detectó un requisito de usabilidad que lo justificara |
| **Recuperación de contraseña por correo** | Requiere el mismo backend de correo que ya se descartó, más un modelo de tokens y una vista de reset |
| **Perfiles de usuario y carga de avatar** | La consigna no los pide. `owner` es la FK directa a `AUTH_USER_MODEL`, sin modelo `Profile` intermedio |
| **Internacionalización de la interfaz** | `LANGUAGE_CODE = 'es'` y los `choices` están en español, pero no hay `{% trans %}` ni archivos `.po`. La interfaz está escrita en español, no traducida |
