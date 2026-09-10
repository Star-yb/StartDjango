#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import argparse
import venv
import keyword
import importlib.util
import json
from pathlib import Path


class DjangoProjectCreator:
    """Django基础项目创建工具 - 只负责基础结构创建"""

    def __init__(self, project_name, project_path=None, use_venv=True, template_name=None):
        self.project_name = project_name
        self.project_path = project_path or os.getcwd()
        self.project_root = os.path.join(self.project_path, project_name)
        self.use_venv = use_venv
        self.venv_path = os.path.join(self.project_root, '.venv') if use_venv else None
        self.tool_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_name = template_name
        self.requirements_file = os.path.join(self.tool_dir, 'requirements.txt')
        self.pyproject_file = os.path.join(self.tool_dir, 'pyproject.toml')
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
        tpl_requirements = os.path.join(self.template_root, 'requirements.txt')
        if os.path.isfile(tpl_requirements):
            self.requirements_file = tpl_requirements
        tpl_pyproject = os.path.join(self.template_root, 'pyproject.toml')
        if os.path.isfile(tpl_pyproject):
            self.pyproject_file = tpl_pyproject
        self.env_manager = "pip"
        self._load_template_config()
        self.base_apps = ['accounts', 'common']
        self.directories = ['media', 'static', 'templates']

    def _load_template_config(self):
        if not os.path.exists(self.template_config_file):
            return
        try:
            with open(self.template_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"加载模板配置失败，继续使用默认 pip: {e}")
            return
        self.template_config = config or {}
        env_manager = self.template_config.get("env_manager") or self.template_config.get("dependency_manager")
        if isinstance(env_manager, str):
            env_manager = env_manager.lower().strip()
            if env_manager in {"pip", "uv"}:
                self.env_manager = env_manager
                print(f"从模板配置中读取到环境管理器: {self.env_manager}")

    def run(self):
        print(f"开始创建Django项目基础结构: {self.project_name}")
        try:
            self._simple_check()
            self._create_project_directory()
            if self.use_venv:
                self._create_virtual_environment()
            self._install_dependencies()
            self._create_django_project()
            self._create_basic_directories()
            self._copy_requirements()
            self._show_completion_info()
        except Exception as e:
            print(f"创建项目时出错: {e}")
            sys.exit(1)

    def _simple_check(self):
        print("检查基础环境...")
        if sys.version_info < (3, 8):
            raise Exception("需要Python 3.8或更高版本")
        print(f"Python {sys.version_info.major}.{sys.version_info.minor} 检查通过")
        self._validate_project_name()

    def _validate_project_name(self):
        print("验证项目名称...")
        if keyword.iskeyword(self.project_name):
            raise Exception(f"项目名称 '{self.project_name}' 是Python关键字，请使用其他名称")
        if not self.project_name.replace('_', '').replace('-', '').isalnum():
            raise Exception(f"项目名称 '{self.project_name}' 包含特殊字符，只能包含字母、数字、下划线和连字符")
        if self.project_name[0].isdigit():
            raise Exception(f"项目名称 '{self.project_name}' 不能以数字开头")
        print(f"项目名称 '{self.project_name}' 验证通过")

    def _create_project_directory(self):
        print(f"创建项目目录: {self.project_root}")
        if os.path.exists(self.project_root):
            choice = input(f"目录 {self.project_root} 已存在，是否删除并重新创建? [y/N]: ").lower()
            if choice == 'y':
                shutil.rmtree(self.project_root)
                print("已删除现有目录")
            else:
                raise Exception("项目目录已存在，操作被取消")
        os.makedirs(self.project_root, exist_ok=True)
        print("项目目录创建成功")

    def _create_virtual_environment(self):
        print("创建虚拟环境...")
        if self.env_manager == "uv":
            try:
                print("使用 uv 创建虚拟环境 (.venv)...")
                subprocess.run(["uv", "venv", ".venv"], check=True, cwd=self.project_root)
                print("uv 虚拟环境创建成功")
                return
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"uv 创建虚拟环境失败，将回退到 venv: {e}")
        try:
            venv.create(self.venv_path, with_pip=True)
            print("虚拟环境创建成功")
        except Exception as e:
            print(f"虚拟环境创建失败: {e}")
            print("将使用系统Python环境")
            self.use_venv = False
            self.venv_path = None

    def _get_python_executable(self):
        if self.use_venv and self.venv_path:
            if os.name == 'nt':
                return os.path.join(self.venv_path, 'Scripts', 'python.exe')
            return os.path.join(self.venv_path, 'bin', 'python')
        return sys.executable

    def _install_dependencies(self):
        print("安装依赖包...")
        if self.env_manager == "uv" and os.path.exists(self.pyproject_file):
            try:
                dest_pyproject = os.path.join(self.project_root, "pyproject.toml")
                shutil.copy2(self.pyproject_file, dest_pyproject)
                print(f"已复制 pyproject.toml 到项目目录: {dest_pyproject}")
                try:
                    with open(dest_pyproject, "r", encoding="utf-8") as f:
                        pyproject_content = f.read()
                    if 'name = "NINJA"' in pyproject_content:
                        pyproject_content = pyproject_content.replace('name = "NINJA"', f'name = "{self.project_name}"')
                    if "[[tool.uv.index]]" not in pyproject_content:
                        pyproject_content += "\n\n[[tool.uv.index]]\nurl = \"https://pypi.tuna.tsinghua.edu.cn/simple\"\ndefault = true\n"
                    with open(dest_pyproject, "w", encoding="utf-8") as f:
                        f.write(pyproject_content)
                    print("已根据项目名称和镜像源更新 pyproject.toml")
                except Exception as e:
                    print(f"更新 pyproject.toml 时出错，将继续使用原始文件: {e}")
                print("使用 uv sync 安装依赖...")
                subprocess.run(["uv", "sync"], check=True, cwd=self.project_root)
                print("依赖包安装完成（uv）")
                return
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"使用 uv 安装依赖失败，将回退到 pip: {e}")
        if not os.path.exists(self.requirements_file):
            raise Exception(f"找不到requirements.txt文件: {self.requirements_file}")
        python_cmd = self._get_python_executable()
        try:
            print("  正在从清华镜像源安装依赖...")
            subprocess.run([
                python_cmd, "-m", "pip", "install", "-r", self.requirements_file,
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            ], check=True, cwd=self.project_root)
            print("依赖包安装完成（pip）")
        except subprocess.CalledProcessError as e:
            raise Exception(f"依赖包安装失败: {e}")

    def _create_django_project(self):
        print(f"创建Django项目: {self.project_name}")
        python_cmd = self._get_python_executable()
        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        try:
            subprocess.run([python_cmd, '-m', 'django', 'startproject', self.project_name, '.'], check=True)
            print("Django项目创建成功")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Django项目创建失败: {e}")
        finally:
            os.chdir(original_cwd)

    def _create_basic_directories(self):
        print("创建基础目录结构...")
        for directory in self.directories:
            dir_path = os.path.join(self.project_root, directory)
            os.makedirs(dir_path, exist_ok=True)
            with open(os.path.join(dir_path, '.gitkeep'), 'w') as f:
                pass
        print("基础目录结构创建完成")

    def _copy_requirements(self):
        if self.env_manager == "uv":
            print("当前使用 uv 管理依赖，不再复制 requirements.txt 到项目目录")
            return
        dest_path = os.path.join(self.project_root, 'requirements.txt')
        shutil.copy2(self.requirements_file, dest_path)
        print("requirements.txt已复制到项目目录")

    def _show_completion_info(self):
        print("\n" + "="*50)
        print("基础Django项目创建完成！")
        print("="*50)
        print(f"项目位置: {self.project_root}")
        if self.use_venv:
            print(f"虚拟环境: {self.venv_path}")
        print("\n注意: 项目结构优化将由django-helper.py完成")


def main():
    parser = argparse.ArgumentParser(description="Django基础项目创建工具")
    parser.add_argument("project_name", help="项目名称")
    parser.add_argument("--path", help="项目路径，默认为当前目录", default=None)
    parser.add_argument("--no-venv", action="store_true", help="不创建虚拟环境")
    args = parser.parse_args()
    creator = DjangoProjectCreator(
        project_name=args.project_name,
        project_path=args.path,
        use_venv=not args.no_venv
    )
    creator.run()


if __name__ == "__main__":
    main()
