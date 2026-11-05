import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import shutil
import tempfile

from .models import Priority, Project, Task, TaskStatus

TEST_MEDIA = tempfile.mkdtemp()


def make_task(project, title='Задача', status='Новая', priority='Средний', deadline=None):
    return Task.objects.create(
        project=project, title=title, deadline=deadline,
        status=TaskStatus.objects.get(name=status), priority=Priority.objects.get(name=priority),
    )


class BaseCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alex', password='pass12345!')
        self.other = User.objects.create_user('bob', password='pass12345!')
        self.project = Project.objects.create(user=self.user, title='Мой проект')
        self.client.login(username='alex', password='pass12345!')

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')


class ReferenceDataTests(TestCase):
    def test_seeded_by_migration(self):
        self.assertEqual(
            list(TaskStatus.objects.values_list('id', 'name')),
            [(1, 'Новая'), (2, 'В работе'), (3, 'Готова')],
        )
        self.assertEqual(
            list(Priority.objects.values_list('id', 'name')),
            [(1, 'Низкий'), (2, 'Средний'), (3, 'Высокий')],
        )


class AuthTests(TestCase):
    def test_pages_require_login(self):
        r = self.client.get(reverse('tasks:project_list'))
        self.assertRedirects(r, '/login/?next=/')

    def test_register_logs_in(self):
        r = self.client.post(reverse('tasks:register'), {
            'username': 'newuser', 'password1': 'Str0ng-pass!', 'password2': 'Str0ng-pass!',
        })
        self.assertRedirects(r, reverse('tasks:project_list'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertEqual(self.client.get(reverse('tasks:project_list')).status_code, 200)

    def test_register_shows_errors(self):
        r = self.client.post(reverse('tasks:register'), {
            'username': 'u', 'password1': 'a', 'password2': 'b',
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)

    def test_login_and_logout(self):
        User.objects.create_user('carl', password='pass12345!')
        r = self.client.post(reverse('login'), {'username': 'carl', 'password': 'pass12345!'})
        self.assertRedirects(r, reverse('tasks:project_list'))
        r = self.client.post(reverse('logout'))
        self.assertRedirects(r, reverse('login'))


class ProjectTests(BaseCase):
    def test_list_and_analytics(self):
        make_task(self.project, status='Готова')
        make_task(self.project, status='В работе')
        r = self.client.get(reverse('tasks:project_list'))
        self.assertEqual(r.status_code, 200)
        a = r.context['analytics']
        self.assertEqual((a['done'], a['total'], a['open'], a['rate']), (1, 2, 1, 50))
        self.assertEqual(a['projects_count'], 1)
        self.assertEqual(len(r.context['week_data']), 7)
        self.assertEqual(r.context['week_total'], 1)

    def test_completed_project_counted(self):
        make_task(self.project, status='Готова')
        r = self.client.get(reverse('tasks:project_list'))
        self.assertEqual(r.context['analytics']['completed_projects'], 1)

    def test_create_update_delete(self):
        r = self.client.post(reverse('tasks:project_create'), {'title': 'Новый', 'description': 'd'})
        self.assertRedirects(r, reverse('tasks:project_list'))
        p = Project.objects.get(title='Новый')
        self.assertEqual(p.user, self.user)
        self.client.post(reverse('tasks:project_update', args=[p.pk]), {'title': 'Правка', 'description': ''})
        p.refresh_from_db()
        self.assertEqual(p.title, 'Правка')
        self.client.post(reverse('tasks:project_delete', args=[p.pk]))
        self.assertFalse(Project.objects.filter(pk=p.pk).exists())

    def test_create_requires_title(self):
        r = self.client.post(reverse('tasks:project_create'), {'title': '', 'description': ''})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'field-error')

    def test_detail_columns(self):
        make_task(self.project, 'A', 'Новая')
        make_task(self.project, 'B', 'Готова')
        r = self.client.get(reverse('tasks:project_detail', args=[self.project.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([len(c['tasks']) for c in r.context['columns']], [1, 0, 1])
        self.assertEqual(r.context['completed_count'], 1)

    def test_other_users_project_is_hidden(self):
        foreign = Project.objects.create(user=self.other, title='Чужой')
        for name in ('project_detail', 'project_update', 'project_delete'):
            self.assertEqual(self.client.get(reverse(f'tasks:{name}', args=[foreign.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('tasks:project_list')), 'Чужой')


class TaskFormViewsTests(BaseCase):
    def test_create_form_renders_and_saves(self):
        url = reverse('tasks:task_create', args=[self.project.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {
            'title': 'Из формы', 'description': '', 'deadline': '2030-01-01', 'status': 1, 'priority': 3,
        })
        self.assertRedirects(r, reverse('tasks:project_detail', args=[self.project.pk]))
        t = Task.objects.get(title='Из формы')
        self.assertEqual((t.priority.name, t.project), ('Высокий', self.project))

    def test_update_form_renders_with_selected_values(self):
        t = make_task(self.project, 'T', 'В работе', 'Высокий')
        r = self.client.get(reverse('tasks:task_update', args=[t.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '<option value="2" selected>В работе</option>', html=True)
        self.assertContains(r, '<option value="3" selected>Высокий</option>', html=True)

    def test_delete_view(self):
        t = make_task(self.project)
        self.assertEqual(self.client.get(reverse('tasks:task_delete', args=[t.pk])).status_code, 200)
        self.client.post(reverse('tasks:task_delete', args=[t.pk]))
        self.assertFalse(Task.objects.filter(pk=t.pk).exists())

    def test_cannot_create_task_in_foreign_project(self):
        foreign = Project.objects.create(user=self.other, title='X')
        r = self.client.get(reverse('tasks:task_create', args=[foreign.pk]))
        self.assertEqual(r.status_code, 404)


class AjaxTests(BaseCase):
    def test_create_task(self):
        r = self.post_json(reverse('tasks:ajax_create_task'), {
            'project_id': self.project.pk, 'title': 'Ajax', 'description': 'd',
            'deadline': '2030-05-01', 'priority_id': 3, 'status_id': 2,
        })
        self.assertEqual(r.status_code, 200)
        t = Task.objects.get(pk=r.json()['task_id'])
        self.assertEqual((t.title, t.status_id, t.priority_id, str(t.deadline)), ('Ajax', 2, 3, '2030-05-01'))

    def test_create_validation(self):
        url = reverse('tasks:ajax_create_task')
        base = {'project_id': self.project.pk, 'title': 'ok'}
        self.assertEqual(self.post_json(url, {**base, 'title': '  '}).status_code, 400)
        self.assertEqual(self.post_json(url, {**base, 'status_id': 99}).status_code, 400)
        self.assertEqual(self.post_json(url, {**base, 'priority_id': 99}).status_code, 400)
        self.assertEqual(self.post_json(url, {**base, 'deadline': 'вчера'}).status_code, 400)
        self.assertEqual(self.client.post(url, 'not json', content_type='application/json').status_code, 400)
        self.assertEqual(Task.objects.count(), 0)

    def test_create_in_foreign_project_forbidden(self):
        foreign = Project.objects.create(user=self.other, title='X')
        r = self.post_json(reverse('tasks:ajax_create_task'), {'project_id': foreign.pk, 'title': 'hack'})
        self.assertEqual(r.status_code, 404)

    def test_get_update_delete(self):
        t = make_task(self.project, 'Old')
        g = self.client.get(reverse('tasks:ajax_get_task', args=[t.pk])).json()
        self.assertEqual(g['title'], 'Old')
        r = self.post_json(reverse('tasks:ajax_update_task', args=[t.pk]), {'title': 'New', 'priority_id': 1})
        self.assertEqual(r.json()['status'], 'ok')
        t.refresh_from_db()
        self.assertEqual((t.title, t.priority_id), ('New', 1))
        r = self.client.delete(reverse('tasks:ajax_delete_task', args=[t.pk]))
        self.assertEqual(r.json()['status'], 'ok')
        self.assertFalse(Task.objects.filter(pk=t.pk).exists())

    def test_update_status_on_drag(self):
        t = make_task(self.project)
        url = reverse('tasks:ajax_update_status', args=[t.pk])
        self.assertEqual(self.post_json(url, {'status_id': 3}).status_code, 200)
        t.refresh_from_db()
        self.assertEqual(t.status.name, 'Готова')
        self.assertEqual(self.post_json(url, {'status_id': 42}).status_code, 400)

    def test_foreign_task_is_protected(self):
        foreign = Project.objects.create(user=self.other, title='X')
        t = make_task(foreign)
        self.assertEqual(self.client.get(reverse('tasks:ajax_get_task', args=[t.pk])).status_code, 404)
        self.assertEqual(self.post_json(reverse('tasks:ajax_update_task', args=[t.pk]), {'title': 'z'}).status_code, 404)
        self.assertEqual(self.client.delete(reverse('tasks:ajax_delete_task', args=[t.pk])).status_code, 404)

    def test_csrf_is_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.login(username='alex', password='pass12345!')
        r = c.post(reverse('tasks:ajax_create_task'), '{}', content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_anonymous_redirected(self):
        self.client.logout()
        r = self.client.post(reverse('tasks:ajax_create_task'), '{}', content_type='application/json')
        self.assertEqual(r.status_code, 302)

    def test_wrong_method(self):
        self.assertEqual(self.client.get(reverse('tasks:ajax_create_task')).status_code, 405)


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class AttachmentTests(BaseCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    def test_upload_list_delete(self):
        t = make_task(self.project)
        f = SimpleUploadedFile('note.txt', b'hello')
        r = self.client.post(reverse('tasks:ajax_upload_attachment', args=[t.pk]), {'file': f})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual((data['name'], data['size']), ('note.txt', 5))
        got = self.client.get(reverse('tasks:ajax_get_task', args=[t.pk])).json()
        self.assertEqual(len(got['attachments']), 1)
        r = self.client.delete(reverse('tasks:ajax_delete_attachment', args=[data['id']]))
        self.assertEqual(r.json()['status'], 'ok')
        self.assertEqual(t.attachments.count(), 0)

    def test_upload_without_file(self):
        t = make_task(self.project)
        self.assertEqual(self.client.post(reverse('tasks:ajax_upload_attachment', args=[t.pk])).status_code, 400)

    @override_settings(MAX_ATTACHMENT_SIZE=3)
    def test_upload_too_large(self):
        t = make_task(self.project)
        f = SimpleUploadedFile('big.bin', b'12345')
        r = self.client.post(reverse('tasks:ajax_upload_attachment', args=[t.pk]), {'file': f})
        self.assertEqual(r.status_code, 400)

    def test_cannot_delete_foreign_attachment(self):
        foreign = Project.objects.create(user=self.other, title='X')
        t = make_task(foreign)
        from .models import TaskAttachment
        a = TaskAttachment.objects.create(task=t, file=SimpleUploadedFile('a.txt', b'x'), original_name='a.txt', size=1)
        self.assertEqual(self.client.delete(reverse('tasks:ajax_delete_attachment', args=[a.pk])).status_code, 404)


class FilterTests(BaseCase):
    def setUp(self):
        super().setUp()
        yesterday = timezone.localdate() - timedelta(days=1)
        make_task(self.project, 'Горит', 'Новая', 'Высокий', deadline=yesterday)
        make_task(self.project, 'Спокойно', 'Новая', 'Низкий')
        make_task(self.project, 'Сделано давно', 'Готова', 'Высокий', deadline=yesterday)
        self.url = reverse('tasks:filter_tasks', args=[self.project.pk])

    def test_no_filter(self):
        data = self.client.get(self.url).json()
        self.assertEqual([data[k]['count'] for k in ('1', '2', '3')], [2, 0, 1])

    def test_priority_filter(self):
        data = self.client.get(self.url, {'priority': 3}).json()
        self.assertEqual([data[k]['count'] for k in ('1', '2', '3')], [1, 0, 1])
        self.assertIn('Горит', data['1']['html'])

    def test_overdue_filter_ignores_done_tasks(self):
        data = self.client.get(self.url, {'overdue': 'true'}).json()
        self.assertEqual([data[k]['count'] for k in ('1', '2', '3')], [1, 0, 0])
        self.assertNotIn('Спокойно', data['1']['html'])

    def test_is_overdue_property(self):
        t = Task.objects.get(title='Горит')
        self.assertTrue(t.is_overdue)
        self.assertFalse(Task.objects.get(title='Сделано давно').is_overdue)
        self.assertFalse(Task.objects.get(title='Спокойно').is_overdue)


class ExportImportTests(BaseCase):
    def test_export(self):
        make_task(self.project, 'Экспорт', deadline=timezone.localdate())
        r = self.client.get(reverse('tasks:export_tasks', args=[self.project.pk]))
        self.assertIn('attachment', r['Content-Disposition'])
        data = json.loads(r.content)
        self.assertEqual(data[0]['title'], 'Экспорт')
        self.assertEqual(data[0]['status__name'], 'Новая')

    def test_roundtrip(self):
        make_task(self.project, 'Туда-сюда', 'В работе', 'Высокий', deadline=timezone.localdate())
        payload = self.client.get(reverse('tasks:export_tasks', args=[self.project.pk])).content
        target = Project.objects.create(user=self.user, title='Копия')
        r = self.client.post(reverse('tasks:import_tasks', args=[target.pk]), payload, content_type='application/json')
        self.assertEqual(r.json()['created'], 1)
        t = target.tasks.get()
        self.assertEqual((t.title, t.status.name, t.priority.name), ('Туда-сюда', 'В работе', 'Высокий'))

    def test_import_skips_bad_items_and_rejects_bad_json(self):
        url = reverse('tasks:import_tasks', args=[self.project.pk])
        good = {'title': 'ok', 'status__name': 'Новая', 'priority__name': 'Низкий', 'deadline': 'мусор'}
        bad = [{'title': 'no status'}, 'строка', {'title': '', 'status__name': 'Новая', 'priority__name': 'Низкий'}]
        r = self.client.post(url, json.dumps([good, *bad]), content_type='application/json')
        self.assertEqual(r.json()['created'], 1)
        self.assertIsNone(self.project.tasks.get().deadline)
        self.assertEqual(self.client.post(url, 'oops', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(url, '{"a": 1}', content_type='application/json').status_code, 400)
