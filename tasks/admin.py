from django.contrib import admin

from .models import Comment, Priority, Project, Task, TaskAttachment, TaskStatus


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('title', 'description')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'deadline')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')


admin.site.register(TaskStatus)
admin.site.register(Priority)
admin.site.register(TaskAttachment)
admin.site.register(Comment)
