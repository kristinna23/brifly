from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Названия справочных значений (создаются миграцией 0002)
DONE_STATUS = 'Готова'
IN_PROGRESS_STATUS = 'В работе'


class TaskStatus(models.Model):
    """Статусы задач (справочник) – аналог smallserial"""
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Статус задачи"
        verbose_name_plural = "Статусы задач"
        ordering = ['id']

    def __str__(self):
        return self.name


class Priority(models.Model):
    """Приоритеты задач (справочник) – аналог smallserial"""
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Приоритет"
        verbose_name_plural = "Приоритеты"
        ordering = ['id']

    def __str__(self):
        return self.name


class Project(models.Model):
    """Проект (пользователь → много проектов)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Task(models.Model):
    """Задача (связи с проектом, статусом, приоритетом)"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    status = models.ForeignKey(TaskStatus, on_delete=models.PROTECT, related_name='tasks')
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-deadline', '-created_at']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        """Просрочена ли задача (выполненные задачи просроченными не считаются)"""
        if not self.deadline or self.status.name == DONE_STATUS:
            return False
        return self.deadline < timezone.localdate()


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ['uploaded_at']

    def __str__(self):
        return self.original_name


class Comment(models.Model):
    """Комментарий к задаче (задача → много комментариев, пользователь → много комментариев)"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at']

    def __str__(self):
        return f"Комментарий #{self.pk} к задаче «{self.task.title}»"
