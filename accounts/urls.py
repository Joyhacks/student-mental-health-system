from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    # The login view is also the landing page: anonymous visitors see the sign-in
    # form, while authenticated visitors are redirected on to their dashboard.
    path('', views.RateLimitedLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
