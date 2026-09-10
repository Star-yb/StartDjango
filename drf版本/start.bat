@echo off
chcp 65001 >nul
title Django项目创建工具

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                Django 项目创建工具                    ║
echo ║                                                      ║
echo ║    快速创建Django项目                                ║
echo ║    集成最佳实践配置                                  ║
echo ║    自动生成API文档                                   ║
echo ║    内置JWT认证系统                                   ║
echo ╚══════════════════════════════════════════════════════╝
echo.

rem 检查必要文件
if not exist "django-creator.py" (
    echo 缺少文件: django-creator.py
    echo 请确保在工具目录下运行此脚本
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo 缺少文件: requirements.txt
    echo 请确保在工具目录下运行此脚本
    pause
    exit /b 1
)

rem 如果有参数，直接创建项目
if not "%1"=="" (
    echo 直接创建项目: %1
    python start.py %*
    goto :end
)

rem 交互模式
python start.py

:end
echo.
echo 按任意键退出...
pause >nul