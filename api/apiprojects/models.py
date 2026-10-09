from django.db import models
from django.core.validators import MinValueValidator, MaxLengthValidator
from django.conf import settings
# Create your models here.

class Staff(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="staff/")

    class Meta:
        verbose_name_plural = "staff"

    def __str__(self):
        return self.name
    
class Service(models.Model):
    service_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="services/")
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.service_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_name} - ₱{self.price}"

class Appointment(models.Model):
    name = models.CharField(max_length=100)
    staff = models.ForeignKey(
        Staff, on_delete=models.PROTECT, related_name="appointments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    appointment_date = models.DateTimeField()
    note = models.TextField(blank=True)
    class Meta:
        ordering = ["appointment_date"]
    def __str__(self):
                # what it shows on admin panel
                return f"{self.name} with {self.staff} on {self.appointment_date:%Y-%m-%d %H:%M}"



class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    staff = models.ForeignKey(Staff,on_delete=models.CASCADE, related_name="reviews")
    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxLengthValidator(5)]
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
        
