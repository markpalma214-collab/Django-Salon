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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="staff_profile", null=True, blank=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=60, blank=True)
    image = models.ImageField(upload_to="staff/")
    number = models.CharField(max_length=20, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        verbose_name_plural = "staff"

    def __str__(self):
        return self.name


class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    description = models.TextField(blank=True)
    starting_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Shown as 'From ₱…' in the Our Services section.",
    )
    tick_popular = models.BooleanField(default=False, verbose_name="Most popular")

    class Meta:
        verbose_name_plural = "service categories"

    def __str__(self):
        return self.name

class AboutSection(models.Model):
    """The About Us block on the homepage. Only one row is used; edit it in the admin."""
    title = models.CharField(max_length=120, default="Where Beauty Meets Relaxation")
    description = models.TextField(
        default="At Michelle's Salon, every visit is a small escape. Our skilled technicians "
                "pair premium products with careful, personal service, so you leave feeling "
                "polished and refreshed."
    )
    image = models.ImageField(upload_to="about/", blank=True)

    years_of_expertise = models.PositiveIntegerField(default=5)
    years_label = models.CharField(max_length=40, default="Years of expertise")
    certified_stylists = models.PositiveIntegerField(default=5)
    certified_label = models.CharField(max_length=40, default="Certified stylists")
    premium_treatments = models.PositiveIntegerField(default=50)
    treatments_label = models.CharField(max_length=40, default="Premium hair treatments")

    class Meta:
        verbose_name = "About section"
        verbose_name_plural = "About section"

    def __str__(self):
        return "About section"

# does the profit come from the service?
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
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True, related_name="appointments")
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

class Expense(models.Model):
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True)
    inventory_item = models.ForeignKey(
        Inventory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchases",
    )
    quantity_added = models.PositiveIntegerField(null=True, blank=True)

class InventoryItem(models.Model):
    name = models.CharField(max_length=100)   # "Hair dye - black"
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20)    # "bottles", "boxes"    

class SiteTestimonial(models.Model):
    """Testimonials about the salon itself. Curated by the admin."""
    author_name = models.CharField(max_length=100)
    author_role = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    tag = models.CharField(max_length=40, blank=True)
    is_published = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-pk"]

    def __str__(self):
        return f"{self.author_name} ({'published' if self.is_published else 'draft'})"

class SiteSettings(models.Model):
    """Brand, footer text and contact details. Only one row is used; edit it in the admin."""
    salon_name = models.CharField(max_length=80, default="Michelle's salon")
    tagline = models.CharField(max_length=60, default="NAIL SALON")
    logo = models.ImageField(upload_to="site/", blank=True,
                             help_text="Leave empty to use the built-in logo.")
    description = models.TextField(
        default="Professional nail care in a relaxing, luxurious environment. "
                "Because you deserve to look and feel amazing."
    )

    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)

    address = models.CharField(max_length=255, blank=True)
    map_link = models.URLField(blank=True, help_text="Optional Google Maps link for the address.")
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    login_banner = models.ImageField(upload_to="site/", blank=True, null=True)
    login_banner_caption = models.CharField(
        max_length=240,
        blank=True,
        default="Professional nail care in a relaxing, luxurious environment. Because you deserve to look and feel amazing.",
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"


class FooterLink(models.Model):
    COLUMN_CHOICES = [("services", "Services column"), ("company", "Company column")]

    column = models.CharField(max_length=10, choices=COLUMN_CHOICES)
    label = models.CharField(max_length=60)
    url = models.CharField(
        max_length=200,
        help_text="A section like #services, a page like /staff/, or a full https:// address.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["column", "sort_order", "pk"]

    def __str__(self):
        return f"{self.get_column_display()}: {self.label}"

