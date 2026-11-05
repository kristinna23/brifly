from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Priority, Project, Task, TaskStatus

DEMO_USER = 'demo'
DEMO_PASSWORD = 'demo12345'


class Command(BaseCommand):
    help = 'Создаёт демо-пользователя demo / demo12345 с готовыми проектами и задачами.'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username=DEMO_USER)
        if not created and user.projects.exists():
            self.stdout.write('Демо-данные уже есть — пропускаю.')
            return
        user.set_password(DEMO_PASSWORD)
        user.save()

        st = {s.name: s for s in TaskStatus.objects.all()}
        pr = {p.name: p for p in Priority.objects.all()}
        today = timezone.localdate()
        d = lambda n: today + timedelta(days=n)

        data = {
            ('Редизайн сайта', 'Новый лендинг и обновлённая дизайн-система для маркетингового сайта.'): [
                ('Собрать референсы', 'Подборка из 10 сайтов конкурентов', 'Готова', 'Низкий', d(-6), 6),
                ('Утвердить палитру и шрифты', '', 'Готова', 'Средний', d(-4), 4),
                ('Макет главной страницы', 'Desktop + mobile в Figma', 'Готова', 'Высокий', d(-2), 3),
                ('Вёрстка шапки и подвала', 'Адаптивная, с тёмной темой', 'В работе', 'Высокий', d(2), None),
                ('Подключить форму обратной связи', 'Отправка на почту', 'В работе', 'Средний', d(5), None),
                ('Проверить доступность', 'Контраст, клавиатура, aria', 'Новая', 'Средний', d(9), None),
                ('Исправить баги вёрстки', 'Список от тестировщика', 'Новая', 'Высокий', d(-1), None),
            ],
            ('Мобильное приложение', 'MVP трекера привычек для iOS и Android.'): [
                ('Описать пользовательские сценарии', '', 'Готова', 'Высокий', d(-5), 5),
                ('Спроектировать API', 'REST, авторизация по токену', 'Готова', 'Высокий', d(-3), 1),
                ('Экран онбординга', '', 'В работе', 'Средний', d(3), None),
                ('Push-уведомления', 'Напоминания о привычках', 'Новая', 'Низкий', d(14), None),
            ],
            ('Подготовка к экзаменам', 'План повторения на сессию.'): [
                ('Базы данных: билеты 1–20', '', 'Готова', 'Высокий', d(-7), 2),
                ('Веб-разработка: курсовая', 'Сдать преподавателю', 'В работе', 'Высокий', d(4), None),
                ('Английский: эссе', '', 'Новая', 'Низкий', None, None),
            ],
        }

        for (title, description), tasks in data.items():
            project = Project.objects.create(user=user, title=title, description=description)
            for t_title, t_desc, status, prio, deadline, done_days_ago in tasks:
                task = Task.objects.create(
                    project=project, title=t_title, description=t_desc, deadline=deadline,
                    status=st[status], priority=pr[prio],
                )
                if done_days_ago is not None:
                    # updated_at — это дата закрытия: нужна для графика «Выполнено за неделю»
                    Task.objects.filter(pk=task.pk).update(
                        updated_at=timezone.now() - timedelta(days=min(done_days_ago, 6)),
                    )
        self.stdout.write(self.style.SUCCESS(f'Готово. Логин: {DEMO_USER}  Пароль: {DEMO_PASSWORD}'))
