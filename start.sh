#!/bin/sh
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL" || true
python manage.py generate_slots --days 7
exec gunicorn ClinicalBookingSystem.wsgi:application --bind 0.0.0.0:$PORT