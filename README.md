# Internal Helpdesk & Task Management System

A demo-only Django application for employee support tickets, task assignment and team activity. It uses SQLite locally and Django REST Framework for authenticated APIs. Do not connect it to production customer systems or real organizational databases.

## Architecture

```text
internalhelpdeskproject/  Django settings and root routes
helpdesk/                 Core domain app: models, pages, forms, permissions and API
  models.py               Department, employee profile, ticket, task, comment, notification, activity
  views.py                Session-authenticated web workflows and CSV export
  api.py                  DRF ticket/task viewsets and role scoping
  serializers.py          Validated JSON representations
  templates/              Dashboard and sign-in/account pages
  static/                 Dashboard CSS and JavaScript
```

The single core app keeps this starter quick to run. As it grows, `accounts`, `tickets`, `tasks` and `reports` can be split out without changing the domain model responsibilities. The default Django user model is paired with `EmployeeProfile` for role and department data; Django's built-in password hashing and sessions handle authentication.

## Local setup

Requires Python 3.12+.

```powershell
cd Internal-Helpdesk-System
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations helpdesk
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in with the superuser. Manage departments and employee profiles at `/admin/`. Admin users can add accounts from the dashboard. API documentation is at `/api/docs/`; ticket and task endpoints are under `/api/tickets/` and `/api/tasks/`. API access requires login. Employees see only tickets they created and tasks assigned to them; support staff see tickets assigned to them; admins can manage all records.

## Main web flows

- Create support tickets from the dashboard; employees see their own requests.
- Admin assigns tickets and tasks, and staff can update ticket status.
- Ticket comments and activity are recorded in the database.
- Admin exports ticket records as CSV.
- Search tickets with the dashboard search field or API `?search=network`; filter the API with `?status=Open`, `?priority=Urgent`, and `?assigned_to=1`.

## API overview

DRF router endpoints: `/api/tickets/`, `/api/tasks/`, `/api/employees/` and `/api/notifications/`. Ticket-specific actions are `/api/tickets/{id}/assign/` (admin only), `/api/tickets/{id}/status/` (admin/support) and `/api/tickets/{id}/comment/` (authenticated ticket participant). Employee management is admin-only; notification rows are private to their owner and support `mark_read`. OpenAPI schema is `/api/schema/` and Swagger UI is `/api/docs/`. Session and Basic authentication are configured for local development. Use HTTPS and a production authentication strategy before deployment.

## Data model

- `Department`: organizational grouping.
- `EmployeeProfile`: one-to-one role, department, contact and designation fields attached to Django's user.
- `Ticket` and `TicketComment`: support request, assignment, status, priority and conversation.
- `Task`: assignment, deadline, priority and progress state.
- `Notification` and `ActivityLog`: user alerts and audit-style workspace events.

## QA status

The APIClient suite in `helpdesk/tests.py` covers authentication, ticket/task CRUD, role boundaries, assignment/status actions, comments, filtering, file uploads, employee management, notifications, reports and password reset. Run it with `python manage.py test helpdesk`.

## Attachments, notifications and account recovery

Ticket attachments accept PDF, PNG/JPG, TXT, DOC/DOCX, XLSX and ZIP files up to 10 MB. Downloads require sign-in and access to the ticket. Password reset links are sent through Django email; the demo uses the console email backend, so copy the reset URL from the terminal. Notifications appear from the bell and can be marked read. Inactive employee accounts are deactivated so historical tickets remain intact.

To notify assignees one day before task deadlines, schedule `python manage.py send_deadline_notifications` to run daily using Windows Task Scheduler (or cron). The command is safe to rerun and avoids duplicate reminders.

## Reports

The admin reports page at `/reports/` shows status distribution, monthly ticket volume, department totals and employee task completion. CSV downloads are available for tickets, tasks, employees, departments and monthly totals from the report page.

## Demo security notes

Set `DEBUG=False`, a private `SECRET_KEY`, explicit `ALLOWED_HOSTS`, HTTPS, secure cookie settings, upload validation and a production database before deployment. Keep this installation and its generated data separate from live systems.
