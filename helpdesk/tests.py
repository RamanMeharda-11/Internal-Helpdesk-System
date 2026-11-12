from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.core.management import call_command
from datetime import date, timedelta
from unittest.mock import patch
from rest_framework.test import APIClient
from .models import Department, EmployeeProfile, Ticket, TicketComment, Task, Notification

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class HelpdeskAPITests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('admin',email='admin@example.com',password='DemoPass123!')
        self.support=User.objects.create_user('support',email='support@example.com',password='DemoPass123!')
        self.employee=User.objects.create_user('staff',email='staff@example.com',password='DemoPass123!')
        EmployeeProfile.objects.create(user=self.admin,role='admin')
        EmployeeProfile.objects.create(user=self.support,role='support')
        EmployeeProfile.objects.create(user=self.employee,role='employee')
        self.own=Ticket.objects.create(title='My issue',description='network test',created_by=self.employee)
        self.other=Ticket.objects.create(title='Other issue',description='software test',created_by=self.admin)
        self.assigned=Ticket.objects.create(title='Assigned support issue',description='printer',created_by=self.employee,assigned_to=self.support)
        self.task=Task.objects.create(title='My task',assigned_to=self.employee,created_by=self.admin)
        self.client=APIClient()

    def test_unauthenticated_api_requests_are_rejected(self):
        for path in ['/api/tickets/','/api/tasks/','/api/employees/','/api/notifications/']:
            self.assertIn(self.client.get(path).status_code,(401,403))

    def test_employee_ticket_list_is_private(self):
        self.client.force_authenticate(self.employee)
        ids=[row['id'] for row in self.client.get('/api/tickets/').json()]
        self.assertEqual(set(ids),{self.own.id,self.assigned.id})
        self.assertEqual(self.client.get(f'/api/tickets/{self.other.id}/').status_code,404)

    def test_employee_can_create_ticket_with_attachment(self):
        self.client.force_authenticate(self.employee)
        upload=SimpleUploadedFile('screen.png',b'fake image bytes',content_type='image/png')
        r=self.client.post('/api/tickets/',{'title':'Upload test','description':'See attachment','attachment':upload},format='multipart')
        self.assertEqual(r.status_code,201,r.data)
        stored_name=Ticket.objects.get(pk=r.data['id']).attachment.name
        self.assertIn('screen',stored_name); self.assertTrue(stored_name.endswith('.png'))

    def test_api_rejects_unsupported_attachment(self):
        self.client.force_authenticate(self.employee)
        upload=SimpleUploadedFile('payload.exe',b'not allowed',content_type='application/octet-stream')
        r=self.client.post('/api/tickets/',{'title':'Bad file','description':'reject this','attachment':upload},format='multipart')
        self.assertEqual(r.status_code,400)

    def test_employee_cannot_update_ticket_fields_or_assign(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.patch(f'/api/tickets/{self.own.id}/',{'status':'Resolved'},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/tickets/{self.own.id}/assign/',{'assigned_to':self.admin.id},format='json').status_code,403)

    def test_admin_assigns_ticket_and_notifies_assignee(self):
        self.client.force_authenticate(self.admin)
        r=self.client.patch(f'/api/tickets/{self.own.id}/assign/',{'assigned_to':self.support.id},format='json')
        self.assertEqual(r.status_code,200)
        self.assertTrue(Notification.objects.filter(user=self.support,message__contains='assigned').exists())

    def test_invalid_assignment_and_invalid_status_return_400(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/tickets/{self.own.id}/assign/',{'assigned_to':999999},format='json').status_code,404)
        self.assertEqual(self.client.patch(f'/api/tickets/{self.own.id}/status/',{'status':'Bogus'},format='json').status_code,400)

    def test_support_can_update_status_and_requester_is_notified(self):
        self.client.force_authenticate(self.support)
        r=self.client.patch(f'/api/tickets/{self.assigned.id}/status/',{'status':'Resolved'},format='json')
        self.assertEqual(r.status_code,200)
        self.assertTrue(Notification.objects.filter(user=self.employee,message__contains='Resolved').exists())

    def test_search_and_filters(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(len(self.client.get('/api/tickets/?search=Other&status=Open').json()),1)
        self.assertEqual(len(self.client.get('/api/tickets/?priority=Urgent').json()),0)
        self.assertEqual(len(self.client.get(f'/api/tickets/?assigned_to={self.support.id}').json()),1)

    def test_invalid_ticket_id_is_404_and_employee_cannot_delete(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get('/api/tickets/999999/').status_code,404)
        self.assertEqual(self.client.delete(f'/api/tickets/{self.own.id}/').status_code,403)

    def test_ticket_required_fields_and_invalid_priority_are_rejected(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.post('/api/tickets/',{},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/tickets/',{'title':'Bad priority','description':'test','priority':'Impossible'},format='json').status_code,400)

    def test_admin_can_delete_ticket(self):
        self.client.force_authenticate(self.admin)
        r=self.client.delete(f'/api/tickets/{self.other.id}/')
        self.assertEqual(r.status_code,204)

    def test_admin_ticket_detail_and_update(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(f'/api/tickets/{self.other.id}/').status_code,200)
        r=self.client.patch(f'/api/tickets/{self.other.id}/',{'title':'Updated title'},format='json')
        self.assertEqual(r.status_code,200); self.other.refresh_from_db(); self.assertEqual(self.other.title,'Updated title')

    def test_task_assignment_visibility_and_status_permissions(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual([x['id'] for x in self.client.get('/api/tasks/').json()],[self.task.id])
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/',{'status':'Completed'},format='json').status_code,200)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/',{'title':'tampered'},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/tasks/',{'title':'not allowed','assigned_to':self.employee.id},format='json').status_code,403)

    def test_admin_task_crud_and_completion_notification(self):
        self.client.force_authenticate(self.admin)
        r=self.client.post('/api/tasks/',{'title':'New work','assigned_to':self.employee.id},format='json')
        self.assertEqual(r.status_code,201,r.data)
        task_id=r.data['id']
        r=self.client.patch(f'/api/tasks/{task_id}/',{'status':'Completed'},format='json')
        self.assertEqual(r.status_code,200)
        self.assertTrue(Notification.objects.filter(user=self.admin,message__contains='completed').exists())
        self.assertEqual(self.client.delete(f'/api/tasks/{task_id}/').status_code,204)

    def test_invalid_task_status_and_id(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/tasks/{self.task.id}/',{'status':'Impossible'},format='json').status_code,400)
        self.assertEqual(self.client.get('/api/tasks/999999/').status_code,404)

    def test_ticket_comment_action_and_notification_scope(self):
        self.client.force_authenticate(self.support)
        r=self.client.post(f'/api/tickets/{self.assigned.id}/comment/',{'body':'Working on it'},format='json')
        self.assertEqual(r.status_code,201)
        self.assertTrue(TicketComment.objects.filter(ticket=self.assigned,body='Working on it').exists())
        self.assertTrue(Notification.objects.filter(user=self.employee,message__contains='comment').exists())

    def test_employee_api_admin_only_create_and_deactivate(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get('/api/employees/').status_code,403)
        self.client.force_authenticate(self.admin)
        r=self.client.post('/api/employees/',{'username':'newperson','email':'new@example.com','password':'DemoPass123!','role':'employee'},format='json')
        self.assertEqual(r.status_code,201,r.data)
        profile_id=r.data['id']; user=User.objects.get(username='newperson')
        self.assertEqual(self.client.delete(f'/api/employees/{profile_id}/').status_code,204)
        user.refresh_from_db(); self.assertFalse(user.is_active)

    def test_admin_can_update_employee_profile(self):
        self.client.force_authenticate(self.admin)
        profile=self.employee.employee_profile
        r=self.client.patch(f'/api/employees/{profile.id}/',{'phone':'555-0102','designation':'Analyst'},format='json')
        self.assertEqual(r.status_code,200,r.data)
        profile.refresh_from_db(); self.assertEqual(profile.phone,'555-0102')

    def test_notification_list_is_private_and_mark_read_works(self):
        item=Notification.objects.create(user=self.employee,message='Private alert')
        self.client.force_authenticate(self.support)
        self.assertEqual(self.client.get('/api/notifications/').json(),[])
        self.client.force_authenticate(self.employee)
        web=Client(); web.force_login(self.employee)
        self.assertEqual(web.get('/notifications/').status_code,200)
        r=self.client.post(f'/api/notifications/{item.id}/mark_read/')
        self.assertEqual(r.status_code,200); item.refresh_from_db(); self.assertTrue(item.read)

    def test_web_login_ticket_upload_and_role_gated_reports(self):
        c=APIClient()
        self.assertEqual(c.get('/login/').status_code,200)
        self.assertEqual(c.post('/login/',{'username':'staff','password':'wrong'}).status_code,200)
        self.assertEqual(c.post('/login/',{'username':'staff','password':'DemoPass123!'}).status_code,302)
        self.assertEqual(c.get('/').status_code,200)
        upload=SimpleUploadedFile('proof.txt',b'help needed',content_type='text/plain')
        r=c.post('/tickets/new/',{'title':'From web','description':'Ticket with file','priority':'High','category':'General Support','attachment':upload})
        self.assertEqual(r.status_code,302)
        self.assertTrue(Ticket.objects.filter(title='From web',attachment__isnull=False).exists())
        self.assertEqual(c.get('/reports/').status_code,403)
        self.assertEqual(c.post('/password-reset/',{'email':'staff@example.com'}).status_code,302)

    def test_admin_report_pages_and_csv_variants(self):
        c=APIClient(); c.force_login(self.admin)
        self.assertEqual(c.get('/reports/').status_code,200)
        for kind in ('tickets','tasks','employees','departments','monthly'):
            r=c.get(f'/reports/tickets.csv?type={kind}')
            self.assertEqual(r.status_code,200); self.assertEqual(r['Content-Type'],'text/csv')

    def test_employee_edit_and_deactivate_views_admin_only(self):
        c=APIClient(); c.force_login(self.employee)
        self.assertEqual(c.get('/employees/').status_code,403)
        c.force_login(self.admin)
        profile=self.employee.employee_profile
        self.assertEqual(c.get('/employees/').status_code,200)
        self.assertEqual(c.get(f'/employees/{profile.id}/edit/').status_code,200)
        self.assertEqual(c.post(f'/employees/{profile.id}/deactivate/').status_code,302)
        self.employee.refresh_from_db(); self.assertFalse(self.employee.is_active)

    def test_attachment_download_requires_ticket_access(self):
        self.own.attachment.save('private.txt',SimpleUploadedFile('private.txt',b'secret'))
        c=APIClient()
        self.assertEqual(c.get(f'/tickets/{self.own.id}/attachment/').status_code,302)
        c.force_login(self.support)
        self.assertEqual(c.get(f'/tickets/{self.own.id}/attachment/').status_code,403)
        c.force_login(self.employee)
        self.assertEqual(c.get(f'/tickets/{self.own.id}/attachment/').status_code,200)

    def test_deadline_command_creates_one_notification_only(self):
        due=date.today()+timedelta(days=1)
        Task.objects.create(title='Due soon',assigned_to=self.employee,created_by=self.admin,due_date=due)
        with patch('helpdesk.management.commands.send_deadline_notifications.timezone.localdate',return_value=date.today()):
            call_command('send_deadline_notifications',verbosity=0)
            call_command('send_deadline_notifications',verbosity=0)
        self.assertEqual(Notification.objects.filter(user=self.employee,message__contains='Due soon').count(),1)
