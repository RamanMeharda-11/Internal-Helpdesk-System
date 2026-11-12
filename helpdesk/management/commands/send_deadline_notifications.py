from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from helpdesk.models import Task, Notification

class Command(BaseCommand):
    help = 'Create one notification for each active task due tomorrow.'

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)
        due_tasks = Task.objects.filter(due_date=tomorrow).exclude(status=Task.Status.COMPLETED).select_related('assigned_to')
        created = 0
        for task in due_tasks:
            message = f'Task deadline tomorrow (task {task.pk}): {task.title}'
            _, was_created = Notification.objects.get_or_create(user=task.assigned_to, message=message)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f'Created {created} deadline notification(s).'))
