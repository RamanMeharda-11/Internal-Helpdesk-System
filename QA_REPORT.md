# QA report

## Verification run

- Django system check: passed.
- Migration consistency check: passed; no ungenerated changes.
- Template compilation: all 11 application and password reset templates compile.
- OpenAPI schema validation: passed with no warnings or errors.
- API/web test suite: 25 tests passed.

## Test coverage

| Area | Scenarios |
|---|---|
| Authentication | Anonymous API rejection, web login success/failure, password reset request |
| Tickets | Create with attachment, required fields, invalid priority/status, search/filter, assignment, status transitions, comments, detail 404, delete permissions |
| Attachments | Upload accepted/rejected by extension; authenticated ticket access required for download |
| Tasks | Role scoped list, allowed status update, blocked field tampering, admin CRUD, invalid status/ID, completion notification |
| Employees | Admin only listing/creation/deactivation and web edit/deactivation; non-admin denied |
| Notifications | Per-user visibility, comment/assignment/status/task events, mark as read |
| Reports | Admin page and CSV exports for tickets, tasks, employees, departments, monthly summary |

Run again with `python manage.py test helpdesk`.

## Remaining operational notes

- Password reset uses the local console email backend. Configure SMTP for actual email delivery.
- Dashboard and reports load Chart.js from a CDN, so charts require internet access in the browser.
- Deadline approaching notifications need a scheduled job before they can be sent automatically.
- The `send_deadline_notifications` management command creates deduplicated reminders; schedule it daily for automatic delivery.
- Configure a private secret key, HTTPS, production host list, and production database before deployment.
