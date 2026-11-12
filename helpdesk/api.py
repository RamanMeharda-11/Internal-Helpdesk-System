from rest_framework import viewsets, permissions, filters, decorators, response
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import Ticket, Task, EmployeeProfile, Notification, TicketComment, ActivityLog
from .serializers import TicketSerializer, TaskSerializer, EmployeeSerializer, NotificationSerializer

def role(user):
    if user.is_superuser: return 'admin'
    try: return user.employee_profile.role
    except EmployeeProfile.DoesNotExist: return 'employee'

class TicketViewSet(viewsets.ModelViewSet):
    queryset=Ticket.objects.all()
    serializer_class=TicketSerializer
    permission_classes=[permissions.IsAuthenticated]
    filter_backends=[filters.SearchFilter,filters.OrderingFilter]
    search_fields=['title','description','category']
    ordering_fields=['created_at','priority','status']
    def get_queryset(self):
        qs=Ticket.objects.select_related('created_by','assigned_to').prefetch_related('comments')
        if role(self.request.user)=='employee': qs=qs.filter(created_by=self.request.user)
        elif role(self.request.user)=='support': qs=qs.filter(assigned_to=self.request.user)
        for field in ('status','priority'):
            value=self.request.query_params.get(field)
            if value: qs=qs.filter(**{field+'__iexact':value})
        assignee=self.request.query_params.get('assigned_to')
        if assignee:
            if not assignee.isdigit(): raise ValidationError({'assigned_to':'Expected a user ID.'})
            qs=qs.filter(assigned_to_id=int(assignee))
        return qs
    def perform_create(self,serializer): serializer.save(created_by=self.request.user)
    def perform_update(self,serializer):
        ticket=self.get_object()
        if role(self.request.user) not in ('admin','support'): raise PermissionDenied('Only support staff can update ticket fields.')
        serializer.save()
    def perform_destroy(self,instance):
        if role(self.request.user)!='admin': raise PermissionDenied('Only admins can delete tickets.')
        instance.delete()
    @decorators.action(detail=True,methods=['patch'])
    def assign(self,request,pk=None):
        if role(request.user)!='admin': raise PermissionDenied('Only admins can assign tickets.')
        ticket=self.get_object(); assignee_id=request.data.get('assigned_to')
        if not assignee_id: raise ValidationError({'assigned_to':'This field is required.'})
        assignee=get_object_or_404(User,pk=assignee_id,is_active=True)
        ticket.assigned_to=assignee; ticket.save(update_fields=['assigned_to','updated_at'])
        Notification.objects.create(user=assignee,message=f'Ticket HD-{ticket.pk:04d} assigned to you')
        ActivityLog.objects.create(user=request.user,message=f'assigned ticket HD-{ticket.pk:04d} to {assignee.username}')
        return response.Response(self.get_serializer(ticket).data)
    @decorators.action(detail=True,methods=['patch'])
    def status(self,request,pk=None):
        if role(request.user) not in ('admin','support'): raise PermissionDenied()
        ticket=self.get_object(); value=request.data.get('status')
        if value not in Ticket.Status.values: raise ValidationError({'status':'Invalid status.'})
        old=ticket.status; ticket.status=value; ticket.save(update_fields=['status','updated_at'])
        if old != value: Notification.objects.create(user=ticket.created_by,message=f'Ticket HD-{ticket.pk:04d} status changed to {value}')
        return response.Response(self.get_serializer(ticket).data)
    @decorators.action(detail=True,methods=['post'])
    def comment(self,request,pk=None):
        ticket=self.get_object(); body=str(request.data.get('body','')).strip()
        if not body: raise ValidationError({'body':'This field is required.'})
        comment=TicketComment.objects.create(ticket=ticket,author=request.user,body=body)
        recipient=ticket.created_by if ticket.created_by_id != request.user.id else ticket.assigned_to
        if recipient and recipient.id != request.user.id: Notification.objects.create(user=recipient,message=f'New comment on ticket HD-{ticket.pk:04d}')
        return response.Response({'id':comment.pk,'body':comment.body,'created_at':comment.created_at},status=201)

class TaskViewSet(viewsets.ModelViewSet):
    queryset=Task.objects.all()
    serializer_class=TaskSerializer; permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        qs=Task.objects.select_related('assigned_to','created_by')
        return qs if role(self.request.user)=='admin' else qs.filter(assigned_to=self.request.user)
    def perform_create(self,serializer):
        if role(self.request.user)!='admin': raise PermissionDenied()
        serializer.save(created_by=self.request.user)
    def perform_update(self,serializer):
        task=self.get_object()
        if role(self.request.user)!='admin' and task.assigned_to_id!=self.request.user.id: raise PermissionDenied()
        if role(self.request.user)!='admin' and set(self.request.data.keys())-{'status'}: raise PermissionDenied('Employees can only update task status.')
        old=task.status; task=serializer.save()
        if old != task.status and task.status=='Completed': Notification.objects.create(user=task.created_by,message=f'Task completed: {task.title}')
    def perform_destroy(self,instance):
        if role(self.request.user)!='admin': raise PermissionDenied()
        instance.delete()

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset=EmployeeProfile.objects.select_related('user','department').all()
    serializer_class=EmployeeSerializer
    permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self):
        if role(self.request.user)!='admin': raise PermissionDenied()
        return super().get_queryset()
    def perform_destroy(self,instance):
        instance.user.is_active=False
        instance.user.save(update_fields=['is_active'])

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=Notification.objects.all()
    serializer_class=NotificationSerializer
    permission_classes=[permissions.IsAuthenticated]
    def get_queryset(self): return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    @decorators.action(detail=True,methods=['post'])
    def mark_read(self,request,pk=None):
        item=self.get_object(); item.read=True; item.save(update_fields=['read'])
        return response.Response(self.get_serializer(item).data)
