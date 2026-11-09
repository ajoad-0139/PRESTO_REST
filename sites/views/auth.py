# sites/views/auth.py
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from sites.exceptions import APIError
from sites.responses import success_response


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET /auth/csrf/  -> sets the csrftoken cookie (call this first)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return success_response({"csrfToken": get_token(request)})


class LoginView(APIView):
    """POST /auth/login/  -> starts a session (sets the sessionid cookie)."""

    permission_classes = [AllowAny]
    authentication_classes = []  # no session check needed to log in

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(request, **serializer.validated_data)
        if user is None:
            raise APIError("Invalid username or password.", 401)
        if not user.is_active:
            raise APIError("This account is disabled.", 403)

        login(request, user)
        return success_response(
            {"id": user.pk, "username": user.get_username()},
            "Login successful",
        )


class LogoutView(APIView):
    """POST /auth/logout/  -> ends the session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return success_response(message="Logged out")


class MeView(APIView):
    """GET /auth/me/  -> who am I (handy to confirm you are logged in)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return success_response({"id": user.pk, "username": user.get_username()})