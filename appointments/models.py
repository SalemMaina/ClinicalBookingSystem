from django.conf import settings
from django.db import models
from django.utils import timezone


class SlotQuerySet(models.QuerySet):
    def available(self):
        buffer_time = timezone.now() + timezone.timedelta(hours=1)
        return self.filter(is_booked=False, datetime__gte=buffer_time)


class Slot(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "doctor"},
        related_name="slots",
    )
    datetime = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    objects = SlotQuerySet.as_manager()

    class Meta:
        unique_together = ("doctor", "datetime")
        ordering = ["datetime"]

    def __str__(self):
        return f"{self.doctor} @ {self.datetime}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    slot = models.OneToOneField(Slot, on_delete=models.CASCADE, related_name="appointment")
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "patient"},
        related_name="appointments",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} -> {self.slot} ({self.status})"