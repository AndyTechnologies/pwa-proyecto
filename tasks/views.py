"""Class-Based Views for the Task Manager.

Every view in this module is a CBV, as required by the assignment. Authorization
is enforced here at the queryset level, never in the templates: mutable views
resolve objects through :meth:`TaskQuerySet.owned_by`, so a task the viewer does
not own is never fetched and results in 404 rather than 403 (ADR-008).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, DetailView, ListView, RedirectView, UpdateView, View

from .forms import RegisterForm, TaskForm
from .models import Tag, Task, Visibility

# Whitelist of sortable fields. User input is only ever a *key* into this map,
# never a field name handed to the ORM, so `?sort=` cannot be used to order by
# an arbitrary column (RF-08).
ALLOWED_SORTS = {
    "due_date": ["due_date"],
    "priority": ["priority"],
}

# Every sort gets a deterministic tie-breaker so that two tasks with the same
# due_date/priority never swap places between requests (RF-08).
SORT_TIE_BREAKER = ["-pk"]

# Whitelist for `?status=`. Anything else falls back to "all" instead of
# reaching the ORM (RF-09).
STATUS_FILTERS = {
    "all": None,
    "pending": False,
    "completed": True,
}
DEFAULT_STATUS = "all"


class HomeRedirectView(RedirectView):
    """Entry point for ``/`` — the app's front door.

    ``/`` used to 404, so the first thing a visitor saw was Django's error
    page. It now decides where to send them by session state: an authenticated
    user goes to their task list, an anonymous one goes to the login page (from
    which, after signing in, ``LOGIN_REDIRECT_URL`` continues to the task list).

    A non-permanent redirect is deliberate: this is a routing decision that
    depends on who is asking, not a permanent move of the URL.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse("tasks:task-list")
        return reverse("login")


class RegisterView(CreateView):
    """RF-01 — self-service user registration.

    Deliberately does not log the user in afterwards: the assignment leaves the
    behaviour open, and redirecting to the login screen keeps the session state
    predictable. Documented in ADR-004 and covered by tests.
    """

    form_class = RegisterForm
    template_name = "tasks/register.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Cuenta creada correctamente. Ya podés iniciar sesión.",
        )
        return response

    def get_success_url(self):
        return reverse("login")


class TaskListView(LoginRequiredMixin, ListView):
    """RF-07/RF-08/RF-09/RF-11 — the owner's task list.

    Scoped to the requesting user, then narrowed by the optional `status`, `tag`
    and `sort` query parameters, each validated against a whitelist.
    """

    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        queryset = Task.objects.owned_by(self.request.user).prefetch_related("tags")

        self.status = self.request.GET.get("status", DEFAULT_STATUS)
        if self.status not in STATUS_FILTERS:
            self.status = DEFAULT_STATUS
        completed = STATUS_FILTERS[self.status]
        if completed is not None:
            queryset = queryset.filter(completed=completed)

        self.tag = self.request.GET.get("tag", "").strip()
        if self.tag:
            queryset = queryset.filter(tags__slug=slugify(self.tag))

        self.sort = self.request.GET.get("sort", "due_date")
        if self.sort not in ALLOWED_SORTS:
            self.sort = "due_date"
        return queryset.order_by(*ALLOWED_SORTS[self.sort], *SORT_TIE_BREAKER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status"] = self.status
        context["tag"] = self.tag
        context["sort"] = self.sort
        context["allowed_sorts"] = ALLOWED_SORTS
        context["all_tags"] = (
            Tag.objects.filter(tasks__owner=self.request.user)
            .order_by("name")
            .distinct()
        )
        return context


class TaskDetailView(DetailView):
    """Read one task under the read policy.

    A public task opens for anonymous visitors; a shared task opens for any
    authenticated user; a private task is only reachable by its owner. Anything
    else 404s (RF-12, RF-13, RF-14).
    """

    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.visible_to(self.request.user).prefetch_related("tags")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_owner"] = self.object.is_editable_by(self.request.user)
        return context


class SharedTaskListView(LoginRequiredMixin, ListView):
    """RF-14 — tasks other users have shared with the viewer (read-only)."""

    model = Task
    template_name = "tasks/shared_task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        return (
            Task.objects.visible_to(self.request.user)
            .exclude(owner=self.request.user)
            .prefetch_related("tags")
            .order_by("-created_at", "-pk")
        )


class PublicTaskListView(ListView):
    """RF-13 — browse every PUBLIC task, no authentication required."""

    model = Task
    template_name = "tasks/public_task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        return (
            Task.objects.filter(visibility=Visibility.PUBLIC)
            .prefetch_related("tags")
            .order_by("-created_at", "-pk")
        )


class TaskCreateView(LoginRequiredMixin, CreateView):
    """RF-03 — create a task owned by the requesting user."""

    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Tarea creada correctamente.")
        return response

    def get_success_url(self):
        return reverse("tasks:task-list")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    """RF-04 — edit, restricted to the owner through the queryset."""

    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    context_object_name = "task"

    def get_queryset(self):
        return Task.objects.owned_by(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Tarea actualizada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tasks:task-list")


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    """RF-05 — delete, restricted to the owner through the queryset."""

    model = Task
    template_name = "tasks/task_confirm_delete.html"

    def get_queryset(self):
        return Task.objects.owned_by(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Tarea eliminada correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tasks:task-list")


class TaskCompleteToggleView(LoginRequiredMixin, View):
    """RF-06 — toggle completed/pending, owner only, POST only.

    A ``View`` subclass is still a Class-Based View, which the assignment
    requires. GET is refused so the state can never be changed by following a
    link or prefetching a URL.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(Task.objects.owned_by(request.user), pk=pk)
        task.completed = not task.completed
        task.save(update_fields=["completed", "updated_at"])
        messages.success(
            request,
            "Tarea marcada como completada." if task.completed else "Tarea marcada como pendiente.",
        )
        return redirect("tasks:task-detail", pk=task.pk)

    def get(self, request, pk):
        return HttpResponseNotAllowed(["POST"])
