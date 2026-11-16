"""Finance model for the CRM revenue analysis page.

FinancialSummary lists every figure the page shows, so you can see the
variables in one place:

    total_revenue         completed appointments x service price
    total_expenses        sum of Expense.amount dated inside the period
    net_profit            total_revenue - total_expenses
    profit_margin         net_profit / total_revenue, in percent (None if no revenue)
    total_appointments    appointments that are not cancelled
    completed_appointments / total_clients
    months                one MonthlyFinance per month of `year`
    loss_months           the months where expenses were higher than revenue

build_financial_summary() fills it from the database.

Notes
- Expenses come only from the Expense model. Staff salaries are included only
  if you enter them as expenses.
- With a branch selected, only that branch's expenses are counted. Expenses
  saved without a branch show up under "All branches".
"""
import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate, TruncMonth

from .models import Appointment, Expense, Review, Staff

ZERO = Decimal("0")

PERIODS = [
    ("year", "Annual"),
    ("month", "Monthly"),
    ("week", "Weekly"),
    ("today", "Today"),
]


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #

@dataclass
class MonthlyFinance:
    month: date                      # first day of the month
    revenue: Decimal = ZERO
    expenses: Decimal = ZERO

    @property
    def net_profit(self) -> Decimal:
        return self.revenue - self.expenses

    @property
    def is_loss(self) -> bool:
        return self.net_profit < 0

    @property
    def label(self) -> str:
        return f"{self.month:%b %Y}"


@dataclass
class FinancialSummary:
    period_key: str                  # year | month | week | today
    start: date
    end: date
    year: int                        # the year the monthly breakdown covers
    total_revenue: Decimal = ZERO
    total_expenses: Decimal = ZERO
    total_appointments: int = 0
    completed_appointments: int = 0
    total_clients: int = 0
    months: list = field(default_factory=list)

    @property
    def net_profit(self) -> Decimal:
        return self.total_revenue - self.total_expenses

    @property
    def profit_margin(self):
        if not self.total_revenue:
            return None
        return self.net_profit / self.total_revenue * 100

    @property
    def loss_months(self) -> list:
        return [m for m in self.months if m.is_loss]

    @property
    def loss_month_count(self) -> int:
        return len(self.loss_months)


# --------------------------------------------------------------------------- #
# Periods
# --------------------------------------------------------------------------- #

def _fmt(d: date) -> str:
    return f"{d:%b} {d.day}, {d.year}"


def resolve_period(key, today, year=None):
    """Return (start, end) dates for a period key."""
    if key == "today":
        return today, today
    if key == "week":                                   # Monday to Sunday
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if key == "month":                                  # calendar month
        last = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last)
    year = year or today.year                           # annual
    return date(year, 1, 1), date(year, 12, 31)


def period_caption(summary: FinancialSummary) -> str:
    if summary.period_key == "year":
        return str(summary.year)
    if summary.period_key == "today":
        return _fmt(summary.start)
    return f"{_fmt(summary.start)} to {_fmt(summary.end)}"


def available_years(today):
    """Years that have appointments or expenses, newest first."""
    years = [today.year]
    first_appt = (Appointment.objects.order_by("appointment_date")
                  .values_list("appointment_date", flat=True).first())
    first_expense = (Expense.objects.order_by("date")
                     .values_list("date", flat=True).first())
    if first_appt:
        years.append(first_appt.year)
    if first_expense:
        years.append(first_expense.year)
    return list(range(today.year, min(years) - 1, -1))


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def _monthly(year, today, branch):
    appts = Appointment.objects.filter(status="completed", appointment_date__year=year)
    expenses = Expense.objects.filter(date__year=year)
    if branch:
        appts = appts.filter(branch=branch)
        expenses = expenses.filter(branch=branch)

    revenue = {
        _as_date(r["m"]): r["total"] or ZERO
        for r in (appts.annotate(m=TruncMonth("appointment_date"))
                  .values("m").annotate(total=Sum("service__price")).order_by())
    }
    spent = {
        _as_date(r["m"]): r["total"] or ZERO
        for r in (expenses.annotate(m=TruncMonth("date"))
                  .values("m").annotate(total=Sum("amount")).order_by())
    }

    last_month = today.month if year == today.year else 12
    months = []
    for n in range(1, last_month + 1):
        first = date(year, n, 1)
        months.append(MonthlyFinance(first, revenue.get(first, ZERO), spent.get(first, ZERO)))
    return months


def build_financial_summary(period_key, today, branch=None, year=None) -> FinancialSummary:
    start, end = resolve_period(period_key, today, year)

    appts = Appointment.objects.filter(
        appointment_date__date__gte=start, appointment_date__date__lte=end)
    expenses = Expense.objects.filter(date__gte=start, date__lte=end)
    if branch:
        appts = appts.filter(branch=branch)
        expenses = expenses.filter(branch=branch)

    completed = appts.filter(status="completed")
    view_year = start.year if period_key == "year" else today.year

    return FinancialSummary(
        period_key=period_key,
        start=start,
        end=end,
        year=view_year,
        total_revenue=completed.aggregate(t=Sum("service__price"))["t"] or ZERO,
        total_expenses=expenses.aggregate(t=Sum("amount"))["t"] or ZERO,
        total_appointments=appts.exclude(status="cancelled").count(),
        completed_appointments=completed.count(),
        total_clients=completed.aggregate(n=Count("user", distinct=True))["n"] or 0,
        months=_monthly(view_year, today, branch),
    )


# --------------------------------------------------------------------------- #
# Chart data
# --------------------------------------------------------------------------- #

def daily_revenue_series(start, end, today, branch=None):
    """Revenue per day from start to end. Days after today are None (a gap)."""
    qs = Appointment.objects.filter(
        status="completed",
        appointment_date__date__gte=start, appointment_date__date__lte=end)
    if branch:
        qs = qs.filter(branch=branch)

    by_day = {
        r["d"]: float(r["total"] or 0)
        for r in (qs.annotate(d=TruncDate("appointment_date"))
                  .values("d").annotate(total=Sum("service__price")).order_by())
    }

    labels, values = [], []
    day = start
    while day <= end:
        labels.append(f"{day:%b} {day.day}")
        values.append(by_day.get(day, 0.0) if day <= today else None)
        day += timedelta(days=1)
    return {"labels": labels, "values": values, "total": sum(v for v in values if v)}


def service_share(start, end, branch=None, limit=6):
    """Appointments per service (not cancelled), top `limit` plus an Other slice."""
    qs = (Appointment.objects
          .filter(appointment_date__date__gte=start, appointment_date__date__lte=end,
                  service__isnull=False)
          .exclude(status="cancelled"))
    if branch:
        qs = qs.filter(branch=branch)

    rows = list(qs.values("service__service_name")
                .annotate(n=Count("pk")).order_by("-n", "service__service_name"))
    labels = [r["service__service_name"] for r in rows[:limit]]
    counts = [r["n"] for r in rows[:limit]]
    other = sum(r["n"] for r in rows[limit:])
    if other:
        labels.append("Other")
        counts.append(other)
    return {"labels": labels, "counts": counts}


def _reviews_for(branch):
    qs = Review.objects.all()
    if branch:
        # Reviews belong to staff, so a branch's reviews are those of staff who work its appointments.
        qs = qs.filter(staff__in=Appointment.objects.filter(branch=branch).values("staff"))
    return qs


def rating_distribution(branch=None):
    """How many clients gave each star rating (all time, reviews have no date)."""
    qs = _reviews_for(branch)
    by_rating = {
        r["rating"]: r["clients"]
        for r in qs.values("rating").annotate(clients=Count("user", distinct=True)).order_by()
    }
    stats = qs.aggregate(avg=Avg("rating"), reviews=Count("pk"))
    return {
        "labels": ["1 star"] + [f"{n} stars" for n in range(2, 6)],
        "counts": [by_rating.get(n, 0) for n in range(1, 6)],
        "reviews": stats["reviews"],
        "average": round(stats["avg"], 1) if stats["avg"] else None,
    }


def top_rated_staff(branch=None, limit=5):
    qs = Staff.objects.annotate(
        avg_rating=Avg("reviews__rating"), review_count=Count("reviews"),
    ).filter(review_count__gt=0)
    if branch:
        qs = qs.filter(pk__in=Appointment.objects.filter(branch=branch).values("staff"))
    return qs.order_by("-avg_rating", "-review_count", "name")[:limit]