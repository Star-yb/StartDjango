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
            
            # 4. 安装依赖
            self._install_dependencies()
            
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
                # 在项目根目录下执行 uv venv .venv
                subprocess.run(
                    ["uv", "venv", ".venv"],
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

    def _get_python_executable(self):
        """获取Python可执行文件路径"""
        if self.use_venv and self.venv_path:
            if os.name == 'nt':  # Windows
                return os.path.join(self.venv_path, 'Scripts', 'python.exe')
            else:  # Unix-like
                return os.path.join(self.venv_path, 'bin', 'python')
        return sys.executable

    def _install_dependencies(self):
        """安装依赖包"""
        print("安装依赖包...")

        # 如果配置为使用 uv，并且存在 pyproject.toml，则使用 uv sync 管理依赖
        if self.env_manager == "uv" and os.path.exists(self.pyproject_file):
            try:
                # 将工具目录下的 pyproject.toml 复制到项目根目录
                dest_pyproject = os.path.join(self.project_root, "pyproject.toml")
                shutil.copy2(self.pyproject_file, dest_pyproject)
                print(f"已复制 pyproject.toml 到项目目录: {dest_pyproject}")

                # 根据当前项目名称和镜像源，调整 pyproject.toml
                try:
                    with open(dest_pyproject, "r", encoding="utf-8") as f:
                        pyproject_content = f.read()

                    # 保证 [project] name 等于当前项目名
                    if 'name = "NINJA"' in pyproject_content:
                        pyproject_content = pyproject_content.replace(
                            'name = "NINJA"',
                            f'name = "{self.project_name}"',
                        )

                    # 为 uv 增加清华镜像配置（若尚未配置）
                    if "[[tool.uv.index]]" not in pyproject_content:
                        pyproject_content += """

[[tool.uv.index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
"""
                    with open(dest_pyproject, "w", encoding="utf-8") as f:
                        f.write(pyproject_content)

                    print("已根据项目名称和镜像源更新 pyproject.toml")
                except Exception as e:
                    print(f"更新 pyproject.toml 时出错，将继续使用原始文件: {e}")

                print("使用 uv sync 安装依赖...")
                subprocess.run(
                    ["uv", "sync"],
                    check=True,
                    cwd=self.project_root,
                )
                print("依赖包安装完成（uv）")
                return
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"使用 uv 安装依赖失败，将回退到 pip: {e}")
                # 回退到 pip 安装 requirements.txt

        # 回退或默认：使用 pip + requirements.txt
        if not os.path.exists(self.requirements_file):
            raise Exception(f"找不到requirements.txt文件: {self.requirements_file}")

        python_cmd = self._get_python_executable()

        try:
            # 使用清华镜像源安装依赖
            print("  正在从清华镜像源安装依赖...")
            subprocess.run(
                [
                    python_cmd,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    self.requirements_file,
                    "-i",
                    "https://pypi.tuna.tsinghua.edu.cn/simple",
                ],
                check=True,
                cwd=self.project_root,
            )
            print("依赖包安装完成（pip）")

        except subprocess.CalledProcessError as e:
            raise Exception(f"依赖包安装失败: {e}")

    def _create_django_project(self):
        """创建Django项目"""
        print(f"创建Django项目: {self.project_name}")
        
        python_cmd = self._get_python_executable()
        
        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        
        try:
            subprocess.run([python_cmd, '-m', 'django', 'startproject', 
                          self.project_name, '.'], check=True)
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
        # 如果当前使用 uv 管理依赖，则不再复制 requirements.txt
        if self.env_manager == "uv":
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
        
        print("\n基础结构:")
        print("- Django项目框架")
        print("- 虚拟环境 (.venv)")
        print("- 依赖包安装完成")
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