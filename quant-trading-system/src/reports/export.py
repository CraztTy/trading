"""
报告导出模块

支持多种格式导出报告：
- JSON: 结构化数据
- CSV: 表格数据
- HTML: 可视化报告
- PDF: 打印和分享
"""
import json
import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict, is_dataclass

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """处理Decimal的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)


class ReportExporter:
    """报告导出器"""

    @classmethod
    def to_json(
        cls,
        report: Any,
        output_path: str,
        indent: int = 2
    ) -> str:
        """
        导出为JSON格式

        Args:
            report: 报告对象
            output_path: 输出文件路径
            indent: JSON缩进

        Returns:
            str: 输出文件路径
        """
        try:
            # 转换为字典
            if hasattr(report, 'to_dict'):
                data = report.to_dict()
            elif is_dataclass(report):
                data = asdict(report)
            else:
                data = report

            # 写入文件
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, cls=DecimalEncoder, indent=indent, ensure_ascii=False)

            logger.info(f"报告已导出为JSON: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            raise

    @classmethod
    def to_csv(
        cls,
        report: Any,
        output_path: str,
        data_field: str = 'trades'
    ) -> str:
        """
        导出为CSV格式

        Args:
            report: 报告对象
            output_path: 输出文件路径
            data_field: 要导出的列表字段名

        Returns:
            str: 输出文件路径
        """
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # 获取要导出的数据
            if hasattr(report, data_field):
                data = getattr(report, data_field)
            elif hasattr(report, 'to_dict'):
                data = report.to_dict().get(data_field, [])
            else:
                data = []

            if not data:
                logger.warning(f"没有找到要导出的数据: {data_field}")
                # 创建一个空文件
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    pass
                return output_path

            # 写入CSV
            with open(path, 'w', newline='', encoding='utf-8') as f:
                if data and len(data) > 0:
                    # 获取字段名
                    first_item = data[0]
                    if hasattr(first_item, '__dict__'):
                        fieldnames = list(first_item.__dict__.keys())
                    elif isinstance(first_item, dict):
                        fieldnames = list(first_item.keys())
                    else:
                        fieldnames = []

                    if fieldnames:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()

                        for item in data:
                            if hasattr(item, '__dict__'):
                                row = cls._prepare_csv_row(item.__dict__)
                            elif isinstance(item, dict):
                                row = cls._prepare_csv_row(item)
                            else:
                                continue
                            writer.writerow(row)

            logger.info(f"报告已导出为CSV: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            raise

    @classmethod
    def to_html(
        cls,
        report: Any,
        output_path: str,
        title: Optional[str] = None
    ) -> str:
        """
        导出为HTML格式

        Args:
            report: 报告对象
            output_path: 输出文件路径
            title: 报告标题

        Returns:
            str: 输出文件路径
        """
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # 转换为字典
            if hasattr(report, 'to_dict'):
                data = report.to_dict()
            elif is_dataclass(report):
                data = asdict(report)
            else:
                data = report

            # 生成标题
            if title is None:
                title = cls._generate_title(report)

            # 生成HTML内容
            html_content = cls._generate_html(data, title)

            # 写入文件
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"报告已导出为HTML: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"导出HTML失败: {e}")
            raise

    @classmethod
    def to_dict(cls, report: Any) -> Dict:
        """
        转换为字典（用于API返回）

        Args:
            report: 报告对象

        Returns:
            Dict: 报告字典
        """
        if hasattr(report, 'to_dict'):
            return report.to_dict()
        elif is_dataclass(report):
            return asdict(report)
        elif isinstance(report, dict):
            return report
        else:
            return {"data": str(report)}

    @staticmethod
    def _prepare_csv_row(row: Dict) -> Dict:
        """准备CSV行数据"""
        result = {}
        for key, value in row.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                result[key] = json.dumps(value, ensure_ascii=False)
            else:
                result[key] = value
        return result

    @staticmethod
    def _generate_title(report: Any) -> str:
        """生成报告标题"""
        if hasattr(report, 'report_type'):
            report_type = report.report_type
            if hasattr(report_type, 'value'):
                type_name = report_type.value.capitalize()
            else:
                type_name = str(report_type)
        else:
            type_name = "Trade"

        if hasattr(report, 'report_date'):
            date_str = str(report.report_date)
        elif hasattr(report, 'start_date') and hasattr(report, 'end_date'):
            date_str = f"{report.start_date} ~ {report.end_date}"
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')

        return f"{type_name} Report - {date_str}"

    @classmethod
    def _generate_html(cls, data: Dict, title: str) -> str:
        """生成HTML内容"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .metric-label {{
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 5px;
        }}
        .metric-value.positive {{
            color: #27ae60;
        }}
        .metric-value.negative {{
            color: #e74c3c;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #95a5a6;
            font-size: 12px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>

        {cls._generate_html_content(data)}

        <div class="footer">
            <p>Generated by Quant Trading System</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        return html

    @classmethod
    def _generate_html_content(cls, data: Dict) -> str:
        """生成HTML内容主体"""
        sections = []

        # 摘要统计
        summary_items = []
        for key, value in data.items():
            if isinstance(value, (int, float, Decimal)) and not key.startswith('_'):
                label = key.replace('_', ' ').title()
                display_value = cls._format_value(value)
                css_class = ''
                if isinstance(value, (int, float, Decimal)):
                    if value > 0:
                        css_class = 'positive'
                    elif value < 0:
                        css_class = 'negative'

                summary_items.append(f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value {css_class}">{display_value}</div>
                    </div>
                """)

        if summary_items:
            sections.append(f"""
                <div class="section">
                    <h2>Summary</h2>
                    <div class="summary">
                        {''.join(summary_items[:8])}  <!-- 最多显示8个指标 -->
                    </div>
                </div>
            """)

        # 交易列表
        if 'trades' in data and data['trades']:
            sections.append(cls._generate_table_section('Trades', data['trades'][:50]))  # 最多50条

        # 订单列表
        if 'orders' in data and data['orders']:
            sections.append(cls._generate_table_section('Orders', data['orders'][:50]))

        # 每日收益
        if 'daily_returns' in data and data['daily_returns']:
            sections.append(cls._generate_table_section('Daily Returns', data['daily_returns']))

        return '\n'.join(sections)

    @classmethod
    def _generate_table_section(cls, title: str, items: List[Dict]) -> str:
        """生成表格部分"""
        if not items:
            return ''

        # 获取表头
        first_item = items[0]
        if hasattr(first_item, '__dict__'):
            headers = list(first_item.__dict__.keys())
        elif isinstance(first_item, dict):
            headers = list(first_item.keys())
        else:
            return ''

        # 限制列数
        headers = headers[:10]

        # 生成表头
        header_html = ''.join(f'<th>{h.replace("_", " ").title()}</th>' for h in headers)

        # 生成行
        rows = []
        for item in items[:100]:  # 最多100行
            if hasattr(item, '__dict__'):
                row_data = item.__dict__
            elif isinstance(item, dict):
                row_data = item
            else:
                continue

            cells = []
            for h in headers:
                value = row_data.get(h, '')
                cells.append(f'<td>{cls._format_value(value)}</td>')
            rows.append(f'<tr>{"".join(cells)}</tr>')

        return f"""
            <div class="section">
                <h2>{title}</h2>
                <table>
                    <thead>
                        <tr>{header_html}</tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        """

    @staticmethod
    def _format_value(value: Any) -> str:
        """格式化值显示"""
        if isinstance(value, Decimal):
            return f"{float(value):,.2f}"
        elif isinstance(value, float):
            if abs(value) < 0.01:
                return f"{value:.6f}"
            return f"{value:,.2f}"
        elif isinstance(value, int):
            return f"{value:,}"
        elif isinstance(value, (date, datetime)):
            return value.isoformat()
        elif value is None:
            return '-'
        else:
            return str(value)[:50]  # 限制长度


class ReportBatchExporter:
    """批量报告导出器"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_multiple(
        self,
        reports: List[Any],
        format_type: str = 'json',
        prefix: str = 'report'
    ) -> List[str]:
        """
        批量导出报告

        Args:
            reports: 报告列表
            format_type: 导出格式 (json/csv/html)
            prefix: 文件名前缀

        Returns:
            List[str]: 导出文件路径列表
        """
        exported_files = []

        for i, report in enumerate(reports):
            filename = f"{prefix}_{i+1:03d}.{format_type}"
            output_path = self.output_dir / filename

            try:
                if format_type == 'json':
                    ReportExporter.to_json(report, str(output_path))
                elif format_type == 'csv':
                    ReportExporter.to_csv(report, str(output_path))
                elif format_type == 'html':
                    ReportExporter.to_html(report, str(output_path))
                else:
                    logger.warning(f"不支持的格式: {format_type}")
                    continue

                exported_files.append(str(output_path))

            except Exception as e:
                logger.error(f"导出报告 {i+1} 失败: {e}")

        logger.info(f"批量导出完成: {len(exported_files)} 个文件")
        return exported_files
