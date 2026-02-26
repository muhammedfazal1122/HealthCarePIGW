"""
URL patterns for the patients app.
"""
from django.urls import path

from .views import PatientIntakeView, PatientRetrieveView

app_name = "patients"

urlpatterns = [
    path("patient-intake/", PatientIntakeView.as_view(), name="patient-intake"),
    # patient_id param matches the FHIR Patient.id string (may contain hyphens)
    path("patients/<str:patient_id>/", PatientRetrieveView.as_view(), name="patient-retrieve"),
]
