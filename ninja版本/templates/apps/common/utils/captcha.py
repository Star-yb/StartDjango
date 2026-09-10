from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


@dataclass(frozen=True)
class CaptchaPayload:
    captcha_key: str
    image_url: str
    audio_url: str | None
    expires_in: int


@dataclass(frozen=True)
class CaptchaVerifyResult:
    ok: bool
    reason: str | None = None


def generate_captcha(request) -> CaptchaPayload:
    from captcha.models import CaptchaStore

    captcha_key = CaptchaStore.generate_key()
    store = CaptchaStore.objects.get(hashkey=captcha_key)

    image_path = reverse("captcha-image", kwargs={"key": captcha_key})
    image_url = request.build_absolute_uri(image_path)
    # try:
    #     audio_path = reverse("captcha-audio", kwargs={"key": captcha_key})
    #     audio_url = request.build_absolute_uri(audio_path)
    # except NoReverseMatch:
    #     audio_url = None

    expires_in = max(0, int((store.expiration - timezone.now()).total_seconds()))
    return CaptchaPayload(
        captcha_key=captcha_key,
        image_url=image_url,
        audio_url=None,
        expires_in=expires_in,
    )


def verify_captcha(*, captcha_key: str, captcha_code: str, delete_on_success: bool = True) -> CaptchaVerifyResult:
    from captcha.models import CaptchaStore

    store = CaptchaStore.objects.filter(hashkey=captcha_key).first()
    if store is None:
        return CaptchaVerifyResult(ok=False, reason="invalid_key")

    if store.expiration <= timezone.now():
        store.delete()
        return CaptchaVerifyResult(ok=False, reason="expired")

    expected = store.response or ""
    provided = captcha_code or ""

    case_sensitive = bool(getattr(settings, "CAPTCHA_CASE_SENSITIVE", False))
    if not case_sensitive:
        expected = expected.lower()
        provided = provided.lower()

    if expected != provided:
        return CaptchaVerifyResult(ok=False, reason="mismatch")

    if delete_on_success:
        store.delete()

    return CaptchaVerifyResult(ok=True)
