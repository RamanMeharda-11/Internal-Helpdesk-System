from django.conf import settings
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name


class EmployeeProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        SUPPORT = 'support', 'Support staff'
        EMPLOYEE = 'employee', 'Employee'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee_profile')
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=30, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    def __str__(self): return self.user.get_full_name() or self.user.username


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'Open', 'Open'
        IN_PROGRESS = 'In Progress', 'In Progress'
        PENDING = 'Pending', 'Pending'
        RESOLVED = 'Resolved', 'Resolved'
        CLOSED = 'Closed', 'Closed'
    class Priority(models.TextChoices):
        LOW = 'Low', 'Low'
        MEDIUM = 'Medium', 'Medium'
        HIGH = 'High', 'High'
        URGENT = 'Urgent', 'Urgent'
    title = models.CharField(max_length=180)
    description = models.TextField()
    category = models.CharField(max_length=80, default='General Support')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    attachment = models.FileField(upload_to='ticket_attachments/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f'HD-{self.pk:04d} {self.title}'


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'To Do', 'To Do'
        IN_PROGRESS = 'In Progress', 'In Progress'
        REVIEW = 'Under Review', 'Under Review'
        COMPLETED = 'Completed', 'Completed'
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='helpdesk_tasks')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_helpdesk_tasks')
    priority = models.CharField(max_length=10, choices=Ticket.Priority.choices, default=Ticket.Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def overdue(self): return bool(self.due_date and self.due_date < timezone.localdate() and self.status != self.Status.COMPLETED)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='helpdesk_notifications')
    message = models.CharField(max_length=240)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    message = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)
