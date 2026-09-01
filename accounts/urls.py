from django.urls import path
from .views import PatientRegisterView, DoctorRegisterView

urlpatterns = [
    path("register/patient/", PatientRegisterView.as_view(), name="register-patient"),
    path("register/doctor/", DoctorRegisterView.as_view(), name="register-doctor"),
]