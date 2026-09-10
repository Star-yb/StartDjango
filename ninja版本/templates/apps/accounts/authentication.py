# authentication.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

class BusinessAuthBackend(BaseBackend):
    """业务用户认证后端"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        print(username)
        try:
            user_account = user_model.objects.get(username=username)
            if user_account.check_password(password) and user_account.is_active:
                return user_account
        except user_model.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
