from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class PatientRegistrationTests(APITestCase):
    def test_patient_can_register(self):
        url = reverse("register-patient")
        data = {
            "username": "patient1",
            "email": "patient1@example.com",
            "password": "strongpass123",
            "first_name": "Jane",
            "last_name": "Doe",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="patient1")
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertTrue(user.check_password("strongpass123"))

    def test_patient_registration_does_not_expose_doctor_fields(self):
        url = reverse("register-patient")
        data = {
            "username": "patient2",
            "password": "strongpass123",
            "description": "Should be ignored",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="patient2")
        self.assertEqual(user.description, "")


class DoctorRegistrationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", password="adminpass123", email="admin@example.com"
        )
        self.patient = User.objects.create_user(
            username="patient1", password="strongpass123", role=User.Role.PATIENT
        )

    def _login(self, username, password):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": username, "password": password})
        return response.data["access"]

    def test_admin_can_register_doctor(self):
        token = self._login("admin", "adminpass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("register-doctor")
        data = {
            "username": "doc1",
            "password": "strongpass123",
            "description": "Cardiologist",
            "shift_start": "09:00",
            "shift_end": "17:00",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        doctor = User.objects.get(username="doc1")
        self.assertEqual(doctor.role, User.Role.DOCTOR)
        self.assertEqual(doctor.description, "Cardiologist")

    def test_non_admin_cannot_register_doctor(self):
        token = self._login("patient1", "strongpass123")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("register-doctor")
        data = {"username": "doc2", "password": "strongpass123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_register_doctor(self):
        url = reverse("register-doctor")
        data = {"username": "doc3", "password": "strongpass123"}
        response = self.client.post(url, data)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class JWTRoleClaimTests(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient1", password="strongpass123", role=User.Role.PATIENT
        )
        self.doctor = User.objects.create_user(
            username="doc1", password="strongpass123", role=User.Role.DOCTOR
        )

    def _decode_token_role(self, token):
        import jwt
        # Signature verification skipped here; we only need the payload for this test
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get("role")

    def test_patient_token_contains_role(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": "patient1", "password": "strongpass123"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._decode_token_role(response.data["access"]), "patient")

    def test_doctor_token_contains_role(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": "doc1", "password": "strongpass123"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._decode_token_role(response.data["access"]), "doctor")