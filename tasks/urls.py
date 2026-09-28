"""URL routes for the tasks app.

Every route is named so templates can use ``{% url %}`` instead of hardcoding
paths (requirement 36).
"""

from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskListView.as_view(), name="task-list"),
    path("create/", views.TaskCreateView.as_view(), name="task-create"),
    path("public/", views.PublicTaskListView.as_view(), name="public-task-list"),
    path("shared/", views.SharedTaskListView.as_view(), name="shared-task-list"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task-update"),
    path("<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task-delete"),
    path("<int:pk>/toggle/", views.TaskCompleteToggleView.as_view(), name="task-toggle"),
]
