from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.db.models import Q

phone_validator = RegexValidator(
    regex=r"^\d{11}$",
    message="Phone number must be exactly 11 digits (example: 09123456789).",
)
# Create your models here.

class Staff(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="staff/")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        verbose_name_plural = "staff"

    def __str__(self):
        return self.name


class ServiceCategory(models.Model):
     name = models.CharField(max_length=50, unique=True)
     def __str__(self):
          return self.name     
     
class Service(models.Model):
    service_name = models.CharField(max_length=100)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services", null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="services/")
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.service_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_name} - ₱{self.price}"

class Branch(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    image = models.ImageField(upload_to="branches/")
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    map_link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "branches"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Appointment(models.Model):
    user = models.ForeignKey(
         settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
         related_name="appointments", null=True, blank=True
    )
    STATUS_CHOICES = [
         ("pending", "Pending"),
         ("completed", "Completed"),
         ("confirmed", "Confirmed"),
         ("cancelled", "Cancelled"),
         ("no_show", "No_show"),
    ]
    name = models.CharField(max_length=100)
    staff = models.ForeignKey(
        Staff, on_delete=models.PROTECT, related_name="appointments"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    appointment_date = models.DateTimeField()
    phone_number = models.CharField(
            max_length=11,
            validators=[phone_validator],
            null=True, blank=True,  
        )   
    note = models.TextField(blank=True)
    class Meta:
        ordering = ["appointment_date"]
        constraints = [
             models.UniqueConstraint(
                  fields=["user"],
                  condition = models.Q(status__in=["pending", 'confirmed']),
                  name="one_active_appointment_per_user",
             )
        ]
    def __str__(self):
                # what it shows on admin panel
                return f"{self.name} with {self.staff} on {self.appointment_date:%Y-%m-%d %H:%M}"



class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    staff = models.ForeignKey(Staff,on_delete=models.CASCADE, related_name="reviews")
    message = models.TextField()
    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ["user","staff"],
                name = "unique_review_per_user_staff"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="rating_between_1_and_5",
            )]
    def __str__(self):
        return f"{self.user} rated {self.staff}: {self.rating}/5"


class Inventory(models.Model):
     name = models.OneToOneField(Service, on_delete=models.CASCADE)
     quantity = models.PositiveIntegerField(default=0)
     category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
     def __str__(self):
          return f"STOCK FOR {self.name}: {self.quantity}"



     