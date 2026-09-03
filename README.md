# Clinic Booking System

**Live application:** https://clinicalbookingsystem.onrender.com
**Repository:** https://github.com/SalemMaina/ClinicalBookingSystem

---

## 1. System Design

### The Scenario

A small clinic with 5 doctors. Patients book 30-minute appointment slots within each doctor's working hours. Once booked, a slot is unavailable to others. Patients can cancel or reschedule.

### Models

**`accounts.User`** (custom `AbstractUser`)
| Field | Notes |
|---|---|
| `role` | `doctor` or `patient` |
| `description` | Doctor specialization (doctor-only) |
| `shift_start` / `shift_end` | Doctor's working hours (default 09:00–17:00, doctor-only) |

**`appointments.Slot`**
| Field | Notes |
|---|---|
| `doctor` | FK to `User`, restricted to `role=doctor` |
| `datetime` | The slot's start time |
| `is_booked` | Boolean flag |
| *(constraint)* | `unique_together(doctor, datetime)` — prevents duplicate slots at the DB level |

**`appointments.Appointment`**
| Field | Notes |
|---|---|
| `slot` | OneToOne FK to `Slot` |
| `patient` | FK to `User`, restricted to `role=patient` |
| `status` | `booked` / `cancelled` / `completed` |
| `created_at` | Auto timestamp |

### Key Design Decisions & Trade-offs

- **`Slot` and `Appointment` are separate models**, not one combined table. This preserves appointment history through cancellation/rescheduling — a slot can be freed and rebooked while the original `Appointment` record (and its `cancelled` status) still exists for audit purposes.
- **Slots are auto-generated**, not created ad-hoc per booking request. A management command (`generate_slots`) creates 30-minute `Slot` rows for each doctor based on their `shift_start`/`shift_end`. This turns "is this a valid bookable time?" into a simple existence check against real rows, rather than re-validating shift math on every booking request. The trade-off: slots must be (re)generated periodically for future dates — handled here by running the command on every deploy (see Section 3).
- **Race safety**: `unique_together` on `(doctor, datetime)` prevents duplicate slots outright. Booking and rescheduling both wrap the slot-state change in `transaction.atomic()` with `select_for_update()`, so two simultaneous booking requests for the same slot can't both succeed — the second correctly receives a conflict response instead of silently overwriting the first.
- **1-hour buffer and past-slot exclusion** live in one place: `Slot.objects.available()`, a custom queryset method. Both the availability-listing endpoint and the booking/reschedule validation call this same method, so the two can never drift out of sync.
- **Shift changes never retroactively affect already-booked future slots.** If a doctor's shift hours change, existing booked slots outside the new window are left alone — only future slot *generation* respects the new hours.
- **Doctor registration is admin-only**, not public self-service (patient registration is public). This reflects the scenario's fixed 5-doctor roster; doctors aren't expected to sign themselves up. Both a protected API endpoint and the Django admin panel support creating doctor accounts.
- **JWT authentication** (`djangorestframework-simplejwt`), with `role` embedded directly in the token payload via a custom `TokenObtainPairSerializer`. This lets clients read a user's role without a separate lookup call.
- **Deviations from the literal endpoint spec** (documented per the assessment's own "note ambiguous decisions" rule):
  - The bonus endpoint `GET /patients/{id}/appointments` is implemented as `GET /api/appointments/my-appointments/`, scoped to the authenticated JWT user rather than an arbitrary `{id}` in the URL. This was a deliberate choice — allowing any patient ID in the URL would let one patient query another's appointment history by guessing IDs. Scoping to `request.user` closes that hole while still satisfying the same functional need.
  - Endpoint paths and structure otherwise follow REST conventions judged clearest for this domain (e.g. `POST /api/appointments/book/` rather than a bare `POST /appointments`) rather than matching the spec's example paths character-for-character; the underlying required behaviors (validation rules, status codes, error handling) are the same.

### Implementation Stack

- **Language/Framework:** Python, Django + Django REST Framework
- **Database:** PostgreSQL
- **Auth:** JWT (`djangorestframework-simplejwt`)
- **Containerization:** Docker + Docker Compose (local dev)
- **Deployment:** Render (Docker-based Web Service + managed Postgres)
- **CI/CD:** GitHub Actions
- **Static files:** WhiteNoise
- **WSGI server (production):** Gunicorn

---

## 2. API Endpoints

Base URL (local): `http://localhost:8001`
Base URL (live): `https://clinicalbookingsystem.onrender.com`

### Authentication

| Method | Path | Description | Auth required |
|---|---|---|---|
| POST | `/api/token/` | Obtain JWT access/refresh tokens (role embedded in payload) | No |
| POST | `/api/token/refresh/` | Refresh an access token | No |

### Accounts

| Method | Path | Description | Auth required |
|---|---|---|---|
| POST | `/api/accounts/register/patient/` | Register a new patient | No |
| POST | `/api/accounts/register/doctor/` | Register a new doctor | **Yes — admin/staff only** |

### Appointments

| Method | Path | Description | Auth required |
|---|---|---|---|
| GET | `/api/appointments/slots/?doctor={id}` | List available slots (optionally filtered by doctor) | Yes — any authenticated user |
| POST | `/api/appointments/book/` | Book an available slot | Yes — **patient only** |
| GET | `/api/appointments/my-appointments/` | List the authenticated patient's own appointments | Yes — **patient only** (scoped to `request.user`) |
| GET | `/api/appointments/my-schedule/` | List the authenticated doctor's own booked appointments | Yes — **doctor only**, 403 otherwise |
| POST | `/api/appointments/{id}/cancel/` | Cancel an appointment (reopens the slot) | Yes — must be the owning patient |
| PATCH | `/api/appointments/{id}/reschedule/` | Move an appointment to a new slot (validated as a fresh booking) | Yes — must be the owning patient |

### Permissions Summary

| Role | Can do |
|---|---|
| **Anonymous** | Register as a patient; obtain a JWT |
| **Patient** | View available slots, book, view own appointments, cancel own, reschedule own |
| **Doctor** | View available slots; view own schedule (`my-schedule`) |
| **Admin/staff** | Everything a normal user can, plus register doctor accounts, full Django admin access |

Enforcement approach: permission checks are inline in each view (e.g. `if request.user.role != User.Role.PATIENT: return 403`) rather than custom `BasePermission` classes. For the current scope (two roles, a handful of endpoints), this keeps the logic visible directly in the view rather than spread across separate permission class files — a trade-off worth revisiting if the role/permission surface grows.

### Testing the API

**1. Get an admin token** (a superuser is bootstrapped on deploy — see Section 3):
```bash
curl -X POST https://clinicalbookingsystem.onrender.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "12345678"}'
```
Copy the `access` token from the response.

**2. Register a doctor** (requires the admin token):
```bash
curl -X POST https://clinicalbookingsystem.onrender.com/api/accounts/register/doctor/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_access_token>" \
  -d '{"username": "doc1", "password": "testpass123", "description": "General Practitioner", "shift_start": "09:00", "shift_end": "17:00"}'
```

**3. Register a patient** (public, no auth needed):
```bash
curl -X POST https://clinicalbookingsystem.onrender.com/api/accounts/register/patient/ \
  -H "Content-Type: application/json" \
  -d '{"username": "patient1", "password": "testpass123"}'
```

**4. Log in as the patient and view available slots:**
```bash
curl -X POST https://clinicalbookingsystem.onrender.com/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "patient1", "password": "testpass123"}'

curl https://clinicalbookingsystem.onrender.com/api/appointments/slots/ \
  -H "Authorization: Bearer <patient_access_token>"
```

**5. Book, cancel, or reschedule** using the patient token and a `slot_id`/`appointment_id` from the responses above:
```bash
curl -X POST https://clinicalbookingsystem.onrender.com/api/appointments/book/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <patient_access_token>" \
  -d '{"slot_id": <id>}'
```

*(Windows PowerShell users: replace `curl -d '...'` with `Invoke-RestMethod -Method Post -Body (... | ConvertTo-Json) -ContentType "application/json"` — PowerShell's `curl` alias doesn't handle this syntax the same way.)*

**Admin panel:** `https://clinicalbookingsystem.onrender.com/admin/` — log in with `admin` / `12345678` to browse/manage users, slots, and appointments directly.

---

## 3. Tests

Test suite: Django's `APITestCase` (DRF), run via `python manage.py test`.

**Coverage (30 tests across `accounts` and `appointments`):**
- **Accounts:** patient self-registration, doctor-only-field isolation, admin-only doctor registration (accepted/rejected for non-admins/anonymous), JWT role claim correctness for both roles.
- **Appointments:**
  - Slot listing: correct exclusion of past/buffered/booked slots, doctor filtering, auth requirement.
  - Booking: success path, rejecting already-booked/past/buffered slots, role enforcement (doctors can't book), nonexistent-slot handling.
  - My-appointments: scoping to the authenticated patient only.
  - My-schedule: scoping to the authenticated doctor only, cancelled-appointment exclusion, strict 403 for non-doctors.
  - Cancellation: success (slot reopened), ownership enforcement, rejecting double-cancellation.
  - Reschedule: success (old slot freed, new slot locked, in one transaction), rejecting reschedule of cancelled appointments, validating the new slot exactly as a fresh booking (past/buffered/already-booked), ownership enforcement.

**Run locally:**
```bash
docker compose exec web python manage.py test
```

**Note on test speed:** a fast password hasher (`MD5PasswordHasher`) is configured for the test environment only, since the default `PBKDF2` hasher's deliberate slowness (correct for production) otherwise makes every JWT-login-based test noticeably slow with no security benefit in a throwaway test DB.

**What wasn't covered:** true concurrent-request race testing (two genuinely simultaneous booking requests hitting the same slot) requires Django's `TransactionTestCase` with real threads, since the standard `TestCase` wraps each test in a transaction that doesn't exercise cross-thread DB locking. `select_for_update()` is still correctly enforced at the database level in production; this is a noted gap in test coverage for that specific scenario, not in the underlying protection itself.

---

## 4. CI/CD Pipeline

**Tool:** GitHub Actions (`.github/workflows/ci-cd.yml`)

**Deployment target:** Render (Docker-based Web Service, connected to a Render-managed PostgreSQL instance)

**Branch that triggers deployment:** `main`

**Pipeline behavior:**
1. **On every push or pull request to `main` or `development`:** a `test` job spins up an isolated PostgreSQL 15 service container, installs dependencies, runs migrations, and runs the full test suite.
2. **On a push to `main` specifically** (i.e. after a PR is merged into `main`), and **only if the `test` job passed**, a `deploy` job runs: it sends a `POST` request to Render's deploy hook URL (stored as the GitHub Actions secret `RENDER_DEPLOY_HOOK`), which triggers Render to pull the latest `main` commit, rebuild the Docker image, and redeploy.
3. Render's own automatic git-push deployment is **disabled**, so deployments only happen through this gated pipeline — a failing test suite blocks deployment entirely.

**Render build/start process:** Render auto-detects the repo's `Dockerfile`. The container's entrypoint is `start.sh`, which runs (in order): `collectstatic`, `migrate`, a one-time-safe `createsuperuser --noinput` (idempotent — no-ops if the user already exists), `generate_slots --days 7` (idempotent via `get_or_create`, keeps a rolling week of bookable slots available on every deploy), then hands off to `gunicorn`.

---

## 5. Running Locally

**Requirements:** Docker, Docker Compose

1. Clone the repo and create a `.env` file with (at minimum):
   ```
   SECRET_KEY=<any local dev value>
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   POSTGRES_DB=clinical_booking
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   DB_HOST=db
   DB_PORT=5432
   ```
2. Build and start:
   ```bash
   docker compose up --build
   ```
3. Run migrations and generate slots (first time only):
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   docker compose exec web python manage.py generate_slots --days 7
   ```
4. The app is available at `http://localhost:8001`.

---

## 6. AI Usage Reflection

See [`AI_REFLECTION.md`](./AI_REFLECTION.md).
