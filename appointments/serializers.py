from rest_framework import serializers
from .models import Slot, Appointment


class SlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)

    class Meta:
        model = Slot
        fields = ["id", "doctor", "doctor_name", "datetime", "is_booked"]
        read_only_fields = ["is_booked"]


class AppointmentSerializer(serializers.ModelSerializer):
    doctor = serializers.CharField(source="slot.doctor.get_full_name", read_only=True)
    slot_datetime = serializers.DateTimeField(source="slot.datetime", read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "slot", "slot_datetime", "doctor", "patient", "status", "created_at"]
        read_only_fields = ["patient", "status", "created_at"]


class BookAppointmentSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()

    def validate_slot_id(self, value):
        if not Slot.objects.available().filter(id=value).exists():
            raise serializers.ValidationError(
                "This slot is not available (already booked, in the past, or within the 1-hour buffer)."
            )
        return value

class RescheduleAppointmentSerializer(serializers.Serializer):
    new_slot_id = serializers.IntegerField()

    def validate_new_slot_id(self, value):
        if not Slot.objects.available().filter(id=value).exists():
            raise serializers.ValidationError(
                "The new slot is not available (already booked, in the past, or within the 1-hour buffer)."
            )
        return value