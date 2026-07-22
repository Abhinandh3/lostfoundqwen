from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views_auth
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication URLs
    path('signup/', views_auth.signup_view, name='signup'),
    path('login/', views_auth.login_view, name='login'),
    path('logout/', views_auth.logout_view, name='logout'),
    path('profile/', views_auth.profile_view, name='profile'),
    path('dashboard/', views_auth.dashboard_view, name='dashboard'),
    
    # Case URLs
    path('cases/create/', views.create_case, name='case_create'),
    path('cases/', views.case_list, name='case_list'),
    path('cases/<int:pk>/', views.case_detail, name='case_detail'),
    path('cases/<int:case_pk>/report/', views.submit_sighting_report, name='submit_sighting'),
    
    # AI Search URL
    path('ai-search/', views.ai_search, name='ai_search'),
    
    # Detective Workflow URLs
    path('cases/<int:case_pk>/request-detective/', views.request_detective, name='request_detective'),
    path('detective/dashboard/', views.detective_dashboard, name='detective_dashboard'),
    path('detective/accept-request/<int:request_pk>/', views.accept_case_assignment, name='accept_assignment'),
    path('detective/update/<int:assignment_pk>/', views.submit_investigation_update, name='submit_update'),
    path('detective/mark-solved/<int:case_pk>/', views.mark_case_solved, name='mark_solved'),
    
    # Admin Dashboard URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/verify-detective/<int:profile_pk>/', views.verify_detective, name='verify_detective'),
    path('admin/assign-detective/<int:case_pk>/', views.assign_detective_manually, name='assign_detective'),
    
    # API Endpoints
    path('api/map-data/', views.map_data_api, name='map_data_api'),
]
