from django.urls import path
from .views import logout_user, user_profile, VerifyOTP, index, regi, AboutUs, ContactUs, login, Register, CreatePayment, validate_payment,resend_otp,validate,CallPaymentAPI

from .views import dashboard , earnings_summary,get_last_7_days_sales, my_profile, update_profile , get_user_details, update_kyc,get_kyc_details,change_password,header_user,leaderboard


urlpatterns = [

    path('', index, name='index'),

    path('register/<int:pkg>', Register.as_view(), name='register'),
    path('login/', login.as_view(), name='login'),
    path('logout/', logout_user, name='logout'),

    path('verify-otp/', VerifyOTP.as_view(), name='verify_otp'),
    path('reg/', regi, name='regi'),
    path('about/', AboutUs, name='about'),
    path('contact/', ContactUs, name='contact'),
    path('payment/<int:pkg>', CreatePayment.as_view(), name='create_payment'),
    path('varPay/', validate, name='cosmofeed_success'),
    path('Pay/', validate_payment, name='cosmofeed_success'),
    path('dashboard/', dashboard, name='dashboard'),
    path('call_payment_api/', CallPaymentAPI.as_view(), name='call_payment_api'),
    path('resend-otp/', resend_otp, name='resend_otp'),



    path('earnings_summary/', earnings_summary, name='earnings_summary'),
    path('get_last_7_days_sales/', get_last_7_days_sales, name='get_last_7_days_sales'),
    path('my_profile/' , my_profile , name = 'my_profile'),
    path('update_profile/', update_profile, name = 'update_profile'),
    path('get_user_details/', get_user_details, name = 'get_user_details'),
    path('update_kyc/', update_kyc, name = 'update_kyc'),
    path('get_kyc_details/', get_kyc_details, name = 'get_kyc_details'),
    path('change_password/', change_password, name = 'change_password'),
    path('header_user/',header_user , name = "header_user"),
    path('leaderboard/',leaderboard, name = 'leaderboard')



]
