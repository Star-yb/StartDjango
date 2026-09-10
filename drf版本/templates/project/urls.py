"""
URL configuration for OnlineEducation project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
import os

from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

path_list = [
    path('accounts/', include('apps.accounts.urls')),
    path('common/', include('apps.common.urls')),
]


urlpatterns = [
    path('doc/schema/', SpectacularAPIView.as_view(), name='schema'),  # schema的配置文件的路由
    path('doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # swagger-ui的路由
    path('doc/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # redoc的路由

    path('admin/', admin.site.urls),

    # 验证码
    path('captcha/', include('captcha.urls')),

    # 应用模块
    # 全局的前缀
    path('', include(path_list)),

    # 配置静态资源路由
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # 设置static路由
    re_path(r'static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    # node_modules静态资源
    re_path(r'node_modules/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'node_modules')}),
]
