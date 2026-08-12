#!/usr/bin/env python3
"""管理附图 manifest、登记表与结构化模型回填。"""

# 延迟解析类型注解，保持独立文件规格加载兼容。
from __future__ import annotations

# 标准库提供附图路径结构与通用类型标注。
from dataclasses import dataclass
from pathlib import Path
from typing import Any
# 把附图资产路径收敛成轻量结构，避免 manifest 构造函数携带过多离散路径参数。
@dataclass(frozen=True)
class FigureArtifactPaths:
    """承载附图交付资产路径。"""

    # 记录正文草稿路径，供 manifest 溯源原始 disclosure draft。
    path_markdown: Path  # 正文草稿路径

    # 记录方法流程图 SVG 路径，供 review 阶段复用矢量稿。
    path_flow_svg: Path  # 方法流程图 SVG 路径

    # 记录方法流程图 PNG 路径，供正式 DOCX 主稿嵌图复用。
    path_flow_png: Path  # 交付主稿嵌图使用的流程图 PNG

    # 记录系统模块图 SVG 路径，供 review 阶段复用矢量稿。
    path_module_svg: Path  # 系统模块图 SVG 路径

    # 记录系统模块图 PNG 路径，供正式 DOCX 主稿嵌图复用。
    path_module_png: Path  # 交付主稿嵌图使用的系统图 PNG

# 以短函数名集中构造附图资产路径对象，避免主流程里出现超长 dataclass 初始化语句。
def make_artifact_paths(
    path_markdown: Path,
    path_flow_svg: Path,
    path_flow_png: Path,
    path_module_svg: Path,
    path_module_png: Path,
) -> FigureArtifactPaths:
    """构造附图资产路径对象。

    参数：
    - `path_markdown`：正文草稿路径。
    - `path_flow_svg`：方法流程图 SVG 路径。
    - `path_flow_png`：方法流程图 PNG 路径。
    - `path_module_svg`：系统模块图 SVG 路径。
    - `path_module_png`：系统模块图 PNG 路径。

    返回：
    - `FigureArtifactPaths`：统一封装后的附图资产路径对象。

    异常：
    - 无。
    """

    # 返回统一封装后的附图资产路径对象，供 manifest 构造逻辑直接消费。
    return FigureArtifactPaths(path_markdown, path_flow_svg, path_flow_png, path_module_svg, path_module_png)

# 组装 figures manifest 结构化数据，供 review 和 export 阶段复用。
def build_manifest(
    obj_artifact_paths: FigureArtifactPaths,
    list_steps: list[dict[str, str]],
    list_modules: list[dict[str, str]],
    module_runtime_support: Any,
) -> dict[str, Any]:
    """构造 figures manifest 结构化数据。

    参数：
    - `obj_artifact_paths`：附图交付资产路径集合。
    - `list_steps`：结构化方法步骤列表。
    - `list_modules`：结构化系统模块列表。
    - `module_runtime_support`：共享运行时支持模块对象。

    返回：
    - `dict[str, Any]`：figures manifest 结构化数据。

    异常：
    - 无。
    """

    # 提取方法流程图中的步骤编号列表，供 manifest 索引与后续校验复用。
    list_step_ids = [dict_step["id"] for dict_step in list_steps]  # 方法流程图步骤编号列表

    # 提取系统模块图中的模块名称列表，供 manifest 索引与后续校验复用。
    list_module_names = [dict_module["name"] for dict_module in list_modules]  # 系统模块图模块名称列表

    # 先组装附图元数据条目列表，保持图1 与图2 的交付语义集中管理。
    list_figures = [
        {
            "figure_no": "图1",  # 方法流程图图号
            "title": "方法流程图",  # 方法流程图标题
            "file": obj_artifact_paths.path_flow_svg.name,  # review 阶段复用的 SVG 文件名
            "delivery_file": obj_artifact_paths.path_flow_png.name,  # 正式交付 PNG 文件名
            "steps": list_step_ids,  # 方法流程图步骤索引列表
        },
        {
            "figure_no": "图2",  # 系统模块图图号
            "title": "系统模块图",  # 系统模块图标题
            "file": obj_artifact_paths.path_module_svg.name,  # review 阶段读取的系统图 SVG 文件名
            "delivery_file": obj_artifact_paths.path_module_png.name,  # 正式交付使用的系统图 PNG 文件名
            "modules": list_module_names,  # 系统模块图模块索引列表
        },
    ]  # figures manifest 附图条目列表

    # 再组装正式交付要暴露的附图文件清单，固定 PNG+SVG 双输出顺序。
    list_delivery_files = [
        obj_artifact_paths.path_flow_png.name,  # 方法流程图 PNG 文件名
        obj_artifact_paths.path_flow_svg.name,  # 正式交付中的流程图 SVG 文件名
        obj_artifact_paths.path_module_png.name,  # 系统模块图 PNG 文件名
        obj_artifact_paths.path_module_svg.name,  # 正式交付中的系统图 SVG 文件名
    ]  # 正式交付附图文件名列表

    # 返回完整 figures manifest 结构化数据，供 JSON 落盘与后链工具复用。
    return {
        "generated_at": module_runtime_support.iso_now(),
        "source_draft": str(obj_artifact_paths.path_markdown.resolve()),
        "figures": list_figures,
        "delivery_files": list_delivery_files,
    }

# 把附图 manifest 转换为模型中的来源与正文绑定登记表。
def build_figure_registry(dict_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """构造附图来源登记表。

    参数：
    - `dict_manifest`：已生成的 figures manifest。

    返回：
    - `list[dict[str, Any]]`：可写入结构化交底模型的附图登记表。

    异常：
    - manifest 中的 `figures` 不是列表时抛出 `ValueError`。
    """

    # 读取附图条目并验证容器类型，防止损坏 manifest 被写入正式模型。
    list_figures = dict_manifest.get("figures", [])  # manifest 附图条目

    # manifest 容器类型错误时立即阻断，避免继续解释不可信结构。
    if not isinstance(list_figures, list):

        # 抛出明确结构错误，要求调用方修复 manifest 后重新生成。
        raise ValueError("> ERR: [Python] figures manifest 的 figures 必须为列表。")

    # 保留正文草稿绝对路径，作为每张图的统一生成来源。
    str_provenance = str(dict_manifest.get("source_draft", "")).strip()  # 附图生成来源

    # 按 manifest 稳定顺序生成 FIG 标识，保持多次运行结果一致。
    list_registry: list[dict[str, Any]] = []  # 附图来源登记表

    # 逐条转换正式附图，保持 manifest 顺序与 FIG 标识一致。
    for int_index, dict_figure in enumerate(list_figures, start=1):

        # 非对象条目无法提供图号、文件和来源索引，必须立即阻断。
        if not isinstance(dict_figure, dict):

            # 抛出明确条目类型错误，避免生成部分有效的附图登记表。
            raise ValueError("> ERR: [Python] figures manifest 的附图条目必须为对象。")

        # 流程图使用步骤索引，模块图使用模块索引，二者统一映射为 source_items。
        list_source_items = dict_figure.get("steps", dict_figure.get("modules", []))  # 图内结构索引

        # 图内索引不是列表时无法建立稳定映射，必须停止回填。
        if not isinstance(list_source_items, list):

            # 抛出明确索引类型错误，要求修复附图生成输入。
            raise ValueError("> ERR: [Python] 附图 steps/modules 必须为列表。")

        # 记录来源、图号、文件及正文绑定，供审查与导出阶段交叉验证。
        list_registry.append(
            {
                "figure_id": f"FIG{int_index:03d}",
                "figure_no": str(dict_figure.get("figure_no", "")).strip(),
                "title": str(dict_figure.get("title", "")).strip(),
                "provenance": str_provenance,
                "section_ids": ["4.2", "5", "6"],
                "file": str(dict_figure.get("file", "")).strip(),
                "delivery_file": str(dict_figure.get("delivery_file", "")).strip(),
                "source_items": [str(obj_item).strip() for obj_item in list_source_items],
            }
        )

    # 返回与模型版本三合同兼容的附图登记表。
    return list_registry

# 在附图完成后回填结构化交底模型，避免模型与交付图件脱节。
def update_disclosure_model_figure_registry(
    path_case_dir: Path,
    dict_manifest: dict[str, Any],
    module_runtime_support: Any,
) -> Path:
    """回填结构化模型中的附图登记表。

    参数：
    - `path_case_dir`：当前案件根目录。
    - `dict_manifest`：已生成的 figures manifest。
    - `module_runtime_support`：共享运行时支持模块。

    返回：
    - `Path`：完成回填的结构化模型路径。

    异常：
    - 模型文件不存在时抛出 `FileNotFoundError`。
    - 模型顶层不是对象时抛出 `ValueError`。
    """

    # 固定读取正式版本三模型，禁止在附图阶段另建旁路真相文件。
    path_model = path_case_dir / "03_drafts" / "latest_disclosure_model.json"  # 正式结构化模型路径

    # 模型不存在时禁止附图旁路落盘，以免交付图件脱离模型真相层。
    if not path_model.exists():

        # 抛出明确缺失错误，要求先完成正式交底模型生成阶段。
        raise FileNotFoundError("> ERR: [Python] 缺少 latest_disclosure_model.json，不能登记附图来源。")

    # 读取并验证模型顶层类型，避免覆盖损坏或非对象 JSON。
    dict_model = module_runtime_support.read_json_file(path_model)  # 当前结构化交底模型

    # 非对象模型无法安全更新登记表，必须保留原文件并停止处理。
    if not isinstance(dict_model, dict):

        # 抛出明确结构错误，避免覆盖损坏的模型文件。
        raise ValueError("> ERR: [Python] latest_disclosure_model.json 顶层必须为对象。")

    # 使用本次 manifest 重建附图登记表，使重复运行保持幂等。
    dict_model["figure_registry"] = build_figure_registry(dict_manifest)  # 本次附图来源登记表

    # 原位写回正式模型，让后续验证和 DOCX 导出读取同一事实源。
    module_runtime_support.write_json_file(path_model, dict_model)

    # 返回模型路径，便于调用方测试或记录本次回填目标。
    return path_model

# 生成 figures manifest 的 Markdown 摘要文本，便于人工快速审阅。
def render_manifest_markdown(path_markdown: Path) -> str:
    """渲染 figures manifest Markdown 摘要文本。

    参数：
    - `path_markdown`：正文草稿路径。

    返回：
    - `str`：figures manifest Markdown 摘要文本。

    异常：
    - 无。
    """

    # 按固定顺序直接组装摘要 Markdown 文本，输出标题、来源草稿和两条附图摘要。
    return "\n".join(
        [
            "# Figures Manifest",  # 文档标题
            "",  # 标题后的空行
            f"Source draft: `{path_markdown.name}`",  # 来源草稿文件名
            "",  # 来源草稿后的空行
            "- 图1：方法流程图",  # 图1 摘要
            "- 图2：系统模块图",  # 图2 的摘要条目
            "",  # 文档结尾空行
        ]
    )

# 执行附图生成入口，读取正文草稿并落盘 SVG、Mermaid 与 manifest 产物。
