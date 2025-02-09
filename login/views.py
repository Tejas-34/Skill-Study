from wtforms import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, RefreshTokenStore, Profile, KYC,OTP, Payment
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

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "referal_id": user.referal_id
            })

    def get(self, request):
            return render(request, 'login.html')
    



#-------------------------- Register ----------------------------

class Register(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        # ✅ **Check for missing fields**
        required_fields = ["email", "name", "phone", "password", "package_id", "ref_by"]
        for field in required_fields:
            if field not in data or not data[field]:
                return Response({"error": f"{field} is required"}, status=400)

        email = data["email"]
        name = data["name"]
        phone = data["phone"]
        password = data["password"].encode('utf-8')
        package_id = data["package_id"]
        ref_by = data["ref_by"]

        # ✅ **Check if email is already registered**
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            if not existing_user.is_verified:
                # ✅ **Check if OTP was sent in the last 5 minutes**
                otp_record = OTP.objects.filter(email=email).first()
                if otp_record and (now() - otp_record.created_at).seconds < 300:
                    return Response({"error": "Please wait before requesting a new OTP"}, status=429)

                otp = send_otp_email(email)
                return render(request, 'otp.html', {"referal": existing_user.referal_id})

            return Response({'error': 'Email already exists'}, status=400)

        # ✅ **Referral Validation**
        referrer = User.objects.filter(referal_id=ref_by).first()
        if not referrer:
            return Response({'error': 'Invalid referral ID'}, status=400)

        # ✅ **Generate referral ID**
        referral_id = make_referal_id()

        # ✅ **Create New User**
        try:
            new_user = User.objects.create(
                email=email,
                name=name,
                phone=phone,
                previous_ref_id=referrer,
                package=package_id,
                referal_id=referral_id,
                password=bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
            )
            new_user.save()
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)

        # ✅ **Send OTP after registration**
        send_otp_email(email)

        return render(request, 'otp.html', {'referal': referral_id})

    def get(self, request):
        return render(request, 'checkout.html')


@api_view(['GET'])
@permission_classes([AllowAny])
def RegisterM(request):
    return render(request, 'register.html')


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
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get authenticated user's profile"""
    user = request.user
    return Response(UserSerializer(user).data)


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





@api_view(['POST'])
def send_otp(request):
    """API to send OTP for email verification"""
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=400)

    otp = send_otp_email(email)
    if otp:
        request.session['otp'] = otp  # Store OTP in session (or DB)
        return Response({"message": "OTP sent successfully!"}, status=200)
    else:
        return Response({"error": "Failed to send OTP"}, status=500)







#-----------  verify OTP ----------------

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    user_otp = request.data.get('otp')
    referal_id = request.data.get('referal_id')

    user = User.objects.filter(referal_id=referal_id).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    otp_record = OTP.objects.filter(email=user.email).first()
    
    if not otp_record or otp_record.otp != user_otp:
        return render(request, 'otp.html', {"referal": referal_id, "error": "Invalid OTP. Please try again."})

    if not otp_record.is_valid():
        return render(request, 'otp.html', {"referal": referal_id, "error": "OTP expired. Please request a new one."})

    # ✅ OTP is valid, activate user
    user.is_verified = True
    user.save()
    # otp_record.delete()  # Remove OTP after successful verification

    return render(request, "payment.html", {"user": user})









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



@api_view(['POST'])
def create_payment(request):
    ref = request.data.get("ref")
    user = User.objects.get(referal_id=ref)
    payment_id = str(uuid.uuid4())  # Generate a unique ID

    # Save payment record in the database
    payment = Payment.objects.create(user=user, payment_id=payment_id, status="pending")

    # Store payment_id in Django session
    request.session["payment_id"] = payment_id
    request.session['user'] = user.referal_id

    # Redirect user to Cosmofeed's payment page
    cosmofeed_payment_url = "https://cosmofeed.com/vp/67a86d37aceb24001394af38"
    return redirect(cosmofeed_payment_url)




@api_view(['GET'])
def payment_success(request):
    # Retrieve payment_id from session

    payment_id = request.session.get("payment_id")
    if not payment_id:
        return render(request, "payment_failed.html", {"message": "No payment session found."})

    # Find the payment record in the database
    try:
        user = User.objects.get(referal_id=request.session['user'])
        payment = Payment.objects.get(payment_id=payment_id, user=user)
        payment.status = "completed"  # Update payment status
        payment.save()

        # Clear session
        del request.session["payment_id"]

        return Response({"message": "Payment successful!"}, status=400)  
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)
