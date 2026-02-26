"""
PatientRecord and AccessLog models.

PII fields (SSN, passport) are encrypted with Fernet (see encryption.py).
AccessLog records every GET access for auditability.
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import models

from .encryption import encrypt_to_db, decrypt_from_db


class PatientRecord(models.Model):
    """One record per unique patient identity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The FHIR Patient.id value – used to deduplicate on intake
    patient_id = models.CharField(max_length=255, unique=True, db_index=True)

    birth_date = models.DateField()

    # PII stored as Fernet ciphertext encoded to base64 text
    ssn_encrypted = models.TextField(blank=True, default="")
    passport_encrypted = models.TextField(blank=True, default="")

    # Full incoming FHIR payload
    raw_json = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Patient Record"
        verbose_name_plural = "Patient Records"

    def __str__(self) -> str:
        return f"PatientRecord({self.patient_id})"

    # ------------------------------------------------------------------
    # SSN helpers
    # ------------------------------------------------------------------

    def set_ssn(self, plaintext: str) -> None:
        """Encrypt *plaintext* SSN and store in ssn_encrypted."""
        self.ssn_encrypted = encrypt_to_db(plaintext)

    def get_ssn(self) -> str:
        """Decrypt and return the stored SSN."""
        if not self.ssn_encrypted:
            return ""
        return decrypt_from_db(self.ssn_encrypted)

    def masked_ssn(self) -> str:
        """Return a masked SSN like ***-**-1234 (last 4 digits visible)."""
        ssn = self.get_ssn()
        if not ssn:
            return ""
        digits = ssn.replace("-", "").replace(" ", "")
        last4 = digits[-4:] if len(digits) >= 4 else digits
        return f"***-**-{last4}"

    # ------------------------------------------------------------------
    # Passport helpers
    # ------------------------------------------------------------------

    def set_passport(self, plaintext: str) -> None:
        """Encrypt *plaintext* passport number and store in passport_encrypted."""
        self.passport_encrypted = encrypt_to_db(plaintext)

    def get_passport(self) -> str:
        """Decrypt and return the stored passport number."""
        if not self.passport_encrypted:
            return ""
        return decrypt_from_db(self.passport_encrypted)


class AccessLog(models.Model):
    """Immutable audit trail for every patient record retrieval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    patient = models.ForeignKey(
        PatientRecord,
        on_delete=models.CASCADE,
        related_name="access_logs",
    )

    # Nullable: anonymous access is possible in dev; enforced by permissions in prod
    accessed_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient_accesses",
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    # auto_now_add makes this effectively immutable after creation
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Access Log"
        verbose_name_plural = "Access Logs"

    def __str__(self) -> str:
        return f"AccessLog({self.patient.patient_id}, {self.timestamp.isoformat()})"
