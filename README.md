# crypto_daily_report

数字货币日报生成工具，包含市场概览、新闻抓取、恐惧贪婪指数分析、AI 视角解读、HTML 报告输出和可选截图生成。

## 当前结构

- `run_report.py`：推荐 CLI 入口
- `crypto_dashboard_optimized_final.py`：兼容旧入口的 wrapper
- `crypto_report/generator.py`：主流程编排、报告保存与截图
- `crypto_report/services/`：市场数据、新闻解析、情绪分析、趋势存储、AI分析服务
- `crypto_report/config.py`：配置模型、本地覆盖加载、资源路径
- `crypto_report/http_client.py`：带重试和日志的 HTTP 客户端
- `crypto_report/logging_utils.py`：日志初始化
- `crypto_report/models.py`：TypedDict 数据模型
- `crypto_report/helpers.py`：纯函数和格式化辅助
- `crypto_report/renderers.py`：HTML 片段渲染
- `crypto_report/templates/report.html.j2`：Jinja2 报告模板
- `crypto_report/assets/report.css`：共享样式文件
- `tests/`：unittest 回归测试、真实响应 fixture 和 HTML 快照

## 环境准备

建议使用项目内虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

## 本地配置

默认配置在 `crypto_report/config.py`，如需覆盖敏感信息或部署参数：

1. 复制 `local_config.example.json`
2. 重命名为 `local_config.json`
3. 填入本地 key / URL / 开关配置

`local_config.json` 已加入 `.gitignore`，不会进入版本管理。旧文件名 `dashboard_local_config.json` 仍兼容读取，但不建议继续使用。

## 常用命令

生成日报：

```bash
.venv/bin/python run_report.py
```

指定配置文件、日期并关闭截图：

```bash
.venv/bin/python run_report.py --config ./local_config.json --date 2026-04-03 --no-screenshot
```

指定输出目录：

```bash
.venv/bin/python run_report.py --config ./local_config.json --output-dir ./dist/reports
```

本次运行完成后部署到 Netlify：

```bash
.venv/bin/python run_report.py --config ./local_config.json --netlify-deploy
```

清理旧报告：

```bash
.venv/bin/python run_report.py cleanup
```

测试模式：

```bash
.venv/bin/python run_report.py test
```

运行测试：

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## 说明

- 报告模板使用 Jinja2 渲染
- 样式文件会在保存报告时自动同步到输出目录
- 截图默认开启，可在 `local_config.json` 里关闭 `generate_screenshots`
- 截图依赖 `playwright`，安装 Python 依赖后还需额外执行 `.venv/bin/python -m playwright install chromium`
- 相对样式路径和绝对资源地址策略可通过 `report_asset_url_mode` 调整
- CSS 可通过 `report_css_mode` 在 `external` 和 `inline` 间切换
- 当 `report_css_mode=inline` 时，会忽略 `report_asset_url_mode`
- `report_css_mode` 仅允许 `external|inline`，`report_asset_url_mode` 仅允许 `relative|absolute`
- CLI 支持 `--config`、`--date`、`--output-dir`、`--no-screenshot`
- 新闻源 URL 和 FGI API URL 已收回到代码内部常量，避免误配置导致功能失效
- 可通过 `report_output_dir` 或 CLI 的 `--output-dir` 将报告输出到独立目录
- 可通过 `enable_netlify_deploy=true`（或 CLI `--netlify-deploy`）在生成 HTML/截图后自动执行 Netlify 部署
- Netlify 部署依赖本机可用 `netlify` CLI，需配置 `netlify_site_id`；可选配置 `netlify_auth_token`
