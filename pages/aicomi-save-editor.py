import hashlib
import io

import streamlit as st
from kkloader import AicomiSaveData

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "アイコミセーブデータエディター",
        "description": """
[アイコミ](https://www.illgames.jp/product/aicomi/)のセーブデータを読み込み、キャラクターの好感度などのパラメータを編集するツールです。

キャラクターを選択し、値を変更したら下のボタンからセーブデータをダウンロードしてください。

**⚠️注意事項**: バグなどあるかもしれませんので、編集前のデータのバックアップはとっておきましょう!
""",
        "file_uploader": "アイコミのセーブデータ (.sav) を選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "success_load": "正常にデータを読み込めました。",
        "download_button": "改変後のセーブデータをダウンロード",
        "metric_save_time": "セーブ日時",
        "metric_map": "マップID",
        "metric_charas": "キャラクター数",
        "select_chara": "編集するキャラクター",
        "no_chara": "編集できるキャラクターがいません。",
        "kind_npc": "NPC",
        "kind_unique": "ユニークNPC",
        "favor": "好感度",
        "favor_help": "100:友人 → 200:親友 → 300:恋人 に到達で昇格、400が最大",
        "relation": "関係",
        "lewdness": "淫乱度",
        "sexperience": "性経験",
        "virgin": "処女",
        "date_count": "デート回数",
        "resist_header": "開発度",
        "chara_file_name": "キャラカードのファイルパス",
        "relation_labels": {
            0: "0: 知人",
            1: "1: 友人",
            2: "2: 親友",
            3: "3: 恋人",
        },
        "resist_labels": ["口", "胸", "乳首", "股間", "アナル", "お尻"],
        "download_chara": "キャラクターデータをダウンロード",
        "bulk_header": "一括編集",
        "btn_relation_max": "全員の関係値をMAXにする",
        "btn_sexp_max": "全員の性経験をMAXにする",
        "btn_lewd_max": "全員の淫乱度をMAXにする",
        "btn_resist_max": "全員の開発度をMAXにする(全部位)",
    },
    "en": {
        "title": "Aicomi Save Data Editor",
        "description": """
A tool to load [Aicomi](https://www.illgames.jp/product/aicomi/) save data and edit character parameters such as favor values.

Select a character, change values, then download the save data from the button below.

**⚠️Caution**: There may be bugs, so please back up your data before editing!
""",
        "file_uploader": "Select Aicomi save data (.sav)",
        "error_load": "Failed to load file. Unsupported file format.",
        "success_load": "Data loaded successfully.",
        "download_button": "Download modified save data",
        "metric_save_time": "Save time",
        "metric_map": "Map ID",
        "metric_charas": "Characters",
        "select_chara": "Character to edit",
        "no_chara": "No editable characters found.",
        "kind_npc": "NPC",
        "kind_unique": "Unique NPC",
        "favor": "Favor",
        "favor_help": "Reaching 100 Friend → 200 Best friend → 300 Girlfriend promotes the relation, max 400",
        "relation": "Relation",
        "lewdness": "Lewdness",
        "sexperience": "Sexual experience",
        "virgin": "Virgin",
        "date_count": "Date count",
        "resist_header": "Development",
        "chara_file_name": "Character card file path",
        "relation_labels": {
            0: "0: Acquaintance",
            1: "1: Friend",
            2: "2: Best friend",
            3: "3: Girlfriend",
        },
        # AC.User.ResistParts: Mouth, Breast, Nipple, Groin, Anal, Hip
        "resist_labels": ["Mouth", "Breast", "Nipple", "Groin", "Anal", "Hip"],
        "download_chara": "Download character data",
        "bulk_header": "Bulk edit",
        "btn_relation_max": "Max out everyone's relation",
        "btn_sexp_max": "Max out everyone's sexual experience",
        "btn_lewd_max": "Max out everyone's lewdness",
        "btn_resist_max": "Max out everyone's development (all parts)",
    },
}

# ========================================
# 各パラメータの最大値
# ========================================
# FAVOR_MAX / RELATION_MAX: 実セーブで好感度400・関係値3(恋人)が最大値として観測。
# RelationTypes enum には 4:Partner も定義されているが、セーブデータでは未観測のため
# 選択肢からは除外している(値として入っていれば表示はされる)。
# LEWDNESS_MAX: 実セーブで100が観測された値。
# RESIST_MAX: ゲーム内で%表記されるため100。
# SEXPERIENCE_MAX: 正確な上限は未確認(観測最大は39)。ゲージ表示が0-100系のため100としている。
FAVOR_MAX = 400
RELATION_MAX = 3
LEWDNESS_MAX = 100
SEXPERIENCE_MAX = 100
RESIST_MAX = 100


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


def chara_name(record):
    p = record["chara"]["Parameter"]
    return f"{p['lastname']} {p['firstname']}".strip()


# fields内のキー -> ウィジェットキーの接尾辞。
# 一括編集で表示中ウィジェットの値も更新するため、対応を共有する。
WIDGET_SUFFIX = {
    "FavorValue": "favor",
    "RelationValue": "relation",
    "LewdnessValue": "lewdness",
    "_sexperience": "sexp",
    "IsVirginFlag": "virgin",
    "DateCount": "date",
    "CharaFileName": "filename",
}


def widget_key(prefix, field):
    return f"{prefix}_{WIDGET_SUFFIX[field]}"


# ウィジェットはsession_stateを唯一の値の置き場とする(デフォルト値は渡さない)。
# デフォルト値方式だと、一括編集でfieldsを書き換えても表示中ウィジェットが
# 古い値を保持し続け、次のrerunでその古い値がfieldsへ書き戻されてしまう。


def number_field(fields, key, label, wkey, min_value=0, max_value=None, help=None):
    """fields[key] を編集するnumber_input。存在しないフィールドは表示しない。"""
    if key not in fields:
        return
    current = int(fields[key])
    st.session_state.setdefault(wkey, current)
    if max_value is not None:
        max_value = max(max_value, current, st.session_state[wkey])
    fields[key] = int(
        st.number_input(
            label,
            min_value=min(min_value, current),
            max_value=max_value,
            step=1,
            key=wkey,
            help=help,
        )
    )


def render_editor(record, lang, wkey_prefix):
    fields = record["fields"]

    number_field(
        fields,
        "FavorValue",
        get_text("favor", lang),
        f"{wkey_prefix}_favor",
        max_value=FAVOR_MAX,
        help=get_text("favor_help", lang),
    )

    if "RelationValue" in fields:
        labels = get_text("relation_labels", lang)
        options = list(labels.keys())
        wkey = widget_key(wkey_prefix, "RelationValue")
        st.session_state.setdefault(wkey, int(fields["RelationValue"]))
        if st.session_state[wkey] not in options:
            options.append(st.session_state[wkey])
        fields["RelationValue"] = st.selectbox(
            get_text("relation", lang),
            options,
            format_func=lambda v: labels.get(v, f"{v}: ?"),
            key=wkey,
        )

    number_field(
        fields,
        "LewdnessValue",
        get_text("lewdness", lang),
        f"{wkey_prefix}_lewdness",
        max_value=LEWDNESS_MAX,
    )
    number_field(
        fields,
        "_sexperience",
        get_text("sexperience", lang),
        f"{wkey_prefix}_sexp",
        max_value=SEXPERIENCE_MAX,
    )

    if "IsVirginFlag" in fields:
        wkey = widget_key(wkey_prefix, "IsVirginFlag")
        st.session_state.setdefault(wkey, bool(fields["IsVirginFlag"]))
        fields["IsVirginFlag"] = st.checkbox(get_text("virgin", lang), key=wkey)

    number_field(
        fields,
        "DateCount",
        get_text("date_count", lang),
        f"{wkey_prefix}_date",
    )

    resist = fields.get("_resistFlags")
    resist_labels = get_text("resist_labels", lang)
    if resist is not None and len(resist) == len(resist_labels):
        st.markdown(f"##### {get_text('resist_header', lang)}")
        cols = st.columns(len(resist_labels))
        for i, (col, label) in enumerate(zip(cols, resist_labels)):
            with col:
                wkey = f"{wkey_prefix}_resist_{i}"
                st.session_state.setdefault(wkey, int(resist[i]))
                resist[i] = int(
                    st.number_input(
                        label,
                        min_value=min(0, resist[i]),
                        max_value=max(RESIST_MAX, resist[i], st.session_state[wkey]),
                        step=1,
                        key=wkey,
                    )
                )

    if fields.get("CharaFileName") is not None:
        wkey = widget_key(wkey_prefix, "CharaFileName")
        st.session_state.setdefault(wkey, fields["CharaFileName"])
        fields["CharaFileName"] = st.text_input(
            get_text("chara_file_name", lang), key=wkey
        )


def render_bulk_buttons(targets, lang):
    """全キャラクターへ一括で最大値を設定するボタン群。

    fieldsと表示中ウィジェットのsession_stateを同時に更新する。
    """

    def set_all(*pairs):
        for _, rec, prefix in targets:
            for key, value in pairs:
                if key in rec["fields"]:
                    rec["fields"][key] = value
                    st.session_state[widget_key(prefix, key)] = value

    st.markdown(f"##### {get_text('bulk_header', lang)}")
    cols = st.columns(2) + st.columns(2)
    if cols[0].button(get_text("btn_relation_max", lang), width="stretch"):
        set_all(("FavorValue", FAVOR_MAX), ("RelationValue", RELATION_MAX))
    if cols[1].button(get_text("btn_sexp_max", lang), width="stretch"):
        set_all(("_sexperience", SEXPERIENCE_MAX))
    if cols[2].button(get_text("btn_lewd_max", lang), width="stretch"):
        set_all(("LewdnessValue", LEWDNESS_MAX))
    if cols[3].button(get_text("btn_resist_max", lang), width="stretch"):
        for _, rec, prefix in targets:
            resist = rec["fields"].get("_resistFlags")
            if resist is not None:
                resist[:] = [RESIST_MAX] * len(resist)
                for i in range(len(resist)):
                    st.session_state[f"{prefix}_resist_{i}"] = RESIST_MAX


############################################
# Streamlitのロジック部分
############################################
title = get_text("title", "ja")
st.set_page_config(page_title=title, layout="wide")

lang = st.session_state.get("lang", "ja")

st.title(get_text("title", lang))
st.divider()

st.markdown(get_text("description", lang))

file = st.file_uploader(get_text("file_uploader", lang))
if file is not None:
    data = file.getvalue()
    file_hash = hashlib.sha1(data).hexdigest()

    # 編集内容を維持するため、同じファイルの間はセッション内に保持する
    if st.session_state.get("acse_hash") != file_hash:
        try:
            st.session_state["acse_sav"] = AicomiSaveData.load(data)
        except Exception:
            st.error(get_text("error_load", lang), icon="🚨")
            st.stop()
        st.session_state["acse_hash"] = file_hash
    sav = st.session_state["acse_sav"]
    st.success(get_text("success_load", lang), icon="✅")

    c1, c2, c3 = st.columns(3)
    c1.metric(get_text("metric_save_time", lang), sav.core.get("SaveTimeText") or "—")
    c2.metric(get_text("metric_map", lang), sav.core.get("MapID", "—"))
    c3.metric(get_text("metric_charas", lang), len(sav.charas))

    targets = []
    for i, npc in enumerate(n for n in sav.npcs if n is not None):
        label = f"{get_text('kind_npc', lang)} #{i}  {chara_name(npc)}"
        targets.append((label, npc, f"{file_hash[:8]}_npc_{i}"))
    for i, unique in enumerate(sav.uniques):
        label = f"{get_text('kind_unique', lang)} #{i}  {chara_name(unique)}"
        targets.append((label, unique, f"{file_hash[:8]}_uniq_{i}"))

    if not targets:
        st.info(get_text("no_chara", lang))
        st.stop()

    st.divider()
    # ボタンのクリック処理は編集ウィジェットの生成前に行う必要がある
    # (fieldsとウィジェット状態の更新を同じrerunで済ませるため)
    render_bulk_buttons(targets, lang)

    st.divider()
    selected = st.selectbox(
        get_text("select_chara", lang),
        range(len(targets)),
        format_func=lambda i: targets[i][0],
    )
    label, record, wkey_prefix = targets[selected]

    left, right = st.columns([1, 2])
    with left:
        image = getattr(record["chara"], "image", None)
        if image:
            st.image(io.BytesIO(image), caption=chara_name(record), width=280)
        # 埋め込まれているキャラカードはPNG先頭の完全なカードデータなので
        # そのまま .png として配布できる
        st.download_button(
            get_text("download_chara", lang),
            bytes(record["chara"]),
            f"{chara_name(record)}.png",
            key=f"{wkey_prefix}_dl_chara",
        )
        st.caption(f"record type: {record['type']}")
    with right:
        render_editor(record, lang, wkey_prefix)

    st.divider()
    st.download_button(
        get_text("download_button", lang), bytes(sav), f"modified_{file.name}"
    )
