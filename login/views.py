from wtforms import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, RefreshTokenStore, Profile, KYC,OTP, Payment, Earning, Withdraw
from .serializers import UserSerializer, KYCSerializer
from .utils import send_otp_email, make_referal_id
from django.shortcuts import render
import requests
from django.shortcuts import redirect
from rest_framework.views import APIView
import bcrypt
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
from rest_framework_simplejwt.authentication import JWTAuthentication
from environ import Env



def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    RefreshTokenStore.objects.update_or_create(user=user, defaults={'token': str(refresh)})
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }



@api_view(['GET'])
@permission_classes([AllowAny])
def index(request):
    return render(request, 'index.html')




#-------------------------- login ----------------------------

class login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
            email = request.data.get("email")
            password = request.data.get("password").encode('utf-8')  # Convert input password to bytes

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"error": "Invalid credentials"}, status=400)
            
            if(user.is_verified == False):
                user.delete()
                return render(request, 'login.html', {"error": "Invalid credentials"})

            stored_password = user.password.encode('utf-8')  # Convert stored hash to bytes

            # Check if the password matches the stored hash
            if not bcrypt.checkpw(password, stored_password):  
                return Response({"error": "Invalid credentials"}, status=400)

            if Payment.objects.filter(user=user).exists() and Payment.objects.get(user=user).status == "pending":
                    try:
                        payment = Payment.objects.get(user=user)
                        # Prepare payload for the external API
                        env = Env()
                        Env.read_env()
                        ACCOUNT_ID=env('ACCOUNT_ID')
                        ACCOUNT_SECRET=env('ACCOUNT_SECRET')      
                        payload = {
                            "fetch_payment": {
                                "account_id" : ACCOUNT_ID,
                                "secret_key" : ACCOUNT_SECRET,
                                "payment_id" : payment.payment_id,
                            }
                        }
                        # External API URL
                        url = "https://zerotize.in/api_payment_status"

                        # Make POST request to external API
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(url, json=payload, headers=headers)
                        if response.status_code == 200:
                            data = response.json()['data'][0]
                            print(data['utr'])

                            if(data['utr'] == None):
                                user.paid = False
                                payment.delete()
                                return Response({"error": "Payment failed"}, status=400)



                            if(data['payment_status'] == "Success"):
                                user.paid = True
                                user.save()
                                payment.status = "completed"
                                payment.save()
                                

                                refresh = RefreshToken.for_user(user)
                                return  Response({
                                        "refresh": str(refresh),
                                        "access": str(refresh.access_token),
                                        "email": user.email,
                                        "pkg":user.package,
                                        'paid':user.paid,
                                    })
                            elif(data['payment_status'] == "Pending"):
                                return Response({"message": "We are Verifying you Payment! within 2 hours you'r account is created"}, status=403)
                            else:
                                user.paid = False
                                payment.delete()
                                return Response({"error": "Payment failed"}, status=400)
                        else:
                            return JsonResponse({"error": "Failed to fetch payment status", "details": response.text}, status=response.status_code)
                    except Exception as e:
                        return Response({"error": f"An error occurred: {str(e)}"}, status=500)
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "email": user.email,
                "pkg":user.package,
                'paid':user.paid,
            })

    def get(self, request):
            return render(request, 'login.html')
    



#-------------------------- Register ----------------------------


from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from datetime import datetime, timezone


class Register(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pkg):
        data = request.data

        # ✅ Check for missing fields
        required_fields = ["email", "name", "phone", "password", "package_id", "ref_by"]
        for field in required_fields:
            if field not in data or not data[field]:
                return Response({"error": f"{field} is required"}, status=400)

        email = data["email"]
        name = data["name"]
        phone = data["phone"]
        password = data["password"]
        package_id = data["package_id"]
        ref_by = data["ref_by"]

        # ✅ Validate email format
        try:
            EmailValidator()(email)
        except ValidationError:
            return Response({"error": "Invalid email format"}, status=400)

        # ✅ Referral Validation
        referrer = User.objects.filter(referal_id=ref_by).first()
        if not referrer or not referrer.paid:
            return Response({'error': 'Invalid or inactive referral ID'}, status=400)

        # ✅ Check if phone number already exists and is active
        active_user_with_phone = User.objects.filter(phone=phone, paid=True).first()
        if active_user_with_phone:
            return Response({"error": "Mobile number already exists"}, status=400)

        # ✅ Check if email is already registered and is active
        active_user_with_email = User.objects.filter(email=email, paid=True).first()
        if active_user_with_email:
            return Response({'error': 'Email is already registered'}, status=400)

        # ✅ Handle unverified or inactive users with the same email
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            existing_user.package = package_id
            if not existing_user.is_verified:
                # ✅ Check if OTP was sent in the last 5 minutes
                otp_record = OTP.objects.filter(email=email).first()
                if otp_record and (datetime.now(timezone.utc) - otp_record.created_at).total_seconds() < 300:
                    return Response({"sent": "Please wait before requesting a new OTP", "email": existing_user.email}, status=429)

                # Update existing user details and resend OTP
                try:
                    existing_user.name = name
                    existing_user.phone = phone
                    existing_user.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    existing_user.package = package_id
                    existing_user.previous_ref_id = referrer
                    existing_user.save()

                    otp = send_otp_email(email)

                    return Response({
                        "success": "OTP sent. Verify your account.",
                        "email": existing_user.email,
                    }, status=200)
                except ValidationError as e:
                    return Response({'error': str(e)}, status=400)
            elif not existing_user.paid:
                return Response({"error": "You already registred. Pay your amount to activate account"}, status=403)

        # ✅ Generate referral ID for new user
        referral_id = make_referal_id()

        # ✅ Create New User and send OTP
        try:
            new_user = User.objects.create(
                email=email,
                name=name,
                phone=phone,
                previous_ref_id=referrer,
                package=package_id,
                referal_id=referral_id,
                password=bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            )
            new_user.save()

            send_otp_email(email)
            return Response({
                "message": f"User {name} registered successfully. OTP sent to {email}",
                "referal_id": referral_id,
            }, status=201)

        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

    def get(self, request, pkg):
        return render(request, 'register.html', {"pkg": pkg})



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout and delete the stored refresh token"""
    try:
        token_entry = RefreshTokenStore.objects.get(user=request.user)
        token_entry.revoke()
        return Response({'message': 'User logged out successfully'}, status=200)
    except RefreshTokenStore.DoesNotExist:
        return Response({'error': 'User not logged in'}, status=400)







@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request):
    """Get authenticated user's profile"""
    user = request.user
    return render(request, 'user/dashboard.html')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_earnings(request):
    """Fetch authenticated user's earnings"""
    earnings = Earning.objects.filter(user=request.user)
    serializer = EarningSerializer(earnings, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_kyc(request):
    """Fetch authenticated user's KYC details"""
    try:
        kyc = request.user.kyc_details  # Since KYC is OneToOneField
        serializer = KYCSerializer(kyc)
        return Response(serializer.data)
    except KYC.DoesNotExist:
        return Response({'error': 'No KYC found'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_withdraws(request):
    """Fetch authenticated user's withdraw history"""
    withdraws = Withdraw.objects.filter(user=request.user)
    serializer = WithdrawSerializer(withdraws, many=True)
    return Response(serializer.data)








#-----------  verify OTP ----------------

class VerifyOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_otp = request.data.get('otp')
        email = request.data.get('email')

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "User not found"}, status=404)

        otp_record = OTP.objects.filter(email=user.email).first()
        
        if not otp_record or otp_record.otp != user_otp:
            return Response({"error": "Invalid OTP. Please try again."}, status=400)

        if not otp_record.is_valid():
            return Response({"error": "OTP expired. Please request a new one."}, status=400)

        # ✅ OTP is valid, activate user
        user.is_verified = True
        user.save()
        otp_record.delete()  # Remove OTP after successful verification

        return Response({"message": "User verified successfully"}, status=200)
    
    def get(self, request):
        return render(request, 'otp.html')
    

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    # Extract email from request body
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email is required"}, status=400)

    # Check if user exists with the provided email
    user = User.objects.filter(email=email).first()
    
    if not user:
        return Response({"error": "User not found"}, status=404)
    # Send OTP via utility function (assumes send_otp_email is implemented)
    otp_sent = send_otp_email(email)

    if otp_sent:
        return Response({"message": "OTP sent successfully"}, status=200)
    
    # Handle case where OTP sending fails
    return Response({"error": "Failed to send OTP. Please try again later."}, status=500)






@api_view(['GET'])
def regi(request):
    return render(request, 'register.html')


@api_view(['GET'])
@permission_classes([AllowAny])
def AboutUs(request):
    return render(request, 'about.html')


@api_view(['GET'])
@permission_classes([AllowAny])
def ContactUs(request):
    return render(request, 'contact.html')




# @api_view(['GET'])
# @permission_classes([AllowAny])
# def register(request):
#     return render(request, 'register.html')


from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist

class CreatePayment(APIView):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def post(self, request, pkg):
        # Extract email from request data
        email = request.data.get("email")

        package = {1: 299, 2:599, 3:1199, 4:2399, 5:4199, 6:6999, 7:9999}
        amount = package[pkg]

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Fetch user by email
            user = User.objects.get(email=email)
            user.package = pkg
            user.save()

        except ObjectDoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
        

        try:
            # Generate unique payment ID and create payment record
            payment_id = str(uuid.uuid4())
            if(Payment.objects.filter(user=user,status='pending').exists()):
                payment = Payment.objects.get(user=user)
                payment.delete()

            if Payment.objects.filter(payment_id=payment_id).exists():
                payment_id = str(uuid.uuid4())
            payment = Payment.objects.create(user=user, payment_id=payment_id, status="pending",amount=amount,package=pkg)
            payment.save()

            env = Env()
            Env.read_env()
            ACCOUNT_ID=env('ACCOUNT_ID')
            ACCOUNT_SECRET=env('ACCOUNT_SECRET')      

            payload = {
                    "init_payment": { 
                    "account_id" : ACCOUNT_ID,
                    "secret_key" : ACCOUNT_SECRET,
                    "payment_id" : payment_id, 
                    "payment_purpose": pkg, 
                    "payment_amount": package[pkg],
                    "payment_name": user.name,
                    "payment_phone": user.phone,
                    "payment_email": user.email,
                    "redirect_url": "https://skill-study.com"
                }
            }

            url = "https://zerotize.in/api_payment_init"

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                print(response.json())
                return JsonResponse(response.json(), status=200)
            else:
                return JsonResponse({"error": "Failed to process payment", "details": response.text}, status=response.status_code)
            
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, pkg):
        return render(request, 'payment.html')




@api_view(['POST'])
def validate_payment(request):

    email = request.data.get("email")

    if not email:
        return JsonResponse({"error": "Invalid data provided."}, status=400)

    try:
        user = User.objects.get(email=email)
        payment = Payment.objects.get(user=user)

        # Update payment status
        payment.status = "completed"
        payment.save()
        
        user.paid = True
        user.save()

        # Referral earnings logic
        referrer = user.previous_ref_id
        package_earnings = {
            1: 299,
            2: 499,
            3: 100,
            4: 150,
            5: 200,
            6: 250,
            7: 300,
        }

        if referrer and payment.package in package_earnings:
            total_earning = package_earnings[payment.package]

            # Distribute earnings (70% to immediate referrer, etc.)
            immediate_earning = total_earning * 0.7
            next_level_earning = total_earning * 0.2

            # Update immediate referrer's earnings
            Earning.objects.create(user=referrer, earn=immediate_earning)

            # Check for next-level referrer
            if referrer.previous_ref_id:
                next_level_referrer = referrer.previous_ref_id
                Earning.objects.create(user=next_level_referrer, earn=next_level_earning)

        return JsonResponse({"message": "Payment successful!"}, status=200)

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)


@api_view(['GET'])
def validate(request):
    return render(request, 'validate.html')










import requests
from django.http import JsonResponse
from django.views import View

class CallPaymentAPI(View):
    def get(self, request, *args, **kwargs):
        try:
            # Extract data from the incoming request
            client_data = request.POST  # If form-data is sent
            # Or use json.loads(request.body) if JSON payload is sent
            
            # # Prepare data for the external API
            # account_id = client_data.get("account_id", "")
            # secret_key = client_data.get("secret_key", "")
            # payment_id = client_data.get("payment_id", "")
            # payment_purpose = client_data.get("payment_purpose", "")
            # payment_amount = client_data.get("payment_amount", "")
            # payment_name = client_data.get("payment_name", "")
            # payment_phone = client_data.get("payment_phone", "")
            # payment_email = client_data.get("payment_email", "")
            # redirect_url = client_data.get("redirect_url", "")

            # # Validate required fields (optional)
            # required_fields = ["account_id", "secret_key", "payment_id", "payment_amount", "redirect_url"]
            # missing_fields = [field for field in required_fields if not locals().get(field)]
            
            # if missing_fields:
            #     return JsonResponse({"error": f"Missing required fields: {', '.join(missing_fields)}"}, status=400)

            # Prepare payload for the external API
            payload = {
                    "init_payment": { 
                    "account_id" : "GggK01KW",
                    "secret_key" : "84MhNv2L0wnnZuMW",
                    "payment_id" : "sdjkksjfkasn", 
                    "payment_purpose": "purpose is to pay", 
                    "payment_amount": "1",
                    "payment_name": "Tejas Patare",
                    "payment_phone": "1234567890",
                    "payment_email": "pataretejas1885@gmail.com",
                    "redirect_url": "https://skill-study.com"
                }
            }

            # External API URL
            url = "https://zerotize.in/api_payment_init"

            # Make POST request to external API
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers)

            # Check response status and return accordingly
            if response.status_code == 200:
                return JsonResponse(response.json(), status=200)
            else:
                return JsonResponse({"error": "Failed to process payment", "details": response.text}, status=response.status_code)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


