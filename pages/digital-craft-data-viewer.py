import copy
import io
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st
from kkloader import HoneycomeSceneData
from kkloader.KoikatuCharaData import BlockData
from PIL import Image, ImageDraw, ImageFont

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "デジクラシーンデータビューア",
        "description": """
デジタルクラフトのシーンデータに含まれている情報を集計・表示するツールです。
""",
        "file_uploader": "シーンデータ（PNG）をアップロード",
        "file_uploader_help": "デジタルクラフトのシーンデータ（.png）をアップロードしてください",
        "success_load": "シーンデータを読み込みました",
        "error_load": "ファイルの読み込みに失敗しました。シーンデータではない可能性があります。",
        "info_upload": "シーンデータ（.png）をアップロードしてください。",
        "scene_info_title": "シーン情報",
        "scene_title": "タイトル",
        "scene_thumbnail": "サムネイル",
        "scene_user_id": "ユーザーID",
        "scene_data_id": "データID",
        "scene_version": "バージョン",
        "object_stats_title": "オブジェクト統計",
        "total_objects": "全オブジェクト数",
        "objects_by_type": "タイプ別オブジェクト数",
        "type_names": {
            0: "キャラクター",
            1: "アイテム",
            2: "ライト",
            3: "フォルダ",
            4: "ルート",
            5: "カメラ",
        },
        "character_info_title": "キャラクター情報",
        "character_headers": "キャラクターのヘッダー（ゲーム種類）",
        "character_list": "キャラクター一覧",
        "character_name": "名前",
        "character_header": "ヘッダー",
        "character_anime": "アニメ",
        "character_download": "DL",
        "no_characters": "キャラクターが含まれていません",
        "hierarchy_info_title": "階層構造情報",
        "max_depth": "最大階層の深さ",
        "folder_structure": "フォルダ構造",
        "item_stats_title": "アイテム統計",
        "item_count": "アイテム数",
        "item_unique": "ユニーク",
        "item_list": "アイテム一覧",
        "item_category_col": "分類",
        "item_name_col": "アイテム名",
        "item_no_col": "no",
        "item_count_col": "個数",
        "route_stats_title": "ルート統計",
        "route_count": "ルート数",
        "route_list": "ルート一覧",
        "route_name": "名前",
        "route_active": "有効",
        "camera_stats_title": "カメラ統計",
        "camera_count": "カメラ数",
        "camera_list": "カメラ一覧",
        "camera_name": "名前",
        "camera_active": "有効",
        "download_json": "データをJSONとしてダウンロード",
    },
    "en": {
        "title": "Digital Craft Scene Data Viewer",
        "description": """
A tool to display and aggregate information contained in Digital Craft/Honey Come scene data.
""",
        "file_uploader": "Upload scene data (PNG)",
        "file_uploader_help": "Please upload a Digital Craft/Honey Come scene data (.png)",
        "success_load": "Scene data loaded successfully",
        "error_load": "Failed to load file. It may not be a scene data file.",
        "info_upload": "Please upload a scene data (.png).",
        "scene_info_title": "Scene Information",
        "scene_title": "Title",
        "scene_thumbnail": "Thumbnail",
        "scene_user_id": "User ID",
        "scene_data_id": "Data ID",
        "scene_version": "Version",
        "object_stats_title": "Object Statistics",
        "total_objects": "Total Objects",
        "objects_by_type": "Objects by Type",
        "type_names": {
            0: "Character",
            1: "Item",
            2: "Light",
            3: "Folder",
            4: "Route",
            5: "Camera",
        },
        "character_info_title": "Character Information",
        "character_headers": "Character Headers (Game Types)",
        "character_list": "Character List",
        "character_name": "Name",
        "character_header": "Header",
        "character_anime": "Anime",
        "character_download": "DL",
        "no_characters": "No characters found",
        "hierarchy_info_title": "Hierarchy Information",
        "max_depth": "Maximum Hierarchy Depth",
        "folder_structure": "Folder Structure",
        "item_stats_title": "Item Statistics",
        "item_count": "Item Count",
        "item_unique": "unique",
        "item_list": "Item List",
        "item_category_col": "Category",
        "item_name_col": "Item Name",
        "item_no_col": "no",
        "item_count_col": "Count",
        "route_stats_title": "Route Statistics",
        "route_count": "Route Count",
        "route_list": "Route List",
        "route_name": "Name",
        "route_active": "Active",
        "camera_stats_title": "Camera Statistics",
        "camera_count": "Camera Count",
        "camera_list": "Camera List",
        "camera_name": "Name",
        "camera_active": "Active",
        "download_json": "Download data as JSON",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


def get_type_name(type_id, lang="ja"):
    """タイプIDから名前を取得"""
    type_names = get_text("type_names", lang)
    return type_names.get(type_id, f"Unknown ({type_id})")


# ========================================
# アイテムデータ用のヘルパー
# ========================================

ITEMS_PARQUET_PATH = (
    Path(__file__).parent / "digital-craft-data-viewer-data" / "items.parquet"
)


@st.cache_data
def load_items_data():
    """items.parquetを読み込んで辞書として返す"""
    if not ITEMS_PARQUET_PATH.exists():
        return {}, {}
    df = pd.read_parquet(ITEMS_PARQUET_PATH)
    # (title, group, category, no) -> アイテム情報 の辞書を作成
    items_dict = {}
    # (title, group, category) -> カテゴリ名 の辞書を作成
    category_dict = {}
    for _, row in df.iterrows():
        key = (row["title"], row["group"], row["category"], row["no"])
        category_name = (
            f"{row['title_name']} -> {row['group_name']} -> {row['category_name']}"
        )
        item_info = {
            "category_name": category_name,
            "item_name": row["item_name"],
            "full_name": f"{category_name} -> {row['item_name']}",
        }
        items_dict[key] = item_info
        # カテゴリ名の辞書も構築
        cat_key = (row["title"], row["group"], row["category"])
        if cat_key not in category_dict:
            category_dict[cat_key] = category_name
    return items_dict, category_dict


def get_item_category_name(title, group, category):
    """(title, group, category) から分類名を取得"""
    _, category_dict = load_items_data()
    key = (title, group, category)
    return category_dict.get(key, f"不明 ({title}, {group}, {category})")


def get_item_info(title, group, category, no):
    """(title, group, category, no) からアイテム情報を取得"""
    items_dict, _ = load_items_data()
    key = (title, group, category, no)
    return items_dict.get(key)


# ========================================
# モーション（アニメ）名マッピング
# ========================================

MOTIONS_PARQUET_PATH = (
    Path(__file__).parent / "digital-craft-data-viewer-data" / "motions.parquet"
)


@st.cache_data
def load_motions_data():
    """motions.parquetを読み込んで辞書として返す"""
    if not MOTIONS_PARQUET_PATH.exists():
        return {}
    df = pd.read_parquet(MOTIONS_PARQUET_PATH)
    # (title, group, category, no) -> 表示名 の辞書を作成
    motions_dict = {}
    for _, row in df.iterrows():
        key = (row["title"], row["group"], row["category"], row["no"])
        display_name = f"{row['title_name']} -> {row['group_name']} -> {row['category_name']} -> {row['anime_name']}"
        motions_dict[key] = display_name
    return motions_dict


def get_anime_display_name(anime_info):
    """anime_info辞書からアニメの表示名を取得"""
    if not anime_info:
        return None
    title = anime_info.get("title", -1)
    group = anime_info.get("group", -1)
    category = anime_info.get("category", -1)
    no = anime_info.get("no", -1)
    key = (title, group, category, no)
    motions_dict = load_motions_data()
    return motions_dict.get(key, f"不明 ({title}, {group}, {category}, {no})")


# ========================================
# キャラクターデータ用のヘルパークラスと定数
# ========================================


class StubBlockData(BlockData):
    def __init__(self, name, version):
        self.name = name
        self.data = {}
        self.version = version


DEFAULT_GAMEPARAMETER_SV = {
    "imageData": None,
    "job": 0,
    "sexualTarget": 0,
    "lvChastity": 0,
    "lvSociability": 0,
    "lvTalk": 0,
    "lvStudy": 0,
    "lvLiving": 0,
    "lvPhysical": 0,
    "lvDefeat": 0,
    "belongings": [0, 0],
    "isVirgin": True,
    "isAnalVirgin": True,
    "isMaleVirgin": True,
    "isMaleAnalVirgin": True,
    "individuality": {"answer": [-1, -1]},
    "preferenceH": {"answer": [-1, -1]},
}

DEFAULT_GAMEPARAMETER_AC = {
    "version": "0.0.0",
    "imageData": None,
    "clubActivities": 3,
    "individuality": [False] * 18,
    "characteristics": {"answer": [-1, -1]},
    "hobby": {"answer": [-1, -1, -1]},
    "erogenousZone": 0,
}

DEFAULT_GAMEINFO_SV = {}

DEFAULT_GAMEINFO_AC = {"version": "0.0.0"}


FONT_PATH = "pages/digital-craft-calligrapher-data/MPLUSRounded1c-Regular.ttf"


def create_placeholder_image(
    game_type="", name="", scene_title="", width=252, height=352
):
    """プレースホルダー画像を生成してPNGバイト列として返す

    Args:
        game_type: ゲームタイプ ("SV" or "AC")
        name: キャラクター名
        scene_title: 抽出元シーン名
        width: 画像幅
        height: 画像高さ
    """
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype(FONT_PATH, 32)
        font_small = ImageFont.truetype(FONT_PATH, 20)
        font_tiny = ImageFont.truetype(FONT_PATH, 14)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    # ゲームタイプを中央上部に描画
    if game_type:
        bbox = draw.textbbox((0, 0), game_type, font=font_large)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, 40), game_type, fill=(255, 255, 255), font=font_large)

    # 名前を中央に描画（長い場合は折り返し）
    if name:
        # 名前が長い場合は複数行に分割
        max_chars_per_line = 10
        lines = [
            name[i : i + max_chars_per_line]
            for i in range(0, len(name), max_chars_per_line)
        ]
        y_start = height // 2 - (len(lines) * 25) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text(
                (x, y_start + i * 25), line, fill=(255, 255, 255), font=font_small
            )

    # 抽出元シーン名を下部に描画
    if scene_title:
        source_text = f"抽出元: {scene_title}"
        # 長い場合は切り詰め
        max_chars = 16
        if len(source_text) > max_chars:
            source_text = source_text[: max_chars - 1] + "…"
        bbox = draw.textbbox((0, 0), source_text, font=font_tiny)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, height - 40), source_text, fill=(200, 200, 200), font=font_tiny)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def set_character_image(chara, name="", scene_title=""):
    """キャラクターのheaderに応じて適切な画像とGameParameterをセットする

    - ハニカム (【HCChara】): face_image (ポートレート画像)
    - サマすく (【SVChara】): プレースホルダー画像 + GameParameter_SV
    - アイコミ (【ACChara】): プレースホルダー画像 + GameParameter_AC
    """
    header = getattr(chara, "header", b"")
    if isinstance(header, bytes):
        header = header.decode("utf-8")

    # 接尾辞なしの GameParameter と GameInfo を削除
    for block_name in ["GameParameter", "GameInfo"]:
        if hasattr(chara, block_name):
            delattr(chara, block_name)
        if block_name in chara.blockdata:
            chara.blockdata.remove(block_name)

    if header == "【HCChara】":
        # ハニカム: face_image を使用
        if hasattr(chara, "face_image") and chara.face_image:
            chara.image = chara.face_image
    elif header == "【SVChara】":
        # サマすく: GameParameter_SV と GameInfo_SV を追加してプレースホルダー画像を設定
        placeholder = create_placeholder_image(
            game_type="SV", name=name, scene_title=scene_title
        )
        chara.image = placeholder
        if not hasattr(chara, "GameParameter_SV"):
            chara.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
            chara.GameParameter_SV.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_SV)
            chara.blockdata.append("GameParameter_SV")
        chara.GameParameter_SV.data["imageData"] = placeholder
        if not hasattr(chara, "GameInfo_SV"):
            chara.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")
            chara.GameInfo_SV.data = copy.deepcopy(DEFAULT_GAMEINFO_SV)
            chara.blockdata.append("GameInfo_SV")
        # blockdata の更新を反映
        chara.serialized_lstinfo_order = chara.blockdata
        chara.original_lstinfo_order = chara.blockdata
    elif header == "【ACChara】":
        # アイコミ: GameParameter_AC と GameInfo_AC を追加してプレースホルダー画像を設定
        placeholder = create_placeholder_image(
            game_type="AC", name=name, scene_title=scene_title
        )
        chara.image = placeholder
        if not hasattr(chara, "GameParameter_AC"):
            chara.GameParameter_AC = StubBlockData("GameParameter_AC", "0.0.0")
            chara.GameParameter_AC.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_AC)
            chara.blockdata.append("GameParameter_AC")
        chara.GameParameter_AC.data["imageData"] = placeholder
        if not hasattr(chara, "GameInfo_AC"):
            chara.GameInfo_AC = StubBlockData("GameInfo_AC", "0.0.0")
            chara.GameInfo_AC.data = copy.deepcopy(DEFAULT_GAMEINFO_AC)
            chara.blockdata.append("GameInfo_AC")
        # blockdata の更新を反映
        chara.serialized_lstinfo_order = chara.blockdata
        chara.original_lstinfo_order = chara.blockdata


def analyze_scene(hs):
    """シーンデータを分析して統計情報を返す

    Object types:
      0: Character (OICharInfo)
      1: Item (OIItemInfo)
      2: Light (OILightInfo)
      3: Folder (OIFolderInfo)
      4: Route (OIRouteInfo)
      5: Camera (OICameraInfo)
    """
    stats = {
        "total_objects": 0,
        "type_counts": Counter(),
        "max_depth": 0,
        "characters": [],
        "character_headers": Counter(),
        "item_keys": Counter(),  # (group, category, no, title) のセットでカウント
        "folder_names": [],
        "routes": [],
        "cameras": [],
    }

    # walk()メソッドで全オブジェクトを走査（深さ情報付き）
    for _, obj, depth in hs.walk(include_depth=True):
        stats["total_objects"] += 1
        obj_type = obj.get("type")
        stats["type_counts"][obj_type] += 1
        stats["max_depth"] = max(stats["max_depth"], depth)

        data = obj.get("data", {})

        # 0: Character (OICharInfo)
        if obj_type == 0:
            chara = data.get("character")
            if chara:
                header = getattr(chara, "header", "Unknown")
                if isinstance(header, bytes):
                    header = header.decode("utf-8")

                # 名前を取得
                name = "Unknown"
                if "Parameter" in chara.blockdata:
                    param = chara["Parameter"]
                    lastname = param.data.get("lastname", "")
                    firstname = param.data.get("firstname", "")
                    if lastname or firstname:
                        name = f"{lastname} {firstname}".strip()

                # アニメ情報を取得
                anime_info = data.get("anime_info")

                stats["characters"].append(
                    {
                        "name": name,
                        "header": header,
                        "data": chara,
                        "anime_info": anime_info,
                    }
                )
                stats["character_headers"][header] += 1

        # 1: Item (OIItemInfo)
        elif obj_type == 1:
            group = data.get("group", -1)
            category = data.get("category", -1)
            no = data.get("no", -1)
            title = data.get("title", -1)
            stats["item_keys"][(group, category, no, title)] += 1

        # 3: Folder (OIFolderInfo)
        elif obj_type == 3:
            folder_name = data.get("name", "")
            if folder_name:
                stats["folder_names"].append({"name": folder_name, "depth": depth})

        # 4: Route (OIRouteInfo)
        elif obj_type == 4:
            route_info = {
                "name": data.get("name", ""),
                "active": data.get("active", False),
            }
            stats["routes"].append(route_info)

        # 5: Camera (OICameraInfo)
        elif obj_type == 5:
            camera_info = {
                "name": data.get("name", ""),
                "active": data.get("active", False),
            }
            stats["cameras"].append(camera_info)

    return stats


def get_top_level_folders(hs):
    """トップレベルのフォルダ名のリストを取得"""
    folders = []

    for _, obj in hs.objects.items():
        if obj.get("type") == 3:  # Folder
            data = obj.get("data", {})
            folder_name = data.get("name", "(unnamed)")
            child_count = len(data.get("child", []))
            folders.append(f"📁 {folder_name} ({child_count})")

    return folders


# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title, page_icon=":bar_chart:")

lang = st.session_state.get("lang", "ja")

st.title(get_text("title", lang))
st.markdown(get_text("description", lang))
st.divider()

# ファイルアップロード
uploaded_file = st.file_uploader(
    get_text("file_uploader", lang),
    type=["png"],
    help=get_text("file_uploader_help", lang),
)

if uploaded_file is not None:
    try:
        # ファイルを読み込み
        file_bytes = uploaded_file.read()
        hs = HoneycomeSceneData.load(io.BytesIO(file_bytes))

        st.success(get_text("success_load", lang))

        # シーン情報
        st.subheader(get_text("scene_info_title", lang))
        col1, col2 = st.columns([1, 2])
        with col1:
            if hs.image:
                st.image(
                    io.BytesIO(hs.image), caption=get_text("scene_thumbnail", lang)
                )
        with col2:
            st.metric(get_text("scene_title", lang), hs.title or "(No title)")

        # シーンメタ情報
        st.dataframe(
            {
                "項目": [
                    get_text("scene_user_id", lang),
                    get_text("scene_data_id", lang),
                    get_text("scene_version", lang),
                ],
                "値": [
                    getattr(hs, "user_id", "N/A"),
                    getattr(hs, "data_id", "N/A"),
                    getattr(hs, "version", "N/A"),
                ],
            },
            hide_index=True,
            width="stretch",
        )

        # 分析実行
        stats = analyze_scene(hs)

        # キャラクター情報
        st.subheader(get_text("character_info_title", lang))
        if stats["characters"]:
            # ヘッダーのユニーク値
            st.write(f"**{get_text('character_headers', lang)}**")
            header_cols = st.columns(len(stats["character_headers"]))
            for i, (header, count) in enumerate(stats["character_headers"].items()):
                header_cols[i].metric(header, count)

            # キャラクター一覧
            st.write(f"**{get_text('character_list', lang)}**")
            # ヘッダー行
            header_col1, header_col2, header_col3, header_col4 = st.columns(
                [2, 2, 4, 1]
            )
            header_col1.write(f"**{get_text('character_name', lang)}**")
            header_col2.write(f"**{get_text('character_header', lang)}**")
            header_col3.write(f"**{get_text('character_anime', lang)}**")
            header_col4.write(f"**{get_text('character_download', lang)}**")
            # データ行
            for i, c in enumerate(stats["characters"]):
                col1, col2, col3, col4 = st.columns([2, 2, 4, 1])
                col1.write(c["name"])
                col2.write(c["header"])
                # アニメ情報を表示
                anime_display = get_anime_display_name(c.get("anime_info"))
                col3.write(anime_display if anime_display else "-")
                # headerに応じた画像をセットしてからバイト化
                chara = c["data"]
                set_character_image(chara, c["name"], hs.title or "")
                chara_bytes = bytes(chara)
                filename = f"{c['name'] or 'character'}_{i}.png"
                col4.download_button(
                    label="⬇",
                    data=chara_bytes,
                    file_name=filename,
                    mime="image/png",
                    key=f"chara_dl_{i}",
                )
        else:
            st.info(get_text("no_characters", lang))

        # オブジェクト統計
        st.subheader(get_text("object_stats_title", lang))

        # 全オブジェクト数
        st.metric(get_text("total_objects", lang), stats["total_objects"])

        # タイプ別オブジェクト数
        st.write(f"**{get_text('objects_by_type', lang)}**")
        type_data = []
        for type_id, count in sorted(stats["type_counts"].items()):
            type_name = get_type_name(type_id, lang)
            type_data.append({"type": type_name, "count": count})

        if type_data:
            cols = st.columns(len(type_data))
            for i, item in enumerate(type_data):
                cols[i].metric(item["type"], item["count"])

        # アイテム統計
        if stats["item_keys"]:
            st.subheader(get_text("item_stats_title", lang))
            total_items = sum(stats["item_keys"].values())
            unique_items = len(stats["item_keys"])
            st.metric(
                get_text("item_count", lang),
                f"{total_items} ({get_text('item_unique', lang)}: {unique_items})",
            )

            with st.expander(get_text("item_list", lang)):
                item_df = []
                for (group, category, no, title), count in sorted(
                    stats["item_keys"].items()
                ):
                    item_info = get_item_info(title, group, category, no)
                    if item_info:
                        category_name = item_info["category_name"]
                        item_name = item_info["item_name"]
                    else:
                        category_name = get_item_category_name(title, group, category)
                        item_name = f"不明 ({no})"
                    item_df.append(
                        {
                            get_text("item_category_col", lang): category_name,
                            get_text("item_name_col", lang): item_name,
                            get_text("item_count_col", lang): count,
                        }
                    )
                st.dataframe(item_df, width="stretch")

        # 階層構造情報
        st.subheader(get_text("hierarchy_info_title", lang))
        st.metric(get_text("max_depth", lang), stats["max_depth"])

        with st.expander(get_text("folder_structure", lang)):
            folders = get_top_level_folders(hs)
            if folders:
                for folder in folders:
                    st.text(folder)
            else:
                st.text("(No folders)")

        # ルート統計
        if stats["routes"]:
            st.subheader(get_text("route_stats_title", lang))
            st.metric(get_text("route_count", lang), len(stats["routes"]))

            with st.expander(get_text("route_list", lang)):
                route_df = [
                    {
                        get_text("route_name", lang): route["name"] or "(unnamed)",
                        get_text("route_active", lang): route["active"],
                    }
                    for route in stats["routes"]
                ]
                st.dataframe(route_df, width="stretch")

        # カメラ統計
        if stats["cameras"]:
            st.subheader(get_text("camera_stats_title", lang))
            st.metric(get_text("camera_count", lang), len(stats["cameras"]))

            with st.expander(get_text("camera_list", lang)):
                camera_df = [
                    {
                        get_text("camera_name", lang): camera["name"] or "(unnamed)",
                        get_text("camera_active", lang): camera["active"],
                    }
                    for camera in stats["cameras"]
                ]
                st.dataframe(camera_df, width="stretch")

    except Exception as e:
        st.error(f"{get_text('error_load', lang)}")
        st.exception(e)
else:
    st.info(get_text("info_upload", lang))
