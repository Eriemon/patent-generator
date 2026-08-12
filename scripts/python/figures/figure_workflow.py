#!/usr/bin/env python3
"""编排附图读取、渲染、登记与清单写入。"""

# 延迟解析类型注解，保持独立文件规格加载兼容。
from __future__ import annotations

# 标准库提供路径解析和标准输出能力。
import sys
from pathlib import Path

# 复用已登记职责模块的稳定公共函数。
from readable_patent_figure_layout import load_runtime_support_module

# 正文提取模块保留原参数入口以及步骤、模块解析行为。
from readable_patent_figure_content import build_parser, extract_method_steps, extract_system_modules

# 渲染模块负责 SVG、PNG 和 Mermaid 三类资产写入。
from readable_patent_figure_renderers import (
    render_flow_svg,
    render_module_svg,
    write_flow_png,
    write_mermaid_files,
    write_module_png,
)

# 登记模块负责清单构造、模型回填和审阅摘要生成。
from readable_patent_figure_registry import (
    build_manifest,
    make_artifact_paths,
    render_manifest_markdown,
    update_disclosure_model_figure_registry,
)

# 执行附图完整生成编排，保持原入口的参数、路径与输出顺序。
def main() -> int:
    """执行附图生成入口。

    参数：
    - 无。

    返回：
    - `int`：成功时返回 `0`。

    异常：
    - 找不到正文草稿时抛出 `FileNotFoundError`。
    - 共享支持加载或文件写入失败时由底层异常上抛。
    """

    # 加载共享运行时支持模块，复用正文后链的一致文件与时间工具。
    module_runtime_support = load_runtime_support_module()  # 共享运行时支持模块

    # 解析命令行参数，读取案件目录和可选输入草稿路径。
    namespace_arguments = build_parser().parse_args()  # 附图入口参数对象

    # 解析案件目录绝对路径，确保附图产物固定落在当前案件空间。
    path_case_dir = Path(namespace_arguments.case_dir).resolve()  # 当前案件根目录

    # 在调用方显式给出输入草稿时解析其绝对路径，否则保留空值供自动定位逻辑处理。
    path_input = Path(namespace_arguments.input).resolve() if namespace_arguments.input else None  # 显式指定的输入草稿路径

    # 定位当前案件可用的 disclosure draft，优先使用显式输入路径。
    path_markdown = module_runtime_support.find_disclosure_draft(path_case_dir, path_input)  # 当前案件正文草稿路径

    # 在找不到可用正文草稿时立即报错，避免生成与案件脱节的附图。
    if path_markdown is None or not path_markdown.exists():

        # 抛出明确错误，提醒调用方先完成 disclosure draft 阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 disclosure draft markdown。")

    # 读取正文草稿全文，供步骤和模块提取逻辑复用。
    str_markdown = path_markdown.read_text(encoding="utf-8")  # 正文草稿 Markdown 全文

    # 提取结构化方法步骤，供方法流程图生成逻辑复用。
    list_steps = extract_method_steps(str_markdown, module_runtime_support)  # 结构化方法步骤列表

    # 提取结构化系统模块，供系统模块图生成逻辑复用。
    list_modules = extract_system_modules(str_markdown, module_runtime_support)  # 结构化系统模块列表

    # 确保附图输出目录存在，后续 SVG、Mermaid 与 manifest 都会落在这里。
    path_output_dir = module_runtime_support.ensure_dir(path_case_dir / "05_figures")  # 附图输出目录

    # 固定方法流程图 SVG 输出路径，保持附图目录命名稳定。
    path_flow_svg = path_output_dir / "图1_方法流程图.svg"  # 方法流程图 SVG 输出路径

    # 固定方法流程图 PNG 输出路径，作为正式主稿嵌图交付资产。
    path_flow_png = path_output_dir / "图1_方法流程图.png"  # 方法流程图 PNG 交付路径

    # 固定系统模块图 SVG 输出路径，保持附图目录命名稳定。
    path_module_svg = path_output_dir / "图2_系统模块图.svg"  # 系统模块图 SVG 输出路径

    # 固定系统模块图 PNG 输出路径，作为正式主稿嵌图交付资产。
    path_module_png = path_output_dir / "图2_系统模块图.png"  # 系统模块图 PNG 交付路径

    # 渲染并写出方法流程图 SVG 文本。
    module_runtime_support.write_text_file(path_flow_svg, render_flow_svg(list_steps))

    # 渲染并写出方法流程图 PNG 文件，作为正文嵌图交付资产。
    write_flow_png(path_flow_png, list_steps)

    # 渲染并写出系统模块图 SVG 文本。
    module_runtime_support.write_text_file(path_module_svg, render_module_svg(list_modules))

    # 渲染并写出系统模块图 PNG 文件，作为正文嵌图交付资产。
    write_module_png(path_module_png, list_modules)

    # 写出两份 Mermaid 源文件，便于后续增强渲染。
    write_mermaid_files(path_output_dir, list_steps, list_modules, module_runtime_support)

    # 先收拢附图资产路径参数序列，避免命名合规修复引入新的超长单行。
    list_artifact_path_args = [path_markdown, path_flow_svg, path_flow_png, path_module_svg, path_module_png]  # 附图资产路径参数序列

    # 先组装附图资产路径对象，供 manifest 构造逻辑统一消费。
    figure_artifact_paths_artifact_paths = make_artifact_paths(*list_artifact_path_args)  # 附图路径集

    # 为 manifest 构造调用准备共享支持别名，避免调用行超过当前项目长度阈值。
    module_support = module_runtime_support  # manifest 构造使用的共享支持模块

    # 再生成 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    dict_manifest = build_manifest(figure_artifact_paths_artifact_paths, list_steps, list_modules, module_support)  # 待落盘的 figures manifest 结果

    # 固定 figures manifest JSON 输出路径，保持后链读取约定稳定。
    path_manifest_json = path_output_dir / "figures_manifest.json"  # figures manifest JSON 输出路径

    # 把 figures manifest JSON 写入案件目录。
    module_runtime_support.write_json_file(path_manifest_json, dict_manifest)

    # 回填正式结构化模型中的附图来源与正文绑定，禁止交付图件脱离模型真相层。
    update_disclosure_model_figure_registry(path_case_dir, dict_manifest, module_runtime_support)

    # 渲染供人工快速审阅的 Markdown 摘要文本。
    str_manifest_markdown = render_manifest_markdown(path_markdown)  # figures manifest Markdown 摘要文本

    # 固定供人工审阅的 Markdown 摘要输出路径，避免与 JSON manifest 混淆。
    path_manifest_markdown = path_output_dir / "figures_manifest.md"  # 附图摘要 Markdown 输出路径

    # 把面向人工的附图摘要 Markdown 写入案件目录。
    module_runtime_support.write_text_file(path_manifest_markdown, str_manifest_markdown)

    # 把 manifest JSON 绝对路径作为机器可读输出写回上游流程。
    sys.stdout.write(str(path_manifest_json.resolve()) + "\n")

    # 返回成功状态码，表示附图相关产物都已完成落盘。
    return 0

# 在脚本被直接执行时进入命令行主流程，导入场景下不产生副作用。
if __name__ == "__main__":

    # 把主流程退出码交还给当前 shell 调用方。
    raise SystemExit(main())
