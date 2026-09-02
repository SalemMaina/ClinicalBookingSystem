from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Slot, Appointment
from .serializers import SlotSerializer, AppointmentSerializer, BookAppointmentSerializer


class AvailableSlotsView(generics.ListAPIView):
    serializer_class = SlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Slot.objects.available()
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset


class BookAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != request.user.Role.PATIENT:
            return Response(
                {"detail": "Only patients can book appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data["slot_id"]

        with transaction.atomic():
            try:
                slot = Slot.objects.select_for_update().get(
                    id=slot_id, is_booked=False
                )
            except Slot.DoesNotExist:
                return Response(
                    {"detail": "This slot is no longer available."},
                    status=status.HTTP_409_CONFLICT,
                )

            slot.is_booked = True
            slot.save()
            appointment = Appointment.objects.create(slot=slot, patient=request.user)

        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class MyAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user)


class CancelAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user)
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if appointment.status != Appointment.Status.BOOKED:
            return Response(
                {"detail": "Only booked appointments can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            appointment.status = Appointment.Status.CANCELLED
            appointment.save()
            appointment.slot.is_booked = False
            appointment.slot.save()

        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)

class MyScheduleView(generics.ListAPIView):
    """Doctor-facing view: shows the authenticated doctor's own booked appointments."""
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if request.user.role != request.user.Role.DOCTOR:
            return Response(
                {"detail": "Only doctors can view their schedule."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        return Appointment.objects.filter(
            slot__doctor=self.request.user
        ).exclude(status=Appointment.Status.CANCELLED)