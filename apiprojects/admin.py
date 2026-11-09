from django.contrib import admin
from .models import Staff, Service, Appointment, Review, Branch, ServiceCategory, SiteTestimonial, AboutSection
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
    
admin.site.register(Appointment)
admin.site.register(Review)
