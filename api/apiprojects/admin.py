from django.contrib import admin
from .models import Staff, Service, Appointment, Review


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
    list_display = ("service_name", "price")
    prepopulated_fields = {"slug": ("service_name",)}


admin.site.register(Appointment)
admin.site.register(Review)