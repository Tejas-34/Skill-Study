from django.urls import path
from .views import logout_user, user_profile, send_otp, verify_otp, index, regi, AboutUs, ContactUs, login, Register, create_payment, payment_success, RegisterM

urlpatterns = [

    path('', index, name='index'),

    path('register/', Register.as_view(), name='register'),
    path('login/', login.as_view(), name='login'),
    path('logout/', logout_user, name='logout'),
    path('profile/', user_profile, name='profile'),  # Protected route
    path('send-otp/', send_otp, name='send_otp'),
    path('reg/verify-otp/', verify_otp, name='verify_otp'),
    
    path('reg/', regi, name='regi'),
    path('mregister/', RegisterM, name='mregister'),
    path('about/', AboutUs, name='about'),
    path('contact/', ContactUs, name='contact'),

    path('pay/', create_payment, name='cosmofeed_webhook'),
    path('verPay/', payment_success, name='cosmofeed_webhook'),

    

]
