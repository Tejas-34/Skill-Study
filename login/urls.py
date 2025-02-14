from django.urls import path
from .views import logout_user, user_profile, VerifyOTP, index, regi, AboutUs, ContactUs, login, Register, CreatePayment, validate_payment,resend_otp,validate,CallPaymentAPI

urlpatterns = [

    path('', index, name='index'),

    path('register/<int:pkg>', Register.as_view(), name='register'),
    path('login/', login.as_view(), name='login'),
    path('logout/', logout_user, name='logout'),
    path('profile/', user_profile, name='profile'),  # Protected route
    path('verify-otp/', VerifyOTP.as_view(), name='verify_otp'),
    
    path('reg/', regi, name='regi'),
    path('about/', AboutUs, name='about'),
    path('contact/', ContactUs, name='contact'),
    path('payment/<int:pkg>', CreatePayment.as_view(), name='create_payment'),
    path('varPay/', validate, name='cosmofeed_success'),
    path('Pay/', validate_payment, name='cosmofeed_success'),

    path('dashboard/', user_profile, name='dashboard'),
    path('call_payment_api/', CallPaymentAPI.as_view(), name='call_payment_api'),
    





    path('resend-otp/', resend_otp, name='resend_otp'),
]
