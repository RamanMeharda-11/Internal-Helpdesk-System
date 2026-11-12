from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.sign_in, name='login'),
    path('logout/', views.sign_out, name='logout'),
    path('employees/add/', views.register, name='register'),
    path('employees/', views.employee_list, name='employees'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/deactivate/', views.employee_delete, name='employee_delete'),
    path('tickets/new/', views.create_ticket, name='create_ticket'),
    path('tickets/<int:pk>/attachment/', views.ticket_attachment, name='ticket_attachment'),
    path('tickets/<int:pk>/update/', views.ticket_action, name='ticket_action'),
    path('tasks/new/', views.create_task, name='create_task'),
    path('tasks/<int:pk>/update/', views.task_action, name='task_action'),
    path('reports/tickets.csv', views.reports_csv, name='reports_csv'),
    path('reports/', views.reports, name='reports'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
]
