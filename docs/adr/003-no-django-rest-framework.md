# ADR-003 — No usar Django REST Framework

Estado: aceptada.

## Contexto

La consigna del trabajo final **prohíbe explícitamente Django REST Framework
(DRF)**. No es una omisión ni una preferencia por simplicidad: es una
restricción del enunciado, de la misma categoría que la obligación de usar CBVs.

La aplicación es un sitio web con plantillas: un usuario se registra, inicia
sesión, crea tareas, las etiqueta, las ordena y las filtra, y consulta las tareas
que otros usuarios comparten. La capa de presentación son plantillas Django en
`templates/`, renderizadas por CBVs, y la validación de entrada la hace un
`ModelForm` (`TaskForm`) y un `UserCreationForm` (`RegisterForm`).

No existe ningún endpoint JSON, ningún cliente móvil y ningún consumidor
programático en el alcance del proyecto.

## Problema

La decisión a documentar es por qué el proyecto no expone una API y qué se pierde
por eso. El riesgo de argumentarla sin honestidad es doble: por un lado,
presentar la ausencia de API como una virtud sin explicar su coste real deja el
proyecto incompleto; por otro, añadir DRF "porque es lo habitual" incumpliría la
consigna.

La comparación relevante es entre dos capas de validación que resuelven el mismo
problema con modelos distintos: los *serializers* de DRF y los formularios de
Django.

## Opciones consideradas

1. **Sin API**: formularios de Django (`forms.ModelForm`, `forms.Form`) y CBVs que
   renderizan plantillas. Es lo que se adopta.
2. **DRF completo**: `ModelSerializer` para el modelo, `ViewSet` y `Router` para
   los endpoints, y formularios de Django solo para el login.
3. **DRF parcial**: usar DRF únicamente para exponer lectura (por ejemplo, un
   listado público en JSON) manteniendo la UI HTML con formularios.
4. **API mínima a mano**: vistas CBVs que devuelven `JsonResponse` sin DRF ni
   framework de serialización.

## Decisión

Se adopta la **opción 1: no hay API**.

**Motivo normativo.** La consigna prohíbe DRF. La decisión está cerrada por
encima de toda valoración técnica, y las opciones 2, 3 y 4 quedan fuera por esa razón
antes de evaluarse por sus méritos.

**Motivo técnico, para el registro.** Los *serializers* de DRF y los formularios
de Django resuelven el mismo problema —validar y convertir datos entre el mundo
externo y el modelo— con dos capas distintas. Un `ModelSerializer` de DRF
reimplementa, campo por campo, gran parte de lo que `ModelForm` ya hace: tipos,
`required`, `max_length`, `choices`, valores por defecto, validación a nivel de
campo y mensajes de error. En este proyecto eso sería duplicación real, porque
`TaskForm` ya declara `title`, `description`, `due_date`, `priority`, `visibility`
y `completed` contra `Task`, y `RegisterForm` ya hereda de `UserCreationForm` con
los validadores de contraseña de Django. Introducir serializers obligaría a
mantener dos declaraciones del mismo contrato y a resolver de forma permanente la
pregunta de cuál manda, sin ganar funcionalidad que la UI necesite.

La validación específica que sí es propia del dominio —el campo `tags_input` de
texto libre separado por comas, su limpieza y la resolución a instancias de `Tag`—
vive en el `ModelForm` porque depende de `Tag` y de la lógica de reutilización
(ADR-006). No es validación genérica de un campo del modelo: es lógica de negocio,
y el `ModelForm` es el lugar correcto para ella.

## Consecuencias

**Beneficios**

- Requisito de la consigna cumplido: DRF no está en `requirements.txt` ni en
  `pyproject.toml`, y no hay ninguna dependencia transitiva de DRF instalada.
- Una sola capa de validación y una sola declaración del contrato de cada
  entidad. No hay dos verdades que sincronizar.
- Superficie de ataque reducida: no hay endpoints públicos que auditar, no hay
  throttling que configurar, no hay permisos por token que rotar.
- El flujo de datos es fácil de explicar y de probar de punta a punta: petición
  → CBV → `ModelForm` → ORM → plantilla.
- Menos dependencias y menos versiones que sostener en un proyecto evaluado.

**Costos**

- **No hay API.** En consecuencia quedan fuera de alcance los clientes móviles,
  las integraciones con servicios de terceros, el acceso programático a los datos
  y cualquier consumidor que no sea un navegador. Cualquier tercero que quisiera
  leer las tareas públicas tendría que consumir la capa HTML, y no debería hacerlo.
- **No hay versionado de contrato.** El contrato de entrada y salida es el
  formulario y la plantilla; no hay una versión de API que mantener compatible
  hacia atrás.
- **No hay paginación ni filtros declarativos reutilizables.** `DRF` habría
  aportado paginación, filtros declarativos y `throttling` listos. El proyecto los
  resuelve a mano con `ALLOWED_SORTS` y `STATUS_FILTERS` (whitelists, no campos
  arbitrarios) y con la paginación de `ListView`.
- La integración futura, si algún día se pidiera, costaría un trabajo adicional
  real: escribir los serializers y las vistas de API desde cero, porque la capa
  de validación existente no es reutilizable tal cual.

## Alternativas descartadas

**DRF completo (opción 2).** Se descarta por dos razones concretas. La primera
es normativa: la consigna lo prohíbe. La segunda es de diseño: `ModelSerializer` +
`ViewSet` + `Router` obligarían a duplicar en serializers la validación que
`TaskForm` y `RegisterForm` ya realizan, y a resolver la divergencia entre dos
declaraciones del mismo contrato. A cambio se obtendrían endpoints que nadie
consume en el alcance del proyecto.

**DRF parcial, solo para lectura (opción 3).** Es la opción más difícil de
descartar, porque un listado público en JSON pareciera útil. Se descarta por
concreto: obligaría a instalar DRF, y por tanto a incorporarlo como dependencia,
para exponer un único caso que ninguna plantilla del proyecto consume. El
detalle de ese caso ya está resuelto sin API: `PublicTaskListView` con
`TemplateView`-style rendering, es decir un `ListView` que renderiza
`tasks/public_task_list.html`. Añadir una segunda ruta sobre el mismo modelo solo
para emitir JSON es el costo —una dependencia prohibida y una capa de
serialización— sin un consumidor que lo justifique.

**API mínima a mano con `JsonResponse` (opción 4).** Se descarta porque es la
peor de las tres: seguiría siendo una API (y por tanto está fuera del alcance
declarado del proyecto), pero sin DRF tendría que resolver a mano la
serialización, la validación de la entrada y los códigos de estado, que es
exactamente el trabajo que Django ya hace con formularios. Además, en cuanto
alguien necesitara dos o tres endpoints, la solución handmade sería peor que
DRF y peor que no tener API: ni tiene la validación de los serializers ni evita
la dependencia prohibida.
