#!/usr/bin/env python3
"""
测试运行脚本

提供便捷的测试执行命令
"""
import subprocess
import sys
import argparse
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], description: str) -> int:
    """运行命令并返回退出码"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60 + '\n')

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def run_unit_tests():
    """运行单元测试"""
    return run_command(
        ['pytest', '-m', 'unit', '-v', '--tb=short'],
        "单元测试"
    )


def run_integration_tests():
    """运行集成测试"""
    return run_command(
        ['pytest', '-m', 'integration', '-v', '--tb=short'],
        "集成测试"
    )


def run_e2e_tests():
    """运行端到端测试"""
    return run_command(
        ['pytest', '-m', 'e2e', '-v', '--tb=short'],
        "端到端测试"
    )


def run_security_tests():
    """运行安全测试"""
    return run_command(
        ['pytest', '-m', 'security', '-v', '--tb=short'],
        "安全测试"
    )


def run_performance_tests():
    """运行性能测试"""
    return run_command(
        ['pytest', '-m', 'performance', '-v', '--benchmark-only'],
        "性能测试"
    )


def run_all_tests():
    """运行所有测试"""
    return run_command(
        ['pytest', '-v', '--tb=short'],
        "所有测试"
    )


def run_tests_with_coverage():
    """运行测试并生成覆盖率报告"""
    return run_command(
        [
            'pytest',
            '-v',
            '--cov=src',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing',
            '--cov-fail-under=90'
        ],
        "测试 + 覆盖率"
    )


def run_fast_tests():
    """运行快速测试（排除慢速测试）"""
    return run_command(
        ['pytest', '-m', 'not slow', '-v', '--tb=short', '-n', 'auto'],
        "快速测试（并行）"
    )


def main():
    parser = argparse.ArgumentParser(
        description='睿之兮量化交易系统测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run_tests.py unit          # 仅单元测试
  python scripts/run_tests.py integration   # 仅集成测试
  python scripts/run_tests.py coverage      # 测试+覆盖率
  python scripts/run_tests.py fast          # 快速测试（并行）
  python scripts/run_tests.py all           # 所有测试
        """
    )

    parser.add_argument(
        'type',
        choices=['unit', 'integration', 'e2e', 'security', 'performance',
                 'all', 'coverage', 'fast'],
        default='fast',
        nargs='?',
        help='测试类型 (默认: fast)'
    )

    args = parser.parse_args()

    test_runners = {
        'unit': run_unit_tests,
        'integration': run_integration_tests,
        'e2e': run_e2e_tests,
        'security': run_security_tests,
        'performance': run_performance_tests,
        'all': run_all_tests,
        'coverage': run_tests_with_coverage,
        'fast': run_fast_tests,
    }

    exit_code = test_runners[args.type]()

    if exit_code == 0:
        print("\n✅ 所有测试通过!")
    else:
        print(f"\n❌ 测试失败 (退出码: {exit_code})")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
