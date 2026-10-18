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
from django.db import IntegrityError, transaction


#==================================================================


#authentication admin panel
def is_owner(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_owner, login_url="login")
def crm_dashboard(request):
    appointments = Appointment.objects.select_related("user", "staff", "service").order_by('-appointment_date')
    completed_appts = appointments.filter(status='completed')
    
    # get the current date for filtering
    today = timezone.now().date()
    
    total_revenue = completed_appts.aggregate(total=Sum('service__price'))['total'] or 0
    
    # Calculate weekly revenue using a date range
    start_of_week = today - timedelta(days=today.weekday())
    weekly_revenue = completed_appts.filter(appointment_date__date__gte=start_of_week).aggregate(total=Sum('service__price'))['total'] or 0
    
    monthly_revenue = completed_appts.filter(
        appointment_date__year=today.year,
        appointment_date__month=today.month
    ).aggregate(total=Sum('service__price'))['total'] or 0
    
    daily_revenue = completed_appts.filter(
        appointment_date__date=today
    ).aggregate(total=Sum('service__price'))['total'] or 0 
    
    context = {
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "daily_revenue": daily_revenue,
        "weekly_revenue": weekly_revenue,
        "appointments": appointments,
    }
    return render(request, 'appointments/main_dashboard.html', context)

@staff_member_required
def admin_dashboard(request):
    appointments = Appointment.objects.select_related("user", "staff", "service").exclude(status='cancelled').order_by('-appointment_date')
    
    context = {
        "appointments": appointments,
        # This tells the HTML to show the form
        "can_manage_status": request.user.is_staff, 
        # This pulls the choices directly from your model
        "status_choices": Appointment.STATUS_CHOICES, 
    }
    
    return render(request, "appointments/admin_dashboard.html", context)


@staff_member_required
@require_POST
def appointment_update_status(request, pk):
    # Find the specific appointment
    appointment = get_object_or_404(Appointment, pk=pk)
    
    # Grab the new status from the dropdown menu in the HTML
    new_status = request.POST.get('status')
    
    # Validate against your model's STATUS_CHOICES before saving
    valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        messages.success(request, f"Status for {appointment.name} updated to {appointment.get_status_display()}.")
    else:
        messages.error(request, "Invalid status selected.")
        
    # Refresh the dashboard page
    return redirect('admin_dashboard')












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
    appointments = Appointment.objects.select_related("staff", "service")
    if not request.user.is_staff:
        appointments = appointments.filter(user=request.user).order_by('-appointment_date')
    return render(request, "appointments/list.html", {
        "appointments": appointments,
        "status_choices": Appointment.STATUS_CHOICES,
        "can_manage_status": request.user.is_staff,
    })


@staff_member_required
@require_POST
def appointment_update_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get('status')
    
    valid_statuses = [choice[0] for choice in Appointment.STATUS_CHOICES]
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        messages.success(request, f"Status for {appointment.name} updated to {appointment.get_status_display()}.")
    else:
        messages.error(request, "Invalid status selected.")
        
    # FIX: Send the user back to the exact URL they submitted the form from
    previous_page = request.META.get('HTTP_REFERER')
    if previous_page:
        return redirect(previous_page)
        
    # Fallback just in case the browser blocks referrer data
    return redirect('admin_dashboard')


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
    # 1. Staff can find any appointment, regular users only find their own
    if request.user.is_staff:
        appointment = get_object_or_404(Appointment, pk=pk)
    else:
        appointment = get_object_or_404(Appointment, pk=pk, user=request.user)
        
    deadline = appointment.appointment_date - timedelta(hours=2)

    # 2. Staff can bypass the 2-hour deadline, regular users cannot
    is_past_deadline = timezone.now() >= deadline
    
    if appointment.status in ("pending", "confirmed"):
        if not request.user.is_staff and is_past_deadline:
            messages.error(request, "Cancellations must be made at least 2 hours before the appointment.")
        else:
            appointment.status = "cancelled"
            appointment.save()
            messages.success(request, "The appointment has been cancelled.")
    else:
        messages.error(request, "This appointment can't be cancelled.")

    # 3. Redirect staff back to dashboard, and regular users back to their list
    if request.user.is_staff:
        return redirect("admin_dashboard")
    return redirect("appointment_list")