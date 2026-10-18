from django.urls import path
from . import views
urlpatterns = [
    path('appointment/<int:pk>/update-status/', views.appointment_update_status, name='appointment_update_status'),
    path('salon/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('crm/dashboard/', views.crm_dashboard, name='crm_dashboard'),
    path("logout/", views.logout, name="logout"),
    path("login/", views.login_or_register, name="login"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/<int:staff_id>/rate/", views.rate_staff, name="rate_staff"),    
    path("home/", views.homepage, name="homepage"),
    path("", views.appointment_list, name="appointment_list"),
    path("appointments/new/", views.appointment_create, name="appointment_create"),
    path("appointments/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path("appointments/<int:pk>/edit/", views.appointment_update, name="appointment_update"),
    path("appointments/<int:pk>/status/", views.appointment_update_status, name="appointment_update_status"),
    path('appointment/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path("appointments/<int:pk>/delete/", views.appointment_delete, name="appointment_delete"),

]