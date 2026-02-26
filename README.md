# PIGW – Patient Interoperability Gateway

A minimal Django + DRF API that ingests FHIR `Patient` resources, encrypts PII
fields (SSN, passport), and stores structured data for downstream interoperability
pipelines.

---

## Quick Start

### 1. Clone and set up a virtual environment

```bash
git clone <repo-url> pigw
cd pigw
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set the following:

| Variable | How to generate |
|---|---|
| `DJANGO_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `FERNET_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `POSTGRES_*` | Your Postgres credentials (leave blank to use SQLite for local dev) |

### 3. Run migrations

```bash
cd pigw        # inner project directory containing manage.py
python manage.py migrate
```

### 4. Start the development server

```bash
python manage.py runserver
```

The API is available at **http://127.0.0.1:8000/api/v1/patient-intake/**.

---

## API Usage

### `POST /api/v1/patient-intake/`

**Request body** – a FHIR `Patient` resource:

```json
{
  "resourceType": "Patient",
  "id": "patient-001",
  "birthDate": "1985-06-15",
  "identifier": [
    {
      "system": "http://hl7.org/fhir/sid/us-ssn",
      "value": "123-45-6789",
      "type": { "text": "SSN" }
    },
    {
      "system": "http://example.org/passport",
      "value": "A9876543",
      "type": { "text": "Passport Number" }
    }
  ]
}
```

**Success (201)**:
```json
{ "status": "accepted", "patient_id": "patient-001" }
```

**Validation error (400)** example:
```json
{ "birthDate": ["Patient must be >= 18 years old (computed age: 15)."] }
```

---

## Running Tests

### Django test runner

```bash
python manage.py test patients.tests
```

### pytest

```bash
pytest                          # from the pigw/ directory (where pytest.ini lives)
```

---

## Encryption notes

| Aspect | Detail |
|---|---|
| **Algorithm** | Fernet (AES-128-CBC + HMAC-SHA256) via the `cryptography` library |
| **Why Fernet?** | Authenticated encryption in a single, audited primitive; no custom crypto |
| **Key storage** | `FERNET_KEY` env var → loaded into `settings.FERNET_KEY` via `dev.py` / OS env |
| **DB storage** | Raw Fernet token → base64-encoded → stored as TEXT column |
| **Key rotation** | Replace `FERNET_KEY` and re-encrypt existing rows (use `MultiFernet` for zero-downtime rotation) |

The key is never stored in source control. Each run reads it from the environment,
so a leaked database dump does **not** expose PII without the key.

---

## Project Structure

```
pigw/
├─ pigw/                     ← Django project package
│  ├─ settings/
│  │  ├─ base.py             ← shared settings
│  │  └─ dev.py              ← dev overrides, .env loading, SQLite fallback
│  ├─ urls.py
│  ├─ asgi.py / wsgi.py
├─ patients/
│  ├─ models.py              ← PatientRecord
│  ├─ encryption.py          ← Fernet helpers
│  ├─ serializers.py         ← PatientIntakeSerializer (FHIR validation)
│  ├─ views.py               ← PatientIntakeView
│  ├─ urls.py
│  └─ tests/
│     └─ test_intake.py
├─ requirements.txt
├─ .env.example
└─ manage.py
```

---

## Status snapshot

- Core patient intake API and encryption are implemented.
- Retrieve endpoint returns masked SSN and writes an access log.
- Dev settings use SQLite fallback; prod settings expect Postgres and env-driven secrets.
- Basic tests exist for intake and encryption; extend as needed for new features.
# HealthCarePIGW
