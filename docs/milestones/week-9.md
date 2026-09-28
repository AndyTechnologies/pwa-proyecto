# Corte Semana 9 — Entrega final: plantillas propias, formularios y documentación

**Objetivo del corte (consigna):** *"Entrega final: la aplicación debe tener sus propias
plantillas y formularios, y toda la documentación del proyecto."*

Este es el corte que cierra el proyecto. A diferencia de los anteriores, donde cada corte
sumaba una capacidad, este agrega tres cosas distintas: la capa de presentación
completa, la verificación automatizada, y el paquete documental.

## 1. Plantillas propias — 11 archivos

La consigna del corte 9 pide que la aplicación deje de usar plantillas básicas. Estado
final:

| Plantilla | Propósito |
| --- | --- |
| `base.html` | Estructura, navbar colapsable, zona de mensajes, `{% block %}` |
| `tasks/task_list.html` | Listado propio con orden, filtro de estado, filtro de etiqueta |
| `tasks/task_detail.html` | Detalle; oculta acciones si no es el propietario |
| `tasks/task_form.html` | Alta y edición, con los cuatro campos exigidos |
| `tasks/task_confirm_delete.html` | Confirmación antes de borrar |
| `tasks/public_task_list.html` | Listado público, solo lectura |
| `tasks/shared_task_list.html` | Listado de compartidas con registradas |
| `tasks/partials/task_card.html` | Tarjeta reutilizada en móvil y escritorio |
| `tasks/register.html` | Formulario de registro |
| `registration/login.html` | Inicio de sesión |
| `registration/logged_out.html` | Confirmación de cierre de sesión |

### Decisión responsive: tabla **y** tarjetas

El listado muestra siete datos por tarea. Una tabla de siete columnas en un teléfono de
360 px obliga a desplazamiento horizontal, que es la peor experiencia posible en la
pantalla más pequeña. La alternativa —ocultar columnas en móvil— obliga al usuario a
descubrir qué dato se ocultó.

La solución aplicada muestra **ambos formatos, uno visible a la vez**: la tabla se oculta
por debajo de 768 px y la grilla de tarjetas se oculta por encima. En móvil se ven
tarjetas apiladas con toda la información; en escritorio, la tabla, que comparte mejor las
columnas.

### Estados de interfaz cubiertos

Listado vacío, listado con contenido, listado filtrado sin resultados, formulario nuevo,
formulario de edición, formulario con errores, confirmación de borrado, detalle en solo
lectura para quien no es propietario, y pantalla de sesión cerrada.

## 2. Formularios propios — 2 clases

| Formulario | Base | Responsabilidad |
| --- | --- | --- |
| `TaskForm` | `ModelForm` | Alta y edición, más la resolución de etiquetas |
| `RegisterForm` | `UserCreationForm` | Registro con los cuatro validadores de contraseña |

### El campo de etiquetas y por qué es texto libre

La consigna pide asignar etiquetas y buscar por ellas. Un usuario real necesita dos
cosas a la vez: reutilizar una etiqueta que ya existe e inventar una nueva. Un selector
múltiple obliga a dos gestos y dos interfaces; un campo de texto con nombres separados
por comas permite ambos en uno, escribiendo `universidad, trabajo`.

La resolución ocurre en `TaskForm.save()`, porque un `ModelForm` no puede persistir una
relación muchos a muchos a partir de un campo de texto corriente. La limpieza normaliza
la entrada: recorta, descarta vacíos, pasa a minúsculas, elimina duplicados dentro de la
misma entrada y busca por nombre y —como fallback— por *slug*.

Ese fallback existe por el defecto 6: nombres distintos que slugifican igual
(`Python 3` y `python-3`) colisionaban contra la restricción de unicidad y producían un
`IntegrityError` que convertía el formulario en un 500.

### Las clases de Bootstrap sin `django-widget-tweaks`

Django no permite fijar atributos de un widget desde una plantilla. La solución
idiomática sería `django-widget-tweaks`, que es exactamente la dependencia que RNF-12
evita. Las clases se aplican entonces en `TaskForm.__init__`, comprobando el tipo de
widget para elegir entre selector, casilla o campo de texto.

## 3. Verificación automatizada — 249 pruebas

| Archivo | Pruebas | Responsabilidad |
| --- | ---: | --- |
| `test_models.py` | 33 | Defaults, orden del metamodelo, *slug*, M2M, cascada |
| `test_forms.py` | 56 | Campos obligatorios, enums, limpieza y resolución de etiquetas |
| `test_views.py` | 53 | Ciclo completo, autenticación, mensajes |
| `test_permissions.py` | 45 | Matriz de autorización y defensa IDOR |
| `test_filters.py` | 34 | Listas blancas, orden determinista, inyección |
| `test_regressions.py` | 28 | Un archivo por cada defecto corregido |

Herramientas nativas de Django únicamente: sin `pytest`, sin `factory_boy`, sin más
dependencias.

### Verificación independiente de la suite

Además de la suite, la entrega final se verificó **desde un clon limpio** del
repositorio, con un entorno virtual nuevo y `pip install -r requirements.txt`:

- `migrate` aplica `tasks.0001_initial` correctamente.
- La suite corre **249/249 en verde**.
- Matriz de autorización comprobada con peticiones HTTP reales:

| Actor | Privada | Compartida | Pública |
| --- | --- | --- | --- |
| Anónimo | 404 | 404 | 200 |
| Registrado no propietario | 404 | 404 | 200 |
| Propietario | 200 | 200 | 200 |

- Un `POST` de alternancia ajeno devuelve **404** y deja `completed` sin cambios.
- `GET /logout/` y `GET /tasks/<pk>/toggle/` devuelven **405**: ambos son POST.
- `makemigrations --check` no detecta cambios: las migraciones están al día.

## 4. Paquete documental — 13 documentos

| Documento | Contenido |
| --- | --- |
| `requirements.md` | 14 RF, 12 RNF, 5 no-objetivos |
| `architecture.md` | Arquitectura, ciclo de petición, diagramas |
| `data-model.md` | Diagrama ER, índices, normalización |
| `security.md` | Amenazas, IDOR, CSRF, inyección, límites |
| `testing.md` | Estrategia y cobertura |
| `development.md` | Setup, convenciones, workflow |
| `decisions.md` | Índice de ADR + 16 ambigüedades resueltas |
| `traceability.md` | Requisito → implementación → test → doc |
| `final-compliance-report.md` | Auditoría contra la consigna |
| `initial-audit.md` | Auditoría del repositorio inicial |
| `adr/` | 8 registros de decisión |
| `milestones/` | Este documento y los de las semanas 3, 5 y 7 |
| `paper/` | Paper académico (1251 líneas) y referencias |

Las 24 URLs de `paper/references.md` fueron verificadas una por una y devuelven HTTP
200. No se eligieron referencias académicas inventadas: solo documentación oficial.

## 5. Estado de cumplimiento al cerrar

Los 8 requisitos funcionales y las 2 restricciones duras: **PASS**, sin parciales.

| Restricción | Estado |
| --- | --- |
| Sin Django REST Framework | PASS — 0 en dependencias, 0 en código |
| Todas las vistas son clases | PASS — 9 CBV, 0 vistas por función |

## 6. Desviación declarada, y su consecuencia

El corte de la **semana 3** —prototipo estático con datos simulados— **se entregó junto
con el corte de la semana 7**, no por separado.

**Razón:** una maqueta estática habría sido código descartable, y mantener dos versiones
del mismo marcado introduce una divergión que nadie se ocupa de sostener. La capa de
diseño se resolvió directamente contra el modelo definitivo, lo que además permitió
verificar la interfaz con datos reales desde el primer momento.

**Consecuencia para la evaluación:** no existe un commit correspondiente al corte de la
semana 3. El contenido de ese corte está entregado y documentado, pero comparte entrega
con la semana 7. La desviación se declara también en `final-compliance-report.md` y en
`decisions.md`.

## 7. Lo que este corte NO incluye

Se registra explícitamente para que la omisión sea deliberada y no un olvido:

- Sin API ni capa de serialización (restricción de la consigna).
- Sin paginación de listados.
- Sin borrado lógico ni papelera.
- Sin restricción de fechas de vencimiento en el pasado.
- Sin pruebas de carga ni extremo a extremo en navegador.
- Sin endurecimiento para producción: `DEBUG=True` y `ALLOWED_HOSTS` vacío.

Cada una está justificada en `docs/decisions.md` y en las secciones 12 y 13 del paper.
