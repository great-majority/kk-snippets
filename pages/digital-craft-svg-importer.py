import copy
import io
import math
from pathlib import Path
from typing import Any

import numpy as np
import pathops
import streamlit as st
import wildmeshing as wildmeshing_lib
from kkloader import HoneycomeSceneData
from PIL import Image, ImageDraw
from scipy.optimize import least_squares
from svgelements import SVG, Arc, Close, CubicBezier, Move, QuadraticBezier
from svgelements import Path as SVGPath

DEG2RAD = math.pi / 180.0

TRANSLATIONS = {
    "ja": {
        "language_label": "Language / 言語",
        "title": "デジクラ SVG ビルダー",
        "subtitle": "SVG画像をデジクラ内で扱えるよう変換します。",
        "qa_title": "Q&A",
        "qa_content": """
**Q: SVGアイコン画像はどこで入手できる？**

A: ライセンスフリーのSVG画像が

- [Google Fonts](https://fonts.google.com/icons)
- [Phosphor Icons](https://phosphoricons.com/)
- [Fonts Awesome](https://fontawesome.com/icons/classic/solid/classic)

などにあります。これ以外にも、「SVG 配布」などで検索してみると良いでしょう。

**Q: 図形が多すぎて重い！ or 図形がカクカクする！**

A: 「詳細設定」の「曲線のなめらかさ」と「三角形の粗さ」を調整してみてください。デフォルトではなめらかめにしてあるため、三角形がちょっと多くなっている可能性があります。

**Q: なんか図形が変になった！**

A: すみません、おそらくバグです！[githubのissue](https://github.com/great-majority/kk-snippets/issues)に不具合が起きた画像とともに報告してもらえれば対応できるかも知れません。
""",
        "upload_label": "SVGファイル",
        "upload_info": "SVGファイルを読み込んでください。",
        "color_label": "色",
        "alpha_label": "透明度",
        "height_label": "縦長サイズ",
        "size_help": "だいたいこの図の数字の大きさがそのまま図形の縦長に一致するようになっています。",
        "text_size_example": "オブジェクトサイズの例",
        "use_svg_color_label": "SVGの色を使用する",
        "use_svg_color_help": "各要素のfill/stroke色をそのまま使います。チェックを外すと色選択が有効になります。",
        "advanced_settings": "詳細設定",
        "curve_smoothness_label": "曲線のなめらかさ",
        "curve_smoothness_help": "高いほどSVGの曲線を細かく読み込みます。三角形数と生成時間が増える場合があります。",
        "curve_smoothness_presets": {
            1: "軽量",
            2: "粗い",
            3: "標準",
            4: "なめらか",
            5: "高精細",
        },
        "mesh_edge_length_r_label": "三角形の粗さ",
        "mesh_edge_length_r_help": "大きいほど三角形が少なくなり、小さいほど細かくなります。",
        "plane_preset_label": "平面プリセット",
        "plane_preset_map": "平面(マップ)",
        "plane_preset_character": "平面(キャラ)",
        "light_influence_label": "ライトの影響度",
        "parse_error": "SVGの解析に失敗しました: {error}",
        "no_contours": "有効な輪郭が見つかりませんでした。",
        "input_preview_title": "入力SVGプレビュー",
        "generate_button": "シーンを生成",
        "generating": "シーンを生成中...",
        "success_generate": "生成完了 ({count} triangles)",
        "scene_info_title": "シーン情報",
        "scene_total_triangles": "総三角形数",
        "scene_accepted": "採用数",
        "scene_failed": "失敗数",
        "warn_solver": "せん断解が収束しなかったため {count} 個の三角形をスキップしました。",
        "warn_reconstruction": "再構成誤差が閾値超過のため {count} 個の三角形をスキップしました。",
        "reconstruction_info": "再構成誤差(採用): max={max_err:.3e}, rmse={rmse:.3e}, threshold={tol:.3e}",
        "triangulation_title": "三角形分割プレビュー",
        "triangulation_empty": "分割結果がありません。",
        "metadata_folder": "メタデータ",
        "scene_root": "SVG",
        "meta_source": "SVGファイル",
        "meta_color": "色",
        "meta_alpha": "透明度",
        "meta_height": "高さ",
        "meta_plane_preset": "平面プリセット",
        "meta_light_influence": "ライトの影響度",
        "meta_curve_smoothness": "曲線のなめらかさ",
        "meta_edge_length_r": "三角形の粗さ",
        "download_button": "シーンファイルをダウンロード",
    },
    "en": {
        "language_label": "Language / 言語",
        "title": "Digital Craft SVG Builder",
        "subtitle": "Convert SVG images for use in Digital Craft.",
        "qa_title": "Q&A",
        "qa_content": """
**Q: Where can I get SVG icon images?**

A: License-free SVG images are available from sources such as:

- [Google Fonts](https://fonts.google.com/icons)
- [Phosphor Icons](https://phosphoricons.com/)
- [Font Awesome](https://fontawesome.com/icons/classic/solid/classic)

You can also search for terms like "free SVG icons" or "SVG icon library".

**Q: There are too many shapes and the scene is heavy, or the shape looks jagged!**

A: Try adjusting "Curve smoothness" and "Triangle coarseness" in Advanced Settings. The defaults are set to be fairly smooth, so the scene may contain more triangles than necessary.

**Q: The shape looks wrong!**

A: Sorry, that is probably a bug. If you report it on [GitHub Issues](https://github.com/great-majority/kk-snippets/issues) with the image that caused the problem, I may be able to fix it.
""",
        "upload_label": "SVG file",
        "upload_info": "Load an SVG file.",
        "color_label": "Color",
        "alpha_label": "Opacity",
        "height_label": "Vertical size",
        "size_help": "The number in this example roughly matches the vertical size of the generated shape.",
        "text_size_example": "Object size example",
        "use_svg_color_label": "Use SVG colors",
        "use_svg_color_help": "Apply each element's fill/stroke color. Uncheck to use the color picker instead.",
        "advanced_settings": "Advanced Settings",
        "curve_smoothness_label": "Curve smoothness",
        "curve_smoothness_help": "Higher values load SVG curves more finely. This may increase triangle count and generation time.",
        "curve_smoothness_presets": {
            1: "Lightweight",
            2: "Coarse",
            3: "Standard",
            4: "Smooth",
            5: "High detail",
        },
        "mesh_edge_length_r_label": "Triangle coarseness",
        "mesh_edge_length_r_help": "Higher values create fewer triangles; lower values create finer triangles.",
        "plane_preset_label": "Plane preset",
        "plane_preset_map": "Plane (Map)",
        "plane_preset_character": "Plane (Character)",
        "light_influence_label": "Light influence",
        "parse_error": "Failed to parse SVG: {error}",
        "no_contours": "No valid contours were found in the SVG.",
        "input_preview_title": "Input SVG Preview",
        "generate_button": "Generate Scene",
        "generating": "Generating scene...",
        "success_generate": "Generation complete ({count} triangles)",
        "scene_info_title": "Scene Info",
        "scene_total_triangles": "Total Triangles",
        "scene_accepted": "Accepted",
        "scene_failed": "Failed",
        "warn_solver": "Skipped {count} triangles because the shear solve did not converge.",
        "warn_reconstruction": "Skipped {count} triangles because reconstruction error exceeded tolerance.",
        "reconstruction_info": "Reconstruction error (accepted): max={max_err:.3e}, rmse={rmse:.3e}, threshold={tol:.3e}",
        "triangulation_title": "Triangulation Preview",
        "triangulation_empty": "No triangulation result.",
        "metadata_folder": "Metadata",
        "scene_root": "SVG",
        "meta_source": "SVG file",
        "meta_color": "Color",
        "meta_alpha": "Opacity",
        "meta_height": "Height",
        "meta_plane_preset": "Plane preset",
        "meta_light_influence": "Light influence",
        "meta_curve_smoothness": "Curve smoothness",
        "meta_edge_length_r": "Triangle coarseness",
        "download_button": "Download scene file",
    },
}


def get_text(key: str, lang: str = "ja") -> str:
    """言語コードに応じたUI文言を取得し、未定義時は英語へフォールバックする。"""
    localized = TRANSLATIONS.get(lang, TRANSLATIONS["ja"])
    if key in localized:
        return localized[key]
    return TRANSLATIONS["en"].get(key, key)


PLANE_PRESETS = {
    "map": {"category": 0, "no": 215},
    "character": {"category": 1, "no": 290},
}

TRIANGLE_PRESETS = {
    "map": {"category": 0, "no": 216},
    "character": {"category": 1, "no": 291},
}

CURVE_SMOOTHNESS_PRESETS = {
    1: {"error": 1e-2, "min_depth": 1, "max_depth": 2},
    2: {"error": 5e-3, "min_depth": 1, "max_depth": 3},
    3: {"error": 2e-3, "min_depth": 2, "max_depth": 3},
    4: {"error": 1e-3, "min_depth": 2, "max_depth": 3},
    5: {"error": 5e-4, "min_depth": 2, "max_depth": 4},
}
CURVE_SMOOTHNESS_DEFAULT = 4
SVG_SCENE_HEIGHT_FACTOR = 0.5


class MeshConfig:
    SOURCE_TRIANGLE = np.array(
        [[0.0, -0.1], [0.086, 0.05], [-0.086, 0.05]], dtype=np.float64
    )
    RECONSTRUCTION_MAX_ABS_TOL = 1e-4
    SOLVER_REACHABLE_RESIDUAL_TOL = 1e-5
    SOLVER_EARLY_BREAK_RESIDUAL_TOL = 1e-12
    SOLVER_MAX_NFEV = 120
    SOLVER_SX_MIN = 0.01
    SOLVER_SX_MAX = 0.999999
    SOLVER_CHILD_SCALE_MIN = 1e-4
    SOLVER_LM_REG_WEIGHT = 1e-6
    SVG_CURVE_SAMPLE_ERROR = 1e-3
    SVG_CURVE_SAMPLE_MIN_DEPTH = 2
    SVG_CURVE_SAMPLE_MAX_DEPTH = 3
    TRIWILD_STOP_QUALITY = 10.0
    TRIWILD_MAX_ITS = 80
    TRIWILD_STAGE = 1
    TRIWILD_EPSILON = -1.0
    TRIWILD_FEATURE_EPSILON = 1e-3
    TRIWILD_TARGET_EDGE_LEN = -1.0
    TRIWILD_EDGE_LENGTH_R = 0.8
    TRIWILD_FLAT_FEATURE_ANGLE = 10.0
    TRIWILD_CUT_OUTSIDE = True
    TRIWILD_SKIP_EPS = True
    TRIWILD_MUTE_LOG = True


TEMPLATE_SCENE_META = {
    "version": "1.0.0",
    "user_id": "deadbeef-dead-beef-dead-beefdeadbeef",
    "data_id": "deadbeef-dead-beef-dead-beefdeadbeef",
    "title": "Template",
    "unknown_1": 1,
    "unknown_2": b"#\\d7\xf1l\xf3\xdb?v\xe0X\xf8\x1cJ\xae\xfc\x10I\x96\x15k*P\xbf*u\x91.Yr\xbe",
    "unknown_tail_1": b"\xee\xaa|\xcfZ\xdc\x97>\x14A\xf6\xfagp'\x84PB\xd3ze_7\xba\xad\xb5\x15\xa8O\xc3F\xd3\x18\x8b\x13&i0\xc9\xa2\x94?\xdcm\\7\x05\xdc",
    "unknown_tail_2": b"\x9a\xd9\x0e\x878|>=k\x1e\x930S\xe9\xdf\x14e\xf3\x00\xb3b?\xcd\xf5\xa1UW{\x01\x98\xd3ob\xbd\x87\xba\xbf\xa3p\xfd.%\xaf'\xa3\x9d\x10>\x81s\xf2\xc7\x8f\x88\x8b.\x96e%\xc8\x1ba;\x0f[\x1e\xa8\xa2\xdd\xf6(\xea\xeaV\xe9\xa6\x0f\xb8\x15^\xde!X\x8e\xb0\x81\xfb\x87d\x89\x9d\xea\x14R\x988\xb7\xa2s\xba\x0e\xf1x2\xed\xd5U\xf6D\x9bJ\x82\xb9L\x8c\xed\xc3B\xd5\xc25\xe2%Z\xba@sN\x9f/\xac\x15\xedj\xabj\xe7\xed\xc2\xec\xdd\xb83\x11l\xf9?\x95B\xdf\r\x15rb<|V\xe7k~\xf1<Q,*@\tD\x97\x01,s\x1d\x8c\xfe!a\t\xfb6\\:2\xfd7\x00Q\x87\x05\x94*@kk!y\x05\xbf5\xef\x0e's\x03\xf5\t{wTa\xeb\xd65\xbc\xd9\xef\xb1\xabQ\xc2I\xec\x1a5",
    "unknown_tail_3": b"\xf8\xe8\x14J\x87\xe2\x8f8v\x07q\x1d\xf1?v\xf14(% \xea\xcb\xaex=lAln\x01{C\xfd\xe9\xb4\xe4\x8e\xfd\x96\xd7;\x85\xff-fr\x16\xfe",
    "unknown_tail_4": b"\xa0\x15a\t\x08\x07J\x0c\xac\xe0C>i\x99\xec\xe0y\xd1[MJ\x05\x0c\xa2\xfc\x96\xf6\xee&\x0c\xe1\x00)r)\xb9\xdf\xaa\xb4nV\x10\x0b\xec\xb6t\xa1\xd3\x95AP\xc2\xf0\x8aBd\x83\xd4\xb4p\xf5B\xce\xb7;k\xed\xf6\xfa\xbc\x1eJF\xcbt1\x87=\xebz\xac\xec^\xf7\x15 8i:QUh\x90!1v",
    "unknown_tail_5": b"`)g\xf9\x1cN\x99\xfb\xc1\x9e\x80\x19\x0c\x96\x16\xe0)t>,\xc8\xc2\xd4t\x89\x98\x91\xd1\xd1\xc4\xd8\xbc\xdf\x92\xcf*b\x0c\x1d\xbaM\xd1\x8a\xf4\x12\x87!\x18",
    "unknown_tail_6": b"\xaa\xf3\xff\xfb\xf4S\x80R\xda]7\x99\xdeig\xc6&\xd4\x187\x80\n\x80\xcf\x80\xd6Ch\x9amy\xb3X\x18\x88;\xce\xdb\x11&`\x89\x8c\x1c\xb7\x8a\xd8\xfe\x1e\x17\xa9l\x1f\xe4#\xb7\xf4\xdc\xc6kh\xaf\x9aB",
    "unknown_tail_7": b"b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE",
    "unknown_tail_8": b"b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE",
    "unknown_tail_9": b'\xf4+\x98\x84\xde\xc3-\x15\xb0M<\xe2!"\xd5\xa5',
    "unknown_tail_10": b"sR?\xa4b\xb8\t\xa6~\xb0\x10\xd3\xa0\xc9u\x16",
    "frame_filename": "",
    "unknown_tail_11": b"D\xaa\xee\x9b\xe40^\xf6+\xe7*d\x08H\xe1]",
    "footer_marker": "【DigitalCraft】",
    "unknown_tail_extra": b"",
}

TEMPLATE_FOLDER_KEY = 0
TEMPLATE_FOLDER_DATA = {
    "dicKey": 0,
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
    "treeState": 1,
    "visible": True,
    "name": "Folder",
    "child": [],
}

TEMPLATE_PLANE_DATA = {
    "dicKey": 1,
    "position": {"x": 0.0, "y": 0.0, "z": 0.0},
    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
    "treeState": 1,
    "visible": True,
    "title": 0,
    "group": 0,
    "category": 0,
    "no": 215,
    "anime_pattern": 0,
    "anime_speed": 1.0,
    "colors": [
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
        {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
    ],
    "shadow_type": -1,
    "shadow_switch": False,
    "shadow_strength": 0.0,
    "patterns": [
        {
            "key": 0,
            "filepath": "",
            "clamp": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
            "rot": 0.0,
        },
        {
            "key": 0,
            "filepath": "",
            "clamp": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
            "rot": 0.0,
        },
        {
            "key": 0,
            "filepath": "",
            "clamp": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
            "rot": 0.0,
        },
    ],
    "alpha": 1.0,
    "line_color": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0},
    "line_width": 0.0,
    "emission_color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
    "emission_power": 0.0,
    "light_cancel": 0.0,
    "panel": {
        "key": 0,
        "filepath": "",
        "clamp": False,
        "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
        "rot": 0.0,
    },
    "enable_fk": False,
    "bones": {},
    "enable_dynamic_bone": True,
    "anime_normalized_time": 0.0,
    "child": [],
}


def build_template_scene() -> HoneycomeSceneData:
    """最小構成のテンプレートシーンを組み立てる。"""
    scene = HoneycomeSceneData()
    scene.image = None
    scene.version = TEMPLATE_SCENE_META["version"]
    scene.dataVersion = TEMPLATE_SCENE_META["version"]
    scene.user_id = TEMPLATE_SCENE_META["user_id"]
    scene.data_id = TEMPLATE_SCENE_META["data_id"]
    scene.title = TEMPLATE_SCENE_META["title"]
    scene.unknown_1 = TEMPLATE_SCENE_META["unknown_1"]
    scene.unknown_2 = TEMPLATE_SCENE_META["unknown_2"]
    scene.unknown_tail_1 = TEMPLATE_SCENE_META["unknown_tail_1"]
    scene.unknown_tail_2 = TEMPLATE_SCENE_META["unknown_tail_2"]
    scene.unknown_tail_3 = TEMPLATE_SCENE_META["unknown_tail_3"]
    scene.unknown_tail_4 = TEMPLATE_SCENE_META["unknown_tail_4"]
    scene.unknown_tail_5 = TEMPLATE_SCENE_META["unknown_tail_5"]
    scene.unknown_tail_6 = TEMPLATE_SCENE_META["unknown_tail_6"]
    scene.unknown_tail_7 = TEMPLATE_SCENE_META["unknown_tail_7"]
    scene.unknown_tail_8 = TEMPLATE_SCENE_META["unknown_tail_8"]
    scene.unknown_tail_9 = TEMPLATE_SCENE_META["unknown_tail_9"]
    scene.unknown_tail_10 = TEMPLATE_SCENE_META["unknown_tail_10"]
    scene.frame_filename = TEMPLATE_SCENE_META["frame_filename"]
    scene.unknown_tail_11 = TEMPLATE_SCENE_META["unknown_tail_11"]
    scene.footer_marker = TEMPLATE_SCENE_META["footer_marker"]
    scene.unknown_tail_extra = TEMPLATE_SCENE_META["unknown_tail_extra"]

    folder_obj = {"type": 3, "data": copy.deepcopy(TEMPLATE_FOLDER_DATA)}
    folder_obj["data"]["child"] = [
        {"type": 1, "data": copy.deepcopy(TEMPLATE_PLANE_DATA)}
    ]
    scene.objects = {TEMPLATE_FOLDER_KEY: folder_obj}
    return scene


@st.cache_resource
def load_template() -> tuple[HoneycomeSceneData, dict[str, Any], int, dict[str, Any]]:
    """生成に使うテンプレート要素をキャッシュ付きで取得する。"""
    template_scene = build_template_scene()
    folder_key = TEMPLATE_FOLDER_KEY
    folder_obj = template_scene.objects[folder_key]
    plane_template = folder_obj["data"]["child"][0]
    return template_scene, plane_template, folder_key, folder_obj


def create_plane(
    template: dict[str, Any],
    x: float,
    y: float,
    z: float,
    color: dict[str, float],
    scale: float = 1.0,
) -> dict[str, Any]:
    """平面テンプレートを複製し、位置・色・一様スケールを反映する。"""
    plane = copy.deepcopy(template)
    plane["data"]["position"]["x"] = x
    plane["data"]["position"]["y"] = y
    plane["data"]["position"]["z"] = z
    plane["data"]["scale"]["x"] = scale
    plane["data"]["scale"]["y"] = scale
    plane["data"]["scale"]["z"] = scale
    plane["data"]["colors"][0] = color
    plane["data"]["line_width"] = 0.0
    return plane


def hex_to_color(hex_color: str) -> dict[str, float]:
    """#RRGGBB 文字列を 0-1 正規化 RGBA 辞書へ変換する。"""
    value = hex_color.lstrip("#")
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return {"r": r, "g": g, "b": b, "a": 1.0}


def build_metadata_folder(
    folder_obj: dict[str, Any], metadata: dict[str, Any], lang: str
) -> dict[str, Any]:
    """生成メタデータを子フォルダとして格納したフォルダを作る。"""
    info_folder = copy.deepcopy(folder_obj)
    info_folder["data"]["name"] = get_text("metadata_folder", lang)
    info_folder["data"]["treeState"] = 1
    info_folder["data"]["child"] = []

    for key, value in metadata.items():
        child_folder = copy.deepcopy(folder_obj)
        child_folder["data"]["name"] = f"{key}={value}"
        child_folder["data"]["treeState"] = 1
        child_folder["data"]["child"] = []
        info_folder["data"]["child"].append(child_folder)

    return info_folder


def render_scene_info(
    plane_count: int, raw_plane_count: int, mesh_stats: dict[str, Any], lang: str
) -> None:
    """三角形数の集計メトリクスを Streamlit 上に表示する。"""
    st.subheader(get_text("scene_info_title", lang))
    col1, col2, col3 = st.columns(3)
    failed = int(mesh_stats.get("solve_failed_count", 0)) + int(
        mesh_stats.get("reconstruction_failed_count", 0)
    )
    with col1:
        st.metric(get_text("scene_total_triangles", lang), f"{raw_plane_count}")
    with col2:
        st.metric(get_text("scene_accepted", lang), f"{plane_count}")
    with col3:
        st.metric(get_text("scene_failed", lang), f"{failed}")


class TriangleSolverOptimized:
    def __init__(self, source_xz: np.ndarray):
        """ソルバ計算で使うソース三角形の前計算行列を初期化する。"""
        source = np.asarray(source_xz, dtype=np.float64)
        if source.shape != (3, 2):
            raise ValueError("TriangleSolverOptimized requires source_xz shape (3, 2)")
        self.source_xz = source
        self.src0 = source[0]

        edge_1 = source[1] - source[0]
        edge_2 = source[2] - source[0]
        s00, s01 = float(edge_1[0]), float(edge_2[0])
        s10, s11 = float(edge_1[1]), float(edge_2[1])
        det = s00 * s11 - s01 * s10
        if abs(det) < 1e-14:
            raise ValueError("source triangle is degenerate")

        inv_det = 1.0 / det
        self.inv_source_edges = np.array(
            [[s11 * inv_det, -s01 * inv_det], [-s10 * inv_det, s00 * inv_det]],
            dtype=np.float64,
        )

    @staticmethod
    def effective_scale(sx: float, sz: float, theta_deg: float) -> tuple[float, float]:
        """回転を考慮した親スケールの実効 X/Z 係数を返す。"""
        rad = theta_deg * DEG2RAD
        cos2 = math.cos(rad) ** 2
        sin2 = math.sin(rad) ** 2
        return sx * cos2 + sz * sin2, sx * sin2 + sz * cos2

    @classmethod
    def _build_A_entries(
        cls,
        alpha: float,
        sx: float,
        sz: float,
        theta: float,
        child_x: float,
        child_z: float,
    ) -> tuple[float, float, float, float]:
        """現在パラメータに対応する線形変換行列 A の要素を計算する。"""
        alpha_rad = alpha * DEG2RAD
        theta_rad = theta * DEG2RAD
        cos_a, sin_a = math.cos(alpha_rad), math.sin(alpha_rad)
        cos_t, sin_t = math.cos(theta_rad), math.sin(theta_rad)

        a00 = child_x * (cos_a * sx * cos_t - sin_a * sz * sin_t)
        a01 = child_z * (cos_a * sx * sin_t + sin_a * sz * cos_t)
        a10 = child_x * (-sin_a * sx * cos_t - cos_a * sz * sin_t)
        a11 = child_z * (-sin_a * sx * sin_t + cos_a * sz * cos_t)
        return a00, a01, a10, a11

    def forward(
        self,
        source_xz: np.ndarray | None = None,
        *,
        px: float,
        pz: float,
        alpha: float,
        sx: float,
        theta: float,
        cs: float | None = None,
        cx: float | None = None,
        cz: float | None = None,
    ) -> np.ndarray:
        """解パラメータでソース三角形座標を前方変換する。"""
        source = (
            self.source_xz
            if source_xz is None
            else np.asarray(source_xz, dtype=np.float64)
        )
        sz = 1.0 - sx
        if cx is None or cz is None:
            if cs is None:
                raise ValueError("forward requires either cs or (cx, cz)")
            cx = cs
            cz = cs
        eff_x, eff_z = self.effective_scale(sx, sz, theta)
        if eff_x <= 1e-12 or eff_z <= 1e-12:
            raise ValueError("effective scale became too small")
        child_x = cx / eff_x
        child_z = cz / eff_z
        a00, a01, a10, a11 = self._build_A_entries(
            alpha, sx, sz, theta, child_x, child_z
        )

        out = np.empty((source.shape[0], 2), dtype=np.float64)
        src_x = source[:, 0]
        src_z = source[:, 1]
        out[:, 0] = a00 * src_x + a01 * src_z + px
        out[:, 1] = a10 * src_x + a11 * src_z + pz
        return out

    def reconstruction_error(
        self, target_xz: np.ndarray, solved: dict[str, Any]
    ) -> dict[str, float]:
        """再構成三角形と目標三角形の誤差指標を計算する。"""
        reconstructed = self.forward(
            px=solved["px"],
            pz=solved["pz"],
            alpha=solved["alpha"],
            sx=solved["sx"],
            theta=solved["theta"],
            cx=solved.get("cx"),
            cz=solved.get("cz"),
            cs=solved.get("cs"),
        )
        target = np.asarray(target_xz, dtype=np.float64)
        diff = reconstructed - target
        return {
            "max_abs": float(np.max(np.abs(diff))),
            "rmse": float(np.sqrt(np.mean(diff * diff))),
        }

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        out = np.empty_like(x)
        positive = x >= 0
        out[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
        exp_x = np.exp(x[~positive])
        out[~positive] = exp_x / (1.0 + exp_x)
        return out

    @staticmethod
    def _softplus(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0.0)

    @staticmethod
    def _softplus_inv(y: np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=np.float64)
        out = np.empty_like(y)
        small = y < 20.0
        out[small] = np.log(np.expm1(y[small]))
        out[~small] = y[~small]
        return out

    @staticmethod
    def _logit(p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=np.float64)
        return np.log(p) - np.log1p(-p)

    def _to_unconstrained(
        self,
        sx: float,
        cx: float,
        cz: float,
        sx_min: float,
        sx_span: float,
        c_min: float,
    ) -> tuple[float, float, float]:
        eps = 1e-12
        p = (sx - sx_min) / sx_span
        p = np.clip(p, eps, 1.0 - eps)
        u = float(self._logit(np.array([p], dtype=np.float64))[0])

        cx_pos = max(cx - c_min, eps)
        cz_pos = max(cz - c_min, eps)
        v = float(self._softplus_inv(np.array([cx_pos], dtype=np.float64))[0])
        w = float(self._softplus_inv(np.array([cz_pos], dtype=np.float64))[0])
        return u, v, w

    def _from_unconstrained(
        self,
        u: float,
        v: float,
        w: float,
        sx_min: float,
        sx_max: float,
        sx_span: float,
        c_min: float,
    ) -> tuple[float, float, float, float]:
        sx = sx_min + sx_span * float(self._sigmoid(np.array([u], dtype=np.float64))[0])
        sx = float(np.clip(sx, sx_min, sx_max))
        sz = 1.0 - sx
        cx = c_min + float(self._softplus(np.array([v], dtype=np.float64))[0])
        cz = c_min + float(self._softplus(np.array([w], dtype=np.float64))[0])
        return sx, sz, cx, cz

    def solve(self, target_xz: np.ndarray) -> dict[str, Any]:
        """ソース三角形を目標三角形へ写す変換パラメータを LM で推定する。"""
        target = np.asarray(target_xz, dtype=np.float64)
        if target.shape != (3, 2):
            raise ValueError("target_xz must be shape (3, 2)")

        sx_min = float(MeshConfig.SOLVER_SX_MIN)
        sx_max = float(MeshConfig.SOLVER_SX_MAX)
        c_min = float(MeshConfig.SOLVER_CHILD_SCALE_MIN)
        reg_weight = float(MeshConfig.SOLVER_LM_REG_WEIGHT)
        if not (0.0 < sx_min < sx_max < 1.0):
            return {"reachable": False, "residual": float("inf")}
        sx_span = sx_max - sx_min

        q0 = target[0]
        dq1 = target[1] - q0
        dq2 = target[2] - q0
        target_edges = np.array([[dq1[0], dq2[0]], [dq1[1], dq2[1]]], dtype=np.float64)

        a_target = target_edges @ self.inv_source_edges
        translation = q0 - a_target @ self.src0

        t00, t01 = float(a_target[0, 0]), float(a_target[0, 1])
        t10, t11 = float(a_target[1, 0]), float(a_target[1, 1])

        u_mat, sigma, v_mat = np.linalg.svd(a_target)
        if np.linalg.det(u_mat) < 0:
            u_mat[:, 1] *= -1
            sigma[1] *= -1
        if np.linalg.det(v_mat) < 0:
            v_mat[1, :] *= -1
            sigma[1] *= -1

        alpha_0 = math.atan2(u_mat[0, 1], u_mat[0, 0]) / DEG2RAD
        theta_0 = math.atan2(v_mat[0, 1], v_mat[0, 0]) / DEG2RAD
        sigma_abs = np.abs(sigma)
        cx_0 = max(float(sigma_abs[0]), c_min)
        cz_0 = max(float(sigma_abs[1]), c_min)
        cs_0 = max(float(sigma_abs[0] + sigma_abs[1]), 0.02)
        sx_0 = float(np.clip(float(sigma_abs[0] / cs_0), sx_min + 1e-8, sx_max - 1e-8))

        candidates_direct = [
            (alpha_0, sx_0, theta_0, cx_0, cz_0),
            (alpha_0 + 180, sx_0, theta_0 + 180, cx_0, cz_0),
            (alpha_0, 1 - sx_0, theta_0 + 90, cz_0, cx_0),
            (alpha_0 + 180, 1 - sx_0, theta_0 + 270, cz_0, cx_0),
            (alpha_0 + 90, 1 - sx_0, theta_0, cz_0, cx_0),
            (alpha_0 + 90, sx_0, theta_0 + 90, cx_0, cz_0),
            (alpha_0 + 270, 1 - sx_0, theta_0 + 180, cz_0, cx_0),
            (alpha_0 + 270, sx_0, theta_0 + 270, cx_0, cz_0),
        ]

        candidates: list[np.ndarray] = []
        for alpha, sx, theta, cx, cz in candidates_direct:
            sx_clamped = float(np.clip(sx, sx_min + 1e-8, sx_max - 1e-8))
            cx_clamped = max(float(cx), c_min + 1e-8)
            cz_clamped = max(float(cz), c_min + 1e-8)
            u, v, w = self._to_unconstrained(
                sx_clamped, cx_clamped, cz_clamped, sx_min, sx_span, c_min
            )
            candidates.append(
                np.array([float(alpha), u, float(theta), v, w], dtype=np.float64)
            )

        def make_equations(prior: np.ndarray):
            def equations(unconstrained_params: np.ndarray) -> np.ndarray:
                alpha, u, theta, v, w = unconstrained_params
                sx, sz, cx, cz = self._from_unconstrained(
                    float(u),
                    float(v),
                    float(w),
                    sx_min,
                    sx_max,
                    sx_span,
                    c_min,
                )
                eff_x, eff_z = self.effective_scale(sx, sz, float(theta))
                if eff_x <= 1e-8 or eff_z <= 1e-8:
                    geom = np.array([1e3, 1e3, 1e3, 1e3], dtype=np.float64)
                else:
                    child_x = cx / eff_x
                    child_z = cz / eff_z
                    a00, a01, a10, a11 = self._build_A_entries(
                        float(alpha), sx, sz, float(theta), child_x, child_z
                    )
                    geom = np.array(
                        [a00 - t00, a01 - t01, a10 - t10, a11 - t11], dtype=np.float64
                    )
                # method="lm" は残差次元>=変数次元が必要なので微小正則化を加える。
                reg = reg_weight * (unconstrained_params - prior)
                return np.concatenate([geom, reg])

            return equations

        best_params: np.ndarray | None = None
        best_residual = float("inf")
        for initial in candidates:
            equations = make_equations(initial)
            try:
                optimized = least_squares(
                    equations,
                    x0=initial,
                    method="lm",
                    max_nfev=MeshConfig.SOLVER_MAX_NFEV,
                    ftol=1e-12,
                    xtol=1e-12,
                    gtol=1e-12,
                )
            except (ValueError, RuntimeError, FloatingPointError):
                continue

            geom = equations(optimized.x)[:4]
            residual = float(np.sum(geom**2))
            if residual < best_residual:
                best_residual = residual
                best_params = optimized.x
            if residual < MeshConfig.SOLVER_EARLY_BREAK_RESIDUAL_TOL:
                break

        if best_params is None:
            return {"reachable": False, "residual": float("inf")}

        alpha, u, theta, v, w = best_params
        sx, sz, cx, cz = self._from_unconstrained(
            float(u), float(v), float(w), sx_min, sx_max, sx_span, c_min
        )
        eff_x, eff_z = self.effective_scale(sx, sz, float(theta))
        if eff_x <= 1e-12 or eff_z <= 1e-12:
            return {"reachable": False, "residual": float("inf")}

        return {
            "px": float(translation[0]),
            "pz": float(translation[1]),
            "alpha": float(float(alpha) % 360),
            "sx": float(sx),
            "sz": float(sz),
            "theta": float(float(theta) % 360),
            "cx": float(cx),
            "cz": float(cz),
            "cs": float(0.5 * (cx + cz)),
            "child_sx": float(cx / eff_x),
            "child_sz": float(cz / eff_z),
            "residual": best_residual,
            "reachable": best_residual < MeshConfig.SOLVER_REACHABLE_RESIDUAL_TOL,
        }


class MeshPipeline:
    @staticmethod
    def default_advanced_settings() -> dict[str, Any]:
        """詳細設定UIの初期値セットを返す。"""
        return {
            "curve_smoothness": CURVE_SMOOTHNESS_DEFAULT,
            "edge_length_r": float(MeshConfig.TRIWILD_EDGE_LENGTH_R),
        }

    @staticmethod
    def render_advanced_settings(lang: str) -> dict[str, Any]:
        """詳細設定UIを描画し、入力値を設定辞書で返す。"""
        settings: dict[str, Any] = {}
        settings["curve_smoothness"] = st.slider(
            get_text("curve_smoothness_label", lang),
            min_value=1,
            max_value=5,
            value=CURVE_SMOOTHNESS_DEFAULT,
            step=1,
            format="%d",
            help=get_text("curve_smoothness_help", lang),
        )
        curve_labels = get_text("curve_smoothness_presets", lang)
        if isinstance(curve_labels, dict):
            selected_label = curve_labels.get(settings["curve_smoothness"])
            if selected_label:
                st.caption(f"{settings['curve_smoothness']}: {selected_label}")

        settings["edge_length_r"] = st.slider(
            get_text("mesh_edge_length_r_label", lang),
            min_value=0.10,
            max_value=1.00,
            value=float(MeshConfig.TRIWILD_EDGE_LENGTH_R),
            step=0.05,
            help=get_text("mesh_edge_length_r_help", lang),
        )
        return settings

    @staticmethod
    def apply_curve_smoothness_settings(curve_smoothness: int) -> None:
        """SVG曲線のプリセット精度を MeshConfig に反映する。"""
        preset = CURVE_SMOOTHNESS_PRESETS.get(
            int(curve_smoothness), CURVE_SMOOTHNESS_PRESETS[CURVE_SMOOTHNESS_DEFAULT]
        )
        MeshConfig.SVG_CURVE_SAMPLE_ERROR = float(preset["error"])
        MeshConfig.SVG_CURVE_SAMPLE_MIN_DEPTH = int(preset["min_depth"])
        MeshConfig.SVG_CURVE_SAMPLE_MAX_DEPTH = int(preset["max_depth"])

    @staticmethod
    def apply_triwild_settings(*, edge_length_r: float) -> None:
        """TriWild関連のメッシュ設定を MeshConfig に反映する。"""
        MeshConfig.TRIWILD_STOP_QUALITY = 10.0
        MeshConfig.TRIWILD_EDGE_LENGTH_R = float(edge_length_r)
        MeshConfig.TRIWILD_TARGET_EDGE_LEN = -1.0

    @staticmethod
    def polygon_signed_area(points: np.ndarray) -> float:
        """靴紐公式で多角形の符号付き面積を計算する。"""
        x_values = points[:, 0]
        y_values = points[:, 1]
        return float(
            0.5
            * (
                np.dot(x_values, np.roll(y_values, -1))
                - np.dot(y_values, np.roll(x_values, -1))
            )
        )

    @staticmethod
    def dedupe_contour_points(contour: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        """連続重複点と終端重複点を許容誤差付きで除去する。"""
        if len(contour) <= 1:
            return contour
        deduped = [contour[0]]
        for point in contour[1:]:
            if np.linalg.norm(point - deduped[-1]) > eps:
                deduped.append(point)
        if len(deduped) > 2 and np.linalg.norm(deduped[0] - deduped[-1]) <= eps:
            deduped = deduped[:-1]
        return np.asarray(deduped, dtype=np.float64)

    @staticmethod
    def point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
        """レイキャスト法で点が多角形内部かを判定する。"""
        px, py = point
        inside = False
        count = len(polygon)
        j = count - 1
        for i in range(count):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi + 1e-15) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    @staticmethod
    def build_contour_hierarchy(
        contours: list[np.ndarray],
    ) -> tuple[list[int], list[int]]:
        """輪郭の包含関係と深さを求める。"""
        contour_count = len(contours)
        areas = [abs(MeshPipeline.polygon_signed_area(contour)) for contour in contours]
        parents = [-1] * contour_count

        def probes(contour: np.ndarray) -> list[np.ndarray]:
            """包含判定に使う代表サンプル点群を作る。"""
            out = [np.mean(contour, axis=0)]
            count = len(contour)
            for i in range(count):
                current = contour[i]
                nxt = contour[(i + 1) % count]
                out.append(current)
                out.append((current + nxt) * 0.5)
            return out

        for i, contour in enumerate(contours):
            candidates = probes(contour)
            containers: list[int] = []
            for j, other in enumerate(contours):
                if i == j:
                    continue
                if areas[j] <= areas[i] + 1e-12:
                    continue
                if any(MeshPipeline.point_in_polygon(p, other) for p in candidates):
                    containers.append(j)
            if containers:
                parents[i] = min(containers, key=lambda idx: areas[idx])

        depths = [0] * contour_count
        for i in range(contour_count):
            depth = 0
            current = parents[i]
            safety = 0
            while current != -1 and safety < contour_count:
                depth += 1
                current = parents[current]
                safety += 1
            depths[i] = depth

        return parents, depths

    @staticmethod
    def find_polygon_interior_point(polygon: np.ndarray) -> np.ndarray | None:
        """穴指定に使える多角形内部点を探索する。"""
        if len(polygon) < 3:
            return None

        candidates = [np.mean(polygon, axis=0)]
        min_x = float(np.min(polygon[:, 0]))
        max_x = float(np.max(polygon[:, 0]))
        min_y = float(np.min(polygon[:, 1]))
        max_y = float(np.max(polygon[:, 1]))
        candidates.append(np.array([(min_x + max_x) * 0.5, (min_y + max_y) * 0.5]))

        count = len(polygon)
        for idx in range(count):
            p_prev = polygon[(idx - 1) % count]
            p_curr = polygon[idx]
            p_next = polygon[(idx + 1) % count]
            candidates.append((p_prev + p_curr + p_next) / 3.0)
            candidates.append((p_curr + p_next) * 0.5)

        for tx in (0.2, 0.35, 0.5, 0.65, 0.8):
            for ty in (0.2, 0.35, 0.5, 0.65, 0.8):
                candidates.append(
                    np.array(
                        [
                            min_x * (1.0 - tx) + max_x * tx,
                            min_y * (1.0 - ty) + max_y * ty,
                        ],
                        dtype=np.float64,
                    )
                )

        for candidate in candidates:
            if MeshPipeline.point_in_polygon(candidate, polygon):
                return candidate
        return None

    @staticmethod
    def normalize_contours_for_triangulation(
        contours: list[np.ndarray],
    ) -> list[np.ndarray]:
        """三角形分割前に輪郭を正規化して重なりを解消する。"""
        valid_contours: list[np.ndarray] = []
        for contour in contours:
            normalized = MeshPipeline.dedupe_contour_points(contour)
            if (
                len(normalized) >= 3
                and abs(MeshPipeline.polygon_signed_area(normalized)) > 1e-9
            ):
                valid_contours.append(normalized)
        if not valid_contours:
            return []

        # 重なり輪郭を含むパスはそのままだと穴判定を誤る場合があるため、
        # 先にブーリアン簡約して単純輪郭へ正規化してから分割する。
        simplified_path = MeshPipeline.contours_to_pathops_path(valid_contours)
        if simplified_path is not None:
            simplified_path.simplify()
            simplified_contours = MeshPipeline.pathops_path_to_contours(simplified_path)
            if simplified_contours:
                return simplified_contours
        return valid_contours

    @staticmethod
    def build_triangle_adjacency_order(
        tri_vertices: np.ndarray, tri_indices: np.ndarray
    ) -> list[int]:
        """共有辺の隣接を優先し、局所性の高い三角形走査順を返す。"""
        triangle_count = len(tri_indices)
        if triangle_count <= 1:
            return list(range(triangle_count))

        tri_vertices = np.asarray(tri_vertices, dtype=np.float64)
        tri_indices = np.asarray(tri_indices, dtype=np.int64)
        centroids = np.mean(tri_vertices[tri_indices], axis=1)

        adjacency: list[set[int]] = [set() for _ in range(triangle_count)]
        edge_to_triangles: dict[tuple[int, int], list[int]] = {}

        # 辺を (min_vertex, max_vertex) で正規化し、向きに依存せず共有辺を検出する。
        for local_index, tri_index in enumerate(tri_indices):
            edges = (
                (int(tri_index[0]), int(tri_index[1])),
                (int(tri_index[1]), int(tri_index[2])),
                (int(tri_index[2]), int(tri_index[0])),
            )
            for u, v in edges:
                if u == v:
                    continue
                if u > v:
                    u, v = v, u
                edge_to_triangles.setdefault((u, v), []).append(local_index)

        # 同じ辺キーを持つ三角形同士を隣接として接続する。
        for triangle_ids in edge_to_triangles.values():
            if len(triangle_ids) < 2:
                continue
            for pos in range(len(triangle_ids) - 1):
                left = triangle_ids[pos]
                for right in triangle_ids[pos + 1 :]:
                    adjacency[left].add(right)
                    adjacency[right].add(left)

        remaining = set(range(triangle_count))
        ordered_indices: list[int] = []
        last_index: int | None = None

        while remaining:
            # 成分の開始点: 初回は左下寄り、以降は直前三角形に最も近い未訪問を選ぶ。
            if last_index is None:
                start = min(
                    remaining,
                    key=lambda idx: (
                        float(centroids[idx, 0]),
                        float(centroids[idx, 1]),
                        idx,
                    ),
                )
            else:
                base = centroids[last_index]
                start = min(
                    remaining,
                    key=lambda idx: (
                        float((centroids[idx, 0] - base[0]) ** 2)
                        + float((centroids[idx, 1] - base[1]) ** 2),
                        float(centroids[idx, 0]),
                        float(centroids[idx, 1]),
                        idx,
                    ),
                )

            stack = [start]
            while stack:
                current = stack.pop()
                if current not in remaining:
                    continue
                remaining.remove(current)
                ordered_indices.append(current)
                last_index = current

                current_center = centroids[current]
                # 近い隣接を先に訪れるため、逆順pushして pop 時に近い順となるようにする。
                neighbors = [
                    neighbor for neighbor in adjacency[current] if neighbor in remaining
                ]
                neighbors.sort(
                    key=lambda idx: (
                        float((centroids[idx, 0] - current_center[0]) ** 2)
                        + float((centroids[idx, 1] - current_center[1]) ** 2),
                        float(centroids[idx, 0]),
                        float(centroids[idx, 1]),
                        idx,
                    ),
                    reverse=True,
                )
                stack.extend(neighbors)

        return ordered_indices

    @staticmethod
    def triangulate_contours(contours: list[np.ndarray]) -> list[np.ndarray]:
        """輪郭群を三角形分割して有効三角形リストを返す。"""
        valid_contours = MeshPipeline.normalize_contours_for_triangulation(contours)
        if not valid_contours:
            return []

        parents, depths = MeshPipeline.build_contour_hierarchy(valid_contours)
        triangles: list[np.ndarray] = []

        for outer_idx, depth in enumerate(depths):
            if depth % 2 != 0:
                continue

            hole_indices = [
                idx
                for idx, parent_idx in enumerate(parents)
                if parent_idx == outer_idx and depths[idx] == depth + 1
            ]
            outer_ring = valid_contours[outer_idx]
            hole_rings = [valid_contours[idx] for idx in hole_indices]

            vertices: list[list[float]] = []
            segments: list[list[int]] = []
            holes: list[list[float]] = []

            def add_ring_segments(ring: np.ndarray) -> None:
                """輪郭リングを頂点列と閉路セグメント列に追加する。"""
                start = len(vertices)
                count = len(ring)
                for point in ring:
                    vertices.append([float(point[0]), float(point[1])])
                for idx in range(count):
                    next_idx = (idx + 1) % count
                    segments.append([start + idx, start + next_idx])

            add_ring_segments(outer_ring)
            for hole_ring in hole_rings:
                add_ring_segments(hole_ring)
                hole_point = MeshPipeline.find_polygon_interior_point(hole_ring)
                if hole_point is not None:
                    holes.append([float(hole_point[0]), float(hole_point[1])])

            if len(vertices) < 3 or len(segments) < 3:
                continue

            tri_vertices_input = np.asarray(vertices, dtype=np.float64)
            tri_segments_input = np.asarray(segments, dtype=np.int32)
            tri_holes_input = (
                np.asarray(holes, dtype=np.float64)
                if holes
                else np.empty((0, 2), dtype=np.float64)
            )

            try:
                tri_vertices, tri_indices, _, _ = wildmeshing_lib.triangulate_data(
                    V=tri_vertices_input,
                    E=tri_segments_input,
                    feature_info=None,
                    stop_quality=MeshConfig.TRIWILD_STOP_QUALITY,
                    max_its=MeshConfig.TRIWILD_MAX_ITS,
                    stage=MeshConfig.TRIWILD_STAGE,
                    epsilon=MeshConfig.TRIWILD_EPSILON,
                    feature_epsilon=MeshConfig.TRIWILD_FEATURE_EPSILON,
                    target_edge_len=MeshConfig.TRIWILD_TARGET_EDGE_LEN,
                    edge_length_r=MeshConfig.TRIWILD_EDGE_LENGTH_R,
                    flat_feature_angle=MeshConfig.TRIWILD_FLAT_FEATURE_ANGLE,
                    cut_outside=MeshConfig.TRIWILD_CUT_OUTSIDE,
                    skip_eps=MeshConfig.TRIWILD_SKIP_EPS,
                    hole_pts=tri_holes_input,
                    mute_log=MeshConfig.TRIWILD_MUTE_LOG,
                )
            except (ValueError, RuntimeError, FloatingPointError):
                continue

            tri_indices = np.asarray(tri_indices, dtype=np.int64)
            tri_vertices = np.asarray(tri_vertices, dtype=np.float64)
            if tri_indices.ndim != 2 or tri_indices.shape[1] != 3:
                continue
            if tri_vertices.ndim != 2 or tri_vertices.shape[1] != 2:
                continue
            if len(tri_indices) == 0 or len(tri_vertices) == 0:
                continue
            if np.any(tri_indices < 0) or np.any(tri_indices >= len(tri_vertices)):
                continue

            triangle_order = MeshPipeline.build_triangle_adjacency_order(
                tri_vertices, tri_indices
            )
            for tri_position in triangle_order:
                tri_index = tri_indices[tri_position]
                triangle = np.asarray(
                    [
                        tri_vertices[tri_index[0]],
                        tri_vertices[tri_index[1]],
                        tri_vertices[tri_index[2]],
                    ],
                    dtype=np.float64,
                )
                area = MeshPipeline.polygon_signed_area(triangle)
                if abs(area) <= 1e-10:
                    continue
                if area < 0:
                    triangle = triangle[[0, 2, 1]]
                triangles.append(triangle)

        return triangles

    @staticmethod
    def create_sheared_triangle(
        plane_template: dict[str, Any],
        triangle_template: dict[str, Any],
        target_triangle: np.ndarray,
        color: dict[str, float],
        solver: TriangleSolverOptimized,
        child_y_scale: float = 0.01,
        y_offset: float = 0.0,
        reconstruction_max_abs_tol: float = MeshConfig.RECONSTRUCTION_MAX_ABS_TOL,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """目標三角形に一致する親子プレーンオブジェクトを生成する。"""
        solved = solver.solve(target_triangle)
        residual = solved.get("residual", float("inf"))
        if not np.isfinite(float(residual)):
            solved["rejected_reason"] = "solve_non_finite"
            return None, solved
        if not bool(solved.get("reachable", False)):
            solved["rejected_reason"] = "solve_not_converged"
            return None, solved

        reconstruction = solver.reconstruction_error(target_triangle, solved)  # type: ignore[arg-type]
        solved["reconstruction_max_abs"] = reconstruction["max_abs"]
        solved["reconstruction_rmse"] = reconstruction["rmse"]
        if reconstruction["max_abs"] > reconstruction_max_abs_tol:
            solved["rejected_reason"] = "reconstruction_error"
            return None, solved

        parent = create_plane(
            plane_template,
            x=float(solved["px"]),
            y=y_offset,
            z=float(solved["pz"]),
            color=color,
            scale=1.0,
        )
        parent["data"]["rotation"]["x"] = 0.0
        parent["data"]["rotation"]["y"] = float(solved["alpha"])
        parent["data"]["rotation"]["z"] = 0.0
        parent["data"]["scale"]["x"] = float(solved["sx"])
        parent["data"]["scale"]["y"] = 1.0
        parent["data"]["scale"]["z"] = float(solved["sz"])
        parent["data"]["colors"][0]["a"] = 0.0
        parent["data"]["line_color"]["a"] = 0.0
        parent["data"]["line_width"] = 0.0

        child = copy.deepcopy(triangle_template)
        child["data"]["position"]["x"] = 0.0
        child["data"]["position"]["y"] = 0.0
        child["data"]["position"]["z"] = 0.0
        child["data"]["rotation"]["x"] = 0.0
        child["data"]["rotation"]["y"] = float(solved["theta"])
        child["data"]["rotation"]["z"] = 0.0
        child["data"]["scale"]["x"] = float(solved.get("cx", solved["cs"]))
        child["data"]["scale"]["y"] = child_y_scale
        child["data"]["scale"]["z"] = float(solved.get("cz", solved["cs"]))
        child_color = copy.deepcopy(color)
        child_color["a"] = 1.0
        child["data"]["alpha"] = 1.0
        child["data"]["colors"][0] = child_color
        child["data"]["line_color"]["a"] = 1.0
        child["data"]["line_width"] = 0.0
        child["data"]["child"] = []

        parent["data"]["child"] = [child]
        return parent, solved

    @staticmethod
    def build_mesh_char_folders(
        labels: list[str],
        char_mesh_data: list[dict[str, Any]],
        plane_template: dict[str, Any],
        triangle_template: dict[str, Any],
        folder_obj: dict[str, Any],
        colors: list[dict[str, float]],
        reconstruction_max_abs_tol: float = MeshConfig.RECONSTRUCTION_MAX_ABS_TOL,
        y_offset: float = 0.0,
        y_offsets: list[float] | None = None,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, float], list[dict[str, Any]]]:
        """文字単位でメッシュ三角形フォルダと統計情報を構築する。"""
        solver = TriangleSolverOptimized(MeshConfig.SOURCE_TRIANGLE)
        char_folders: list[dict[str, Any]] = []
        triangle_count = 0
        raw_triangle_count = 0
        solve_failed_count = 0
        reconstruction_failed_count = 0
        accepted_max_abs_errors: list[float] = []
        accepted_rmse_errors: list[float] = []
        triangle_status_records: list[dict[str, Any]] = []

        triangles_per_char: list[list[np.ndarray]] = []
        for idx, _ in enumerate(labels):
            contours = char_mesh_data[idx]["contours"]
            triangles = MeshPipeline.triangulate_contours(contours)
            triangles_per_char.append(triangles)
            raw_triangle_count += len(triangles)

        for idx, label in enumerate(labels):
            char_data = char_mesh_data[idx]
            triangles = triangles_per_char[idx]
            triangle_objects: list[dict[str, Any]] = []
            folder_x = float(char_data["folder_x"])
            current_folder_y_offset = (
                float(y_offsets[idx])
                if y_offsets is not None and idx < len(y_offsets)
                else 0.0
            )
            current_triangle_y_offset = (
                0.0 if y_offsets is not None else float(y_offset)
            )
            for triangle in triangles:
                triangle_object, solved = MeshPipeline.create_sheared_triangle(
                    plane_template,
                    triangle_template,
                    triangle,
                    colors[idx],
                    solver,
                    y_offset=current_triangle_y_offset,
                    reconstruction_max_abs_tol=reconstruction_max_abs_tol,
                )
                shifted_triangle = triangle.copy()
                shifted_triangle[:, 0] += folder_x
                if triangle_object is None:
                    rejected_reason = solved.get(
                        "rejected_reason", "solve_not_converged"
                    )
                    if rejected_reason == "reconstruction_error":
                        reconstruction_failed_count += 1
                        triangle_status_records.append(
                            {
                                "triangle": shifted_triangle,
                                "status": "reconstruction_failed",
                                "char_index": idx,
                                "folder_x": folder_x,
                            }
                        )
                    else:
                        solve_failed_count += 1
                        triangle_status_records.append(
                            {
                                "triangle": shifted_triangle,
                                "status": "solve_failed",
                                "char_index": idx,
                                "folder_x": folder_x,
                            }
                        )
                    continue

                accepted_max_abs_errors.append(
                    float(solved.get("reconstruction_max_abs", 0.0))
                )
                accepted_rmse_errors.append(
                    float(solved.get("reconstruction_rmse", 0.0))
                )
                triangle_status_records.append(
                    {
                        "triangle": shifted_triangle,
                        "status": "accepted",
                        "char_index": idx,
                        "folder_x": folder_x,
                    }
                )
                triangle_objects.append(triangle_object)

            triangle_count += len(triangle_objects)
            char_folder = copy.deepcopy(folder_obj)
            char_folder["data"]["name"] = f"Shape_{idx + 1}_{label}"
            char_folder["data"]["position"]["x"] = folder_x
            char_folder["data"]["position"]["y"] = current_folder_y_offset
            char_folder["data"]["child"] = triangle_objects
            char_folder["data"]["treeState"] = 1
            char_folders.append(char_folder)

        mesh_stats = {
            "solve_failed_count": float(solve_failed_count),
            "reconstruction_failed_count": float(reconstruction_failed_count),
            "reconstruction_tol": float(reconstruction_max_abs_tol),
            "accepted_max_abs_error": float(max(accepted_max_abs_errors))
            if accepted_max_abs_errors
            else 0.0,
            "accepted_rmse": float(np.mean(accepted_rmse_errors))
            if accepted_rmse_errors
            else 0.0,
        }
        return (
            char_folders,
            triangle_count,
            raw_triangle_count,
            mesh_stats,
            triangle_status_records,
        )

    @staticmethod
    def build_mesh_triangulation_preview(
        char_mesh_data: list[dict[str, Any]],
        triangle_status_records: list[dict[str, Any]],
        width: int = 900,
        height: int = 360,
        padding: int = 24,
    ) -> Image.Image | None:
        """輪郭と三角形ステータスのプレビュー画像を生成する。"""
        global_contours: list[np.ndarray] = []
        global_triangles = triangle_status_records or []

        for char_data in char_mesh_data:
            folder_x = float(char_data["folder_x"])
            for contour in char_data["contours"]:
                shifted = contour.copy()
                shifted[:, 0] += folder_x
                global_contours.append(shifted)

        if not global_contours and not global_triangles:
            return None

        points: list[np.ndarray] = []
        points.extend(global_contours)
        for record in global_triangles:
            points.append(record["triangle"])
        all_points = np.vstack(points)

        min_x = float(np.min(all_points[:, 0]))
        max_x = float(np.max(all_points[:, 0]))
        min_y = float(np.min(all_points[:, 1]))
        max_y = float(np.max(all_points[:, 1]))
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)

        legend_gap = 12
        legend_panel_width = 240
        plot_left = padding
        plot_top = padding
        plot_right = max(
            plot_left + 1, width - padding - legend_panel_width - legend_gap
        )
        plot_bottom = height - padding
        plot_width = max(1.0, float(plot_right - plot_left))
        plot_height = max(1.0, float(plot_bottom - plot_top))

        scale = min(plot_width / span_x, plot_height / span_y)
        scaled_width = span_x * scale
        scaled_height = span_y * scale
        plot_offset_x = plot_left + (plot_width - scaled_width) * 0.5
        plot_offset_y = plot_top + (plot_height - scaled_height) * 0.5

        def project(point: np.ndarray) -> tuple[float, float]:
            """ワールド座標をプレビュー画像座標へ射影する。"""
            x = plot_offset_x + (point[0] - min_x) * scale
            y = plot_offset_y + (max_y - point[1]) * scale
            return float(x), float(y)

        image = Image.new("RGBA", (width, height), (18, 20, 24, 255))
        draw = ImageDraw.Draw(image, "RGBA")

        status_style: dict[str, dict[str, Any]] = {
            "accepted": {
                "priority": 0,
                "fill": (64, 180, 255, 35),
                "outline": (120, 220, 255, 180),
            },
            "reconstruction_failed": {
                "priority": 1,
                "fill": (255, 174, 66, 70),
                "outline": (255, 196, 122, 220),
            },
            "solve_failed": {
                "priority": 2,
                "fill": (255, 87, 127, 75),
                "outline": (255, 130, 164, 230),
            },
        }

        sorted_records = sorted(
            global_triangles,
            key=lambda record: status_style.get(
                record["status"], status_style["accepted"]
            )["priority"],
        )
        for record in sorted_records:
            style = status_style.get(record["status"], status_style["accepted"])
            projected = [project(vertex) for vertex in record["triangle"]]
            draw.polygon(projected, fill=style["fill"], outline=style["outline"])

        for contour in global_contours:
            projected = [project(vertex) for vertex in contour]
            if len(projected) >= 2:
                draw.line(
                    projected + [projected[0]], fill=(220, 220, 220, 220), width=1
                )

        legend_x = int(plot_right + legend_gap)
        legend_y = padding
        legend_w = max(120, width - legend_x - padding)
        legend_h = 64
        draw.rectangle(
            [(legend_x, legend_y), (legend_x + legend_w, legend_y + legend_h)],
            fill=(10, 10, 10, 180),
            outline=(180, 180, 180, 180),
        )
        legend_items = [
            ("solver not converged", status_style["solve_failed"]["outline"]),
            ("reconstruction failed", status_style["reconstruction_failed"]["outline"]),
            ("accepted", status_style["accepted"]["outline"]),
        ]
        for idx, (label, color) in enumerate(legend_items):
            top = legend_y + 8 + idx * 18
            draw.rectangle(
                [(legend_x + 8, top), (legend_x + 22, top + 12)],
                fill=color,
                outline=(230, 230, 230, 230),
            )
            draw.text((legend_x + 28, top - 1), label, fill=(235, 235, 235, 240))

        return image

    @staticmethod
    def contours_to_pathops_path(contours: list[np.ndarray]) -> Any | None:
        """輪郭配列を PathOps の閉路パスへ変換する。"""
        path = pathops.Path()
        has_contour = False
        for contour in contours:
            normalized = MeshPipeline.dedupe_contour_points(
                np.asarray(contour, dtype=np.float64)
            )
            if (
                len(normalized) < 3
                or abs(MeshPipeline.polygon_signed_area(normalized)) <= 1e-9
            ):
                continue
            first_point = normalized[0]
            path.moveTo(float(first_point[0]), float(first_point[1]))
            for point in normalized[1:]:
                path.lineTo(float(point[0]), float(point[1]))
            path.close()
            has_contour = True
        return path if has_contour else None

    @staticmethod
    def pathops_path_to_contours(path: Any) -> list[np.ndarray]:
        """PathOps パスを有効な輪郭配列へ戻す。"""
        if path is None:
            return []
        converted: list[np.ndarray] = []
        for contour in path.contours:
            points = np.asarray(list(contour.points), dtype=np.float64)
            normalized = MeshPipeline.dedupe_contour_points(points)
            if (
                len(normalized) >= 3
                and abs(MeshPipeline.polygon_signed_area(normalized)) > 1e-9
            ):
                converted.append(normalized)
        return converted

    @staticmethod
    def render_generation_feedback(mesh_stats: dict[str, Any], lang: str) -> None:
        """生成時の失敗警告と誤差サマリを表示する。"""
        if int(mesh_stats.get("solve_failed_count", 0)) > 0:
            st.warning(
                get_text("warn_solver", lang).format(
                    count=int(mesh_stats["solve_failed_count"])
                )
            )
        if int(mesh_stats.get("reconstruction_failed_count", 0)) > 0:
            st.warning(
                get_text("warn_reconstruction", lang).format(
                    count=int(mesh_stats["reconstruction_failed_count"])
                )
            )
        st.caption(
            get_text("reconstruction_info", lang).format(
                max_err=mesh_stats["accepted_max_abs_error"],
                rmse=mesh_stats["accepted_rmse"],
                tol=mesh_stats["reconstruction_tol"],
            )
        )

    @staticmethod
    def render_triangulation_section(
        triangulation_preview: Image.Image | None, lang: str
    ) -> None:
        """三角形分割プレビューの表示セクションを描画する。"""
        st.subheader(get_text("triangulation_title", lang))
        if triangulation_preview is None:
            st.caption(get_text("triangulation_empty", lang))
        else:
            st.image(triangulation_preview, width="stretch")


def point_to_np(point: Any) -> np.ndarray:
    """svgelements の点オブジェクトを NumPy 座標へ変換する。"""
    return np.array([float(point.x), float(point.y)], dtype=np.float64)


def parse_svg_float(value: Any, default: float) -> float:
    """SVG属性値を安全に float へ変換する。"""
    if value is None:
        return float(default)
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return float(default)
            if text.endswith("%"):
                parsed = float(text[:-1]) / 100.0
            else:
                parsed = float(text)
        else:
            parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not np.isfinite(parsed):
        return float(default)
    return float(parsed)


def is_visible_svg_paint(paint: Any, effective_opacity: float) -> bool:
    """paint が none/透明でない場合に True を返す。"""
    if effective_opacity <= 1e-9 or paint is None:
        return False
    paint_value = getattr(paint, "value", None)
    if paint_value is None:
        return False
    paint_text = str(paint).strip().lower()
    if paint_text in ("", "none", "transparent"):
        return False
    paint_alpha = getattr(paint, "alpha", None)
    if paint_alpha is None:
        return True
    try:
        return float(paint_alpha) > 0.0
    except (TypeError, ValueError):
        return True


def resolve_svg_fill_enabled(element: Any) -> bool:
    """SVG要素が可視 fill を持つかを判定する。"""
    values = getattr(element, "values", {}) or {}
    fill = getattr(element, "fill", None)
    global_opacity = parse_svg_float(values.get("opacity"), 1.0)
    fill_opacity = parse_svg_float(values.get("fill-opacity"), 1.0)
    effective_opacity = float(np.clip(global_opacity * fill_opacity, 0.0, 1.0))
    return is_visible_svg_paint(fill, effective_opacity)


def resolve_svg_stroke_style(
    element: Any,
) -> tuple[float, Any, Any, float] | None:
    """SVG要素の stroke スタイルを PathOps 用に解決する。"""
    values = getattr(element, "values", {}) or {}
    stroke = getattr(element, "stroke", None)
    global_opacity = parse_svg_float(values.get("opacity"), 1.0)
    stroke_opacity = parse_svg_float(values.get("stroke-opacity"), 1.0)
    effective_opacity = float(np.clip(global_opacity * stroke_opacity, 0.0, 1.0))
    if not is_visible_svg_paint(stroke, effective_opacity):
        return None

    stroke_width = parse_svg_float(
        getattr(element, "stroke_width", values.get("stroke-width")), 0.0
    )
    if stroke_width <= 1e-9:
        return None

    linecap_text = str(values.get("stroke-linecap") or "butt").strip().lower()
    linejoin_text = str(values.get("stroke-linejoin") or "miter").strip().lower()
    miter_limit = parse_svg_float(values.get("stroke-miterlimit"), 4.0)
    if miter_limit < 1.0:
        miter_limit = 1.0

    linecap = {
        "round": pathops.LineCap.ROUND_CAP,
        "square": pathops.LineCap.SQUARE_CAP,
    }.get(linecap_text, pathops.LineCap.BUTT_CAP)
    linejoin = {
        "round": pathops.LineJoin.ROUND_JOIN,
        "bevel": pathops.LineJoin.BEVEL_JOIN,
    }.get(linejoin_text, pathops.LineJoin.MITER_JOIN)
    return float(stroke_width), linecap, linejoin, float(miter_limit)


def extract_svg_element_color(
    element: Any, is_stroke: bool = False
) -> dict[str, float] | None:
    """SVG要素のfill/stroke色を rgba dict で返す。取得できなければ None。"""
    paint = getattr(element, "stroke" if is_stroke else "fill", None)
    if paint is None:
        return None
    try:
        r = getattr(paint, "red", None)
        g = getattr(paint, "green", None)
        b = getattr(paint, "blue", None)
        if r is not None and g is not None and b is not None:
            return {
                "r": float(r) / 255.0,
                "g": float(g) / 255.0,
                "b": float(b) / 255.0,
                "a": 1.0,
            }
        color_str = str(paint).strip()
        if color_str.startswith("#"):
            return hex_to_color(color_str)
    except Exception:
        pass
    return None


SVG_CURVE_SEGMENT_TYPES = (Arc, CubicBezier, QuadraticBezier)


def segment_point_to_np(segment: Any, t: float) -> np.ndarray:
    """セグメント上のパラメータ t を NumPy 座標へ変換する。"""
    return point_to_np(segment.point(float(t)))


def should_split_svg_curve(
    segment: Any,
    start_t: float,
    end_t: float,
    start_point: np.ndarray,
    end_point: np.ndarray,
    error: float,
    depth: int,
) -> bool:
    """wildmeshing の曲線サンプリングと同じ弦長誤差で分割可否を判定する。"""
    if depth < MeshConfig.SVG_CURVE_SAMPLE_MIN_DEPTH:
        return True
    if depth >= MeshConfig.SVG_CURVE_SAMPLE_MAX_DEPTH:
        return False

    chord_length = float(np.linalg.norm(end_point - start_point))
    mid_t = 0.5 * (start_t + end_t)
    mid_point = segment_point_to_np(segment, mid_t)
    split_length = float(
        np.linalg.norm(mid_point - start_point) + np.linalg.norm(end_point - mid_point)
    )
    return abs(split_length - chord_length) > error


def sample_curve_segment_points(segment: Any, error: float) -> list[np.ndarray]:
    """曲線セグメントを誤差ベースで再帰分割して終点を含む点列にする。"""
    points: list[np.ndarray] = []

    def recurse(
        start_t: float,
        end_t: float,
        start_point: np.ndarray,
        end_point: np.ndarray,
        depth: int,
    ) -> None:
        if should_split_svg_curve(
            segment=segment,
            start_t=start_t,
            end_t=end_t,
            start_point=start_point,
            end_point=end_point,
            error=error,
            depth=depth,
        ):
            mid_t = 0.5 * (start_t + end_t)
            mid_point = segment_point_to_np(segment, mid_t)
            recurse(start_t, mid_t, start_point, mid_point, depth + 1)
            recurse(mid_t, end_t, mid_point, end_point, depth + 1)
            return
        points.append(end_point)

    start_point = segment_point_to_np(segment, 0.0)
    end_point = segment_point_to_np(segment, 1.0)
    recurse(0.0, 1.0, start_point, end_point, 0)
    return points


def sample_segment_points(segment: Any) -> list[np.ndarray]:
    """セグメントをポリライン化して、始点を除くサンプル点列を返す。"""
    if isinstance(segment, SVG_CURVE_SEGMENT_TYPES):
        return sample_curve_segment_points(
            segment,
            error=MeshConfig.SVG_CURVE_SAMPLE_ERROR,
        )
    return [segment_point_to_np(segment, 1.0)]


def path_to_contours(
    path_obj: SVGPath, auto_close_open_paths: bool
) -> list[np.ndarray]:
    """1つの SVG パスを有効な輪郭列へ変換する。"""
    contours: list[np.ndarray] = []
    current_points: list[np.ndarray] = []
    has_draw_segment = False
    current_closed = False

    def flush_contour() -> None:
        """現在のサブパスを検証して輪郭として確定する。"""
        nonlocal current_points, has_draw_segment, current_closed
        if not current_points or not has_draw_segment:
            current_points = []
            has_draw_segment = False
            current_closed = False
            return

        contour = np.asarray(current_points, dtype=np.float64)
        if current_closed or auto_close_open_paths:
            if len(contour) >= 2 and np.linalg.norm(contour[0] - contour[-1]) > 1e-9:
                contour = np.vstack([contour, contour[0]])

        if len(contour) > 1 and np.allclose(contour[0], contour[-1]):
            contour = contour[:-1]
        contour = MeshPipeline.dedupe_contour_points(contour)

        if len(contour) >= 3 and abs(MeshPipeline.polygon_signed_area(contour)) > 1e-9:
            contours.append(contour)

        current_points = []
        has_draw_segment = False
        current_closed = False

    for segment in path_obj:
        if isinstance(segment, Move):
            flush_contour()
            current_points = [point_to_np(segment.end)]
            continue

        if not current_points:
            start = getattr(segment, "start", None)
            if start is not None:
                current_points = [point_to_np(start)]
            else:
                end = getattr(segment, "end", None)
                if end is not None:
                    current_points = [point_to_np(end)]

        sampled = sample_segment_points(segment)
        if sampled:
            current_points.extend(sampled)
            has_draw_segment = True
        if isinstance(segment, Close):
            current_closed = True

    flush_contour()
    return contours


def svg_path_to_pathops_path(path_obj: SVGPath) -> Any | None:
    """SVGパスをPathOpsの開閉サブパスに変換する。"""
    path = pathops.Path()
    has_path = False
    current_points: list[np.ndarray] = []
    has_draw_segment = False
    current_closed = False

    def flush_subpath() -> None:
        """現在のサブパスをPathOpsへ追加する。"""
        nonlocal current_points, has_draw_segment, current_closed, has_path
        if not current_points or not has_draw_segment:
            current_points = []
            has_draw_segment = False
            current_closed = False
            return

        points = MeshPipeline.dedupe_contour_points(
            np.asarray(current_points, dtype=np.float64)
        )
        if len(points) < 2:
            current_points = []
            has_draw_segment = False
            current_closed = False
            return

        path.moveTo(float(points[0, 0]), float(points[0, 1]))
        for point in points[1:]:
            path.lineTo(float(point[0]), float(point[1]))
        if current_closed:
            path.close()
        has_path = True

        current_points = []
        has_draw_segment = False
        current_closed = False

    for segment in path_obj:
        if isinstance(segment, Move):
            flush_subpath()
            current_points = [point_to_np(segment.end)]
            continue

        if not current_points:
            start = getattr(segment, "start", None)
            if start is not None:
                current_points = [point_to_np(start)]
            else:
                end = getattr(segment, "end", None)
                if end is not None:
                    current_points = [point_to_np(end)]

        sampled = sample_segment_points(segment)
        if sampled:
            current_points.extend(sampled)
            has_draw_segment = True
        if isinstance(segment, Close):
            current_closed = True

    flush_subpath()
    return path if has_path else None


def stroke_path_to_contours(
    path_obj: SVGPath,
    stroke_width: float,
    linecap: Any,
    linejoin: Any,
    miter_limit: float,
) -> list[np.ndarray]:
    """SVG stroke を輪郭化して有効輪郭列として返す。"""
    if stroke_width <= 1e-9:
        return []

    source_path = svg_path_to_pathops_path(path_obj)
    if source_path is None:
        return []

    try:
        stroked = pathops.Path()
        stroked.addPath(source_path)
        stroked.stroke(
            width=float(stroke_width),
            cap=linecap,
            join=linejoin,
            miter_limit=float(miter_limit),
        )
        try:
            stroked.simplify()
        except pathops.UnsupportedVerbError:
            # round cap/join で CONIC を含む場合は簡約不可なのでそのまま使う。
            pass
        return MeshPipeline.pathops_path_to_contours(stroked)
    except (
        ValueError,
        RuntimeError,
        FloatingPointError,
        pathops.UnsupportedVerbError,
    ):
        return []


def svg_bytes_to_contours(
    svg_bytes: bytes,
    auto_close_open_paths: bool,
) -> list[tuple[list[np.ndarray], dict[str, float] | None]]:
    """SVG バイト列から要素ごとの輪郭と色を抽出する。"""
    svg = SVG.parse(io.BytesIO(svg_bytes))
    groups: list[tuple[list[np.ndarray], dict[str, float] | None]] = []
    for element in svg.elements():
        try:
            path_obj = SVGPath(element)
        except Exception:
            continue
        if len(path_obj) == 0:
            continue
        if resolve_svg_fill_enabled(element):
            fill_contours = path_to_contours(
                path_obj=path_obj,
                auto_close_open_paths=auto_close_open_paths,
            )
            if fill_contours:
                groups.append(
                    (fill_contours, extract_svg_element_color(element, is_stroke=False))
                )
        stroke_style = resolve_svg_stroke_style(element)
        if stroke_style is not None:
            stroke_width, linecap, linejoin, miter_limit = stroke_style
            stroke_contours = stroke_path_to_contours(
                path_obj=path_obj,
                stroke_width=stroke_width,
                linecap=linecap,
                linejoin=linejoin,
                miter_limit=miter_limit,
            )
            if stroke_contours:
                groups.append(
                    (
                        stroke_contours,
                        extract_svg_element_color(element, is_stroke=True),
                    )
                )
    return groups


def build_svg_mesh_data(
    colored_groups: list[tuple[list[np.ndarray], dict[str, float] | None]],
    target_height: float,
) -> list[dict[str, Any]]:
    """要素ごとの輪郭と色を高さ基準で正規化したメッシュ入力へ変換する。"""
    all_contours = [c for group, _ in colored_groups for c in group]
    all_points = np.vstack(all_contours)
    min_x = float(np.min(all_points[:, 0]))
    max_x = float(np.max(all_points[:, 0]))
    min_y = float(np.min(all_points[:, 1]))
    max_y = float(np.max(all_points[:, 1]))

    height = max(1e-6, max_y - min_y)
    scale = float(target_height) / height
    center_x = 0.5 * (min_x + max_x)
    center_y = 0.5 * (min_y + max_y)

    def transform(contour: np.ndarray) -> np.ndarray:
        out = np.empty_like(contour)
        out[:, 0] = (contour[:, 0] - center_x) * scale
        out[:, 1] = -(contour[:, 1] - center_y) * scale
        return out

    return [
        {
            "char": "SVG",
            "folder_x": 0.0,
            "contours": [transform(c) for c in group],
            "svg_color": svg_color,
        }
        for group, svg_color in colored_groups
    ]


def rgba_dict_to_tuple(
    color: dict[str, float] | None, fallback: tuple[int, int, int, int]
) -> tuple[int, int, int, int]:
    """0-1 RGBA 辞書を Pillow 用 0-255 タプルへ変換する。"""
    if color is None:
        return fallback
    return (
        int(np.clip(float(color.get("r", 0.0)), 0.0, 1.0) * 255),
        int(np.clip(float(color.get("g", 0.0)), 0.0, 1.0) * 255),
        int(np.clip(float(color.get("b", 0.0)), 0.0, 1.0) * 255),
        int(np.clip(float(color.get("a", 1.0)), 0.0, 1.0) * 255),
    )


def build_source_preview(
    colored_groups: list[tuple[list[np.ndarray], dict[str, float] | None]],
    *,
    fallback_color: dict[str, float] | None = None,
    use_svg_color: bool = True,
    force_opaque_shapes: bool = False,
    width: int = 900,
    height: int = 360,
    padding: int = 24,
) -> Image.Image | None:
    """入力輪郭のプレビュー画像を生成する。"""
    if not colored_groups:
        return None

    contours = [c for group, _ in colored_groups for c in group]
    if not contours:
        return None

    all_points = np.vstack(contours)
    min_x = float(np.min(all_points[:, 0]))
    max_x = float(np.max(all_points[:, 0]))
    min_y = float(np.min(all_points[:, 1]))
    max_y = float(np.max(all_points[:, 1]))

    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)
    supersample = 3
    draw_width = width * supersample
    draw_height = height * supersample
    draw_padding = padding * supersample
    scale = min(
        (draw_width - 2 * draw_padding) / span_x,
        (draw_height - 2 * draw_padding) / span_y,
    )
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0

    origin_x = (draw_width - span_x * scale) * 0.5
    origin_y = (draw_height - span_y * scale) * 0.5

    def project(point: np.ndarray) -> tuple[float, float]:
        """輪郭座標をソースプレビュー画像座標へ変換する。"""
        x = origin_x + (point[0] - min_x) * scale
        y = origin_y + (point[1] - min_y) * scale
        return float(x), float(y)

    background = (246, 247, 248, 255)
    default_shape_fill = (51, 65, 85, 235)
    fallback_fill = rgba_dict_to_tuple(fallback_color, default_shape_fill)
    image = Image.new("RGBA", (draw_width, draw_height), background)
    draw = ImageDraw.Draw(image, "RGBA")

    for group_contours, svg_color in colored_groups:
        normalized_contours = [
            MeshPipeline.dedupe_contour_points(np.asarray(contour, dtype=np.float64))
            for contour in group_contours
        ]
        normalized_contours = [
            contour
            for contour in normalized_contours
            if len(contour) >= 3
            and abs(MeshPipeline.polygon_signed_area(contour)) > 1e-9
        ]
        if not normalized_contours:
            continue

        _, depths = MeshPipeline.build_contour_hierarchy(normalized_contours)
        draw_order = sorted(
            range(len(normalized_contours)),
            key=lambda idx: (
                depths[idx],
                -abs(MeshPipeline.polygon_signed_area(normalized_contours[idx])),
            ),
        )
        shape_fill = (
            rgba_dict_to_tuple(svg_color, fallback_fill)
            if use_svg_color
            else fallback_fill
        )
        if force_opaque_shapes:
            shape_fill = (*shape_fill[:3], 255)

        for contour_index in draw_order:
            contour = normalized_contours[contour_index]
            projected = [project(p) for p in contour]
            if len(projected) < 3:
                continue
            is_hole = depths[contour_index] % 2 == 1
            fill = background if is_hole else shape_fill
            draw.polygon(projected, fill=fill)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_opaque_image(
    image: Image.Image, background: tuple[int, int, int, int] = (246, 247, 248, 255)
) -> Image.Image:
    """RGBA画像を背景色に合成して不透明化する。"""
    rgba = image.convert("RGBA")
    base = Image.new("RGBA", rgba.size, background)
    return Image.alpha_composite(base, rgba).convert("RGB")


def build_svg_scene(
    *,
    template_scene: HoneycomeSceneData,
    plane_template: dict[str, Any],
    triangle_template: dict[str, Any],
    folder_key: int,
    folder_obj: dict[str, Any],
    use_svg_color: bool,
    fallback_color: dict[str, float],
    color_alpha: float,
    svg_mesh_data: list[dict[str, Any]],
    generation_metadata: dict[str, Any],
    scene_root_name: str,
    lang: str,
) -> tuple[HoneycomeSceneData, int, int, dict[str, Any], Image.Image | None]:
    """メッシュ生成結果とメタデータをまとめてシーンを構築する。"""
    n = len(svg_mesh_data)
    labels = [f"SVG_{i + 1}" for i in range(n)]
    y_offsets = [-(n - 1 - idx) * 0.001 for idx in range(n)]

    if use_svg_color:
        colors = []
        for entry in svg_mesh_data:
            c = entry.get("svg_color") or fallback_color
            c = dict(c)
            c["a"] = color_alpha
            colors.append(c)
    else:
        colors = [fallback_color] * n

    (
        char_folders,
        plane_count,
        raw_plane_count,
        mesh_stats,
        triangle_status_records,
    ) = MeshPipeline.build_mesh_char_folders(
        labels,
        svg_mesh_data,
        plane_template,
        triangle_template,
        folder_obj,
        colors,
        y_offsets=y_offsets,
    )

    scene_children: list[dict[str, Any]] = []
    scene_children.extend(char_folders)

    merged_mesh_stats = {
        "solve_failed_count": int(mesh_stats["solve_failed_count"]),
        "reconstruction_failed_count": int(mesh_stats["reconstruction_failed_count"]),
        "reconstruction_tol": float(mesh_stats["reconstruction_tol"]),
        "accepted_max_abs_error": float(mesh_stats["accepted_max_abs_error"]),
        "accepted_rmse": float(mesh_stats["accepted_rmse"]),
    }

    triangulation_preview = MeshPipeline.build_mesh_triangulation_preview(
        svg_mesh_data, triangle_status_records
    )

    scene = copy.deepcopy(template_scene)
    scene.title = scene_root_name
    new_folder = copy.deepcopy(folder_obj)
    new_folder["data"]["name"] = scene_root_name
    metadata_folder = build_metadata_folder(folder_obj, generation_metadata, lang)
    new_folder["data"]["child"] = [metadata_folder] + scene_children
    scene.objects = {folder_key: new_folder}

    return scene, plane_count, raw_plane_count, merged_mesh_stats, triangulation_preview


def sanitize_stem(name: str) -> str:
    """出力ファイル名に使える安全なステム文字列を作る。"""
    stem = Path(name).stem
    safe = "".join(ch if ch.isalnum() else "_" for ch in stem)
    return safe or "svg"


def main() -> None:
    """SVG ビルダーの Streamlit アプリ本体を実行する。"""
    st.set_page_config(
        page_title="Digital Craft SVG Builder / デジクラ SVG ビルダー",
        page_icon="🧩",
        layout="wide",
    )

    lang = st.session_state.get("lang", "ja")

    st.title(f"🧩 {get_text('title', lang)}")
    st.markdown(get_text("subtitle", lang))

    with st.expander(f"❓ {get_text('qa_title', lang)}", expanded=False):
        st.markdown(get_text("qa_content", lang).strip())

    uploaded_svg = st.file_uploader(get_text("upload_label", lang), type=["svg"])
    if uploaded_svg is None:
        st.info(get_text("upload_info", lang))
        st.stop()

    svg_bytes = uploaded_svg.getvalue()

    use_svg_color = st.checkbox(
        get_text("use_svg_color_label", lang),
        value=True,
        help=get_text("use_svg_color_help", lang),
    )
    if not use_svg_color:
        color_hex = st.color_picker(get_text("color_label", lang), value="#FFFFFF")
    else:
        color_hex = "#FFFFFF"
    color_alpha = st.slider(
        get_text("alpha_label", lang),
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
    )
    text_height = st.slider(
        get_text("height_label", lang),
        min_value=0.01,
        max_value=2.0,
        value=0.5,
        step=0.01,
    )
    with st.expander(get_text("text_size_example", lang), expanded=False):
        st.text(get_text("size_help", lang))
        st.markdown("![font size example](https://i.imgur.com/wbhZ8Gd.jpeg)")

    mesh_settings = MeshPipeline.default_advanced_settings()
    with st.expander(get_text("advanced_settings", lang), expanded=False):
        mesh_settings = MeshPipeline.render_advanced_settings(lang)
        plane_preset_key = st.selectbox(
            get_text("plane_preset_label", lang),
            options=["map", "character"],
            format_func=lambda key: get_text(f"plane_preset_{key}", lang),
            index=0,
        )
        light_cancel = st.slider(
            get_text("light_influence_label", lang),
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.05,
        )

    MeshPipeline.apply_curve_smoothness_settings(int(mesh_settings["curve_smoothness"]))

    try:
        source_contours = svg_bytes_to_contours(
            svg_bytes=svg_bytes,
            auto_close_open_paths=True,
        )
    except Exception as exc:
        st.error(get_text("parse_error", lang).format(error=exc))
        st.exception(exc)
        st.stop()

    flat_source_contours = [c for group, _ in source_contours for c in group]
    if not flat_source_contours:
        st.error(get_text("no_contours", lang))
        st.stop()

    preview_fallback_color = hex_to_color(color_hex)
    preview_fallback_color["a"] = color_alpha
    source_preview = build_source_preview(
        source_contours,
        fallback_color=preview_fallback_color,
        use_svg_color=use_svg_color,
    )
    if source_preview is not None:
        st.subheader(get_text("input_preview_title", lang))
        st.image(source_preview, width="stretch")

    if not st.button(
        get_text("generate_button", lang), type="primary", width="stretch"
    ):
        st.stop()

    template_scene, plane_template, folder_key, folder_obj = load_template()
    plane_settings = PLANE_PRESETS[plane_preset_key]
    triangle_settings = TRIANGLE_PRESETS[plane_preset_key]

    resolved_plane_template = {
        **plane_template,
        "data": {
            **plane_template["data"],
            "category": plane_settings["category"],
            "no": plane_settings["no"],
            "light_cancel": 1.0 - light_cancel,
        },
    }

    triangle_template = {
        **plane_template,
        "data": {
            **plane_template["data"],
            "category": triangle_settings["category"],
            "no": triangle_settings["no"],
            "light_cancel": 1.0 - light_cancel,
        },
    }

    MeshPipeline.apply_triwild_settings(
        edge_length_r=float(mesh_settings["edge_length_r"]),
    )

    color = hex_to_color(color_hex)
    color["a"] = color_alpha

    curve_labels = get_text("curve_smoothness_presets", lang)
    curve_smoothness_label = str(mesh_settings["curve_smoothness"])
    if isinstance(curve_labels, dict):
        curve_smoothness_label = (
            f"{mesh_settings['curve_smoothness']}: "
            f"{curve_labels.get(mesh_settings['curve_smoothness'], '')}"
        ).strip()

    generation_metadata = {
        get_text("meta_source", lang): uploaded_svg.name,
        get_text("meta_color", lang): color_hex,
        get_text("meta_alpha", lang): color_alpha,
        get_text("meta_height", lang): text_height,
        get_text("meta_plane_preset", lang): get_text(
            f"plane_preset_{plane_preset_key}", lang
        ),
        get_text("meta_light_influence", lang): light_cancel,
        get_text("meta_curve_smoothness", lang): curve_smoothness_label,
        get_text("meta_edge_length_r", lang): mesh_settings["edge_length_r"],
    }

    svg_mesh_data = build_svg_mesh_data(
        source_contours, target_height=text_height * SVG_SCENE_HEIGHT_FACTOR
    )
    scene_root_name = (
        f"{get_text('scene_root', lang)}: {sanitize_stem(uploaded_svg.name)}"
    )

    with st.spinner(get_text("generating", lang)):
        scene, plane_count, raw_plane_count, mesh_stats, triangulation_preview = (
            build_svg_scene(
                template_scene=template_scene,
                plane_template=resolved_plane_template,
                triangle_template=triangle_template,
                folder_key=folder_key,
                folder_obj=folder_obj,
                use_svg_color=use_svg_color,
                fallback_color=color,
                color_alpha=color_alpha,
                svg_mesh_data=svg_mesh_data,
                generation_metadata=generation_metadata,
                scene_root_name=scene_root_name,
                lang=lang,
            )
        )

    st.success(get_text("success_generate", lang).format(count=plane_count))
    MeshPipeline.render_generation_feedback(mesh_stats, lang)
    render_scene_info(
        plane_count=plane_count,
        raw_plane_count=raw_plane_count,
        mesh_stats=mesh_stats,
        lang=lang,
    )
    MeshPipeline.render_triangulation_section(triangulation_preview, lang)

    scene_image = build_source_preview(
        source_contours,
        fallback_color=color,
        use_svg_color=use_svg_color,
        force_opaque_shapes=True,
        width=1280,
        height=720,
        padding=64,
    )
    if scene_image is None:
        scene_image = (
            source_preview if source_preview is not None else triangulation_preview
        )
    if scene_image is None:
        scene_image = Image.new("RGBA", (1280, 720), (20, 20, 20, 255))

    preview_buf = io.BytesIO()
    make_opaque_image(scene_image).save(preview_buf, format="PNG")
    scene.image = preview_buf.getvalue()

    filename = f"digitalcraft_scene_svg_{sanitize_stem(uploaded_svg.name)}.png"
    st.download_button(
        label=get_text("download_button", lang),
        data=bytes(scene),
        file_name=filename,
        mime="image/png",
        type="primary",
        width="stretch",
    )


if __name__ == "__main__":
    main()
