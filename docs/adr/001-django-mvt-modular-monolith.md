# ADR-001 — Arquitectura monolítica modular sobre el patrón MVT de Django

Estado: aceptada.

## Contexto

El proyecto es un trabajo práctico final de una carrera y se entrega en cuatro
cortes. El dominio es acotado y conocido: gestoras de tareas con un dueño por
tarea, tres niveles de visibilidad de lectura, etiquetas, ordenamiento y filtro
controlados por el usuario. La consigna fija el stack: Python >= 3.12, Django
6.1.1, SQLite y plantillas de Django. También fija la forma de la capa de
presentación (todas las vistas deben ser Class-Based Views) y prohíbe Django REST
Framework.

El volumen de código es el de una aplicación pequeña: una app `tasks` con sus
modelos, formularios, vistas, URLs, admin y plantillas, más el paquete de
proyecto `config`. La base de datos es un archivo SQLite local.

## Problema

La decisión de arquitectura no es "qué framework usar" —eso ya está fijado por la
consigna— sino **qué forma darle al sistema dentro de ese framework**. En
concreto hay que decidir entre una aplicación monolítica organizada en capas
dentro de Django (el MVT/MTV que el propio Django impone) y las alternativas que
la industria propone para sistemas de mayor escala: microservicios, separación de
comandos y consultas con CQRS, registro de eventos con Event Sourcing, y una
arquitectura por capas con puertos y adaptadores.

La tentación habitual es adoptar la práctica de la industria aunque el problema
no la justifique. El riesgo es concreto: cada una de esas alternativas agrega
componentes, un modelo de despliegue y una carga conceptual que no resuelven
ninguna dificultad real de este proyecto, y convierten en difícil de explicar algo
que el proyecto entrega resuelto de forma simple.

## Opciones consideradas

1. **Monolito modular con el MVT de Django** (URLconf → vista → plantilla, más
   el ORM en la capa de modelo).
2. **Microservicios**: API gateway, servicios independientes, contratos
   versionados, despliegue y escalado separados por servicio.
3. **CQRS**: modelo de escritura y modelo de lectura separados, con
   proyecciones y, típicamente, una cola de sincronización.
4. **Event Sourcing**: el estado se deriva de un log de eventos y el modelo
   relacional es una proyección reconstruible.
5. **Arquitectura por capas con puertos y adaptadores**: casos de uso en el
   centro, dominio agnostico del framework e inversión de dependencias.

## Decisión

Se adopta la **opción 1: monolito modular sobre el MVT de Django**, es decir
monolito por despliegue y modular por comportamiento.

En la práctica esto significa:

- Un único proceso WSGI, un único proyecto Django y una única base de datos.
- Una app de dominio (`tasks`) que concentra modelos, formularios, vistas, URLs y
  admin, y que no importa nada de `config` salvo los settings que necesita.
- El proyecto Django (`config`) queda reducido a configuración: settings,
  URLconf raíz, ASGI y WSGI.
- Las plantillas viven en `templates/`, versionadas junto al proyecto, y
  heredan de una base común en lugar de duplicar estructura.
- La autorización vive en la capa de modelo, no en las vistas ni en las
  plantillas (ver [ADR-008](008-authorization-strategy.md)), lo que refuerza que
  la lógica de dominio pertenece al módulo y no al punto de entrada HTTP.

Se descarta explícitamente la variante estricta de arquitectura por capas con
inversión de dependencias completa. La separación que aporta valor en este
proyecto —las políticas de lectura y escritura, que son la parte más delicada del
dominio— ya está aislada de forma comprobable en `TaskQuerySet`. Añadir una capa
de puertos, casos de uso y adaptadores por encima de Django obligaría a duplicar
el modelo de datos, o a mantenerlo en dos lugares, y a escribir adaptadores que
solo reenvían a Django.

## Consecuencias

**Beneficios**

- El concepto de capa que la consigna pide explicar se corresponde con un hecho
  verificable en el código: una petición entra por el URLconf, la resuelve una
  vista, la vista consulta el modelo a través del ORM y renderiza una plantilla.
- Cero infraestructura de despliegue: un proceso, un archivo `db.sqlite3` y un
  servidor de archivos estáticos.
- Las transacciones son locales y triviales: guardar una tarea y sus etiquetas
  ocurre dentro de la misma unidad de trabajo del ORM.
- El refactor es barato. Un cambio de modelo se propaga a vistas y plantillas sin
  contratos que renegociar.
- Se evita por completo el problema de consistencia distribuida que CQRS y Event
  Sourcing introducen sin que exista una necesidad que lo compense.

**Costos**

- **No escala hacia despliegue independiente.** Esta es la limitación honesta de
  la decisión: con microservicios, el módulo de tareas podría escalar, fallar y
  desplegarse por separado del resto. Con este monolito, un punto de cuello de
  botella obliga a escalar el proceso completo. La afirmación correcta no es que
  microservicios serían mejores en abstracto, sino que resuelven un problema
  —escalar y desplegar módulos por separado— que este proyecto no tiene.
- Acoplamiento al framework. Mover `tasks` a otro stack significa reescribir
  vistas, formularios y plantillas: el modelo y el admin se trasladan bien, el
  resto no.
- La modularidad es por convención, no por frontera técnica. Nada impide que una
  vista de `tasks` importe lógica de otra app; con un solo módulo el riesgo es
  bajo, pero la frontera existe solo en la práctica.
- Un monolito con un único módulo no aporta el escalado interno de un monolito
  multi-módulo. Si el dominio creciera, habría que extraer fronteras reales
  (paquetes, no apps) en ese momento.

## Alternativas descartadas

**Microservicios.** Se descartan porque su beneficio central —despliegue, escalado
y aislamiento de fallos independientes por módulo— no aplica: hay un único
dominio, un único desarrollador y cuatro cortes de entrega. Su coste es inmediato
y muy alto: contratos de red entre servicios, transacciones distribuidas,
despliegue de varios procesos, manejo de fallos de red, versionado de contratos y
observabilidad distribuida. Además contradirían la consigna, que exige vistas de
clase de Django y prohíbe una API REST: un microservicio se consume por API y, sin
API, no queda nada que actúe como frontera.

**CQRS.** Se descarta porque solo tiene sentido cuando el modelo de lectura y el de
escritura divergen en forma o en carga (listados de búsqueda, agregados, lecturas
analíticas). Aquí la lectura y la escritura recaen sobre la misma tabla `tasks`
con exactamente las mismas columnas; un segundo modelo de lectura sería una copia
que se desincroniza y que nadie mantiene. Además obligaría a resolver el desfase
entre ambos modelos, que en un sistema de un solo módulo es un problema
inventado. La separación que sí existe en el proyecto —leer con `visible_to`,
escribir con `owned_by`— es una distinción de *política de acceso*, no de modelo
de datos, y no requiere CQRS.

**Event Sourcing.** Se descarta porque el dominio no tiene una razón de ser
histórico. Un usuario que marca una tarea como completada no espera poder
reconstruir el historial de cambios ni auditar una secuencia de eventos. El coste
—persistir el log de eventos además del estado, mantener proyecciones
reconstruibles, tolerar eventos tardíos y duplicados, y depurar el log en lugar
del estado— es muy superior al beneficio. El modelo relacional con
`created_at` y `updated_at` cubre la necesidad mínima de saber cuándo cambió una
tarea sin entrar en Event Sourcing.

**Arquitectura por capas con puertos y adaptadores.** Se descarta porque en un
proyecto de este tamaño la inversión de dependencias se paga con duplicación y no
se recupera. El núcleo de dominio quedaría separado de Django y habría que
mantener el modelo en dos lugares o construir un mapeo completo; cada operación
cruzaría tres capas para terminar ejecutando la misma consulta que hoy ejecuta el
ORM. La separación útil (políticas de acceso aisladas del HTTP) ya está lograda
de forma verificable en `TaskQuerySet`. Como atenuante, se conserva la buena
intención: el proyecto no mezcla el modelo con la capa HTTP, de modo que migrar
a un esquema con casos de uso sigue siendo posible si el dominio creciera.
