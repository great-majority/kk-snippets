import io
import streamlit as st
from kkloader import HoneycomeSceneData

st.set_page_config(page_title="デジクラアイテム変換", page_icon=":arrows_counterclockwise:")
st.title("デジクラアイテム変換ツール")
st.write("シーンデータ内のプレーンアイテムをマップ/キャラ間で変換します。")

# 使い方の説明
with st.expander("使い方"):
    st.markdown("""
    1. デジタルクラフトのシーンデータ（.png）をアップロードします
    2. トップレベルのフォルダから変換対象を選択します
    3. 変換先（マップライト or キャラライト）を選択します
    4. 「変換を実行」ボタンをクリックします
    5. 変換済みファイルをダウンロードします

    **注意:**
    - シーンのタイトル名に変換先にした"(マップ)"か"(キャラ)"がつきます
    - 処理を軽くするため、ワークスペースの最も階層が上のフォルダのみ選択できるようになってます
    - 選択したフォルダ以下のすべてのサブフォルダ内のアイテムも再帰的に変換されます
    """)

# マップ/キャラ変換用の辞書
PLANE_MAP_CHARA_DICT = [
    {"name": "丸", "id": [{"category": 0, "no": 192}, {"category": 1, "no": 267}]},
    {"name": "半丸", "id": [{"category": 0, "no": 193}, {"category": 1, "no": 268}]},
    {"name": "四半丸", "id": [{"category": 0, "no": 194}, {"category": 1, "no": 269}]},
    {"name": "穴あき丸", "id": [{"category": 0, "no": 195}, {"category": 1, "no": 270}]},
    {"name": "穴あき半丸", "id": [{"category": 0, "no": 196}, {"category": 1, "no": 271}]},
    {"name": "穴あき四半丸", "id": [{"category": 0, "no": 197}, {"category": 1, "no": 272}]},
    {"name": "平らな円", "id": [{"category": 0, "no": 198}, {"category": 1, "no": 273}]},
    {"name": "平らな半円", "id": [{"category": 0, "no": 199}, {"category": 1, "no": 274}]},
    {"name": "平らな四半円", "id": [{"category": 0, "no": 200}, {"category": 1, "no": 275}]},
    {"name": "コーン", "id": [{"category": 0, "no": 201}, {"category": 1, "no": 276}]},
    {"name": "半コーン", "id": [{"category": 0, "no": 202}, {"category": 1, "no": 277}]},
    {"name": "四半コーン", "id": [{"category": 0, "no": 203}, {"category": 1, "no": 278}]},
    {"name": "四角錐", "id": [{"category": 0, "no": 204}, {"category": 1, "no": 279}]},
    {"name": "半四角錐", "id": [{"category": 0, "no": 205}, {"category": 1, "no": 280}]},
    {"name": "四半四角錐", "id": [{"category": 0, "no": 206}, {"category": 1, "no": 281}]},
    {"name": "三角錐", "id": [{"category": 0, "no": 207}, {"category": 1, "no": 282}]},
    {"name": "四角", "id": [{"category": 0, "no": 208}, {"category": 1, "no": 283}]},
    {"name": "穴あき四角", "id": [{"category": 0, "no": 209}, {"category": 1, "no": 284}]},
    {"name": "穴あき四角半", "id": [{"category": 0, "no": 210}, {"category": 1, "no": 285}]},
    {"name": "穴あき四角四半", "id": [{"category": 0, "no": 211}, {"category": 1, "no": 286}]},
    {"name": "穴あき細四角", "id": [{"category": 0, "no": 212}, {"category": 1, "no": 287}]},
    {"name": "穴あき細四角半", "id": [{"category": 0, "no": 213}, {"category": 1, "no": 288}]},
    {"name": "穴あき細四角四半", "id": [{"category": 0, "no": 214}, {"category": 1, "no": 289}]},
    {"name": "平面", "id": [{"category": 0, "no": 215}, {"category": 1, "no": 290}]},
    {"name": "三角柱", "id": [{"category": 0, "no": 216}, {"category": 1, "no": 291}]},
    {"name": "半三角柱", "id": [{"category": 0, "no": 217}, {"category": 1, "no": 292}]},
    {"name": "三角柱三等分", "id": [{"category": 0, "no": 218}, {"category": 1, "no": 293}]},
    {"name": "穴あき三角柱", "id": [{"category": 0, "no": 219}, {"category": 1, "no": 294}]},
    {"name": "穴あき半三角柱", "id": [{"category": 0, "no": 220}, {"category": 1, "no": 295}]},
    {"name": "穴あき三角柱三等分", "id": [{"category": 0, "no": 221}, {"category": 1, "no": 296}]},
    {"name": "円柱", "id": [{"category": 0, "no": 222}, {"category": 1, "no": 297}]},
    {"name": "半円柱", "id": [{"category": 0, "no": 223}, {"category": 1, "no": 298}]},
    {"name": "四半円柱", "id": [{"category": 0, "no": 224}, {"category": 1, "no": 299}]},
    {"name": "穴あき円柱", "id": [{"category": 0, "no": 225}, {"category": 1, "no": 300}]},
    {"name": "穴あき半円柱", "id": [{"category": 0, "no": 226}, {"category": 1, "no": 301}]},
    {"name": "穴あき四半円柱", "id": [{"category": 0, "no": 227}, {"category": 1, "no": 302}]},
    {"name": "穴あき細円柱", "id": [{"category": 0, "no": 228}, {"category": 1, "no": 303}]},
    {"name": "穴あき細半円柱", "id": [{"category": 0, "no": 229}, {"category": 1, "no": 304}]},
    {"name": "穴あき細四半円柱", "id": [{"category": 0, "no": 230}, {"category": 1, "no": 305}]},
    {"name": "六角", "id": [{"category": 0, "no": 231}, {"category": 1, "no": 306}]},
    {"name": "六角半", "id": [{"category": 0, "no": 232}, {"category": 1, "no": 307}]},
    {"name": "六角四半", "id": [{"category": 0, "no": 233}, {"category": 1, "no": 308}]},
    {"name": "穴あき六角", "id": [{"category": 0, "no": 234}, {"category": 1, "no": 309}]},
    {"name": "穴あき六角半", "id": [{"category": 0, "no": 235}, {"category": 1, "no": 310}]},
    {"name": "穴あき六角四半", "id": [{"category": 0, "no": 236}, {"category": 1, "no": 311}]},
    {"name": "穴あき細六角", "id": [{"category": 0, "no": 237}, {"category": 1, "no": 312}]},
    {"name": "穴あき細六角半", "id": [{"category": 0, "no": 238}, {"category": 1, "no": 313}]},
    {"name": "穴あき細六角四半", "id": [{"category": 0, "no": 239}, {"category": 1, "no": 314}]},
    {"name": "リング", "id": [{"category": 0, "no": 240}, {"category": 1, "no": 315}]},
    {"name": "半リング", "id": [{"category": 0, "no": 241}, {"category": 1, "no": 316}]},
    {"name": "四半リング", "id": [{"category": 0, "no": 242}, {"category": 1, "no": 317}]},
    {"name": "細リング", "id": [{"category": 0, "no": 243}, {"category": 1, "no": 318}]},
    {"name": "半細リング", "id": [{"category": 0, "no": 244}, {"category": 1, "no": 319}]},
    {"name": "四半細リング", "id": [{"category": 0, "no": 245}, {"category": 1, "no": 320}]},
    {"name": "ハート", "id": [{"category": 0, "no": 246}, {"category": 1, "no": 321}]},
    {"name": "半ハート", "id": [{"category": 0, "no": 247}, {"category": 1, "no": 322}]},
    {"name": "ダイヤ", "id": [{"category": 0, "no": 248}, {"category": 1, "no": 323}]},
    {"name": "半ダイヤ", "id": [{"category": 0, "no": 249}, {"category": 1, "no": 324}]},
    {"name": "四半ダイヤ", "id": [{"category": 0, "no": 250}, {"category": 1, "no": 325}]},
    {"name": "十字", "id": [{"category": 0, "no": 251}, {"category": 1, "no": 326}]},
    {"name": "細十字", "id": [{"category": 0, "no": 252}, {"category": 1, "no": 327}]},
    {"name": "矢印", "id": [{"category": 0, "no": 253}, {"category": 1, "no": 328}]},
    {"name": "半矢印", "id": [{"category": 0, "no": 254}, {"category": 1, "no": 329}]},
    {"name": "細矢印", "id": [{"category": 0, "no": 255}, {"category": 1, "no": 330}]},
    {"name": "半細矢印", "id": [{"category": 0, "no": 256}, {"category": 1, "no": 331}]},
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
            folders.append({
                "name": folder_name,
                "child_count": len(child_list),
                "obj": obj,
                "key": key,
            })

    return folders


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


def set_folder_items_light_type(folder_obj, plane_map_chara_dict, target_light="map", alpha=None):
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
    "シーンデータ（PNG）をアップロード",
    type=["png"],
    help="デジタルクラフトのシーンデータ（.png）をアップロードしてください"
)

if uploaded_file is not None:
    try:
        # ファイルを読み込み
        file_bytes = uploaded_file.read()
        hs = HoneycomeSceneData.load(io.BytesIO(file_bytes))

        st.success(f"シーンデータを読み込みました: {uploaded_file.name}")

        # トップレベルのフォルダを取得
        folders = find_top_level_folders(hs.objects)

        if not folders:
            st.warning("トップレベルにフォルダが見つかりませんでした。")
        else:
            st.subheader("フォルダ選択")

            # フォルダ選択用のドロップダウン
            folder_options = {
                f"{f['name']} ({f['child_count']} children)": i
                for i, f in enumerate(folders)
            }

            selected_folder_name = st.selectbox(
                "変換対象のフォルダを選択",
                options=list(folder_options.keys()),
                help="選択したフォルダ以下のすべてのアイテムが変換されます"
            )

            selected_folder_idx = folder_options[selected_folder_name]
            selected_folder = folders[selected_folder_idx]

            # 変換先の選択
            st.subheader("変換先の選択")
            target_light = st.radio(
                "変換先を選択",
                options=["map", "chara"],
                format_func=lambda x: "マップライト" if x == "map" else "キャラライト",
                help="マップライト: category=0, キャラライト: category=1"
            )

            # マップライトへの変換時のみアルファ値を設定可能
            alpha_value = None
            if target_light == "map":
                alpha_value = st.slider(
                    "アルファ値（透明度）",
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.01,
                    help="0: 完全に透明、1: 完全に不透明"
                )

            # 変換実行ボタン
            if st.button("変換を実行", type="primary"):
                # 変換を実行
                converted_count = set_folder_items_light_type(
                    selected_folder["obj"],
                    PLANE_MAP_CHARA_DICT,
                    target_light=target_light,
                    alpha=alpha_value
                )

                target_name = "マップライト" if target_light == "map" else "キャラライト"
                st.success(f"'{selected_folder['name']}' 以下の {converted_count} 個のアイテムを{target_name}に変換しました")

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
                    label="変換済みファイルをダウンロード",
                    data=output,
                    file_name=output_filename,
                    mime="image/png"
                )

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.exception(e)
else:
    st.info("シーンデータ（.png）をアップロードしてください。")
