"""
Serializers for the patients app.

PatientIntakeSerializer  – validates incoming FHIR Patient resource (Prompt 1).
PatientRetrieveSerializer – shapes the GET /patients/<id>/ response (Prompt 2).
"""
import datetime
import os
from typing import Any, Dict

from django.conf import settings
from rest_framework import serializers


class PatientIntakeSerializer(serializers.Serializer):
    """Validates a raw FHIR Patient JSON payload."""

    resourceType = serializers.CharField()
    id = serializers.CharField()
    birthDate = serializers.CharField()

    # Optional FHIR identifier list
    identifier = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )

    def validate_resourceType(self, value: str) -> str:
        if value != "Patient":
            raise serializers.ValidationError(
                f"Expected resourceType 'Patient', got '{value}'."
            )
        return value

    def validate_birthDate(self, value: str) -> datetime.date:
        """Parse and age-check the birthDate."""
        try:
            birth = datetime.date.fromisoformat(value)
        except ValueError:
            raise serializers.ValidationError(
                "birthDate must be in ISO format YYYY-MM-DD."
            )

        today = datetime.date.today()
        age = today.year - birth.year - (
            (today.month, today.day) < (birth.month, birth.day)
        )
        if age < 18:
            raise serializers.ValidationError(
                f"Patient must be >= 18 years old (computed age: {age})."
            )
        return birth

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Allow extra FHIR fields to pass through alongside validated ones."""
        validated = super().to_internal_value(data)
        validated["identifier"] = data.get("identifier", [])
        return validated


class PatientRetrieveSerializer(serializers.Serializer):
    """Shapes the response for GET /api/v1/patients/<patient_id>/.

    raw_json is included only when settings.RETURN_RAW_JSON is True.
    """

    patient_id = serializers.CharField()
    birth_date = serializers.DateField(format="%Y-%m-%d")
    ssn_masked = serializers.SerializerMethodField()
    raw_json = serializers.SerializerMethodField()

    def get_ssn_masked(self, obj: Any) -> str:
        return obj.masked_ssn()

    def get_raw_json(self, obj: Any) -> Any:
        # Only expose raw FHIR payload when explicitly enabled via env flag
        if getattr(settings, "RETURN_RAW_JSON", False):
            return obj.raw_json
        return None

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        rep = super().to_representation(instance)
        # Drop raw_json key entirely when disabled — no null leakage
        if not getattr(settings, "RETURN_RAW_JSON", False):
            rep.pop("raw_json", None)
        return rep
