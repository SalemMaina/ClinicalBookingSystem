from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Slot, Appointment

User = get_user_model()


class AppointmentsTestBase(APITestCase):
    """Shared setup for appointments tests: one doctor, one patient, one future slot."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            username="doc1", password="testpass123", role=User.Role.DOCTOR,
            description="GP", shift_start="09:00", shift_end="17:00",
        )
        self.patient = User.objects.create_user(
            username="patient1", password="testpass123", role=User.Role.PATIENT,
        )
        self.other_patient = User.objects.create_user(
            username="patient2", password="testpass123", role=User.Role.PATIENT,
        )

        # A slot safely in the future, outside the 1-hour buffer
        self.future_slot = Slot.objects.create(
            doctor=self.doctor, datetime=timezone.now() + timedelta(days=1)
        )
        # A slot inside the 1-hour buffer — should never show as available
        self.buffered_slot = Slot.objects.create(
            doctor=self.doctor, datetime=timezone.now() + timedelta(minutes=30)
        )
        # A slot in the past
        self.past_slot = Slot.objects.create(
            doctor=self.doctor, datetime=timezone.now() - timedelta(days=1)
        )

    def _login(self, username, password="testpass123"):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {"username": username, "password": password})
        return response.data["access"]

    def _auth(self, username):
        token = self._login(username)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class AvailableSlotsTests(AppointmentsTestBase):
    def test_lists_only_available_slots(self):
        self._auth("patient1")
        url = reverse("available-slots")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {slot["id"] for slot in response.data}

        self.assertIn(self.future_slot.id, returned_ids)
        self.assertNotIn(self.buffered_slot.id, returned_ids)
        self.assertNotIn(self.past_slot.id, returned_ids)

    def test_can_filter_by_doctor(self):
        other_doctor = User.objects.create_user(
            username="doc2", password="testpass123", role=User.Role.DOCTOR,
        )
        other_slot = Slot.objects.create(
            doctor=other_doctor, datetime=timezone.now() + timedelta(days=1)
        )

        self._auth("patient1")
        url = reverse("available-slots")
        response = self.client.get(url, {"doctor": self.doctor.id})

        returned_ids = {slot["id"] for slot in response.data}
        self.assertIn(self.future_slot.id, returned_ids)
        self.assertNotIn(other_slot.id, returned_ids)

    def test_anonymous_cannot_list_slots(self):
        url = reverse("available-slots")
        response = self.client.get(url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class BookAppointmentTests(AppointmentsTestBase):
    def test_patient_can_book_available_slot(self):
        self._auth("patient1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": self.future_slot.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.future_slot.refresh_from_db()
        self.assertTrue(self.future_slot.is_booked)

        appointment = Appointment.objects.get(slot=self.future_slot)
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.status, Appointment.Status.BOOKED)

    def test_cannot_book_already_booked_slot(self):
        Appointment.objects.create(slot=self.future_slot, patient=self.other_patient)
        self.future_slot.is_booked = True
        self.future_slot.save()

        self._auth("patient1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": self.future_slot.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_slot_within_buffer(self):
        self._auth("patient1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": self.buffered_slot.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_past_slot(self):
        self._auth("patient1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": self.past_slot.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_doctor_cannot_book_appointment(self):
        self._auth("doc1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": self.future_slot.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_slot_returns_error(self):
        self._auth("patient1")
        url = reverse("book-appointment")
        response = self.client.post(url, {"slot_id": 99999})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MyAppointmentsTests(AppointmentsTestBase):
    def test_patient_sees_only_their_own_appointments(self):
        my_appointment = Appointment.objects.create(slot=self.future_slot, patient=self.patient)
        other_slot = Slot.objects.create(
            doctor=self.doctor, datetime=timezone.now() + timedelta(days=2)
        )
        Appointment.objects.create(slot=other_slot, patient=self.other_patient)

        self._auth("patient1")
        url = reverse("my-appointments")
        response = self.client.get(url)

        returned_ids = {a["id"] for a in response.data}
        self.assertIn(my_appointment.id, returned_ids)
        self.assertEqual(len(response.data), 1)


class CancelAppointmentTests(AppointmentsTestBase):
    def setUp(self):
        super().setUp()
        self.appointment = Appointment.objects.create(slot=self.future_slot, patient=self.patient)
        self.future_slot.is_booked = True
        self.future_slot.save()

    def test_patient_can_cancel_own_appointment(self):
        self._auth("patient1")
        url = reverse("cancel-appointment", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.appointment.refresh_from_db()
        self.future_slot.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)
        self.assertFalse(self.future_slot.is_booked)  # slot reopened

    def test_cannot_cancel_someone_elses_appointment(self):
        self._auth("patient2")
        url = reverse("cancel-appointment", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_cancel_already_cancelled_appointment(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save()

        self._auth("patient1")
        url = reverse("cancel-appointment", kwargs={"pk": self.appointment.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)