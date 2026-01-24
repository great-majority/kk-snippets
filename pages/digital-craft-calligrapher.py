import copy
import io
import json
import struct
import textwrap
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Dict, Union

import numpy as np
import streamlit as st
from kkloader.funcs import get_png, load_string, load_type, write_string
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
""",
        "param_settings": "パラメータ設定",
        "text_input": "テキスト",
        "text_placeholder": "ここにテキストを入力",
        "font_label": "フォント",
        "color_label": "色",
        "alpha_label": "色の透明度(マップ平面のみ有効)",
        "text_size_title": "文字の大きさ",
        "text_size_help": "文字の縦幅。0.1で一文字がキャラの手のひらほどの大きさ、1.7でキャラの身長ほどの大きさになります。",
        "height_label": "縦幅",
        "advanced_settings": "詳細設定",
        "resolution_label": "一文字あたり細かさ",
        "resolution_help": "文字のピクセルの細かさ。この値を大きくするほど文字が綺麗になる一方、シーンが重くなります",
        "antialias_label": "アンチエイリアスを使う",
        "antialias_color_label": "アンチエイリアスの色",
        "merge_horizontal_label": "横方向の平面結合",
        "merge_horizontal_help": "横方向に色が一致していれば長方形で代替し平面の数を大幅に減らします。1Pixelごといじりたいのであればこのチェックを外してください。",
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
        "preview_title": "プレビュー",
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
""",
        "param_settings": "Parameter Settings",
        "text_input": "Text",
        "text_placeholder": "Enter text here",
        "font_label": "Font",
        "color_label": "Color",
        "alpha_label": "Color transparency (Map plane only)",
        "text_size_title": "Text Size",
        "text_size_help": "Text height. 0.1 is about the size of a character's palm, 1.7 is about character height.",
        "height_label": "Height",
        "advanced_settings": "Advanced Settings",
        "resolution_label": "Resolution per character",
        "resolution_help": "Pixel fineness of text. Higher values produce cleaner text but heavier scenes",
        "antialias_label": "Use antialiasing",
        "antialias_color_label": "Antialiasing color",
        "merge_horizontal_label": "Horizontal plane merging",
        "merge_horizontal_help": "Replaces matching horizontal colors with rectangles to greatly reduce plane count. Uncheck to edit per pixel.",
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
        "preview_title": "Preview",
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
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


SPACING_RATIO = 0.2
FONT_SIZE = 200
FONT_DIR = Path(__file__).parent / "digital-craft-calligrapher-data"
CHAR_CANVAS_PADDING = 5
CHAR_GAP_PX = 2
PLANE_PRESETS = {
    "平面(マップ)": {"group": 0, "category": 0, "no": 215},
    "平面(キャラ)": {"group": 1, "category": 0, "no": 290},
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


def render_scene_info(scene, plane_count, raw_plane_count, lang="ja"):
    st.subheader(f"📝 {get_text('scene_info_title', lang)}")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.metric(get_text("plane_count", lang), f"{plane_count}")
    with info_col2:
        if raw_plane_count is not None:
            delta = raw_plane_count - plane_count
            delta_text = f"-{delta}" if delta >= 0 else f"+{abs(delta)}"
            st.metric(
                get_text("plane_reduction", lang),
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
    "unknown_2": 32,
    "unknown_3": b"#\\d7\xf1l\xf3\xdb?v\xe0X\xf8\x1cJ\xae\xfc\x10I\x96\x15k*P\xbf*u\x91.Yr\xbe",
    "unknown_tail": b"0\x00\x00\x00\xee\xaa|\xcfZ\xdc\x97>\x14A\xf6\xfagp'\x84PB\xd3ze_7\xba\xad\xb5\x15\xa8O\xc3F\xd3"
    b"\x18\x8b\x13&i0\xc9\xa2\x94?\xdcm\\7\x05\xdc\xe0\x00\x00\x00\x9a\xd9\x0e\x878|>=k\x1e\x930"
    b"S\xe9\xdf\x14e\xf3\x00\xb3b?\xcd\xf5\xa1UW{\x01\x98\xd3ob\xbd\x87\xba\xbf\xa3p\xfd.%\xaf'"
    b"\xa3\x9d\x10>\x81s\xf2\xc7\x8f\x88\x8b.\x96e%\xc8\x1ba;\x0f[\x1e\xa8\xa2\xdd\xf6(\xea\xeaV\xe9\xa6"
    b"\x0f\xb8\x15^\xde!X\x8e\xb0\x81\xfb\x87d\x89\x9d\xea\x14R\x988\xb7\xa2s\xba\x0e\xf1x2\xed\xd5U\xf6"
    b"D\x9bJ\x82\xb9L\x8c\xed\xc3B\xd5\xc25\xe2%Z\xba@sN\x9f/\xac\x15\xedj\xabj\xe7\xed\xc2\xec"
    b"\xdd\xb83\x11l\xf9?\x95B\xdf\r\x15rb<|V\xe7k~\xf1<Q,*@\tD\x97\x01,s\x1d\x8c\xfe!a\t\xfb6\\:2\xfd"
    b"7\x00Q\x87\x05\x94*@kk!y\x05\xbf5\xef\x0e's\x03\xf5\t{wTa\xeb\xd65\xbc\xd9\xef\xb1\xabQ\xc2"
    b"I\xec\x1a50\x00\x00\x00\xf8\xe8\x14J\x87\xe2\x8f8v\x07q\x1d\xf1?v\xf14(% \xea\xcb\xaex=lAln\x01{C"
    b"\xfd\xe9\xb4\xe4\x8e\xfd\x96\xd7;\x85\xff-fr\x16\xfe`\x00\x00\x00\xa0\x15a\t\x08\x07J\x0c\xac\xe0C>"
    b"i\x99\xec\xe0y\xd1[MJ\x05\x0c\xa2\xfc\x96\xf6\xee&\x0c\xe1\x00)r)\xb9\xdf\xaa\xb4nV\x10\x0b\xec"
    b"\xb6t\xa1\xd3\x95AP\xc2\xf0\x8aBd\x83\xd4\xb4p\xf5B\xce\xb7;k\xed\xf6\xfa\xbc\x1eJF\xcbt1\x87=\xebz"
    b"\xac\xec^\xf7\x15 8i:QUh\x90!1v0\x00\x00\x00`)g\xf9\x1cN\x99\xfb\xc1\x9e\x80\x19\x0c\x96\x16\xe0)t>,"
    b"\xc8\xc2\xd4t\x89\x98\x91\xd1\xd1\xc4\xd8\xbc\xdf\x92\xcf*b\x0c\x1d\xbaM\xd1\x8a\xf4\x12\x87!\x18"
    b"@\x00\x00\x00\xaa\xf3\xff\xfb\xf4S\x80R\xda]7\x99\xdeig\xc6&\xd4\x187\x80\n\x80\xcf\x80\xd6Ch"
    b"\x9amy\xb3X\x18\x88;\xce\xdb\x11&`\x89\x8c\x1c\xb7\x8a\xd8\xfe\x1e\x17\xa9l\x1f\xe4#\xb7"
    b"\xf4\xdc\xc6kh\xaf\x9aB\x10\x00\x00\x00b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE"
    b"\x10\x00\x00\x00b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE\x10\x00\x00\x00\xf4+\x98\x84"
    b'\xde\xc3-\x15\xb0M<\xe2!"\xd5\xa5\x10\x00\x00\x00sR?\xa4b\xb8\t\xa6~\xb0\x10\xd3\xa0\xc9u\x16'
    b"\x00\x10\x00\x00\x00D\xaa\xee\x9b\xe40^\xf6+\xe7*d\x08H\xe1]\x12\xe3\x80\x90DigitalCraft\xe3\x80\x91",
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
    "unknown_1": 0,
    "unknown_2": 0,
    "group": 0,
    "category": 0,
    "no": 215,
    "unknown_3": b"\x00\x00\x00\x00\x00\x00\x80?",
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
    "unknown_4": -1,
    "unknown_5": False,
    "patterns": [
        {
            "unknown_float": 1.0,
            "key": 0,
            "clamp": False,
            "unknown_bool": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
        },
        {
            "unknown_float": 0.0,
            "key": 0,
            "clamp": False,
            "unknown_bool": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
        },
        {
            "unknown_float": 0.0,
            "key": 0,
            "clamp": False,
            "unknown_bool": False,
            "uv": {"x": 0.0, "y": 0.0, "z": 1.0, "w": 1.0},
        },
    ],
    "unknown_6": b"\x00\x00\x00\x00",
    "alpha": 1.0,
    "line_color": {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0},
    "line_width": 1.0,
    "emission_color": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0},
    "emission_power": 0.0,
    "light_cancel": 0.0,
    "unknown_7": b"\x00\x00\x00\x00\x00\x00",
    "unknown_8": '{"x":0.0,"y":0.0,"z":1.0,"w":1.0}',
    "unknown_9": b"\x00\x00\x00\x00",
    "enable_fk": False,
    "bones": {},
    "enable_dynamic_bone": True,
    "unknown_10": True,
    "anime_normalized_time": 0.0,
    "child": [],
}


def build_template_scene() -> "HoneycomeSceneDataSimple":
    scene = HoneycomeSceneDataSimple()
    scene.image = None
    scene.version = TEMPLATE_SCENE_META["version"]
    scene.dataVersion = TEMPLATE_SCENE_META["version"]
    scene.user_id = TEMPLATE_SCENE_META["user_id"]
    scene.data_id = TEMPLATE_SCENE_META["data_id"]
    scene.title = TEMPLATE_SCENE_META["title"]
    scene.unknown_1 = TEMPLATE_SCENE_META["unknown_1"]
    scene.unknown_2 = TEMPLATE_SCENE_META["unknown_2"]
    scene.unknown_3 = TEMPLATE_SCENE_META["unknown_3"]
    scene.unknown_tail = TEMPLATE_SCENE_META["unknown_tail"]

    folder_obj = {"type": 3, "data": copy.deepcopy(TEMPLATE_FOLDER_DATA)}
    folder_obj["data"]["child"] = [
        {"type": 1, "data": copy.deepcopy(TEMPLATE_PLANE_DATA)}
    ]
    scene.dicObject = {TEMPLATE_FOLDER_KEY: folder_obj}
    return scene


class HoneycomeSceneObjectLoader:
    """Minimal loader/saver for Honeycome items and folders."""

    _LOAD_DISPATCH = {
        1: "load_item_info",
        3: "load_folder_info",
    }

    _SAVE_DISPATCH = {
        1: "save_item_info",
        3: "save_folder_info",
    }

    @staticmethod
    def _dispatch_load(
        data_stream: BinaryIO,
        obj_type: int,
        obj_info: Dict[str, Any],
        version: str = None,
    ) -> None:
        method_name = HoneycomeSceneObjectLoader._LOAD_DISPATCH.get(obj_type)
        if method_name is None:
            return
        method = getattr(HoneycomeSceneObjectLoader, method_name)
        method(data_stream, obj_info, version)

    @staticmethod
    def _dispatch_save(
        data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None
    ) -> None:
        obj_type = obj_info.get("type", -1)
        method_name = HoneycomeSceneObjectLoader._SAVE_DISPATCH.get(obj_type)
        if method_name is None:
            raise ValueError(f"Unknown object type: {obj_type}")
        method = getattr(HoneycomeSceneObjectLoader, method_name)
        method(data_stream, obj_info, version)

    @staticmethod
    def _load_vector3(data_stream: BinaryIO) -> Dict[str, float]:
        return {
            "x": struct.unpack("f", data_stream.read(4))[0],
            "y": struct.unpack("f", data_stream.read(4))[0],
            "z": struct.unpack("f", data_stream.read(4))[0],
        }

    @staticmethod
    def _save_vector3(
        data_stream: BinaryIO, vector3: Dict[str, float], default: float = 0.0
    ) -> None:
        data_stream.write(struct.pack("f", vector3.get("x", default)))
        data_stream.write(struct.pack("f", vector3.get("y", default)))
        data_stream.write(struct.pack("f", vector3.get("z", default)))

    @staticmethod
    def _load_object_info_base(data_stream: BinaryIO) -> Dict[str, Any]:
        return {
            "dicKey": struct.unpack("i", data_stream.read(4))[0],
            "position": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "rotation": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "scale": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "treeState": struct.unpack("i", data_stream.read(4))[0],
            "visible": bool(struct.unpack("b", data_stream.read(1))[0]),
        }

    @staticmethod
    def _save_object_info_base(data_stream: BinaryIO, data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("i", data.get("dicKey", 0)))

        pos = data.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, pos, default=0.0)

        rot = data.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, rot, default=0.0)

        scale = data.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, scale, default=1.0)

        data_stream.write(struct.pack("i", data.get("treeState", 0)))
        data_stream.write(struct.pack("b", int(data.get("visible", True))))

    @staticmethod
    def load_bone_info(data_stream: BinaryIO) -> Dict[str, Any]:
        bone_data = {}
        bone_data["dicKey"] = struct.unpack("i", data_stream.read(4))[0]
        bone_data["changeAmount"] = {
            "position": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "rotation": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "scale": HoneycomeSceneObjectLoader._load_vector3(data_stream),
        }
        return bone_data

    @staticmethod
    def save_bone_info(data_stream: BinaryIO, bone_data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("i", bone_data.get("dicKey", 0)))
        change_amount = bone_data.get("changeAmount", {})
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        )
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0})
        )
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0})
        )

    @staticmethod
    def load_pattern_info(data_stream: BinaryIO) -> Dict[str, Any]:
        pattern_data = {}
        pattern_data["unknown_float"] = struct.unpack("f", data_stream.read(4))[0]
        pattern_data["key"] = struct.unpack("i", data_stream.read(4))[0]
        pattern_data["clamp"] = bool(struct.unpack("b", data_stream.read(1))[0])
        pattern_data["unknown_bool"] = bool(struct.unpack("b", data_stream.read(1))[0])
        uv_json = load_string(data_stream).decode("utf-8")
        pattern_data["uv"] = json.loads(uv_json)
        return pattern_data

    @staticmethod
    def save_pattern_info(data_stream: BinaryIO, pattern_data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("f", pattern_data.get("unknown_float", 1.0)))
        data_stream.write(struct.pack("i", pattern_data["key"]))
        data_stream.write(struct.pack("b", int(pattern_data["clamp"])))
        data_stream.write(
            struct.pack("b", int(pattern_data.get("unknown_bool", False)))
        )
        write_string(
            data_stream,
            json.dumps(pattern_data["uv"], separators=(",", ":")).encode("utf-8"),
        )

    @staticmethod
    def load_item_info(
        data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None
    ) -> None:
        data = HoneycomeSceneObjectLoader._load_object_info_base(data_stream)
        data["unknown_1"] = struct.unpack("i", data_stream.read(4))[0]
        data["unknown_2"] = struct.unpack("i", data_stream.read(4))[0]
        data["group"] = struct.unpack("i", data_stream.read(4))[0]

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.1.1.0") >= 0:
            data["category"] = struct.unpack("i", data_stream.read(4))[0]
        else:
            data["category"] = 0

        data["no"] = struct.unpack("i", data_stream.read(4))[0]
        data["unknown_3"] = data_stream.read(8)

        data["colors"] = []
        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.3") >= 0:
            num_colors = 8
        else:
            num_colors = 7
        for _ in range(num_colors):
            color_bytes = load_string(data_stream)
            if len(color_bytes) > 0:
                data["colors"].append(json.loads(color_bytes.decode("utf-8")))
            else:
                data["colors"].append(None)
        if num_colors == 7:
            data["colors"].append({"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})

        data["unknown_4"] = struct.unpack("i", data_stream.read(4))[0]
        data["unknown_5"] = bool(struct.unpack("b", data_stream.read(1))[0])

        data["patterns"] = []
        for _ in range(3):
            data["patterns"].append(
                HoneycomeSceneObjectLoader.load_pattern_info(data_stream)
            )

        data["unknown_6"] = data_stream.read(4)
        data["alpha"] = struct.unpack("f", data_stream.read(4))[0]

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.4") >= 0:
            line_color_json = load_string(data_stream).decode("utf-8")
            data["line_color"] = json.loads(line_color_json)
            data["line_width"] = struct.unpack("f", data_stream.read(4))[0]
        else:
            data["line_color"] = {
                "r": 128.0 / 255.0,
                "g": 128.0 / 255.0,
                "b": 128.0 / 255.0,
                "a": 1.0,
            }
            data["line_width"] = 1.0

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.7") >= 0:
            emission_color_json = load_string(data_stream).decode("utf-8")
            data["emission_color"] = json.loads(emission_color_json)
            data["emission_power"] = struct.unpack("f", data_stream.read(4))[0]
            data["light_cancel"] = struct.unpack("f", data_stream.read(4))[0]
        else:
            data["emission_color"] = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
            data["emission_power"] = 0.0
            data["light_cancel"] = 0.0

        data["unknown_7"] = data_stream.read(6)
        data["unknown_8"] = load_string(data_stream).decode("utf-8")
        data["unknown_9"] = data_stream.read(4)

        data["enable_fk"] = bool(struct.unpack("b", data_stream.read(1))[0])

        bones_count = struct.unpack("i", data_stream.read(4))[0]
        data["bones"] = {}
        for _ in range(bones_count):
            bone_key = load_string(data_stream).decode("utf-8")
            data["bones"][bone_key] = HoneycomeSceneObjectLoader.load_bone_info(
                data_stream
            )

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.0.1") >= 0:
            data["enable_dynamic_bone"] = bool(
                struct.unpack("b", data_stream.read(1))[0]
            )
        else:
            data["enable_dynamic_bone"] = True

        data["unknown_10"] = bool(struct.unpack("b", data_stream.read(1))[0])
        data["anime_normalized_time"] = struct.unpack("f", data_stream.read(4))[0]
        data["child"] = HoneycomeSceneObjectLoader.load_child_objects(
            data_stream, version
        )
        obj_info["data"] = data

    @staticmethod
    def load_folder_info(
        data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None
    ) -> None:
        data = HoneycomeSceneObjectLoader._load_object_info_base(data_stream)
        name_bytes = load_string(data_stream)
        data["name"] = name_bytes.decode("utf-8")
        data["child"] = HoneycomeSceneObjectLoader.load_child_objects(
            data_stream, version
        )
        obj_info["data"] = data

    @staticmethod
    def save_item_info(
        data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None
    ) -> None:
        data = obj_info["data"]
        HoneycomeSceneObjectLoader._save_object_info_base(data_stream, data)

        data_stream.write(struct.pack("i", data["unknown_1"]))
        data_stream.write(struct.pack("i", data["unknown_2"]))
        data_stream.write(struct.pack("i", data["group"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.1.1.0") >= 0:
            data_stream.write(struct.pack("i", data["category"]))

        data_stream.write(struct.pack("i", data["no"]))
        data_stream.write(data["unknown_3"])

        num_colors = (
            8
            if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.3") >= 0
            else 7
        )
        for i in range(num_colors):
            color = (
                data["colors"][i]
                if i < len(data["colors"]) and data["colors"][i] is not None
                else {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
            )
            write_string(
                data_stream, json.dumps(color, separators=(",", ":")).encode("utf-8")
            )

        data_stream.write(struct.pack("i", data["unknown_4"]))
        data_stream.write(struct.pack("b", int(data["unknown_5"])))

        for pattern in data["patterns"]:
            HoneycomeSceneObjectLoader.save_pattern_info(data_stream, pattern)

        data_stream.write(data["unknown_6"])
        data_stream.write(struct.pack("f", data["alpha"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.4") >= 0:
            write_string(
                data_stream,
                json.dumps(data["line_color"], separators=(",", ":")).encode("utf-8"),
            )
            data_stream.write(struct.pack("f", data["line_width"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.7") >= 0:
            write_string(
                data_stream,
                json.dumps(data["emission_color"], separators=(",", ":")).encode(
                    "utf-8"
                ),
            )
            data_stream.write(struct.pack("f", data["emission_power"]))
            data_stream.write(struct.pack("f", data["light_cancel"]))

        data_stream.write(data["unknown_7"])
        write_string(data_stream, data["unknown_8"].encode("utf-8"))
        data_stream.write(data["unknown_9"])

        data_stream.write(struct.pack("b", int(data["enable_fk"])))
        data_stream.write(struct.pack("i", len(data["bones"])))
        for bone_key, bone_data in data["bones"].items():
            write_string(data_stream, bone_key.encode("utf-8"))
            HoneycomeSceneObjectLoader.save_bone_info(data_stream, bone_data)

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.0.1") >= 0:
            data_stream.write(struct.pack("b", int(data["enable_dynamic_bone"])))

        data_stream.write(struct.pack("b", int(data["unknown_10"])))
        data_stream.write(struct.pack("f", data["anime_normalized_time"]))

        data_stream.write(struct.pack("i", len(data.get("child", []))))
        for child in data.get("child", []):
            HoneycomeSceneObjectLoader.save_child_objects(data_stream, child, version)

    @staticmethod
    def save_folder_info(
        data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None
    ) -> None:
        data = obj_info["data"]
        HoneycomeSceneObjectLoader._save_object_info_base(data_stream, data)
        name = data.get("name", "")
        name_bytes = name.encode("utf-8") if isinstance(name, str) else name
        write_string(data_stream, name_bytes)

        child_list = data.get("child", [])
        data_stream.write(struct.pack("i", len(child_list)))
        for child in child_list:
            HoneycomeSceneObjectLoader.save_child_objects(data_stream, child, version)

    @staticmethod
    def load_child_objects(data_stream: BinaryIO, version: str = None) -> list:
        child_list = []
        count = struct.unpack("i", data_stream.read(4))[0]
        for _ in range(count):
            obj_type = struct.unpack("i", data_stream.read(4))[0]
            obj_info = {"type": obj_type, "data": {}}
            HoneycomeSceneObjectLoader._dispatch_load(
                data_stream, obj_type, obj_info, version
            )
            child_list.append(obj_info)
        return child_list

    @staticmethod
    def save_child_objects(
        data_stream: BinaryIO, child_data: Dict[str, Any], version: str = None
    ) -> None:
        obj_type = child_data.get("type", -1)
        data_stream.write(struct.pack("i", obj_type))
        HoneycomeSceneObjectLoader._dispatch_save(data_stream, child_data, version)

    @staticmethod
    def _compare_versions(version_str: str, target: str) -> int:
        if version_str is None:
            return 1
        version_parts = [int(x) for x in version_str.split(".")]
        target_parts = [int(x) for x in target.split(".")]
        while len(version_parts) < len(target_parts):
            version_parts.append(0)
        while len(target_parts) < len(version_parts):
            target_parts.append(0)
        for v, t in zip(version_parts, target_parts):
            if v < t:
                return -1
            if v > t:
                return 1
        return 0


class HoneycomeSceneDataSimple:
    """Minimal Honeycome scene loader/saver for items and folders."""

    def __init__(self):
        self.image = None
        self.version = None
        self.dataVersion = None
        self.user_id = None
        self.data_id = None
        self.title = None
        self.unknown_1 = None
        self.unknown_2 = None
        self.unknown_3 = None
        self.dicObject = {}
        self.unknown_tail = b""

    @classmethod
    def load(
        cls, filelike: Union[str, bytes, io.BytesIO]
    ) -> "HoneycomeSceneDataSimple":
        hs = cls()
        if isinstance(filelike, str):
            with open(filelike, "br") as f:
                data = f.read()
            data_stream = io.BytesIO(data)
        elif isinstance(filelike, bytes):
            data_stream = io.BytesIO(filelike)
        elif isinstance(filelike, io.BytesIO):
            data_stream = filelike
        else:
            raise ValueError(f"Unsupported input type: {type(filelike)}")

        hs.image = get_png(data_stream)
        version_str = load_string(data_stream).decode("utf-8")
        hs.user_id = load_string(data_stream).decode("utf-8")
        hs.data_id = load_string(data_stream).decode("utf-8")
        hs.title = load_string(data_stream).decode("utf-8")
        hs.unknown_1 = load_type(data_stream, "i")
        hs.unknown_2 = load_type(data_stream, "i")
        hs.unknown_3 = data_stream.read(32)
        hs.version = version_str
        hs.dataVersion = version_str

        obj_count = load_type(data_stream, "i")
        for _ in range(obj_count):
            key = load_type(data_stream, "i")
            obj_type = load_type(data_stream, "i")
            obj_info = {"type": obj_type, "data": {}}
            HoneycomeSceneObjectLoader._dispatch_load(
                data_stream, obj_type, obj_info, version_str
            )
            hs.dicObject[key] = obj_info

        hs.unknown_tail = data_stream.read()
        return hs

    def __bytes__(self) -> bytes:
        data_stream = io.BytesIO()
        if self.image:
            data_stream.write(self.image)

        version_bytes = self.version.encode("utf-8")
        data_stream.write(struct.pack("b", len(version_bytes)))
        data_stream.write(version_bytes)

        write_string(data_stream, self.user_id.encode("utf-8"))
        write_string(data_stream, self.data_id.encode("utf-8"))
        write_string(data_stream, self.title.encode("utf-8"))

        data_stream.write(struct.pack("i", self.unknown_1))
        data_stream.write(struct.pack("i", self.unknown_2))
        data_stream.write(self.unknown_3)

        data_stream.write(struct.pack("i", len(self.dicObject)))
        for key, obj_info in self.dicObject.items():
            data_stream.write(struct.pack("i", key))
            data_stream.write(struct.pack("i", obj_info["type"]))
            HoneycomeSceneObjectLoader._dispatch_save(
                data_stream, obj_info, self.version
            )

        data_stream.write(self.unknown_tail)
        return data_stream.getvalue()


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
    folder_obj = template_scene.dicObject[folder_key]
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
    text_height = bbox[3] - bbox[1]
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
        x_first = start_x + run_start * spacing
        x_last = start_x + run_end * spacing
        x = (x_first + x_last) / 2
        z = start_z + row_index * spacing
        y = 0.0
        plane = create_plane(plane_template, x, y, z, run_color, scale)
        plane["data"]["scale"]["x"] = scale * run_length
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

    return planes


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
    text_length = len(text)
    grid_width = max(1, int(round(img.width * per_char_resolution / img.height)))

    global_start_x = -((grid_width - 1) * spacing) / 2
    global_start_z = -((grid_height - 1) * spacing) / 2
    char_pixels_list = []
    char_center_cols = []
    raw_plane_count = 0
    effective_threshold = 1 if antialias else 128

    dummy_img = Image.new("L", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    text_bbox = dummy_draw.textbbox((0, 0), text, font=font, anchor="ls")
    text_left = text_bbox[0]
    text_width = max(1, text_bbox[2] - text_bbox[0])
    x_offset = (img.width - text_width) // 2 - text_left

    def measure_text_advance(value):
        if hasattr(dummy_draw, "textlength"):
            return dummy_draw.textlength(value, font=font)
        if hasattr(font, "getlength"):
            return font.getlength(value)
        bbox = dummy_draw.textbbox((0, 0), value, font=font, anchor="ls")
        return bbox[2] - bbox[0]

    centers = []
    for index, char in enumerate(text):
        advance = measure_text_advance(text[:index])
        char_bbox = dummy_draw.textbbox((advance, 0), char, font=font, anchor="ls")
        if char_bbox is None or (char_bbox[2] - char_bbox[0]) == 0:
            char_advance = measure_text_advance(char)
            center = advance + char_advance / 2
        else:
            center = (char_bbox[0] + char_bbox[2]) / 2
        center_image = x_offset + center
        centers.append(center_image / max(1, img.width))

    for index, char in enumerate(text):
        display_index = index
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

        nonzero_cols = np.where(char_pixels >= effective_threshold)[1]
        if nonzero_cols.size == 0:
            center_col = (per_char_resolution - 1) / 2
        else:
            center_col = (nonzero_cols.min() + nonzero_cols.max()) / 2

        char_pixels_list.append(char_pixels)
        char_center_cols.append(center_col)

    desired_centers_display = centers
    preview_pixels = resample_image(img, grid_width, grid_height)

    char_folders = []
    plane_count = 0
    for index, char in enumerate(text):
        display_index = index
        char_pixels = np.fliplr(char_pixels_list[index])
        center_col = char_center_cols[index]

        char_start_x = global_start_x + display_index * per_char_resolution * spacing
        center_x = char_start_x + center_col * spacing
        planes = pixels_to_planes(
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
        for plane in planes:
            plane["data"]["position"]["x"] -= center_x
        plane_count += len(planes)

        desired_center_x = (
            global_start_x
            + (grid_width - 1)
            * spacing
            * (1.0 - desired_centers_display[display_index])
        )

        char_folder = copy.deepcopy(folder_obj)
        char_label = char if char.strip() else "空白"
        char_folder["data"]["name"] = f"文字_{index + 1}_{char_label}"
        char_folder["data"]["position"]["x"] = desired_center_x
        char_folder["data"]["child"] = planes
        char_folder["data"]["treeState"] = 1
        char_folders.append(char_folder)

    # 3. シーンを作成
    scene = HoneycomeSceneDataSimple()
    scene.version = template_scene.version
    scene.dataVersion = template_scene.dataVersion
    scene.user_id = template_scene.user_id
    scene.data_id = str(uuid.uuid4())
    scene.title = f"テキスト: {text}"
    scene.unknown_1 = template_scene.unknown_1
    scene.unknown_2 = template_scene.unknown_2
    scene.unknown_3 = template_scene.unknown_3
    scene.unknown_tail = template_scene.unknown_tail
    scene.image = template_scene.image

    new_folder = copy.deepcopy(folder_obj)
    new_folder["data"]["name"] = f"テキスト_{text}"
    new_folder["data"]["child"] = char_folders
    new_folder["data"]["treeState"] = 1
    scene.dicObject = {folder_key: new_folder}

    return scene, img, preview_pixels, plane_count, raw_plane_count


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
    text_height = st.slider(
        get_text("height_label", lang),
        min_value=0.1,
        max_value=2.0,
        value=0.5,
        step=0.05,
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

        antialias = st.checkbox(get_text("antialias_label", lang), value=True)
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

                    (
                        scene,
                        original_img,
                        preview_pixels,
                        plane_count,
                        raw_plane_count,
                    ) = generate_text_scene(
                        text=text_input,
                        template_scene=template_scene,
                        plane_template={
                            **plane_template,
                            "data": {
                                **plane_template["data"],
                                "group": plane_settings["group"],
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
                    render_scene_info(scene, plane_count, raw_plane_count, lang)

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
