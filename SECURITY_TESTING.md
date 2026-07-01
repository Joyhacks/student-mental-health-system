# Security Testing and Hardening

This document records the security testing carried out on the Student Mental Health
Information Management System and the production hardening applied. It is the
evidence base for the security discussion in the project write-up.

## 1. Automated test suite

The application ships with an automated test suite built on Django's own test
framework (`TestCase` and the test client). Every test builds its own data from
the role Groups created by the migrations and does not depend on the demo seed.

Run it with:

```
python manage.py test
```

Total: **26 tests, all passing** (run time approximately 2 seconds).

Coverage by area:

| Area | What the tests verify |
|------|-----------------------|
| Authentication | Valid login reaches the dashboard; logout returns to login; a wrong password is rejected and does not create a session; anonymous access to `/dashboard/`, `/records/`, and `/audit/` redirects to login; each role sees its own dashboard. |
| Access control | Students receive 403 on record create, edit, and delete; counselors see only their assigned students and receive 404 for records outside their caseload; counselors cannot delete (403); students see only their own records and receive 404 for others'; administrators can list, create, edit, and soft-delete; `/audit/` is 200 for administrators and 403 for counselors and students; the counselor create form offers only assigned students. |
| Encryption | The stored content column is base64 ciphertext, never the plaintext; reading the field returns the original text; the same plaintext saved twice yields different ciphertext (fresh IV per save); blank content round-trips safely. |
| Soft-delete | An administrator delete sets `is_active` to false, keeps the database row, and removes the record from every role's list and detail (404 thereafter). |
| Audit logging | A login writes exactly one entry; opening a record detail writes one view entry while the list writes none; create, update, and soft-delete each write exactly one entry with no duplication; a failed login records the attempted username but never the password; audit entries cannot be modified or deleted. |
| Injection and XSS | A SQL-injection payload submitted through a form and a search filter is treated as literal data (the ORM parameterises queries) and no table is affected; record content containing a `<script>` tag is rendered escaped in the page, not executed (Django templates auto-escape). |

### Test-speed configuration

Password hashing with the default PBKDF2-SHA256 is deliberately slow, which made
the suite take several minutes. `config/settings.py` now detects when it is being
run under `manage.py test` (via `sys.argv`) and, only in that case, substitutes a
fast MD5 password hasher. Production and normal running are unaffected and keep
PBKDF2-SHA256. No extra flags are needed; `python manage.py test` is unchanged.
Run time dropped from roughly 230 seconds to about 2 seconds.

## 2. Static and dependency scanning

Scanning tools are pinned in `dev-requirements.txt` (separate from the runtime
`requirements.txt`): `bandit==1.9.4` and `pip-audit==2.6.2`.

### Bandit (static analysis)

```
bandit -r accounts records audit config -x "*/tests.py,*/factories.py" -f txt -o bandit_report.txt
```

The initial run reported three issues, all reviewed and resolved:

| ID | Location | Severity | Assessment and resolution |
|----|----------|----------|---------------------------|
| B608 hardcoded_sql_expressions | `records/management/commands/show_encryption.py` | Medium | Not exploitable. The only interpolated value is the table name, taken from the model's own metadata (a trusted constant), and the record id is passed as a bound parameter. Marked `# nosec B608` with an explanatory comment. |
| B105 hardcoded_password_string | `accounts/management/commands/seed_demo.py` (demo user password) | Low | Expected. This is a demo-only seed credential that the command exists to create and print, not a production secret. Marked `# nosec B105` with a reason. |
| B105 hardcoded_password_string | `accounts/management/commands/seed_demo.py` (superuser password) | Low | Same as above: demo seed credential. Marked `# nosec B105` with a reason. |

After review, bandit reports **0 issues** (3 findings consciously disabled with
written justifications; no finding was silenced without a stated reason). The
full output is saved in `bandit_report.txt`.

### pip-audit (dependency vulnerabilities)

```
pip-audit
```

The initial run found **4 known vulnerabilities in `cryptography` 45.0.7**
(PYSEC-2026-35, PYSEC-2026-36, GHSA-r6ph-v2qm-q3c2, GHSA-537c-gmf6-5ccf). This
was a real finding. Resolution: `cryptography` was upgraded to **49.0.0** (pinned
in `requirements.txt`), which is past all listed fix versions. The encryption
field was re-tested after the upgrade and continues to pass. A re-run of pip-audit
reports **No known vulnerabilities found**. The output is saved in
`pip_audit_report.txt`.

## 3. Production hardening

All hardening is gated on the `DJANGO_PRODUCTION` environment flag so the same
codebase runs over plain http in development and fully hardened when deployed.

With `DJANGO_PRODUCTION=true`:

- `DEBUG` is `False`.
- `SECURE_SSL_REDIRECT` is on (http is redirected to https).
- `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are on.
- `SECURE_HSTS_SECONDS` is one year, with `SECURE_HSTS_INCLUDE_SUBDOMAINS` and
  `SECURE_HSTS_PRELOAD` enabled.
- `SECURE_PROXY_SSL_HEADER` trusts the platform's forwarded-protocol header.

Applied in every environment (safe for http development):

- Session and CSRF cookies are `HttpOnly` and `SameSite=Lax`.
- `SECURE_CONTENT_TYPE_NOSNIFF` is `True`.
- `X_FRAME_OPTIONS` is `DENY`.

`ALLOWED_HOSTS` is read from the `DJANGO_ALLOWED_HOSTS` environment variable
(comma-separated), defaulting to `127.0.0.1,localhost`, so the deployment domain
(for example a PythonAnywhere subdomain) can be added at deploy time while local
development keeps working.

Verification:

```
DJANGO_PRODUCTION=true DJANGO_ALLOWED_HOSTS="<domain>,127.0.0.1,localhost" \
    python manage.py check --deploy
```

reports **System check identified no issues (0 silenced)**. In normal development
mode, `python manage.py check` is also clean and the application serves over http
locally (verified: the login page returns HTTP 200).

## 4. Summary of security posture

The system enforces defence in depth. Access control is applied at both the view
level (login and role checks) and the queryset level (role-scoped queries), so
unauthorised records are never loaded and cannot be reached by guessing a URL.
Sensitive record content is encrypted at rest with AES-256-CBC using a key held
only in the environment, with a fresh IV per record. All access and data changes
are written to an append-only audit trail that cannot be edited or deleted through
the application or the admin. Passwords use Django's PBKDF2-SHA256; failed logins
are rate-limited and logged without the password. The framework's built-in
protections against SQL injection (parameterised ORM queries), XSS (template
auto-escaping), and CSRF (token middleware) are in force and covered by tests.
Static analysis (bandit) and dependency auditing (pip-audit) are clean after one
real dependency vulnerability was remediated by upgrading `cryptography`.
Production deployment is hardened behind an environment flag and passes Django's
deployment check with no warnings.
