"""
Patient API views.

PatientIntakeView  – POST /api/v1/patient-intake/      (accepts FHIR Patient)
PatientRetrieveView – GET  /api/v1/patients/<patient_id>/  (retrieve + audit log)
"""
from typing import Any, Dict, List, Optional

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AccessLog, PatientRecord
from .serializers import PatientIntakeSerializer, PatientRetrieveSerializer


def _find_identifier_value(
    identifiers: List[Dict[str, Any]], keyword: str
) -> Optional[str]:
    """Return the first identifier value whose system or type.text contains *keyword*."""
    kw = keyword.lower()
    for item in identifiers:
        system: str = item.get("system", "")
        type_text: str = (item.get("type") or {}).get("text", "")
        if kw in system.lower() or kw in type_text.lower():
            return item.get("value")
    return None


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract real client IP, respecting X-Forwarded-For if present."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # First address in the list is the originating client
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@method_decorator(csrf_exempt, name='dispatch')
class PatientIntakeView(APIView):
    """Ingest a FHIR Patient resource and persist it.

    Auth: AllowAny in dev for easy curl testing.
    In production, lock this down with IsAuthenticated or API-key middleware.
    """
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PatientIntakeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        identifiers: List[Dict[str, Any]] = data.get("identifier", [])

        ssn = _find_identifier_value(identifiers, "ssn")
        passport = _find_identifier_value(identifiers, "passport")

        # Create-or-update – patient_id is the natural dedup key
        record, _ = PatientRecord.objects.get_or_create(
            patient_id=data["id"],
            defaults={"birth_date": data["birthDate"], "raw_json": request.data},
        )

        # Always refresh mutable fields on re-ingestion
        record.birth_date = data["birthDate"]
        record.raw_json = request.data

        if ssn:
            record.set_ssn(ssn)
        if passport:
            record.set_passport(passport)

        record.save()

        return Response(
            {"status": "accepted", "patient_id": data["id"]},
            status=status.HTTP_201_CREATED,
        )


class PatientRetrieveView(APIView):
    """Return masked patient data and write an AccessLog entry.

    Auth: IsAuthenticated — requires a logged-in user (session or basic auth).
    In development: create a user with `python manage.py createsuperuser` and
    pass Basic Auth credentials, or log in via /admin/ to get a session cookie.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, patient_id: str) -> Response:
        record = get_object_or_404(PatientRecord, patient_id=patient_id)

        # Write an immutable audit entry for every successful retrieval
        AccessLog.objects.create(
            patient=record,
            accessed_by=request.user if request.user.is_authenticated else None,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        serializer = PatientRetrieveSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)
