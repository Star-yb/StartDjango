"""
URL configuration for OnlineEducation project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
import os
from apps.accounts.api.captcha import captcha_router
from apps.accounts.api.auth import CustomAuthController

API=settings.API
API.add_router("/auth", captcha_router)  # 验证码相关接口

# API.register_controllers(CustomAuthController)  # 注册控制器，自动生成CRUD接口
urlpatterns = [


    path('admin/', admin.site.urls),

    # 验证码
    path('captcha/', include('captcha.urls')),

    # 应用模块
    # 全局的前缀
    path('api/', API.urls),  # 所有API接口的入口

    # 配置静态资源路由
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # 设置static路由
    re_path(r'static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    # node_modules静态资源
    re_path(r'node_modules/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'node_modules')}),
]
