from django.apps import AppConfig




class AccountsConfig(AppConfig):
    name = 'apps.accounts'
    def ready(self):
        pass
        # 在应用就绪时导入控制器，确保它们被注册到API中
        from apps.accounts.api.auth import CustomAuthController
        from django.conf import settings
        var = settings.API
        var.register_controllers(CustomAuthController)
        # settings.API.register_controllers(CustomAuthController)
        
