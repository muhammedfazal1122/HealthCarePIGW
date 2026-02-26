"""
Tests for the patient intake endpoint.

Run with:
    python manage.py test patients.tests          (Django test runner)
    pytest --ds=pigw.settings.dev                 (pytest + django-pytest plugin)
"""
import datetime
import json

from django.test import TestCase, Client
from django.urls import reverse

from patients.models import PatientRecord


class CSRFDisabledTestCase(TestCase):
    """Test case with CSRF protection disabled for API testing."""
    
    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=False)


def _make_patient(
    patient_id: str = "pat-001",
    birth_date: str = "1990-05-15",
    ssn: str | None = "123-45-6789",
    passport: str | None = None,
) -> dict:
    """Build a minimal FHIR Patient payload for test requests."""
    payload: dict = {
        "resourceType": "Patient",
        "id": patient_id,
        "birthDate": birth_date,
        "identifier": [],
    }
    if ssn:
        payload["identifier"].append(
            {
                "system": "http://hl7.org/fhir/sid/us-ssn",
                "value": ssn,
                "type": {"text": "SSN"},
            }
        )
    if passport:
        payload["identifier"].append(
            {
                "system": "http://example.org/passport",
                "value": passport,
                "type": {"text": "Passport Number"},
            }
        )
    return payload


INTAKE_URL = "/api/v1/patient-intake/"


class IntakeUnder18Test(CSRFDisabledTestCase):
    """Under-18 patients must be rejected with HTTP 400."""

    def test_under_18_is_rejected(self) -> None:
        # Birth date 10 years ago → clearly under 18
        young_dob = (datetime.date.today() - datetime.timedelta(days=10 * 365)).isoformat()
        payload = _make_patient(birth_date=young_dob)

        response = self.client.post(
            INTAKE_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        # Error should mention 18
        response_body = response.json()
        self.assertIn("birthDate", response_body)

    def test_exactly_17_years_old_rejected(self) -> None:
        today = datetime.date.today()
        dob = today.replace(year=today.year - 17).isoformat()
        payload = _make_patient(birth_date=dob)
        response = self.client.post(
            INTAKE_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class IntakeValidPatientTest(CSRFDisabledTestCase):
    """Valid adult patient ingestion should persist accurately."""

    def setUp(self) -> None:
        # Use a known Fernet key for tests so encryption works without .env
        import os
        from cryptography.fernet import Fernet
        from django.conf import settings

        if not getattr(settings, "FERNET_KEY", ""):
            settings.FERNET_KEY = Fernet.generate_key().decode()

    def test_valid_patient_ingestion(self) -> None:
        plain_ssn = "987-65-4321"
        payload = _make_patient(
            patient_id="pat-test-valid",
            birth_date="1985-03-20",
            ssn=plain_ssn,
            passport="A1234567",
        )

        response = self.client.post(
            INTAKE_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )

        # 1. API returns 201 with expected body
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(body["patient_id"], "pat-test-valid")

        # 2. PatientRecord actually created in DB
        record = PatientRecord.objects.get(patient_id="pat-test-valid")

        # 3. raw_json stored correctly
        self.assertEqual(record.raw_json["id"], "pat-test-valid")
        self.assertIn("identifier", record.raw_json)

        # 4. SSN is NOT stored as plaintext
        self.assertNotEqual(record.ssn_encrypted, plain_ssn)
        self.assertTrue(len(record.ssn_encrypted) > 0, "ssn_encrypted should not be empty")

        # 5. Decryption returns the original value
        self.assertEqual(record.get_ssn(), plain_ssn)

        # 6. Masked SSN shows correct format
        masked = record.masked_ssn()
        self.assertTrue(masked.startswith("***-**-"))
        self.assertTrue(masked.endswith("4321"))

    def test_duplicate_patient_is_updated_not_duplicated(self) -> None:
        payload = _make_patient(patient_id="pat-dupe", birth_date="1990-01-01")
        self.client.post(INTAKE_URL, data=json.dumps(payload), content_type="application/json")
        self.client.post(INTAKE_URL, data=json.dumps(payload), content_type="application/json")

        count = PatientRecord.objects.filter(patient_id="pat-dupe").count()
        self.assertEqual(count, 1, "Re-ingestion should update, not create a duplicate")

    def test_missing_resource_type_returns_400(self) -> None:
        payload = {"id": "pat-x", "birthDate": "1980-01-01"}
        response = self.client.post(
            INTAKE_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_wrong_resource_type_returns_400(self) -> None:
        payload = {"resourceType": "Observation", "id": "pat-x", "birthDate": "1980-01-01"}
        response = self.client.post(
            INTAKE_URL,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
