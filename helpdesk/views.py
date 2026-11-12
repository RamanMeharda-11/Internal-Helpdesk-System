from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Ticket, TicketComment, Task, EmployeeProfile, Department, Notification, ActivityLog
from .forms import TicketCreateForm, EmployeeForm, EmployeeProfileForm

def _role(user):
    if user.is_superuser: return 'admin'
    try: return user.employee_profile.role
    except EmployeeProfile.DoesNotExist: return 'employee'

def sign_in(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user); return redirect('dashboard')
        messages.error(request, 'Email or password was not recognized.')
    return render(request, 'auth.html', {'register': False})

def register(request):
    if not request.user.is_authenticated or _role(request.user) != 'admin':
        messages.error(request, 'Only admins can add employee accounts.'); return redirect('login')
    if request.method == 'POST':
        username=request.POST.get('username','').strip(); email=request.POST.get('email','').strip(); password=request.POST.get('password','')
        valid_roles={choice for choice,label in EmployeeProfile.Role.choices}
        if username and email and len(password) >= 8 and request.POST.get('role','employee') in valid_roles and not User.objects.filter(username=username).exists():
            user=User.objects.create_user(username=username,email=email,password=password,first_name=request.POST.get('first_name',''))
            EmployeeProfile.objects.create(user=user, role=request.POST.get('role','employee'))
            messages.success(request, 'Employee account created.'); return redirect('dashboard')
        messages.error(request, 'Provide a unique username, email and password of at least 8 characters.')
    return render(request, 'auth.html', {'register': True})

@login_required
def dashboard(request):
    role=_role(request.user); tickets=Ticket.objects.select_related('created_by','assigned_to')
    tasks=Task.objects.select_related('assigned_to')
    if role == 'employee': tickets=tickets.filter(created_by=request.user); tasks=tasks.filter(assigned_to=request.user)
    elif role == 'support': tickets=tickets.filter(Q(assigned_to=request.user)|Q(assigned_to__isnull=True))
    q=request.GET.get('q','').strip()
    if q: tickets=tickets.filter(Q(title__icontains=q)|Q(description__icontains=q)|Q(category__icontains=q))
    status_counts=list(tickets.values('status').annotate(total=Count('id')).order_by('status'))
    priority_counts=list(tickets.values('priority').annotate(total=Count('id')).order_by('priority'))
    monthly=list(tickets.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Count('id')).order_by('month'))
    context={'role':role,'tickets':tickets.order_by('-created_at')[:8],'tasks':tasks.order_by('due_date')[:8],
      'total_tickets':tickets.count(),'open_tickets':tickets.filter(status='Open').count(),
      'pending_tickets':tickets.filter(status='Pending').count(),'resolved_tickets':tickets.filter(status='Resolved').count(),
      'total_tasks':tasks.count(),'employees':User.objects.filter(is_active=True).count(),
      'users':User.objects.filter(is_active=True).order_by('first_name'), 'departments':Department.objects.all(),
      'ticket_statuses':Ticket.Status.choices, 'task_statuses':Task.Status.choices,
      'chart_statuses':[x['status'] for x in status_counts], 'chart_status_values':[x['total'] for x in status_counts],
      'chart_priorities':[x['priority'] for x in priority_counts], 'chart_priority_values':[x['total'] for x in priority_counts],
      'chart_months':[x['month'].strftime('%b %Y') for x in monthly], 'chart_month_values':[x['total'] for x in monthly],
      'activities':ActivityLog.objects.select_related('user').order_by('-created_at')[:5], 'notifications':request.user.helpdesk_notifications.filter(read=False).count()}
    return render(request,'dashboard.html',context)

@login_required
def create_ticket(request):
    if request.method=='POST':
        form=TicketCreateForm(request.POST,request.FILES)
        if form.is_valid():
            ticket=form.save(commit=False); ticket.created_by=request.user; ticket.save()
            ActivityLog.objects.create(user=request.user,message=f'created ticket HD-{ticket.pk:04d}: {ticket.title}')
            messages.success(request,'Ticket created successfully.')
        else:
            for errors in form.errors.values():
                for error in errors: messages.error(request,error)
    return redirect('dashboard')

@login_required
@require_POST
def ticket_action(request, pk):
    ticket=get_object_or_404(Ticket,pk=pk)
    if _role(request.user)=='employee' and ticket.created_by_id!=request.user.id: return HttpResponse('Forbidden',status=403)
    if request.POST.get('action')=='comment':
        body=request.POST.get('body','').strip()
        if body:
            TicketComment.objects.create(ticket=ticket,author=request.user,body=body)
            if ticket.created_by_id != request.user.id: Notification.objects.create(user=ticket.created_by,message=f'New comment on ticket HD-{ticket.pk:04d}')
    elif _role(request.user) in ('admin','support'):
        old_status=ticket.status
        if request.POST.get('status') in Ticket.Status.values: ticket.status=request.POST['status']
        assigned=request.POST.get('assigned_to')
        if assigned and _role(request.user)=='admin': ticket.assigned_to=get_object_or_404(User,pk=assigned)
        ticket.save(); ActivityLog.objects.create(user=request.user,message=f'updated ticket HD-{ticket.pk:04d}')
        if old_status != ticket.status: Notification.objects.create(user=ticket.created_by,message=f'Ticket HD-{ticket.pk:04d} status changed to {ticket.status}')
        if assigned and ticket.assigned_to_id: Notification.objects.create(user=ticket.assigned_to,message=f'Ticket HD-{ticket.pk:04d} assigned to you')
    messages.success(request,'Ticket updated.'); return redirect('dashboard')

@login_required
def ticket_attachment(request,pk):
    ticket=get_object_or_404(Ticket,pk=pk)
    role=_role(request.user)
    if role=='employee' and ticket.created_by_id!=request.user.id: return HttpResponse('Forbidden',status=403)
    if role=='support' and ticket.assigned_to_id!=request.user.id: return HttpResponse('Forbidden',status=403)
    if not ticket.attachment: return HttpResponse('Attachment not found',status=404)
    return FileResponse(ticket.attachment.open('rb'),as_attachment=True,filename=ticket.attachment.name.rsplit('/',1)[-1])

@login_required
@require_POST
def create_task(request):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    assignee=get_object_or_404(User,pk=request.POST.get('assigned_to'))
    task=Task.objects.create(title=request.POST.get('title','').strip(),description=request.POST.get('description',''),assigned_to=assignee,created_by=request.user,priority=request.POST.get('priority','Medium'),due_date=request.POST.get('due_date') or None)
    if not task.title: task.delete(); messages.error(request,'Task title is required.')
    else:
        Notification.objects.create(user=assignee,message=f'New task assigned: {task.title}')
        ActivityLog.objects.create(user=request.user,message=f'assigned task {task.title} to {assignee.get_username()}')
        messages.success(request,'Task assigned.')
    return redirect('dashboard')

@login_required
@require_POST
def task_action(request,pk):
    task=get_object_or_404(Task,pk=pk)
    if task.assigned_to_id!=request.user.id and _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    old=task.status
    if request.POST.get('status') in Task.Status.values: task.status=request.POST['status']; task.save()
    if old != task.status and task.status=='Completed' and task.created_by_id != request.user.id: Notification.objects.create(user=task.created_by,message=f'Task completed: {task.title}')
    return redirect('dashboard')

@login_required
def reports_csv(request):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    import csv
    report=request.GET.get('type','tickets')
    if report not in {'tickets','tasks','employees','departments','monthly'}: report='tickets'
    response=HttpResponse(content_type='text/csv'); response['Content-Disposition']=f'attachment; filename="helpdesk-{report}.csv"'
    writer=csv.writer(response)
    if report=='tasks':
        writer.writerow(['Task','Status','Priority','Assigned to','Due date'])
        for x in Task.objects.select_related('assigned_to'): writer.writerow([x.title,x.status,x.priority,x.assigned_to.username,x.due_date or ''])
    elif report=='employees':
        writer.writerow(['Username','Name','Email','Role','Department','Active'])
        for p in EmployeeProfile.objects.select_related('user','department'): writer.writerow([p.user.username,p.user.get_full_name(),p.user.email,p.role,p.department.name if p.department else '',p.user.is_active])
    elif report=='departments':
        writer.writerow(['Department','Tickets','Open','Resolved'])
        for d in Department.objects.annotate(total=Count('ticket'),opened=Count('ticket',filter=Q(ticket__status='Open')),resolved=Count('ticket',filter=Q(ticket__status='Resolved'))): writer.writerow([d.name,d.total,d.opened,d.resolved])
    elif report=='monthly':
        writer.writerow(['Month','Tickets','Resolved'])
        for x in Ticket.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Count('id'),resolved=Count('id',filter=Q(status='Resolved'))).order_by('month'): writer.writerow([x['month'].strftime('%Y-%m'),x['total'],x['resolved']])
    else:
        writer.writerow(['Ticket','Title','Status','Priority','Created by','Assigned to','Created at'])
        for t in Ticket.objects.select_related('created_by','assigned_to'): writer.writerow([f'HD-{t.pk:04d}',t.title,t.status,t.priority,t.created_by.username,t.assigned_to.username if t.assigned_to else '',t.created_at.isoformat()])
    return response

@login_required
def reports(request):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    status_data=list(Ticket.objects.values('status').annotate(total=Count('id')).order_by('status'))
    dept_data=list(Department.objects.annotate(total=Count('ticket')).values('name','total').order_by('name'))
    monthly_data=list(Ticket.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(total=Count('id'),resolved=Count('id',filter=Q(status='Resolved'))).order_by('month'))
    return render(request,'reports.html',{'status_labels':[x['status'] for x in status_data],'status_values':[x['total'] for x in status_data],
        'dept_labels':[x['name'] for x in dept_data],'dept_values':[x['total'] for x in dept_data],
        'month_labels':[x['month'].strftime('%b %Y') for x in monthly_data], 'month_values':[x['total'] for x in monthly_data],
        'total_tickets':Ticket.objects.count(),'resolved_tickets':Ticket.objects.filter(status='Resolved').count(),
        'pending_tickets':Ticket.objects.filter(status='Pending').count(),'total_tasks':Task.objects.count(),
        'completed_tasks':Task.objects.filter(status='Completed').count(),
        'performance':Task.objects.values('assigned_to__username').annotate(total=Count('id'),completed=Count('id',filter=Q(status='Completed'))).order_by('assigned_to__username')} )

@login_required
def notifications(request):
    rows=request.user.helpdesk_notifications.order_by('-created_at')
    return render(request,'notifications.html',{'notifications_list':rows})

@login_required
@require_POST
def notification_read(request,pk):
    notification=get_object_or_404(Notification,pk=pk,user=request.user); notification.read=True; notification.save(update_fields=['read'])
    return redirect('notifications')

@login_required
def employee_list(request):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    profiles=EmployeeProfile.objects.select_related('user','department').order_by('user__first_name','user__username')
    return render(request,'employees.html',{'profiles':profiles,'departments':Department.objects.all()})

@login_required
def employee_edit(request,pk):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    profile=get_object_or_404(EmployeeProfile.objects.select_related('user'),pk=pk); employee_form=EmployeeForm(request.POST or None,instance=profile.user); profile_form=EmployeeProfileForm(request.POST or None,instance=profile)
    if request.method=='POST' and employee_form.is_valid() and profile_form.is_valid():
        employee_form.save(); profile_form.save(); messages.success(request,'Employee details updated.'); return redirect('employees')
    return render(request,'employee_edit.html',{'employee_form':employee_form,'profile_form':profile_form,'profile':profile})

@login_required
@require_POST
def employee_delete(request,pk):
    if _role(request.user)!='admin': return HttpResponse('Forbidden',status=403)
    profile=get_object_or_404(EmployeeProfile.objects.select_related('user'),pk=pk)
    if profile.user_id==request.user.id: messages.error(request,'You cannot deactivate your own account.')
    else:
        profile.user.is_active=False; profile.user.save(update_fields=['is_active']); messages.success(request,'Employee account deactivated; ticket history is preserved.')
    return redirect('employees')

def sign_out(request): logout(request); return redirect('login')
