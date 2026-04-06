import copy
import io
import math
import uuid
from pathlib import Path

import numpy as np
import pathops
import streamlit as st
import wildmeshing as wildmeshing_lib
from fontPens.flattenPen import FlattenPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from kkloader import HoneycomeSceneData
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import least_squares

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "デジクラカリグラファー",
        "subtitle": """テキストをデジタルクラフトのシーン内に置くことができます。     

- 文字を四角形の平面を並べて作る **ドットモード**
- 文字を滑らかな曲線として作る **メッシュモード**

の2つのモードがあります。""",
        "qa_title": "Q&A",
        "qa_content": """
#### 文字を入れると動作が重くなる！

ドットモードの状態で **アンチエイリアス** をOFFにし、 **横方向の平面結合** を有効にすると最も平面の数が小さくなります。

他にも **一文字あたり細かさ**を下げることで平面数が減りますが、文字の解像度が下がるので可読性も悪くなってしまいます。
どうしても平面数を下げたければこのパラメータを調整していい塩梅を探してみてください。

#### どの設定で文字を作ったか忘れた！

シーン内に生成された **「文字情報」フォルダ** の中に、使用したパラメータが保存されています。

#### 生成方式の"ドット"と"メッシュ"はどう違う？

ドットは平面を整列させることで文字を表現し、メッシュでは三角形ポリゴンを柔軟に敷き詰めて文字を表現します。

<div style="text-align: center; margin: 1.5em 0"><img src="https://imgur.com/FHjmBkb.png" width=50%><br><small>左がメッシュモード、右がドットモードです</small></div>

- ドットモードは処理が早く、生成後のアイテム数が少ないため動作が軽い一方、文字の縁がギザギザします。
- メッシュモードは処理に時間がかかりますが、文字の滑らかな輪郭をそのまま表現することができます。

シーン中に小さく表示できればよい程度ではドットモード、ロゴなど文字を大きくシンボリックに表現したい場合はメッシュモードがおすすめです。

#### どうやって曲線を作っている？

[こちらのリンク先](https://qiita.com/tropical-362827/items/6be88a910efa81f45791)に解説記事を書いてみました。ご興味あれば読んでみてください。

""",
        "metadata_folder": "文字情報",
        "meta_font": "フォント",
        "meta_color": "色",
        "meta_alpha": "透明度",
        "meta_text_height": "文字の高さ",
        "meta_resolution": "解像度",
        "meta_antialias": "アンチエイリアス",
        "meta_aa_color": "AA色",
        "meta_merge_horizontal": "横方向結合",
        "meta_plane_size": "平面サイズ",
        "meta_plane_type": "平面タイプ",
        "meta_light_influence": "ライト影響度",
        "meta_render_mode": "生成方式",
        "meta_mesh_flatten_length": "メッシュ線分長",
        "meta_mesh_stop_quality": "メッシュ stop_quality",
        "meta_mesh_edge_length_r": "メッシュ edge_length_r",
        "meta_mesh_target_edge_len": "メッシュ target_edge_len",
        "meta_mesh_outline_enabled": "メッシュ縁取り",
        "meta_mesh_outline_width": "メッシュ縁取り幅",
        "meta_mesh_outline_color": "メッシュ縁取り色",
        "param_settings": "パラメータ設定",
        "text_input": "テキスト",
        "text_placeholder": "ここにテキストを入力",
        "font_label": "フォント",
        "color_label": "色",
        "alpha_label": "色の透明度",
        "text_size_title": "文字の大きさ",
        "text_size_help": "文字の縦幅。0.1で一文字がキャラの手のひらほどの大きさ、0.4でキャラの頭ほどの大きさになります。",
        "text_size_example": "フォントサイズの例",
        "height_label": "縦幅",
        "advanced_settings": "詳細設定",
        "resolution_label": "一文字あたり細かさ",
        "resolution_help": "文字のピクセルの細かさ。この値を大きくするほど文字が綺麗になる一方、シーンが重くなります",
        "antialias_label": "アンチエイリアスを使う",
        "antialias_color_label": "アンチエイリアスの色",
        "merge_horizontal_label": "平面結合",
        "merge_horizontal_help": "同じ色の平面を長方形で代替し、同じ長さが縦に連続する場合は縦方向にも結合します。平面の数を大幅に減らします。1Pixelごといじりたいのであればこのチェックを外してください。",
        "plane_size_label": "平面の大きさ",
        "plane_size_help": "1.0が現在の大きさ。小さくすると文字がスカスカになります。ドット感のある文字の描写に使います。",
        "x_spacing_label": "横方向の間隔",
        "x_spacing_help": "横方向だけ間隔を詰めたり広げたりします。1.0が現在の間隔です。",
        "plane_type_label": "使用する平面",
        "plane_type_help": "マップの方(基本形→通常)の平面を使うか、キャラの方(基本形→キャラ)の平面を使うかを設定します。マップライトとキャラライトのどちらのライトに影響されるかが決まります。",
        "plane_map": "平面(マップ)",
        "plane_chara": "平面(キャラ)",
        "triangle_type_label": "使用する三角形",
        "triangle_type_help": "マップの方(基本形→通常)の三角形を使うか、キャラの方(基本形→キャラ)の三角形を使うかを設定します。マップライトとキャラライトのどちらのライトに影響されるかが決まります。",
        "triangle_map": "三角形(マップ)",
        "triangle_chara": "三角形(キャラ)",
        "render_mode_label": "生成方式",
        "render_mode_help": "ドット平面で作るか、三角形メッシュで作るかを選びます。",
        "render_mode_dot": "ドット(平面)",
        "render_mode_mesh": "メッシュ(三角形)",
        "mesh_flatten_length_label": "メッシュ線分長",
        "mesh_flatten_length_help": "値を小さくすると曲線を細かく分割し、三角形の数が増えて重くなります。",
        "mesh_stop_quality_label": "メッシュ品質しきい値(stop_quality)",
        "mesh_stop_quality_help": "大きいほど早く止まりやすく軽くなり、小さいほど重くなりやすいです。",
        "mesh_edge_length_r_label": "メッシュ辺長比(edge_length_r)",
        "mesh_edge_length_r_help": "大きいほど粗く軽く、小さいほど細かく重くなります。",
        "mesh_target_edge_len_enable": "絶対辺長(target_edge_len)を使う",
        "mesh_target_edge_len_label": "絶対辺長(target_edge_len)",
        "mesh_target_edge_len_help": "有効時のみ使用。小さいほど三角形が増えます。",
        "mesh_outline_enable_label": "縁取りを有効化",
        "mesh_outline_enable_help": "ONにすると、文字の背面に縁取りメッシュを追加します。",
        "mesh_outline_width_label": "縁取り幅",
        "mesh_outline_width_help": "0で無効。値を大きくすると文字の外側に縁取りメッシュを追加します。",
        "mesh_outline_color_label": "縁取り色",
        "mesh_outline_folder_name": "縁取り",
        "mesh_solver_skip_warn": "三角形 {failed} 個はせん断解の収束に失敗したためスキップしました。",
        "mesh_reconstruction_skip_warn": "三角形 {failed} 個は再構成誤差が閾値超過のためスキップしました。",
        "mesh_reconstruction_info": "再構成誤差 (採用三角形): max={max_err:.3e}, rmse={rmse:.3e}, 閾値={tol:.3e}",
        "mesh_triangulation_title": "三角形分割プレビュー",
        "mesh_triangulation_empty": "分割結果がありません。",
        "mesh_dependency_error": "メッシュ生成には wildmeshing / fonttools / fontpens / scipy が必要です。",
        "mesh_missing_glyph_error": '文字"{error_moji}"はフォントに未収録のためレンダリングできませんでした',
        "mesh_stage_prepare": "準備中",
        "mesh_stage_glyph": "フォント輪郭を抽出中",
        "mesh_stage_triangulate": "輪郭を三角形分割中",
        "mesh_stage_solve": "三角形せん断を計算中",
        "mesh_stage_outline_triangulate": "縁取り輪郭を三角形分割中",
        "mesh_stage_outline_solve": "縁取り三角形せん断を計算中",
        "mesh_stage_preview": "分割プレビューを描画中",
        "mesh_stage_scene": "シーンを組み立て中",
        "mesh_stage_done": "完了",
        "light_cancel_label": "ライトの影響度",
        "light_cancel_help": 'アイテム設定の"ライトの影響度"を一括設定します。1ほどライトを反射しやすく、0ほどライトを吸収しやすくなります。',
        "generate_button": "シーンを生成",
        "error_no_text": "テキストが入力されていません",
        "generating": "シーンを生成中...",
        "success_generate": "生成完了！ ({count} 個の平面)",
        "preview_title": "文字生成イメージ",
        "original_image": "元のテキスト画像",
        "pixel_data": "ピクセルデータ ({width}×{height})",
        "scene_info_title": "シーン情報",
        "plane_count": "平面数",
        "plane_reduction": "平面削減",
        "mesh_triangle_total": "総三角形数",
        "mesh_triangle_accepted": "採用数",
        "mesh_triangle_failed": "失敗数",
        "download_button": "シーンファイルをダウンロード",
        "error_init": "アプリケーションの初期化に失敗しました:",
        "error_occurred": "エラーが発生しました:",
        "font_not_found": "フォントが見つかりません",
        "default_font_used": "デフォルトフォントを使用しています",
        "scene_title_prefix": "テキスト: ",
        "folder_title_prefix": "テキスト_",
    },
    "en": {
        "title": "Digital Craft Calligrapher",
        "subtitle": """Place text inside a Digital Craft scene.

- **Dot mode** — builds characters by arranging square planes in a grid
- **Mesh mode** — builds characters as smooth curves

Two modes are available.""",
        "qa_title": "Q&A",
        "qa_content": """
#### It gets heavy when I add text!

Turn **Antialiasing** OFF and enable **Horizontal plane merging** to minimize the number of planes.

You can also reduce plane count by lowering **Resolution per character**, but this decreases text resolution and readability.
If you must reduce plane count, adjust this parameter to find a good balance.

#### I forgot which settings I used!

The parameters are saved inside the **"Text Info"** folder in the generated scene.

#### What's the difference between "Dot" and "Mesh" render modes?

Dot mode represents text by arranging planes in a grid, while Mesh mode represents text by filling glyphs with flexible triangle polygons.

- Dot mode is faster and creates fewer items, so scenes stay lighter, but text edges can look jagged.
- Mesh mode takes longer to process, but it preserves smooth glyph outlines.

If the text is only displayed small in a scene, Dot mode is usually enough. For large, symbolic text such as logos, Mesh mode is recommended.

#### How are the curves generated?

I wrote a blog post explaining it [here](https://qiita.com/tropical-362827/items/6be88a910efa81f45791). Feel free to check it out if you're curious.

""",
        "metadata_folder": "Text Info",
        "meta_font": "Font",
        "meta_color": "Color",
        "meta_alpha": "Opacity",
        "meta_text_height": "Text height",
        "meta_resolution": "Resolution",
        "meta_antialias": "Antialiasing",
        "meta_aa_color": "AA color",
        "meta_merge_horizontal": "Merge horizontal",
        "meta_plane_size": "Plane size",
        "meta_plane_type": "Plane type",
        "meta_light_influence": "Light influence",
        "meta_render_mode": "Render mode",
        "meta_mesh_flatten_length": "Mesh segment length",
        "meta_mesh_stop_quality": "Mesh stop_quality",
        "meta_mesh_edge_length_r": "Mesh edge_length_r",
        "meta_mesh_target_edge_len": "Mesh target_edge_len",
        "meta_mesh_outline_enabled": "Mesh outline",
        "meta_mesh_outline_width": "Mesh outline width",
        "meta_mesh_outline_color": "Mesh outline color",
        "param_settings": "Parameter Settings",
        "text_input": "Text",
        "text_placeholder": "Enter text here",
        "font_label": "Font",
        "color_label": "Color",
        "alpha_label": "Color transparency",
        "text_size_title": "Text Size",
        "text_size_help": "Text height. 0.1 is about the size of a character's palm, 0.4 is about character's head.",
        "text_size_example": "Font size example",
        "height_label": "Height",
        "advanced_settings": "Advanced Settings",
        "resolution_label": "Resolution per character",
        "resolution_help": "Pixel fineness of text. Higher values produce cleaner text but heavier scenes",
        "antialias_label": "Use antialiasing",
        "antialias_color_label": "Antialiasing color",
        "merge_horizontal_label": "Plane merging",
        "merge_horizontal_help": "Replaces matching colors with rectangles and also merges vertically when runs have the same length. Greatly reduces plane count. Uncheck to edit per pixel.",
        "plane_size_label": "Plane size",
        "plane_size_help": "1.0 is current size. Smaller values make text sparse. Used for pixel-art style text.",
        "x_spacing_label": "Horizontal spacing",
        "x_spacing_help": "Adjust horizontal spacing only. 1.0 is the current spacing.",
        "plane_type_label": "Plane type to use",
        "plane_type_help": "Choose whether to use map (Primitives → Normal) planes or character (Primitives → Character) planes. This determines which light type affects them.",
        "plane_map": "Plane (Map)",
        "plane_chara": "Plane (Character)",
        "triangle_type_label": "Triangle type to use",
        "triangle_type_help": "Choose whether to use map (Primitives → Normal) triangles or character (Primitives → Character) triangles. This determines which light type affects them.",
        "triangle_map": "Triangle (Map)",
        "triangle_chara": "Triangle (Character)",
        "render_mode_label": "Render mode",
        "render_mode_help": "Choose dot planes or triangulated mesh rendering.",
        "render_mode_dot": "Dots (Planes)",
        "render_mode_mesh": "Mesh (Triangles)",
        "mesh_flatten_length_label": "Mesh segment length",
        "mesh_flatten_length_help": "Smaller values split curves more finely but increase triangle count.",
        "mesh_stop_quality_label": "Mesh quality threshold (stop_quality)",
        "mesh_stop_quality_help": "Higher values stop earlier and are usually lighter; lower values tend to be heavier.",
        "mesh_edge_length_r_label": "Mesh edge ratio (edge_length_r)",
        "mesh_edge_length_r_help": "Higher values make coarser/lighter meshes; lower values make denser/heavier meshes.",
        "mesh_target_edge_len_enable": "Use absolute edge length (target_edge_len)",
        "mesh_target_edge_len_label": "Absolute edge length (target_edge_len)",
        "mesh_target_edge_len_help": "Used only when enabled. Smaller values increase triangle count.",
        "mesh_outline_enable_label": "Enable outline",
        "mesh_outline_enable_help": "Adds an outline mesh behind the glyphs.",
        "mesh_outline_width_label": "Outline width",
        "mesh_outline_width_help": "Set to 0 to disable. Larger values add a thicker outline mesh behind glyphs.",
        "mesh_outline_color_label": "Outline color",
        "mesh_outline_folder_name": "Outline",
        "mesh_solver_skip_warn": "Skipped {failed} triangles because the shear solve did not converge.",
        "mesh_reconstruction_skip_warn": "Skipped {failed} triangles because reconstruction error exceeded the threshold.",
        "mesh_reconstruction_info": "Reconstruction error (accepted triangles): max={max_err:.3e}, rmse={rmse:.3e}, threshold={tol:.3e}",
        "mesh_triangulation_title": "Triangulation Preview",
        "mesh_triangulation_empty": "No triangulation result.",
        "mesh_dependency_error": "Mesh mode requires wildmeshing / fonttools / fontpens / scipy.",
        "mesh_missing_glyph_error": 'Character "{error_moji}" is not available in the selected font and could not be rendered.',
        "mesh_stage_prepare": "Preparing",
        "mesh_stage_glyph": "Extracting glyph outlines",
        "mesh_stage_triangulate": "Triangulating contours",
        "mesh_stage_solve": "Solving triangle shears",
        "mesh_stage_outline_triangulate": "Triangulating outline contours",
        "mesh_stage_outline_solve": "Solving outline triangle shears",
        "mesh_stage_preview": "Rendering triangulation preview",
        "mesh_stage_scene": "Building scene",
        "mesh_stage_done": "Done",
        "light_cancel_label": "Light influence",
        "light_cancel_help": 'Sets item "Light influence" setting. Higher values reflect light more, lower values absorb light more.',
        "generate_button": "Generate Scene",
        "error_no_text": "No text entered",
        "generating": "Generating scene...",
        "success_generate": "Generation complete! ({count} planes)",
        "preview_title": "Text generation preview",
        "original_image": "Original text image",
        "pixel_data": "Pixel data ({width}×{height})",
        "scene_info_title": "Scene Info",
        "plane_count": "Plane count",
        "plane_reduction": "Plane reduction",
        "mesh_triangle_total": "Total triangles",
        "mesh_triangle_accepted": "Accepted",
        "mesh_triangle_failed": "Failed",
        "download_button": "Download scene file",
        "error_init": "Failed to initialize application:",
        "error_occurred": "An error occurred:",
        "font_not_found": "Font not found",
        "default_font_used": "Using default font",
        "scene_title_prefix": "Text: ",
        "folder_title_prefix": "Text_",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


DEG2RAD = math.pi / 180.0
FONT_DIR = Path(__file__).parent / "digital-craft-calligrapher-data"


class DotRenderConfig:
    SPACING_RATIO = 0.2
    FONT_SIZE = 200
    CHAR_CANVAS_PADDING = 5
    DEFAULT_RESOLUTION = 100


class MeshRenderConfig:
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
    SOLVER_REFERENCE_TEXT_HEIGHT = 1.0
    FLATTEN_SEGMENT_LENGTH_DEFAULT = 50.0
    OUTLINE_WIDTH_DEFAULT = 0.0
    OUTLINE_COLOR_HEX_DEFAULT = "#000000"
    OUTLINE_Y_OFFSET_DEFAULT = -0.001
    # wildmeshing の分割設定。triwild.ipynb の使用例に合わせる。
    TRIWILD_STOP_QUALITY = 20.0
    TRIWILD_MAX_ITS = 80
    TRIWILD_STAGE = 1
    TRIWILD_EPSILON = -1.0
    TRIWILD_FEATURE_EPSILON = 1e-3
    TRIWILD_TARGET_EDGE_LEN = -1.0
    TRIWILD_EDGE_LENGTH_R = 0.12
    TRIWILD_FLAT_FEATURE_ANGLE = 10.0
    TRIWILD_CUT_OUTSIDE = True
    TRIWILD_SKIP_EPS = True
    TRIWILD_MUTE_LOG = True


class MissingGlyphError(ValueError):
    def __init__(self, error_moji):
        self.error_moji = error_moji
        super().__init__(error_moji)


PLANE_PRESETS = {
    "平面(マップ)": {"category": 0, "no": 215},
    "平面(キャラ)": {"category": 1, "no": 290},
}
TRIANGLE_PRESETS = {
    "三角形(マップ)": {"category": 0, "no": 216},
    "三角形(キャラ)": {"category": 1, "no": 291},
}


def list_available_fonts():
    return sorted(FONT_DIR.glob("*.ttf"))


def format_font_option(font_path):
    impressions = {
        "NotoSansJP-Regular.ttf": "ゴシック体",
        "NotoSerifJP-Regular.ttf": "明朝体",
        "YujiSyuku-Regular.ttf": "毛筆風",
        "MPLUSRounded1c-Regular.ttf": "やわらかな書体",
        "KleeOne-SemiBold.ttf": "手書き風",
        "DelaGothicOne-Regular.ttf": "極太",
        "YuseiMagic-Regular.ttf": "油性マジック",
        "DotGothic16-Regular.ttf": "ドット文字",
        "KaiseiDecol-Regular.ttf": "おしゃれ明朝",
        "Oswald-Regular.ttf": "縦長英字",
        "ZenKakuGothicNew-Regular.ttf": "無機質ゴシック",
        "ZenKakuGothicNew-Black.ttf": "無機質ゴシック太字",
        "青春6フォント.ttf": "エモい手書き文字, ひらがなカタカナのみ",
    }
    note = impressions.get(font_path.name)
    if note:
        return f"{font_path.name} ({note})"
    return font_path.name


def select_font_option(available_fonts, default_font_name):
    if not available_fonts:
        st.warning("フォントが見つかりません")
        return None
    default_font = FONT_DIR / default_font_name
    default_index = (
        available_fonts.index(default_font) if default_font in available_fonts else 0
    )
    return st.selectbox(
        "🔤 フォント",
        available_fonts,
        format_func=format_font_option,
        index=default_index,
    )


def compute_grid_width_from_image(img, grid_height):
    """元の画像の縦横比を維持したまま、グリッド幅を算出する。"""
    return max(1, int(round(img.width * grid_height / img.height)))


def build_preview_from_image(img, grid_width, grid_height):
    """元のPIL画像をプレビューサイズに縮小する。"""
    return resample_image(img, grid_width, grid_height)


def render_preview(original_img, preview_pixels, grid_width, grid_height, lang="ja"):
    st.subheader(f"🖼️ {get_text('preview_title', lang)}")
    st.markdown(
        f"**{get_text('pixel_data', lang).format(width=grid_width, height=grid_height)}**"
    )
    preview_img = Image.fromarray(preview_pixels)
    scale = max(1, min(12, int(512 / max(1, preview_img.width))))
    preview_img = preview_img.resize(
        (preview_img.width * scale, preview_img.height * scale),
        Image.Resampling.NEAREST,
    )
    st.image(preview_img, width="content")


def render_scene_info(
    scene,
    plane_count,
    plane_count_horizontal,
    raw_plane_count,
    lang="ja",
    is_mesh_mode=False,
    mesh_stats=None,
):
    st.subheader(f"📝 {get_text('scene_info_title', lang)}")
    info_col1, info_col2, info_col3 = st.columns(3)

    if is_mesh_mode:
        total_triangles = raw_plane_count
        accepted_triangles = plane_count
        if mesh_stats is not None:
            failed_triangles = int(mesh_stats.get("solve_failed_count", 0)) + int(
                mesh_stats.get("reconstruction_failed_count", 0)
            )
        elif raw_plane_count is not None:
            failed_triangles = max(0, raw_plane_count - plane_count)
        else:
            failed_triangles = 0

        with info_col1:
            st.metric(
                get_text("mesh_triangle_total", lang),
                f"{total_triangles}" if total_triangles is not None else "-",
            )
        with info_col2:
            st.metric(get_text("mesh_triangle_accepted", lang), f"{accepted_triangles}")
        with info_col3:
            st.metric(get_text("mesh_triangle_failed", lang), f"{failed_triangles}")
        return

    with info_col1:
        st.metric(get_text("plane_count", lang), f"{plane_count}")
    with info_col2:
        if raw_plane_count is not None:
            delta = raw_plane_count - plane_count
            delta_text = f"-{delta}" if delta >= 0 else f"+{abs(delta)}"
            horizontal_delta = raw_plane_count - plane_count_horizontal
            horizontal_delta_text = (
                f"-{horizontal_delta}"
                if horizontal_delta >= 0
                else f"+{abs(horizontal_delta)}"
            )
            st.metric(
                f"{get_text('plane_reduction', lang)}(横)",
                horizontal_delta_text,
                f"{plane_count_horizontal}/{raw_plane_count}",
            )
        else:
            st.metric(get_text("plane_reduction", lang), "-", "-")
    with info_col3:
        if raw_plane_count is not None:
            delta = raw_plane_count - plane_count
            delta_text = f"-{delta}" if delta >= 0 else f"+{abs(delta)}"
            st.metric(
                f"{get_text('plane_reduction', lang)}(縦)",
                delta_text,
                f"{plane_count}/{raw_plane_count}",
            )
        else:
            st.metric(get_text("plane_reduction", lang), "-", "-")


def build_scene_filename(text_input, render_mode_key="dot"):
    safe_text = "".join(c if c.isalnum() else "_" for c in text_input)
    return f"digitalcraft_scene_{render_mode_key}_text_{safe_text}.png"


TEMPLATE_SCENE_META = {
    "version": "1.0.0",
    "user_id": "deadbeef-dead-beef-dead-beefdeadbeef",
    "data_id": "deadbeef-dead-beef-dead-beefdeadbeef",
    "title": "テンプレート",
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
    "name": "フォルダー",
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


def build_template_scene() -> "HoneycomeSceneData":
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


# テンプレートの読み込み
@st.cache_resource
def load_template():
    """テンプレートシーンを読み込む"""
    template_scene = build_template_scene()
    folder_key = TEMPLATE_FOLDER_KEY
    folder_obj = template_scene.objects[folder_key]
    plane_template = folder_obj["data"]["child"][0]

    return template_scene, plane_template, folder_key, folder_obj


# 関数定義
def load_font(font_size, font_path=None):
    font = None
    if font_path is not None:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except OSError:
            font = None
    if font is None:
        for candidate in list_available_fonts():
            try:
                font = ImageFont.truetype(str(candidate), font_size)
                break
            except OSError:
                font = None
    if font is None:
        font = ImageFont.load_default()
        st.warning("デフォルトフォントを使用しています")
    return font


def text_to_image(
    text,
    font_size=100,
    canvas_width=None,
    canvas_height=None,
    font_path=None,
    font=None,
    padding=10,
):
    """テキストを画像に描画"""
    if font is None:
        font = load_font(font_size, font_path)

    dummy_img = Image.new("L", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font, anchor="ls")
    text_width = bbox[2] - bbox[0]
    if canvas_width is None:
        canvas_width = text_width + padding * 2
    if canvas_height is None:
        ascent, descent = font.getmetrics()
        canvas_height = ascent + descent + padding * 2

    img = Image.new("L", (canvas_width, canvas_height), color=0)
    draw = ImageDraw.Draw(img)

    x = (canvas_width - text_width) // 2 - bbox[0]
    baseline_y = padding + font.getmetrics()[0]
    draw.text((x, baseline_y), text, fill=255, font=font, anchor="ls")

    return img


def resample_image(img, target_width, target_height):
    """画像を指定サイズにリサンプル"""
    scale = min(target_width / img.width, target_height / img.height)
    resized_width = max(1, int(img.width * scale))
    resized_height = max(1, int(img.height * scale))
    resized = img.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
    canvas = Image.new("L", (target_width, target_height), color=0)
    x = (target_width - resized_width) // 2
    y = target_height - resized_height
    canvas.paste(resized, (x, y))
    pixels = np.array(canvas)
    return pixels


def create_plane(template, x, y, z, color, scale=1.0):
    """平面オブジェクトを作成"""
    plane = copy.deepcopy(template)
    plane["data"]["position"]["x"] = x
    plane["data"]["position"]["y"] = y
    plane["data"]["position"]["z"] = z
    plane["data"]["scale"]["x"] = scale
    plane["data"]["scale"]["y"] = scale
    plane["data"]["scale"]["z"] = scale
    plane["data"]["colors"][0] = color
    # テンプレート由来の値に依存しないよう、線幅は常に0に固定する。
    plane["data"]["line_width"] = 0.0
    return plane


class TriangleSolverLMReparam:
    """sx/cx/cz を再パラメータ化して LM で解くソルバ。"""

    def __init__(self, source_xz):
        source = np.asarray(source_xz, dtype=np.float64)
        if source.shape != (3, 2):
            raise ValueError("TriangleSolverLMReparam requires source_xz shape (3, 2)")
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
    def effective_scale(sx, sz, theta_deg):
        rad = theta_deg * DEG2RAD
        cos2 = math.cos(rad) ** 2
        sin2 = math.sin(rad) ** 2
        return sx * cos2 + sz * sin2, sx * sin2 + sz * cos2

    @classmethod
    def _build_A_entries(cls, alpha, sx, sz, theta, child_x, child_z):
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
        self, source_xz=None, *, px, pz, alpha, sx, theta, cs=None, cx=None, cz=None
    ):
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

    def reconstruction_error(self, target_xz, solved):
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
    def _sigmoid(x):
        x = np.asarray(x, dtype=np.float64)
        out = np.empty_like(x)
        positive = x >= 0
        out[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
        exp_x = np.exp(x[~positive])
        out[~positive] = exp_x / (1.0 + exp_x)
        return out

    @staticmethod
    def _softplus(x):
        x = np.asarray(x, dtype=np.float64)
        return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0.0)

    @staticmethod
    def _softplus_inv(y):
        y = np.asarray(y, dtype=np.float64)
        out = np.empty_like(y)
        small = y < 20.0
        out[small] = np.log(np.expm1(y[small]))
        out[~small] = y[~small]
        return out

    @staticmethod
    def _logit(p):
        p = np.asarray(p, dtype=np.float64)
        return np.log(p) - np.log1p(-p)

    def _to_unconstrained(self, sx, cx, cz, sx_min, sx_span, c_min):
        eps = 1e-12
        p = (sx - sx_min) / sx_span
        p = np.clip(p, eps, 1.0 - eps)
        u = float(self._logit(np.array([p], dtype=np.float64))[0])

        cx_pos = max(cx - c_min, eps)
        cz_pos = max(cz - c_min, eps)
        v = float(self._softplus_inv(np.array([cx_pos], dtype=np.float64))[0])
        w = float(self._softplus_inv(np.array([cz_pos], dtype=np.float64))[0])
        return u, v, w

    def _from_unconstrained(self, u, v, w, sx_min, sx_max, sx_span, c_min):
        sx = sx_min + sx_span * float(self._sigmoid(np.array([u], dtype=np.float64))[0])
        sx = float(np.clip(sx, sx_min, sx_max))
        sz = 1.0 - sx
        cx = c_min + float(self._softplus(np.array([v], dtype=np.float64))[0])
        cz = c_min + float(self._softplus(np.array([w], dtype=np.float64))[0])
        return sx, sz, cx, cz

    def solve(self, target_xz):
        target = np.asarray(target_xz, dtype=np.float64)
        if target.shape != (3, 2):
            raise ValueError("target_xz must be shape (3, 2)")

        sx_min = float(MeshRenderConfig.SOLVER_SX_MIN)
        sx_max = float(MeshRenderConfig.SOLVER_SX_MAX)
        c_min = float(MeshRenderConfig.SOLVER_CHILD_SCALE_MIN)
        reg_weight = float(MeshRenderConfig.SOLVER_LM_REG_WEIGHT)
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

        candidates = []
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

        def make_equations(prior):
            def equations(unconstrained_params):
                alpha, u, theta, v, w = unconstrained_params
                sx, sz, cx, cz = self._from_unconstrained(
                    u, v, w, sx_min, sx_max, sx_span, c_min
                )
                eff_x, eff_z = self.effective_scale(sx, sz, theta)
                if eff_x <= 1e-8 or eff_z <= 1e-8:
                    geom = np.array([1e3, 1e3, 1e3, 1e3], dtype=np.float64)
                else:
                    child_x = cx / eff_x
                    child_z = cz / eff_z
                    a00, a01, a10, a11 = self._build_A_entries(
                        alpha, sx, sz, theta, child_x, child_z
                    )
                    geom = np.array(
                        [a00 - t00, a01 - t01, a10 - t10, a11 - t11], dtype=np.float64
                    )
                # method=\"lm\" は残差次元>=変数次元が必要なので微小正則化を加える。
                reg = reg_weight * (unconstrained_params - prior)
                return np.concatenate([geom, reg])

            return equations

        best_params = None
        best_residual = float("inf")
        for initial in candidates:
            equations = make_equations(initial)
            try:
                optimized = least_squares(
                    equations,
                    x0=initial,
                    method="lm",
                    max_nfev=MeshRenderConfig.SOLVER_MAX_NFEV,
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
            if residual < MeshRenderConfig.SOLVER_EARLY_BREAK_RESIDUAL_TOL:
                break

        if best_params is None:
            return {"reachable": False, "residual": float("inf")}

        alpha, u, theta, v, w = best_params
        sx, sz, cx, cz = self._from_unconstrained(
            u, v, w, sx_min, sx_max, sx_span, c_min
        )
        eff_x, eff_z = self.effective_scale(sx, sz, theta)
        if eff_x <= 1e-12 or eff_z <= 1e-12:
            return {"reachable": False, "residual": float("inf")}

        result = {
            "px": float(translation[0]),
            "pz": float(translation[1]),
            "alpha": float(alpha % 360),
            "sx": float(sx),
            "sz": float(sz),
            "theta": float(theta % 360),
            "cx": float(cx),
            "cz": float(cz),
            "cs": float(0.5 * (cx + cz)),
            "child_sx": float(cx / eff_x),
            "child_sz": float(cz / eff_z),
            "residual": best_residual,
            "reachable": best_residual < MeshRenderConfig.SOLVER_REACHABLE_RESIDUAL_TOL,
        }
        return result


def hex_to_color(hex_color):
    """#RRGGBB to color dict with 0-1 floats."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return {"r": r, "g": g, "b": b, "a": 1.0}


def build_metadata_folder(folder_obj, metadata: dict, lang="ja"):
    """生成時のパラメータを子フォルダ名として埋め込んだ情報フォルダを作成する。"""
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


class DotRenderPipeline:
    """ドット(平面)レンダリング関連の設定と処理入口を集約する。"""

    Config = DotRenderConfig

    @staticmethod
    def compute_canvas_height(text, font, padding):
        ascent, descent = font.getmetrics()
        return (ascent + descent) + padding * 2

    @staticmethod
    def compute_canvas_size(text, font, padding):
        max_char_width = 0
        dummy_img = Image.new("L", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        for char in text:
            bbox = dummy_draw.textbbox((0, 0), char, font=font, anchor="ls")
            max_char_width = max(max_char_width, bbox[2] - bbox[0])
        max_char_width = max(1, max_char_width)
        return max_char_width + padding * 2, DotRenderPipeline.compute_canvas_height(
            text, font, padding
        )

    @staticmethod
    def compute_layout(text_input, per_char_resolution, text_height, plane_size_factor):
        grid_width = max(1, per_char_resolution * max(1, len(text_input)))
        grid_height = per_char_resolution
        pixel_size = text_height / per_char_resolution
        text_scale = (pixel_size / DotRenderConfig.SPACING_RATIO) * plane_size_factor
        spacing = pixel_size
        return {
            "grid_width": grid_width,
            "grid_height": grid_height,
            "pixel_size": pixel_size,
            "text_scale": text_scale,
            "spacing": spacing,
        }

    @staticmethod
    def measure_text_advance(draw, font, value):
        """PILのメトリクスから文字列のアドバンス幅を取得する。"""
        if hasattr(draw, "textlength"):
            return draw.textlength(value, font=font)
        if hasattr(font, "getlength"):
            return font.getlength(value)
        bbox = draw.textbbox((0, 0), value, font=font, anchor="ls")
        return bbox[2] - bbox[0]

    @staticmethod
    def compute_text_center_ratios(text, font, img_width):
        """PILの描画位置に基づき、各文字の中心Xの比率(0-1)を返す。"""
        dummy_img = Image.new("L", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        text_bbox = dummy_draw.textbbox((0, 0), text, font=font, anchor="ls")
        text_left = text_bbox[0]
        text_width = max(1, text_bbox[2] - text_bbox[0])
        x_offset = (img_width - text_width) // 2 - text_left

        centers = []
        for index, char in enumerate(text):
            advance = DotRenderPipeline.measure_text_advance(
                dummy_draw, font, text[:index]
            )
            char_bbox = dummy_draw.textbbox((advance, 0), char, font=font, anchor="ls")
            if char_bbox is None or (char_bbox[2] - char_bbox[0]) == 0:
                char_advance = DotRenderPipeline.measure_text_advance(
                    dummy_draw, font, char
                )
                center = advance + char_advance / 2
            else:
                center = (char_bbox[0] + char_bbox[2]) / 2
            center_image = x_offset + center
            centers.append(center_image / max(1, img_width))
        return centers

    @staticmethod
    def build_char_pixels(
        text,
        font,
        font_size,
        per_char_resolution,
        canvas_width,
        canvas_height,
        effective_threshold,
    ):
        """各文字を描画し、1文字分の正方形ピクセルグリッドへ縮小する。"""
        char_pixels_list = []
        char_center_cols = []
        raw_plane_count = 0

        # 各文字を同一サイズのキャンバスへ描画して、等解像度のピクセルへ変換する。
        for char in text:
            char_img = text_to_image(
                char,
                font_size=font_size,
                font=font,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )
            char_pixels = resample_image(
                char_img,
                per_char_resolution,
                per_char_resolution,
            )
            raw_plane_count += int(np.sum(char_pixels >= effective_threshold))

            # 文字の見た目中心を求めるために、非ゼロ列の範囲を測る。
            nonzero_cols = np.where(char_pixels >= effective_threshold)[1]
            if nonzero_cols.size == 0:
                center_col = (per_char_resolution - 1) / 2
            else:
                center_col = (nonzero_cols.min() + nonzero_cols.max()) / 2

            char_pixels_list.append(char_pixels)
            char_center_cols.append(center_col)

        return char_pixels_list, char_center_cols, raw_plane_count

    @staticmethod
    def build_char_folders(
        text,
        char_pixels_list,
        char_center_cols,
        desired_centers,
        plane_template,
        folder_obj,
        grid_width,
        spacing,
        threshold,
        color,
        edge_color,
        antialias,
        plane_scale,
        global_start_x,
        global_start_z,
        per_char_resolution,
        merge_horizontal,
        merge_color_threshold,
    ):
        """文字ごとの平面とフォルダを生成し、中心比率に沿って配置する。"""
        char_folders = []
        plane_count = 0
        plane_count_horizontal = 0

        for index, char in enumerate(text):
            # 左右反転を補正し、座標系の向きに合わせる。
            char_pixels = np.fliplr(char_pixels_list[index])
            center_col = char_center_cols[index]

            # 文字画像の左端位置（X）を、文字ごとの解像度に基づいて配置する。
            char_start_x = global_start_x + index * per_char_resolution * spacing
            center_x = char_start_x + center_col * spacing
            planes, planes_horizontal = DotRenderPipeline.pixels_to_planes(
                char_pixels,
                plane_template,
                spacing=spacing,
                threshold=threshold,
                color=color,
                edge_color=edge_color,
                antialias=antialias,
                scale=plane_scale,
                start_x=char_start_x,
                start_z=global_start_z,
                merge_horizontal=merge_horizontal,
                merge_color_threshold=merge_color_threshold,
            )
            # ローカル中心に合わせて平面をオフセットする。
            for plane in planes:
                plane["data"]["position"]["x"] -= center_x
            plane_count += len(planes)
            plane_count_horizontal += planes_horizontal

            # PIL上の中心比率を、シーンのX座標へ変換する。
            desired_center_x = global_start_x + (grid_width - 1) * spacing * (
                1.0 - desired_centers[index]
            )

            char_folder = copy.deepcopy(folder_obj)
            char_label = char if char.strip() else "空白"
            char_folder["data"]["name"] = f"文字_{index + 1}_{char_label}"
            char_folder["data"]["position"]["x"] = desired_center_x
            char_folder["data"]["child"] = planes
            char_folder["data"]["treeState"] = 1
            char_folders.append(char_folder)

        return char_folders, plane_count, plane_count_horizontal

    @staticmethod
    def blend_colors(fg_color, bg_color, pixel_value):
        """Blend foreground and background using grayscale brightness."""
        t = pixel_value / 255.0
        return {
            "r": bg_color["r"] * (1.0 - t) + fg_color["r"] * t,
            "g": bg_color["g"] * (1.0 - t) + fg_color["g"] * t,
            "b": bg_color["b"] * (1.0 - t) + fg_color["b"] * t,
            "a": 1.0,
        }

    @staticmethod
    def resolve_pixel_color(pixel_value, fg_color, bg_color, antialias):
        """Return per-pixel color based on antialias setting."""
        if not antialias:
            return fg_color
        return DotRenderPipeline.blend_colors(fg_color, bg_color, pixel_value)

    @staticmethod
    def colors_close(color_a, color_b, threshold):
        if threshold <= 0:
            return color_a == color_b
        for channel in ("r", "g", "b"):
            if abs(color_a[channel] - color_b[channel]) > threshold:
                return False
        return True

    @staticmethod
    def pixels_to_planes(
        pixels,
        plane_template,
        spacing=0.05,
        threshold=1,
        color=None,
        edge_color=None,
        antialias=True,
        scale=1.0,
        start_x=None,
        start_z=None,
        merge_horizontal=False,
        merge_color_threshold=0.05,
    ):
        """ピクセルデータから平面オブジェクトを生成"""
        height, width = pixels.shape
        planes = []
        runs = []
        runs_by_row = [[] for _ in range(height)]
        if color is None:
            color = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
        if edge_color is None:
            edge_color = {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}

        if start_x is None:
            start_x = -((width - 1) * spacing) / 2
        if start_z is None:
            start_z = -((height - 1) * spacing) / 2

        effective_threshold = 1 if antialias else 128

        def flush_run(run_start, run_end, run_color, row_index):
            run_length = run_end - run_start + 1
            run_info = {
                "start": run_start,
                "end": run_end,
                "length": run_length,
                "row": row_index,
                "color": run_color,
            }
            runs.append(run_info)
            runs_by_row[row_index].append(run_info)

        def add_plane(run_start, run_end, run_color, row_start, row_end):
            run_length = run_end - run_start + 1
            run_height = row_end - row_start + 1
            x_first = start_x + run_start * spacing
            x_last = start_x + run_end * spacing
            z_first = start_z + row_start * spacing
            z_last = start_z + row_end * spacing
            x = (x_first + x_last) / 2
            z = (z_first + z_last) / 2
            y = 0.0
            plane = create_plane(plane_template, x, y, z, run_color, scale)
            plane["data"]["scale"]["x"] = scale * run_length
            plane["data"]["scale"]["z"] = scale * run_height
            planes.append(plane)

        for row in range(height):
            run_start = None
            run_color = None
            run_end = None

            for col in range(width):
                pixel_value = pixels[row, col]
                if pixel_value >= effective_threshold:
                    shaded_color = DotRenderPipeline.resolve_pixel_color(
                        pixel_value, color, edge_color, antialias
                    )
                    if run_start is None:
                        run_start = col
                        run_end = col
                        run_color = shaded_color
                    elif merge_horizontal and DotRenderPipeline.colors_close(
                        shaded_color, run_color, merge_color_threshold
                    ):
                        run_end = col
                    else:
                        flush_run(run_start, run_end, run_color, row)
                        run_start = col
                        run_end = col
                        run_color = shaded_color
                else:
                    if run_start is not None:
                        flush_run(run_start, run_end, run_color, row)
                        run_start = None
                        run_end = None
                        run_color = None

            if run_start is not None:
                flush_run(run_start, run_end, run_color, row)

        if not merge_horizontal:
            for run in runs:
                add_plane(
                    run["start"], run["end"], run["color"], run["row"], run["row"]
                )
            return planes, len(runs)

        def color_key(color_value):
            return (
                color_value["r"],
                color_value["g"],
                color_value["b"],
                color_value["a"],
            )

        active_runs = {}
        for row in range(height):
            row_runs = runs_by_row[row]
            next_active = {}
            for run in row_runs:
                key = (run["start"], run["end"], color_key(run["color"]))
                if key in active_runs and active_runs[key]["row_end"] == row - 1:
                    active_runs[key]["row_end"] = row
                    next_active[key] = active_runs[key]
                else:
                    next_active[key] = {
                        "start": run["start"],
                        "end": run["end"],
                        "color": run["color"],
                        "row_start": row,
                        "row_end": row,
                    }

            for key, active in active_runs.items():
                if key not in next_active:
                    add_plane(
                        active["start"],
                        active["end"],
                        active["color"],
                        active["row_start"],
                        active["row_end"],
                    )
            active_runs = next_active

        for active in active_runs.values():
            add_plane(
                active["start"],
                active["end"],
                active["color"],
                active["row_start"],
                active["row_end"],
            )

        return planes, len(runs)

    @staticmethod
    def generate_text_scene(
        text,
        template_scene,
        plane_template,
        folder_key,
        folder_obj,
        grid_height=60,
        font_size=100,
        text_scale=0.25,
        spacing=None,
        threshold=1,
        color=None,
        edge_color=None,
        antialias=True,
        font_path=None,
        merge_horizontal=False,
        merge_color_threshold=0.05,
        generation_metadata=None,
        lang="ja",
    ):
        """テキストから3Dシーンを生成"""
        # spacing = scale × 0.2 の関係を利用
        if spacing is None:
            spacing = text_scale * DotRenderConfig.SPACING_RATIO
        plane_scale = text_scale

        # 1. テキストを画像に変換（プレビュー用）
        font = load_font(font_size, font_path)
        img = text_to_image(text, font_size=font_size, font=font)
        canvas_width, canvas_height = DotRenderPipeline.compute_canvas_size(
            text, font, DotRenderConfig.CHAR_CANVAS_PADDING
        )

        # 2. 1文字ごとに平面を生成
        per_char_resolution = grid_height
        grid_width = compute_grid_width_from_image(img, per_char_resolution)

        # グリッド幅に合わせてテキスト全体の左右スケールを揃える。
        global_start_x = -((grid_width - 1) * spacing) / 2
        global_start_z = -((grid_height - 1) * spacing) / 2
        effective_threshold = 1 if antialias else 128

        # PILの文字中心比率を使って、各文字の配置基準を決める。
        desired_centers = DotRenderPipeline.compute_text_center_ratios(
            text, font, img.width
        )
        (
            char_pixels_list,
            char_center_cols,
            raw_plane_count,
        ) = DotRenderPipeline.build_char_pixels(
            text,
            font,
            font_size,
            per_char_resolution,
            canvas_width,
            canvas_height,
            effective_threshold,
        )
        # プレビューは元画像をグリッドサイズに合わせて縮小する。
        preview_pixels = build_preview_from_image(img, grid_width, grid_height)

        # 文字ごとの平面を構築し、フォルダにまとめる。
        char_folders, plane_count, plane_count_horizontal = (
            DotRenderPipeline.build_char_folders(
                text,
                char_pixels_list,
                char_center_cols,
                desired_centers,
                plane_template,
                folder_obj,
                grid_width,
                spacing,
                threshold,
                color,
                edge_color,
                antialias,
                plane_scale,
                global_start_x,
                global_start_z,
                per_char_resolution,
                merge_horizontal,
                merge_color_threshold,
            )
        )

        # 3. シーンを作成
        scene = HoneycomeSceneData()
        scene.version = template_scene.version
        scene.dataVersion = template_scene.dataVersion
        scene.user_id = template_scene.user_id
        scene.data_id = str(uuid.uuid4())
        scene.title = f"{get_text('scene_title_prefix', lang)}{text}"
        scene.unknown_1 = template_scene.unknown_1
        scene.unknown_2 = template_scene.unknown_2
        scene.unknown_tail_1 = template_scene.unknown_tail_1
        scene.unknown_tail_2 = template_scene.unknown_tail_2
        scene.unknown_tail_3 = template_scene.unknown_tail_3
        scene.unknown_tail_4 = template_scene.unknown_tail_4
        scene.unknown_tail_5 = template_scene.unknown_tail_5
        scene.unknown_tail_6 = template_scene.unknown_tail_6
        scene.unknown_tail_7 = template_scene.unknown_tail_7
        scene.unknown_tail_8 = template_scene.unknown_tail_8
        scene.unknown_tail_9 = template_scene.unknown_tail_9
        scene.unknown_tail_10 = template_scene.unknown_tail_10
        scene.frame_filename = template_scene.frame_filename
        scene.unknown_tail_11 = template_scene.unknown_tail_11
        scene.footer_marker = template_scene.footer_marker
        scene.unknown_tail_extra = template_scene.unknown_tail_extra
        scene.image = template_scene.image

        new_folder = copy.deepcopy(folder_obj)
        new_folder["data"]["name"] = f"{get_text('folder_title_prefix', lang)}{text}"
        new_folder["data"]["treeState"] = 1

        # 文字情報フォルダを先頭に追加（再現用メタデータ）
        if generation_metadata:
            metadata_folder = build_metadata_folder(
                folder_obj, generation_metadata, lang
            )
            new_folder["data"]["child"] = [metadata_folder] + char_folders
        else:
            new_folder["data"]["child"] = char_folders

        scene.objects = {folder_key: new_folder}

        return (
            scene,
            img,
            preview_pixels,
            plane_count,
            plane_count_horizontal,
            raw_plane_count,
        )

    @staticmethod
    def default_advanced_settings():
        return {
            "per_char_resolution": DotRenderConfig.DEFAULT_RESOLUTION,
            "threshold": 1,
            "antialias": False,
            "edge_color_hex": "#000000",
            "merge_horizontal": False,
            "merge_color_threshold": 0.0,
            "plane_size_factor": 1.0,
        }

    @staticmethod
    def render_advanced_settings(lang):
        settings = DotRenderPipeline.default_advanced_settings()
        col1, col2 = st.columns(2)
        with col1:
            settings["per_char_resolution"] = st.slider(
                get_text("resolution_label", lang),
                min_value=10,
                max_value=200,
                value=DotRenderConfig.DEFAULT_RESOLUTION,
                step=5,
                help=get_text("resolution_help", lang),
            )
        with col2:
            settings["threshold"] = 1
        settings["antialias"] = st.checkbox(
            get_text("antialias_label", lang), value=False
        )
        settings["edge_color_hex"] = st.color_picker(
            get_text("antialias_color_label", lang), value="#000000"
        )
        settings["merge_horizontal"] = st.checkbox(
            get_text("merge_horizontal_label", lang),
            value=True,
            help=get_text("merge_horizontal_help", lang),
        )
        settings["plane_size_factor"] = st.slider(
            get_text("plane_size_label", lang),
            min_value=0.5,
            max_value=1.0,
            value=1.0,
            step=0.05,
            help=get_text("plane_size_help", lang),
        )
        return settings

    @staticmethod
    def build_generation_metadata(
        *,
        lang,
        selected_font,
        color_hex,
        color_alpha,
        text_height,
        plane_preset_key,
        light_cancel,
        dot_settings,
    ):
        return {
            get_text("meta_font", lang): selected_font.name
            if selected_font
            else "default",
            get_text("meta_color", lang): color_hex,
            get_text("meta_alpha", lang): color_alpha,
            get_text("meta_text_height", lang): text_height,
            get_text("meta_resolution", lang): dot_settings["per_char_resolution"],
            get_text("meta_antialias", lang): (
                "ON" if dot_settings["antialias"] else "OFF"
            ),
            get_text("meta_aa_color", lang): dot_settings["edge_color_hex"],
            get_text("meta_merge_horizontal", lang): (
                "ON" if dot_settings["merge_horizontal"] else "OFF"
            ),
            get_text("meta_plane_size", lang): dot_settings["plane_size_factor"],
            get_text("meta_plane_type", lang): plane_preset_key,
            get_text("meta_light_influence", lang): light_cancel,
            get_text("meta_render_mode", lang): get_text("render_mode_dot", lang),
            get_text("meta_mesh_flatten_length", lang): "-",
        }

    @staticmethod
    def generate_for_main(
        *,
        text_input,
        template_scene,
        plane_template,
        folder_key,
        folder_obj,
        layout,
        font_size,
        color,
        selected_font,
        dot_settings,
        generation_metadata,
        lang,
    ):
        edge_color = hex_to_color(dot_settings["edge_color_hex"])
        with st.spinner(get_text("generating", lang)):
            (
                scene,
                original_img,
                preview_pixels,
                plane_count,
                plane_count_horizontal,
                raw_plane_count,
            ) = DotRenderPipeline.generate_scene(
                text=text_input,
                template_scene=template_scene,
                plane_template=plane_template,
                folder_key=folder_key,
                folder_obj=folder_obj,
                grid_height=layout["grid_height"],
                font_size=font_size,
                text_scale=layout["text_scale"],
                spacing=layout["spacing"],
                threshold=dot_settings["threshold"],
                color=color,
                edge_color=edge_color,
                antialias=dot_settings["antialias"],
                font_path=selected_font,
                merge_horizontal=dot_settings["merge_horizontal"],
                merge_color_threshold=dot_settings["merge_color_threshold"],
                generation_metadata=generation_metadata,
                lang=lang,
            )
        return {
            "scene": scene,
            "original_img": original_img,
            "preview_pixels": preview_pixels,
            "plane_count": plane_count,
            "plane_count_horizontal": plane_count_horizontal,
            "raw_plane_count": raw_plane_count,
            "mesh_stats": None,
            "triangulation_preview": None,
        }

    generate_scene = generate_text_scene


class MeshRenderPipeline:
    """メッシュ(三角形)レンダリング関連の設定と処理入口を集約する。"""

    Config = MeshRenderConfig
    Solver = TriangleSolverLMReparam

    @staticmethod
    def find_missing_glyphs(text, font_path):
        """フォント cmap に存在しない文字(空白類は除外)を返す。"""
        tt_font = TTFont(str(font_path))
        try:
            cmap = tt_font.getBestCmap() or {}
            missing = []
            seen = set()
            for char in text:
                if char.isspace():
                    continue
                if ord(char) not in cmap and char not in seen:
                    missing.append(char)
                    seen.add(char)
            return missing
        finally:
            tt_font.close()

    @staticmethod
    def build_mesh_char_folders(
        text,
        char_mesh_data,
        plane_template,
        triangle_template,
        folder_obj,
        color,
        reconstruction_max_abs_tol=MeshRenderConfig.RECONSTRUCTION_MAX_ABS_TOL,
        y_offset=0.0,
        triangulate_stage="triangulate",
        solve_stage="solve",
        progress_callback=None,
    ):
        """文字輪郭を wildmeshing で三角形分割し、親平面+子三角形で表現する。"""
        solver = TriangleSolverLMReparam(MeshRenderConfig.SOURCE_TRIANGLE)
        char_folders = []
        triangle_count = 0
        raw_triangle_count = 0
        solve_failed_count = 0
        reconstruction_failed_count = 0
        accepted_max_abs_errors = []
        accepted_rmse_errors = []
        triangle_status_records = []
        triangles_per_char = []
        char_count = len(text)

        for index, char in enumerate(text):
            char_data = char_mesh_data[index]
            contours = char_data["contours"]
            triangles = MeshRenderPipeline.triangulate_contours(contours)
            triangles_per_char.append(triangles)
            raw_triangle_count += len(triangles)

            if progress_callback is not None:
                progress_callback(
                    stage=triangulate_stage,
                    current=index + 1,
                    total=char_count,
                    note=f"{char} ({len(triangles)})",
                )

        total_triangles = sum(len(triangles) for triangles in triangles_per_char)
        processed_triangles = 0
        solve_progress_step = (
            max(1, total_triangles // 250) if total_triangles > 0 else 1
        )

        for index, char in enumerate(text):
            char_data = char_mesh_data[index]
            triangles = triangles_per_char[index]
            triangle_objects = []
            folder_x = char_data["folder_x"]
            for triangle in triangles:
                processed_triangles += 1
                if progress_callback is not None and (
                    processed_triangles == 1
                    or processed_triangles == total_triangles
                    or (processed_triangles % solve_progress_step) == 0
                ):
                    progress_callback(
                        stage=solve_stage,
                        current=processed_triangles,
                        total=total_triangles,
                        note=f"{char}",
                    )

                triangle_object, solved = MeshRenderPipeline.create_sheared_triangle(
                    plane_template,
                    triangle_template,
                    triangle,
                    color,
                    solver,
                    y_offset=y_offset,
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
                                "char_index": index,
                                "folder_x": folder_x,
                            }
                        )
                    else:
                        solve_failed_count += 1
                        triangle_status_records.append(
                            {
                                "triangle": shifted_triangle,
                                "status": "solve_failed",
                                "char_index": index,
                                "folder_x": folder_x,
                            }
                        )
                    continue
                accepted_max_abs_errors.append(
                    solved.get("reconstruction_max_abs", 0.0)
                )
                accepted_rmse_errors.append(solved.get("reconstruction_rmse", 0.0))
                triangle_status_records.append(
                    {
                        "triangle": shifted_triangle,
                        "status": "accepted",
                        "char_index": index,
                        "folder_x": folder_x,
                    }
                )
                triangle_objects.append(triangle_object)

            triangle_count += len(triangle_objects)

            char_folder = copy.deepcopy(folder_obj)
            char_label = char if char.strip() else "空白"
            char_folder["data"]["name"] = f"文字_{index + 1}_{char_label}"
            char_folder["data"]["position"]["x"] = char_data["folder_x"]
            char_folder["data"]["child"] = triangle_objects
            char_folder["data"]["treeState"] = 1
            char_folders.append(char_folder)

        mesh_stats = {
            "solve_failed_count": solve_failed_count,
            "reconstruction_failed_count": reconstruction_failed_count,
            "reconstruction_tol": reconstruction_max_abs_tol,
            "accepted_max_abs_error": (
                float(max(accepted_max_abs_errors)) if accepted_max_abs_errors else 0.0
            ),
            "accepted_rmse": (
                float(np.mean(accepted_rmse_errors)) if accepted_rmse_errors else 0.0
            ),
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
        char_mesh_data, triangle_status_records, width=900, height=360, padding=24
    ):
        """文字輪郭と三角形分割結果を2Dプレビュー画像として描画する。"""
        global_contours = []
        global_triangles = triangle_status_records or []

        for char_data in char_mesh_data:
            folder_x = char_data["folder_x"]
            contours = char_data["contours"]
            for contour in contours:
                shifted = contour.copy()
                shifted[:, 0] += folder_x
                global_contours.append(shifted)

        if not global_contours and not global_triangles:
            return None

        points = []
        for contour in global_contours:
            points.append(contour)
        for record in global_triangles:
            points.append(record["triangle"])
        all_points = np.vstack(points)
        min_x = float(np.min(all_points[:, 0]))
        max_x = float(np.max(all_points[:, 0]))
        min_y = float(np.min(all_points[:, 1]))
        max_y = float(np.max(all_points[:, 1]))

        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)

        # 右側に凡例専用パネルを確保し、図形と重ならないようにする。
        legend_gap = 12
        legend_panel_width = 240
        plot_left = padding
        plot_top = padding
        plot_right = max(
            plot_left + 1,
            width - padding - legend_panel_width - legend_gap,
        )
        plot_bottom = height - padding
        plot_width = max(1.0, float(plot_right - plot_left))
        plot_height = max(1.0, float(plot_bottom - plot_top))
        scale = min(plot_width / span_x, plot_height / span_y)
        scaled_width = span_x * scale
        scaled_height = span_y * scale
        plot_offset_x = plot_left + (plot_width - scaled_width) * 0.5
        plot_offset_y = plot_top + (plot_height - scaled_height) * 0.5

        def project(point):
            # グリフ座標をシーンXZへ正規化する際に反転が入るため、
            # プレビュー側はX/Yを反転して見た目を元の文字方向に合わせる。
            x = plot_offset_x + (max_x - point[0]) * scale
            y = (plot_offset_y + scaled_height) - (max_y - point[1]) * scale
            return float(x), float(y)

        image = Image.new("RGBA", (width, height), (18, 20, 24, 255))
        draw = ImageDraw.Draw(image, "RGBA")

        status_style = {
            "accepted": {
                "priority": 0,
                "fill": (64, 180, 255, 35),
                "outline": (120, 220, 255, 180),
                "label": "accepted",
            },
            "reconstruction_failed": {
                "priority": 1,
                "fill": (255, 174, 66, 70),
                "outline": (255, 196, 122, 220),
                "label": "reconstruction failed",
            },
            "solve_failed": {
                "priority": 2,
                "fill": (255, 87, 127, 75),
                "outline": (255, 130, 164, 230),
                "label": "solver not converged",
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
    def recorded_commands_to_contours(recorded_commands):
        """RecordingPen の move/line コマンド列を輪郭配列へ変換する。"""
        contours = []
        current_points = []

        def flush_contour():
            nonlocal current_points
            if not current_points:
                return
            contour = np.array(current_points, dtype=np.float64)
            if len(contour) > 1 and np.allclose(contour[0], contour[-1]):
                contour = contour[:-1]
            contour = MeshRenderPipeline.dedupe_contour_points(contour)
            if (
                len(contour) >= 3
                and abs(MeshRenderPipeline.polygon_signed_area(contour)) > 1e-9
            ):
                contours.append(contour)
            current_points = []

        for command, args in recorded_commands:
            if command == "moveTo":
                flush_contour()
                current_points = [np.array(args[0], dtype=np.float64)]
            elif command == "lineTo":
                point = np.array(args[0], dtype=np.float64)
                if not current_points:
                    current_points = [point]
                else:
                    current_points.append(point)
            elif command in ("closePath", "endPath"):
                flush_contour()

        flush_contour()
        return contours

    @staticmethod
    def flatten_glyph_to_contours(glyph, glyph_set, segment_length):
        """fontPens.FlattenPen を使ってグリフ輪郭を線分化する。"""
        recording_pen = DecomposingRecordingPen(glyph_set)
        flatten_pen = FlattenPen(
            recording_pen,
            approximateSegmentLength=max(1.0, float(segment_length)),
            segmentLines=False,
            filterDoubles=True,
        )
        glyph.draw(flatten_pen)
        return MeshRenderPipeline.recorded_commands_to_contours(recording_pen.value)

    @staticmethod
    def polygon_signed_area(points):
        x_values = points[:, 0]
        y_values = points[:, 1]
        return 0.5 * (
            np.dot(x_values, np.roll(y_values, -1))
            - np.dot(y_values, np.roll(x_values, -1))
        )

    @staticmethod
    def dedupe_contour_points(contour, eps=1e-9):
        if len(contour) <= 1:
            return contour
        deduped = [contour[0]]
        for point in contour[1:]:
            if np.linalg.norm(point - deduped[-1]) > eps:
                deduped.append(point)
        if len(deduped) > 2 and np.linalg.norm(deduped[0] - deduped[-1]) <= eps:
            deduped = deduped[:-1]
        return np.array(deduped, dtype=np.float64)

    @staticmethod
    def point_in_polygon(point, polygon):
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
    def build_contour_hierarchy(contours):
        contour_count = len(contours)
        areas = [
            abs(MeshRenderPipeline.polygon_signed_area(contour)) for contour in contours
        ]
        parents = [-1] * contour_count

        def containment_probes(contour):
            probes = [np.mean(contour, axis=0)]
            count = len(contour)
            for index in range(count):
                current = contour[index]
                nxt = contour[(index + 1) % count]
                probes.append(current)
                probes.append((current + nxt) * 0.5)
            return probes

        for index, contour in enumerate(contours):
            probe_candidates = containment_probes(contour)
            containers = []
            for other_index, other_contour in enumerate(contours):
                if index == other_index:
                    continue
                # 親候補は必ず自分より大きい輪郭に限定し、循環参照を防ぐ。
                if areas[other_index] <= areas[index] + 1e-12:
                    continue
                if any(
                    MeshRenderPipeline.point_in_polygon(probe, other_contour)
                    for probe in probe_candidates
                ):
                    containers.append(other_index)
            if containers:
                parents[index] = min(containers, key=lambda idx: areas[idx])

        depths = [0] * contour_count
        for index in range(contour_count):
            depth = 0
            current = parents[index]
            safety = 0
            while current != -1 and safety < contour_count:
                depth += 1
                current = parents[current]
                safety += 1
            depths[index] = depth

        return parents, depths

    @staticmethod
    def find_polygon_interior_point(polygon):
        """三角形分割ライブラリ向けに、多角形内部の代表点を返す。"""
        if len(polygon) < 3:
            return None

        candidates = [np.mean(polygon, axis=0)]

        min_x = float(np.min(polygon[:, 0]))
        max_x = float(np.max(polygon[:, 0]))
        min_y = float(np.min(polygon[:, 1]))
        max_y = float(np.max(polygon[:, 1]))
        candidates.append(np.array([(min_x + max_x) * 0.5, (min_y + max_y) * 0.5]))

        count = len(polygon)
        for index in range(count):
            p_prev = polygon[(index - 1) % count]
            p_curr = polygon[index]
            p_next = polygon[(index + 1) % count]
            candidates.append((p_prev + p_curr + p_next) / 3.0)
            candidates.append((p_curr + p_next) * 0.5)

        # 追加のグリッド候補で、凹多角形でも内点を拾いやすくする。
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
            if MeshRenderPipeline.point_in_polygon(candidate, polygon):
                return candidate
        return None

    @staticmethod
    def normalize_contours_for_triangulation(contours):
        """三角形分割前に輪郭を正規化して重なりを解消する。"""
        valid_contours = []
        for contour in contours:
            normalized = MeshRenderPipeline.dedupe_contour_points(contour)
            if (
                len(normalized) >= 3
                and abs(MeshRenderPipeline.polygon_signed_area(normalized)) > 1e-9
            ):
                valid_contours.append(normalized)
        if not valid_contours:
            return []

        # Noto系など重なり輪郭を含むグリフは、そのままでは穴判定を誤る。
        # 先にブーリアン簡約して単純輪郭へ正規化してから分割する。
        simplified_path = MeshRenderPipeline.contours_to_pathops_path(valid_contours)
        if simplified_path is not None:
            simplified_path.simplify()
            simplified_contours = MeshRenderPipeline.pathops_path_to_contours(
                simplified_path
            )
            if simplified_contours:
                return simplified_contours
        return valid_contours

    @staticmethod
    def build_triangle_adjacency_order(tri_vertices, tri_indices):
        """共有辺の隣接を優先し、局所性の高い三角形走査順を返す。"""
        triangle_count = len(tri_indices)
        if triangle_count <= 1:
            return list(range(triangle_count))

        tri_vertices = np.asarray(tri_vertices, dtype=np.float64)
        tri_indices = np.asarray(tri_indices, dtype=np.int64)
        centroids = np.mean(tri_vertices[tri_indices], axis=1)

        adjacency = [set() for _ in range(triangle_count)]
        edge_to_triangles = {}

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
        ordered_indices = []
        last_index = None

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
    def triangulate_contours(contours):
        """輪郭群を三角形分割し、有効三角形を返す。"""
        valid_contours = MeshRenderPipeline.normalize_contours_for_triangulation(
            contours
        )
        if not valid_contours:
            return []

        parents, depths = MeshRenderPipeline.build_contour_hierarchy(valid_contours)
        triangles = []

        for outer_index, depth in enumerate(depths):
            if depth % 2 != 0:
                continue

            hole_indices = [
                contour_index
                for contour_index, parent_index in enumerate(parents)
                if parent_index == outer_index and depths[contour_index] == depth + 1
            ]
            outer_ring = valid_contours[outer_index]
            hole_rings = [valid_contours[hole_index] for hole_index in hole_indices]

            vertices = []
            segments = []
            holes = []

            def add_ring_segments(ring):
                start = len(vertices)
                ring_count = len(ring)
                for point in ring:
                    vertices.append([float(point[0]), float(point[1])])
                for index in range(ring_count):
                    next_index = (index + 1) % ring_count
                    segments.append([start + index, start + next_index])

            add_ring_segments(outer_ring)
            for hole_ring in hole_rings:
                add_ring_segments(hole_ring)
                hole_point = MeshRenderPipeline.find_polygon_interior_point(hole_ring)
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
                    stop_quality=MeshRenderConfig.TRIWILD_STOP_QUALITY,
                    max_its=MeshRenderConfig.TRIWILD_MAX_ITS,
                    stage=MeshRenderConfig.TRIWILD_STAGE,
                    epsilon=MeshRenderConfig.TRIWILD_EPSILON,
                    feature_epsilon=MeshRenderConfig.TRIWILD_FEATURE_EPSILON,
                    target_edge_len=MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN,
                    edge_length_r=MeshRenderConfig.TRIWILD_EDGE_LENGTH_R,
                    flat_feature_angle=MeshRenderConfig.TRIWILD_FLAT_FEATURE_ANGLE,
                    cut_outside=MeshRenderConfig.TRIWILD_CUT_OUTSIDE,
                    skip_eps=MeshRenderConfig.TRIWILD_SKIP_EPS,
                    hole_pts=tri_holes_input,
                    mute_log=MeshRenderConfig.TRIWILD_MUTE_LOG,
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

            triangle_order = MeshRenderPipeline.build_triangle_adjacency_order(
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
                area = MeshRenderPipeline.polygon_signed_area(triangle)
                if abs(area) <= 1e-10:
                    continue
                if area < 0:
                    triangle = triangle[[0, 2, 1]]
                triangles.append(triangle)

        return triangles

    @staticmethod
    def build_kerning_table(tt_font):
        kerning = {}
        if "kern" not in tt_font:
            return kerning
        for table in tt_font["kern"].kernTables:
            if hasattr(table, "kernTable"):
                kerning.update(table.kernTable)
        return kerning

    @staticmethod
    def build_text_mesh_characters(
        text,
        font_path,
        text_height,
        flatten_segment_length=MeshRenderConfig.FLATTEN_SEGMENT_LENGTH_DEFAULT,
        progress_callback=None,
    ):
        tt_font = TTFont(str(font_path))
        try:
            glyph_set = tt_font.getGlyphSet()
            cmap = tt_font.getBestCmap() or {}
            metrics = tt_font["hmtx"].metrics
            units_per_em = float(tt_font["head"].unitsPerEm)
            kerning = MeshRenderPipeline.build_kerning_table(tt_font)

            cursor_x = 0.0
            previous_glyph = None
            raw_characters = []
            all_points = []
            total_chars = len(text)
            effective_segment_length = max(1e-3, float(flatten_segment_length))

            for index, char in enumerate(text):
                codepoint = ord(char)
                glyph_name = cmap.get(codepoint)
                if glyph_name is None:
                    glyph_name = ".notdef" if ".notdef" in glyph_set else None

                if glyph_name is None:
                    advance = units_per_em * 0.5
                    center_x = cursor_x + advance * 0.5
                    raw_characters.append(
                        {
                            "char": char,
                            "center_x": center_x,
                            "contours": [],
                        }
                    )
                    cursor_x += advance
                    previous_glyph = None
                    if progress_callback is not None:
                        progress_callback(
                            stage="glyph",
                            current=index + 1,
                            total=total_chars,
                            note=char,
                        )
                    continue

                if previous_glyph is not None:
                    cursor_x += float(kerning.get((previous_glyph, glyph_name), 0.0))

                start_x = cursor_x
                glyph = glyph_set[glyph_name]
                flattened_contours = MeshRenderPipeline.flatten_glyph_to_contours(
                    glyph, glyph_set, effective_segment_length
                )

                translated_contours = []
                for contour in flattened_contours:
                    translated = contour.copy()
                    translated[:, 0] += start_x
                    translated_contours.append(translated)
                    all_points.append(translated)

                advance = float(metrics.get(glyph_name, (units_per_em, 0))[0])
                if advance <= 0:
                    advance = units_per_em * 0.5
                cursor_x += advance

                if translated_contours:
                    min_x = min(contour[:, 0].min() for contour in translated_contours)
                    max_x = max(contour[:, 0].max() for contour in translated_contours)
                    center_x = (min_x + max_x) * 0.5
                else:
                    center_x = start_x + advance * 0.5

                raw_characters.append(
                    {
                        "char": char,
                        "center_x": center_x,
                        "contours": translated_contours,
                    }
                )
                previous_glyph = glyph_name
                if progress_callback is not None:
                    progress_callback(
                        stage="glyph", current=index + 1, total=total_chars, note=char
                    )

            if not all_points:
                return [
                    {"char": char_data["char"], "folder_x": 0.0, "contours": []}
                    for char_data in raw_characters
                ]

            all_points_arr = np.vstack(all_points)
            min_x = float(np.min(all_points_arr[:, 0]))
            max_x = float(np.max(all_points_arr[:, 0]))
            min_y = float(np.min(all_points_arr[:, 1]))
            max_y = float(np.max(all_points_arr[:, 1]))

            glyph_height = max(1e-6, max_y - min_y)
            scale = text_height / glyph_height
            center_x = 0.5 * (min_x + max_x)
            center_y = 0.5 * (min_y + max_y)

            transformed_characters = []
            for char_data in raw_characters:
                folder_x = -(char_data["center_x"] - center_x) * scale
                transformed_contours = []
                for contour in char_data["contours"]:
                    transformed = np.empty_like(contour)
                    transformed[:, 0] = -(contour[:, 0] - center_x) * scale - folder_x
                    transformed[:, 1] = -(contour[:, 1] - center_y) * scale
                    transformed_contours.append(transformed)
                transformed_characters.append(
                    {
                        "char": char_data["char"],
                        "folder_x": folder_x,
                        "contours": transformed_contours,
                    }
                )

            return transformed_characters
        finally:
            tt_font.close()

    @staticmethod
    def compute_char_mesh_height(char_mesh_data):
        """文字輪郭データ全体のY範囲高さを返す。"""
        min_y = float("inf")
        max_y = float("-inf")
        for char_data in char_mesh_data:
            for contour in char_data.get("contours", []):
                if contour.size == 0:
                    continue
                min_y = min(min_y, float(np.min(contour[:, 1])))
                max_y = max(max_y, float(np.max(contour[:, 1])))
        if not (np.isfinite(min_y) and np.isfinite(max_y)):
            return 0.0
        return max(0.0, max_y - min_y)

    @staticmethod
    def build_dot_alignment_targets(
        text, font, font_size, img_width, grid_width, grid_height, spacing
    ):
        """Dot配置に合わせるための中心X列と目標高さを計算する。"""
        desired_centers = DotRenderPipeline.compute_text_center_ratios(
            text, font, img_width
        )
        global_start_x = -((grid_width - 1) * spacing) / 2
        target_centers_x = [
            global_start_x + (grid_width - 1) * spacing * (1.0 - ratio)
            for ratio in desired_centers
        ]

        canvas_width, canvas_height = DotRenderPipeline.compute_canvas_size(
            text, font, DotRenderConfig.CHAR_CANVAS_PADDING
        )
        char_pixels_list, _, _ = DotRenderPipeline.build_char_pixels(
            text,
            font,
            font_size,
            grid_height if grid_height > 0 else 1,
            canvas_width,
            canvas_height,
            effective_threshold=128,
        )

        dot_min_z = float("inf")
        dot_max_z = float("-inf")
        global_start_z = -((grid_height - 1) * spacing) / 2
        for char_pixels in char_pixels_list:
            rows = np.where(char_pixels >= 128)[0]
            if rows.size == 0:
                continue
            row_min = float(np.min(rows))
            row_max = float(np.max(rows))
            dot_min_z = min(dot_min_z, global_start_z + row_min * spacing)
            dot_max_z = max(dot_max_z, global_start_z + row_max * spacing)

        if not (np.isfinite(dot_min_z) and np.isfinite(dot_max_z)):
            target_height = 0.0
        else:
            target_height = max(0.0, dot_max_z - dot_min_z)

        return {
            "target_centers_x": target_centers_x,
            "target_height": target_height,
        }

    @staticmethod
    def contours_to_pathops_path(contours):
        if pathops is None:
            return None
        path = pathops.Path()
        has_contour = False
        for contour in contours:
            normalized = MeshRenderPipeline.dedupe_contour_points(
                np.asarray(contour, dtype=np.float64)
            )
            if (
                len(normalized) < 3
                or abs(MeshRenderPipeline.polygon_signed_area(normalized)) <= 1e-9
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
    def pathops_path_to_contours(path):
        if path is None:
            return []
        converted = []
        for contour in path.contours:
            points = np.asarray(list(contour.points), dtype=np.float64)
            normalized = MeshRenderPipeline.dedupe_contour_points(points)
            if (
                len(normalized) >= 3
                and abs(MeshRenderPipeline.polygon_signed_area(normalized)) > 1e-9
            ):
                converted.append(normalized)
        return converted

    @staticmethod
    def build_outline_contours_with_pathops(contours, outline_width):
        """pathops の stroke + difference で縁取りリングを生成する。"""
        if pathops is None:
            return None
        fill_path = MeshRenderPipeline.contours_to_pathops_path(contours)
        if fill_path is None:
            return None
        try:
            fill_path.simplify()
            stroked_path = pathops.Path()
            stroked_path.addPath(fill_path)
            stroked_path.stroke(
                width=float(2.0 * outline_width),
                cap=pathops.LineCap.BUTT_CAP,
                join=pathops.LineJoin.MITER_JOIN,
                miter_limit=4.0,
            )
            ring_path = pathops.op(stroked_path, fill_path, pathops.PathOp.DIFFERENCE)
            ring_path.simplify()
            return MeshRenderPipeline.pathops_path_to_contours(ring_path)
        except (ValueError, RuntimeError, FloatingPointError):
            return None

    @staticmethod
    def offset_contour_polygon(contour, offset_distance, miter_limit=4.0):
        """単一輪郭を辺法線ベースでオフセットする。"""
        points = MeshRenderPipeline.dedupe_contour_points(
            np.asarray(contour, dtype=np.float64)
        )
        if len(points) < 3:
            return None

        area = MeshRenderPipeline.polygon_signed_area(points)
        if abs(area) <= 1e-9:
            return None

        point_count = len(points)
        edge_dirs = []
        outward_normals = []
        for index in range(point_count):
            p0 = points[index]
            p1 = points[(index + 1) % point_count]
            edge = p1 - p0
            edge_norm = np.linalg.norm(edge)
            if edge_norm <= 1e-12:
                return None
            edge_dir = edge / edge_norm
            left_normal = np.array([-edge_dir[1], edge_dir[0]], dtype=np.float64)
            # 多角形の面積符号により、外向き法線を決める。
            outward = -left_normal if area > 0 else left_normal
            edge_dirs.append(edge_dir)
            outward_normals.append(outward)

        orientation = 1.0 if area > 0 else -1.0
        max_miter = max(1.0, float(miter_limit)) * abs(float(offset_distance))
        result_points = []

        for index in range(point_count):
            vertex = points[index]
            dir_prev = edge_dirs[index - 1]
            dir_next = edge_dirs[index]
            normal_prev = outward_normals[index - 1]
            normal_next = outward_normals[index]

            cross = dir_prev[0] * dir_next[1] - dir_prev[1] * dir_next[0]
            is_concave = orientation * cross < -1e-9
            shifted_prev = vertex + normal_prev * offset_distance
            shifted_next = vertex + normal_next * offset_distance

            if is_concave:
                # 凹角はベベルで自己交差を避ける。
                result_points.append(shifted_prev)
                result_points.append(shifted_next)
                continue

            denom = dir_prev[0] * dir_next[1] - dir_prev[1] * dir_next[0]
            if abs(denom) <= 1e-9:
                candidate = vertex + (normal_prev + normal_next) * 0.5 * offset_distance
            else:
                delta = shifted_next - shifted_prev
                t = (delta[0] * dir_next[1] - delta[1] * dir_next[0]) / denom
                candidate = shifted_prev + dir_prev * t

            miter_vec = candidate - vertex
            miter_len = float(np.linalg.norm(miter_vec))
            if miter_len > max_miter and miter_len > 1e-12:
                candidate = vertex + (miter_vec / miter_len) * max_miter
            result_points.append(candidate)

        offset_contour = MeshRenderPipeline.dedupe_contour_points(
            np.asarray(result_points, dtype=np.float64)
        )
        if len(offset_contour) < 3:
            return None
        if abs(MeshRenderPipeline.polygon_signed_area(offset_contour)) <= 1e-9:
            return None
        return offset_contour

    @staticmethod
    def build_outline_char_mesh_data(char_mesh_data, outline_width):
        """輪郭オフセットで縁取り用の差分リング輪郭を作る。"""
        expanded_characters = []
        effective_width = max(0.0, float(outline_width))

        for char_data in char_mesh_data:
            contours = [
                np.asarray(contour, dtype=np.float64).copy()
                for contour in char_data.get("contours", [])
            ]
            if effective_width <= 0.0 or not contours:
                expanded_characters.append(
                    {
                        "char": char_data["char"],
                        "folder_x": float(char_data.get("folder_x", 0.0)),
                        "contours": contours,
                    }
                )
                continue

            pathops_contours = MeshRenderPipeline.build_outline_contours_with_pathops(
                contours, effective_width
            )
            if pathops_contours:
                expanded_characters.append(
                    {
                        "char": char_data["char"],
                        "folder_x": float(char_data.get("folder_x", 0.0)),
                        "contours": pathops_contours,
                    }
                )
                continue

            valid_contours = []
            valid_original_indices = []
            for contour_index, contour in enumerate(contours):
                normalized = MeshRenderPipeline.dedupe_contour_points(contour)
                if (
                    len(normalized) >= 3
                    and abs(MeshRenderPipeline.polygon_signed_area(normalized)) > 1e-9
                ):
                    valid_contours.append(normalized)
                    valid_original_indices.append(contour_index)

            depth_map = {}
            if valid_contours:
                _, depths = MeshRenderPipeline.build_contour_hierarchy(valid_contours)
                for local_index, original_index in enumerate(valid_original_indices):
                    depth_map[original_index] = depths[local_index]

            expanded_contours = []
            for contour_index, contour in enumerate(contours):
                normalized_contour = MeshRenderPipeline.dedupe_contour_points(contour)
                if (
                    len(normalized_contour) < 3
                    or abs(MeshRenderPipeline.polygon_signed_area(normalized_contour))
                    <= 1e-9
                ):
                    continue

                depth = depth_map.get(contour_index, 0)
                # 偶数深度(外周)は外向き、奇数深度(穴)は内向きへオフセットする。
                offset_distance = (
                    effective_width if depth % 2 == 0 else -effective_width
                )
                normalized_offset = MeshRenderPipeline.offset_contour_polygon(
                    normalized_contour, offset_distance
                )
                if normalized_offset is None:
                    continue

                # 縁取りは「拡張形状そのもの」ではなく、元輪郭との差分リングとして作る。
                if depth % 2 == 0:
                    outer_ring = normalized_offset
                    inner_ring = normalized_contour
                else:
                    outer_ring = normalized_contour
                    inner_ring = normalized_offset

                probe = np.mean(inner_ring, axis=0)
                if not MeshRenderPipeline.point_in_polygon(probe, outer_ring):
                    continue

                expanded_contours.append(outer_ring)
                expanded_contours.append(inner_ring)

            expanded_characters.append(
                {
                    "char": char_data["char"],
                    "folder_x": float(char_data.get("folder_x", 0.0)),
                    "contours": expanded_contours,
                }
            )

        return expanded_characters

    @staticmethod
    def scale_triangle_object_output(triangle_parent, scale_factor):
        """solve後の親子三角形オブジェクトをXZ方向にスケールする。"""
        if abs(scale_factor - 1.0) <= 1e-12:
            return

        parent_data = triangle_parent.get("data", {})
        parent_pos = parent_data.get("position", {})
        parent_pos["x"] = float(parent_pos.get("x", 0.0)) * scale_factor
        parent_pos["z"] = float(parent_pos.get("z", 0.0)) * scale_factor

        for child in parent_data.get("child", []):
            child_data = child.get("data", {})
            child_scale = child_data.get("scale", {})
            child_scale["x"] = float(child_scale.get("x", 1.0)) * scale_factor
            child_scale["z"] = float(child_scale.get("z", 1.0)) * scale_factor

    @staticmethod
    def align_mesh_output_to_dot(
        char_mesh_data,
        char_folders,
        triangle_status_records,
        target_centers_x,
        target_height,
        scale_factor_override=None,
    ):
        """solve後のメッシュをDot基準の高さと文字中心へ合わせる。"""
        source_height = MeshRenderPipeline.compute_char_mesh_height(char_mesh_data)
        if scale_factor_override is not None:
            scale_factor = float(scale_factor_override)
        elif source_height > 1e-9 and target_height > 1e-9:
            scale_factor = target_height / source_height
        else:
            scale_factor = 1.0

        def center_for(index, fallback):
            if 0 <= index < len(target_centers_x):
                return float(target_centers_x[index])
            return float(fallback) * scale_factor

        for index, char_data in enumerate(char_mesh_data):
            old_folder_x = float(char_data.get("folder_x", 0.0))
            new_folder_x = center_for(index, old_folder_x)

            scaled_contours = []
            for contour in char_data.get("contours", []):
                scaled_contours.append(
                    np.asarray(contour, dtype=np.float64) * scale_factor
                )
            char_data["contours"] = scaled_contours
            char_data["folder_x"] = new_folder_x

            if index < len(char_folders):
                char_folder = char_folders[index]
                char_folder["data"]["position"]["x"] = new_folder_x
                for triangle_parent in char_folder["data"].get("child", []):
                    MeshRenderPipeline.scale_triangle_object_output(
                        triangle_parent, scale_factor
                    )

        for record in triangle_status_records:
            triangle = np.asarray(record.get("triangle"), dtype=np.float64)
            if triangle.shape != (3, 2):
                continue
            old_folder_x = float(record.get("folder_x", 0.0))
            char_index = int(record.get("char_index", -1))
            new_folder_x = center_for(char_index, old_folder_x)

            local_triangle = triangle.copy()
            local_triangle[:, 0] -= old_folder_x
            local_triangle *= scale_factor
            local_triangle[:, 0] += new_folder_x
            record["triangle"] = local_triangle
            record["folder_x"] = new_folder_x

        return {
            "scale_factor": scale_factor,
            "source_height": source_height,
            "target_height": target_height,
        }

    @staticmethod
    def create_sheared_triangle(
        plane_template,
        triangle_template,
        target_triangle,
        color,
        solver,
        child_y_scale=0.01,
        y_offset=0.0,
        reconstruction_max_abs_tol=MeshRenderConfig.RECONSTRUCTION_MAX_ABS_TOL,
    ):
        solved = solver.solve(target_triangle)
        residual = solved.get("residual", float("inf"))
        if not np.isfinite(residual):
            solved["rejected_reason"] = "solve_non_finite"
            return None, solved
        if not solved.get("reachable", False):
            solved["rejected_reason"] = "solve_not_converged"
            return None, solved

        reconstruction = solver.reconstruction_error(target_triangle, solved)
        solved["reconstruction_max_abs"] = reconstruction["max_abs"]
        solved["reconstruction_rmse"] = reconstruction["rmse"]
        if reconstruction["max_abs"] > reconstruction_max_abs_tol:
            solved["rejected_reason"] = "reconstruction_error"
            return None, solved

        parent = create_plane(
            plane_template,
            x=solved["px"],
            y=y_offset,
            z=solved["pz"],
            color=color,
            scale=1.0,
        )
        parent["data"]["rotation"]["x"] = 0.0
        parent["data"]["rotation"]["y"] = solved["alpha"]
        parent["data"]["rotation"]["z"] = 0.0
        parent["data"]["scale"]["x"] = solved["sx"]
        parent["data"]["scale"]["y"] = 1.0
        parent["data"]["scale"]["z"] = solved["sz"]
        # 親平面は三角形せん断のためだけに使うので色だけ完全透過にする。
        parent["data"]["colors"][0]["a"] = 0.0
        parent["data"]["line_color"]["a"] = 0.0
        parent["data"]["line_width"] = 0.0

        child = copy.deepcopy(triangle_template)
        child["data"]["position"]["x"] = 0.0
        child["data"]["position"]["y"] = 0.0
        child["data"]["position"]["z"] = 0.0
        child["data"]["rotation"]["x"] = 0.0
        child["data"]["rotation"]["y"] = solved["theta"]
        child["data"]["rotation"]["z"] = 0.0
        child["data"]["scale"]["x"] = solved.get("cx", solved["cs"])
        child["data"]["scale"]["y"] = child_y_scale
        child["data"]["scale"]["z"] = solved.get("cz", solved["cs"])
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
    def generate_text_scene_mesh(
        text,
        template_scene,
        plane_template,
        triangle_template,
        folder_key,
        folder_obj,
        grid_height=60,
        font_size=100,
        text_scale=0.25,
        spacing=None,
        color=None,
        font_path=None,
        flatten_segment_length=MeshRenderConfig.FLATTEN_SEGMENT_LENGTH_DEFAULT,
        outline_width=MeshRenderConfig.OUTLINE_WIDTH_DEFAULT,
        outline_color=None,
        outline_y_offset=MeshRenderConfig.OUTLINE_Y_OFFSET_DEFAULT,
        generation_metadata=None,
        lang="ja",
        progress_callback=None,
    ):
        """文字輪郭を三角形メッシュ化して3Dシーンを生成する。"""
        if spacing is None:
            spacing = text_scale * DotRenderConfig.SPACING_RATIO

        if progress_callback is not None:
            progress_callback(stage="prepare", current=0, total=1, note="start")

        font = load_font(font_size, font_path)
        img = text_to_image(text, font_size=font_size, font=font)
        grid_width = compute_grid_width_from_image(img, grid_height)
        preview_pixels = build_preview_from_image(img, grid_width, grid_height)

        if font_path is None:
            available_fonts = list_available_fonts()
            if not available_fonts:
                raise RuntimeError("No font file found for mesh generation")
            mesh_font_path = available_fonts[0]
        else:
            mesh_font_path = font_path

        missing_glyphs = MeshRenderPipeline.find_missing_glyphs(text, mesh_font_path)
        if missing_glyphs:
            raise MissingGlyphError(missing_glyphs[0])

        mesh_height = max(1e-5, spacing * grid_height)
        solve_mesh_height = max(
            mesh_height, MeshRenderConfig.SOLVER_REFERENCE_TEXT_HEIGHT
        )
        dot_alignment_targets = MeshRenderPipeline.build_dot_alignment_targets(
            text=text,
            font=font,
            font_size=font_size,
            img_width=img.width,
            grid_width=grid_width,
            grid_height=grid_height,
            spacing=spacing,
        )
        char_mesh_data = MeshRenderPipeline.build_text_mesh_characters(
            text,
            mesh_font_path,
            text_height=solve_mesh_height,
            flatten_segment_length=flatten_segment_length,
            progress_callback=progress_callback,
        )
        source_mesh_height = MeshRenderPipeline.compute_char_mesh_height(char_mesh_data)
        if source_mesh_height > 1e-9 and dot_alignment_targets["target_height"] > 1e-9:
            alignment_scale_factor = (
                dot_alignment_targets["target_height"] / source_mesh_height
            )
        else:
            alignment_scale_factor = 1.0

        (
            char_folders,
            plane_count,
            raw_plane_count,
            mesh_stats,
            triangle_status_records,
        ) = MeshRenderPipeline.build_mesh_char_folders(
            text,
            char_mesh_data,
            plane_template,
            triangle_template,
            folder_obj,
            color,
            progress_callback=progress_callback,
        )
        outline_effective_width = max(0.0, float(outline_width))
        outline_plane_count = 0
        outline_raw_plane_count = 0
        outline_mesh_stats = {
            "solve_failed_count": 0,
            "reconstruction_failed_count": 0,
            "reconstruction_tol": MeshRenderConfig.RECONSTRUCTION_MAX_ABS_TOL,
            "accepted_max_abs_error": 0.0,
            "accepted_rmse": 0.0,
        }
        if outline_color is None:
            outline_color = hex_to_color(MeshRenderConfig.OUTLINE_COLOR_HEX_DEFAULT)
        outline_color["a"] = 1.0
        if outline_effective_width > 0.0:
            if alignment_scale_factor > 1e-9:
                outline_reference_width = (
                    outline_effective_width / alignment_scale_factor
                )
            else:
                outline_reference_width = outline_effective_width
            outline_char_mesh_data = MeshRenderPipeline.build_outline_char_mesh_data(
                char_mesh_data, outline_reference_width
            )
            (
                outline_char_folders,
                outline_plane_count,
                outline_raw_plane_count,
                outline_mesh_stats,
                _,
            ) = MeshRenderPipeline.build_mesh_char_folders(
                text,
                outline_char_mesh_data,
                plane_template,
                triangle_template,
                folder_obj,
                outline_color,
                y_offset=outline_y_offset,
                triangulate_stage="triangulate_outline",
                solve_stage="solve_outline",
                progress_callback=progress_callback,
            )
        else:
            outline_char_mesh_data = []
            outline_char_folders = []
        outline_group_folder = None

        alignment_info = MeshRenderPipeline.align_mesh_output_to_dot(
            char_mesh_data,
            char_folders,
            triangle_status_records,
            dot_alignment_targets["target_centers_x"],
            dot_alignment_targets["target_height"],
            scale_factor_override=alignment_scale_factor,
        )
        if outline_char_mesh_data:
            MeshRenderPipeline.align_mesh_output_to_dot(
                outline_char_mesh_data,
                outline_char_folders,
                [],
                dot_alignment_targets["target_centers_x"],
                dot_alignment_targets["target_height"],
                scale_factor_override=alignment_info["scale_factor"],
            )
            if outline_char_folders and outline_plane_count > 0:
                outline_group_folder = copy.deepcopy(folder_obj)
                outline_group_folder["data"]["name"] = get_text(
                    "mesh_outline_folder_name", lang
                )
                outline_group_folder["data"]["treeState"] = 1
                outline_group_folder["data"]["child"] = outline_char_folders

        accepted_main = plane_count
        accepted_outline = outline_plane_count
        total_accepted = accepted_main + accepted_outline
        weighted_rmse = 0.0
        if total_accepted > 0:
            weighted_rmse = (
                mesh_stats["accepted_rmse"] * accepted_main
                + outline_mesh_stats["accepted_rmse"] * accepted_outline
            ) / total_accepted
        mesh_stats = {
            "solve_failed_count": mesh_stats["solve_failed_count"]
            + outline_mesh_stats["solve_failed_count"],
            "reconstruction_failed_count": mesh_stats["reconstruction_failed_count"]
            + outline_mesh_stats["reconstruction_failed_count"],
            "reconstruction_tol": mesh_stats["reconstruction_tol"],
            "accepted_max_abs_error": max(
                mesh_stats["accepted_max_abs_error"],
                outline_mesh_stats["accepted_max_abs_error"],
            ),
            "accepted_rmse": float(weighted_rmse),
        }
        plane_count += outline_plane_count
        raw_plane_count += outline_raw_plane_count
        mesh_stats["dot_align_scale_factor"] = alignment_info["scale_factor"]
        mesh_stats["dot_align_source_height"] = alignment_info["source_height"]
        mesh_stats["dot_align_target_height"] = alignment_info["target_height"]
        mesh_stats["solve_mesh_height"] = solve_mesh_height
        mesh_stats["requested_mesh_height"] = mesh_height
        mesh_stats["outline_width"] = outline_effective_width

        if progress_callback is not None:
            progress_callback(stage="preview", current=1, total=1, note="")

        triangulation_preview = MeshRenderPipeline.build_mesh_triangulation_preview(
            char_mesh_data, triangle_status_records
        )

        if progress_callback is not None:
            progress_callback(stage="scene", current=1, total=1, note="")

        scene = HoneycomeSceneData()
        scene.version = template_scene.version
        scene.dataVersion = template_scene.dataVersion
        scene.user_id = template_scene.user_id
        scene.data_id = str(uuid.uuid4())
        scene.title = f"{get_text('scene_title_prefix', lang)}{text}"
        scene.unknown_1 = template_scene.unknown_1
        scene.unknown_2 = template_scene.unknown_2
        scene.unknown_tail_1 = template_scene.unknown_tail_1
        scene.unknown_tail_2 = template_scene.unknown_tail_2
        scene.unknown_tail_3 = template_scene.unknown_tail_3
        scene.unknown_tail_4 = template_scene.unknown_tail_4
        scene.unknown_tail_5 = template_scene.unknown_tail_5
        scene.unknown_tail_6 = template_scene.unknown_tail_6
        scene.unknown_tail_7 = template_scene.unknown_tail_7
        scene.unknown_tail_8 = template_scene.unknown_tail_8
        scene.unknown_tail_9 = template_scene.unknown_tail_9
        scene.unknown_tail_10 = template_scene.unknown_tail_10
        scene.frame_filename = template_scene.frame_filename
        scene.unknown_tail_11 = template_scene.unknown_tail_11
        scene.footer_marker = template_scene.footer_marker
        scene.unknown_tail_extra = template_scene.unknown_tail_extra
        scene.image = template_scene.image

        new_folder = copy.deepcopy(folder_obj)
        new_folder["data"]["name"] = f"{get_text('folder_title_prefix', lang)}{text}"
        new_folder["data"]["treeState"] = 1
        scene_children = list(char_folders)
        if outline_group_folder is not None:
            scene_children.append(outline_group_folder)

        if generation_metadata:
            metadata_folder = build_metadata_folder(
                folder_obj, generation_metadata, lang
            )
            new_folder["data"]["child"] = [metadata_folder] + scene_children
        else:
            new_folder["data"]["child"] = scene_children

        scene.objects = {folder_key: new_folder}

        if progress_callback is not None:
            progress_callback(stage="done", current=1, total=1, note="")

        return (
            scene,
            img,
            preview_pixels,
            plane_count,
            plane_count,
            raw_plane_count,
            mesh_stats,
            triangulation_preview,
        )

    @staticmethod
    def default_advanced_settings():
        return {
            "flatten_segment_length": float(
                MeshRenderConfig.FLATTEN_SEGMENT_LENGTH_DEFAULT
            ),
            "outline_enabled": False,
            "outline_width": float(MeshRenderConfig.OUTLINE_WIDTH_DEFAULT),
            "outline_color_hex": MeshRenderConfig.OUTLINE_COLOR_HEX_DEFAULT,
            "stop_quality": float(MeshRenderConfig.TRIWILD_STOP_QUALITY),
            "edge_length_r": float(MeshRenderConfig.TRIWILD_EDGE_LENGTH_R),
            "target_edge_len_enabled": MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN > 0.0,
            "target_edge_len": (
                float(MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN)
                if MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN > 0.0
                else 0.04
            ),
        }

    @staticmethod
    def render_advanced_settings(lang):
        settings = {}
        settings["flatten_segment_length"] = st.slider(
            get_text("mesh_flatten_length_label", lang),
            min_value=2.0,
            max_value=100.0,
            value=float(MeshRenderConfig.FLATTEN_SEGMENT_LENGTH_DEFAULT),
            step=1.0,
            help=get_text("mesh_flatten_length_help", lang),
        )
        settings["outline_enabled"] = st.checkbox(
            get_text("mesh_outline_enable_label", lang),
            value=False,
            help=get_text("mesh_outline_enable_help", lang),
        )
        if settings["outline_enabled"]:
            settings["outline_width"] = st.slider(
                get_text("mesh_outline_width_label", lang),
                min_value=0.0,
                max_value=0.015,
                value=float(MeshRenderConfig.OUTLINE_WIDTH_DEFAULT),
                step=0.001,
                format="%.3f",
                help=get_text("mesh_outline_width_help", lang),
            )
            settings["outline_color_hex"] = st.color_picker(
                get_text("mesh_outline_color_label", lang),
                value=MeshRenderConfig.OUTLINE_COLOR_HEX_DEFAULT,
            )
        else:
            settings["outline_width"] = 0.0
            settings["outline_color_hex"] = MeshRenderConfig.OUTLINE_COLOR_HEX_DEFAULT
        settings["stop_quality"] = st.slider(
            get_text("mesh_stop_quality_label", lang),
            min_value=1.0,
            max_value=40.0,
            value=float(MeshRenderConfig.TRIWILD_STOP_QUALITY),
            step=1.0,
            help=get_text("mesh_stop_quality_help", lang),
        )
        settings["edge_length_r"] = st.slider(
            get_text("mesh_edge_length_r_label", lang),
            min_value=0.02,
            max_value=0.20,
            value=float(MeshRenderConfig.TRIWILD_EDGE_LENGTH_R),
            step=0.01,
            help=get_text("mesh_edge_length_r_help", lang),
        )
        settings["target_edge_len_enabled"] = st.checkbox(
            get_text("mesh_target_edge_len_enable", lang),
            value=MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN > 0.0,
        )
        if settings["target_edge_len_enabled"]:
            settings["target_edge_len"] = st.slider(
                get_text("mesh_target_edge_len_label", lang),
                min_value=0.005,
                max_value=0.10,
                value=(
                    float(MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN)
                    if MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN > 0.0
                    else 0.04
                ),
                step=0.005,
                help=get_text("mesh_target_edge_len_help", lang),
            )
        else:
            settings["target_edge_len"] = -1.0
        return settings

    @staticmethod
    def apply_triwild_settings(*, stop_quality, edge_length_r, target_edge_len):
        MeshRenderConfig.TRIWILD_STOP_QUALITY = float(stop_quality)
        MeshRenderConfig.TRIWILD_EDGE_LENGTH_R = float(edge_length_r)
        MeshRenderConfig.TRIWILD_TARGET_EDGE_LEN = float(target_edge_len)

    @staticmethod
    def build_generation_metadata(
        *,
        lang,
        selected_font,
        color_hex,
        color_alpha,
        text_height,
        plane_preset_key,
        light_cancel,
        flatten_segment_length,
        stop_quality,
        edge_length_r,
        target_edge_len,
        outline_enabled,
        outline_width,
        outline_color_hex,
    ):
        return {
            get_text("meta_font", lang): selected_font.name
            if selected_font
            else "default",
            get_text("meta_color", lang): color_hex,
            get_text("meta_alpha", lang): color_alpha,
            get_text("meta_text_height", lang): text_height,
            get_text("meta_resolution", lang): "-",
            get_text("meta_antialias", lang): "-",
            get_text("meta_aa_color", lang): "-",
            get_text("meta_merge_horizontal", lang): "-",
            get_text("meta_plane_size", lang): "-",
            get_text("meta_plane_type", lang): plane_preset_key,
            get_text("meta_light_influence", lang): light_cancel,
            get_text("meta_render_mode", lang): get_text("render_mode_mesh", lang),
            get_text("meta_mesh_flatten_length", lang): flatten_segment_length,
            get_text("meta_mesh_stop_quality", lang): stop_quality,
            get_text("meta_mesh_edge_length_r", lang): edge_length_r,
            get_text("meta_mesh_target_edge_len", lang): target_edge_len,
            get_text("meta_mesh_outline_enabled", lang): (
                "ON" if outline_enabled else "OFF"
            ),
            get_text("meta_mesh_outline_width", lang): outline_width,
            get_text("meta_mesh_outline_color", lang): outline_color_hex,
        }

    @staticmethod
    def build_progress_callback(lang):
        progress_bar = st.progress(0, text=f"{get_text('generating', lang)} 0%")
        progress_status = st.empty()
        progress_state = {"percent": -1, "status": ""}
        stage_labels = {
            "prepare": get_text("mesh_stage_prepare", lang),
            "glyph": get_text("mesh_stage_glyph", lang),
            "triangulate": get_text("mesh_stage_triangulate", lang),
            "solve": get_text("mesh_stage_solve", lang),
            "triangulate_outline": get_text("mesh_stage_outline_triangulate", lang),
            "solve_outline": get_text("mesh_stage_outline_solve", lang),
            "preview": get_text("mesh_stage_preview", lang),
            "scene": get_text("mesh_stage_scene", lang),
            "done": get_text("mesh_stage_done", lang),
        }

        def mesh_progress_callback(stage, current=None, total=None, note=""):
            if stage == "prepare":
                percent = 5
            elif stage == "glyph":
                ratio = 0.0
                if total and total > 0 and current is not None:
                    ratio = min(1.0, max(0.0, float(current) / float(total)))
                percent = int(round(10 + 20 * ratio))
            elif stage == "triangulate":
                ratio = 0.0
                if total and total > 0 and current is not None:
                    ratio = min(1.0, max(0.0, float(current) / float(total)))
                percent = int(round(30 + 12 * ratio))
            elif stage == "solve":
                ratio = 0.0
                if total and total > 0 and current is not None:
                    ratio = min(1.0, max(0.0, float(current) / float(total)))
                percent = int(round(42 + 36 * ratio))
            elif stage == "triangulate_outline":
                ratio = 0.0
                if total and total > 0 and current is not None:
                    ratio = min(1.0, max(0.0, float(current) / float(total)))
                percent = int(round(78 + 8 * ratio))
            elif stage == "solve_outline":
                ratio = 0.0
                if total and total > 0 and current is not None:
                    ratio = min(1.0, max(0.0, float(current) / float(total)))
                percent = int(round(86 + 8 * ratio))
            elif stage == "preview":
                percent = 96
            elif stage == "scene":
                percent = 98
            elif stage == "done":
                percent = 100
            else:
                percent = (
                    progress_state["percent"] if progress_state["percent"] >= 0 else 0
                )

            percent = max(0, min(100, int(percent)))
            if progress_state["percent"] >= 0:
                percent = max(progress_state["percent"], percent)
            stage_label = stage_labels.get(stage, stage)
            status_text = stage_label
            if total and total > 0 and current is not None:
                status_text = f"{status_text} ({int(current)}/{int(total)})"
            if note:
                status_text = f"{status_text} [{note}]"

            if percent != progress_state["percent"]:
                progress_bar.progress(
                    percent, text=f"{get_text('generating', lang)} {percent}%"
                )
                progress_state["percent"] = percent
            if status_text != progress_state["status"]:
                progress_status.caption(status_text)
                progress_state["status"] = status_text

        return mesh_progress_callback

    @staticmethod
    def generate_for_main(
        *,
        text_input,
        template_scene,
        plane_template,
        triangle_template,
        folder_key,
        folder_obj,
        layout,
        font_size,
        color,
        selected_font,
        flatten_segment_length,
        stop_quality,
        edge_length_r,
        target_edge_len,
        outline_width,
        outline_color_hex,
        generation_metadata,
        lang,
    ):
        MeshRenderPipeline.apply_triwild_settings(
            stop_quality=stop_quality,
            edge_length_r=edge_length_r,
            target_edge_len=target_edge_len,
        )
        progress_callback = MeshRenderPipeline.build_progress_callback(lang)
        outline_color = hex_to_color(outline_color_hex)
        (
            scene,
            original_img,
            preview_pixels,
            plane_count,
            plane_count_horizontal,
            raw_plane_count,
            mesh_stats,
            triangulation_preview,
        ) = MeshRenderPipeline.generate_scene(
            text=text_input,
            template_scene=template_scene,
            plane_template=plane_template,
            triangle_template=triangle_template,
            folder_key=folder_key,
            folder_obj=folder_obj,
            grid_height=layout["grid_height"],
            font_size=font_size,
            text_scale=layout["text_scale"],
            spacing=layout["spacing"],
            color=color,
            font_path=selected_font,
            flatten_segment_length=flatten_segment_length,
            outline_width=outline_width,
            outline_color=outline_color,
            generation_metadata=generation_metadata,
            lang=lang,
            progress_callback=progress_callback,
        )
        return {
            "scene": scene,
            "original_img": original_img,
            "preview_pixels": preview_pixels,
            "plane_count": plane_count,
            "plane_count_horizontal": plane_count_horizontal,
            "raw_plane_count": raw_plane_count,
            "mesh_stats": mesh_stats,
            "triangulation_preview": triangulation_preview,
        }

    @staticmethod
    def render_generation_feedback(mesh_stats, lang):
        if not mesh_stats:
            return
        if mesh_stats["solve_failed_count"] > 0:
            st.warning(
                get_text("mesh_solver_skip_warn", lang).format(
                    failed=mesh_stats["solve_failed_count"]
                )
            )
        if mesh_stats["reconstruction_failed_count"] > 0:
            st.warning(
                get_text("mesh_reconstruction_skip_warn", lang).format(
                    failed=mesh_stats["reconstruction_failed_count"]
                )
            )
        st.caption(
            get_text("mesh_reconstruction_info", lang).format(
                max_err=mesh_stats["accepted_max_abs_error"],
                rmse=mesh_stats["accepted_rmse"],
                tol=mesh_stats["reconstruction_tol"],
            )
        )

    @staticmethod
    def render_triangulation_section(triangulation_preview, lang):
        st.subheader(f"🔺 {get_text('mesh_triangulation_title', lang)}")
        if triangulation_preview is None:
            st.caption(get_text("mesh_triangulation_empty", lang))
        else:
            st.image(triangulation_preview, width="stretch")

    build_triangulation_preview = build_mesh_triangulation_preview
    generate_scene = generate_text_scene_mesh


def main():
    # メイン UI
    try:
        # ページ設定
        title = get_text("title", "ja")
        st.set_page_config(page_title=title, page_icon="✨", layout="wide")

        lang = st.session_state.get("lang", "ja")

        st.title(f"✨ {get_text('title', lang)}")
        st.markdown(get_text("subtitle", lang))

        # セッション状態の初期化
        if "template_scene" not in st.session_state:
            st.session_state.template_scene = None
            st.session_state.plane_template = None
            st.session_state.folder_key = None
            st.session_state.folder_obj = None

        # テンプレート読み込み
        template_scene, plane_template, folder_key, folder_obj = load_template()

        if template_scene is None:
            st.stop()

        with st.expander(f"❓ {get_text('qa_title', lang)}", expanded=False):
            st.markdown(get_text("qa_content", lang).strip(), unsafe_allow_html=True)

        # メインページでパラメータ設定
        st.header(f"⚙️ {get_text('param_settings', lang)}")

        # テキスト入力
        text_input = st.text_input(
            f"📝 {get_text('text_input', lang)}",
            value="",
            max_chars=50,
            placeholder=get_text("text_placeholder", lang),
        )
        available_fonts = list_available_fonts()
        selected_font = select_font_option(
            available_fonts, "MPLUSRounded1c-Regular.ttf"
        )
        render_mode = st.selectbox(
            f"✨️{get_text('render_mode_label', lang)} **NEW** ✨️",
            options=[
                get_text("render_mode_dot", lang),
                get_text("render_mode_mesh", lang),
            ],
            index=0,
            help=get_text("render_mode_help", lang),
        )
        render_mode_key = (
            "mesh" if render_mode == get_text("render_mode_mesh", lang) else "dot"
        )

        # 色設定
        color_hex = st.color_picker(get_text("color_label", lang), value="#FFFFFF")

        # 文字の大きさ（縦幅）
        text_height = st.slider(
            f"📏 {get_text('text_size_title', lang)}",
            min_value=0.01,
            max_value=2.0,
            value=0.5,
            step=0.01,
        )
        st.caption(get_text("text_size_help", lang))
        with st.expander(get_text("text_size_example", lang), expanded=False):
            st.markdown("![font size example](https://i.imgur.com/y04URY3.jpeg)")

        st.markdown("---")

        # 詳細設定（エキスパンダーで折りたたみ）
        font_size = DotRenderPipeline.Config.FONT_SIZE
        dot_settings = DotRenderPipeline.default_advanced_settings()
        mesh_settings = MeshRenderPipeline.default_advanced_settings()
        with st.expander(f"🎨 {get_text('advanced_settings', lang)}", expanded=False):
            match render_mode_key:
                case "mesh":
                    mesh_settings = MeshRenderPipeline.render_advanced_settings(lang)
                case "dot":
                    dot_settings = DotRenderPipeline.render_advanced_settings(lang)
            if render_mode_key == "mesh":
                plane_preset = st.selectbox(
                    get_text("triangle_type_label", lang),
                    options=[get_text("triangle_map", lang), get_text("triangle_chara", lang)],
                    index=0,
                    help=get_text("triangle_type_help", lang),
                )
            else:
                plane_preset = st.selectbox(
                    get_text("plane_type_label", lang),
                    options=[get_text("plane_map", lang), get_text("plane_chara", lang)],
                    index=0,
                    help=get_text("plane_type_help", lang),
                )
            is_map_preset = plane_preset in (
                get_text("plane_map", lang),
                get_text("triangle_map", lang),
            )
            if is_map_preset:
                color_alpha = st.slider(
                    get_text("alpha_label", lang),
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.05,
                )
            else:
                color_alpha = 1.0
            light_cancel = st.slider(
                get_text("light_cancel_label", lang),
                min_value=0.0,
                max_value=1.0,
                value=1.0,
                step=0.05,
                help=get_text("light_cancel_help", lang),
            )

        plane_size_factor_for_layout = 1.0
        match render_mode_key:
            case "dot":
                plane_size_factor_for_layout = dot_settings["plane_size_factor"]

        layout = DotRenderPipeline.compute_layout(
            text_input,
            dot_settings["per_char_resolution"],
            text_height,
            plane_size_factor_for_layout,
        )

        # 生成ボタン
        generate_button = st.button(
            f"🚀 {get_text('generate_button', lang)}", type="primary", width="stretch"
        )

        # 生成処理
        if generate_button:
            if not text_input:
                st.error(get_text("error_no_text", lang))
            else:
                try:
                    color = hex_to_color(color_hex)
                    color["a"] = color_alpha
                    # plane_preset は言語によって変わるので、インデックスで判定
                    is_map = plane_preset in (
                        get_text("plane_map", lang),
                        get_text("triangle_map", lang),
                    )
                    plane_preset_key = "平面(マップ)" if is_map else "平面(キャラ)"
                    triangle_preset_key = "三角形(マップ)" if is_map else "三角形(キャラ)"
                    plane_settings = PLANE_PRESETS[plane_preset_key]
                    triangle_settings = TRIANGLE_PRESETS[triangle_preset_key]
                    resolved_plane_template = {
                        **plane_template,
                        "data": {
                            **plane_template["data"],
                            "category": plane_settings["category"],
                            "no": plane_settings["no"],
                            "light_cancel": 1.0 - light_cancel,
                        },
                    }

                    match render_mode_key:
                        case "mesh":
                            generation_metadata = (
                                MeshRenderPipeline.build_generation_metadata(
                                    lang=lang,
                                    selected_font=selected_font,
                                    color_hex=color_hex,
                                    color_alpha=color_alpha,
                                    text_height=text_height,
                                    plane_preset_key=triangle_preset_key,
                                    light_cancel=light_cancel,
                                    flatten_segment_length=mesh_settings[
                                        "flatten_segment_length"
                                    ],
                                    stop_quality=mesh_settings["stop_quality"],
                                    edge_length_r=mesh_settings["edge_length_r"],
                                    target_edge_len=mesh_settings["target_edge_len"],
                                    outline_enabled=mesh_settings["outline_enabled"],
                                    outline_width=mesh_settings["outline_width"],
                                    outline_color_hex=mesh_settings[
                                        "outline_color_hex"
                                    ],
                                )
                            )
                            result = MeshRenderPipeline.generate_for_main(
                                text_input=text_input,
                                template_scene=template_scene,
                                plane_template=resolved_plane_template,
                                triangle_template={
                                    **plane_template,
                                    "data": {
                                        **plane_template["data"],
                                        "category": triangle_settings["category"],
                                        "no": triangle_settings["no"],
                                        "light_cancel": 1.0 - light_cancel,
                                    },
                                },
                                folder_key=folder_key,
                                folder_obj=folder_obj,
                                layout=layout,
                                font_size=font_size,
                                color=color,
                                selected_font=selected_font,
                                flatten_segment_length=mesh_settings[
                                    "flatten_segment_length"
                                ],
                                stop_quality=mesh_settings["stop_quality"],
                                edge_length_r=mesh_settings["edge_length_r"],
                                target_edge_len=mesh_settings["target_edge_len"],
                                outline_width=mesh_settings["outline_width"],
                                outline_color_hex=mesh_settings["outline_color_hex"],
                                generation_metadata=generation_metadata,
                                lang=lang,
                            )
                            MeshRenderPipeline.render_generation_feedback(
                                result["mesh_stats"], lang
                            )
                        case "dot":
                            generation_metadata = (
                                DotRenderPipeline.build_generation_metadata(
                                    lang=lang,
                                    selected_font=selected_font,
                                    color_hex=color_hex,
                                    color_alpha=color_alpha,
                                    text_height=text_height,
                                    plane_preset_key=plane_preset_key,
                                    light_cancel=light_cancel,
                                    dot_settings=dot_settings,
                                )
                            )
                            result = DotRenderPipeline.generate_for_main(
                                text_input=text_input,
                                template_scene=template_scene,
                                plane_template=resolved_plane_template,
                                folder_key=folder_key,
                                folder_obj=folder_obj,
                                layout=layout,
                                font_size=font_size,
                                color=color,
                                selected_font=selected_font,
                                dot_settings=dot_settings,
                                generation_metadata=generation_metadata,
                                lang=lang,
                            )

                    scene = result["scene"]
                    original_img = result["original_img"]
                    preview_pixels = result["preview_pixels"]
                    plane_count = result["plane_count"]
                    plane_count_horizontal = result["plane_count_horizontal"]
                    raw_plane_count = result["raw_plane_count"]
                    mesh_stats = result["mesh_stats"]
                    triangulation_preview = result["triangulation_preview"]

                    st.success(
                        f"✅ {get_text('success_generate', lang).format(count=plane_count)}"
                    )

                    match render_mode_key:
                        case "dot":
                            render_preview(
                                original_img,
                                preview_pixels,
                                preview_pixels.shape[1],
                                layout["grid_height"],
                                lang,
                            )
                    render_scene_info(
                        scene,
                        plane_count,
                        plane_count_horizontal,
                        raw_plane_count,
                        lang,
                        is_mesh_mode=render_mode_key == "mesh",
                        mesh_stats=mesh_stats,
                    )
                    match render_mode_key:
                        case "mesh":
                            MeshRenderPipeline.render_triangulation_section(
                                triangulation_preview, lang
                            )

                    # ダウンロードボタン
                    filename = build_scene_filename(text_input, render_mode_key)

                    preview_buf = io.BytesIO()
                    Image.fromarray(preview_pixels).save(preview_buf, format="PNG")
                    scene.image = preview_buf.getvalue()

                    scene_bytes = bytes(scene)

                    st.download_button(
                        label=f"💾 {get_text('download_button', lang)}",
                        data=scene_bytes,
                        file_name=filename,
                        mime="image/png",
                        type="primary",
                        width="stretch",
                    )

                except MissingGlyphError as e:
                    st.error(
                        get_text("mesh_missing_glyph_error", lang).format(
                            error_moji=e.error_moji
                        )
                    )
                except Exception as e:
                    st.error(f"{get_text('error_occurred', lang)} {str(e)}")
                    st.exception(e)

    except Exception as e:
        st.error(f"{get_text('error_init', lang)} {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
