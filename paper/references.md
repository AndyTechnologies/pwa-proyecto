# Referencias

Este archivo contiene únicamente fuentes verificables y de existencia comprobada:
las documentaciones oficiales de las tres tecnologías que el proyecto usa como
base, más la documentación del motor de base de datos. No se incluyen artículos
científicos, libros, tesis ni identificadores bibliográficos que no puedan
verificarse, porque una referencia no comprobada es peor que una referencia
ausente.

---

## 1. Django Software Foundation — Django 6.1 documentation

- **Organismo:** Django Software Foundation
- **Título:** *Django 6.1 documentation*
- **Versión:** 6.1 (el proyecto fija Django 6.1.1)
- **URL canónica:** <https://docs.djangoproject.com/en/6.1/>
- **Secciones citadas en este trabajo:**
  - *Writing views* — vistas basadas en clases (`ListView`, `DetailView`,
    `CreateView`, `UpdateView`, `DeleteView`, `View`) y el mecanismo
    `get_queryset()`.
    <https://docs.djangoproject.com/en/6.1/topics/class-based-views/>
  - *The queryset API* — Filtering, `Q` objects y `order_by`.
    <https://docs.djangoproject.com/en/6.1/ref/models/querysets/>
  - *Model field reference* — `IntegerChoices`, `TextChoices`, `ManyToManyField`,
    `SlugField` e índices en `Meta.indexes`.
    <https://docs.djangoproject.com/en/6.1/ref/models/fields/>
  - *Authentication* — `django.contrib.auth`, `AuthenticationForm`,
    `LoginView`, `LogoutView` y `LoginRequiredMixin`.
    <https://docs.djangoproject.com/en/6.1/topics/auth/default/>
  - *Security* — protección CSRF, escapado automático de plantillas y
    recomendaciones de endurecimiento para producción.
    <https://docs.djangoproject.com/en/6.1/topics/security/>
  - *Template engine* — sintaxis de plantillas y herencia con `{% extends %}`.
    <https://docs.djangoproject.com/en/6.1/topics/templates/>
  - *Testing* — el ejecutor de pruebas integrado y `TestCase`.
    <https://docs.djangoproject.com/en/6.1/topics/testing/>
  - *System check framework* — `manage.py check` y `manage.py test`.
    <https://docs.djangoproject.com/en/6.1/ref/checks/>
- **Uso en este trabajo:** es la referencia primaria del proyecto. Define el
  patrón MVT, el ORM, el sistema de autenticación, las vistas basadas en clases,
  el motor de plantillas, la protección CSRF y el ejecutor de pruebas. Todas las
  afirmaciones sobre el comportamiento de Django en este texto se apoyan en esta
  fuente.

---

## 2. Python Software Foundation — Python 3.12 documentation

- **Organismo:** Python Software Foundation
- **Título:** *The Python 3.12 documentation*
- **Versión:** 3.12
- **URL canónica:** <https://docs.python.org/3.12/>
- **Secciones citadas en este trabajo:**
  - *Tutorial: Virtual Environments and Packages* — el uso de `venv` y `pip`
    como uno de los dos caminos de instalación soportados.
    <https://docs.python.org/3.12/tutorial/venv.html>
  - *The Python Standard Library* — en particular `enum`, base de los tipos
    `IntegerChoices` y `TextChoices` que el proyecto usa para `Priority` y
    `Visibility`.
    <https://docs.python.org/3.12/library/enum.html>
  - *Data Persistence* — la biblioteca `sqlite3`, que es la que emplea
    internamente Django para el motor SQLite.
    <https://docs.python.org/3.12/library/sqlite3.html>
- **Uso en este trabajo:** fundamenta el lenguaje sobre el que corre el
  proyecto, el mecanismo de entornos virtuales que hace reproducible la
  instalación, y el módulo `enum` del que derivan las enumeraciones del modelo de
  dominio.

---

## 3. The Bootstrap Team — Bootstrap 5.3 documentation

- **Organismo:** The Bootstrap Team
- **Título:** *Bootstrap 5.3 documentation*
- **Versión:** 5.3 (el proyecto fija Bootstrap 5.3.8)
- **URL canónica:** <https://getbootstrap.com/docs/5.3/>
- **Secciones citadas en este trabajo:**
  - *Layout* — sistema de cuadrícula, puntos de corte `md`, `lg` y
    contenedores.
    <https://getbootstrap.com/docs/5.3/layout/grid/>
  - *Components* — navbar, tarjetas, tablas, formularios, botones y
    discontinuidades.
    <https://getbootstrap.com/docs/5.3/components/>
  - *Content* — rebobinado tipográfico y utilidades de texto.
    <https://getbootstrap.com/docs/5.3/content/>
  - *Helpers* — utilidades de espaciado, flexbox y color.
    <https://getbootstrap.com/docs/5.3/helpers/>
  - *Accessibility* — etiquetas ARIA y recomendaciones de uso.
    <https://getbootstrap.com/docs/5.3/getting-started/accessibility/>
- **Uso en este trabajo:** es la referencia del sistema visual. La decisión de
  alternar entre tabla y tarjetas según el ancho de pantalla se apoya en las
  reglas de la cuadrícula y en los puntos de corte documentados aquí, no en
  criterio personal.

---

## 4. SQLite Consortium — SQLite Documentation

- **Organismo:** SQLite Consortium (dominio oficial del proyecto)
- **Título:** *SQLite Documentation*
- **URL canónica:** <https://www.sqlite.org/docs.html>
- **Secciones citadas en este trabajo:**
  - *Documentation Index* — organized by subject.
    <https://www.sqlite.org/docs.html>
  - *CREATE TABLE* — restricciones `UNIQUE` y `NOT NULL`, que respaldan la
    integridad de `Tag.name` y `Tag.slug`.
    <https://www.sqlite.org/lang_createtable.html>
  - *Query Planning* — comportamiento del planificador y/utilidad de los
    índices, relevante para justificar los dos índices declarados en
    `Task.Meta.indexes`.
    <https://www.sqlite.org/queryplanner.html>
  - *Transactional Behavior* — transacciones y propiedades ACID, que explican
    por qué una restricción `UNIQUE` violada aborta la operación con un error de
    integridad en lugar de guardar un dato duplicado.
    <https://www.sqlite.org/transactional.html>
  - *WAL Mode* — comportamiento del registro de escritura, relevante para la
  declaración de limitación sobre concurrencia.
    <https://www.sqlite.org/wal.html>
- **Uso en este trabajo:** sustenta las afirmaciones sobre integridad referencial
  y de unicidad, sobre la utilidad de los índices y sobre las limitaciones de
  concurrencia del motor por defecto.

---

## Nota sobre el criterio de citación

La consigna exige no inventar referencias. Por eso este listado es corto a
propósito: cuatro fuentes oficiales y verificables sostienen la totalidad de las
afirmaciones técnicas del trabajo. Los conceptos de arquitectura que aparecen en
la sección 10 se presentan con su propio razonamiento —requisito, restricción,
alternativas, decisión y consecuencia— y no se respaldan con citas
bibliográficas de autoría incierta, sino con la evidencia del propio repositorio
documentada en `docs/adr/`.

No se incluyen números de página, ISBN, DOI ni nombres de revista porque no
hay ninguna fuente de ese tipo que pueda verificarse con certeza.
