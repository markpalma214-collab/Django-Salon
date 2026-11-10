from django.contrib import admin
from .models import Staff, Service, Appointment, Review, Branch, ServiceCategory, SiteTestimonial, AboutSection, FooterLink, SiteSettings
from django import forms
from django.db import models

class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser



@admin.register(Staff)
class StaffAdmin(SuperuserOnlyAdmin):
    list_display = ("name",)


   
@admin.register(Service)
class ServiceAdmin(SuperuserOnlyAdmin):
    list_display = ("service_name", "category", "price")
    prepopulated_fields = {"slug": ("service_name",)}
    list_filter = ("category",)
    search_fields = ("service_name",)
    ordering = ("category__name", "service_name")

    
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TimeField: {
            "widget": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
        },
    }

@admin.register(SiteTestimonial)
class SiteTestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "author_role", "location", "rating", "is_published", "sort_order")
    list_editable = ("is_published", "sort_order")
    list_filter = ("is_published", "rating")
    search_fields = ("author_name", "quote")

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "starting_price", "tick_popular")
    list_editable = ("starting_price", "tick_popular")


@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not AboutSection.objects.exists()      # keep it to a single row

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Brand", {"fields": ("salon_name", "tagline", "logo", "description")}),
        ("Social links", {"fields": ("facebook_url", "instagram_url", "tiktok_url")}),
        ("Contact details", {"fields": ("address", "map_link", "phone", "email")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()      # one row only

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "column", "url", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("column", "is_active")


admin.site.register(Appointment)
admin.site.register(Review)
