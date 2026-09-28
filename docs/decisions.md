# Decisiones de diseño y ambigüedades resueltas

Este documento es el índice de las decisiones arquitectónicas del proyecto y el registro
de las ambigüedades de la consigna que se resolvieron sin consultar al destinatario.

Los registros completos, cada uno con contexto, alternativas evaluadas, decisión,
consecuencias y estado, están en [`adr/`](adr/). La justificación extendida, con el
razonamiento completo, está en el [paper académico](../paper/paper.md) §10.

## Decisiones arquitectónicas

| ADR | Decisión | Alternativa descartada | Costo asumido |
| --- | --- | --- | --- |
| [001](adr/001-django-mvt-modular-monolith.md) | Monolito modular sobre el ciclo de Django | Microservicios, capas con Ports and Adapters, Event Sourcing | Sin escalado ni despliegue independiente |
| [002](adr/002-class-based-views.md) | Clases genéricas de Django (`ListView`, `CreateView`, …) | Clases escritas desde cero, o vistas por función | Lectura menos evidente; exige conocer el orden de los *mixins* |
| [003](adr/003-no-django-rest-framework.md) | Server-rendered, sin capa de API | API REST paralela | Sin acceso programático; la validación se escribe a mano |
| [004](adr/004-django-authentication.md) | `django.contrib.auth` con `LoginView`, `LogoutView`, `UserCreationForm` | Autenticación propia, biblioteca de terceros | Dependencia del framework; el registro no inicia sesión |
| [005](adr/005-task-visibility-model.md) | Campo `Visibility` con tres valores en `Task` | Tabla de permisos por usuario, lista de usuarios autorizados | No permite compartir con usuarios concretos |
| [006](adr/006-many-to-many-tags.md) | `Tag` con relación `ManyToMany` | Campo de texto libre, copia de la etiqueta por tarea | La resolución de etiquetas al guardar es la parte más delicada del formulario |
| [007](adr/007-bootstrap-5.md) | Bootstrap 5.3.8 con los *assets* vendorizados | CDN, CSS propio, otro sistema de utilidades | Las actualizaciones son manuales |
| [008](adr/008-authorization-strategy.md) | Políticas en `TaskQuerySet` (`owned_by`, `visible_to`) | `UserPassesTestMixin`, decoradores, marco propio de permisos | El 404 borra la distinción entre «no existe» y «no permitido» |

### Las dos decisiones que sostienen el resto

**ADR-008 es la decisión estructural del proyecto.** Concentrar la autorización en el
`QuerySet` —y no en las vistas— es lo que garantiza que ninguna vista pueda
reimplementar las reglas. La consecuencia medible es que la seguridad del sistema se
puede verificar con la suite de pruebas sin inspeccionar las vistas una por una.

**ADR-005 es la decisión de dominio.** La consigna pide un número cerrado de estados de
visibilidad, y un campo enumerado es la representación directa de esa forma cerrada. El
riesgo —que la visibilidad llegue a conceder escritura— está cerrado por diseño: las
consultas de escritura nunca consultan el campo de visibilidad, usan `owned_by()`.

## Ambigüedades de la consigna resueltas

La consigna, en su apartado final, indica que no se consulten las ambigüedades que puedan
quedarse resueltas por criterio. Las que surgieron y cómo se resolvieron:

| # | Ambigüedad | Resolución | Motivo |
| --- | --- | --- | --- |
| 1 | Formato del campo prioridad | Entera: 1 baja, 2 media, 3 alta | `ORDER BY priority` coincide con el orden semántico, sin tabla auxiliar |
| 2 | Formato del campo visibilidad | Cadena: `private`, `authenticated`, `public` | Legible en SQL, en logs y en la administración; añade niveles sin migrar datos |
| 3 | ¿El registro inicia sesión automáticamente? | No; redirige a `/login/` | Estado de sesión explícito y predecible; revela de inmediato una contraseña mal elegida |
| 4 | ¿Cierre de sesión por `GET` o `POST`? | `POST` exclusivamente | Django 5 eliminó el `GET`; un enlace permitiría cerrar la sesión desde otro sitio |
| 5 | ¿Visibilidad pública con o sin sesión? | Sin sesión: el requisito 7 nombra al usuario anónimo | La consigna lo pide explícitamente |
| 6 | ¿Se puede editar una tarea compartida? | No; la visibilidad concede solo lectura | El requisito 7 dice «solo lectura» de forma explícita |
| 7 | ¿Las etiquetas se seleccionan de una lista o se escriben? | Campo de texto con nombres separados por comas | Permite reutilizar e inventar etiquetas en un solo gesto |
| 8 | ¿Las tareas pueden vencidas en el pasado? | Sí; no se restringe | La consigna exige el campo, no su restricción; registrar tareas atrasadas es legítimo |
| 9 | ¿Se guarda la fecha de completado? | No | `updated_at` ya cambia; un campo más sería redundante (RNF-12) |
| 10 | ¿Hay paginación? | No | No es requisito y no es necesario en el volumen del curso; coherente con RNF-12 |
| 11 | ¿Se borra lógicamente? | No | No es requisito; añadiría estado a cada consulta |
| 12 | ¿Bootstrap por CDN o vendorizado? | Vendorizado | La aplicación funciona sin red y ambos caminos de instalación se comportan igual |
| 13 | ¿Modelos de usuario y perfil propios? | Solo `django.contrib.auth` | La consigna no pide datos de perfil; duplicar la autenticación sería redundante |
| 14 | ¿Controles de formulario con `django-widget-tweaks`? | No; clases aplicadas en el `Form.__init__` | RNF-12 evita dependencias innecesarias |
| 15 | ¿Qué base de datos? | SQLite en desarrollo | La consigna no exige producción; se documenta que SQLite no es apta para concurrencia |
| 16 | ¿App `core` o `tasks`? | `tasks` | `core` contenía una sola vista de saludo, sin lógica de dominio |

## Desviación declarada

El **corte de la semana 3** —prototipo estático con datos simulados— se entregó
**junto con el corte de la semana 7**, no por separado.

La razón es que una maqueta estática habría sido código descartable, y mantener dos
versiones del mismo marcado introduce una divergión que nadie sostiene. La capa de diseño
se resolvió directamente contra el modelo definitivo.

La consecuencia para la evaluación: **no existe un commit correspondiente al corte de la
semana 3**. El contenido de ese corte sí está entregado y documentado en
[`milestones/week-3.md`](milestones/week-3.md), pero comparte entrega con la semana 7.

Esta desviación está declarada también en [`final-compliance-report.md`](final-compliance-report.md)
y en [`milestones/week-7.md`](milestones/week-7.md).
