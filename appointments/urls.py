from django.urls import path
from .views import AvailableSlotsView, BookAppointmentView, MyAppointmentsView, CancelAppointmentView, MyScheduleView, RescheduleAppointmentView

urlpatterns = [
    path("slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("book/", BookAppointmentView.as_view(), name="book-appointment"),
    path("my-appointments/", MyAppointmentsView.as_view(), name="my-appointments"),
    path("my-schedule/", MyScheduleView.as_view(), name="my-schedule"),
    path("<int:pk>/reschedule/", RescheduleAppointmentView.as_view(), name="reschedule-appointment"),
    path("<int:pk>/cancel/", CancelAppointmentView.as_view(), name="cancel-appointment"),
]