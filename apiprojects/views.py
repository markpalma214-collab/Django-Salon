from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import user_passes_test, login_required
from .forms import AppointmentForm, ReviewForm, StaffForm
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.db import IntegrityError, transaction
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegisterForm
from django.db.models import Sum, Count, Q, Avg, ProtectedError
from .models import Appointment, Service, Staff, Review, Branch, Expense, ServiceCategory, SiteTestimonial, AboutSection, FooterLink, SiteSettings 
from .forms import ServiceForm   # add to your existing "from .forms import ..." line
from django.core.exceptions import PermissionDenied


# ================================================================= #
# authentication section

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")  # change to your own URL name

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("home")
    else:
        form = RegisterForm()

    return render(request, "appointments/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("homepage")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Respect the "Remember me" checkbox
            if not request.POST.get("remember"):
                request.session.set_expiry(0)
            messages.success(request, f"Welcome back, {user.username}!")

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("homepage")
    else:
        form = AuthenticationForm()

    return render(request, "appointments/login.html", {
        "form": form,
        **_landing_context(),
    })








#==================================================================


#authentication admin panel
def is_owner(user):
    return user.is_authenticated and user.is_superuser

def is_staff(user):
    return user.is_authenticated and Staff.objects.filter(user=user).exists()
def can_view_dashboard(user):
    return is_owner(user) or is_staff(user)

@user_passes_test(can_view_dashboard, login_url="login")
def crm_dashboard(request):
    DASH_RANGES = [
    ("today", "Today"),
    ("week", "Last 7 days"),
    ("month", "Last 30 days"),
    ("year", "Last year"),
    ("all", "All time"),
]
    
    print(request.user, request.user.is_superuser, request.user.is_staff)
    if is_owner(request.user):
        reviews = Review.objects.all() # the owner can see all reviews
    else:
        reviews = Review.objects.filter(staff__user=request.user)
    stats = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    avg_rating = stats["avg"] or 0
    total_reviews = stats["count"]

    appointments = Appointment.objects.select_related("user", "staff", "service").order_by('-appointment_date')
    completed_appts = appointments.filter(status='completed')
    clients = completed_appts.aggregate(client=Count("user", distinct=True))["client"] 
    
    # get the current date for filtering
    today = timezone.localdate()

    
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
        # ----- Chart filters -----
    range_key = request.GET.get("range", "month")
    if range_key not in dict(DASH_RANGES):
        range_key = "month"

    branches = Branch.objects.order_by("name")
    picked = request.GET.get("branch", "")
    selected_branch = branches.filter(pk=picked).first() if picked.isdigit() else None

    period = {} if range_key == "all" else _range_filter(range_key, today)
    scope = Appointment.objects.filter(**period)

    # ----- Bar chart: every branch, revenue (completed) vs appointments (not cancelled) -----
    stats = {
        row["branch"]: row
        for row in scope.values("branch").annotate(
            revenue=Sum("service__price", filter=Q(status="completed")),
            appt_count=Count("pk", filter=~Q(status="cancelled")),
        ).order_by()
    }
    branch_chart = {
        "labels": [b.name for b in branches],
        "revenue": [float(stats.get(b.pk, {}).get("revenue") or 0) for b in branches],
        "appointments": [stats.get(b.pk, {}).get("appt_count") or 0 for b in branches],
    }

    # ----- Doughnut: most booked services (one branch if picked, otherwise all) -----
    service_scope = scope.exclude(status="cancelled").filter(service__isnull=False)
    if selected_branch:
        service_scope = service_scope.filter(branch=selected_branch)
    top_services = (service_scope.values("service__service_name")
                    .annotate(total=Count("pk")).order_by("-total")[:6])
    service_chart = {
        "labels": [s["service__service_name"] for s in top_services],
        "counts": [s["total"] for s in top_services],
    }
    
    context = {
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "daily_revenue": daily_revenue,
        "weekly_revenue": weekly_revenue,
        "appointments": appointments,
        "average_rating":avg_rating,
        "total_reviews": total_reviews,
        "total_clients": clients,
        "branches": branches,
        "selected_branch": selected_branch,
        "date_ranges": DASH_RANGES,
        "range_key": range_key,
        "branch_chart": branch_chart,
        "service_chart": service_chart,
    }
    return render(request, 'crm_dashboard/dashboard.html', context)

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

# admin views for navigation bars


from django.contrib import messages
from django.urls import reverse
from .forms import BranchForm
from .models import Appointment, Service, Staff, Review, Branch, Expense

DATE_RANGES = [
("today", "Today"),
("yesterday", "Yesterday"),
("week", "Last 7 days"),
("month", "Last 30 days"),
("year", "Last year"),
("upcoming", "Upcoming"),
]

def _range_filter(key, today):
    """Turn a range name into an ORM filter on the appointment date."""
    if key == "yesterday":
        return {"appointment_date__date": today - timedelta(days=1)}
    if key in ("week", "month", "year"):
        days = {"week": 6, "month": 29, "year": 364}[key]
        return {
            "appointment_date__date__gte": today - timedelta(days=days),
            "appointment_date__date__lte": today,
        }
    if key == "upcoming":
        return {"appointment_date__date__gt": today}
    return {"appointment_date__date": today}


@staff_member_required
def branch_management(request):

    
    
    branches = Branch.objects.all().order_by("name")

    selected = request.GET.get("branch", "")
    branch = branches.filter(pk=selected).first() if selected.isdigit() else None
    branch = branch or branches.first()

    edit_form = BranchForm(instance=branch, prefix="edit") if branch else None
    create_form = BranchForm(prefix="create")
    force_tab = ""   # which tab to open when the page reloads after a failed save

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "edit" and branch:
            edit_form = BranchForm(request.POST, request.FILES, instance=branch, prefix="edit")
            if edit_form.is_valid():
                saved = edit_form.save()
                messages.success(request, f"{saved.name} updated.")
                return redirect(f"{reverse('crm_branches')}?branch={saved.pk}#edit")
            force_tab = "edit"

        elif action == "create":
            create_form = BranchForm(request.POST, request.FILES, prefix="create")
            if create_form.is_valid():
                saved = create_form.save()
                messages.success(request, f"{saved.name} created.")
                return redirect(f"{reverse('crm_branches')}?branch={saved.pk}#current")
            force_tab = "create"

    # ----- Current branch tab: today's numbers + pending appointments -----
        # ----- Current branch tab: today's cards + appointment table -----
    today = timezone.localdate()

    range_key = request.GET.get("range", "today")
    if range_key not in dict(DATE_RANGES):
        range_key = "today"

    status = request.GET.get("status", "all")
    if status != "all" and status not in dict(Appointment.STATUS_CHOICES):
        status = "all"

    try:
        limit = max(5, int(request.GET.get("limit", 5)))
    except ValueError:
        limit = 5

    daily_revenue = daily_expenses = 0
    daily_appointments = rows_total = 0
    rows = []

    if branch:
        todays = branch.appointments.filter(appointment_date__date=today)
        daily_revenue = todays.filter(status="completed").aggregate(
            total=Sum("service__price"))["total"] or 0
        daily_expenses = Expense.objects.filter(branch=branch, date=today).aggregate(
            total=Sum("amount"))["total"] or 0
        daily_appointments = todays.exclude(status="cancelled").count()

        rows_qs = (branch.appointments
                   .filter(**_range_filter(range_key, today))
                   .select_related("service", "staff"))
        if status != "all":
            rows_qs = rows_qs.filter(status=status)

        # soonest first for today/upcoming, newest first for past ranges
        order = "appointment_date" if range_key in ("today", "upcoming") else "-appointment_date"
        rows_qs = rows_qs.order_by(order)
        rows_total = rows_qs.count()
        rows = rows_qs[:limit]

    context = {
        "branches": branches,
        "branch": branch,
        "edit_form": edit_form,
        "create_form": create_form,
        "force_tab": force_tab,
        "daily_revenue": daily_revenue,
        "daily_profit": daily_revenue - daily_expenses,
        "daily_appointments": daily_appointments,
        "rows": rows,
        "rows_total": rows_total,
        "has_more": rows_total > limit,
        "next_limit": limit + 5,
        "date_ranges": DATE_RANGES,
        "range_key": range_key,
        "status": status,
        "status_choices": Appointment.STATUS_CHOICES,
    }
    return render(request, "crm_dashboard/branch.html", context)

# ===================== CRM: services =====================

@staff_member_required
def service_list(request):
    services = list(
        Service.objects.select_related("category")
        .annotate(appt_count=Count("appointment", filter=~Q(appointment__status="cancelled")))
        .order_by("-pk")   # newest first (Service has no created_at field)
    )

    # Reviews belong to technicians, so a service's rating is the average rating
    # of the technicians who have performed it.
    staff_avg = {
        row["staff"]: row["avg"]
        for row in Review.objects.values("staff").annotate(avg=Avg("rating")).order_by()
    }
    ratings = {}
    pairs = (Appointment.objects.exclude(status="cancelled")
             .values_list("service_id", "staff_id").order_by().distinct())
    for service_id, staff_id in pairs:
        if staff_id in staff_avg:
            ratings.setdefault(service_id, []).append(staff_avg[staff_id])
    for s in services:
        vals = ratings.get(s.pk)
        s.rating = round(sum(vals) / len(vals), 1) if vals else None

    categories = ServiceCategory.objects.annotate(n=Count("services")).order_by("name")

    return render(request, "crm_dashboard/services.html", {
        "services": services,
        "categories": categories,
        "total": len(services),
    })


@staff_member_required
def service_form_view(request, pk=None):
    """One view for both creating (no pk) and editing (pk)."""
    service = get_object_or_404(Service, pk=pk) if pk else None
    form = ServiceForm(request.POST or None, request.FILES or None, instance=service)

    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"{saved.service_name} {'updated' if service else 'created'}.")
        return redirect("crm_services")

    return render(request, "crm_dashboard/service_form.html", {"form": form, "service": service})


@staff_member_required
@require_POST
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    name = service.service_name
    try:
        service.delete()
        messages.success(request, f"{name} deleted.")
    except ProtectedError:
        messages.error(request, f"{name} can't be deleted because appointments already use it. Edit it instead.")
    return redirect("crm_services")

# ===================== CRM: staff overview =====================

def _rating_status(avg):
    """Badge shown on a staff card, derived from the average rating."""
    if avg is None:
        return "N/A", "na"
    if avg >= 4.5:
        return "Excellent", "excellent"
    if avg >= 3.5:
        return "Good", "good"
    return "Fair", "fair"


@user_passes_test(can_view_dashboard, login_url="login")
def staff_overview(request):
    # One multi-valued join (reviews), so Avg and Count are safe together
    staff_members = list(
        Staff.objects
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
        .order_by("-pk")   # newest first
    )

    # Revenue per staff member: completed appointments only, one grouped query
    revenue = {
        row["staff"]: row["total"]
        for row in (Appointment.objects.filter(status="completed")
                    .values("staff").annotate(total=Sum("service__price")).order_by())
    }
    for s in staff_members:
        s.revenue = revenue.get(s.pk) or 0
        s.status_label, s.status_key = _rating_status(s.avg_rating)

    return render(request, "crm_dashboard/staff_overview.html", {
        "staff_members": staff_members,
        "can_manage": is_owner(request.user),
    })


@user_passes_test(can_view_dashboard, login_url="login")
def staff_detail(request, pk):
    member = get_object_or_404(
        Staff.objects.annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews")),
        pk=pk,
    )
    appts = Appointment.objects.filter(staff=member)
    total_appointments = appts.exclude(status="cancelled").count()
    total_clients = appts.filter(status="completed").aggregate(
        n=Count("user", distinct=True))["n"]

    status_label, status_key = _rating_status(member.avg_rating)

    return render(request, "crm_dashboard/staff_detail.html", {
        "member": member,
        "status_label": status_label,
        "status_key": status_key,
        "total_appointments": total_appointments,
        "total_clients": total_clients,
        "reviews": member.reviews.select_related("user").order_by("-pk"),  # newest first
        "can_manage": is_owner(request.user),
    })


@login_required
def staff_edit(request, pk):
    if not is_owner(request.user):
        raise PermissionDenied
    member = get_object_or_404(Staff, pk=pk)
    form = StaffForm(request.POST or None, request.FILES or None, instance=member)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{member.name} updated.")
        return redirect("crm_staff_detail", pk=member.pk)

    return render(request, "crm_dashboard/staff_form.html", {"form": form, "member": member})


@login_required
@require_POST
def staff_delete(request, pk):
    if not is_owner(request.user):
        raise PermissionDenied
    member = get_object_or_404(Staff, pk=pk)
    name = member.name
    try:
        member.delete()
        messages.success(request, f"{name} deleted.")
    except ProtectedError:
        messages.error(request, f"{name} can't be deleted because appointments are linked to them.")
    return redirect("crm_staff")

# ===================== Reviews (customer site) =====================

def _reviews_context():
    """Data for the reviews section on the homepage."""
    return {
        "testimonials": SiteTestimonial.objects.filter(is_published=True).order_by("sort_order", "-pk")[:3],
        "client_reviews": Review.objects.select_related("user", "staff").order_by("-pk")[:12],  # newest 12
    }


@login_required
def review_create(request):
    staff_members = list(
        Staff.objects
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
        .order_by("name")
    )

    # This user's existing reviews, so the form can pre-fill when they pick that staff member
    mine = {r.staff_id: r for r in Review.objects.filter(user=request.user)}
    for s in staff_members:
        existing = mine.get(s.pk)
        s.my_rating = existing.rating if existing else ""
        s.my_message = existing.message if existing else ""

    selected_id = request.GET.get("staff", "")
    form = ReviewForm()

    if request.method == "POST":
        selected_id = request.POST.get("staff", "")
        member = next((s for s in staff_members if str(s.pk) == selected_id), None)
        if member is None:
            messages.error(request, "Please choose a staff member to review.")
        else:
            form = ReviewForm(request.POST, instance=mine.get(member.pk))
            if form.is_valid():
                review = form.save(commit=False)
                review.user = request.user
                review.staff = member
                review.save()
                messages.success(request, f"Thanks! You rated {member.name} {review.rating}/5.")
                return redirect(f"{reverse('homepage')}#reviews")

    return render(request, "appointments/review_form.html", {
        "staff_members": staff_members,
        "form": form,
        "selected_id": selected_id,
    })

#==========================================================


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
    if request.user.is_authenticated:
        return redirect("homepage")
    return render(request, "appointments/login.html", _landing_context())


# home
@login_required()
def homepage(request):
    serviceobj = Service.objects.all()
    branch = Branch.objects.filter(is_active=True)
    forms = AppointmentForm()
    active_appointment = (
        Appointment.objects
        .filter(user=request.user, status__in=["pending", "confirmed"])
        .select_related("staff", "service", "branch")
        .order_by("appointment_date")
        .first()
    )
    context = {
        "services": serviceobj,
        "branch": branch,
        "form": forms,
        "active_appointment": active_appointment,
    }
    context.update(_reviews_context())
    context.update(_landing_context())
    return render(request, "appointments/homepage.html", context)

def _landing_context():
    """Our Services, About Us, navbar and footer data for the homepage."""
    return {
        "categories": ServiceCategory.objects.order_by("-tick_popular", "name"),
        "about": AboutSection.objects.first() or AboutSection.objects.create(),
        "site": SiteSettings.objects.first() or SiteSettings.objects.create(),
        "footer_services": FooterLink.objects.filter(column="services", is_active=True),
        "footer_company": FooterLink.objects.filter(column="company", is_active=True),
    }



from django.contrib.auth.decorators import login_required

# READ (list) - only the logged-in user's own appointments
@login_required
def appointment_list(request):
    user_appointments = list(
        Appointment.objects
        .filter(user=request.user)
        .select_related("staff", "service", "branch")
        .order_by("-appointment_date")
    )

    # Prefer the user's active (pending/confirmed) appointment, or fall back to their most recent one
    appointment = next(
        (a for a in user_appointments if a.status in ("pending", "confirmed")),
        user_appointments[0] if user_appointments else None,
    )

    can_cancel = False
    is_active = False
    past_deadline = False
    deadline = None
    staff_stats = {"avg": None, "count": 0}

    if appointment:
        deadline = appointment.appointment_date - timedelta(hours=2)
        is_active = appointment.status in ("pending", "confirmed")
        past_deadline = timezone.now() >= deadline
        can_cancel = is_active and (request.user.is_staff or not past_deadline)

        if appointment.staff_id:
            staff_stats = Review.objects.filter(staff_id=appointment.staff_id).aggregate(
                avg=Avg("rating"),
                count=Count("id"),
            )

    context = {
        "appointment": appointment,
        "appointments": user_appointments,
        "can_cancel": can_cancel,
        "is_active": is_active,
        "past_deadline": past_deadline,
        "deadline": deadline,
        "staff_avg": staff_stats["avg"],
        "staff_review_count": staff_stats["count"],
    }
    return render(request, "appointments/list.html", context)

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
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.user = request.user
            try:
                appointment.save()
            except IntegrityError:
                form.add_error(
                    None,
                    "You already have an active appointment. You can book again once it's completed or cancelled.",
                )
            else:
                messages.success(request, "Your appointment has been booked!")
                return redirect("appointment_list")
    else:
        form = AppointmentForm()

    active_appointment = (
        Appointment.objects
        .filter(user=request.user, status__in=["pending", "confirmed"])
        .select_related("staff", "service", "branch")
        .order_by("appointment_date")
        .first()
    )

    return render(request, "appointments/homepage.html", {
        "form": form,
        "services": Service.objects.all(),
        "branch": Branch.objects.filter(is_active=True),
        "active_appointment": active_appointment,
        **_reviews_context(),
        **_landing_context(),
    })

# UPDATE
@login_required
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

# CANCEL
@login_required
@require_POST
def cancel_appointment(request, pk):
    # Staff can find any appointment, regular users only their own
    if request.user.is_staff:
        appointment = get_object_or_404(Appointment, pk=pk)
    else:
        appointment = get_object_or_404(Appointment, pk=pk, user=request.user)

    deadline = appointment.appointment_date - timedelta(hours=2)
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

    if request.user.is_staff:
        return redirect("admin_dashboard")
    return redirect("appointment_list")

# reviewing form
@login_required
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
    staff_members = Staff.objects.annotate(
        average_rating = Avg("reviews__rating"),
        review_count = Count("reviews")
    )
    return render(request, "appointments/staff_list.html", {
        "staff_members": staff_members,
        "title": "Our Staff",
    })

# cancel appointment


@login_required
def appointment_detail(request, pk):
    # Staff can view any appointment, regular users only their own
    if request.user.is_staff:
        appointment = get_object_or_404(
            Appointment.objects.select_related("staff", "service", "branch"), pk=pk
        )
    else:
        appointment = get_object_or_404(
            Appointment.objects.select_related("staff", "service", "branch"),
            pk=pk, user=request.user,
        )

    # Same rules as cancel_appointment, so the button only shows when cancelling would work
    deadline = appointment.appointment_date - timedelta(hours=2)
    is_active = appointment.status in ("pending", "confirmed")
    past_deadline = timezone.now() >= deadline
    can_cancel = is_active and (request.user.is_staff or not past_deadline)

    context = {
        "appointment": appointment,
        "can_cancel": can_cancel,
        "is_active": is_active,
        "past_deadline": past_deadline,
        "deadline": deadline,
    }
    return render(request, "appointments/detail.html", context)