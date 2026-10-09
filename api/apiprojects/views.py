from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AppointmentForm
from .models import Appointment, Service

# home
def homepage(request):
    serviceobj = Service.objects.all()
    context = {
        "services":serviceobj
    }
    return render(request, "appointments/homepage.html", context)
# READ (list)
def appointment_list(request):
    appointments = Appointment.objects.select_related("staff")
    return render(request, "appointments/list.html", {"appointments": appointments})


# READ (single)
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, "appointments/detail.html", {"appointment": appointment})


# CREATE
def appointment_create(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your appointment has been booked!")
            return redirect("appointment_list")
    else:
        form = AppointmentForm()

    return render(request, "appointments/form.html", {"form": form, "title": "Book an Appointment"})


# UPDATE
def appointment_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, "Your appointment has been updated.")
            return redirect("appointment_detail", pk=appointment.pk)
    else:
        form = AppointmentForm(instance=appointment)

    return render(request, "appointments/form.html", {"form": form, "title": "Edit Appointment"})


# DELETE
def appointment_delete(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == "POST":
        appointment.delete()
        messages.success(request, "Your appointment has been cancelled.")
        return redirect("appointment_list")

    return render(request, "appointments/confirm_delete.html", {"appointment": appointment})