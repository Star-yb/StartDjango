#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import argparse
import json


def _parse_settings_blocks(content):
    lines = content.splitlines(keepends=True)
    blocks = []
    i = 0
    var_pattern = re.compile(r'^\s*([A-Z_][A-Z0-9_]*)\s*=')
    while i < len(lines):
        line = lines[i]
        match = var_pattern.match(line)
        if match:
            var_name = match.group(1)
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
            chunk = []
            while i < len(lines) and not var_pattern.match(lines[i]):
                chunk.append(lines[i])
                i += 1
            if chunk:
                blocks.append((None, ''.join(chunk)))
    return blocks


def _merge_settings_blocks(original_blocks, template_blocks):
    template_by_name = {name: text for name, text in template_blocks if name is not None}
    used_from_template = set()
    result = []
    for name, text in original_blocks:
        if name is None:
            result.append((None, text))
        elif name in template_by_name:
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
    def __init__(self, project_name, project_path=None, template_name=None):
        self.project_name = project_name
        self.project_path = project_path or os.getcwd()
        self.base_dir = self.project_path
        self.apps_dir = os.path.join(self.base_dir, 'apps')
        self.tool_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_name = template_name
        base_templates_root = os.path.join(self.tool_dir, 'templates')
        if self.template_name:
            candidate_root = os.path.join(base_templates_root, self.template_name)
            self.template_root = candidate_root if os.path.isdir(candidate_root) else base_templates_root
        else:
            self.template_root = base_templates_root
        self.template_config_file = os.path.join(self.template_root, 'config.json')
        self.template_config = {}
        self.base_apps = ['accounts', 'common']
        self.directories = ['media', 'static', 'templates']

    def run(self):
        print(f"开始优化Django项目: {self.project_name}")
        if not self.check_project_exists():
            print(f"错误: 项目 {self.project_name} 不存在于路径 {self.base_dir}")
            sys.exit(1)
        self.load_template_config()
        self.create_directories()
        self.create_apps()
        self.update_settings()
        self.update_urls()
        print(f"\n项目 {self.project_name} 已成功优化！")
        print("python manage.py migrate")
        print("python manage.py createsuperuser")
        print("python manage.py runserver")

    def check_project_exists(self):
        if not os.path.exists(os.path.join(self.base_dir, 'manage.py')):
            return False
        if not os.path.exists(os.path.join(self.base_dir, self.project_name)):
            return False
        if not os.path.exists(os.path.join(self.base_dir, self.project_name, 'settings.py')):
            return False
        return True

    def load_template_config(self):
        if not os.path.exists(self.template_config_file):
            return
        try:
            with open(self.template_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as exc:
            print(f"加载模板配置文件失败，忽略模板配置: {exc}")
            return
        self.template_config = config or {}
        dirs = self.template_config.get("directories")
        if isinstance(dirs, list) and dirs:
            self.directories = dirs
            print(f"使用模板配置的基础目录: {self.directories}")
        apps = self.template_config.get("apps")
        if isinstance(apps, list) and apps:
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
        print("正在创建基础目录...")
        for directory in self.directories:
            os.makedirs(os.path.join(self.base_dir, directory), exist_ok=True)
            print(f"已创建/确认目录: {directory}")
            gitkeep_path = os.path.join(self.base_dir, directory, '.gitkeep')
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, 'w') as f:
                    pass

    def create_apps(self):
        print("正在创建apps目录和应用...")
        os.makedirs(self.apps_dir, exist_ok=True)
        with open(os.path.join(self.apps_dir, '__init__.py'), 'w', encoding='utf-8') as f:
            pass
        for app_name in self.base_apps:
            self._create_app(app_name)

    def _create_app(self, app_name):
        print(f"正在创建应用: {app_name}")
        app_dir = os.path.join(self.apps_dir, app_name)
        if os.path.exists(app_dir):
            print(f"警告: 应用 {app_name} 已存在!")
            choice = input(f"是否覆盖应用 {app_name}? [y/N]: ").lower()
            if choice != 'y':
                print(f"跳过创建应用 {app_name}")
                return
            shutil.rmtree(app_dir)
        app_template_dir = os.path.join(self.template_root, 'apps', app_name)
        if os.path.isdir(app_template_dir):
            shutil.copytree(app_template_dir, app_dir)
            print(f"已从模板目录创建应用: {app_name}")
            return
        os.makedirs(app_dir, exist_ok=True)
        files = {
            '__init__.py': '',
            'admin.py': 'from django.contrib import admin\n\n# Register your models here.\n',
            'apps.py': (
                f"from django.apps import AppConfig\n\n\nclass {app_name.capitalize()}Config(AppConfig):\n"
                f"    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.{app_name}'\n"
            ),
            'models.py': 'from django.db import models\n\n# Create your models here.\n',
            'views.py': 'from rest_framework.views import APIView\nfrom apps.common.utils.response import Response\n\n# Create your views here.\n',
            'urls.py': 'from django.urls import path\n\nurlpatterns = []\n',
            'tests.py': 'from django.test import TestCase\n\n# Create your tests here.\n',
        }
        for filename, content in files.items():
            with open(os.path.join(app_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)
        migrations_dir = os.path.join(app_dir, 'migrations')
        os.makedirs(migrations_dir, exist_ok=True)
        with open(os.path.join(migrations_dir, '__init__.py'), 'w', encoding='utf-8') as f:
            pass
        print(f"应用 {app_name} 创建成功")

    def update_settings(self):
        print("正在更新settings.py...")
        settings_path = os.path.join(self.base_dir, self.project_name, 'settings.py')
        backup_file = f"{settings_path}.bak"
        if not os.path.exists(backup_file):
            shutil.copy2(settings_path, backup_file)
            print(f"已创建设置文件备份: {backup_file}")
        try:
            settings_tpl_rel = self.template_config.get("settings_template")
            if settings_tpl_rel:
                settings_tpl_path = os.path.join(self.template_root, settings_tpl_rel)
                if os.path.exists(settings_tpl_path):
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    with open(settings_tpl_path, 'r', encoding='utf-8') as f:
                        tpl_content = f.read()
                    tpl_content = tpl_content.replace("{{ project_name }}", self.project_name)
                    settings_mode = (self.template_config.get("settings_mode") or "merge").strip().lower()
                    if settings_mode == "replace":
                        with open(settings_path, 'w', encoding='utf-8') as f:
                            f.write(tpl_content)
                        print("已根据模板 settings_template 整文件覆盖 settings.py（settings_mode=replace）")
                    else:
                        original_blocks = _parse_settings_blocks(original_content)
                        template_blocks = _parse_settings_blocks(tpl_content)
                        merged = _merge_settings_blocks(original_blocks, template_blocks)
                        merged_content = _blocks_to_content(merged).replace("{{ project_name }}", self.project_name)
                        with open(settings_path, 'w', encoding='utf-8') as f:
                            f.write(merged_content)
                        print("已根据模板 settings_template 按变量覆盖 settings.py 中对应配置（settings_mode=merge）")
                    return
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_content = f.read()
            if 'import os' not in settings_content:
                settings_content = 'import os\nimport datetime\n' + settings_content
            settings_content = settings_content.replace('ALLOWED_HOSTS = []', 'ALLOWED_HOSTS = ["*"]')
            settings_content = settings_content.replace("LANGUAGE_CODE = 'en-us'", "LANGUAGE_CODE = 'zh-hans'")
            settings_content = settings_content.replace("TIME_ZONE = 'UTC'", "TIME_ZONE = 'Asia/Shanghai'")
            if 'CORS_ALLOW_ALL_ORIGINS' not in settings_content:
                settings_content += "\n# CORS跨域\nCORS_ALLOW_ALL_ORIGINS = True\n"
            if 'REST_FRAMEWORK' not in settings_content:
                settings_content += (
                    "\nREST_FRAMEWORK = {\n"
                    "    'DEFAULT_AUTHENTICATION_CLASSES': [\n"
                    "        'rest_framework_simplejwt.authentication.JWTAuthentication',\n"
                    "        'rest_framework.authentication.SessionAuthentication',\n"
                    "    ],\n"
                    "    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],\n"
                    "    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',\n}\n"
                )
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            print("settings.py文件更新成功")
        except Exception as exc:
            print(f"更新settings.py文件时出错: {exc}")
            sys.exit(1)

    def update_urls(self):
        print("正在更新urls.py...")
        urls_path = os.path.join(self.base_dir, self.project_name, 'urls.py')
        backup_file = f"{urls_path}.bak"
        if not os.path.exists(backup_file):
            shutil.copy2(urls_path, backup_file)
            print(f"已创建urls文件备份: {backup_file}")
        try:
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
            print("urls.py 无模板，跳过覆盖")
        except Exception as exc:
            print(f"更新urls.py文件时出错: {exc}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Django项目结构优化工具")
    parser.add_argument("project_name", help="项目名称")
    parser.add_argument("--path", help="项目路径，默认为当前目录", default=None)
    args = parser.parse_args()
    DjangoProjectOptimizer(args.project_name, args.path).run()


if __name__ == "__main__":
    main()
