#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Django项目创建工具启动脚本
提供交互式项目创建体验
"""

import os
import sys
import subprocess


def show_banner():
    """显示欢迎信息"""
    banner = """
╔══════════════════════════════════════════════════════╗
║                Django 项目创建工具                    ║
║                                                      ║
║    快速创建Django项目                                ║
║    集成最佳实践配置                                  ║
║    自动生成API文档                                   ║
║    内置JWT认证系统                                   ║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)


def get_user_input():
    """获取用户输入"""
    print("请输入项目配置信息:")
    
    # 项目名称
    while True:
        project_name = input("项目名称: ").strip()
        if not project_name:
            print("项目名称不能为空，请重新输入")
            continue
            
        # 基本验证
        if not validate_project_name(project_name):
            continue
        break
    
    # 项目路径
    project_path = input("项目路径 (留空使用当前目录): ").strip()
    if not project_path:
        project_path = os.getcwd()
    
    # 虚拟环境
    while True:
        use_venv = input("是否创建虚拟环境? [Y/n]: ").strip().lower()
        if use_venv in ['', 'y', 'yes']:
            use_venv = True
            break
        elif use_venv in ['n', 'no']:
            use_venv = False
            break
        print("请输入 y/yes 或 n/no")
    
    return project_name, project_path, use_venv


def choose_template():
    """
    选择模板版本。
    
    返回值:
        - 模板名称（即 templates/<name>/ 目录名）
        - 或 None 表示不使用模板，走默认 requirements.txt 流程
    """
    tool_dir = os.getcwd()
    templates_root = os.path.join(tool_dir, "templates")

    if not os.path.isdir(templates_root):
        print("\n未检测到 templates 目录，将使用默认 requirements.txt 流程。")
        return None

    # 查找所有子目录作为模板版本
    candidates = [
        name for name in os.listdir(templates_root)
        if os.path.isdir(os.path.join(templates_root, name))
    ]

    if not candidates:
        print("\ntemplates 目录为空，将使用默认 requirements.txt 流程。")
        return None

    print("\n可用模板版本:")
    for idx, name in enumerate(candidates, start=1):
        print(f"  {idx}. {name}")
    print("  0. 不使用模板（默认 requirements.txt + pip）")

    while True:
        choice = input("\n请选择模板版本编号 (回车默认 0): ").strip()
        if choice == "":
            return None
        if not choice.isdigit():
            print("请输入数字编号。")
            continue
        choice_idx = int(choice)
        if choice_idx == 0:
            return None
        if 1 <= choice_idx <= len(candidates):
            return candidates[choice_idx - 1]
        print("编号超出范围，请重新输入。")


def validate_project_name(project_name):
    """验证项目名称"""
    import keyword
    
    # 检查是否为Python关键字
    if keyword.iskeyword(project_name):
        print(f"项目名称 '{project_name}' 是Python关键字，请使用其他名称")
        return False
    
    # 检查是否与Python内置模块冲突
    forbidden_names = [
        'abc', 'ast', 'io', 'os', 're', 'sys', 'json', 'math', 'time', 'datetime',
        'random', 'collections', 'itertools', 'functools', 'operator', 'pathlib',
        'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3', 'pickle',
        'hashlib', 'hmac', 'secrets', 'ssl', 'socket', 'threading', 'multiprocessing',
        'subprocess', 'argparse', 'logging', 'unittest', 'doctest', 'pdb',
        'string', 'difflib'
    ]
    
    if project_name.lower() in forbidden_names:
        suggestions = [
            f"{project_name}_project",
            f"my_{project_name}",
            f"{project_name}_app",
            f"{project_name}_web"
        ]
        print(f"项目名称 '{project_name}' 与Python内置模块冲突")
        print(f"建议使用: {', '.join(suggestions)}")
        return False
    
    # 检查是否包含特殊字符
    if not project_name.replace('_', '').replace('-', '').isalnum():
        print(f"项目名称 '{project_name}' 包含特殊字符，只能包含字母、数字、下划线和连字符")
        return False
    
    # 检查是否以数字开头
    if project_name[0].isdigit():
        print(f"项目名称 '{project_name}' 不能以数字开头")
        return False
    
    return True


def show_usage_info():
    """显示使用说明"""
    print("""
Django项目创建工具使用说明
==========================

基本用法:
   python django-creator.py myproject

高级用法:
   python django-creator.py myproject --path /path/to/projects
   python django-creator.py myproject --no-venv

参数说明:
   project_name  : 项目名称 (必需)
   --path       : 创建路径 (可选，默认当前目录)
   --no-venv    : 不创建虚拟环境 (可选)

项目名称要求:
   - 不能是Python关键字
   - 不能与Python内置模块同名
   - 只能包含字母、数字、下划线和连字符
   - 不能以数字开头

推荐项目名称:
   my_project, web_app, blog_site, api_server

创建后的操作:
   1. cd myproject
   2. source .venv/bin/activate  # 如果创建了虚拟环境
   3. python manage.py migrate
   4. python manage.py createsuperuser
   5. python manage.py runserver

访问地址:
   管理后台: http://127.0.0.1:8000/admin/
   API文档:  http://127.0.0.1:8000/doc/swagger/

项目特性:
   - JWT认证系统
   - 图片验证码
   - 统一响应格式
   - API文档生成
   - 后台管理美化
   - 跨域支持
   - 基础模型类
""")


def create_project(project_name, project_path, use_venv, template_name=None):
    """创建项目"""
    print(f"\n开始创建项目: {project_name}")
    print("="*50)
    
    try:
        # 第一步：创建基础Django项目
        print("步骤1: 创建基础Django项目和环境...")
        basic_cmd = [sys.executable, "django-creator.py", project_name]
        
        if project_path != os.getcwd():
            basic_cmd.extend(["--path", project_path])
        
        if not use_venv:
            basic_cmd.append("--no-venv")

        # 传递模板版本（如果选择了）
        if template_name:
            basic_cmd.extend(["--template", template_name])
        
        print(f"执行命令: {' '.join(basic_cmd)}")
        subprocess.run(basic_cmd, check=True)
        
        # 第二步：优化项目结构
        print("\n步骤2: 优化项目结构...")
        
        # 进入项目目录
        project_full_path = os.path.join(project_path, project_name)
        original_cwd = os.getcwd()
        os.chdir(project_full_path)
        
        try:
            # 调用django-helper.py优化项目结构
            helper_cmd = [sys.executable, os.path.join(original_cwd, "django-helper.py"), project_name]
            if template_name:
                helper_cmd.extend(["--template", template_name])
            print(f"执行命令: {' '.join(helper_cmd)}")
            subprocess.run(helper_cmd, check=True)
        finally:
            os.chdir(original_cwd)
        
        print("\n" + "="*50)
        print("项目创建成功！")
        
        # 显示后续操作指南
        show_next_steps(project_name, project_path, use_venv)
        
    except subprocess.CalledProcessError as e:
        print(f"\n项目创建失败: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n用户取消操作")
        return False
    except Exception as e:
        print(f"\n发生异常: {e}")
        return False
    
    return True


def show_next_steps(project_name, project_path, use_venv):
    """显示后续操作步骤"""
    full_path = os.path.join(project_path, project_name)
    
    print("\n下一步操作:")
    print(f"1. cd {full_path}")
    
    if use_venv:
        if os.name == 'nt':  # Windows
            print("2. .venv\\Scripts\\activate")
        else:  # Unix-like
            print("2. source .venv/bin/activate")
    
    print("3. python manage.py migrate")
    print("4. python manage.py createsuperuser")
    print("5. python manage.py runserver")
    
    print("\n访问地址:")
    print("   应用首页: http://127.0.0.1:8000/")
    print("   管理后台: http://127.0.0.1:8000/admin/")
    print("   API文档:  http://127.0.0.1:8000/doc/swagger/")
    
    print("\nAPI端点:")
    print("   POST /accounts/token/         # 用户登录")
    print("   POST /accounts/token/refresh/ # 刷新Token")
    print("   GET  /accounts/captcha/       # 获取验证码")


def show_menu():
    """显示主菜单"""
    while True:
        print("\n" + "="*50)
        print("请选择操作:")
        print("1. 创建新项目")
        print("2. 查看使用说明")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-2): ").strip()
        
        if choice == '1':
            # 创建新项目
            project_name, project_path, use_venv = get_user_input()
            
            print(f"\n项目配置确认:")
            print(f"   项目名称: {project_name}")
            print(f"   项目路径: {project_path}")
            print(f"   虚拟环境: {'是' if use_venv else '否'}")
            
            confirm = input("\n确认创建? [Y/n]: ").strip().lower()
            if confirm in ['', 'y', 'yes']:
                create_project(project_name, project_path, use_venv)
            else:
                print("操作已取消")
                
        elif choice == '2':
            # 查看使用说明
            show_usage_info()
                
        elif choice == '0':
            print("再见!")
            break
            
        else:
            print("无效选择，请重试")


def main():
    """主函数"""
    # 检查必要文件
    required_files = ["django-creator.py", "django-helper.py", "requirements.txt"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"缺少必要文件: {missing_files}")
        print("请确保在工具目录下运行此脚本")
        sys.exit(1)
    
    show_banner()
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 直接运行模式
        project_name = sys.argv[1]
        project_path = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        use_venv = '--no-venv' not in sys.argv
        
        create_project(project_name, project_path, use_venv)
    else:
        # 交互模式
        show_menu()


if __name__ == "__main__":
    main()
