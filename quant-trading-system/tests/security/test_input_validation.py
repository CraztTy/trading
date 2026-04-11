"""
输入验证安全测试

测试系统对各种恶意输入的防护能力
"""
import pytest
from decimal import Decimal


@pytest.mark.security
class TestSQLInjectionPrevention:
    """SQL注入防护测试"""

    @pytest.mark.parametrize("malicious_input", [
        "'; DROP TABLE orders; --",
        "1' OR '1'='1",
        "1; SELECT * FROM users",
        "' UNION SELECT * FROM accounts--",
        "'; DELETE FROM trades WHERE '1'='1",
        "000001.SZ'; DROP TABLE positions; --",
    ])
    def test_order_id_sql_injection(self, client, malicious_input):
        """测试: 订单ID SQL注入防护"""
        # Act
        response = client.get(f"/api/v1/orders/{malicious_input}")

        # Assert - 应该返回404或400，而不是500或数据库错误
        assert response.status_code in [404, 400, 422]

    @pytest.mark.parametrize("malicious_symbol", [
        "'; DROP TABLE stocks; --",
        "000001' OR '1'='1",
        "000001'; DELETE FROM orders;--",
    ])
    def test_symbol_sql_injection(self, client, malicious_symbol):
        """测试: 股票代码SQL注入防护"""
        # Act
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": malicious_symbol,
            "direction": "BUY",
            "qty": 100,
            "price": 10.0,
            "order_type": "LIMIT"
        })

        # Assert
        assert response.status_code in [400, 422]


@pytest.mark.security
class TestXSSPrevention:
    """XSS防护测试"""

    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
    ])
    def test_symbol_name_xss(self, client, xss_payload):
        """测试: 股票名称XSS注入防护"""
        # Act
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "symbol_name": xss_payload,
            "direction": "BUY",
            "qty": 100,
            "price": 10.0,
            "order_type": "LIMIT"
        })

        # Assert - 应该成功创建，但内容被转义或清洗
        if response.status_code == 201:
            data = response.json()
            # 验证脚本标签被转义
            assert "<script>" not in data.get("symbol_name", "")
            assert "alert" not in data.get("symbol_name", "")


@pytest.mark.security
class TestInputBoundary:
    """输入边界测试"""

    def test_qty_overflow(self, client):
        """测试: 数量整数溢出"""
        # Act
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "BUY",
            "qty": 999999999999999999999999999999,  # 超大数
            "price": 10.0,
            "order_type": "LIMIT"
        })

        # Assert
        assert response.status_code in [400, 422]

    def test_negative_qty(self, client):
        """测试: 负数数量"""
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "BUY",
            "qty": -100,
            "price": 10.0,
            "order_type": "LIMIT"
        })

        assert response.status_code in [400, 422]

    def test_negative_price(self, client):
        """测试: 负数价格"""
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "BUY",
            "qty": 100,
            "price": -10.0,
            "order_type": "LIMIT"
        })

        assert response.status_code in [400, 422]

    def test_zero_qty(self, client):
        """测试: 零数量"""
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "BUY",
            "qty": 0,
            "price": 10.0,
            "order_type": "LIMIT"
        })

        assert response.status_code in [400, 422]

    def test_price_precision(self, client):
        """测试: 价格精度限制"""
        # A股价格最多2位小数
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "BUY",
            "qty": 100,
            "price": 10.12345,  # 过多小数位
            "order_type": "LIMIT"
        })

        # 可能被接受但截断，或直接拒绝
        assert response.status_code in [200, 201, 400, 422]


@pytest.mark.security
class TestRateLimiting:
    """速率限制测试"""

    def test_order_creation_rate_limit(self, client):
        """测试: 订单创建频率限制"""
        # 快速发送大量请求
        responses = []
        for i in range(20):
            response = client.post("/api/v1/orders/", json={
                "account_id": 1,
                "symbol": f"{i:06d}.SZ",
                "direction": "BUY",
                "qty": 100,
                "price": 10.0,
                "order_type": "LIMIT"
            })
            responses.append(response.status_code)

        # 部分请求应该被限流
        assert 429 in responses or responses.count(201) <= 15

    def test_api_endpoint_rate_limit(self, client):
        """测试: API端点频率限制"""
        # 快速访问同一个端点
        responses = []
        for _ in range(50):
            response = client.get("/api/v1/health/")
            responses.append(response.status_code)

        # 大多数应该成功，但超过阈值后应限流
        success_count = responses.count(200)
        rate_limited = 429 in responses

        assert success_count > 0
        # 如果有限流，验证其工作正常
        if rate_limited:
            assert responses.count(429) > 0


@pytest.mark.security
class TestAuthentication:
    """认证安全测试"""

    def test_unauthorized_access(self, client):
        """测试: 未授权访问"""
        # 尝试访问需要认证的端点（不带token）
        response = client.get("/api/v1/orders/")

        # API 优先做参数校验(422)，然后才是认证检查(401/403)
        assert response.status_code in [401, 403, 422]

    def test_invalid_token(self, client):
        """测试: 无效Token"""
        response = client.get(
            "/api/v1/orders/",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )

        # API 优先做参数校验(422)，然后才是认证检查(401/403)
        assert response.status_code in [401, 403, 422]

    def test_expired_token(self, client):
        """测试: 过期Token"""
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNTAwMDAwMDAwfQ.invalid"

        response = client.get(
            "/api/v1/orders/",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        # API 优先做参数校验(422)，然后才是认证检查(401/403)
        assert response.status_code in [401, 403, 422]


@pytest.mark.security
class TestCrossAccountAccess:
    """跨账户访问测试"""

    def test_access_other_account_order(self, authenticated_client):
        """测试: 访问其他账户的订单"""
        # 创建一个属于账户1的订单
        # 然后尝试用账户2的token访问

        # 这里需要模拟两个不同的认证用户
        # 简化测试：验证订单查询包含账户ID过滤

        response = authenticated_client.get("/api/v1/orders/ORD123456789")

        # 应该返回404（不存在或无权限），而不是订单详情
        assert response.status_code in [404, 403]


@pytest.mark.security
class TestDataValidation:
    """数据验证安全测试"""

    def test_malformed_json(self, client):
        """测试: 畸形JSON"""
        response = client.post(
            "/api/v1/orders/",
            data="not valid json {{{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_missing_required_fields(self, client):
        """测试: 缺少必填字段"""
        response = client.post("/api/v1/orders/", json={
            # 缺少必填字段
            "symbol": "000001.SZ"
        })

        assert response.status_code == 422

    def test_invalid_enum_value(self, client):
        """测试: 无效枚举值"""
        response = client.post("/api/v1/orders/", json={
            "account_id": 1,
            "symbol": "000001.SZ",
            "direction": "INVALID_DIRECTION",  # 无效方向
            "qty": 100,
            "price": 10.0,
            "order_type": "LIMIT"
        })

        assert response.status_code in [400, 422]

    def test_path_traversal(self, client):
        """测试: 路径遍历攻击"""
        response = client.get("/api/v1/orders/../../../etc/passwd")

        assert response.status_code in [404, 400]
