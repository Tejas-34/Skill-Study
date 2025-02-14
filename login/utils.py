import requests
import requests
import json
import random
import uuid
from django.utils.timezone import now
from .models import OTP, User

TENANT_ID = "d2c1f693-a3c9-485b-ba2c-844166334bd8"
CLIENT_ID = "b9690156-4dcf-4cde-a4b9-b5220a404132"
CLIENT_SECRET = "fcm8Q~jOWxZKorqKh4ivnr93E36_RFQluG-AWamB"
SENDER_EMAIL = "support@skill-study.com" 

def get_access_token():
    """Fetch OAuth 2.0 Token from Microsoft Identity Platform"""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(url, data=payload, headers=headers)
    response_data = response.json()
    
    return response_data.get("access_token")

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_otp_email(recipient_email):
    """Send OTP email using Microsoft Graph API"""
    access_token = get_access_token()

    if not access_token:
        print("Failed to get access token")
        return None

    otp = generate_otp()
    email_subject = "Your OTP Code"
    email_body = f"Your OTP is: {otp}"

    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"

    email_payload = {
        "message": {
            "subject": email_subject,
            "body": {
                "contentType": "Text",
                "content": email_body
            },
            "toRecipients": [
                {"emailAddress": {"address": recipient_email}}
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(email_payload))

    if response.status_code == 202:
        print(f"OTP sent to {recipient_email}: {otp}")
        OTP.objects.update_or_create(email=recipient_email, defaults={'otp': otp, 'created_at': now()})
        return otp
    else:
        print(f"Failed to send email: {response.json()}")
        return None



def make_referal_id():
        return "SK-"+str(uuid.uuid4())


def make_referal_id():
    while True:
        # Generate a random 4-digit number (0000-9999)
        unique_number = f"{random.randint(0, 9999):04d}"
        
        # Create the referral ID
        referal_id = f"SS-{unique_number}"
        
        # Ensure uniqueness
        user = User.objects.filter(referal_id=referal_id).first()
        if not user :
            return referal_id