from ninja_extra import Router

from apps.accounts.schemas import CaptchaPayloadSchema, CaptchaVerifyInputSchema
from apps.common.utils.captcha import generate_captcha, verify_captcha
from apps.common.utils.response import ResponseSchema, ApiResponse

captcha_router = Router(tags=["验证码"])


@captcha_router.get("/captcha", response={200: ResponseSchema}, tags=["验证码"])
def get_captcha(request):
    payload = generate_captcha(request)
    data = CaptchaPayloadSchema(
        captcha_key=payload.captcha_key,
        image_url=payload.image_url,
        audio_url=payload.audio_url,
        expires_in=payload.expires_in,
    ).dict()
    return ApiResponse.success(data=data, msg="获取验证码成功")


@captcha_router.post("/captcha/refresh", response={200: ResponseSchema}, tags=["验证码"])
def refresh_captcha(request):
    payload = generate_captcha(request)
    data = CaptchaPayloadSchema(
        captcha_key=payload.captcha_key,
        image_url=payload.image_url,
        audio_url=payload.audio_url,
        expires_in=payload.expires_in,
    ).dict()
    return ApiResponse.success(data=data, msg="刷新验证码成功")


@captcha_router.post("/captcha/verify", response={200: ResponseSchema}, tags=["验证码"])
def verify_captcha_api(request, body: CaptchaVerifyInputSchema):
    result = verify_captcha(captcha_key=body.captcha_key, captcha_code=body.captcha_code)
    if result.ok:
        return ApiResponse.success(data={"ok": True}, msg="验证码正确")

    if result.reason == "expired":
        return ApiResponse.validation_error(msg="验证码已过期", data={"ok": False})
    if result.reason == "mismatch":
        return ApiResponse.validation_error(msg="验证码错误", data={"ok": False})
    return ApiResponse.validation_error(msg="验证码无效", data={"ok": False})
