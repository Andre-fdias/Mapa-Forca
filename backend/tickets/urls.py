from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list_view, name='ticket_list'),
    path('novo/', views.ticket_create_view, name='ticket_create'),
    path('<int:pk>/', views.ticket_detail_view, name='ticket_detail'),
    path('<int:pk>/status/', views.ticket_update_status, name='ticket_update_status'),
]
