from django.db import models
from decimal import Decimal
import uuid
from django.contrib.auth.hashers import make_password
from django.conf import settings
from datetime import date
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from django.utils.timezone import now

class UserManager(BaseUserManager):
    def create_user(self, email, name, phone, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, phone=phone, **extra_fields)
        user.set_password(password)  # Securely hash password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, name, phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    referal_id = models.CharField( max_length=255, unique=True, db_index=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    phone = models.BigIntegerField(unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    package = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    previous_ref_id = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required for Django Admin
    username = None

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Login using email instead of username
    REQUIRED_FIELDS = []

    class Meta:
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        return self.email

class RefreshTokenStore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="refresh_token")
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refresh Token for {self.user.email}"

    def revoke(self):
        self.delete()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    dob = models.DateField( blank=True, default=date.today)
    pro_photo = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"Profile of {self.user.name}"


class KYC(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_name = models.CharField(max_length=255)
    holder_name = models.CharField(max_length=255)
    account_no = models.CharField(max_length=20, unique=True)
    ifsc_code = models.CharField(max_length=20)
    aadhar_no = models.CharField(max_length=12, unique=True)
    pan_no = models.CharField(max_length=10, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc_details")

    def __str__(self):
        return f"KYC for {self.user.name}"


class Earning(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    earn = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    date = models.DateField(blank=True, default=date.today)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="earnings")

    def __str__(self):
        return f"Earnings for {self.user.name} on {self.my_date}"



class Withdraw(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    time = models.TimeField()
    my_date = models.DateField( blank=True, default=date.today)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdraws")
    earning = models.ForeignKey(Earning, on_delete=models.CASCADE, related_name="withdraws")

    def __str__(self):
        return f"Withdraw of {self.amount} by {self.user.name}"




class OTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (now() - self.created_at).seconds < 300  # Valid for 5 minutes
    

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"