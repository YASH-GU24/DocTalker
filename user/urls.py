from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth.views import (PasswordResetView, PasswordResetDoneView, 
                                       PasswordResetConfirmView, PasswordResetCompleteView)



urlpatterns = [
    path("register/",views.register,name="register"),
    path("dashboard/",views.dashboard,name="dashboard"),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('upload_from_csv/', views.upload_from_csv, name='upload_from_csv'),
    path('add_data_from_csv/', views.add_data_from_csv, name='add_data_from_csv'),
    path('add_from_files/', views.add_from_files, name='add_from_files'),
    path('chat/', views.get_answer, name='get_answer'),
    path('namespaces/', views.get_namespaces, name='get_namespace'),
    path('library_manager/', views.library_manager, name='library_manager'),
    path('modify_data/', views.modify_data, name='modify_data'),
    path('get_chat_history/', views.get_chat_history, name='get_chat_history'),
    path('reset_chat_history/', views.reset_chat_history, name='reset_chat_history'),
    path('password_reset/', PasswordResetView.as_view(
        template_name='user/password_reset.html',
        success_url=reverse_lazy('password_reset_done'),
        email_template_name='user/password_reset_email.html'  # this is the email template
    ), name='password_reset'),

    path('password_reset/done/', PasswordResetDoneView.as_view(
        template_name='user/password_reset_done.html'
    ), name='password_reset_done'),

    path('password_reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='user/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),

    path('password_reset/complete/', PasswordResetCompleteView.as_view(
        template_name='user/password_reset_complete.html'
    ), name='password_reset_complete'),
]
