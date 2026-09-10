"""
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
