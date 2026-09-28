# ADR-004 — Autenticación con `django.contrib.auth`

Estado: aceptada.

## Contexto

El proyecto necesita registro de usuarios, inicio de sesión, cierre de sesión y
protección de rutas. La consigna no impone un mecanismo de autenticación concreto,
pero sí exige que las vistas sean CBVs y que exista una experiencia de
autenticación completa.

El proyecto ya incluye `django.contrib.auth` en `INSTALLED_APPS`, con
`AuthenticationMiddleware` y `CsrfViewMiddleware` activos en `MIDDLEWARE`, y
cuatro validadores de contraseña configurados en `AUTH_PASSWORD_VALIDATORS`
(`UserAttributeSimilarityValidator`, `MinimumLengthValidator`,
`CommonPasswordValidator`, `NumericPasswordValidator`).

El registro se implementa con `RegisterView` (`CreateView`) sobre
`RegisterForm`, que hereda de `django.contrib.auth.forms.UserCreationForm`. El
login y el logout usan `django.contrib.auth.views.LoginView` y `LogoutView`
declarados en `config/urls.py`. `LoginView` usa el `AuthenticationForm` del propio
Django, sin reimplementar.

## Problema

Hay tres caminos para resolver la autenticación: construirla desde cero, añadir
un paquete de terceros, o usar el sistema integrado de Django. La decisión tiene
consecuencias directas sobre el modelo de datos, sobre la confianza en la
seguridad y sobre el comportamiento observable del registro y del logout.

Hay además un punto de comportamiento que la consigna deja abierto y que debe
quedar decidido y documentado: **qué ocurre inmediatamente después de que un
usuario se registra**.

## Opciones consideradas

1. **`django.contrib.auth` de Django** (modelo `User`, `AuthenticationForm`,
   `LoginView`, `LogoutView`, validadores de contraseña, sesiones y cookies).
2. **Autenticación construida desde cero**: modelo `Account` propio, hash de
   contraseña implementado a mano, gestión propia de sesiones y cookies.
3. **Paquete de terceros** (`allauth`, `dj-rest-auth`, `django-simple-login` u
   otros equivalentes) para el flujo de registro y login.

## Decisión

Se adopta la **opción 1: `django.contrib.auth`**, sin reimplementar ninguna de
sus piezas.

La razón de fondo es que la autenticación es un problema resuelto y auditado, no
un problema del dominio. Todo lo que este proyecto necesita ya está en Django:
validación de credenciales, hash de contraseñas, sesiones, rotación de
identificadores de sesión, protección CSRF, validadores de contraseña y mensajes
de error en el idioma configurado (`LANGUAGE_CODE = 'es'`). Escribir
cualquiera de esas piezas de nuevo sería asumir la responsabilidad de auditar
seguridad crítica sin ningún beneficio funcional.

**No se reimplementa el formulario de login.** `LoginView` consume el
`AuthenticationForm` de Django. Reescribirlo sería abstraer el framework por
apariencia, sin ganar nada: la validación de credenciales ya es correcta y el
formulario de Django ya genera los mensajes de error en el idioma configurado. La
única personalización que hace el proyecto es indicar la plantilla
(`template_name="registration/login.html"`).

### Comportamiento posterior al registro

`RegisterView` **no inicia sesión automáticamente**. Tras un registro exitoso
redirige a la página de login (`get_success_url` devuelve `reverse("login")`) y
muestra un mensaje de éxito que indica que ya se puede iniciar sesión.

Justificación:

- **Estado de sesión predecible.** El usuario sabe exactamente en qué estado está
  después de registrarse: tiene cuenta, no tiene sesión. Con auto-login, la
  diferencia entre "recién creado" y "ya autenticado" se vuelve implícita.
- **No sorprende al usuario.** El flujo pide credenciales en un paso explícito y
  comprueba la contraseña que acaba de elegir. El propio formulario de
  `UserCreationForm` muestra la contraseña en texto plano, así que el paso
  adicional no aporta fricción real.
- **La pantalla de login confirma que la cuenta existe.** Es el punto donde la
  cuenta se demuestra válida antes de entrar, y evita el patrón en el que un
  registro aparentemente exitoso deja al usuario sin sesión y sin explicación de
  por qué.
- **Es una decisión reversible y barata.** Añadir auto-login más adelante es
  cambiar `get_success_url` y llamar a `login()`; no hay migración ni cambio de
  modelo. Este argumento solo sería válido si el camino de vuelta fuera costoso, y
  no lo es.

### Cierre de sesión

`LogoutView` de Django se usa directamente. Desde Django 5 el cierre de sesión
por GET está eliminado por seguridad (un GET puede dispararse desde cualquier
sitio enlazado, un formulario embebido o una precarga de URL), por lo que el
proyecto define `LOGOUT_REDIRECT_URL = 'login'` y renderiza el cierre de sesión
como un formulario con POST en la navegación. `TaskCompleteToggleView` aplica el
mismo criterio y restringe `http_method_names` a `["post"]`.

## Consecuencias

**Beneficios**

- No hay código de autenticación propio que auditar: hash de contraseñas,
  sesiones, CSRF y validación de credenciales provienen del framework.
- `RegisterForm` hereda de `UserCreationForm` y con ello hereda automáticamente
  los cuatro validadores de contraseña configurados, sin reimplementar reglas de
  fortaleza.
- El login y el logout son CBVs de Django, coherentes con el resto de la capa de
  presentación (ADR-002).
- Los mensajes de error y de éxito se muestran en español por la configuración
  global del proyecto, sin cadenas duplicadas.
- El modelo de usuario es el `User` estándar, con `related_name="tasks"` en el
  `ForeignKey` de `Task.owner`; cambiar de modelo de usuario más adelante
  requeriría una migración, pero sería una decisión localizada.
- El estado tras el registro es explícito y verificable por tests.

**Costos**

- **El modelo `User` de Django tiene más campos de los estrictamente
  necesarios** (username, first name, last name, email, staff, active, date
  joined). Se usan el subconjunto que hace falta y se ignoran los demás; es
  espacio y ruido visual en el formulario y en el admin.
- **La dependencia del `User` estándar es rígida.** Un proyecto real con datos de
  perfil usaría un modelo de usuario propio (`AUTH_USER_MODEL`), lo que exige
  planearlo antes de la primera migración. Aquí no se necesita, pero es un punto
  en el que el diseño quedó fijado por comodidad del proyecto.
- **Sin auto-login tras el registro** hay un paso extra para el usuario. Es una
  decisión deliberada, pero es un coste real de fricción.
- **El cierre de sesión como POST obliga a la interfaz a ser un formulario y no
  un enlace.** Un `<a href="/logout/">` corriente ya no funciona, y cualquier
  plantilla nueva debe recordarlo.
- `django.contrib.auth` arrastra `django.contrib.contenttypes` y
  `django.contrib.sessions`; son dependencias que este proyecto no usa
  directamente pero que no puede excluir sin romper permisos y sesión.

## Alternativas descartadas

**Autenticación desde cero (opción 2).** Se descarta porque obligaría a
implementar y auditar el hash de contraseñas, la gestión de sesiones y cookies,
la protección CSRF y la comparación en tiempo constante. El resultado sería peor en
todos los criterios que importan y solo se diferenciaría en lo accesorio. Además
introduciría un modelo `Account` que no se integraría con `django.contrib.admin`
sin trabajo adicional, y violaría la expectativa del proyecto de que la
seguridad se resuelve con mecanismos estándar y auditables.

**Paquete de terceros (opción 3).** Se descarta por dos razones concretas. La
primera es de alcance: un paquete como `allauth` resuelve verificación por correo,
redes sociales, recuperación de contraseña y confirmación de cuenta, ninguna de
cuales está en el alcance de este proyecto. La segunda es de coste: añadiría
dependencias, modelos propios (tablas de confirmada, tokens, conexiones sociales),
plantillas que habría que sobreescribir y una capa de comportamiento difícil de
explicar en una defensa. Para el registro que necesita el proyecto, un
`UserCreationForm` y un `AuthenticationForm` son suficientes y son los que usa.
