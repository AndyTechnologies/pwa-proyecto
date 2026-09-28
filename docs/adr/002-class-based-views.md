# ADR-002 — Class-Based Views en todo el proyecto

Estado: aceptada.

## Contexto

La consigna del trabajo final exige que **todas** las vistas sean Class-Based
Views (CBVs). No es una preferencia del equipo: es un requisito de evaluación, y
por eso esta decisión no se revierte por la comodidad del proyecto.

El proyecto tiene nueve CBVs propias en `tasks/views.py`, más dos que provienen
de Django y se usan tal cual:

- `RegisterView` (`CreateView`)
- `TaskListView` (`ListView` + `LoginRequiredMixin`)
- `TaskDetailView` (`DetailView`)
- `SharedTaskListView` (`ListView` + `LoginRequiredMixin`)
- `PublicTaskListView` (`ListView`)
- `TaskCreateView` (`CreateView` + `LoginRequiredMixin`)
- `TaskUpdateView` (`UpdateView` + `LoginRequiredMixin`)
- `TaskDeleteView` (`DeleteView` + `LoginRequiredMixin`)
- `TaskCompleteToggleView` (`View` + `LoginRequiredMixin`, solo `POST`)

Y en el URLconf raíz, `django.contrib.auth.views.LoginView` y `LogoutView`, que
también son CBVs.

Cada vista se instancia con `as_view()` en `config/urls.py` o `tasks/urls.py`.
**No existe ninguna Function-Based View en el codebase.**

## Problema

Hay que elegir el estilo de vista y hay que justificarlo con honestidad. La
tensión es real: la documentación de Django advierte que las vistas genéricas
introducen indirección y que, para una vista muy simple, una función resulta más
directa y más fácil de leer. Quien conoce esa documentación puede sostener
razonadamente que en este proyecto la mayoría de las vistas son simples y que las
CBV son sobreingeniería justificada por una restricción externa.

La decisión debe argumentar a favor sin ocultar ese coste, y debe dejar claro qué
parte del argumento es "esto es mejor por sí mismo" y qué parte es "esto es
obligatorio por la consigna y, además, tiene un beneficio propio".

## Opciones consideradas

1. **CBVs para todas las vistas**, apoyadas en `django.views.generic` y en
   `django.contrib.auth.mixins`.
2. **Function-Based Views** para todo.
3. **Híbrido**: CBVs donde la reutilización aporta y FBVs para pantallas
   triviales.
4. **Una clase base propia de vista**, con helpers de sesión, mensajes y
   redirección, para no repetir esos bloques en cada subclase.

## Decisión

Se adopta la **opción 1: todas las vistas son CBVs**, usando las vistas genéricas
de `django.views.generic` como base y `django.contrib.auth.mixins` para el control
de acceso.

El argumento tiene dos partes, y conviene no mezclarlas.

**Es un requisito.** La consigna lo pide explícitamente. Incumplirlo descalifica
el entregable, y por eso las opciones 2 y 3 no se evalúan como alternativas
reales sino como lo que serían: incumplimiento.

**Además, el estilo paga un dividendo real en el código concreto.** El beneficio
no es abstracto ("las CBV son más DRY"); se ve en cuatro puntos del proyecto:

- **Reutilización de mixins.** `LoginRequiredMixin` aparece en seis vistas y
  resuelve la redirección al login sin escribir una sola línea por vista. La
  regla "esta vista exige sesión" queda enunciada en la cabecera de la clase,
  donde se lee, en lugar de estar escondida en un decorador o en la primera
  línea del cuerpo.
- **Reutilización del queryset.** `get_queryset()` es el punto de extensión que
  usa `TaskQuerySet.owned_by` y `visible_to` (ADR-008). Con `UpdateView` y
  `DeleteView` se obtiene resolución de objeto restringida al propietario sin
  duplicar el filtro.
- **Un ciclo de vida ya resuelto.** `CreateView` y `UpdateView` gestionan
  `form_valid`, la redirección de éxito y el binding del objeto; `DeleteView`
  gestiona la confirmación. El código propio queda reducido a lo propio del
  dominio.
- **Un punto de extensión nombrado para las URL.** `as_view()` separa la
  configuración de la URL de la implementación de la vista.

La opción 4 (clase base propia) se descarta: la repetición que resolvería es
pequeña —un `messages.success` y un `get_success_url` por vista— y una clase base
propia agregaría indirección justo en el punto donde la consigna pide claridad.

## Consecuencias

**Beneficios**

- Requisito de la consigna cumplido de forma total y verificable: cero
  Function-Based Views en el repositorio, y `LoginView` y `LogoutView` son CBVs
  de Django.
- Autenticación obligatoria reutilizable y declarativa.
- Resolución de objetos filtrada por propietario reutilizable entre
  `TaskUpdateView` y `TaskDeleteView`.
- Menos código por vista y un contrato uniforme: toda vista declara `model`,
  `form_class`, `template_name` y `context_object_name`.
- Homogeneidad con las vistas de autenticación de Django, que también son CBVs,
  de modo que la capa de presentación es uniforme de punta a punta.

**Costos**

- **Más verboso y menos obvio que una función para páginas triviales.** Una vista
  que solo muestra texto estático se escribe en menos líneas como función. Es un
  coste real, y la documentación de Django lo señala.
- **El flujo de una petición no se lee de arriba abajo en el archivo.** Hay que
  saber qué hace `ListView` para entender una subclase. Para quien ya conoce
  Django es un coste bajo; para quien empieza, es un obstáculo real.
- **El comportamiento se reparte en varios puntos.** Cambios de clase en
  `get_queryset`, `get_context_data`, `form_valid` y atributos de clase, de modo
  que una misma vista puede necesitar tocarse en lugares dispersos.
- **Métodos hook disponibles que no siempre se usan.** `get_context_data`
  aparece en más vistas de las estrictamente necesarias, porque el punto de
  extensión existe aunque no se aproveche siempre.
- Riesgo de sobreingeniería si cada vista termina reescribiendo la mitad del
  comportamiento de su clase base. El proyecto lo evita concentrando la lógica
  en `TaskQuerySet` (ADR-008) en lugar de dispersarla entre las subclases.

## Alternativas descartadas

**Function-Based Views para todo.** Se descarta por dos motivos, en este orden. El
primero es directo: la consigna exige CBVs y esta opción la incumple. El segundo,
independiente del requisito, es que en este proyecto la jerarquía paga: seis
vistas comparten `LoginRequiredMixin` y dos comparten la resolución por
propietario. En FBV eso se resolvería con un decorador escrito a medida más un
`get_object_or_404` repetido en cada función, moviendo la política de acceso del
lugar donde se lee hacia un lugar donde se llama. Conviene reconocer que para una
aplicación de una sola página trivial la respuesta sería la inversa: la función
sería más corta y más clara.

**Híbrido (CBVs para lo reutilizable, FBVs para lo trivial).** Se descarta porque
es la opción que peor se sostiene frente a la consigna: permite resolver el
requisito solo a medias y obliga a cada vista a justificar individualmente por qué
usa una forma u otra. El resultado es un criterio de estilo no uniforme en un
proyecto evaluado sobre consistencia. Además, la única vista que realmente podría
beneficiarse de ser trivial —la lista pública— necesita igual un `get_queryset`
propio, así que la hibridación no habría eliminado ni una clase ni una función.

**Clase base propia de vista (opción 4).** Se descarta porque la repetición que
elimina es de una o dos líneas por vista (`get_success_url`, un
`messages.success`), mientras que el coste sí es estructural: una capa de
herencia más que hay que comprender antes de entender cualquier vista, en un
proyecto cuyo objetivo pedagógico es que cada vista se lea por sí sola. Se
conserva el poder de las clases sin la capa intermedia.
