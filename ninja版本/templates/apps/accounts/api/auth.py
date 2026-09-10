from ninja_extra import api_controller, route
from ninja_jwt.controller import AsyncNinjaJWTDefaultController
from ninja_jwt.exceptions import InvalidToken, TokenError
from pydantic import ValidationError

from apps.accounts.schemas import TokenResponseSchema, UserLoginSchema, TokenRefreshResponseSchema, \
    BusinessTokenRefreshSchema, TokenVerifyResponseSchema, BusinessTokenVerifyInputSchema, UserSchema


@api_controller('/auth', tags=['认证'])
class CustomAuthController(AsyncNinjaJWTDefaultController):
    """
    自定义令牌获取控制器，覆盖默认的 obtain_token 逻辑
    """

    @route.post('/login', response={200: TokenResponseSchema}, url_name='custom_login')
    async def obtain_token(self, user_token: UserLoginSchema):
        """
        重写登录逻辑，添加自定义验证
        """

        # 1. 调用父类方法获取基础令牌
        response = super().obtain_token(user_token)

        # 2. 获取用户对象（从 user_token._user 访问）
        user = user_token._user

        # 3. 自定义业务逻辑：检查用户状态、记录登录日志等
        if not user.is_active:
            raise ValidationError("账户已被禁用")

        # 4. 记录登录（异步支持可使用 await）
        # LoginLog.objects.create(user=user, device_id=...)

        # 5. 返回自定义格式的数据
        return user_token.to_response_schema()
        return user_token.output_schema()

    @route.post('/refresh',
                response={200: TokenRefreshResponseSchema},
                url_name="token_refresh",
                operation_id="token_refresh",
                )
    def refresh_token(self, refresh_token: BusinessTokenRefreshSchema):
        """
        重写刷新逻辑，框架会自动：
        1. 验证 refresh token 有效性
        2. 解码 token 并填充 refresh_token._user
        3. 调用 output_schema() 生成返回数据
        """
        try:
            from datetime import datetime
            from ninja_jwt.tokens import RefreshToken
            import time

            # 解析传入的刷新令牌
            refresh = RefreshToken(refresh_token.refresh)

            # 基于同一用户创建新的访问令牌（保持刷新令牌不变）
            new_access_token = str(refresh.access_token)

            # 计算刷新令牌剩余时间
            now_timestamp = time.time()
            expires_at_timestamp = refresh.get('exp', 0)
            remaining_seconds = max(0, int(expires_at_timestamp - now_timestamp))

            # 返回符合 TokenRefreshResponseSchema 格式的响应
            return {
                "access": new_access_token,
                "refresh_token_expires_in": remaining_seconds,
                "server_time": datetime.now()
            }
        except Exception as e:
            # ✅ 兜底异常
            raise InvalidToken(f"刷新失败: {str(e)}")

    @route.post("/verify",
                response={200: TokenVerifyResponseSchema},
                url_name="token_verify",
                operation_id="token_verify",
                )
    async def verify_token(self, token: BusinessTokenVerifyInputSchema):
        # 1. 调用父类方法获取基础令牌
        # response = super().verify_token(token)
        # 2. 解析token以获取类型和用户信息
        from ninja_jwt.tokens import AccessToken, RefreshToken
        from django.contrib.auth import get_user_model
        from asgiref.sync import sync_to_async
        user_model = get_user_model()

        # 3. 尝试解析token
        try:
            parsed_token = AccessToken(token.token)
            token_type = parsed_token.token_type
            user_id = parsed_token.get('user_id')
        except TokenError as e:
            # 如果不是AccessToken，尝试作为RefreshToken解析
            parsed_token = await sync_to_async(RefreshToken)(token.token) # 注意：使用黑名单后 RefreshToken 可能需要异步解析 
            token_type = parsed_token.token_type
            user_id = parsed_token.get('user_id')
            # 查询用户信息

        # 使用sync_to_async包装数据库查询
        # user = sync_to_async(user_model.objects.get)(id=user_id)
        user = await user_model.objects.aget(id=user_id)

        # 返回包含token类型和用户信息的响应
        return TokenVerifyResponseSchema(
            type=token_type,
            exp=parsed_token.get('exp'),
            status="ok",
            user=UserSchema.from_orm(user)
        )
