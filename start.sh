#!/bin/sh
python manage.py collectstatic --noinput
python manage.py migrate
exec gunicorn ClinicalBookingSystem.wsgi:application --bind 0.0.0.0:$PORT