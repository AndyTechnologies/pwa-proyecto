# Corte Semana 7 — Routing, vistas y autenticación

**Objetivo del corte (consigna):** *"Enrutamientos, vistas y autentificación. El sitio ya
debe ser funcional, pero con plantillas muy básicas."*

## Vistas implementadas — las 9 son Class-Based Views

| Vista | Base | Mixin | Requisito |
| --- | --- | --- | --- |
| `RegisterView` | `CreateView` | — | RF-01 |
| `TaskListView` | `ListView` | `LoginRequiredMixin` | RF-07 |
| `TaskDetailView` | `DetailView` | — | RF-12 |
| `SharedTaskListView` | `ListView` | `LoginRequiredMixin` | RF-14 |
| `PublicTaskListView` | `ListView` | — | RF-13 |
| `TaskCreateView` | `CreateView` | `LoginRequiredMixin` | RF-03 |
| `TaskUpdateView` | `UpdateView` | `LoginRequiredMixin` | RF-04 |
| `TaskDeleteView` | `DeleteView` | `LoginRequiredMixin` | RF-05 |
| `TaskCompleteToggleView` | `View` | `LoginRequiredMixin` | RF-06 |

`auth_views.LoginView` y `auth_views.LogoutView` cubren RF-02. **Cero vistas
function-based.**

## URLs

```
/admin/                  Django Admin
/login/                  LoginView
/logout/                 LogoutView  (POST only, Django 5+)
/register/               RegisterView
/tasks/                  TaskListView              (requiere login)
/tasks/create/           TaskCreateView            (requiere login)
/tasks/public/           PublicTaskListView        (anónimo permitido)
/tasks/shared/           SharedTaskListView        (requiere login)
/tasks/<pk>/             TaskDetailView            (según política de lectura)
/tasks/<pk>/edit/        TaskUpdateView            (solo owner)
/tasks/<pk>/delete/      TaskDeleteView            (solo owner)
/tasks/<pk>/toggle/      TaskCompleteToggleView    (POST only, solo owner)
```

Todas con nombre y bajo el namespace `tasks`. Ninguna ruta hardcodeada en plantillas.

## Autorización — verificada con peticiones reales

Toda vista mutable resuelve objetos por `Task.objects.owned_by(user)` y la de detalle por
`Task.objects.visible_to(user)`. Resultado medido:

| Tarea de alice | Anónimo | Bob (registrado) | Alice (owner) |
| --- | --- | --- | --- |
| PRIVATE | 404 | 404 | 200 |
| AUTHENTICATED | 404 | 200 (solo lectura) | 200 |
| PUBLIC | 200 (solo lectura) | 200 (solo lectura) | 200 |

Y sobre la tarea pública de alice, el usuario bob:

| Operación | Resultado | Razón |
| --- | --- | --- |
| `GET /tasks/<pk>/` | 200 | Lectura permitida |
| `GET /tasks/<pk>/edit/` | 404 | No es owner |
| `GET /tasks/<pk>/delete/` | 404 | No es owner |
| `POST /tasks/<pk>/toggle/` | 404 | No es owner |
| `GET /logout/` | 405 | Logout es POST-only |

El 404 —y no 403— es deliberado: un 403 confirmaría que la tarea existe, lo que filtra
información sobre datos ajenos.

## Ordenamiento y filtrado con whitelist

`ALLOWED_SORTS = {"due_date", "priority"}` y `STATUS_FILTERS = {all, pending, completed}`.
El input del usuario es solo una *clave* del diccionario, nunca un nombre de campo que
llegue al ORM. Cada ordenamiento añade `-pk` como desempate determinista.

Comportamiento con entradas maliciosas, medido:

| Entrada | Resultado |
| --- | --- |
| `?sort=owner; DROP TABLE tasks--` | 200, cae a `due_date` |
| `?sort=' or 1=1--` | 200, cae a `due_date` |
| `?status=INJECTED` | 200, cae a `all` |
| `?tag=inexistente` | 200, lista vacía |

## Etiquetas

Many-to-Many entre `Task` y `Tag`, con reutilización insensible a mayúsculas
(`Tag.objects.matching()`) y resolución por slug para evitar colisiones entre nombres
que colisionan al slugificar.

## Defectos encontrados y corregidos durante este corte

Se documentan porque la consigna exige registrar lo descubierto (§38, tests de
regresión):

1. `is_editable_by` estaba declarado como `@property` pero recibía un parámetro `user`.
   Un property no admite argumentos: reventaba con `TypeError` en toda página de detalle.
   Corregido a método.
2. `all_tags` consultaba `user.tasks.order_by("name")`; `user.tasks` son `Task`, no
   `Tag`, y `Task` no tiene campo `name` → `FieldError` en el listado. Corregido a
   `Tag.objects.filter(tasks__owner=...)`.
3. Faltaba la ruta `register/`; toda página anónima devolvía 500 por `NoReverseMatch`.
4. `TaskUpdateView` sin `context_object_name`, por lo que el formulario de edición
   mostraba el título "Nueva tarea".
5. Los widgets no tenían clases Bootstrap. No es posible fijarlas desde una plantilla
   de Django, y `django-widget-tweaks` es una dependencia que la consigna no justifica
   (RNF-12), así que se aplican en `TaskForm.__init__`.
6. **Colisión de slug en `Tag`**: nombres distintos que slugifican igual (`Python 3` y
   `python-3`) provocaban `IntegrityError` → 500. `TaskForm._resolve_tags` ahora busca
   también por slug.
7. Las URLs de `tasks.urls` estaban montadas en `""` en lugar de `"tasks/"`, por lo que
   las rutas reales eran `/<pk>/` y no `/tasks/<pk>/` como pide la consigna.
