"""
风控管理 API

提供风控规则配置、风险报告、预警通知等功能
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from src.risk.risk_manager import RiskManager, RiskConfig, TradeSignal
from src.risk.rules import (
    RiskRuleRegistry, RiskCheckResult, RiskLevel,
    PositionLimitRule, StopLossCheckRule, DailyLossLimitRule,
    OrderFrequencyRule, ConsecutiveLossRule, PriceLimitRule, BlacklistRule
)
from src.risk.position_manager import PositionManager
from src.risk.stop_loss import StopLossManager
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()

# ============ 全局风控管理器实例 ============
risk_manager = RiskManager(config=RiskConfig())
rule_registry = RiskRuleRegistry()

# 初始化默认规则
rule_registry.create_rule(
    "position_limit",
    max_single_position_pct=Decimal("0.10"),
    max_total_position_pct=Decimal("0.80")
)
rule_registry.create_rule("stop_loss_check", require_stop_loss=True)
rule_registry.create_rule("daily_loss_limit", max_daily_loss_pct=Decimal("0.02"))
rule_registry.create_rule("order_frequency", max_orders_per_minute=10)
rule_registry.create_rule("consecutive_loss", max_consecutive_losses=3)
rule_registry.create_rule("price_limit")
rule_registry.create_rule("blacklist")

# 预警存储
_risk_alerts: List[Dict[str, Any]] = []
_alert_id_counter = 0


# ============ Pydantic 模型 ============

class RiskStatusResponse(BaseModel):
    status: str  # safe, warning, danger
    score: int  # 0-100
    active_rules: int
    pending_alerts: int


class RiskRuleConfig(BaseModel):
    enabled: bool
    config: Dict[str, Any]


class RiskAlert(BaseModel):
    id: int
    level: str  # WARNING, CRITICAL
    title: str
    message: str
    timestamp: str
    acknowledged: bool


class PositionRiskInfo(BaseModel):
    symbol: str
    quantity: int
    market_value: float
    weight: float  # 仓位占比
    unrealized_pnl_pct: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_level: str  # low, medium, high


class RiskReport(BaseModel):
    timestamp: str
    overall_status: str
    risk_score: int
    position_summary: Dict[str, Any]
    active_stop_losses: Dict[str, Any]
    active_take_profits: Dict[str, Any]
    recent_alerts: List[RiskAlert]


class EmergencyCloseRequest(BaseModel):
    reason: str = "紧急清仓"
    confirm: bool = False


# ============ API 端点 ============

@router.get("/status", response_model=RiskStatusResponse)
async def get_risk_status():
    """获取风控整体状态"""
    try:
        # 计算风险评分
        score = _calculate_risk_score()

        # 确定状态
        if score >= 80:
            status = "safe"
        elif score >= 60:
            status = "warning"
        else:
            status = "danger"

        # 统计待处理预警
        pending = len([a for a in _risk_alerts if not a["acknowledged"]])

        # 统计启用规则
        active_rules = sum(1 for r in rule_registry.get_all_rules() if r.enabled)

        return RiskStatusResponse(
            status=status,
            score=score,
            active_rules=active_rules,
            pending_alerts=pending
        )
    except Exception as e:
        logger.error(f"获取风控状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report", response_model=RiskReport)
async def get_risk_report():
    """获取详细风控报告"""
    try:
        report = risk_manager.get_risk_report()

        # 获取最近预警
        recent_alerts = [
            RiskAlert(**alert) for alert in _risk_alerts[-10:]
        ]

        # 计算整体评分
        score = _calculate_risk_score()

        return RiskReport(
            timestamp=datetime.now().isoformat(),
            overall_status="safe" if score >= 80 else "warning" if score >= 60 else "danger",
            risk_score=score,
            position_summary=report.get("position", {}),
            active_stop_losses=report.get("stop_loss", {}),
            active_take_profits=report.get("take_profit", {}),
            recent_alerts=recent_alerts
        )
    except Exception as e:
        logger.error(f"获取风控报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def get_all_rules():
    """获取所有风控规则状态"""
    rules = rule_registry.get_all_rules()
    return [
        {
            "code": r.code,
            "name": r.name,
            "type": r.rule_type.value,
            "level": r.level.value,
            "enabled": r.enabled,
            "stats": r.get_stats()
        }
        for r in rules
    ]


@router.post("/rules/{code}/toggle")
async def toggle_rule(code: str):
    """启用/禁用规则"""
    rule = rule_registry.get_rule(code)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {code} 不存在")

    rule.enabled = not rule.enabled
    logger.info(f"规则 {code} 已{'启用' if rule.enabled else '禁用'}")

    return {
        "code": code,
        "enabled": rule.enabled,
        "message": f"规则已{'启用' if rule.enabled else '禁用'}"
    }


@router.put("/rules/{code}")
async def update_rule_config(code: str, config: RiskRuleConfig):
    """更新规则配置"""
    rule = rule_registry.get_rule(code)
    if not rule:
        raise HTTPException(status_code=404, detail=f"规则 {code} 不存在")

    # 更新启用状态
    rule.enabled = config.enabled

    # 更新配置参数
    for key, value in config.config.items():
        rule.update_config(**{key: value})

    logger.info(f"规则 {code} 配置已更新")

    return {
        "code": code,
        "enabled": rule.enabled,
        "config": config.config,
        "message": "规则配置已更新"
    }


@router.get("/positions", response_model=List[PositionRiskInfo])
async def get_position_risks():
    """获取持仓风险信息"""
    try:
        report = risk_manager.get_risk_report()
        positions = report.get("position", {}).get("positions", [])
        active_stop_losses = report.get("stop_loss", {})
        active_take_profits = report.get("take_profit", {})

        result = []
        for pos in positions:
            symbol = pos["symbol"]
            weight = pos.get("weight", 0)
            pnl_pct = pos.get("unrealized_pnl_pct", 0)

            # 确定风险级别
            if weight > 0.15 or pnl_pct < -0.05:
                risk_level = "high"
            elif weight > 0.10 or pnl_pct < -0.03:
                risk_level = "medium"
            else:
                risk_level = "low"

            # 获取止损止盈设置
            sl_info = active_stop_losses.get(symbol, {})
            tp_info = active_take_profits.get(symbol, {})

            result.append(PositionRiskInfo(
                symbol=symbol,
                quantity=pos.get("quantity", 0),
                market_value=pos.get("market_value", 0),
                weight=weight,
                unrealized_pnl_pct=pnl_pct,
                stop_loss=float(sl_info["stop_price"]) if sl_info.get("stop_price") else None,
                take_profit=float(tp_info["target_price"]) if tp_info.get("target_price") else None,
                risk_level=risk_level
            ))

        return result
    except Exception as e:
        logger.error(f"获取持仓风险失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[RiskAlert])
async def get_risk_alerts(
    level: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50
):
    """获取风险预警列表"""
    alerts = _risk_alerts

    if level:
        alerts = [a for a in alerts if a["level"] == level]

    if acknowledged is not None:
        alerts = [a for a in alerts if a["acknowledged"] == acknowledged]

    return [RiskAlert(**a) for a in alerts[-limit:]]


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(alert_id: int):
    """确认风险预警"""
    for alert in _risk_alerts:
        if alert["id"] == alert_id:
            alert["acknowledged"] = True
            logger.info(f"预警 {alert_id} 已确认")
            return {"id": alert_id, "acknowledged": True}

    raise HTTPException(status_code=404, detail=f"预警 {alert_id} 不存在")


@router.post("/alerts/clear")
async def clear_acknowledged_alerts():
    """清空已确认的预警"""
    global _risk_alerts
    cleared = len([a for a in _risk_alerts if a["acknowledged"]])
    _risk_alerts = [a for a in _risk_alerts if not a["acknowledged"]]

    logger.info(f"已清空 {cleared} 条已确认预警")
    return {"cleared": cleared}


@router.post("/emergency-close")
async def emergency_close(request: EmergencyCloseRequest):
    """紧急清仓"""
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="请确认执行紧急清仓操作（设置 confirm: true）"
        )

    try:
        risk_manager.emergency_close_all()

        # 记录紧急操作预警
        _add_risk_alert(
            level="CRITICAL",
            title="紧急清仓已执行",
            message=f"原因: {request.reason}"
        )

        logger.critical(f"紧急清仓已执行: {request.reason}")

        return {
            "success": True,
            "message": "紧急清仓已执行",
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"紧急清仓失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-loss/{symbol}")
async def update_stop_loss(symbol: str, price: float):
    """手动更新止损价"""
    try:
        success = risk_manager.update_stop_loss(
            symbol,
            Decimal(str(price))
        )
        if success:
            return {
                "success": True,
                "symbol": symbol,
                "stop_loss": price,
                "message": "止损价已更新"
            }
        raise HTTPException(status_code=404, detail=f"持仓 {symbol} 不存在")
    except Exception as e:
        logger.error(f"更新止损价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/take-profit/{symbol}")
async def update_take_profit(symbol: str, price: float):
    """手动更新止盈价"""
    try:
        success = risk_manager.update_take_profit(
            symbol,
            Decimal(str(price))
        )
        if success:
            return {
                "success": True,
                "symbol": symbol,
                "take_profit": price,
                "message": "止盈价已更新"
            }
        raise HTTPException(status_code=404, detail=f"持仓 {symbol} 不存在")
    except Exception as e:
        logger.error(f"更新止盈价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ WebSocket 实时推送 ============

class RiskConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"风控 WebSocket 连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"风控 WebSocket 连接断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


risk_ws_manager = RiskConnectionManager()


@router.websocket("/ws")
async def risk_websocket(websocket: WebSocket):
    """风控实时数据 WebSocket"""
    await risk_ws_manager.connect(websocket)
    try:
        # 发送初始状态
        await websocket.send_json({
            "type": "connected",
            "message": "风控监控已连接"
        })

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 处理订阅请求
            if data.get("action") == "subscribe":
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": ["alerts", "position_risk", "rule_updates"]
                })

            # 处理心跳
            elif data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        risk_ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"风控 WebSocket 错误: {e}")
        risk_ws_manager.disconnect(websocket)


# ============ 辅助函数 ============

def _calculate_risk_score() -> int:
    """计算风险评分 (0-100，越高越安全)"""
    score = 100

    try:
        report = risk_manager.get_risk_report()
        position_summary = report.get("position", {}).get("summary", {})

        # 1. 仓位风险 (最高扣40分)
        total_weight = position_summary.get("total_position_weight", 0)
        if total_weight > 0.8:
            score -= 40
        elif total_weight > 0.6:
            score -= 20
        elif total_weight > 0.4:
            score -= 10

        # 2. 单票集中度风险 (最高扣30分)
        positions = report.get("position", {}).get("positions", [])
        max_weight = max([p.get("weight", 0) for p in positions], default=0)
        if max_weight > 0.3:
            score -= 30
        elif max_weight > 0.2:
            score -= 15
        elif max_weight > 0.1:
            score -= 5

        # 3. 未设置止损风险 (最高扣20分)
        active_sl = report.get("stop_loss", {})
        if positions:
            no_sl_count = len(positions) - len(active_sl)
            no_sl_ratio = no_sl_count / len(positions)
            score -= int(20 * no_sl_ratio)

        # 4. 预警数量风险 (最高扣10分)
        pending_alerts = len([a for a in _risk_alerts if not a["acknowledged"]])
        score -= min(10, pending_alerts * 2)

    except Exception as e:
        logger.error(f"计算风险评分失败: {e}")

    return max(0, min(100, score))


def _add_risk_alert(level: str, title: str, message: str):
    """添加风险预警"""
    global _alert_id_counter
    _alert_id_counter += 1

    alert = {
        "id": _alert_id_counter,
        "level": level,
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "acknowledged": False
    }

    _risk_alerts.append(alert)

    # 限制预警数量
    if len(_risk_alerts) > 1000:
        _risk_alerts = _risk_alerts[-500:]

    # 异步推送 WebSocket
    import asyncio
    asyncio.create_task(risk_ws_manager.broadcast({
        "type": "risk_alert",
        "data": alert
    }))

    logger.warning(f"风险预警 [{level}]: {title} - {message}")


# 注册风控回调
risk_manager.on_reject(lambda symbol, reason: _add_risk_alert(
    level="WARNING",
    title=f"交易被拦截: {symbol}",
    message=reason
))
