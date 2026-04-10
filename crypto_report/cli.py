from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .config import load_script_config
from .generator import CryptoReportGenerator


def parse_report_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期格式必须是 YYYY-MM-DD") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="生成数字货币日报")
    parser.add_argument("command", nargs="?", choices=["run", "cleanup", "test"], default="run")
    parser.add_argument("--config", type=Path, help="指定配置文件路径，例如 ./local_config.json")
    parser.add_argument("--date", type=parse_report_date, help="指定报告日期，格式 YYYY-MM-DD")
    parser.add_argument("--output-dir", type=Path, help="指定报告输出目录，例如 ./dist/reports")
    parser.add_argument("--no-screenshot", action="store_true", help="本次运行关闭截图生成")
    parser.add_argument(
        "--netlify-deploy",
        action="store_true",
        help="本次运行完成后将报告目录部署到 Netlify（需在配置中提供 site id / token）",
    )
    args = parser.parse_args()

    runtime_overrides = {}
    if args.no_screenshot:
        runtime_overrides["generate_screenshots"] = False
    if args.netlify_deploy:
        runtime_overrides["enable_netlify_deploy"] = True
    if args.output_dir:
        runtime_overrides["report_output_dir"] = args.output_dir.resolve()
    config_path = args.config.resolve() if args.config else None
    base_dir = config_path.parent if config_path else None
    config = load_script_config(
        base_dir=base_dir,
        config_file=config_path,
        runtime_overrides=runtime_overrides or None,
    )
    generator = CryptoReportGenerator(config=config, report_date=args.date)

    if args.command == "cleanup":
        print("🧹 开始清理旧报告...")
        generator.cleanup_old_reports(generator.config.cleanup_days_to_keep)
        return

    if args.command == "test":
        print("🧪 测试模式：生成报告并清理")

    generator.run()
