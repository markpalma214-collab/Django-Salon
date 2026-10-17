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
    list_display = ("service_name", "category", "price")
    prepopulated_fields = {"slug": ("service_name",)}
    list_filter = ("category",)
    search_fields = ("service_name",)
    ordering = ("category__name", "service_name")
    


admin.site.register(Appointment)
admin.site.register(Review)