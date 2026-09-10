"""
Schema定义模块
定义API请求和响应的数据模型
"""
from datetime import datetime
from typing import Optional, Dict
from ninja import Schema, ModelSchema
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.http import HttpRequest
from ninja_jwt.schema import TokenObtainPairInputSchema, TokenRefreshInputSchema, TokenVerifyInputSchema
from ninja_jwt.tokens import RefreshToken
from ninja_jwt.exceptions import ValidationError as JWTValidationError
from ninja_jwt.settings import api_settings
from uuid import UUID


# ============ 用户相关 Schema ============

class UserSchema(Schema):
    """用户信息Schema"""
    id: UUID | int 
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserRegisterSchema(Schema):
    """用户注册Schema"""
    username: str
    password: str
    email: Optional[str] = None


# class UserLoginSchema(Schema):
#     """用户登录Schema"""
#     username: str
#     password: str

#  自定义返回结构
class UserLoginSchema(TokenObtainPairInputSchema):
    """
    登录 Schema。重写认证方法，使登录失败返回 400 + ValidationError，而非 401 + AuthenticationFailed。
    """
    client_ip: Optional[str] = None  # 客户端IP

    def authenticate(self, request: HttpRequest, credentials: Dict) -> None:
        """重写：认证失败时抛 ValidationError(400)，不抛 AuthenticationFailed(401)。"""
        self._user = authenticate(request, **credentials)
        if not (self._user is not None and self._user.is_active):
            raise JWTValidationError(
                detail=self._default_error_messages["no_active_account"],
                code="invalid_credentials",
            )

    def check_user_authentication_rule(self) -> None:
        """重写：规则校验不通过时返回 400，不返回 401。"""
        if not api_settings.USER_AUTHENTICATION_RULE(self._user):
            raise JWTValidationError(
                detail=self._default_error_messages["no_active_account"],
                code="invalid_credentials",
            )

    @classmethod
    def get_response_schema(cls):
        # 告诉框架：我返回的是这个 Schema
        return TokenResponseSchema

    @classmethod
    def get_token(cls, user) -> Dict:
        values = super().get_token(user)
        values.update(user=UserSchema.from_orm(user)) # this will be needed when creating output schema
        return values

    # 第二种：自定义返回结构
    def output_schema(self):
        print("输出自定义数据")
        out_dict = self.get_response_schema_init_kwargs()
        print(out_dict)
        out_dict.update(user=UserSchema.from_orm(self._user))
        print(out_dict)
        return TokenResponseSchema(**out_dict)


class BusinessTokenRefreshSchema(TokenRefreshInputSchema):
    device_id: Optional[str] = None


class BusinessTokenVerifyInputSchema(TokenVerifyInputSchema):
    device_id: Optional[str] = None


# ============ 请求返回的 Schema ============
class TokenResponseSchema(Schema):
    """Token响应Schema"""
    access: str
    refresh: str
    user: UserSchema

class TokenRefreshResponseSchema(Schema):
    access: str
    # 添加自定义返回字段
    refresh_token_expires_in: int  # 刷新令牌剩余秒数
    server_time: datetime

class TokenVerifyResponseSchema(Schema):
    type: str
    exp: int
    status: str
    user: UserSchema

# ============ 验证码相关Schema ============
class CaptchaPayloadSchema(Schema):
    captcha_key: str
    image_url: str
    audio_url: Optional[str] = None
    expires_in: int


class CaptchaVerifyInputSchema(Schema):
    captcha_key: str
    captcha_code: str


class CaptchaVerifyResultSchema(Schema):
    ok: bool


