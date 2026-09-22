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
2. セーブコメントを入力し、NPCを選択してパラメータや行動回数を編集する
3. 「編集済みセーブデータをダウンロード」を押す
4. ダウンロードしたファイル名から `modified_` を削除し、元のセーブフォルダへ戻す
5. ゲームを起動して反映を確認する

#### 効率よくイベントシーンを回収する方法

「このキャラをイベント開始状態にする」ボタンを押せばイベント開始状態に設定されます。そのままセーブデータをダウンロードし起動すればイベント回収できます。
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
        "set_event_ready": "このキャラをイベント開始状態にする",
        "set_everyone_event_ready": "全員をイベント開始状態にする",
        "favorability": "親密度",
        "inclusiveness": "包容力",
        "proactivity": "積極性",
        "curiosity": "好奇心",
        "save_comment": "セーブコメント",
        "game_counts": "行動回数",
        "h_count": "H回数",
        "massage_count": "マッサージ回数",
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
2. Edit the save comment, then select an NPC and edit their parameters and action counts
3. Press “Download modified save data”
4. Remove `modified_` from the downloaded filename and return it to the save folder
5. Launch the game and verify the changes

#### How to efficiently collect event scenes

Click “Set this character to event-ready state” to configure the character for the event. Then download the save data and launch the game to view the event.
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
        "set_event_ready": "Set this character to event-ready state",
        "set_everyone_event_ready": "Set everyone to event-ready state",
        "favorability": "Intimacy",
        "inclusiveness": "Inclusiveness",
        "proactivity": "Proactivity",
        "curiosity": "Curiosity",
        "save_comment": "Save comment",
        "game_counts": "Action counts",
        "h_count": "H count",
        "massage_count": "Massage count",
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

GAME_COUNTS = {
    "H": "h_count",
    "Massage": "massage_count",
}

EVENT_READY_COUNTS = {
    0: {"H": 0, "Massage": 1},
    1: {"H": 1, "Massage": 0},
    2: {"H": 1, "Massage": 1},
    3: {"H": 1, "Massage": 1},
    4: {"H": 1, "Massage": 1},
    5: {"H": 2, "Massage": 0},
}


def get_text(key, lang="ja"):
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


def chara_name(record):
    parameter = record["chara"]["Parameter"]
    return f"{parameter['lastname']} {parameter['firstname']}".strip()


def parameter_widget_key(prefix, parameter_name, member):
    return f"{prefix}_{parameter_name}_{member}"


def game_count_widget_key(prefix, count_name):
    return f"{prefix}_GameCount_{count_name}"


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


def set_event_ready(fields, prefix):
    favorability = fields["GameParameter"]["Favorability"]
    counts = EVENT_READY_COUNTS.get(int(favorability["LV"]))
    if counts is None:
        return

    favorability["Point"] = 100
    favorability["IsMaxLv"] = False
    st.session_state[parameter_widget_key(prefix, "Favorability", "Point")] = 100

    game_count = fields["GameCount"]
    for count_name, value in counts.items():
        game_count[count_name] = value
        st.session_state[game_count_widget_key(prefix, count_name)] = value


def sync_parameter_widgets(fields, prefix):
    """Apply editor state before the download button is constructed."""
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

    game_count = fields["GameCount"]
    for count_name in GAME_COUNTS:
        key = game_count_widget_key(prefix, count_name)
        if key in st.session_state:
            game_count[count_name] = int(st.session_state[key])


def render_editor(record, lang, prefix):
    fields = record["fields"]
    game_parameter = fields["GameParameter"]

    max_col, event_col = st.columns(2)
    max_col.button(
        get_text("set_all_max", lang),
        key=f"{prefix}_all_max",
        on_click=set_all_parameters_max,
        args=(fields, prefix),
    )
    event_col.button(
        get_text("set_event_ready", lang),
        key=f"{prefix}_event_ready",
        on_click=set_event_ready,
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

    st.markdown(f"#### {get_text('game_counts', lang)}")
    count_columns = st.columns(len(GAME_COUNTS))
    game_count = fields["GameCount"]
    for column, (count_name, label_key) in zip(count_columns, GAME_COUNTS.items()):
        key = game_count_widget_key(prefix, count_name)
        current = int(game_count[count_name])
        st.session_state.setdefault(key, current)
        game_count[count_name] = int(
            column.number_input(
                get_text(label_key, lang),
                min_value=0,
                max_value=2_147_483_647,
                step=1,
                key=key,
            )
        )


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
    comment_key = f"{file_hash[:8]}_save_comment"
    st.session_state.setdefault(comment_key, save.core.get("Comment") or "")
    save.core["Comment"] = st.text_input(
        get_text("save_comment", lang),
        key=comment_key,
    )

    max_col, event_col, download_col = st.columns(3)
    if max_col.button(
        get_text("set_everyone_max", lang),
        key=f"{file_hash[:8]}_everyone_max",
    ):
        for _, _, npc, prefix in targets:
            set_all_parameters_max(npc["fields"], prefix)
    if event_col.button(
        get_text("set_everyone_event_ready", lang),
        key=f"{file_hash[:8]}_everyone_event_ready",
    ):
        for _, _, npc, prefix in targets:
            set_event_ready(npc["fields"], prefix)
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
