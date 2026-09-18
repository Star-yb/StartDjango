#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
import subprocess
import argparse
import venv
import keyword
import secrets
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

        # 工具所在目录
        self.tool_dir = os.path.dirname(os.path.abspath(__file__))

        # 模板版本名称（对应 templates/<name>/）
        self.template_name = template_name

        # 默认依赖文件（无模板或老版本时使用）
        self.requirements_file = os.path.join(self.tool_dir, 'requirements.txt')
        self.pyproject_file = os.path.join(self.tool_dir, 'pyproject.toml')

        # 基础模板根目录
        base_templates_root = os.path.join(self.tool_dir, 'templates')

        # 根据模板版本选择具体模板目录
        if self.template_name:
            candidate_root = os.path.join(base_templates_root, self.template_name)
            if os.path.isdir(candidate_root):
                self.template_root = candidate_root
            else:
                print(f"警告: 模板版本 '{self.template_name}' 未找到，将回退到默认 templates 目录（如存在）。")
                self.template_root = base_templates_root
        else:
            self.template_root = base_templates_root

        # 模板配置文件路径
        self.template_config_file = os.path.join(self.template_root, 'config.json')
        self.template_config = {}

        # 如果当前选择的模板目录下存在专用的 requirements/pyproject，则优先使用
        tpl_requirements = os.path.join(self.template_root, 'requirements.txt')
        if os.path.isfile(tpl_requirements):
            self.requirements_file = tpl_requirements
        tpl_pyproject = os.path.join(self.template_root, 'pyproject.toml')
        if os.path.isfile(tpl_pyproject):
            self.pyproject_file = tpl_pyproject

        # 依赖/虚拟环境管理器：默认使用 pip + venv，可通过模板配置切换为 uv
        self.env_manager = "pip"  # 或 "uv"

        # 读取模板配置（如果存在），覆盖 env_manager 等设置
        self._load_template_config()
        
        # 基础应用列表（目前未在本文件中使用，保留占位）
        self.base_apps = ['accounts', 'common']
        self.directories = ['media', 'static', 'templates']

    def _load_template_config(self):
        """从模板配置中读取环境管理设置（如选择 uv）"""
        if not os.path.exists(self.template_config_file):
            return

        try:
            with open(self.template_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"加载模板配置失败，继续使用默认 pip: {e}")
            return

        self.template_config = config or {}

        # 允许在 config.json 里配置 env_manager / dependency_manager，值为 'pip' 或 'uv'
        env_manager = (
            self.template_config.get("env_manager")
            or self.template_config.get("dependency_manager")
        )
        if isinstance(env_manager, str):
            env_manager = env_manager.lower().strip()
            if env_manager in {"pip", "uv"}:
                self.env_manager = env_manager
                print(f"从模板配置中读取到环境管理器: {self.env_manager}")

    def run(self):
        """执行基础项目创建流程"""
        print(f"开始创建Django项目基础结构: {self.project_name}")
        
        try:
            # 1. 简单环境检查
            self._simple_check()
            
            # 2. 创建项目目录
            self._create_project_directory()
            
            # 3. 创建虚拟环境（可选）
            if self.use_venv:
                self._create_virtual_environment()
            
            # 4. 复制依赖清单；仅在创建虚拟环境时才安装依赖
            self._copy_dependency_manifests()
            if self.use_venv:
                self._install_dependencies()
            else:
                print("已选择不创建虚拟环境：跳过全部依赖安装")
                print("不会创建 .venv，也不会向系统 Python 安装任何包")
            
            # 5. 创建Django项目
            self._create_django_project()
            
            # 6. 创建基础目录结构
            self._create_basic_directories()
            
            # 7. 复制requirements.txt
            self._copy_requirements()
            
            # 8. 显示完成信息
            self._show_completion_info()
            
        except Exception as e:
            print(f"创建项目时出错: {e}")
            sys.exit(1)

    def _simple_check(self):
        """简化的环境检查"""
        print("检查基础环境...")
        
        # 只检查Python版本和pip
        if sys.version_info < (3, 8):
            raise Exception("需要Python 3.8或更高版本")
        
        print(f"Python {sys.version_info.major}.{sys.version_info.minor} 检查通过")
        
        # 检查项目名称
        self._validate_project_name()

    def _validate_project_name(self):
        """验证项目名称"""
        print("验证项目名称...")
        
        # 检查是否为Python关键字
        if keyword.iskeyword(self.project_name):
            raise Exception(f"项目名称 '{self.project_name}' 是Python关键字，请使用其他名称")
        
        # 检查是否与Python内置模块冲突
        forbidden_names = [
            'abc', 'ast', 'io', 'os', 're', 'sys', 'json', 'math', 'time', 'datetime',
            'random', 'collections', 'itertools', 'functools', 'operator', 'pathlib',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3', 'pickle',
            'hashlib', 'hmac', 'secrets', 'ssl', 'socket', 'threading', 'multiprocessing',
            'subprocess', 'argparse', 'logging', 'unittest', 'doctest', 'pdb',
            'profile', 'timeit', 'trace', 'gc', 'weakref', 'copy', 'pprint',
            'reprlib', 'enum', 'numbers', 'cmath', 'decimal', 'fractions', 'statistics',
            'array', 'struct', 'codecs', 'unicodedata', 'stringprep', 'readline',
            'rlcompleter', 'shutil', 'glob', 'fnmatch', 'linecache', 'tempfile',
            'gzip', 'bz2', 'lzma', 'zipfile', 'tarfile', 'configparser', 'netrc',
            'xdrlib', 'plistlib', 'calendar', 'hashlib', 'zlib', 'binascii',
            'base64', 'uu', 'quopri', 'textwrap', 'string', 'difflib'
        ]
        
        if self.project_name.lower() in forbidden_names:
            suggestions = [
                f"{self.project_name}_project",
                f"my_{self.project_name}",
                f"{self.project_name}_app",
                f"{self.project_name}_web"
            ]
            raise Exception(
                f"项目名称 '{self.project_name}' 与Python内置模块冲突，请使用其他名称。\n"
                f"建议使用: {', '.join(suggestions)}"
            )
        
        # 检查是否包含特殊字符
        if not self.project_name.replace('_', '').replace('-', '').isalnum():
            raise Exception(f"项目名称 '{self.project_name}' 包含特殊字符，只能包含字母、数字、下划线和连字符")
        
        # 检查是否以数字开头
        if self.project_name[0].isdigit():
            raise Exception(f"项目名称 '{self.project_name}' 不能以数字开头")
        
        print(f"项目名称 '{self.project_name}' 验证通过")

    def _create_project_directory(self):
        """创建项目目录"""
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
        """创建虚拟环境"""
        print("创建虚拟环境...")

        # 优先使用 uv 创建虚拟环境（如果配置为 uv）
        if self.env_manager == "uv":
            try:
                print("使用 uv 创建虚拟环境 (.venv)...")
                # --seed 会安装 pip，避免后续回退 python -m pip 时找不到模块
                subprocess.run(
                    ["uv", "venv", "--seed", ".venv"],
                    check=True,
                    cwd=self.project_root,
                )
                print("uv 虚拟环境创建成功")
                return
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"uv 创建虚拟环境失败，将回退到 venv: {e}")
                # 回退到 venv

        # 默认使用标准库 venv
        try:
            venv.create(self.venv_path, with_pip=True)
            print("虚拟环境创建成功")
        except Exception as e:
            print(f"虚拟环境创建失败: {e}")
            print("将使用系统Python环境")
            self.use_venv = False
            self.venv_path = None

    def _venv_python_path(self):
        """返回项目 .venv 中的 Python 路径（文件不一定存在）。"""
        venv_root = self.venv_path or os.path.join(self.project_root, '.venv')
        if os.name == 'nt':
            return os.path.join(venv_root, 'Scripts', 'python.exe')
        return os.path.join(venv_root, 'bin', 'python')

    def _get_python_executable(self):
        """按用户选择返回解释器：要虚拟环境才用 .venv，否则始终用系统 Python。"""
        if self.use_venv:
            venv_python = self._venv_python_path()
            if os.path.isfile(venv_python):
                return venv_python
            print("未找到虚拟环境 Python，将使用系统 Python")
            self.use_venv = False
            self.venv_path = None
        return sys.executable

    def _prepare_pyproject(self, dest_pyproject):
        """把模板 pyproject.toml 的项目名和镜像源改成当前项目可用的配置。"""
        with open(dest_pyproject, "r", encoding="utf-8") as f:
            pyproject_content = f.read()

        pyproject_content = re.sub(
            r'(?m)^name\s*=\s*"[^"]+"',
            f'name = "{self.project_name}"',
            pyproject_content,
            count=1,
        )

        if "[[tool.uv.index]]" not in pyproject_content:
            pyproject_content += """

[[tool.uv.index]]
name = "tuna"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
"""

        if 'url = "https://pypi.org/simple"' not in pyproject_content:
            pyproject_content += """

[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple"
"""

        with open(dest_pyproject, "w", encoding="utf-8") as f:
            f.write(pyproject_content)

    def _read_pyproject_dependencies(self, pyproject_path):
        """读取 pyproject.toml 里 [project].dependencies，避免和 requirements.txt 各装一套。"""
        if not os.path.isfile(pyproject_path):
            return []
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.S)
        if not match:
            return []
        return re.findall(r'"([^"]+)"', match.group(1))

    def _install_package_spec(self):
        """安装参数：优先项目 pyproject.toml 的 dependencies，否则 requirements.txt。"""
        dest_pyproject = os.path.join(self.project_root, "pyproject.toml")
        dependencies = self._read_pyproject_dependencies(dest_pyproject)
        if dependencies:
            return dependencies
        if os.path.isfile(self.requirements_file):
            return ["-r", self.requirements_file]
        raise Exception(f"找不到可安装的依赖清单: {dest_pyproject} 或 {self.requirements_file}")

    def _install_with_uv_pip(self, index_url):
        """用 uv pip 把依赖装进当前选定的解释器。系统 Python 需加 --system。"""
        python_cmd = self._get_python_executable()
        command = [
            "uv",
            "pip",
            "install",
            "--python",
            python_cmd,
            "-i",
            index_url,
        ]
        if not self.use_venv:
            command.append("--system")
        command.extend(self._install_package_spec())
        subprocess.run(command, check=True, cwd=self.project_root)

    def _install_with_python_pip(self, index_url):
        """用 python -m pip 安装依赖；若环境没有 pip 则先 ensurepip。"""
        python_cmd = self._get_python_executable()
        subprocess.run(
            [python_cmd, "-m", "ensurepip", "--upgrade"],
            check=False,
            cwd=self.project_root,
        )
        command = [
            python_cmd,
            "-m",
            "pip",
            "install",
            "-i",
            index_url,
        ]
        command.extend(self._install_package_spec())
        subprocess.run(command, check=True, cwd=self.project_root)

    def _copy_dependency_manifests(self):
        """只复制依赖清单，不执行安装。"""
        if os.path.isfile(self.pyproject_file):
            dest_pyproject = os.path.join(self.project_root, "pyproject.toml")
            shutil.copy2(self.pyproject_file, dest_pyproject)
            try:
                self._prepare_pyproject(dest_pyproject)
                print(f"已复制并更新 pyproject.toml: {dest_pyproject}")
            except Exception as e:
                print(f"更新 pyproject.toml 时出错，将继续使用原始文件: {e}")

    def _install_dependencies(self):
        """仅在创建虚拟环境时安装依赖。优先 uv sync，失败再回退 uv pip / pip。"""
        print("安装依赖包...")
        tuna_index = "https://pypi.tuna.tsinghua.edu.cn/simple"
        pypi_index = "https://pypi.org/simple"

        dest_pyproject = os.path.join(self.project_root, "pyproject.toml")
        if self.env_manager == "uv" and os.path.isfile(dest_pyproject):
            uv_sync_attempts = [
                (["uv", "sync"], "清华镜像"),
                (["uv", "sync", "--index-url", pypi_index], "官方 PyPI"),
            ]
            for command, source_name in uv_sync_attempts:
                try:
                    print(f"使用 uv sync 安装依赖（{source_name}）...")
                    subprocess.run(command, check=True, cwd=self.project_root)
                    print(f"依赖包安装完成（uv / {source_name}）")
                    return
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f"uv sync（{source_name}）失败: {e}")
            print("uv sync 失败，将回退到 uv pip / pip")

        pip_attempts = [
            (self._install_with_uv_pip, tuna_index, "uv pip + 清华镜像"),
            (self._install_with_uv_pip, pypi_index, "uv pip + 官方 PyPI"),
            (self._install_with_python_pip, tuna_index, "pip + 清华镜像"),
            (self._install_with_python_pip, pypi_index, "pip + 官方 PyPI"),
        ]
        last_error = None
        for installer, index_url, label in pip_attempts:
            try:
                print(f"正在使用 {label} 安装依赖...")
                installer(index_url)
                print(f"依赖包安装完成（{label}）")
                return
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"{label} 失败: {e}")
                last_error = e

        raise Exception(f"依赖包安装失败: {last_error}")

    def _write_django_project_skeleton(self):
        """不依赖本机是否已安装 Django，直接写出 startproject 骨架。"""
        project_package = os.path.join(self.project_root, self.project_name)
        os.makedirs(project_package, exist_ok=True)

        secret_key = secrets.token_urlsafe(50)
        manage_py = f'''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{self.project_name}.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''
        init_py = ""
        settings_py = f'''from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "{secret_key}"

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "{self.project_name}.urls"

TEMPLATES = [
    {{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {{
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        }},
    }},
]

WSGI_APPLICATION = "{self.project_name}.wsgi.application"

DATABASES = {{
    "default": {{
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }}
}}

AUTH_PASSWORD_VALIDATORS = [
    {{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}},
    {{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'''
        urls_py = '''from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
'''
        wsgi_py = f'''import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{self.project_name}.settings")

application = get_wsgi_application()
'''
        asgi_py = f'''import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{self.project_name}.settings")

application = get_asgi_application()
'''

        with open(os.path.join(self.project_root, "manage.py"), "w", encoding="utf-8") as f:
            f.write(manage_py)
        with open(os.path.join(project_package, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(init_py)
        with open(os.path.join(project_package, "settings.py"), "w", encoding="utf-8") as f:
            f.write(settings_py)
        with open(os.path.join(project_package, "urls.py"), "w", encoding="utf-8") as f:
            f.write(urls_py)
        with open(os.path.join(project_package, "wsgi.py"), "w", encoding="utf-8") as f:
            f.write(wsgi_py)
        with open(os.path.join(project_package, "asgi.py"), "w", encoding="utf-8") as f:
            f.write(asgi_py)

    def _create_django_project(self):
        """创建Django项目。无虚拟环境时不调用本机 Django，只写骨架文件。"""
        print(f"创建Django项目: {self.project_name}")

        if not self.use_venv:
            self._write_django_project_skeleton()
            print("已写入 Django 项目骨架（未安装依赖，未调用系统 Django）")
            return

        python_cmd = self._get_python_executable()
        print(f"使用 Python: {python_cmd}")

        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        try:
            subprocess.run(
                [python_cmd, "-m", "django", "startproject", self.project_name, "."],
                check=True,
            )
            print("Django项目创建成功")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Django项目创建失败: {e}")
        finally:
            os.chdir(original_cwd)

    def _create_basic_directories(self):
        """创建基础目录结构"""
        print("创建基础目录结构...")
        
        for directory in self.directories:
            dir_path = os.path.join(self.project_root, directory)
            os.makedirs(dir_path, exist_ok=True)
            
            # 创建.gitkeep文件
            gitkeep_path = os.path.join(dir_path, '.gitkeep')
            with open(gitkeep_path, 'w') as f:
                pass
        
        print("基础目录结构创建完成")




    def _copy_requirements(self):
        """复制requirements.txt到项目目录"""
        # 仅在使用 uv + 虚拟环境时以 pyproject.toml 为准，不再复制 requirements.txt
        if self.env_manager == "uv" and self.use_venv:
            print("当前使用 uv 管理依赖，不再复制 requirements.txt 到项目目录")
            return

        dest_path = os.path.join(self.project_root, 'requirements.txt')
        shutil.copy2(self.requirements_file, dest_path)
        print("requirements.txt已复制到项目目录")

    def _show_completion_info(self):
        """显示基础项目创建完成信息"""
        print("\n" + "="*50)
        print("基础Django项目创建完成！")
        print("="*50)
        print(f"项目位置: {self.project_root}")
        if self.use_venv:
            print(f"虚拟环境: {self.venv_path}")
            print("依赖安装: 已完成")
        else:
            print("虚拟环境: 未创建")
            print("依赖安装: 已跳过（未写入系统 Python）")
        
        print("\n基础结构:")
        print("- Django项目框架")
        if self.use_venv:
            print("- 虚拟环境 (.venv)")
            print("- 依赖包安装完成")
        else:
            print("- 依赖清单已复制（pyproject.toml / requirements.txt）")
        print("- 基础目录 (media, static, templates)")
        
        print("\n注意: 项目结构优化将由django-helper.py完成")


def main():
    """主函数 - 创建基础Django项目"""
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