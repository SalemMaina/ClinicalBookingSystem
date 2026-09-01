from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Slot

User = get_user_model()


class Command(BaseCommand):
    help = "Generate 30-minute appointment slots for all doctors over a date range."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=7,
            help="Number of days ahead to generate slots for (default: 7)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        doctors = User.objects.filter(role=User.Role.DOCTOR)

        if not doctors.exists():
            self.stdout.write(self.style.WARNING("No doctors found. Nothing to generate."))
            return

        today = timezone.localdate()
        created_count = 0

        for doctor in doctors:
            for day_offset in range(days):
                day = today + timedelta(days=day_offset)
                current = timezone.make_aware(
                    datetime.combine(day, doctor.shift_start)
                )
                end = timezone.make_aware(
                    datetime.combine(day, doctor.shift_end)
                )

                while current < end:
                    _, created = Slot.objects.get_or_create(
                        doctor=doctor, datetime=current
                    )
                    if created:
                        created_count += 1
                    current += timedelta(minutes=30)

        self.stdout.write(
            self.style.SUCCESS(f"Generated {created_count} new slot(s) for {doctors.count()} doctor(s).")
        )