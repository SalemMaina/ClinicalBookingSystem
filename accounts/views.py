from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import PatientRegistrationSerializer, DoctorRegistrationSerializer, CustomTokenObtainPairSerializer


class PatientRegisterView(generics.CreateAPIView):
    serializer_class = PatientRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class DoctorRegisterView(generics.CreateAPIView):
    serializer_class = DoctorRegistrationSerializer
    permission_classes = [permissions.IsAdminUser]

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer