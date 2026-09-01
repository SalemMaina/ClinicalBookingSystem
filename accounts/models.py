from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    role = models.CharField(max_length=10, choices=Role.choices)
    description = models.TextField(
        blank=True,
        help_text="Doctor specialization (ignored for patients)",
    )
    shift_start = models.TimeField(default="09:00")
    shift_end = models.TimeField(default="17:00")

    def __str__(self):
        return f"{self.username} ({self.role})"
