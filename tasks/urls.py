from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Регистрация
    path('register/', views.RegisterView.as_view(), name='register'),

    # Проекты
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('project/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('project/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('project/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('project/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Задачи (обычный CRUD)
    path('project/<int:project_pk>/task/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('task/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('task/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),

    # AJAX для модального окна (ЭТИ ФУНКЦИИ МЫ ДОБАВИМ В views.py)
    path('ajax/task/create/', views.ajax_create_task, name='ajax_create_task'),
    path('ajax/task/<int:pk>/update/', views.ajax_update_task, name='ajax_update_task'),
    path('ajax/task/<int:pk>/get/', views.ajax_get_task, name='ajax_get_task'),
    path('ajax/task/<int:pk>/update-status/', views.ajax_update_status, name='ajax_update_status'),
    path('ajax/task/<int:pk>/delete/', views.ajax_delete_task, name='ajax_delete_task'),

    # Вложения задач
    path('ajax/task/<int:pk>/attachments/', views.ajax_upload_attachment, name='ajax_upload_attachment'),
    path('ajax/attachment/<int:pk>/delete/', views.ajax_delete_attachment, name='ajax_delete_attachment'),

    # Фильтрация, экспорт, импорт
    path('project/<int:project_pk>/filter/', views.filter_tasks, name='filter_tasks'),
    path('project/<int:project_pk>/export/', views.export_tasks_json, name='export_tasks'),
    path('project/<int:project_pk>/import/', views.import_tasks_json, name='import_tasks'),

    
]