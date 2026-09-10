#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import subprocess
import argparse
import json
from pathlib import Path


def _parse_settings_blocks(content):
    """
    将 settings 内容解析为 (变量名, 整块文本) 的列表。
    只识别行首的大写变量赋值（如 INSTALLED_APPS = ...），
    每块从 VAR = 起至下一个同类赋值行或文件末尾止。
    """
    lines = content.splitlines(keepends=True)
    blocks = []  # (name or None, block_text)
    i = 0
    var_pattern = re.compile(r'^\s*([A-Z_][A-Z0-9_]*)\s*=')

    while i < len(lines):
        line = lines[i]
        m = var_pattern.match(line)
        if m:
            var_name = m.group(1)
            block_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if var_pattern.match(next_line):
                    break
                block_lines.append(next_line)
                i += 1
            blocks.append((var_name, ''.join(block_lines)))
        else:
            # 无变量名（如 import、注释、空行）
            chunk = []
            while i < len(lines) and not var_pattern.match(lines[i]):
                chunk.append(lines[i])
                i += 1
            if chunk:
                blocks.append((None, ''.join(chunk)))
    return blocks


def _merge_settings_blocks(original_blocks, template_blocks):
    """
    用模板里的变量块覆盖原始块中同名变量，其余保留；模板中多出的变量追加到末尾。
    """
    template_by_name = {name: text for name, text in template_blocks if name is not None}
    used_from_template = set()
    result = []
    for name, text in original_blocks:
        if name is None:
            result.append((None, text))
        else:
            if name in template_by_name:
                result.append((name, template_by_name[name]))
                used_from_template.add(name)
            else:
                result.append((name, text))
    for name, text in template_blocks:
        if name is not None and name not in used_from_template:
            result.append((name, text))
    return result


def _blocks_to_content(blocks):
    return ''.join(text for _, text in blocks)


class DjangoProjectOptimizer:
    """Django项目结构优化工具"""

    def __init__(self, project_name, project_path=None, template_name=None):
        """
        初始化项目优化器
        
        Args:
            project_name: 项目名称
            project_path: 项目路径，默认为当前目录
        """
        self.project_name = project_name
        self.project_path = project_path or os.getcwd()
        self.base_dir = self.project_path
        self.apps_dir = os.path.join(self.base_dir, 'apps')

        # 工具所在目录 & 模板配置
        self.tool_dir = os.path.dirname(os.path.abspath(__file__))

        # 模板版本名称（对应 templates/<name>/）
        self.template_name = template_name

        base_templates_root = os.path.join(self.tool_dir, 'templates')
        if self.template_name:
            candidate_root = os.path.join(base_templates_root, self.template_name)
            if os.path.isdir(candidate_root):
                self.template_root = candidate_root
            else:
                print(f"警告: 模板版本 '{self.template_name}' 未找到，将回退到默认 templates 目录（如存在）。")
                self.template_root = base_templates_root
        else:
            self.template_root = base_templates_root

        self.template_config_file = os.path.join(self.template_root, 'config.json')
        self.template_config = {}

        # 基础应用列表 - 可以根据需要通过模板配置覆盖
        self.base_apps = ['accounts', 'common']

        # 创建的目录列表 - 也可以通过模板配置覆盖
        self.directories = ['media', 'static', 'templates']

    def run(self):
        """执行项目优化流程"""
        print(f"开始优化Django项目: {self.project_name}")
        
        # 1. 检查项目是否存在
        if not self.check_project_exists():
            print(f"错误: 项目 {self.project_name} 不存在于路径 {self.base_dir}")
            sys.exit(1)

        # 1.5 加载模板配置（如果存在），优先用配置驱动结构
        self.load_template_config()
        
        # 2. 创建基础目录
        self.create_directories()
        
        # 3. 创建apps目录和应用
        self.create_apps()
        
        # 4. 更新settings.py
        self.update_settings()
        
        # 5. 更新主urls.py
        self.update_urls()

        print(f"\n项目 {self.project_name} 已成功优化！")
        print("\n可以通过以下命令启动项目:")
        print("python manage.py migrate")
        print("python manage.py createsuperuser")
        print("python manage.py runserver")

    def check_project_exists(self):
        """检查项目是否存在"""
        # 检查manage.py文件
        if not os.path.exists(os.path.join(self.base_dir, 'manage.py')):
            return False
        
        # 检查项目配置目录
        if not os.path.exists(os.path.join(self.base_dir, self.project_name)):
            return False
            
        # 检查settings.py文件
        if not os.path.exists(os.path.join(self.base_dir, self.project_name, 'settings.py')):
            return False
            
        return True

    def load_template_config(self):
        """从模板目录加载结构/文件配置（可选）"""
        if not os.path.exists(self.template_config_file):
            return

        try:
            with open(self.template_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"加载模板配置文件失败，忽略模板配置: {e}")
            return

        self.template_config = config or {}

        # 覆盖目录列表
        dirs = self.template_config.get("directories")
        if isinstance(dirs, list) and dirs:
            self.directories = dirs
            print(f"使用模板配置的基础目录: {self.directories}")

        # 覆盖基础应用列表
        apps = self.template_config.get("apps")
        if isinstance(apps, list) and apps:
            # apps 可以是字符串列表或包含 name 字段的对象列表
            normalized_apps = []
            for item in apps:
                if isinstance(item, str):
                    normalized_apps.append(item)
                elif isinstance(item, dict) and "name" in item:
                    normalized_apps.append(item["name"])
            if normalized_apps:
                self.base_apps = normalized_apps
                print(f"使用模板配置的基础应用: {self.base_apps}")

    def create_directories(self):
        """创建基础目录结构"""
        print("正在创建基础目录...")
        
        for directory in self.directories:
            dir_path = os.path.join(self.base_dir, directory)
            os.makedirs(dir_path, exist_ok=True)
            print(f"已创建/确认目录: {directory}")
        
        # 在目录中创建一个空的.gitkeep文件以便Git可以跟踪该目录
        for directory in self.directories:
            gitkeep_path = os.path.join(self.base_dir, directory, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, 'w') as f:
                    pass

    def create_apps(self):
        """创建apps目录和基础应用"""
        print("正在创建apps目录和应用...")
        
        # 创建apps目录
        os.makedirs(self.apps_dir, exist_ok=True)
        
        # 创建apps/__init__.py使其成为Python包
        with open(os.path.join(self.apps_dir, '__init__.py'), 'w', encoding='utf-8') as f:
            pass
        
        # 为每个基础应用创建目录结构
        for app_name in self.base_apps:
            self._create_app(app_name)
    
    def _create_app(self, app_name):
        """创建单个应用"""
        print(f"正在创建应用: {app_name}")
        
        app_dir = os.path.join(self.apps_dir, app_name)

        # 如果应用目录已存在，询问是否覆盖
        if os.path.exists(app_dir):
            print(f"警告: 应用 {app_name} 已存在!")
            choice = input(f"是否覆盖应用 {app_name}? [y/N]: ").lower()
            if choice != 'y':
                print(f"跳过创建应用 {app_name}")
                return
            else:
                print(f"重新创建应用 {app_name}")
                shutil.rmtree(app_dir)

        # 1. 优先从模板目录拷贝应用骨架（如果存在）
        app_template_dir = os.path.join(self.template_root, 'apps', app_name)
        if os.path.isdir(app_template_dir):
            shutil.copytree(app_template_dir, app_dir)
            print(f"已从模板目录创建应用: {app_name}")
            return

        # 2. 否则使用内置的默认模板逻辑
        os.makedirs(app_dir, exist_ok=True)

        # 创建基本文件
        files = {
            '__init__.py': '',
            'admin.py': 'from django.contrib import admin\n\n# Register your models here.\n',
            'apps.py': f'''from django.apps import AppConfig


class {app_name.capitalize()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{app_name}'
''',
            'models.py': 'from django.db import models\n\n# Create your models here.\n',
            'views.py': 'from rest_framework.views import APIView\nfrom apps.common.utils.response import Response\n\n# Create your views here.\n',
            'urls.py': '''from django.urls import path

urlpatterns = []
''',
            'tests.py': 'from django.test import TestCase\n\n# Create your tests here.\n',
        }
        
        # 写入文件
        for filename, content in files.items():
            file_path = os.path.join(app_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 创建migrations目录
        migrations_dir = os.path.join(app_dir, 'migrations')
        os.makedirs(migrations_dir, exist_ok=True)
        with open(os.path.join(migrations_dir, '__init__.py'), 'w', encoding='utf-8') as f:
            pass
        
        # 如果是通用模块，创建额外的目录和文件
        if app_name == 'common':
            # 创建models.py，添加所有基础模型类
            with open(os.path.join(app_dir, 'models.py'), 'w', encoding='utf-8') as f:
                f.write('''import uuid

from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel, UUIDModel
from model_utils.fields import AutoCreatedField, AutoLastModifiedField


# 使用django-model-utils重构的通用模型继承
class BaseModel(TimeStampedModel, SoftDeletableModel):
    """
    通用基础模型，集成django-model-utils功能
    
    功能特性：
    - TimeStampedModel: 自动管理created和modified字段
    - SoftDeletableModel: 软删除功能，使用is_removed字段
    """
    
    class Meta:
        abstract = True

    # @property
    # def create_time(self):
    #     """兼容性属性，映射到created"""
    #     return self.created

    # @property
    # def update_time(self):
    #     """兼容性属性，映射到modified"""
    #     return self.modified

    # @property
    # def delete_time(self):
    #     """兼容性属性，软删除时间（django-model-utils不直接支持，返回None）"""
    #     return None

    # @property
    # def is_delete(self):
    #     """兼容性属性，映射到is_removed"""
    #     return self.is_removed

    # @is_delete.setter
    # def is_delete(self, value):
    #     """兼容性属性，映射到is_removed"""
    #     self.is_removed = value


# 主键继承模型
class IdModel(models.Model):
    """自增ID主键模型"""
    id = models.AutoField(primary_key=True)

    class Meta:
        abstract = True


class BigIdModel(models.Model):
    """大整数ID主键模型"""
    id = models.BigAutoField(primary_key=True)

    class Meta:
        abstract = True


class UUIdModel(UUIDModel):
    """
    UUID主键模型，基于django-model-utils的UUIDModel
    """
    class Meta:
        abstract = True


''')

            # 更新admin.py，添加验证码管理
            with open(os.path.join(app_dir, 'admin.py'), 'w', encoding='utf-8') as f:
                f.write('''from django.contrib import admin, messages
from django.db import transaction


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

''')

            # 更新views.py，添加CommonMixinViewSet
            with open(os.path.join(app_dir, 'views.py'), 'w', encoding='utf-8') as f:
                f.write('''from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.exceptions import NotFound
from rest_framework.viewsets import GenericViewSet

from apps.common.utils.pagination import PageNumberPaginationUtil
from apps.common.utils.response import Response as Re


class ListModelMixin:
    """
    列表查询 Mixin
    """

    def list(self, request, *args, **kwargs):
        """
        获取对象列表

        支持分页、过滤和排序功能

        Args:
            request: HTTP请求对象
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含对象列表的响应
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        # 如果需要分页，则返回分页数据
        if request.query_params.get('page') and page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = {
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'current': self.paginator.page.number,
                'max_page': self.paginator.page.paginator.num_pages,
                'results': serializer.data
            }
            return Re.success(data=paginated_data, message="列表获取成功")

        # 不分页，返回所有数据
        serializer = self.get_serializer(queryset, many=True)
        return Re.success(data=serializer.data, message="列表获取成功")


class RetrieveModelMixin:
    """
    详情查询 Mixin
    """

    def retrieve(self, request, *args, **kwargs):
        """
        获取单个对象详情

        Args:
            request: HTTP请求对象
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含对象详情的响应
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Re.success(data=serializer.data, message="详情获取成功")
        except NotFound:
            return Re.not_found()


class CreateModelMixin:
    """
    创建对象 Mixin
    """

    def create(self, request, *args, **kwargs):
        """
        创建对象

        Args:
            request: HTTP请求对象，包含创建数据
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含创建结果的响应
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 调用钩子函数保存对象
            self.perform_create(serializer)
            instance = serializer.instance

            # 返回创建成功的数据
            return Re.success(
                data=self.get_serializer(instance).data,
                message="创建成功"
            )

        # 数据验证失败，返回错误信息
        return Re.bad_request(
            message="数据验证失败",
            data=serializer.errors
        )

    def perform_create(self, serializer):
        """
        创建对象的钩子函数

        子类可以重写此方法来自定义创建逻辑

        Args:
            serializer: 序列化器实例
        """
        serializer.save()


class UpdateModelMixin:
    """
    更新对象 Mixin
    """

    def update(self, request, *args, **kwargs):
        """
        更新对象

        Args:
            request: HTTP请求对象，包含更新数据
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含更新结果的响应
        """
        partial = kwargs.pop('partial', False)
        try:
            # 获取要更新的对象
            instance = self.get_object()
        except NotFound:
            return Re.not_found()

        # 使用序列化器验证和更新对象 partial=True 表示部分更新
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            # 调用钩子函数更新对象
            self.perform_update(serializer)
            instance = serializer.instance

            # 返回更新后的数据
            return Re.success(
                data=self.get_serializer(instance).data,
                message="更新成功"
            )

        # 数据验证失败，返回错误信息
        return Re.bad_request(
            message="数据验证失败",
            data=serializer.errors
        )

    def partial_update(self, request, *args, **kwargs):
        """
        部分更新对象

        Args:
            request: HTTP请求对象，包含部分更新数据
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含更新结果的响应
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def perform_update(self, serializer):
        """
        更新对象的钩子函数

        子类可以重写此方法来自定义更新逻辑

        Args:
            serializer: 序列化器实例
        """
        serializer.save()


class DestroyModelMixin:
    """
    删除对象 Mixin
    """

    def destroy(self, request, *args, **kwargs):
        """
        删除对象（软删除）

        Args:
            request: HTTP请求对象
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Response: 包含删除结果的响应
        """
        try:
            instance = self.get_object()
            # 软删除：只标记为已删除，不真正从数据库中移除
            # instance.is_removed = True
            # instance.save()
            instance.delete()
            return Re.success(data={}, message="删除成功")
        except NotFound:
            return Re.not_found()


class ReadOnlyModelViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    只读视图集，提供基础的查询功能

    该类封装了列表查询和详情获取功能，并支持分页、过滤和排序。
    """

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]  # 添加过滤和排序功能
    pagination_class = PageNumberPaginationUtil  # 添加分页功能
    ordering = ['created']  # 默认排序字段


# 引入serializers
from rest_framework import serializers


class ModelViewSet(ListModelMixin,
                   RetrieveModelMixin,
                   CreateModelMixin,
                   UpdateModelMixin,
                   DestroyModelMixin,
                   GenericViewSet):
    """
    通用视图集，提供基础的增删改查功能

    该类封装了常见的 CRUD 操作，包括列表查询、详情获取、创建、更新和删除功能，
    并支持分页、过滤和排序。

    通过继承不同的 Mixin 类，可以自由组合需要的功能。
    """

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]  # 添加过滤和排序功能
    pagination_class = PageNumberPaginationUtil  # 添加分页功能
    ordering = ['created']  # 默认排序字段


# 保持原有的 CommonMixinViewSet 作为 ModelViewSet 的别名，确保向后兼容
CommonMixinViewSet = ModelViewSet

# 请求方法到操作的映射
METHOD_ACTION = {'get': 'list', "post": "create"}
METHOD_ACTION_SINGLE = {'get': 'retrieve', "put": "update", "delete": "destroy"}
METHOD_ACTION_SINGLE_PLUS = {**METHOD_ACTION_SINGLE, "patch": "partial_update"}

''')

            # 创建utils目录和基本工具文件
            utils_dir = os.path.join(app_dir, 'utils')
            os.makedirs(utils_dir, exist_ok=True)
            with open(os.path.join(utils_dir, '__init__.py'), 'w', encoding='utf-8') as f:
                pass
            
            # 创建response.py
            with open(os.path.join(utils_dir, 'response.py'), 'w', encoding='utf-8') as f:
                f.write('''# response.py
from __future__ import annotations

from typing import Any, Final, Protocol

from rest_framework import status
from rest_framework.response import Response as DRFResponse


class _RespDict(Protocol):
    code: int
    message: str
    data: dict[str, Any] | None
    success: bool


# ---------- 常量 ----------
CODE_OK: Final[int] = 200
CODE_BAD: Final[int] = 400
CODE_UNAUTHORIZED: Final[int] = 401
CODE_FORBIDDEN: Final[int] = 403
CODE_NOT_FOUND: Final[int] = 404


class Response:
    """统一响应工具，所有方法返回 DRF Response"""

    # --------------------------------------------------
    # 基础方法
    # --------------------------------------------------
    @staticmethod
    def success(
            data: dict[str, Any] | None = None,
            *,
            message: str = "请求成功",
            status_code: int = status.HTTP_200_OK,
    ) -> DRFResponse:
        return Response._base(True, CODE_OK, message, data, status_code)

    @staticmethod
    def error(
            message: str = "操作失败",
            *,
            data: dict[str, Any] | None = None,
            code: int = CODE_BAD,
            status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> DRFResponse:
        return Response._base(False, code, message, data, status_code)

    # --------------------------------------------------
    # 快捷函数
    # --------------------------------------------------
    @staticmethod
    def unauthorized(
            message: str = "认证失败", data: dict[str, Any] | None = None
    ) -> DRFResponse:
        return Response.error(
            message, data=data or dict(), code=CODE_UNAUTHORIZED, status_code=status.HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def forbidden(message: str = "没有权限", data: dict[str, Any] | None = None) -> DRFResponse:
        return Response.error(
            message, data=data or dict(), code=CODE_FORBIDDEN, status_code=status.HTTP_403_FORBIDDEN
        )

    @staticmethod
    def not_found(message: str = "资源不存在", data: dict[str, Any] | None = None) -> DRFResponse:
        return Response.error(
            message, data=data or dict(), code=CODE_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    def bad_request(
            message: str = "请求参数错误", data: dict[str, Any] | None = None
    ) -> DRFResponse:
        return Response.error(message, data=data or dict())  # 默认 400

    # --------------------------------------------------
    # 内部工具
    # --------------------------------------------------
    @staticmethod
    def _base(
            success: bool,
            code: int,
            message: str,
            data: dict[str, Any] | None,
            status_code: int,
    ) -> DRFResponse:
        return DRFResponse(
            {"code": code, "message": message, "data": data or dict(), "success": success},
            status=status_code,
        )

''')
            
            # 创建account.py
            with open(os.path.join(utils_dir, 'account.py'), 'w', encoding='utf-8') as f:
                f.write('''from typing import Union

from captcha.models import CaptchaStore

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth import get_user_model
                        
                        

def code_check(captcha_key: str, captcha_value: str) -> dict[str, Union[bool, str]]:
    """
    验证码校验函数
    
    Args:
        captcha_key (str): 验证码的唯一标识符
        captcha_value (str): 用户输入的验证码值
        
    Returns:
        dict: 包含验证状态和消息的字典
            - status (bool): 验证是否成功
            - msg (str): 验证结果消息
            
    Example:
        >>> result = code_check("key123", "ABCD")
        >>> print(result)
        {"status": True, "msg": "验证通过"}
    """
    # 检查验证码参数是否为空
    if not captcha_key or not captcha_value:
        return {"status": False, "msg": "验证码不能为空"}

    try:
        # 获取验证码对象
        captcha = CaptchaStore.objects.get(hashkey=captcha_key)

        # 比较验证码（忽略大小写）
        if captcha.response.lower() != captcha_value.lower():
            return {"status": False, "msg": "验证码错误"}

        # 验证成功后删除验证码，防止重复使用
        # captcha.delete()
        return {"status": True, "msg": "验证通过"}
    except CaptchaStore.DoesNotExist:
        return {"status": False, "msg": "验证码已过期"}
    except Exception as e:
        return {"status": False, "msg": f'验证失败: {str(e)}'}

                        
UserModel = get_user_model()
                        

class CustomBackend(ModelBackend):
    """
    自定义用户认证后端
    
    允许使用用户名或邮箱登录系统
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        用户认证方法
        
        Args:
            request: HTTP请求对象
            username (str, optional): 用户名或邮箱地址
            password (str, optional): 用户密码
            **kwargs: 其他关键字参数
            
        Returns:
            User对象: 认证成功返回用户对象
            None: 认证失败返回None
        """
        try:
            # 使用用户名或邮箱查询用户（不区分大小写）
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )

            # 验证密码是否正确
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            # 用户不存在，返回None
            return None
        except Exception:
            # 其他异常情况，返回None
            return None

        # 认证失败，返回None
        return None

''')
            
            # 创建pagination.py
            with open(os.path.join(utils_dir, 'pagination.py'), 'w', encoding='utf-8') as f:
                f.write('''from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PageNumberPaginationUtil(PageNumberPagination):
    """
    自定义分页器
    """
    # 每页的默认显示数据量
    page_size = 10

    # URL参数中设置每页展示数量的名称
    page_size_query_param = 'page_size'

    # URL参数中设置页码的名称
    page_query_param = 'page'

    # 每页的最大数据量
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        重写分页响应方法

        Args:
            data: 分页数据

        Returns:
            Response: 分页响应
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current': self.page.number,
            'max_page': self.page.paginator.num_pages,
            'results': data
        })
''')
            
            # 创建middleware目录和基本中间件
            middleware_dir = os.path.join(app_dir, 'middleware')
            os.makedirs(middleware_dir, exist_ok=True)
            with open(os.path.join(middleware_dir, '__init__.py'), 'w', encoding='utf-8') as f:
                pass
                
            # 创建NetworkMiddleware.py
            with open(os.path.join(middleware_dir, 'NetworkMiddleware.py'), 'w', encoding='utf-8') as f:
                f.write('''class NetworkRequestMiddleware:
    """
    网络请求中间件
    
    用于记录请求信息
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 获取请求IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # 将IP信息添加到请求对象中
        request.client_ip = ip
        
        # 记录请求信息
        # 此处可以添加日志记录等功能
        
        response = self.get_response(request)
        return response
''')
            
            # 创建management目录和命令
            management_dir = os.path.join(app_dir, 'management')
            commands_dir = os.path.join(management_dir, 'commands')
            os.makedirs(commands_dir, exist_ok=True)
            
            with open(os.path.join(management_dir, '__init__.py'), 'w', encoding='utf-8') as f:
                pass
                
            with open(os.path.join(commands_dir, '__init__.py'), 'w', encoding='utf-8') as f:
                pass
                
            # 创建自定义命令server.py
            with open(os.path.join(commands_dir, 'server.py'), 'w', encoding='utf-8') as f:
                f.write('''"""
Django自定义管理命令：server
使用uvicorn启动Django ASGI应用
"""

import os
import sys
import uvicorn
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    """
    使用uvicorn启动Django ASGI服务器的自定义管理命令
    
    该命令提供了一个便捷的方式来启动Django ASGI应用，支持热重载、多进程和日志配置等功能
    """
    
    help = '使用uvicorn启动Django ASGI服务器'

    def add_arguments(self, parser):
        """
        添加命令行参数
        
        Args:
            parser: 参数解析器对象
        """
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='服务器绑定地址（默认: 127.0.0.1）'
        )
        
        parser.add_argument(
            '--port',
            type=int,
            default=8005,
            help='服务器端口（默认: 8005）'
        )
        
        parser.add_argument(
            '--reload',
            action='store_true',
            default=True,
            help='启用自动重载（默认: 启用）'
        )
        
        parser.add_argument(
            '--no-reload',
            action='store_false',
            dest='reload',
            help='禁用自动重载'
        )
        
        parser.add_argument(
            '--workers',
            type=int,
            default=1,
            help='工作进程数（默认: 1）'
        )
        
        parser.add_argument(
            '--log-level',
            choices=['critical', 'error', 'warning', 'info', 'debug'],
            default='info',
            help='日志级别（默认: info）'
        )
        
        parser.add_argument(
            '--no-access-log',
            action='store_false',
            dest='access_log',
            default=True,
            help='禁用访问日志'
        )

    def handle(self, *args, **options):
        """
        处理命令执行
        
        Args:
            *args: 位置参数
            **options: 命令行选项字典
            
        Raises:
            CommandError: 当服务器启动失败时抛出
        """
        try:
            # 获取项目根目录
            BASE_DIR = Path(settings.BASE_DIR)
            
            # 获取ASGI应用模块路径
            # 从ROOT_URLCONF设置中提取模块名，例如: 'DjangoLearn.urls' -> 'DjangoLearn'
            app_module = settings.ROOT_URLCONF.split('.')[0]
            asgi_module = f"{app_module}.asgi:application"
            
            # 服务器配置
            config = {
                "app": asgi_module,
                "host": options['host'],
                "port": options['port'],
                "reload": options['reload'],
                "workers": options['workers'],
                "access_log": options['access_log'],
                "log_level": options['log_level'],
            }
            
            # 如果是单进程且启用重载，添加重载目录
            if options['workers'] == 1 and options['reload']:
                config["reload_dirs"] = [str(BASE_DIR)]
            
            # 显示启动信息
            self._print_startup_info(options)
            
            # 启动服务器
            uvicorn.run(**config)
            
        except KeyboardInterrupt:
            # 处理 Ctrl+C 中断
            self.stdout.write(
                self.style.SUCCESS("✅ 服务器已停止")
            )
        except Exception as e:
            # 处理其他异常
            raise CommandError(f"❌ 启动失败: {e}")

    def _print_startup_info(self, options):
        """
        打印服务器启动信息
        
        Args:
            options (dict): 命令行选项字典
        """
        self.stdout.write(
            self.style.SUCCESS("🚀 正在启动Django ASGI服务器...")
        )
        self.stdout.write(f"📍 服务地址: http://{options['host']}:{options['port']}")
        self.stdout.write(f"👥 工作进程数: {options['workers']}")
        self.stdout.write(f"📊 日志级别: {options['log_level']}")
        self.stdout.write(f"🔄 自动重载: {'启用' if options['reload'] else '禁用'}")
        self.stdout.write(f"📝 访问日志: {'启用' if options['access_log'] else '禁用'}")
        self.stdout.write("🛑 按 Ctrl+C 停止服务器")
        self.stdout.write("-" * 50)

# 使用案例
# python manage.py server 
# python manage.py server --host 0.0.0.0 --port 8005 --no-reload

''')
        
        # 对于accounts模块，创建基本的认证视图和URL
        elif app_name == 'accounts':
            with open(os.path.join(app_dir, 'views.py'), 'w', encoding='utf-8') as f:
                f.write('''from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.common.utils.account import code_check
from apps.common.utils.response import Response


class GetCaptcha(APIView):
    """
    验证码获取接口
    
    提供图形验证码的生成和获取功能
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        """
        获取新的验证码
        
        Args:
            request (Request): HTTP请求对象
            
        Returns:
            Response: 包含验证码key和图片URL的响应
            
        Response Format:
            {
                "code": 200,
                "message": "请求成功",
                "data": {
                    "captcha_key": "验证码唯一标识",
                    "captcha_image": "验证码图片URL"
                },
                "success": true
            }
        """
        # 生成新的验证码
        captcha_key = CaptchaStore.generate_key()
        captcha_image = captcha_image_url(captcha_key)

        # 返回验证码信息
        captcha_data = {
            "captcha_key": captcha_key,
            "captcha_image": captcha_image
        }

        return Response.success(data=captcha_data, message="验证码获取成功")


class LoginTokenObtainPairView(TokenObtainPairView):
    """
    用户登录认证接口
    
    验证用户凭据并返回访问令牌和刷新令牌
    """

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        用户登录认证
        
        Args:
            request (Request): 包含用户名和密码的请求
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Response: 认证结果和令牌信息
            
        Response Format (Success):
            {
                "code": 200,
                "message": "登录成功",
                "data": {
                    "access": "访问令牌",
                    "refresh": "刷新令牌",
                    "username": "用户名"
                },
                "success": true
            }
            
        Response Format (Error):
            {
                "code": 401,
                "message": "认证失败消息",
                "data": {},
                "success": false
            }
        """
        # 验证码校验（如果需要启用）
        # captcha_key = request.data.get("captcha_key")
        # captcha_value = str(request.data.get("captcha_value"))
        # captcha_result = code_check(captcha_key, captcha_value)
        # if not captcha_result["status"]:
        #     return Response.error(message=captcha_result["msg"])

        # 获取序列化器并验证用户凭据
        serializer = self.get_serializer(data=request.data)
        try:
            # 验证数据，如果验证失败会抛出异常
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # 处理令牌错误
            # return InvalidToken(e.args[0])
            return Response.unauthorized(message=str(e))
        except AuthenticationFailed as e:
            # 处理认证失败
            return Response.unauthorized(message=str(e))
        except Exception as e:
            # 处理其他异常
            return Response.error(message=f"登录失败: {str(e)}")

        # 获取验证后的数据
        result = serializer.validated_data
        result["username"] = serializer.user.username

        return Response.success(data=result, message="登录成功")


class CustomTokenRefreshView(TokenRefreshView):
    """
    刷新访问令牌接口
    
    使用有效的刷新令牌获取新的访问令牌
    """

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        刷新访问令牌
        
        Args:
            request (Request): 包含刷新令牌的请求
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Response: 新的访问令牌信息
            
        Response Format (Success):
            {
                "code": 200,
                "message": "Token刷新成功",
                "data": {
                    "access": "新的访问令牌"
                },
                "success": true
            }
            
        Response Format (Error):
            {
                "code": 401,
                "message": "Token无效或已过期",
                "data": {},
                "success": false
            }
        """
        # 获取序列化器并验证刷新令牌
        serializer = self.get_serializer(data=request.data)

        try:
            # 验证数据，如果验证失败会抛出异常
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # 处理令牌错误（如令牌过期、无效等）
            return Response.unauthorized(message="Token无效或已过期")
        except Exception as e:
            # 处理其他异常
            return Response.error(message=f"Token刷新失败: {str(e)}")

        # 获取验证后的数据
        result = serializer.validated_data
        return Response.success(data=result, message="Token刷新成功")


class CustomTokenVerifyView(TokenVerifyView):
    """
    验证令牌有效性接口
    
    验证令牌是否有效，并返回令牌类型和用户信息（如果是访问令牌）
    """

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        验证令牌有效性
        
        Args:
            request (Request): 包含待验证令牌的请求
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Response: 令牌验证结果和相关信息
            
        Response Format (Access Token Success):
            {
                "code": 200,
                "message": "Token验证成功",
                "data": {
                    "token_type": "access",
                    "is_valid": true,
                    "user": {
                        "id": 1,
                        "username": "用户名",
                        "email": "邮箱",
                        ...
                    }
                },
                "success": true
            }
            
        Response Format (Refresh Token Success):
            {
                "code": 200,
                "message": "Token验证成功",
                "data": {
                    "token_type": "refresh",
                    "is_valid": true
                },
                "success": true
            }
        """
        # 获取序列化器并验证令牌
        serializer = self.get_serializer(data=request.data)

        try:
            # 验证数据，如果验证失败会抛出异常
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            # 处理令牌错误（如令牌过期、无效等）
            return Response.unauthorized(message="Token无效或已过期")
        except Exception as e:
            # 处理其他异常
            return Response.error(message=f"Token验证失败: {str(e)}")

        # 获取令牌值
        token_value = request.data.get('token')

        try:
            # 解析令牌以获取令牌类型
            untyped_token = UntypedToken(token_value)
            token_type = untyped_token.get('token_type')

            # 准备响应数据
            response_data = {
                "token_type": token_type,
                "is_valid": True
            }

            # 如果是访问令牌，获取并返回用户信息
            if token_type == 'access':
                try:
                    # 使用JWT认证获取用户
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(token_value)
                    user = jwt_auth.get_user(validated_token)

                    # 构造用户信息数据
                    user_data = {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_active": user.is_active,
                        "is_staff": user.is_staff,
                        "is_superuser": user.is_superuser,
                        "date_joined": user.date_joined.isoformat(),
                        "last_login": user.last_login.isoformat() if user.last_login else None
                    }
                    response_data["user"] = user_data

                except Exception as e:
                    # 如果获取用户信息失败，只返回基本验证信息
                    # 不抛出异常，因为令牌本身是有效的
                    pass

            return Response.success(data=response_data, message="Token验证成功")

        except Exception as e:
            # 如果无法解析令牌类型，返回基本验证成功信息
            return Response.success(
                data={"is_valid": True},
                message="Token验证成功"
            )

''')
            
            # 更新accounts的URLs
            with open(os.path.join(app_dir, 'urls.py'), 'w', encoding='utf-8') as f:
                f.write('''from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from django.urls import path

from . import views

drf_patterns = [
    path('token/', views.LoginTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # 刷新Token有效期的接口
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    # 验证Token的有效性
    path('token/verify/', views.CustomTokenVerifyView.as_view(), name='token_verify'),

    # 验证码获取
    path('captcha/', views.GetCaptcha.as_view()),

]

urlpatterns = drf_patterns
''')
            # 创建业务认证后端 authentication.py
            with open(os.path.join(app_dir, 'authentication.py'), 'w', encoding='utf-8') as f:
                f.write('''
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
''')
        
        print(f"应用 {app_name} 创建成功")

    def update_settings(self):
        """更新settings.py文件"""
        print("正在更新settings.py...")
        
        settings_path = os.path.join(self.base_dir, self.project_name, 'settings.py')
        
        # 备份原始设置文件
        backup_file = f"{settings_path}.bak"
        if not os.path.exists(backup_file):
            shutil.copy2(settings_path, backup_file)
            print(f"已创建设置文件备份: {backup_file}")
        
        try:
            # 如果有模板文件，按配置决定是「按变量覆盖」还是「整文件覆盖」
            settings_tpl_rel = self.template_config.get("settings_template")
            if settings_tpl_rel:
                settings_tpl_path = os.path.join(self.template_root, settings_tpl_rel)
                if os.path.exists(settings_tpl_path):
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    with open(settings_tpl_path, 'r', encoding='utf-8') as f:
                        tpl_content = f.read()
                    tpl_content = tpl_content.replace("{{ project_name }}", self.project_name)
                    # 默认只覆盖模板里出现的变量，不整文件替换
                    settings_mode = (self.template_config.get("settings_mode") or "merge").strip().lower()
                    if settings_mode == "replace":
                        with open(settings_path, 'w', encoding='utf-8') as f:
                            f.write(tpl_content)
                        print("已根据模板 settings_template 整文件覆盖 settings.py（settings_mode=replace）")
                    else:
                        original_blocks = _parse_settings_blocks(original_content)
                        template_blocks = _parse_settings_blocks(tpl_content)
                        merged = _merge_settings_blocks(original_blocks, template_blocks)
                        merged_content = _blocks_to_content(merged)
                        merged_content = merged_content.replace("{{ project_name }}", self.project_name)
                        with open(settings_path, 'w', encoding='utf-8') as f:
                            f.write(merged_content)
                        print("已根据模板 settings_template 按变量覆盖 settings.py 中对应配置（settings_mode=merge）")
                    return

            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_content = f.read()
            
            # 导入必要的模块
            if 'import os' not in settings_content:
                settings_content = 'import os\nimport datetime\n' + settings_content
            elif 'import datetime' not in settings_content:
                settings_content = settings_content.replace('import os', 'import os\nimport datetime')
            
            # 更新ALLOWED_HOSTS
            settings_content = settings_content.replace('ALLOWED_HOSTS = []', 'ALLOWED_HOSTS = ["*"]')
            
            # 更新语言和时区设置
            settings_content = settings_content.replace("LANGUAGE_CODE = 'en-us'", "LANGUAGE_CODE = 'zh-hans'")
            settings_content = settings_content.replace("TIME_ZONE = 'UTC'", "TIME_ZONE = 'Asia/Shanghai'")
            
            # 添加USE_TZ和USE_I18N设置
            if 'USE_TZ = True' in settings_content:
                settings_content = settings_content.replace('USE_TZ = True', 'USE_TZ = False')
            
            # 添加跨域设置
            if 'X_FRAME_OPTIONS = "DENY"' in settings_content:
                settings_content = settings_content.replace('X_FRAME_OPTIONS = "DENY"', 'X_FRAME_OPTIONS = "ALLOWALL"')
            
            # 添加INSTALLED_APPS
            # 修改前：
            simpleui_app = ["    'simpleui',  # 后台管理"]
            django_apps = [
                "    'django.contrib.admin',",
                "    'django.contrib.auth',",
                "    'django.contrib.contenttypes',",
                "    'django.contrib.sessions',",
                "    'django.contrib.messages',",
                "    'django.contrib.staticfiles',",
            ]
            third_party_apps = [
                "    'drf_spectacular',  # OpenAPI 接口",
                "    'django_filters',  # 过滤器",
                "    'rest_framework',  # 序列化",
                "    'rest_framework_simplejwt',  # 认证",
                "    'rest_framework_simplejwt.token_blacklist',  # 黑名单",
                "    'corsheaders',  # 跨域",
                "    'mptt',  # 树形结构",
                "    'captcha',  # 图片验证码",
            ]
            local_apps = [
                "    # 应用模块",
                "    'apps.accounts',  # 认证",
                "    'apps.common',  # 公共",
            ]
            
            # 修改为：
            # 查找INSTALLED_APPS并添加新应用
            if 'INSTALLED_APPS = [' in settings_content:
                # 找到INSTALLED_APPS列表的开始
                start_index = settings_content.find('INSTALLED_APPS = [')
                # 找到INSTALLED_APPS列表结束的]
                end_index = settings_content.find(']', start_index)
                
                # 获取原始的Django应用
                original_apps_str = settings_content[start_index + len('INSTALLED_APPS = ['):end_index].strip()
                original_apps = [app.strip() for app in original_apps_str.split('\n') if app.strip()]
                
                # 构建新的INSTALLED_APPS，确保simpleui在最前面
                new_installed_apps = 'INSTALLED_APPS = [\n'
                
                # 添加simpleui
                for app in simpleui_app:
                    if not any(app.split('#')[0].strip() in original_app for original_app in original_apps):
                        new_installed_apps += f"{app}\n"
                
                # 添加Django内置应用
                for app in django_apps:
                    if not any(app.split('#')[0].strip() in original_app for original_app in original_apps):
                        new_installed_apps += f"{app}\n"
                    else:
                        # 如果已存在，保留原有的配置
                        for original_app in original_apps:
                            if app.split('#')[0].strip() in original_app:
                                new_installed_apps += f"{original_app}\n"
                                break
                
                # 添加第三方应用
                for app in third_party_apps:
                    if not any(app.split('#')[0].strip() in original_app for original_app in original_apps):
                        new_installed_apps += f"{app}\n"
                
                # 添加本地应用
                for app in local_apps:
                    if not any('apps.' in app and app.split('#')[0].strip() in original_app for original_app in original_apps):
                        new_installed_apps += f"{app}\n"
                
                new_installed_apps += ']'
                
                # 替换原有的INSTALLED_APPS
                settings_content = settings_content[:start_index] + new_installed_apps + settings_content[end_index+1:]
            
            # 添加MIDDLEWARE
            if 'MIDDLEWARE = [' in settings_content and 'apps.common.middleware.NetworkMiddleware.NetworkRequestMiddleware' not in settings_content:
                settings_content = settings_content.replace(
                    "'django.middleware.clickjacking.XFrameOptionsMiddleware',",
                    "'django.middleware.clickjacking.XFrameOptionsMiddleware',\n    'apps.common.middleware.NetworkMiddleware.NetworkRequestMiddleware',"
                )
            
            # 修复TEMPLATES配置
            # 查找TEMPLATES配置
            if "'DIRS': []," in settings_content:
                settings_content = settings_content.replace(
                    "'DIRS': [],",
                    "'DIRS': [os.path.join(BASE_DIR, 'templates')],"
                )

# 修复重复的STATIC_URL
            # 添加静态文件和媒体文件配置
            media_config = """
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = 'static/'

# 收集静态文件的根目录
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# 额外的静态文件目录
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static/'),
# ]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
"""
            # 删除重复的STATIC_URL定义
            # 首先检查是否存在原始的STATIC_URL
            static_url_index = settings_content.find('STATIC_URL =')
            if static_url_index != -1:
                # 找到第一个定义后的换行符
                end_line = settings_content.find('\n', static_url_index)
                # 如果找到了结束位置，那么从静态URL定义到下一行的开始都应该被删除
                if end_line != -1:
                    # 检查后面是否有另一个STATIC_URL定义
                    next_static_url = settings_content.find('STATIC_URL =', end_line)
                    if next_static_url != -1:
                        # 找到重复定义的结束位置
                        next_end_line = settings_content.find('\n', next_static_url)
                        if next_end_line != -1:
                            # 删除第二个STATIC_URL定义
                            settings_content = settings_content[:next_static_url] + settings_content[next_end_line+1:]
            
            # 确保不会重复添加
            if 'MEDIA_ROOT = ' not in settings_content:
                # 查找和替换整个静态文件配置部分
                static_pattern = "# Static files (CSS, JavaScript, Images)"
                static_index = settings_content.find(static_pattern)
                if static_index != -1:
                    # 找到这一部分的结束
                    static_end = settings_content.find('\n\n', static_index)
                    if static_end != -1:
                        settings_content = settings_content[:static_index] + media_config + settings_content[static_end+2:]
                    else:
                        settings_content += media_config
                else:
                    settings_content += media_config
            
            # 添加CORS配置
            cors_config = """
# CORS跨域
CORS_ALLOW_ALL_ORIGINS = True
"""
            if 'CORS_ALLOW_ALL_ORIGINS' not in settings_content:
                settings_content += cors_config
            
            # 添加REST_FRAMEWORK配置
            rest_framework_config = """
# 配置JWT认证
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 默认认证方式
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT认证
        'rest_framework.authentication.SessionAuthentication',  # 会话认证
        'rest_framework.authentication.BasicAuthentication',  # 基本认证（用于API文档登录）
    ],
    # 默认权限控制
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # 默认要求认证
    ],
    # 匿名用户限流
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '50/hour',  # 匿名用户每小时50次
        'user': '1000/hour'  # 认证用户每小时1000次
    },
    # 配置OpenAPI
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': '平台的API',
    'DESCRIPTION': '这是项目的API文档',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,  # 是否包含架构
    'SCHEMA_PATH_PREFIX': None,  # 架构路径前缀
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,  # 是否深链接
        "persistAuthorization": True,  # 是否持久化授权
        "displayOperationId": True,  # 是否显示操作ID
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SECURITY': [
        {
            'basicAuth': [],  # 基本认证
        },
        {
            'bearerAuth': [],  # JWT认证
        },
        {
            'cookieAuth': [],  # 会话认证
        }
    ],
    'COMPONENTS': {
        'securitySchemes': {
            'basicAuth': {
                'type': 'http',
                'scheme': 'basic',
                'description': '使用用户名和密码进行基本认证'
            },
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': '使用JWT Token进行认证，格式：Bearer <token>'
            },
            'cookieAuth': {
                'type': 'apiKey',
                'in': 'cookie',
                'name': 'sessionid',
                'description': '使用会话Cookie进行认证'
            }
        }
    },
}

# 指定认证方式
AUTHENTICATION_BACKENDS = (
    # 'apps.common.utils.account.CustomBackend',
    'apps.accounts.authentication.BusinessAuthBackend',
    'django.contrib.auth.backends.ModelBackend',  # default
)

# 字母验证码
CAPTCHA_IMAGE_SIZE = (120, 48)  # 设置 captcha 图片大小
CAPTCHA_LENGTH = 4  # 字符个数
CAPTCHA_TIMEOUT = 5  # 超时(minutes)

# JWT设置
SIMPLE_JWT = {
    # 时区设置
    'TIME_ZONE': 'Asia/Shanghai', 
    # 访问令牌的有效期，设置为5分钟
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=5),
    # 刷新令牌的有效期，设置为1天
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=1),
    # 是否在刷新访问令牌时旋转刷新令牌
    'ROTATE_REFRESH_TOKENS': False,
    # 在刷新令牌旋转后，是否将旧的刷新令牌加入黑名单
    'BLACKLIST_AFTER_ROTATION': True,
    # 是否在用户登录时更新他们的最后登录时间
    'UPDATE_LAST_LOGIN': True,
    # 签名算法
    'ALGORITHM': 'HS256',
    # 用于签名JWT的密钥
    'SIGNING_KEY': SECRET_KEY,
    # 用于验证JWT的公钥
    'VERIFYING_KEY': None,
    # 指定JWT的audience（受众）声明
    'AUDIENCE': None,
    # 指定JWT的issuer（发行者）声明
    'ISSUER': None,
    # 认证头部的类型
    'AUTH_HEADER_TYPES': ('Bearer',),
    # 认证头部的名称
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    # 用户模型中的字段，用于唯一标识用户
    'USER_ID_FIELD': 'id',
    # JWT中的声明，用于存储用户ID
    'USER_ID_CLAIM': 'user_id',
    # 用于确定用户是否通过认证的规则
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    # 允许的认证令牌类
    'AUTH_TOKEN_CLASSES': (
        'rest_framework_simplejwt.tokens.AccessToken',
    ),
    # JWT中的声明，用于标识令牌类型
    'TOKEN_TYPE_CLAIM': 'token_type',
    # 自定义的用户类，用于表示JWT中的用户信息
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    # JWT中的声明，用于存储JWT的唯一标识符
    'JTI_CLAIM': 'jti',
}
"""
            if 'REST_FRAMEWORK' not in settings_content:
                settings_content += rest_framework_config
            
            # 写入更新后的settings.py文件
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            
            print("settings.py文件更新成功")
            
        except Exception as e:
            print(f"更新settings.py文件时出错: {e}")
            sys.exit(1)

    def update_urls(self):
        """更新主urls.py文件"""
        print("正在更新urls.py...")
        
        urls_path = os.path.join(self.base_dir, self.project_name, 'urls.py')
        
        # 备份原始urls文件
        backup_file = f"{urls_path}.bak"
        if not os.path.exists(backup_file):
            shutil.copy2(urls_path, backup_file)
            print(f"已创建urls文件备份: {backup_file}")
        
        try:
            # 如果有模板文件，优先使用模板完全覆盖 urls.py
            urls_tpl_rel = self.template_config.get("urls_template")
            if urls_tpl_rel:
                urls_tpl_path = os.path.join(self.template_root, urls_tpl_rel)
                if os.path.exists(urls_tpl_path):
                    with open(urls_tpl_path, 'r', encoding='utf-8') as f:
                        tpl_content = f.read()
                    tpl_content = tpl_content.replace("{{ project_name }}", self.project_name)
                    with open(urls_path, 'w', encoding='utf-8') as f:
                        f.write(tpl_content)
                    print("已根据模板 urls_template 覆盖 urls.py")
                    return

            # 读取现有urls.py文件
            with open(urls_path, 'r', encoding='utf-8') as f:
                urls_content = f.read()
            
            # 检查是否已经包含我们要添加的路由
            has_accounts = 'path(\'accounts/\'' in urls_content
            has_common = 'path(\'common/\'' in urls_content
            has_spectacular = 'SpectacularAPIView' in urls_content
            has_captcha = 'path(\'captcha/\'' in urls_content
            has_static_media = 're_path(r\'media/' in urls_content
            
            # 如果已经包含大部分特征，可能已经是我们需要的格式
            if has_accounts and has_common and has_spectacular and has_captcha and has_static_media:
                print("urls.py已包含必要的配置，跳过更新")
                return
            
            # 创建新的urls.py内容
            urls_content = '''"""
URL configuration for {project_name} project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings

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
    re_path(r'media/(?P<path>.*)$', serve, {{'document_root': settings.MEDIA_ROOT}}),

    # 设置static路由
    re_path(r'static/(?P<path>.*)$', serve, {{'document_root': settings.STATIC_ROOT}}),
]
'''.format(project_name=self.project_name)
            
            # 写入新的urls.py文件
            with open(urls_path, 'w', encoding='utf-8') as f:
                f.write(urls_content)
            
            print("urls.py文件更新成功")
            
        except Exception as e:
            print(f"更新urls.py文件时出错: {e}")
            sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Django项目结构优化工具")
    parser.add_argument("project_name", help="项目名称")
    parser.add_argument("--path", help="项目路径，默认为当前目录", default=None)
    
    args = parser.parse_args()
    
    optimizer = DjangoProjectOptimizer(args.project_name, args.path)
    optimizer.run()


if __name__ == "__main__":
    main()