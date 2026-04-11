"""
优化器工具函数
"""
import hashlib
import json
from typing import Dict, Any, List

from src.strategy.optimizer.base import ParameterSpace


def param_dict_to_key(params: Dict[str, Any]) -> str:
    """
    将参数字典转换为字符串键

    Args:
        params: 参数字典

    Returns:
        字符串键
    """
    # 按键排序确保一致性
    items = sorted(params.items())
    return "|".join(f"{k}={v}" for k, v in items)


def get_param_hash(params: Dict[str, Any]) -> str:
    """
    获取参数的哈希值

    Args:
        params: 参数字典

    Returns:
        哈希字符串
    """
    key = param_dict_to_key(params)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def clip_params(params: Dict[str, Any], param_space: List[ParameterSpace]) -> Dict[str, Any]:
    """
    将参数裁剪到有效范围内

    Args:
        params: 参数字典
        param_space: 参数空间定义

    Returns:
        裁剪后的参数
    """
    clipped = params.copy()

    for param in param_space:
        if param.name not in clipped:
            continue

        value = clipped[param.name]

        if param.param_type.value == "integer":
            value = int(max(param.low, min(param.high, value)))
        elif param.param_type.value == "float":
            value = float(max(param.low, min(param.high, value)))

        clipped[param.name] = value

    return clipped


def validate_params(params: Dict[str, Any], param_space: List[ParameterSpace]) -> bool:
    """
    验证参数是否在有效范围内

    Args:
        params: 参数字典
        param_space: 参数空间定义

    Returns:
        是否有效
    """
    param_dict = {p.name: p for p in param_space}

    # 检查必需参数
    for param in param_space:
        if param.name not in params:
            return False

    # 检查参数值
    for name, value in params.items():
        if name not in param_dict:
            continue

        param = param_dict[name]

        if param.param_type.value in ["integer", "float"]:
            if value < param.low or value > param.high:
                return False

        elif param.param_type.value == "categorical":
            if value not in param.choices:
                return False

    return True


def calculate_weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    计算加权得分

    Args:
        scores: 各指标得分
        weights: 各指标权重

    Returns:
        加权得分
    """
    total = 0.0
    total_weight = 0.0

    for key, score in scores.items():
        weight = weights.get(key, 0.0)
        total += score * weight
        total_weight += weight

    return total / total_weight if total_weight > 0 else 0.0
