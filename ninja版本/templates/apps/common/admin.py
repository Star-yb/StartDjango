from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

try:
    from captcha.models import CaptchaStore
except Exception:
    CaptchaStore = None


def hard_delete_selected(modeladmin, request, queryset):
    # 只有超级管理员可见和执行此操作
    if not request.user.is_superuser:
        modeladmin.message_user(request, '只有超级管理员可以执行真删除操作', level=messages.ERROR)
        return

    if not modeladmin.has_delete_permission(request):
        modeladmin.message_user(request, '没有执行删除的权限', level=messages.ERROR)
        return

    # 1. 用 all_objects 拿到"包含已软删"的 QuerySet
    pks = queryset.values_list('pk', flat=True)
    real_qs = modeladmin.model.all_objects.filter(pk__in=pks)

    # 2. 调用真正的 delete()
    try:
        with transaction.atomic():
            deleted, _rows_count = real_qs.delete()
    except Exception as e:
        modeladmin.message_user(request, f'删除失败：{e}', level=messages.ERROR)
        return

    modeladmin.message_user(request, f'已真删除 {deleted} 条记录', level=messages.SUCCESS)


# 为 hard_delete_selected 添加 SimpleUI 样式和确认弹窗配置
hard_delete_selected.short_description = '删除所选（真）'
hard_delete_selected.icon = 'fas fa-trash-alt'  # 删除图标
hard_delete_selected.type = 'danger'  # 危险操作，红色按钮
hard_delete_selected.confirm = '您确定要永久删除选中的记录吗？此操作不可恢复！'  # 确认弹窗文本

# 全局：隐藏非超级管理员的该动作
_original_get_actions = admin.ModelAdmin.get_actions


def _patched_get_actions(self, request):
    actions = _original_get_actions(self, request)
    if not request.user.is_superuser:
        actions.pop('hard_delete_selected', None)
    return actions


admin.ModelAdmin.get_actions = _patched_get_actions

# 将硬删除操作添加到全局 admin site
admin.site.add_action(hard_delete_selected, name='hard_delete_selected')


if CaptchaStore is not None:
    if admin.site.is_registered(CaptchaStore):
        admin.site.unregister(CaptchaStore)

    class CaptchaStoreAdmin(admin.ModelAdmin):
        list_display = ("hashkey", "challenge", "expiration")
        search_fields = ("hashkey", "challenge")
        list_filter = ("expiration",)
        ordering = ("-expiration",)
        actions = ("delete_expired_captchas", "delete_all_captchas")

        def delete_expired_captchas(self, request, queryset):
            if not request.user.is_superuser:
                self.message_user(request, "只有超级管理员可以执行此操作", level=messages.ERROR)
                return
            expired_qs = CaptchaStore.objects.filter(expiration__lt=timezone.now())
            deleted_count = expired_qs.count()
            expired_qs.delete()
            self.message_user(request, f"已删除过期验证码 {deleted_count} 条", level=messages.SUCCESS)

        def delete_all_captchas(self, request, queryset):
            if not request.user.is_superuser:
                self.message_user(request, "只有超级管理员可以执行此操作", level=messages.ERROR)
                return
            deleted_count = CaptchaStore.objects.count()
            CaptchaStore.objects.all().delete()
            self.message_user(request, f"已删除验证码 {deleted_count} 条", level=messages.SUCCESS)

        delete_expired_captchas.short_description = "删除过期验证码"
        delete_all_captchas.short_description = "删除全部验证码"

    admin.site.register(CaptchaStore, CaptchaStoreAdmin)

