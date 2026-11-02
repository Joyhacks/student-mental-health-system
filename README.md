# Student Mental Health Information Management System

A Django app for keeping student counselling records where the content is sensitive and access has to be provable. Students, counselors and administrators each see a different slice of the data, record content is encrypted in the database, and every access is written to an audit log that can't be edited.

## How access works

| Role | Can see | Can change |
|---|---|---|
| Student | Their own records | Nothing |
| Counselor | Records for students assigned to them | Create and edit for those students |
| Administrator | Everything, plus the audit log | Create, edit and soft-delete |

Scoping is done in the queryset, not only in the view. A counselor who guesses the URL of another counselor's record gets a 404, because the record is never loaded.

## Security

- Record content uses a custom `EncryptedTextField`: AES-256 with a fresh random IV per save. The key comes from the environment and the app refuses to start if it's missing or the wrong length.
- An append-only audit trail records logins, failed logins (username only, never the password), record views and every create, update and delete. Entries can't be changed or removed through the app or the admin.
- Failed logins are rate-limited per client IP. The limit reads `REMOTE_ADDR` only, because `X-Forwarded-For` can be spoofed.
- Deletes are soft deletes, so the row and its history stay.
- With `DJANGO_PRODUCTION=true` you get HTTPS redirect, secure cookies and a one-year HSTS. `check --deploy` passes with no warnings.

[SECURITY_TESTING.md](SECURITY_TESTING.md) has the full test results, the bandit and pip-audit findings and what was done about each.

## Running it

Python 3.10 or newer.

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then set SECRET_KEY and ENCRYPTION_KEY
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` creates an administrator, two counselors and two students with sample records, all with invented details, and prints the logins.

To see the encryption for yourself, `python manage.py show_encryption` prints the first record's decrypted text next to the raw ciphertext stored in the database.

## Tests

```bash
python manage.py test
```

26 tests covering authentication, per-role access, encryption, soft delete, audit logging, and SQL injection and XSS payloads. CI runs them on every push along with bandit and pip-audit.

## Layout

```
accounts/   login, rate limiting, role dashboards, demo seed
records/    student profiles, encrypted records, permissions
audit/      audit log model, signals and middleware
config/     settings and URLs
```
