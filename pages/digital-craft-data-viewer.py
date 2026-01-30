import io
from collections import Counter

import streamlit as st
from kkloader import HoneycomeSceneData

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
        "no_characters": "キャラクターが含まれていません",
        "hierarchy_info_title": "階層構造情報",
        "max_depth": "最大階層の深さ",
        "folder_structure": "フォルダ構造",
        "item_stats_title": "アイテム統計",
        "item_count": "アイテム数",
        "item_unique": "ユニーク",
        "item_list": "アイテム一覧 (group, category, no)",
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
        "no_characters": "No characters found",
        "hierarchy_info_title": "Hierarchy Information",
        "max_depth": "Maximum Hierarchy Depth",
        "folder_structure": "Folder Structure",
        "item_stats_title": "Item Statistics",
        "item_count": "Item Count",
        "item_unique": "unique",
        "item_list": "Item List (group, category, no)",
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
        "item_keys": Counter(),  # (group, category, no) のペアでカウント
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

                stats["characters"].append({"name": name, "header": header})
                stats["character_headers"][header] += 1

        # 1: Item (OIItemInfo)
        elif obj_type == 1:
            group = data.get("group", -1)
            category = data.get("category", -1)
            no = data.get("no", -1)
            stats["item_keys"][(group, category, no)] += 1

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

# サイドバーに言語選択を配置
with st.sidebar:
    lang = st.selectbox(
        "Language / 言語",
        options=["ja", "en"],
        format_func=lambda x: "日本語" if x == "ja" else "English",
        index=0,
    )

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

        # 分析実行
        stats = analyze_scene(hs)

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
            chara_df = [
                {
                    get_text("character_name", lang): c["name"],
                    get_text("character_header", lang): c["header"],
                }
                for c in stats["characters"]
            ]
            st.dataframe(chara_df, width="stretch")
        else:
            st.info(get_text("no_characters", lang))

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
                item_df = [
                    {
                        "group": group,
                        "category": category,
                        "no": no,
                        get_text("item_count_col", lang): count,
                    }
                    for (group, category, no), count in sorted(
                        stats["item_keys"].items()
                    )
                ]
                st.dataframe(item_df, width="stretch")

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
