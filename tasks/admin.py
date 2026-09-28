"""Django Admin configuration.

Required by the Semana 5 deliverable ("modelos creados y registrados en el
Sitio de Administración de Django"). Configured to be actually useful for
inspection and moderation, not just a bare registration.
"""

from django.contrib import admin

from .models import Tag, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "due_date",
        "priority",
        "completed",
        "visibility",
        "tag_list",
    )
    list_filter = ("completed", "visibility", "priority", "due_date")
    search_fields = ("title", "description", "owner__username")
    autocomplete_fields = ("tags",)
    date_hierarchy = "due_date"
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Tarea", {"fields": ("title", "description", "due_date", "priority")}),
        ("Estado y privacidad", {"fields": ("completed", "visibility")}),
        ("Etiquetas", {"fields": ("tags",)}),
        ("Auditoría", {"fields": ("owner", "created_at", "updated_at")}),
    )

    @admin.display(description="Etiquetas", ordering="tags__name")
    def tag_list(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "task_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    @admin.display(description="Tareas")
    def task_count(self, obj):
        return obj.tasks.count()
