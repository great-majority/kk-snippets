import hashlib
import io

import streamlit as st
from kkloader import AmanatsuSaveData

TRANSLATIONS = {
    "ja": {
        "title": "甘夏ろけーしょんセーブデータエディター",
        "description": """
[甘夏ろけーしょん](https://www.illgames.jp/product/amaloca/)のセーブデータを読み込み、キャラの各パラメータ(親密度など)を編集するツールです。

キャラクターを選択して値を変更した後、編集済みのセーブデータをダウンロードしてください。

**⚠️注意事項**: バグなどあるかもしれませんので、編集前のデータのバックアップはとっておきましょう!
""",
        "usage_header": "使い方",
        "usage": """
1. セーブフォルダ (`AmanatsuLocation/UserData/save/user`) にあるセーブデータ（例: `001.sav`）を読み込む
2. NPCを選択してパラメータを編集する
3. 「編集済みセーブデータをダウンロード」を押す
4. ダウンロードしたファイル名から `modified_` を削除し、元のセーブフォルダへ戻す
5. ゲームを起動して反映を確認する
""",
        "file_uploader": "甘夏ろけーしょんのセーブデータ (.sav) を選択",
        "error_load": "ファイルを読み込めませんでした。未対応または破損したセーブデータです。",
        "success_load": "セーブデータを読み込みました。",
        "select_chara": "編集するNPC",
        "no_chara": "編集できるNPCがいません。",
        "point": "Point",
        "level": "LV",
        "set_all_max": "このNPCの全パラメータをMAXにする",
        "set_everyone_max": "全NPCの全パラメータをMAXにする",
        "favorability": "親密度",
        "inclusiveness": "包容力",
        "proactivity": "積極性",
        "curiosity": "好奇心",
        "download_chara": "キャラクターデータをダウンロード",
        "download_save": "編集済みセーブデータをダウンロード",
    },
    "en": {
        "title": "Amanatsu Location Save Data Editor",
        "description": """
A tool for editing character parameters (such as intimacy) in [Amanatsu Location](https://www.illgames.jp/product/amaloca/) save data.

Select a character, edit the values, then download the modified save data.

**⚠️Caution**: There may be bugs, so be sure to back up your data before editing!
""",
        "usage_header": "How to use",
        "usage": """
1. Load a save file (for example, `001.sav`) from `AmanatsuLocation/UserData/save/user`
2. Select an NPC and edit their parameters
3. Press “Download modified save data”
4. Remove `modified_` from the downloaded filename and return it to the save folder
5. Launch the game and verify the changes
""",
        "file_uploader": "Select Amanatsu Location save data (.sav)",
        "error_load": "Failed to load the file. It may be unsupported or corrupted.",
        "success_load": "Save data loaded successfully.",
        "select_chara": "NPC to edit",
        "no_chara": "No editable NPCs found.",
        "point": "Point",
        "level": "LV",
        "set_all_max": "Max all parameters for this NPC",
        "set_everyone_max": "Max all parameters for every NPC",
        "favorability": "Intimacy",
        "inclusiveness": "Inclusiveness",
        "proactivity": "Proactivity",
        "curiosity": "Curiosity",
        "download_chara": "Download character data",
        "download_save": "Download modified save data",
    },
}


# MAX states observed in an in-game save. Favorability uses a different final
# state from the other three parameters: its Point returns to zero at LV 6.
PARAMETERS = {
    "Favorability": {"label": "favorability", "point": 0, "level": 6},
    "Inclusiveness": {"label": "inclusiveness", "point": 100, "level": 4},
    "Proactivity": {"label": "proactivity", "point": 100, "level": 4},
    "Curiosity": {"label": "curiosity", "point": 100, "level": 4},
}


def get_text(key, lang="ja"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


def chara_name(record):
    parameter = record["chara"]["Parameter"]
    return f"{parameter['lastname']} {parameter['firstname']}".strip()


def parameter_widget_key(prefix, parameter_name, member):
    return f"{prefix}_{parameter_name}_{member}"


def set_parameter_max(fields, parameter_name, prefix):
    maximum = PARAMETERS[parameter_name]
    parameter = fields["GameParameter"][parameter_name]
    values = {
        "Point": maximum["point"],
        "LV": maximum["level"],
        "IsMaxLv": True,
    }
    parameter.update(values)
    for member in ("Point", "LV"):
        value = values[member]
        st.session_state[parameter_widget_key(prefix, parameter_name, member)] = value


def set_all_parameters_max(fields, prefix):
    for parameter_name in PARAMETERS:
        set_parameter_max(fields, parameter_name, prefix)


def sync_parameter_widgets(fields, prefix):
    """Apply slider state before the download button is constructed."""
    game_parameter = fields["GameParameter"]
    for parameter_name, config in PARAMETERS.items():
        parameter = game_parameter[parameter_name]
        point_key = parameter_widget_key(prefix, parameter_name, "Point")
        level_key = parameter_widget_key(prefix, parameter_name, "LV")
        if point_key in st.session_state:
            parameter["Point"] = int(st.session_state[point_key])
        if level_key in st.session_state:
            parameter["LV"] = int(st.session_state[level_key])
        parameter["IsMaxLv"] = parameter["LV"] >= config["level"]


def render_editor(record, lang, prefix):
    fields = record["fields"]
    game_parameter = fields["GameParameter"]

    st.button(
        get_text("set_all_max", lang),
        key=f"{prefix}_all_max",
        on_click=set_all_parameters_max,
        args=(fields, prefix),
    )

    for parameter_name, config in PARAMETERS.items():
        parameter = game_parameter[parameter_name]
        label = get_text(config["label"], lang)
        st.markdown(f"#### {label}")

        point_col, level_col = st.columns(2)

        point_key = parameter_widget_key(prefix, parameter_name, "Point")
        level_key = parameter_widget_key(prefix, parameter_name, "LV")
        st.session_state.setdefault(point_key, int(parameter["Point"]))
        st.session_state.setdefault(level_key, int(parameter["LV"]))

        point_limit = max(100, int(parameter["Point"]), st.session_state[point_key])
        level_limit = max(
            config["level"], int(parameter["LV"]), st.session_state[level_key]
        )

        parameter["Point"] = int(
            point_col.slider(
                get_text("point", lang),
                min_value=min(0, int(parameter["Point"])),
                max_value=point_limit,
                step=1,
                key=point_key,
            )
        )
        parameter["LV"] = int(
            level_col.slider(
                get_text("level", lang),
                min_value=min(0, int(parameter["LV"])),
                max_value=level_limit,
                step=1,
                key=level_key,
            )
        )
        parameter["IsMaxLv"] = parameter["LV"] >= config["level"]


title = get_text("title", "ja")
st.set_page_config(page_title=title, layout="wide")

lang = st.session_state.get("lang", "ja")

st.title(get_text("title", lang))
st.divider()
st.markdown(get_text("description", lang))

with st.expander(get_text("usage_header", lang)):
    st.markdown(get_text("usage", lang))

file = st.file_uploader(get_text("file_uploader", lang), type=["sav"])
if file is not None:
    data = file.getvalue()
    file_hash = hashlib.sha1(data).hexdigest()

    if st.session_state.get("alse_hash") != file_hash:
        try:
            st.session_state["alse_sav"] = AmanatsuSaveData.load(data)
        except Exception:
            st.error(get_text("error_load", lang), icon="🚨")
            st.stop()
        st.session_state["alse_hash"] = file_hash

    save = st.session_state["alse_sav"]
    st.success(get_text("success_load", lang), icon="✅")

    targets = []
    for slot, npc in enumerate(save.npcs):
        if npc is None:
            continue
        prefix = f"{file_hash[:8]}_npc_{slot}"
        label = f"NPC #{slot}  {chara_name(npc)}"
        targets.append((label, slot, npc, prefix))

    if not targets:
        st.info(get_text("no_chara", lang))
        st.stop()

    for _, _, npc, prefix in targets:
        sync_parameter_widgets(npc["fields"], prefix)

    st.divider()
    max_col, download_col = st.columns(2)
    if max_col.button(
        get_text("set_everyone_max", lang),
        key=f"{file_hash[:8]}_everyone_max",
    ):
        for _, _, npc, prefix in targets:
            set_all_parameters_max(npc["fields"], prefix)
    download_col.download_button(
        get_text("download_save", lang),
        bytes(save),
        f"modified_{file.name}",
    )

    selected = st.selectbox(
        get_text("select_chara", lang),
        range(len(targets)),
        format_func=lambda index: targets[index][0],
    )
    _, _, record, prefix = targets[selected]

    left, right = st.columns([1, 2])
    with left:
        image = getattr(record["chara"], "image", None)
        if image:
            st.image(io.BytesIO(image), caption=chara_name(record), width=280)
        st.download_button(
            get_text("download_chara", lang),
            bytes(record["chara"]),
            f"{chara_name(record)}.png",
            key=f"{prefix}_download_chara",
        )

    with right:
        render_editor(record, lang, prefix)
