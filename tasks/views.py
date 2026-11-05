import json
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView, DeleteView, DetailView, FormView, ListView, UpdateView,
)

from .forms import ProjectForm, TaskForm
from .models import (
    DONE_STATUS, IN_PROGRESS_STATUS, Priority, Project, Task, TaskAttachment, TaskStatus,
)


# ======================= РЕГИСТРАЦИЯ =======================

class RegisterView(FormView):
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('tasks:project_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('tasks:project_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


# ======================= ПРОЕКТЫ (CRUD) =======================

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'tasks/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).annotate(task_count=Count('tasks'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projects = list(context['projects'])
        all_tasks = Task.objects.filter(project__user=self.request.user)
        done_tasks = all_tasks.filter(status__name=DONE_STATUS)
        total = all_tasks.count()
        done = done_tasks.count()

        # Выполненные задачи по проектам одним запросом
        done_by_project = dict(
            done_tasks.values_list('project_id').annotate(c=Count('id')).values_list('project_id', 'c')
        )

        completed_projects = 0
        projects_progress = []
        for p in projects:
            if p.task_count:
                d = done_by_project.get(p.pk, 0)
                if d == p.task_count:
                    completed_projects += 1
                projects_progress.append({'title': p.title, 'pct': round(d / p.task_count * 100)})
        projects_progress.sort(key=lambda x: -x['pct'])

        context['analytics'] = {
            'done': done,
            'total': total,
            'open': total - done,
            'rate': round(done / total * 100) if total else 0,
            'projects_count': len(projects),
            'completed_projects': completed_projects,
        }

        today = timezone.localdate()
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        week_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            week_data.append({
                'd': day_names[d.weekday()],
                'v': done_tasks.filter(updated_at__date=d).count(),
            })
        week_max = max((w['v'] for w in week_data), default=1) or 1
        for w in week_data:
            w['bar_h'] = max(round(w['v'] / week_max * 100), 4)
        context['week_data'] = week_data
        context['week_total'] = sum(w['v'] for w in week_data)
        context['projects_progress'] = projects_progress[:4]
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'tasks/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        statuses = list(TaskStatus.objects.all())
        tasks = list(
            self.object.tasks
            .select_related('status', 'priority')
            .annotate(attachment_count=Count('attachments'))
        )
        context['statuses'] = statuses
        context['priorities'] = Priority.objects.all()
        context['tasks'] = tasks
        context['columns'] = [
            {'status': s, 'tasks': [t for t in tasks if t.status_id == s.id]} for s in statuses
        ]
        context['in_progress_count'] = sum(1 for t in tasks if t.status.name == IN_PROGRESS_STATUS)
        context['completed_count'] = sum(1 for t in tasks if t.status.name == DONE_STATUS)
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'tasks/project_form.html'
    success_url = reverse_lazy('tasks:project_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'tasks/project_form.html'
    success_url = reverse_lazy('tasks:project_list')

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'tasks/project_confirm_delete.html'
    success_url = reverse_lazy('tasks:project_list')

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)


# ======================= ЗАДАЧИ (CRUD, обычные формы) =======================

class TaskFormContextMixin:
    """Справочники для выпадающих списков в task_form.html."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuses'] = TaskStatus.objects.all()
        context['priorities'] = Priority.objects.all()
        context['project'] = self.get_project()
        return context


class TaskCreateView(LoginRequiredMixin, TaskFormContextMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.project = get_object_or_404(Project, pk=kwargs['project_pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_project(self):
        return self.project

    def form_valid(self, form):
        form.instance.project = self.project
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('tasks:project_detail', kwargs={'pk': self.project.pk})


class TaskUpdateView(LoginRequiredMixin, TaskFormContextMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_queryset(self):
        return Task.objects.filter(project__user=self.request.user)

    def get_project(self):
        return self.object.project

    def get_success_url(self):
        return reverse_lazy('tasks:project_detail', kwargs={'pk': self.object.project.pk})


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'

    def get_queryset(self):
        return Task.objects.filter(project__user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('tasks:project_detail', kwargs={'pk': self.object.project.pk})


# ======================= AJAX (модальное окно, канбан) =======================
# CSRF-защита включена: фронтенд передаёт заголовок X-CSRFToken.

def _json_body(request):
    try:
        data = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        raise ValueError('Некорректный JSON')
    if not isinstance(data, dict):
        raise ValueError('Ожидается JSON-объект')
    return data


def _clean_task_fields(data, current=None):
    """Проверяет и нормализует поля задачи из JSON. Бросает ValueError с понятным текстом."""
    title = str(data.get('title', current.title if current else '')).strip()
    if not title:
        raise ValueError('Укажите название задачи')
    if len(title) > 200:
        raise ValueError('Название не длиннее 200 символов')

    status_id = data.get('status_id', current.status_id if current else 1)
    priority_id = data.get('priority_id', current.priority_id if current else 2)
    if not TaskStatus.objects.filter(pk=status_id).exists():
        raise ValueError('Неизвестный статус')
    if not Priority.objects.filter(pk=priority_id).exists():
        raise ValueError('Неизвестный приоритет')

    deadline = data.get('deadline') or None
    if deadline is not None:
        try:
            deadline = date.fromisoformat(str(deadline))
        except ValueError:
            raise ValueError('Дедлайн должен быть датой в формате ГГГГ-ММ-ДД')

    description = data.get('description', current.description if current else '')
    return {
        'title': title,
        'description': str(description or ''),
        'deadline': deadline,
        'status_id': status_id,
        'priority_id': priority_id,
    }


@login_required
@require_http_methods(['POST'])
def ajax_create_task(request):
    try:
        data = _json_body(request)
        project = get_object_or_404(Project, pk=data.get('project_id'), user=request.user)
        task = Task.objects.create(project=project, **_clean_task_fields(data))
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'ok', 'task_id': task.id})


@login_required
@require_http_methods(['POST'])
def ajax_update_task(request, pk):
    task = get_object_or_404(Task, pk=pk, project__user=request.user)
    try:
        fields = _clean_task_fields(_json_body(request), current=task)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    for key, value in fields.items():
        setattr(task, key, value)
    task.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['GET'])
def ajax_get_task(request, pk):
    task = get_object_or_404(Task, pk=pk, project__user=request.user)
    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'description': task.description or '',
        'deadline': task.deadline.isoformat() if task.deadline else '',
        'priority_id': task.priority_id,
        'status_id': task.status_id,
        'attachments': [
            {'id': a.id, 'name': a.original_name, 'size': a.size, 'url': a.file.url}
            for a in task.attachments.all()
        ],
    })


@login_required
@require_http_methods(['POST'])
def ajax_update_status(request, pk):
    """Смена статуса при перетаскивании карточки."""
    task = get_object_or_404(Task, pk=pk, project__user=request.user)
    try:
        status_id = _json_body(request).get('status_id')
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    status = TaskStatus.objects.filter(pk=status_id).first() if status_id else None
    if status is None:
        return JsonResponse({'status': 'error', 'message': 'Неизвестный статус'}, status=400)
    task.status = status
    task.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['DELETE', 'POST'])
def ajax_delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, project__user=request.user)
    for attachment in task.attachments.all():
        attachment.file.delete(save=False)
    task.delete()
    return JsonResponse({'status': 'ok'})


# ---- Вложения ----

@login_required
@require_http_methods(['POST'])
def ajax_upload_attachment(request, pk):
    task = get_object_or_404(Task, pk=pk, project__user=request.user)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'status': 'error', 'message': 'Файл не передан'}, status=400)
    if f.size > settings.MAX_ATTACHMENT_SIZE:
        limit = settings.MAX_ATTACHMENT_SIZE // (1024 * 1024)
        return JsonResponse({'status': 'error', 'message': f'Файл больше {limit} МБ'}, status=400)
    attachment = TaskAttachment.objects.create(
        task=task, file=f, original_name=f.name[:255], size=f.size,
    )
    return JsonResponse({
        'id': attachment.id,
        'name': attachment.original_name,
        'size': attachment.size,
        'url': attachment.file.url,
    })


@login_required
@require_http_methods(['DELETE', 'POST'])
def ajax_delete_attachment(request, pk):
    attachment = get_object_or_404(TaskAttachment, pk=pk, task__project__user=request.user)
    attachment.file.delete(save=False)
    attachment.delete()
    return JsonResponse({'status': 'ok'})


# ======================= ФИЛЬТРАЦИЯ КАНБАН-ДОСКИ =======================

@login_required
@require_http_methods(['GET'])
def filter_tasks(request, project_pk):
    """Возвращает JSON {status_id: html карточек} с учётом фильтров."""
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    tasks = (
        project.tasks.select_related('status', 'priority')
        .annotate(attachment_count=Count('attachments'))
    )

    priority_id = request.GET.get('priority')
    if priority_id and priority_id.isdigit():
        tasks = tasks.filter(priority_id=priority_id)
    if request.GET.get('overdue') == 'true':
        tasks = tasks.filter(deadline__lt=timezone.localdate()).exclude(status__name=DONE_STATUS)

    result = {}
    for status in TaskStatus.objects.all():
        status_tasks = [t for t in tasks if t.status_id == status.id]
        result[str(status.id)] = {
            'count': len(status_tasks),
            'html': render_to_string(
                'tasks/partials/task_cards.html', {'tasks': status_tasks}, request=request,
            ),
        }
    return JsonResponse(result)


# ======================= ЭКСПОРТ / ИМПОРТ JSON =======================

@login_required
@require_http_methods(['GET'])
def export_tasks_json(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    data = list(project.tasks.values(
        'title', 'description', 'deadline', 'status__name', 'priority__name',
    ))
    for task in data:
        if task['deadline']:
            task['deadline'] = task['deadline'].isoformat()
    response = JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="tasks_{project_pk}.json"'
    return response


@login_required
@require_http_methods(['POST'])
def import_tasks_json(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, user=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Файл не является корректным JSON')
    if not isinstance(data, list):
        return HttpResponseBadRequest('Ожидается список задач')

    created = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        status_name = item.get('status__name')
        priority_name = item.get('priority__name')
        title = str(item.get('title') or '').strip()
        if not status_name or not priority_name or not title:
            continue
        status, _ = TaskStatus.objects.get_or_create(name=status_name)
        priority, _ = Priority.objects.get_or_create(name=priority_name)
        try:
            deadline = date.fromisoformat(item["deadline"]) if item.get('deadline') else None
        except (ValueError, TypeError):
            deadline = None
        Task.objects.create(
            project=project,
            title=title[:200],
            description=str(item.get('description') or ''),
            deadline=deadline,
            status=status,
            priority=priority,
        )
        created += 1
    return JsonResponse({'status': 'ok', 'created': created})
