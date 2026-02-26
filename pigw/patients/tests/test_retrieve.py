"""
Tests for the patient retrieve endpoint and access logging.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from patients.models import AccessLog, PatientRecord


class CSRFDisabledTestCase(TestCase):
    """Test case with CSRF protection disabled for API testing."""
    
    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=False)


class PatientRetrieveTest(CSRFDisabledTestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="testpass123"
        )

        self.record = PatientRecord.objects.create(
            patient_id="pat-retrieve-1",
            birth_date="1980-01-01",
            raw_json={"id": "pat-retrieve-1"},
        )
        self.record.set_ssn("111-22-3333")
        self.record.save()

        self.url = f"/api/v1/patients/{self.record.patient_id}/"

    def test_requires_authentication(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_returns_masked_ssn_and_creates_access_log(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            self.url,
            HTTP_USER_AGENT="pytest-agent",
            REMOTE_ADDR="203.0.113.10",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["patient_id"], self.record.patient_id)
        self.assertTrue(body["ssn_masked"].startswith("***-**-"))
        self.assertTrue(body["ssn_masked"].endswith("3333"))
        self.assertNotIn("raw_json", body)

        log = AccessLog.objects.get(patient=self.record)
        self.assertEqual(log.accessed_by, self.user)
        self.assertEqual(str(log.ip_address), "203.0.113.10")
        self.assertIn("pytest-agent", log.user_agent)

