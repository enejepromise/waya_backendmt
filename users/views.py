from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from rest_framework.permissions import AllowAny
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
import requests
from rest_framework.response import Response
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from .models import SocialLoginAccount
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics, status, permissions
from users.models import EmailVerification
from django.utils import timezone
from users.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
)
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework.views import APIView


User = get_user_model()

class UserRegistrationView(generics.CreateAPIView): 
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()

        domain = getattr(settings, 'DOMAIN', None) or get_current_site(self.request).domain

        uidb64 = urlsafe_base64_encode(force_bytes(str(user.id)))
        token = user.email_verifications.latest('created_at').token  # Get latest token

        verification_link = f"https://{domain}{reverse('verify-email')}?uidb64={uidb64}&token={token}"

        # Send verification email
        subject = "Verify Your Waya Account"
        message = f"Click the link to verify your email: {verification_link}"
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'id': str(user.id),
                'name': user.full_name,
                'email': user.email,
                'avatar': user.avatar.url if user.avatar else None,
                'token': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=request)  # Ensure your serializer implements email sending
        return Response({"message": "Password reset email sent if the email is registered."})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset successfully."})


class EmailVerificationView(APIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data['uidb64']
        token = serializer.validated_data['token']

        try:
            # Decode user ID from uidb64
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            # Find the EmailVerification token for this user
            email_verification = EmailVerification.objects.get(
                user=user,
                token=token,
                verified=False
            )
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, EmailVerification.DoesNotExist):
            return Response({"detail": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if token is expired
        if email_verification.is_expired():
            return Response({"detail": "Verification link has expired."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark user as verified and token as used
        user.is_verified = True
        user.save()
        email_verification.mark_as_verified()

        return Response({"message": "Email verified successfully!"}, status=status.HTTP_200_OK)


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Implement sending password reset email logic here if not handled in serializer.save()
        return Response({"detail": "Password reset email sent."})


class ResetPasswordConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Provide user context if possible, else None
        serializer = self.get_serializer(data=request.data, context={'user': None})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset successfully."})


def home(request):
    return JsonResponse({"message": "Welcome to the Waya Backend API"})


class GoogleLoginView(APIView):
    def post(self, request):
        id_token = request.data.get('id_token')
        if not id_token:
            return Response({'error': 'Missing ID token'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the token with Google
        google_response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if google_response.status_code != 200:
            return Response({'error': 'Invalid ID token'}, status=status.HTTP_400_BAD_REQUEST)

        user_info = google_response.json()
        email = user_info.get('email')
        uid = user_info.get('sub')

        if not email or not uid:
            return Response({'error': 'Invalid Google token: missing email or uid'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if UID already exists
            social_account = SocialLoginAccount.objects.get(provider='google', uid=uid)
            user = social_account.user
        except SocialLoginAccount.DoesNotExist:
            # Check if a user with the same email exists
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.username = email.split('@')[0]
                user.set_unusable_password()
                user.save()

            # Create new social account link
            SocialLoginAccount.objects.create(
                user=user,
                provider='google',
                uid=uid,
                extra_data=user_info
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)
