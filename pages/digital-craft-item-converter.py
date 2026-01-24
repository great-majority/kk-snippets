import io

import streamlit as st
from kkloader import HoneycomeSceneData

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "デジクラ基本形アイテム変換ツール",
        "subtitle": "シーンデータ内の基本形アイテム(平面とか)をマップ/キャラ間で変換します。\nどちらのライトで当てたいかを選択できるようになります。",
        "usage_title": "使い方",
        "usage_content": """
1. デジタルクラフトのシーンデータ（.png）をアップロードします
2. フォルダの選択方法を選びます:
   - **最上位フォルダから選択**: トップレベルのフォルダから1つ選択
   - **文字列パターンで選択**: 入力した文字列を含むフォルダをすべて選択
3. 変換先（マップライト or キャラライト）を選択します
4. 「変換を実行」ボタンをクリックします
5. 変換済みファイルをダウンロードします

**パターン検索の例:**

「家具」と入力した場合、以下のように該当フォルダが再帰的に選択されます:
```
ワークスペース
├── 部屋A
│   ├── 家具_テーブル ← ✓ マッチ
│   ├── 家具_椅子 ← ✓ マッチ
│   └── 照明
├── 部屋B
│   ├── 家具_ソファ ← ✓ マッチ
│   └── カーテン
└── 外装
    └── 植物
```

**注意:**
- シーンのタイトル名に変換先にした"(マップ)"か"(キャラ)"がつきます
- 選択したフォルダ以下のすべてのサブフォルダ内のアイテムも再帰的に変換されます
""",
        "file_uploader": "シーンデータ（PNG）をアップロード",
        "file_uploader_help": "デジタルクラフトのシーンデータ（.png）をアップロードしてください",
        "success_load": "シーンデータを読み込みました:",
        "warning_no_folders": "トップレベルにフォルダが見つかりませんでした。",
        "folder_selection_title": "フォルダ選択",
        "folder_selection_mode": "選択方法",
        "mode_dropdown": "最上位フォルダから選択",
        "mode_pattern": "文字列パターンで選択",
        "folder_selection_label": "変換対象のフォルダを選択",
        "folder_selection_help": "選択したフォルダ以下のすべてのアイテムが変換されます",
        "pattern_input_label": "フォルダ名に含まれる文字列",
        "pattern_input_help": "この文字列を含むすべてのフォルダを再帰的に検索して変換します",
        "matched_folders": "マッチしたフォルダ: {count}件",
        "no_matched_folders": "指定した文字列を含むフォルダが見つかりませんでした",
        "target_selection_title": "変換先の選択",
        "target_selection_label": "変換先を選択",
        "target_selection_help": "マップライト: category=0, キャラライト: category=1",
        "map_light": "マップライト",
        "chara_light": "キャラライト",
        "alpha_slider": "アルファ値（透明度）",
        "alpha_slider_help": "0: 完全に透明、1: 完全に不透明",
        "execute_button": "変換を実行",
        "success_convert": "以下の {count} 個のアイテムを{target}に変換しました",
        "download_button": "変換済みファイルをダウンロード",
        "info_upload": "シーンデータ（.png）をアップロードしてください。",
        "error_occurred": "エラーが発生しました:",
    },
    "en": {
        "title": "Digital Craft Primitive Item Converter",
        "subtitle": "Convert primitive items (planes, etc.) in scene data between Map/Character light types.\nThis allows you to choose which light type to apply.",
        "usage_title": "How to use",
        "usage_content": """
1. Upload a Digital Craft scene data (.png)
2. Choose how to select folders:
   - **Select from dropdown**: Choose one folder from top-level folders
   - **Search by pattern**: Search all folders containing the input string
3. Choose the conversion target (Map Light or Character Light)
4. Click the "Execute Conversion" button
5. Download the converted file

**Pattern search example:**

If you enter "furniture", matching folders are recursively selected:
```
Workspace
├── RoomA
│   ├── furniture_table ← ✓ Match
│   ├── furniture_chair ← ✓ Match
│   └── lighting
├── RoomB
│   ├── furniture_sofa ← ✓ Match
│   └── curtain
└── Exterior
    └── plants
```

**Notes:**
- The scene title will have "(Map)" or "(Chara)" appended based on the conversion target
- All items in subfolders under the selected folder will also be converted recursively
""",
        "file_uploader": "Upload scene data (PNG)",
        "file_uploader_help": "Please upload a Digital Craft scene data (.png)",
        "success_load": "Scene data loaded:",
        "warning_no_folders": "No folders found at the top level.",
        "folder_selection_title": "Folder Selection",
        "folder_selection_mode": "Selection Method",
        "mode_dropdown": "Select from dropdown",
        "mode_pattern": "Search by pattern",
        "folder_selection_label": "Select folder to convert",
        "folder_selection_help": "All items under the selected folder will be converted",
        "pattern_input_label": "String to match in folder names",
        "pattern_input_help": "Recursively search and convert all folders containing this string",
        "matched_folders": "Matched folders: {count}",
        "no_matched_folders": "No folders found containing the specified string",
        "target_selection_title": "Conversion Target Selection",
        "target_selection_label": "Select conversion target",
        "target_selection_help": "Map Light: category=0, Character Light: category=1",
        "map_light": "Map Light",
        "chara_light": "Character Light",
        "alpha_slider": "Alpha value (transparency)",
        "alpha_slider_help": "0: Fully transparent, 1: Fully opaque",
        "execute_button": "Execute Conversion",
        "success_convert": "Converted {count} items under '{folder}' to {target}",
        "download_button": "Download converted file",
        "info_upload": "Please upload a scene data (.png).",
        "error_occurred": "An error occurred:",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title, page_icon=":arrows_counterclockwise:")

# サイドバーに言語選択を配置
with st.sidebar:
    lang = st.selectbox(
        "Language / 言語",
        options=["ja", "en"],
        format_func=lambda x: "日本語" if x == "ja" else "English",
        index=0,
    )

st.title(get_text("title", lang))
st.write(get_text("subtitle", lang))

# 使い方の説明
with st.expander(get_text("usage_title", lang)):
    st.markdown(get_text("usage_content", lang))

# マップ/キャラ変換用の辞書
PLANE_MAP_CHARA_DICT = [
    {"name": "丸", "id": [{"category": 0, "no": 192}, {"category": 1, "no": 267}]},
    {"name": "半丸", "id": [{"category": 0, "no": 193}, {"category": 1, "no": 268}]},
    {"name": "四半丸", "id": [{"category": 0, "no": 194}, {"category": 1, "no": 269}]},
    {
        "name": "穴あき丸",
        "id": [{"category": 0, "no": 195}, {"category": 1, "no": 270}],
    },
    {
        "name": "穴あき半丸",
        "id": [{"category": 0, "no": 196}, {"category": 1, "no": 271}],
    },
    {
        "name": "穴あき四半丸",
        "id": [{"category": 0, "no": 197}, {"category": 1, "no": 272}],
    },
    {
        "name": "平らな円",
        "id": [{"category": 0, "no": 198}, {"category": 1, "no": 273}],
    },
    {
        "name": "平らな半円",
        "id": [{"category": 0, "no": 199}, {"category": 1, "no": 274}],
    },
    {
        "name": "平らな四半円",
        "id": [{"category": 0, "no": 200}, {"category": 1, "no": 275}],
    },
    {"name": "コーン", "id": [{"category": 0, "no": 201}, {"category": 1, "no": 276}]},
    {
        "name": "半コーン",
        "id": [{"category": 0, "no": 202}, {"category": 1, "no": 277}],
    },
    {
        "name": "四半コーン",
        "id": [{"category": 0, "no": 203}, {"category": 1, "no": 278}],
    },
    {"name": "四角錐", "id": [{"category": 0, "no": 204}, {"category": 1, "no": 279}]},
    {
        "name": "半四角錐",
        "id": [{"category": 0, "no": 205}, {"category": 1, "no": 280}],
    },
    {
        "name": "四半四角錐",
        "id": [{"category": 0, "no": 206}, {"category": 1, "no": 281}],
    },
    {"name": "三角錐", "id": [{"category": 0, "no": 207}, {"category": 1, "no": 282}]},
    {"name": "四角", "id": [{"category": 0, "no": 208}, {"category": 1, "no": 283}]},
    {
        "name": "穴あき四角",
        "id": [{"category": 0, "no": 209}, {"category": 1, "no": 284}],
    },
    {
        "name": "穴あき四角半",
        "id": [{"category": 0, "no": 210}, {"category": 1, "no": 285}],
    },
    {
        "name": "穴あき四角四半",
        "id": [{"category": 0, "no": 211}, {"category": 1, "no": 286}],
    },
    {
        "name": "穴あき細四角",
        "id": [{"category": 0, "no": 212}, {"category": 1, "no": 287}],
    },
    {
        "name": "穴あき細四角半",
        "id": [{"category": 0, "no": 213}, {"category": 1, "no": 288}],
    },
    {
        "name": "穴あき細四角四半",
        "id": [{"category": 0, "no": 214}, {"category": 1, "no": 289}],
    },
    {"name": "平面", "id": [{"category": 0, "no": 215}, {"category": 1, "no": 290}]},
    {"name": "三角柱", "id": [{"category": 0, "no": 216}, {"category": 1, "no": 291}]},
    {
        "name": "半三角柱",
        "id": [{"category": 0, "no": 217}, {"category": 1, "no": 292}],
    },
    {
        "name": "三角柱三等分",
        "id": [{"category": 0, "no": 218}, {"category": 1, "no": 293}],
    },
    {
        "name": "穴あき三角柱",
        "id": [{"category": 0, "no": 219}, {"category": 1, "no": 294}],
    },
    {
        "name": "穴あき半三角柱",
        "id": [{"category": 0, "no": 220}, {"category": 1, "no": 295}],
    },
    {
        "name": "穴あき三角柱三等分",
        "id": [{"category": 0, "no": 221}, {"category": 1, "no": 296}],
    },
    {"name": "円柱", "id": [{"category": 0, "no": 222}, {"category": 1, "no": 297}]},
    {"name": "半円柱", "id": [{"category": 0, "no": 223}, {"category": 1, "no": 298}]},
    {
        "name": "四半円柱",
        "id": [{"category": 0, "no": 224}, {"category": 1, "no": 299}],
    },
    {
        "name": "穴あき円柱",
        "id": [{"category": 0, "no": 225}, {"category": 1, "no": 300}],
    },
    {
        "name": "穴あき半円柱",
        "id": [{"category": 0, "no": 226}, {"category": 1, "no": 301}],
    },
    {
        "name": "穴あき四半円柱",
        "id": [{"category": 0, "no": 227}, {"category": 1, "no": 302}],
    },
    {
        "name": "穴あき細円柱",
        "id": [{"category": 0, "no": 228}, {"category": 1, "no": 303}],
    },
    {
        "name": "穴あき細半円柱",
        "id": [{"category": 0, "no": 229}, {"category": 1, "no": 304}],
    },
    {
        "name": "穴あき細四半円柱",
        "id": [{"category": 0, "no": 230}, {"category": 1, "no": 305}],
    },
    {"name": "六角", "id": [{"category": 0, "no": 231}, {"category": 1, "no": 306}]},
    {"name": "六角半", "id": [{"category": 0, "no": 232}, {"category": 1, "no": 307}]},
    {
        "name": "六角四半",
        "id": [{"category": 0, "no": 233}, {"category": 1, "no": 308}],
    },
    {
        "name": "穴あき六角",
        "id": [{"category": 0, "no": 234}, {"category": 1, "no": 309}],
    },
    {
        "name": "穴あき六角半",
        "id": [{"category": 0, "no": 235}, {"category": 1, "no": 310}],
    },
    {
        "name": "穴あき六角四半",
        "id": [{"category": 0, "no": 236}, {"category": 1, "no": 311}],
    },
    {
        "name": "穴あき細六角",
        "id": [{"category": 0, "no": 237}, {"category": 1, "no": 312}],
    },
    {
        "name": "穴あき細六角半",
        "id": [{"category": 0, "no": 238}, {"category": 1, "no": 313}],
    },
    {
        "name": "穴あき細六角四半",
        "id": [{"category": 0, "no": 239}, {"category": 1, "no": 314}],
    },
    {"name": "リング", "id": [{"category": 0, "no": 240}, {"category": 1, "no": 315}]},
    {
        "name": "半リング",
        "id": [{"category": 0, "no": 241}, {"category": 1, "no": 316}],
    },
    {
        "name": "四半リング",
        "id": [{"category": 0, "no": 242}, {"category": 1, "no": 317}],
    },
    {
        "name": "細リング",
        "id": [{"category": 0, "no": 243}, {"category": 1, "no": 318}],
    },
    {
        "name": "半細リング",
        "id": [{"category": 0, "no": 244}, {"category": 1, "no": 319}],
    },
    {
        "name": "四半細リング",
        "id": [{"category": 0, "no": 245}, {"category": 1, "no": 320}],
    },
    {"name": "ハート", "id": [{"category": 0, "no": 246}, {"category": 1, "no": 321}]},
    {
        "name": "半ハート",
        "id": [{"category": 0, "no": 247}, {"category": 1, "no": 322}],
    },
    {"name": "ダイヤ", "id": [{"category": 0, "no": 248}, {"category": 1, "no": 323}]},
    {
        "name": "半ダイヤ",
        "id": [{"category": 0, "no": 249}, {"category": 1, "no": 324}],
    },
    {
        "name": "四半ダイヤ",
        "id": [{"category": 0, "no": 250}, {"category": 1, "no": 325}],
    },
    {"name": "十字", "id": [{"category": 0, "no": 251}, {"category": 1, "no": 326}]},
    {"name": "細十字", "id": [{"category": 0, "no": 252}, {"category": 1, "no": 327}]},
    {"name": "矢印", "id": [{"category": 0, "no": 253}, {"category": 1, "no": 328}]},
    {"name": "半矢印", "id": [{"category": 0, "no": 254}, {"category": 1, "no": 329}]},
    {"name": "細矢印", "id": [{"category": 0, "no": 255}, {"category": 1, "no": 330}]},
    {
        "name": "半細矢印",
        "id": [{"category": 0, "no": 256}, {"category": 1, "no": 331}],
    },
    {"name": "ボルト1", "id": [{"category": 0, "no": 257}, {"category": 1, "no": 332}]},
    {"name": "ボルト2", "id": [{"category": 0, "no": 258}, {"category": 1, "no": 333}]},
    {"name": "歯車1", "id": [{"category": 0, "no": 259}, {"category": 1, "no": 334}]},
    {"name": "歯車2", "id": [{"category": 0, "no": 260}, {"category": 1, "no": 335}]},
    {"name": "歯車3", "id": [{"category": 0, "no": 261}, {"category": 1, "no": 336}]},
    {"name": "歯車4", "id": [{"category": 0, "no": 262}, {"category": 1, "no": 337}]},
    {"name": "歯車5", "id": [{"category": 0, "no": 263}, {"category": 1, "no": 338}]},
    {"name": "歯車6", "id": [{"category": 0, "no": 264}, {"category": 1, "no": 339}]},
    {"name": "歯車7", "id": [{"category": 0, "no": 265}, {"category": 1, "no": 340}]},
    {"name": "歯車8", "id": [{"category": 0, "no": 266}, {"category": 1, "no": 341}]},
]

FOLDER_TYPE = 3
ITEM_TYPE = 1


def find_top_level_folders(objects):
    """
    トップレベル（一番上の階層）のフォルダのみをリストアップする
    """
    folders = []

    for key, obj in objects.items():
        obj_type = obj.get("type")
        data = obj.get("data", {})

        if obj_type == FOLDER_TYPE:
            folder_name = data.get("name", "")
            child_list = data.get("child", [])
            folders.append(
                {
                    "name": folder_name,
                    "child_count": len(child_list),
                    "obj": obj,
                    "key": key,
                }
            )

    return folders


def find_folders_by_pattern(hs, pattern):
    """
    指定したパターン（文字列）を含むフォルダをすべて再帰的に検索する
    walk()メソッドを使用して全オブジェクトを走査する
    """
    matched_folders = []

    for key, obj in hs.walk():
        if obj.get("type") == FOLDER_TYPE:
            data = obj.get("data", {})
            folder_name = data.get("name", "")

            if pattern in folder_name:
                child_list = data.get("child", [])
                matched_folders.append(
                    {
                        "name": folder_name,
                        "key": key,
                        "child_count": len(child_list),
                        "obj": obj,
                    }
                )

    return matched_folders


def build_plane_conversion_map(plane_map_chara_dict):
    """変換用のマッピングを構築"""
    to_map = {}
    to_chara = {}

    for item in plane_map_chara_dict:
        ids = item["id"]
        map_id = next((x for x in ids if x["category"] == 0), None)
        chara_id = next((x for x in ids if x["category"] == 1), None)

        if map_id and chara_id:
            key_chara = (chara_id["category"], chara_id["no"])
            to_map[key_chara] = (map_id["category"], map_id["no"])

            key_map = (map_id["category"], map_id["no"])
            to_chara[key_map] = (chara_id["category"], chara_id["no"])

    return to_map, to_chara


def set_folder_items_light_type(
    folder_obj, plane_map_chara_dict, target_light="map", alpha=None
):
    """
    フォルダ以下のすべてのアイテムを、マップライトまたはキャラライトに統一する
    """
    to_map, to_chara = build_plane_conversion_map(plane_map_chara_dict)
    conversion_map = to_map if target_light == "map" else to_chara
    target_category = 0 if target_light == "map" else 1

    converted_count = 0

    def traverse_and_convert(obj):
        nonlocal converted_count
        obj_type = obj.get("type")
        data = obj.get("data", {})

        if obj_type == ITEM_TYPE:
            current_key = (data.get("category"), data.get("no"))

            if data.get("category") == target_category:
                pass
            elif current_key in conversion_map:
                new_category, new_no = conversion_map[current_key]
                data["category"] = new_category
                data["no"] = new_no
                converted_count += 1
                # マップライトへの変換時にアルファ値を設定
                if target_light == "map" and alpha is not None:
                    colors = data.get("colors", [])
                    for color in colors:
                        color["a"] = alpha

            for child in data.get("child", []):
                traverse_and_convert(child)

        elif obj_type == FOLDER_TYPE:
            for child in data.get("child", []):
                traverse_and_convert(child)

        elif isinstance(data.get("child"), list):
            for child in data["child"]:
                traverse_and_convert(child)
        elif isinstance(data.get("child"), dict):
            for child_list in data["child"].values():
                for child in child_list:
                    traverse_and_convert(child)

    traverse_and_convert(folder_obj)
    return converted_count


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

        st.success(f"{get_text('success_load', lang)} {uploaded_file.name}")

        # トップレベルのフォルダを取得
        folders = find_top_level_folders(hs.objects)

        st.subheader(get_text("folder_selection_title", lang))

        # 選択方法の切り替え
        selection_mode = st.radio(
            get_text("folder_selection_mode", lang),
            options=["dropdown", "pattern"],
            format_func=lambda x: get_text("mode_dropdown", lang)
            if x == "dropdown"
            else get_text("mode_pattern", lang),
            horizontal=True,
        )

        target_folders = []

        if selection_mode == "dropdown":
            # 既存のドロップダウン方式
            if not folders:
                st.warning(get_text("warning_no_folders", lang))
            else:
                folder_options = {
                    f"{f['name']} ({f['child_count']} children)": i
                    for i, f in enumerate(folders)
                }

                selected_folder_name = st.selectbox(
                    get_text("folder_selection_label", lang),
                    options=list(folder_options.keys()),
                    help=get_text("folder_selection_help", lang),
                )

                selected_folder_idx = folder_options[selected_folder_name]
                target_folders = [folders[selected_folder_idx]]

        else:
            # パターンマッチ方式
            pattern = st.text_input(
                get_text("pattern_input_label", lang),
                help=get_text("pattern_input_help", lang),
            )

            if pattern:
                matched = find_folders_by_pattern(hs, pattern)
                if matched:
                    st.info(
                        get_text("matched_folders", lang).format(count=len(matched))
                    )
                    # マッチしたフォルダを表示
                    with st.expander("Matched folders", expanded=False):
                        for f in matched:
                            st.write(
                                f"- {f['name']} (key: {f['key']}, {f['child_count']} children)"
                            )
                    target_folders = matched
                else:
                    st.warning(get_text("no_matched_folders", lang))

        # 変換対象がある場合のみ続行
        if target_folders:
            # 変換先の選択
            st.subheader(get_text("target_selection_title", lang))
            target_light = st.radio(
                get_text("target_selection_label", lang),
                options=["map", "chara"],
                format_func=lambda x: get_text("map_light", lang)
                if x == "map"
                else get_text("chara_light", lang),
                help=get_text("target_selection_help", lang),
            )

            # マップライトへの変換時のみアルファ値を設定可能
            alpha_value = None
            if target_light == "map":
                alpha_value = st.slider(
                    get_text("alpha_slider", lang),
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    help=get_text("alpha_slider_help", lang),
                )

            # 変換実行ボタン
            if st.button(get_text("execute_button", lang), type="primary"):
                # すべてのターゲットフォルダに対して変換を実行
                total_converted = 0
                converted_folder_names = []

                for folder in target_folders:
                    converted_count = set_folder_items_light_type(
                        folder["obj"],
                        PLANE_MAP_CHARA_DICT,
                        target_light=target_light,
                        alpha=alpha_value,
                    )
                    total_converted += converted_count
                    converted_folder_names.append(folder["name"])

                target_name = (
                    get_text("map_light", lang)
                    if target_light == "map"
                    else get_text("chara_light", lang)
                )

                if len(target_folders) == 1:
                    st.success(
                        f"'{converted_folder_names[0]}' {get_text('success_convert', lang).format(count=total_converted, target=target_name, folder=converted_folder_names[0])}"
                    )
                else:
                    folder_list = ", ".join(converted_folder_names)
                    st.success(
                        f"{get_text('success_convert', lang).format(count=total_converted, target=target_name, folder=folder_list)} (folders: {folder_list})"
                    )

                # タイトルに変換先を追加
                suffix = "(マップ)" if target_light == "map" else "(キャラ)"
                hs.title = hs.title + suffix

                # ダウンロード用にファイルを生成
                output = io.BytesIO()
                hs.save(output)
                output.seek(0)

                # 出力ファイル名を生成
                original_name = uploaded_file.name.rsplit(".", 1)[0]
                output_filename = f"{original_name}_{target_light}.png"

                st.download_button(
                    label=get_text("download_button", lang),
                    data=output,
                    file_name=output_filename,
                    mime="image/png",
                )

    except Exception as e:
        st.error(f"{get_text('error_occurred', lang)} {e}")
        st.exception(e)
else:
    st.info(get_text("info_upload", lang))
