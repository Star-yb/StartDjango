"""
工具类模块
提供统一的API响应格式和其他辅助工具
"""
from typing import Any, Optional
from ninja import Schema


class ResponseSchema(Schema):
    """
    统一的API响应格式Schema
    所有API接口的响应都应该遵循这个格式
    """
    code: int  # 状态码：0表示成功，非0表示各种错误
    msg: str   # 消息描述
    data: Optional[Any] = None  # 响应数据，可以是任何类型


class ApiResponse:
    """
    API响应工具类
    用于生成统一格式的响应数据
    """
    
    # 状态码常量定义
    SUCCESS = 0           # 成功
    ERROR = 1             # 通用错误
    VALIDATION_ERROR = 2  # 验证错误
    AUTH_ERROR = 3        # 认证错误
    PERMISSION_ERROR = 4  # 权限错误
    NOT_FOUND = 5         # 资源不存在
    ALREADY_EXISTS = 6    # 资源已存在
    
    @staticmethod
    def success(data: Any = None, msg: str = "操作成功") -> dict:
        """
        返回成功响应
        
        Args:
            data: 响应数据
            msg: 提示消息
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return {
            "code": ApiResponse.SUCCESS,
            "msg": msg,
            "data": data
        }
    
    @staticmethod
    def error(msg: str = "操作失败", code: int = ERROR, data: Any = None) -> dict:
        """
        返回错误响应
        
        Args:
            msg: 错误消息
            code: 错误码
            data: 额外的错误数据
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return {
            "code": code,
            "msg": msg,
            "data": data
        }
    
    @staticmethod
    def validation_error(msg: str = "数据验证失败", data: Any = None) -> dict:
        """
        返回验证错误响应
        
        Args:
            msg: 错误消息
            data: 验证错误详情
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return ApiResponse.error(msg=msg, code=ApiResponse.VALIDATION_ERROR, data=data)
    
    @staticmethod
    def auth_error(msg: str = "认证失败") -> dict:
        """
        返回认证错误响应
        
        Args:
            msg: 错误消息
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return ApiResponse.error(msg=msg, code=ApiResponse.AUTH_ERROR)
    
    @staticmethod
    def permission_error(msg: str = "权限不足") -> dict:
        """
        返回权限错误响应
        
        Args:
            msg: 错误消息
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return ApiResponse.error(msg=msg, code=ApiResponse.PERMISSION_ERROR)
    
    @staticmethod
    def not_found(msg: str = "资源不存在") -> dict:
        """
        返回资源不存在响应
        
        Args:
            msg: 错误消息
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return ApiResponse.error(msg=msg, code=ApiResponse.NOT_FOUND)
    
    @staticmethod
    def already_exists(msg: str = "资源已存在") -> dict:
        """
        返回资源已存在响应
        
        Args:
            msg: 错误消息
            
        Returns:
            符合ResponseSchema格式的字典
        """
        return ApiResponse.error(msg=msg, code=ApiResponse.ALREADY_EXISTS)

