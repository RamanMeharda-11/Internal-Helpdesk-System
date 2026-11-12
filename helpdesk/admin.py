from django.contrib import admin
from .models import Department, EmployeeProfile, Ticket, TicketComment, Task, Notification, ActivityLog

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display=('id','title','status','priority','created_by','assigned_to','created_at')
    list_filter=('status','priority','department')
    search_fields=('title','description','created_by__username','assigned_to__username')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display=('title','assigned_to','status','priority','due_date')
    list_filter=('status','priority')
    search_fields=('title','assigned_to__username')

admin.site.register((Department,EmployeeProfile,TicketComment,Notification,ActivityLog))
