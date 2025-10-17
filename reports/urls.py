"""
URL configuration for reports app
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('system-usage/', views.system_usage_report, name='system_usage'),
    path('lab-utilization/', views.lab_utilization_report, name='lab_utilization'),
    path('computer-inventory/', views.computer_inventory_report, name='computer_inventory'),
    path('attendance/', views.attendance_report, name='attendance'),
]
