from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import user_passes_test, login_required
from .forms import AppointmentForm, ReviewForm
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from .models import Appointment, Service, Staff, Review
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum


#==================================================================


#authentication admin panel
def is_owner(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_owner, login_url="login")
def crm_dashboard(request):
    appointments = Appointment.objects.select_related("user", "staff", "service").order_by('-appointment_date')
    completed_appts = appointments.objects.filter(status='completed')
    # get the current date for filtering
    today = completed_appts.timezone.now().date()
    total_revenue = completed_appts.aggregate(
        total=Sum('service__price')['total'] or 0
    )
    weekly_revenue = completed_appts.filter(appointment_date__year=today.year, appointment_date__week = today.week).aggregate(total=Sum('service__price'))['total'] or 0
    monthly_revenue = completed_appts.filter(
        appointment_date__year = today.year
        appointment_date__month = today.month
    ).aggregate(total=Sum('service__price')['total'] or 0)
    daily_revenue = completed_appts.filter(
        appointment_date__date = today
    ).aggregate(total=Sum('service')['total'] or 0) 
    context = {
        "total_revenue": total_revenue,
        "monthly_revenue":monthly_revenue,
        "daily_revenue":daily_revenue,
    }
    return render(request, 'appointments/admin_dashboard.html', context)

@staff_member_required
def admin_dashboard(request):
    appointments = Appointment.objects.select_related("user","staff", "service").order_by('-appointment_date')
    return render(request, "appointments/admin_dashboard.html", {"appointments": appointments})














#===================================================================
#login page
@require_POST
def logout(request):
    auth_logout(request)
    return redirect("login")

def login_or_register(request):
    return render(request, 'appointments/login.html')


# home
@login_required()
def homepage(request):
    serviceobj = Service.objects.all()
    context = {
        "services":serviceobj
    }
    return render(request, "appointments/homepage.html", context)
from django.contrib.auth.decorators import login_required

# READ (list)
@login_required
def appointment_list(request):
    # Filter by the logged-in user, keeping your select_related optimization
    appointments = Appointment.objects.filter(user=request.user).select_related("staff")
    return render(request, "appointments/list.html", {"appointments": appointments})


# READ (single)
def appointment_detail(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, "appointments/detail.html", {"appointment": appointment})


# CREATE
@login_required
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            # 1. Save the form but DON'T commit to the database yet
            appointment = form.save(commit=False)
            
            # 2. Attach the currently logged-in user to the appointment
            appointment.user = request.user
            
            # 3. Now save it to the database
            appointment.save()
            
            messages.success(request, "Your appointment has been booked!")
            return redirect('appointment_list')
    else:
        form = AppointmentForm()
        
    return render(request, 'appointments/form.html', {'form': form})

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



# reviewing form
def rate_staff(request, staff_id):
    staff = get_object_or_404(Staff, pk=staff_id)

    # If this user already reviewed this staff member, edit that review
    review = Review.objects.filter(user=request.user, staff=staff).first()

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.staff = staff
            review.save()
            messages.success(request, f"Thanks! You rated {staff} {review.rating}/5.")
            return redirect("staff_list")  # change to your own URL name
    else:
        form = ReviewForm(instance=review)

    return render(request, "appointments/rate_staff.html", {
        "form": form,
        "staff": staff,
        "title": f"Rate {staff}",
    })
from django.db.models import Avg, Count


def staff_list(request):
    staff_members = list(
        Staff.objects.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews"),
        )
    )

    # Ratings the current user already gave, as {staff_id: rating}
    my_ratings = {}
    if request.user.is_authenticated:
        my_ratings = dict(
            Review.objects.filter(user=request.user)
            .values_list("staff_id", "rating")
        )

    for member in staff_members:
        member.my_rating = my_ratings.get(member.id)

    return render(request, "appointments/staff_list.html", {
        "staff_members": staff_members,
        "title": "Our Staff",
    })

# cancel appointment


@login_required
@require_POST
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, user=request.user)
    deadline = appointment.appointment_date - timedelta(hours=2)

    if appointment.status in ("pending", "confirmed") and timezone.now() < deadline:
        appointment.status = "cancelled"
        appointment.save()
        messages.success(request, "Your appointment has been cancelled.")
    else:
        if appointment.status not in ("pending", "confirmed"):
            messages.error(request, "This appointment can't be cancelled.")
        else:
            messages.error(request, "Cancellations must be made at least 2 hours before the appointment.")

    return redirect("appointment_list")