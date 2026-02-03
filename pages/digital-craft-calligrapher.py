import copy
import io
import uuid
from pathlib import Path

import numpy as np
import streamlit as st
from kkloader import HoneycomeSceneData
from PIL import Image, ImageDraw, ImageFont

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "デジクラカリグラファー",
        "subtitle": "テキストをデジタルクラフトのシーン内で平面を並べて再現します。ダウンロードしたシーンをインポートして使えます。",
        "qa_title": "Q&A",
        "qa_content": """
#### 文字を入れると重い！

**アンチエイリアス** をOFFにし、 **横方向の平面結合** を有効にすると最も平面の数が小さくなります。

他にも **一文字あたり細かさ**を下げることで平面数が減りますが、文字の解像度が下がるので可読性も悪くなってしまいます。
どうしても平面数を下げたければこのパラメータを調整していい塩梅を探してみてください。

#### どの設定で文字を作ったか忘れた！

シーン内に生成された **「文字情報」フォルダ** の中に、使用したパラメータが保存されています。
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
        "param_settings": "パラメータ設定",
        "text_input": "テキスト",
        "text_placeholder": "ここにテキストを入力",
        "font_label": "フォント",
        "color_label": "色",
        "alpha_label": "色の透明度(マップ平面のみ有効)",
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
        "plane_type_help": "マップの方の平面を使うか、キャラの方の平面を使うかを設定します。マップライトとキャラライトのどちらのライトに影響されるかが決まります。",
        "plane_map": "平面(マップ)",
        "plane_chara": "平面(キャラ)",
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
        "subtitle": "Recreate text using planes arranged in a Digital Craft scene. Import the downloaded scene to use.",
        "qa_title": "Q&A",
        "qa_content": """
#### It gets heavy when I add text!

Turn **Antialiasing** OFF and enable **Horizontal plane merging** to minimize the number of planes.

You can also reduce plane count by lowering **Resolution per character**, but this decreases text resolution and readability.
If you must reduce plane count, adjust this parameter to find a good balance.

#### I forgot which settings I used!

The parameters are saved inside the **"Text Info"** folder in the generated scene.
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
        "param_settings": "Parameter Settings",
        "text_input": "Text",
        "text_placeholder": "Enter text here",
        "font_label": "Font",
        "color_label": "Color",
        "alpha_label": "Color transparency (Map plane only)",
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
        "plane_type_help": "Choose whether to use map planes or character planes. This determines which light type affects them.",
        "plane_map": "Plane (Map)",
        "plane_chara": "Plane (Character)",
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


SPACING_RATIO = 0.2
FONT_SIZE = 200
FONT_DIR = Path(__file__).parent / "digital-craft-calligrapher-data"
CHAR_CANVAS_PADDING = 5
PLANE_PRESETS = {
    "平面(マップ)": {"category": 0, "no": 215},
    "平面(キャラ)": {"category": 1, "no": 290},
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
    }
    note = impressions.get(font_path.name)
    if note:
        return f"{font_path.name} ({note})"
    return font_path.name


def compute_canvas_height(text, font, padding):
    ascent, descent = font.getmetrics()
    return (ascent + descent) + padding * 2


def compute_canvas_size(text, font, padding):
    max_char_width = 0
    dummy_img = Image.new("L", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    for char in text:
        bbox = dummy_draw.textbbox((0, 0), char, font=font, anchor="ls")
        max_char_width = max(max_char_width, bbox[2] - bbox[0])
    max_char_width = max(1, max_char_width)
    return max_char_width + padding * 2, compute_canvas_height(text, font, padding)


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


def compute_layout(text_input, per_char_resolution, text_height, plane_size_factor):
    grid_width = max(1, per_char_resolution * max(1, len(text_input)))
    grid_height = per_char_resolution
    pixel_size = text_height / per_char_resolution
    text_scale = (pixel_size / SPACING_RATIO) * plane_size_factor
    spacing = pixel_size
    return {
        "grid_width": grid_width,
        "grid_height": grid_height,
        "pixel_size": pixel_size,
        "text_scale": text_scale,
        "spacing": spacing,
    }


def measure_text_advance(draw, font, value):
    """PILのメトリクスから文字列のアドバンス幅を取得する。"""
    if hasattr(draw, "textlength"):
        return draw.textlength(value, font=font)
    if hasattr(font, "getlength"):
        return font.getlength(value)
    bbox = draw.textbbox((0, 0), value, font=font, anchor="ls")
    return bbox[2] - bbox[0]


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
        advance = measure_text_advance(dummy_draw, font, text[:index])
        char_bbox = dummy_draw.textbbox((advance, 0), char, font=font, anchor="ls")
        if char_bbox is None or (char_bbox[2] - char_bbox[0]) == 0:
            char_advance = measure_text_advance(dummy_draw, font, char)
            center = advance + char_advance / 2
        else:
            center = (char_bbox[0] + char_bbox[2]) / 2
        center_image = x_offset + center
        centers.append(center_image / max(1, img_width))
    return centers


def compute_grid_width_from_image(img, grid_height):
    """元の画像の縦横比を維持したまま、グリッド幅を算出する。"""
    return max(1, int(round(img.width * grid_height / img.height)))


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


def build_preview_from_image(img, grid_width, grid_height):
    """元のPIL画像をプレビューサイズに縮小する。"""
    return resample_image(img, grid_width, grid_height)


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
        planes, planes_horizontal = pixels_to_planes(
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
    scene, plane_count, plane_count_horizontal, raw_plane_count, lang="ja"
):
    st.subheader(f"📝 {get_text('scene_info_title', lang)}")
    info_col1, info_col2, info_col3 = st.columns(3)
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


def build_scene_filename(text_input):
    safe_text = "".join(c if c.isalnum() else "_" for c in text_input)
    return f"digitalcraft_scene_text_{safe_text}.png"


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
    "line_width": 1.0,
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


# ============================
# Streamlit App
# ============================
# ページ設定
title = get_text("title", "ja")
st.set_page_config(page_title=title, page_icon="✨", layout="wide")

# サイドバーに言語選択を配置
with st.sidebar:
    lang = st.selectbox(
        "Language / 言語",
        options=["ja", "en"],
        format_func=lambda x: "日本語" if x == "ja" else "English",
        index=0,
    )

st.title(f"✨ {get_text('title', lang)}")
st.markdown(get_text("subtitle", lang))


# セッション状態の初期化
if "template_scene" not in st.session_state:
    st.session_state.template_scene = None
    st.session_state.plane_template = None
    st.session_state.folder_key = None
    st.session_state.folder_obj = None


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
        except Exception:
            font = None
    if font is None:
        for candidate in list_available_fonts():
            try:
                font = ImageFont.truetype(str(candidate), font_size)
                break
            except Exception:
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
    return plane


def hex_to_color(hex_color):
    """#RRGGBB to color dict with 0-1 floats."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return {"r": r, "g": g, "b": b, "a": 1.0}


def blend_colors(fg_color, bg_color, pixel_value):
    """Blend foreground and background using grayscale brightness."""
    t = pixel_value / 255.0
    return {
        "r": bg_color["r"] * (1.0 - t) + fg_color["r"] * t,
        "g": bg_color["g"] * (1.0 - t) + fg_color["g"] * t,
        "b": bg_color["b"] * (1.0 - t) + fg_color["b"] * t,
        "a": 1.0,
    }


def resolve_pixel_color(pixel_value, fg_color, bg_color, antialias):
    """Return per-pixel color based on antialias setting."""
    if not antialias:
        return fg_color
    return blend_colors(fg_color, bg_color, pixel_value)


def colors_close(color_a, color_b, threshold):
    if threshold <= 0:
        return color_a == color_b
    for channel in ("r", "g", "b"):
        if abs(color_a[channel] - color_b[channel]) > threshold:
            return False
    return True


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
                shaded_color = resolve_pixel_color(
                    pixel_value, color, edge_color, antialias
                )
                if run_start is None:
                    run_start = col
                    run_end = col
                    run_color = shaded_color
                elif merge_horizontal and colors_close(
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
            add_plane(run["start"], run["end"], run["color"], run["row"], run["row"])
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
        spacing = text_scale * SPACING_RATIO
    plane_scale = text_scale

    # 1. テキストを画像に変換（プレビュー用）
    font = load_font(font_size, font_path)
    img = text_to_image(text, font_size=font_size, font=font)
    canvas_width, canvas_height = compute_canvas_size(text, font, CHAR_CANVAS_PADDING)

    # 2. 1文字ごとに平面を生成
    per_char_resolution = grid_height
    grid_width = compute_grid_width_from_image(img, per_char_resolution)

    # グリッド幅に合わせてテキスト全体の左右スケールを揃える。
    global_start_x = -((grid_width - 1) * spacing) / 2
    global_start_z = -((grid_height - 1) * spacing) / 2
    effective_threshold = 1 if antialias else 128

    # PILの文字中心比率を使って、各文字の配置基準を決める。
    desired_centers = compute_text_center_ratios(text, font, img.width)
    (
        char_pixels_list,
        char_center_cols,
        raw_plane_count,
    ) = build_char_pixels(
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
    char_folders, plane_count, plane_count_horizontal = build_char_folders(
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
        metadata_folder = build_metadata_folder(folder_obj, generation_metadata, lang)
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


# メイン UI
try:
    # テンプレート読み込み
    template_scene, plane_template, folder_key, folder_obj = load_template()

    if template_scene is None:
        st.stop()

    with st.expander(f"❓ {get_text('qa_title', lang)}", expanded=False):
        st.markdown(get_text("qa_content", lang).strip())

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
    selected_font = select_font_option(available_fonts, "MPLUSRounded1c-Regular.ttf")

    # 色設定
    color_hex = st.color_picker(get_text("color_label", lang), value="#FFFFFF")
    color_alpha = st.slider(
        get_text("alpha_label", lang),
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
    )
    st.markdown("---")

    # 文字の大きさ（縦幅）
    st.subheader(f"📏 {get_text('text_size_title', lang)}")
    st.text(get_text("text_size_help", lang))

    with st.expander(get_text("text_size_example", lang), expanded=False):
        st.markdown("![font size example](https://i.imgur.com/y04URY3.jpeg)")

    text_height = st.slider(
        get_text("height_label", lang),
        min_value=0.01,
        max_value=2.0,
        value=0.5,
        step=0.01,
    )

    st.markdown("---")

    # 詳細設定（エキスパンダーで折りたたみ）
    with st.expander(f"🎨 {get_text('advanced_settings', lang)}", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            # 1文字あたりの解像度設定
            per_char_resolution = st.slider(
                get_text("resolution_label", lang),
                min_value=10,
                max_value=200,
                value=100,
                step=5,
                help=get_text("resolution_help", lang),
            )
            font_size = FONT_SIZE

        with col2:
            threshold = 1

        antialias = st.checkbox(get_text("antialias_label", lang), value=False)
        edge_color_hex = st.color_picker(
            get_text("antialias_color_label", lang), value="#000000"
        )
        merge_horizontal = st.checkbox(
            get_text("merge_horizontal_label", lang),
            value=True,
            help=get_text("merge_horizontal_help", lang),
        )
        merge_color_threshold = 0.0
        plane_size_factor = st.slider(
            get_text("plane_size_label", lang),
            min_value=0.5,
            max_value=1.0,
            value=1.0,
            step=0.05,
            help=get_text("plane_size_help", lang),
        )
        plane_preset = st.selectbox(
            get_text("plane_type_label", lang),
            options=[get_text("plane_map", lang), get_text("plane_chara", lang)],
            index=0,
            help=get_text("plane_type_help", lang),
        )
        light_cancel = st.slider(
            get_text("light_cancel_label", lang),
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.05,
            help=get_text("light_cancel_help", lang),
        )

    layout = compute_layout(
        text_input, per_char_resolution, text_height, plane_size_factor
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
            with st.spinner(get_text("generating", lang)):
                try:
                    color = hex_to_color(color_hex)
                    color["a"] = color_alpha
                    edge_color = hex_to_color(edge_color_hex)
                    # plane_preset は言語によって変わるので、インデックスで判定
                    plane_preset_key = (
                        "平面(マップ)"
                        if plane_preset == get_text("plane_map", lang)
                        else "平面(キャラ)"
                    )
                    plane_settings = PLANE_PRESETS[plane_preset_key]

                    # 再現用メタデータを構築
                    generation_metadata = {
                        get_text("meta_font", lang): (
                            selected_font.name if selected_font else "default"
                        ),
                        get_text("meta_color", lang): color_hex,
                        get_text("meta_alpha", lang): color_alpha,
                        get_text("meta_text_height", lang): text_height,
                        get_text("meta_resolution", lang): per_char_resolution,
                        get_text("meta_antialias", lang): "ON" if antialias else "OFF",
                        get_text("meta_aa_color", lang): edge_color_hex,
                        get_text("meta_merge_horizontal", lang): (
                            "ON" if merge_horizontal else "OFF"
                        ),
                        get_text("meta_plane_size", lang): plane_size_factor,
                        get_text("meta_plane_type", lang): plane_preset_key,
                        get_text("meta_light_influence", lang): light_cancel,
                    }

                    (
                        scene,
                        original_img,
                        preview_pixels,
                        plane_count,
                        plane_count_horizontal,
                        raw_plane_count,
                    ) = generate_text_scene(
                        text=text_input,
                        template_scene=template_scene,
                        plane_template={
                            **plane_template,
                            "data": {
                                **plane_template["data"],
                                "category": plane_settings["category"],
                                "no": plane_settings["no"],
                                "light_cancel": 1.0 - light_cancel,
                            },
                        },
                        folder_key=folder_key,
                        folder_obj=folder_obj,
                        grid_height=layout["grid_height"],
                        font_size=font_size,
                        text_scale=layout["text_scale"],
                        spacing=layout["spacing"],
                        threshold=threshold,
                        color=color,
                        edge_color=edge_color,
                        antialias=antialias,
                        font_path=selected_font,
                        merge_horizontal=merge_horizontal,
                        merge_color_threshold=merge_color_threshold,
                        generation_metadata=generation_metadata,
                        lang=lang,
                    )

                    st.success(
                        f"✅ {get_text('success_generate', lang).format(count=plane_count)}"
                    )

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
                    )

                    # ダウンロードボタン
                    filename = build_scene_filename(text_input)

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

                except Exception as e:
                    st.error(f"{get_text('error_occurred', lang)} {str(e)}")
                    st.exception(e)


except Exception as e:
    st.error(f"{get_text('error_init', lang)} {str(e)}")
    st.exception(e)
