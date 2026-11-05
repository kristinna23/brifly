from django import forms
from .models import Project, Task, TaskStatus, Priority

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название проекта'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание (необязательно)'}),
        }

class TaskForm(forms.ModelForm):
    # Поля для статуса и приоритета будут выпадающими списками из справочников
    status = forms.ModelChoiceField(queryset=TaskStatus.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ModelChoiceField(queryset=Priority.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))
    deadline = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), required=False)

    class Meta:
        model = Task
        fields = ['title', 'description', 'deadline', 'status', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание (необязательно)'}),
        }
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'deadline': 'Дедлайн',
            'status': 'Статус',
            'priority': 'Приоритет',
        }