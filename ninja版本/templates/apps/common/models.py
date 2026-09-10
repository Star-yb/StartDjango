import uuid

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


