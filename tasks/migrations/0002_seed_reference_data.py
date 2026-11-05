from django.db import migrations

# id фиксированы: views.py использует status_id=1 («Новая») и priority_id=2 («Средний») по умолчанию
STATUSES = [(1, 'Новая'), (2, 'В работе'), (3, 'Готова')]
PRIORITIES = [(1, 'Низкий'), (2, 'Средний'), (3, 'Высокий')]


def seed(apps, schema_editor):
    TaskStatus = apps.get_model('tasks', 'TaskStatus')
    Priority = apps.get_model('tasks', 'Priority')
    for pk, name in STATUSES:
        TaskStatus.objects.update_or_create(pk=pk, defaults={'name': name})
    for pk, name in PRIORITIES:
        Priority.objects.update_or_create(pk=pk, defaults={'name': name})


class Migration(migrations.Migration):
    dependencies = [('tasks', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
