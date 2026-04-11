"""
算法执行模块

提供各种订单执行算法：
- TWAP: 时间加权平均价格
- VWAP: 成交量加权平均价格
- MARKET: 市价单直接执行
- LIMIT: 限价单直接执行
"""
from src.execution.algorithms.base import AlgorithmConfig, AlgorithmStatus, ExecutionAlgorithm
from src.execution.algorithms.twap import TWAPAlgorithm
from src.execution.algorithms.vwap import VWAPAlgorithm
from src.execution.algorithms.market import MarketAlgorithm


def create_algorithm(
    algorithm_type: str,
    order,
    config: AlgorithmConfig,
    session
) -> ExecutionAlgorithm:
    """
    创建算法执行器

    Args:
        algorithm_type: 算法类型 (TWAP, VWAP, MARKET, LIMIT)
        order: 订单
        config: 算法配置
        session: 数据库会话

    Returns:
        ExecutionAlgorithm: 算法执行器

    Raises:
        ValueError: 未知算法类型
    """
    algorithm_type = algorithm_type.upper()

    if algorithm_type == "TWAP":
        return TWAPAlgorithm(order, config, session)
    elif algorithm_type == "VWAP":
        return VWAPAlgorithm(order, config, session)
    elif algorithm_type in ["MARKET", "LIMIT"]:
        return MarketAlgorithm(order, config, session, algorithm_type)
    else:
        raise ValueError(f"未知算法类型: {algorithm_type}")


__all__ = [
    "AlgorithmConfig",
    "AlgorithmStatus",
    "ExecutionAlgorithm",
    "TWAPAlgorithm",
    "VWAPAlgorithm",
    "MarketAlgorithm",
    "create_algorithm",
]
