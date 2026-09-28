# Corte Semana 3 — Prototipo visual Bootstrap 5

**Objetivo del corte (consigna):** *"Sitio web estático basado en Bootstrap 5 como
prototipo de diseño."*

## Desviación respecto de la consigna — declarada

Este corte se entregó **junto con el de Semana 7**, no como un incremento separado con
datos mock. La razón es concreta: una maqueta estática separada habría sido código
desechable. Django Templates no exige datos reales para renderizar, y la capa de
diseño (estructura, jerarquía visual, estados) se resolvió directamente contra el
modelo definitivo. Las decisiones de diseño son exactamente las que se habrían tomado
en la maqueta; lo que se evitó fue mantener dos versiones del HTML.

Queda registrado como desviación en `docs/final-compliance-report.md`.

## La capa de diseño entregada

### Sistema visual

Bootstrap 5.3.8 **vendorizado** en `static/css/` y `static/js/`. No se usa CDN: la
aplicación renderiza completa sin acceso a la red, y esto se decidió así en el commit
inicial. Los assets están bajo licencia MIT.

### Sistema de plantillas

Jerarquía de herencia, sin duplicación de navbar ni pie:

```
templates/base.html
├── registration/login.html
├── registration/logged_out.html
└── tasks/
    ├── task_list.html
    ├── task_detail.html
    ├── task_form.html          (create y edit)
    ├── task_confirm_delete.html
    ├── shared_task_list.html
    ├── public_task_list.html
    └── partials/task_card.html  (tarjeta reutilizada por los 3 listados)
```

### Responsive

Verificado en tres anchos: **360 px** (móvil), **768 px** (tablet) y **1440 px**
(escritorio).

- Navbar colapsable con `data-bs-toggle="collapse"`.
- El listado usa una **tabla Bootstrap en md+** (`d-none d-md-block`) y **tarjetas apiladas
  en móvil** (`d-md-none`). Se chose este patrón y no scroll horizontal porque en 360 px
  una tabla de 7 columnas obliga a desplazamiento lateral, que es la peor experiencia
  posible en la pantalla más chica.
- Grilla de tarjetas `row row-cols-1 row-cols-md-2 row-cols-lg-3` en los listados
  públicos y compartidos.
- Formularios con clases `form-control` / `form-select` / `form-check-input`.

### Estados de interfaz cubiertos

| Estado | Dónde |
| --- | --- |
| Lista vacía | `task_list.html`, `shared_task_list.html`, `public_task_list.html` |
| Lista con contenido | Las mismas, con tarjetas y badges |
| Lista filtrada sin resultados | `task_list.html` (estado vacío específico de filtro) |
| Formulario nuevo | `task_form.html` con `{% if task %}` para el título |
| Formulario de edición | Idem, con datos precargados y etiquetas como texto |
| Formulario con errores | `invalid-feedback` + `is-invalid` + `alert-danger` |
| Confirmación de borrado | `task_confirm_delete.html` |
| Solo lectura | `task_detail.html` cuando `is_owner` es falso |
| Sesión cerrada | `registration/logged_out.html` |
| Mensajes | `base.html`, mapeados desde `message.tags` a alertas Bootstrap |

### Codificación visual del dominio

| Elemento | Tratamiento |
| --- | --- |
| Prioridad LOW | `bg-secondary` |
| Prioridad MEDIUM | `bg-warning text-dark` |
| Prioridad HIGH | `bg-danger` |
| Tarea completada | `text-decoration-line-through` + `opacity-75` |
| Tarea vencida y pendiente | Badge `bg-danger` "Vencida" |
| Visibilidad | Badge con `get_visibility_display()` |
| Etiquetas | Badges secundarios por etiqueta |

## Accesibilidad (RNF-08)

- HTML semántico: `<nav>`, `<main>`, `<table>` con `<thead>`/`<th scope>`.
- Cada input tiene su `<label class="form-label">` asociado.
- Errores con `aria`-friendly `invalid-feedback`, no solo color.
- Acciones destructivas con confirmación explícita.
- Contraste respetado por la paleta de Bootstrap.

## Verificación

Los 11 templates compilan (`get_template()`), `manage.py check` sin problemas, y todas
las páginas responden 200 en los escenarios válidos y 404/302 en los inválidos.
