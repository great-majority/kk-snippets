import copy
import io

import streamlit as st
from kkloader.EmocreCharaData import EmocreCharaData  # noqa
from kkloader.KoikatuCharaData import Coordinate, KoikatuCharaData  # noqa

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "エモクリ→コイカツキャラクター変換ツール",
        "description": "エモーションクリエイターズで作成されたキャラクターを無印コイカツで読めるように変換するツールです。",
        "file_uploader": "エモーション・クリエイターズのキャラクター画像を選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "header_label": "ヘッダ:",
        "name_label": "キャラクター名:",
        "card_image_caption": "カード画像",
        "success_convert": "正常にデータを変換しました。",
        "download_button": "データをダウンロード",
    },
    "en": {
        "title": "Emocre → Koikatsu Character Converter",
        "description": "A tool to convert characters created in Emotion Creators to be readable in original Koikatsu.",
        "file_uploader": "Select an Emotion Creators character image",
        "error_load": "Failed to load file. Unsupported file format.",
        "header_label": "Header:",
        "name_label": "Character name:",
        "card_image_caption": "Card image",
        "success_convert": "Data converted successfully.",
        "download_button": "Download data",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title)

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

file = st.file_uploader(get_text("file_uploader", lang))
if file is not None:
    try:
        ec = EmocreCharaData.load(file.getvalue())
    except Exception as e:
        st.error(get_text("error_load", lang), icon="🚨")
        st.stop()

    st.write(get_text("header_label", lang), ec.header.decode("utf-8"))
    st.write(get_text("name_label", lang), ec["Parameter"]["fullname"])
    st.image(io.BytesIO(ec.image), caption=get_text("card_image_caption", lang))

    kk = KoikatuCharaData()

    kk.image = ec.image
    kk.face_image = ec.image
    kk.product_no = 100
    kk.header = "【KoiKatuChara】".encode("utf-8")
    kk.version = "0.0.0".encode("ascii")
    kk.blockdata = copy.deepcopy(ec.blockdata)
    kk.serialized_lstinfo_order = copy.deepcopy(kk.blockdata)
    kk.original_lstinfo_order = copy.deepcopy(kk.blockdata)

    kk.Custom = copy.deepcopy(ec.Custom)
    kk.Coordinate = Coordinate(data=None, version="0.0.0")
    kk.Parameter = copy.deepcopy(ec.Parameter)
    kk.Status = copy.deepcopy(ec.Status)

    if "KKEx" in ec.blockdata:
        kk.KKEx = copy.deepcopy(ec.KKEx)

    kk.Custom["face"]["version"] = "0.0.2"
    kk.Custom["face"]["pupilHeight"] *= 1.08
    kk.Custom["face"]["hlUpY"] = (kk.Custom["face"]["hlUpY"] - 0.25) * 2
    del kk.Custom["face"]["hlUpX"]
    del kk.Custom["face"]["hlDownX"]
    del kk.Custom["face"]["hlUpScale"]
    del kk.Custom["face"]["hlDownScale"]
    kk.Custom["body"]["version"] = "0.0.2"
    kk.Custom["hair"]["version"] = "0.0.4"

    ec.Coordinate["clothes"]["hideBraOpt"] = [False, False]
    ec.Coordinate["clothes"]["hideShortsOpt"] = [False, False]
    for i, p in enumerate(ec.Coordinate["clothes"]["parts"]):
        a = {
            "emblemeId": p["emblemeId"][0],
            "emblemeId2": p["emblemeId"][1],
        }
        ec.Coordinate["clothes"]["parts"][i].update(a)
    ec.Coordinate["clothes"]["parts"].append(ec.Coordinate["clothes"]["parts"][-1])
    for i, a in enumerate(ec.Coordinate["accessory"]["parts"]):
        del ec.Coordinate["accessory"]["parts"][i]["hideTiming"]
    makeup = copy.deepcopy(ec.Custom["face"]["baseMakeup"])
    kk.Coordinate.data = [
        {
            "clothes": ec.Coordinate["clothes"],
            "accessory": ec.Coordinate["accessory"],
            "enableMakeup": False,
            "makeup": makeup,
        }
    ] * 7

    kk.Parameter["version"] = "0.0.5"
    kk.Parameter["lastname"] = " "
    kk.Parameter["firstname"] = ec.Parameter["fullname"]
    kk.Parameter["nickname"] = " "
    kk.Parameter["callType"] = -1
    kk.Parameter["clubActivities"] = 0
    kk.Parameter["weakPoint"] = 0
    items = [
        "animal",
        "eat",
        "cook",
        "exercise",
        "study",
        "fashionable",
        "blackCoffee",
        "spicy",
        "sweet",
    ]
    kk.Parameter["awnser"] = dict.fromkeys(items, True)
    items = ["kiss", "aibu", "anal", "massage", "notCondom"]
    kk.Parameter["denial"] = dict.fromkeys(items, False)
    items = [
        "hinnyo",
        "harapeko",
        "donkan",
        "choroi",
        "bitch",
        "mutturi",
        "dokusyo",
        "ongaku",
        "kappatu",
        "ukemi",
        "friendly",
        "kireizuki",
        "taida",
        "sinsyutu",
        "hitori",
        "undo",
        "majime",
        "likeGirls",
    ]
    kk.Parameter["attribute"] = dict.fromkeys(items, True)
    kk.Parameter["aggressive"] = 0
    kk.Parameter["diligence"] = 0
    kk.Parameter["kindness"] = 0
    del kk.Parameter["fullname"]
    kk.Parameter["personality"] = 0

    kk.Status["version"] = "0.0.0"
    kk.Status["clothesState"] = b"\x00" * 9
    kk.Status["eyesBlink"] = False
    kk.Status["mouthPtn"] = 1
    kk.Status["mouthOpenMax"] = 0
    kk.Status["mouthFixed"] = True
    kk.Status["eyesLookPtn"] = 1
    kk.Status["neckLookPtn"] = 3
    kk.Status["visibleSonAlways"] = False
    del kk.Status["mouthOpenMin"]
    del kk.Status["enableSonDirection"]
    del kk.Status["sonDirectionX"]
    del kk.Status["sonDirectionY"]
    kk.Status["coordinateType"] = 4
    kk.Status["backCoordinateType"] = 0
    kk.Status["shoesType"] = 1

    st.success(get_text("success_convert", lang), icon="✅")
    st.download_button(
        get_text("download_button", lang), bytes(kk), file_name="converted.png"
    )
