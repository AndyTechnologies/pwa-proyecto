# Seguridad — Task Manager

## 1. Modelo de amenazas

El activo principal es la **integridad y la confidencialidad de las tareas de cada
usuario**. Un usuario registrado no debe poder leer las tareas privadas de otro ni
modificar ninguna tarea que no sea suya. La superficie de ataque relevante es exactamente
la que expone una aplicación web clásica: peticiones HTTP manipulables, formularios con
estado, parámetros de consulta y plantillas que renderizan datos controlados por terceros.

| # | Actor | Capacidad | Objetivo plausible | Vector |
| --- | --- | --- | --- | --- |
| T1 | Visitante anónimo | Navegar `/login/`, `/register/`, `/tasks/public/`, `/tasks/<pk>/` | Ver tareas privadas o compartidas de otros | `GET /tasks/<pk>/` con `pk` adivinando el siguiente entero |
| T2 | Usuario registrado malicioso | Todo lo de T1, más crear tareas y ver las propias | Leer o escribir tareas ajenas | IDOR: editar, borrar o alternar el estado de la tarea de otro |
| T3 | Usuario registrado malicioso | Igual que T2 | Romper la consulta de listado | Inyección por `?sort=`, `?status=`, `?tag=` |
| T4 | Usuario registrado malicioso | Igual que T2 | Inyectar script en páginas de terceros | Título, descripción o etiqueta con `<script>` |
| T5 | Cualquiera con una sesión | Sesión propia | Escalar privilegios con `GET /logout/` o `GET /tasks/<pk>/toggle/` | Cambio de estado por método inseguro (CSRF) |
| T6 | Visitante anónimo | `/register/` | Crear cuentas en masa o con contraseña trivial | Sin límite de intentos ni verificación |
| T7 | Red intermediaria | Respuestas HTTP | Capturar credenciales o sesiones | Ausencia de HTTPS y de `SESSION_COOKIE_SECURE` |

Qué está fuera del modelo: el acceso al servidor, al sistema de archivos o a la consola de
SQLite se consideran comprometidos desde el inicio. La app no se despliega en producción
y no pretende serlo (ver sección 9).

## 2. CSRF

### Mecanismo

`django.middleware.csrf.CsrfViewMiddleware` está activo en `MIDDLEWARE`. Cada plantilla que
renderiza un formulario que muta estado incluye `{% csrf_token %}`:

| Formulario | Plantilla | Token |
| --- | --- | --- |
| Login | `templates/registration/login.html` | `AuthenticationForm` renderiza el token vía `LoginView` |
| Registro | `templates/tasks/register.html` | `{% csrf_token %}` |
| Crear / editar tarea | `templates/tasks/task_form.html` | `{% csrf_token %}` |
| Borrar tarea | `templates/tasks/task_confirm_delete.html` | `{% csrf_token %}` |
| Alternar completada | `templates/tasks/partials/task_card.html` y `templates/tasks/task_detail.html` | `{% csrf_token %}` |
| Cerrar sesión | `templates/base.html` (navbar) | `{% csrf_token %}` |

### Por qué cerrar sesión y alternar estado son `POST`

`LogoutView` es `POST`-only desde Django 5, y `TaskCompleteToggleView` declara
`http_method_names = ["post"]`. Un `GET` a cualquiera de las dos rutas responde **405**.

La razón no es estética: un `GET` no puede llevar un token CSRF, porque el token vive en el
cuerpo del formulario. Si un `<img src="/tasks/1/toggle/">` en una página de terceros
bastara para cambiar el estado, la protección CSRF sería inútil. Forzar `POST` significa que
cualquier cambio de estado pasa por un formulario con token, que es la única forma de
demostrar que la petición solo sale del propio sitio.

Costes asumidos: la acción de completar una tarea deja de ser un enlace, y la de cerrar
sesión exige un formulario en la navbar. Ambos están implementados y ambos tienen tests que
afirman el 405.

## 3. Autenticación

| Control | Implementación | Dónde |
| --- | --- | --- |
| Almacenamiento de contraseñas | `check_password()` con el hasher por defecto de Django (PBKDF2 con sal por usuario) | `AuthenticationForm` de Django |
| Longitud mínima | `MinimumLengthValidator` | `AUTH_PASSWORD_VALIDATORS` |
| Contraseñas comunes | `CommonPasswordValidator` contra una lista de contraseñas filtradas | Ídem |
| Solo numéricas | `NumericPasswordValidator` | Ídem |
| Similitud con el usuario | `UserAttributeSimilarityValidator` | Ídem |
| Confirmación | `password1` / `password2` en `UserCreationForm` | `RegisterForm` |
| Sesión | Creada por `login()` dentro de `auth_views.LoginView` | `SessionMiddleware` + cookie de sesión |

Los cuatro validadores son los que Django activa por defecto y están sin modificar. Se
aplican en el registro porque `RegisterForm` hereda de `UserCreationForm`, que encadena
`validate_password` automáticamente.

**Lo que no existe:** verificación de correo, segundo factor, límite de intentos de acceso,
expiración de sesión por inactividad y cierre de sesión remoto. Ver sección 9.

## 4. Autorización

### Dos políticas, dos métodos

La autorización vive en `TaskQuerySet`, no en las vistas ni en las plantillas:

| Método | Política | Regla | Quién lo usa |
| --- | --- | --- | --- |
| `TaskQuerySet.owned_by(user)` | **Escritura** | `filter(owner=user)`. Ignora la visibilidad por completo. | `TaskUpdateView`, `TaskDeleteView`, `TaskCompleteToggleView`, `TaskListView` |
| `TaskQuerySet.visible_to(user)` | **Lectura** | Anónimo → solo `PUBLIC`. Registrado no propietario → `AUTHENTICATED` + `PUBLIC`. Propietario → todas las propias. | `TaskDetailView`, `SharedTaskListView` |

Que estén en el queryset es la propiedad de seguridad que importa: una vista nueva no
puede "olvidarse" la regla porque no tiene dónde escribirla. O llama a `owned_by` o llama a
`visible_to`; no existe una tercera vía dentro de la app.

```mermaid
flowchart TD
    R[Petición] --> AUTH{¿Hay sesión?}
    AUTH -->|No| ANON{Ruta pública?}
    ANON -->|Sí: login, register,<br/>tasks/public, detalle de pública| V[visible_to(AnonymousUser)]
    ANON -->|No: lista, create, shared, edit,<br/>delete, toggle| RLOGIN[302 a LOGIN_URL]
    AUTH -->|Sí| MIX{¿LoginRequiredMixin?}
    MIX -->|Sí, y es escritura| OWN["owned_by(user)<br/>→ 404 si no es suya"]
    MIX -->|No, es lectura| VIS["visible_to(user)<br/>→ 404 si no es visible"]
    OWN --> ACC{[¿La fila existe<br/>en ese queryset?]}
    VIS --> ACC
    ACC -->|No| E404[404 Not Found]
    ACC -->|Sí| OK[Vista procesa la petición]
```

### Por qué 404 y no 403

Una tarea que existe pero no es visible responde **404**, igual que un `pk` inexistente.

Un 403 ("Forbidden") es una confirmación de existencia. Si `/tasks/42/` devolviera 403 para
un usuario que no es el dueño, y 404 para un `pk` que nadie creó, un atacante podría
recorrer `pk` consecutivos y **distinguir cuáles existen**. Eso es una fuga de
información sobre datos ajenos: no revela el contenido, pero revela la existencia y la
cantidad de tareas de otros usuarios, y en el caso de `PUBLIC` vs `PRIVATE` revela el
nivel de privacidad de cada tarea.

El 404 no cuesta nada funcional: la interfaz nunca necesita distinguir "no existe" de "no
puedo verlo", porque en ambos casos la respuesta correcta para el usuario es la misma —
no mostrar nada. `tasks/tests/test_permissions.py` afirma explícitamente el 404 en la clase
`NonOwnerWritePolicyTests`, con nombres de test que dicen `test_non_owner_gets_404_not_403_on_the_edit_page`
y sus equivalentes para delete y toggle.

### Por qué ocultar botones no es un control

En las plantillas, las acciones de escritura aparecen dentro de `{% if is_owner %}`.
`is_owner` viene de `Task.is_editable_by(user)`, que es un método que devuelve un booleano y
que el propio docstring declara como **"presentation hint only"**.

Eso es exactamente lo que es. Ocultar un botón no impide nada: el atacante no usa la
interfaz, usa la URL. Un `GET` directo a `/tasks/42/edit/` o un `POST` a
`/tasks/42/delete/` no pasa por ninguna plantilla.

Por eso el control real es que `TaskUpdateView.get_queryset()` devuelve
`Task.objects.owned_by(self.request.user)`: si la tarea no es del usuario, la fila nunca
llega a existir en el queryset, `get_object_or_404` no encuentra nada y la respuesta es
404 **antes** de que se llegue a construir un formulario. Lo mismo en `TaskDeleteView` y en
`TaskCompleteToggleView`.

Es decir: el `{% if is_owner %}` es UX, y la ausencia del recurso en el queryset es
seguridad. Si alguien borrara el `{% if is_owner %}` de `task_card.html`, el sistema
seguiría siendo seguro, solo menos usable.

## 5. Defensa contra IDOR

(IDOR — *Insecure Direct Object Reference* — es el nombre del ataque donde el atacante
cambia el identificador de un recurso en la URL para alcanzar uno ajeno.)

### El ataque

`alice` crea una tarea privada, que queda con `pk=1`. `bob` está registrado. Bob quiere
editarla. Su navegador ya conoce el patrón de URL —lo ve en sus propias tareas—, así que
simplemente navega:

```
GET /tasks/1/edit/     →  ?
POST /tasks/1/delete/  →  ?
POST /tasks/1/toggle/ →  ?
```

La URL es adivinable porque `Task.pk` es un entero autoincremental: los `pk` de las tareas
de Bob son 2, 3, 4... y el 1 existe. No hay nada secreto en el identificador, y aunque
lo hubiera, seguridad no depende de la secretosidad de un entero.

### La defensa

Tres capas, y la primera es la que importa:

1. **El queryset acotado por propietario.** `TaskUpdateView.get_queryset()` no devuelve
   `Task.objects.all()`, devuelve `Task.objects.owned_by(self.request.user)`. La consulta
   ejecutada es `SELECT ... WHERE id = 1 AND owner_id = 2`. Con `owner_id = bob` el
   registro de Alice no está en el conjunto de resultados. Django lanza `Http404` y la
   vista responde 404. **El dato ajeno nunca se lee de la base**, no se renderiza, no se
   toca.

2. **`LoginRequiredMixin` antes que el handler.** El mixin actúa en `dispatch()` antes de
   `get()`, así que un anónimo que intenta editar recibe un 302 al login, no un 404 — lo
   cual es correcto, porque primero hay que demostrar quién es.

3. **`TaskCompleteToggleView` también es `POST`-only y también usa `owned_by`.**
   `get_object_or_404(Task.objects.owned_by(request.user), pk=pk)` es la misma defensa en
   la única vista que no hereda de las genéricas.

### Verificación

`tasks/tests/test_permissions.py` cubre el ataque, no solo la función:

| Test | Qué afirma |
| --- | --- |
| `test_non_owner_gets_404_not_403_on_the_edit_page` | Un no propietario en `/tasks/<pk>/edit/` recibe 404 |
| `test_non_owner_gets_404_not_403_on_the_delete_page` | Ídem para la confirmación de borrado |
| `test_non_owner_gets_404_not_403_when_posting_the_delete_form` | Y también cuando el POST es real, no solo el GET |
| `test_non_owner_gets_404_not_403_when_posting_the_toggle` | Ídem para el toggle |
| `test_a_rejected_toggle_leaves_the_task_untouched` | El `POST` rechazado no modifica `completed` |
| `test_a_rejected_delete_leaves_the_task_untouched` | El borrado rechazado no borra la fila |
| `test_owned_by_ignores_visibility_and_only_honours_ownership` | `owned_by` no abre la puerta a una tarea pública ajena |

Las dos últimas son las importantes: prueban que el rechazo ocurre **antes** del efecto, no
que se rechace la respuesta.

### Lo que NO protege esta defensa

- **Enumeración de existencia vía el timing o el código de estado:** no aplica, porque el
  código de estado es 404 tanto si existe como si no. El tiempo de respuesta tampoco
  distingue, porque en ambos casos la consulta devuelve cero filas.
- **Un usuario que adivine el `username` de otro:** no hay endpoint que lo exponga. El
  campo `owner` solo es visible en el admin, que exige `is_staff`.
- **Fuga por el listado público:** `PublicTaskListView` filtra por
  `visibility=Visibility.PUBLIC` de forma explícita, no con `visible_to`, así que no
  depende de la lógica de actor y no puede arrastrar filas privadas.
- **Cambio de propietario:** `owner` no está en `TaskForm.Meta.fields`. Un POST con
  `owner=otro_id` no llega a setterse porque el `ModelForm` no tiene el campo.

## 6. Inyección por parámetros

`?sort=`, `?status=` y `?tag=` son controlados por el atacante.

La respuesta es la **whitelist**: el input del usuario es una *clave de diccionario*, nunca
un nombre de campo, una expresión o un valor que llegue al ORM.

```python
ALLOWED_SORTS = {"due_date": ["due_date"], "priority": ["priority"]}
SORT_TIE_BREAKER = ["-pk"]
STATUS_FILTERS = {"all": None, "pending": False, "completed": True}
DEFAULT_STATUS = "all"
```

Cómo se aplica:

| Parámetro | Validación | Si es inválido |
| --- | --- | --- |
| `?sort=` | `if self.sort not in ALLOWED_SORTS: self.sort = "due_date"` | Cae a `due_date` |
| `?status=` | `if self.status not in STATUS_FILTERS: self.status = DEFAULT_STATUS` | Cae a `all` |
| `?tag=` | Se pasa por `slugify()` y se filtra por `tags__slug` | Lista vacía, nunca error |

El detalle que importa: en `?status=` el valor inválido **no se pasa al ORM**. Se descarta
primero y se reemplaza por `"all"`, cuyo valor en el diccionario es `None`, y el código
hace `if completed is not None:` antes de filtrar. Es decir, un string arbitrario jamás
llega a ser el valor de una comparación en la base.

Lo que un `order_by` con input crudo habría permitido, y que aquí no ocurre:

| Entrada | Con whitelist (comportamiento real) |
| --- | --- |
| `?sort=owner; DROP TABLE tasks--` | No está en el diccionario → `due_date` |
| `?sort=' or 1=1--` | No está en el diccionario → `due_date` |
| `?sort=-created_at` | No está en el diccionario → `due_date` (no se permite invertir el orden) |
| `?status=INJECTED` | No está en el diccionario → `all` |
| `?tag=<script>alert(1)</script>` | Pasa por `slugify` → no coincide con ningún slug → lista vacía |

Hay que ser honesto sobre el alcance de esto: Django usa parámetros preparados en el ORM,
así que la inyección SQL tampoco era explotable aunque el valor llegara crudo. La whitelist
no es la primera línea contra SQL injection — lo es el ORM — sino que **cierra por diseño**
la superficie: el conjunto de campos por los que se puede ordenar es una constante escrita
en el código, y agregar uno es un cambio revisable, no un parámetro de URL.

`tasks/tests/test_filters.py` verifica el comportamiento: `test_an_injection_attempt_in_the_sort_parameter_does_not_drop_the_table`,
`test_an_unknown_sort_column_does_not_reach_the_orm` y `test_the_sort_filter_never_leaks_another_users_tasks`.

## 7. XSS y autoescapado

Las plantillas de Django autoescapan **por omisión**. Cualquier interpolación pasa por
`django.utils.html.escape`:

- `{{ task.title }}` → `<script>alert(1)</script>` se renderiza como texto visible.
- `{{ task.description }}` → igual.
- `{{ t.name }}` en `task_card.html` → igual, y el valor proviene de `tags_input`, que es
  100% del usuario.

La navegación construye URLs con `{% url %}`, nunca con concatenación de strings, así que
un `pk` o un nombre de ruta no puede inyectar atributos HTML.

**Superficie residual, y es real:** no se usa `|safe` en ninguna plantilla, pero tampoco se
usan `mark_safe`, `{% autoescape off %}` ni `format_html` con contenido de usuario. La lista
completa de lo que escapa Django está en el motor de plantillas; lo importante es que el
proyecto no abre excepciones. Una futura etiqueta renderizada con `|safe` (por ejemplo, un
`title` con acentos) reabriría el riesgo y debería pasar por `format_html` en su lugar.

## 8. Validación del lado del servidor

| Capa | Qué valida | Ejemplo |
| --- | --- | --- |
| Tipo del campo | Que no venga vacío y que sea convertible | `title` obligatorio, `due_date` parseable como fecha |
| `choices` | Que el valor esté en la enumeración | `priority=9` se rechaza; `visibility=hack` se rechaza |
| `max_length` | Longitud máxima | `title` de 500 caracteres se rechaza |
| `clean_tags_input` | Normalización y longitud por etiqueta | `" Django , django , DJANGO "` → `["django"]`; un nombre de 51 caracteres se rechaza con mensaje en español |
| `_resolve_tags` | Integridad de la unicidad | Reutiliza por `iexact` y, si no encuentra, por `slug` |
| Unicidad en la base | Última línea | `unique=True` en `Tag.name` y `Tag.slug` |

Nada de esto confía en el navegador. El `required` del HTML, el `type="date"` y el
`maxlength` son ayudas de UX: un `curl` con el campo vacío llega igual al formulario, y ahí
se rechaza.

La validación de contraseña se suma a todo lo anterior para el registro.

## 9. Manejo de secretos

`SECRET_KEY` está en `config/settings.py` con el valor de ejemplo que genera
`django-admin startproject`:

```python
SECRET_KEY = 'django-insecure-h91@ak2-+2!iomxys$uk6adqp(+pt^8bpyb9!5*56u3l)76w+l'
```

Es aceptable **porque la configuración de este proyecto es de desarrollo y no hay ningún
valor real detrás**: la base es un `db.sqlite3` descartable, no hay pasarela de pago, ni
API keys, ni credenciales de terceros, ni correo saliente. El nombre del proyecto lo dice:
`django-insecure-`.

Lo que habría que hacer antes de cualquier despliegue (y que el proyecto no hace):

1. Mover `SECRET_KEY` a una variable de entorno y fallar al arrancar si no está definida.
2. `DEBUG = False`, con `ALLOWED_HOSTS` explícito.
3. Rotar la clave: cualquier sesión firmada con la clave publicada está compromise, porque
   las cookies de sesión se firman con ella.
4. Generar el hash de las contraseñas con un hasher de menor costo solo en desarrollo; en
   producción, PBKDF2 con iteraciones altas.

`.gitignore` ya excluye `.env` y `.env.*`, así que la variable de entorno tiene un hogar
preparado cuando se use.

## 10. Limitaciones conocidas

Estas limitaciones son deliberadas para un proyecto académico y **deben** declararse como
tales. Ninguna está resuelta por el código actual.

| # | Limitación | Consecuencia | Cómo se resolvería |
| --- | --- | --- | --- |
| L1 | **`DEBUG = True`** | En producción, cualquier excepción muestra la página de traceback con rutas del servidor, consulta SQL y variables de contexto. Es una fuga de información directa. | `DEBUG = False` y `ALLOWED_HOSTS` con los dominios reales |
| L2 | **`ALLOWED_HOSTS = []`** | Con `DEBUG=True` Django acepta cualquier `Host`. Con `DEBUG=False` la aplicación no serviría ninguna petición. | Declarar los dominios |
| L3 | **`SECRET_KEY` en el código** | Cualquiera que lea el repositorio puede falsificar cookies de sesión y asumir la identidad de un usuario contra el mismo despliegue. | Variable de entorno + rotación |
| L4 | **Sin rate limiting en el login ni en el registro** | Fuerza bruta de credenciales y creación masiva de cuentas son viables a voluntad. | `django-axes`, un `LoginView` subclass con contador, o un proxy con limitación por IP |
| L5 | **Sin HTTPS configurado** | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` están en su valor por defecto (`False`). Credenciales y cookie de sesión viajan en claro. | Activar los tres indicadores en un entorno con TLS y terminar TLS en el proxy |
| L6 | **SQLite no es base de producción** | Escritura serializada: un único escritor a la vez. Con concurrencia real produce `database is locked`. No hay red, ni réplicas, ni backups automáticos. | PostgreSQL: cambiar `DATABASES['default']['ENGINE']`, que es la única línea que lo impide |
| L7 | **Sin endurecimiento de sesión** | `SESSION_COOKIE_AGE` por defecto (dos semanas), sin `SESSION_EXPIRE_AT_BROWSER_CLOSE`, sin invalidación al cambiar la contraseña, sin rotación de `session_key` en el login. | Ajustar `SESSION_*` y conectar `update_session_auth_hash` |
| L8 | **Sin CSP ni cabeceras endurecidas** | `XFrameOptionsMiddleware` cubre clickjacking, pero no hay `Content-Security-Policy`, `X-Content-Type-Options` ni `Referrer-Policy`. | Middleware propio o `django-csp` |
| L9 | **Sin verificación de correo ni recuperación de contraseña** | Cualquiera puede registrar la dirección de otra persona. No hay vía de recuperación. | Modelo de token, backend de correo y vistas de reset |
| L10 | **`MAILERS` no es una setting de Django** | El bloque `MAILERS` de `settings.py` no lo lee ningún componente: Django usa `EMAIL_BACKEND`. Es código muerto, no una configuración efectiva. | Borrarlo, o escribir `EMAIL_BACKEND` si alguna vez se usa el correo |
| L11 | **Sin dependencia de defensa en profundidad para el admin** | El admin exige `is_staff`, que es lo correcto, pero un superusuario tiene acceso total a las tareas de todos sin que la política `visible_to` aplique | Riesgo aceptado: el admin es una herramienta de administración, no de usuario final |
| L12 | **`TaskCompleteToggleView.get()` es código inalcanzable** | `http_method_names = ["post"]` hace que `View.dispatch()` rechace `GET` antes de resolver el método, así que el método `get()` que devuelve `HttpResponseNotAllowed` nunca se ejecuta. El 405 es correcto; ese `get()` es redundante. | Eliminar el método `get()` o el `http_method_names`, pero no ambos |
