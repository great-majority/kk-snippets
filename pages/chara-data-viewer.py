import io
import tempfile

import streamlit as st
from kkloader import (
    AicomiCharaData as acd,
)
from kkloader import (
    EmocreCharaData as ecd,
)
from kkloader import (
    HoneycomeCharaData as hcd,
)
from kkloader import (
    KoikatuCharaData as kcd,
)
from kkloader import (
    SummerVacationCharaData as svcd,
)
from kkloader.funcs import get_png, load_length, load_type
from kkloader.KoikatuCharaData import BlockData

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "illusion/ILLGAMESキャラ情報表示",
        "description": """
illusion/ILLGAMESのキャラ画像に含まれている色々なデータを一覧表示するツールです。

対応しているゲームは以下の通りです。
- illusion
    - コイカツ/コイカツサンシャイン
    - エモーションクリエイターズ
- ILLGAMES
    - ハニカム
    - サマバケすくらんぶる
    - アイコミ
""",
        "expander_title": "さらに詳しい説明を見る",
        "expander_content": """
ゲームやバージョンによって、含まれているデータが違っている場合があります。
↓はあくまで参考程度に考えてください。

| タブ名           | 値の中身                                                                                       |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| Custom           | 体型・顔つき・瞳の設定値が入っています。                                                       |
| Coordinate       | 私服/部屋着/風呂着のコーデ情報が入っています。髪型もここにあります。                           |
| Parameter        | 名前や性格、誕生日などの設定値が入っています。                                                 |
| Status           | ゲーム中の動作の状態(アクセサリーを表示するか、カメラ目線にするかなど)を表す値が入っています。 |
| Graphic          | 影の表現・影の濃さ・アウトラインの幅の設定値が入っています。                                   |
| About            | キャラクターの作者のIDとキャラデータ自体のIDが入っています。                                   |
| Gameparameter_* | "綺麗好き"や"一目惚れ"などのキャラクターのメンタルの設定値です。                               |
| Gameinfo_*      | ゲーム中のステータス(隷属や好感など)が保存されています。                                       |
| KKEx             | modの設定情報が格納される場所です。                                                            |
""",
        "file_uploader": "コイカツ/サマすく/ハニカムのキャラ画像を選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "success_load": "正常にデータを読み込めました。",
        "error_unsupported": "このヘッダのファイルには対応していません:",
        "card_image_caption": "カード画像",
        "face_image_caption": "顔画像",
        "icon_image_caption": "アイコン画像",
        "download_json": "データをjsonとしてダウンロード",
    },
    "en": {
        "title": "illusion/ILLGAMES Character Data Viewer",
        "description": """
A tool to display various data contained in illusion/ILLGAMES character images.

Supported games:
- illusion
    - Koikatsu/Koikatsu Sunshine
    - Emotion Creators
- ILLGAMES
    - Honey Come
    - Summer Vacation Scramble
    - Aicomi
""",
        "expander_title": "Show more details",
        "expander_content": """
The data included may vary depending on the game and version.
Please consider the following as a reference only.

| Tab Name         | Contents                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| Custom           | Contains body shape, facial features, and pupil settings.                                       |
| Coordinate       | Contains outfit information for casual/room/bath wear. Hairstyle is also here.                  |
| Parameter        | Contains name, personality, birthday, and other settings.                                       |
| Status           | Contains in-game state values (accessory visibility, camera look, etc.).                        |
| Graphic          | Contains shadow expression, shadow intensity, and outline width settings.                       |
| About            | Contains the creator's ID and the character data ID.                                            |
| Gameparameter_* | Mental settings like "neat freak" or "love at first sight".                                     |
| Gameinfo_*      | In-game status (slavery, affection, etc.) is saved here.                                        |
| KKEx             | Storage location for mod configuration data.                                                    |
""",
        "file_uploader": "Select a character image (Koikatsu/Summer Vacation/Honey Come)",
        "error_load": "Failed to load file. Unsupported file format.",
        "success_load": "Data loaded successfully.",
        "error_unsupported": "This header file is not supported:",
        "card_image_caption": "Card image",
        "face_image_caption": "Face image",
        "icon_image_caption": "Icon image",
        "download_json": "Download data as JSON",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


# ヘッダ部分だけ読み込むクラス
class KoikatuCharaHeader:
    @classmethod
    def load(cls, filelike, contains_png=True):
        kch = cls()

        if isinstance(filelike, str):
            with open(filelike, "br") as f:
                data = f.read()
            data_stream = io.BytesIO(data)

        elif isinstance(filelike, bytes):
            data_stream = io.BytesIO(filelike)

        elif isinstance(filelike, io.BytesIO):
            data_stream = filelike

        else:
            raise ValueError("unsupported input. type:{}".format(type(filelike)))

        kch.image = None
        if contains_png:
            kch.image = get_png(data_stream)

        kch.product_no = load_type(data_stream, "i")  # 100
        kch.header = load_length(data_stream, "b")  # 【KoiKatuChara】
        kch.version = load_length(data_stream, "b")  # 0.0.0
        kch.face_image = load_length(data_stream, "i")

        return kch


# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title)

lang = st.session_state.get("lang", "ja")

st.title(get_text("title", lang))

st.markdown(get_text("description", lang))

with st.expander(get_text("expander_title", lang)):
    st.markdown(get_text("expander_content", lang))

st.divider()

file = st.file_uploader(get_text("file_uploader", lang))
if file is not None:
    try:
        kch = KoikatuCharaHeader.load(file.getvalue())
    except Exception as e:
        st.error(get_text("error_load", lang), icon="🚨")
        # st.write(e)
        st.stop()

    st.success(get_text("success_load", lang), icon="✅")

    header = kch.header.decode("utf-8")
    st.write(header)

    match header:
        case "【KoiKatuChara】" | "【KoiKatuCharaSun】":
            chara = kcd.load(file.getvalue())
            col1, col2 = st.columns(2)
            with col1:
                st.image(
                    io.BytesIO(chara.image),
                    caption=get_text("card_image_caption", lang),
                )
            with col2:
                st.image(
                    io.BytesIO(chara.face_image),
                    caption=get_text("face_image_caption", lang),
                )
            name = " ".join(
                [chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]]
            )

        case "【EroMakeChara】":
            chara = ecd.load(file.getvalue())
            st.image(
                io.BytesIO(chara.image), caption=get_text("card_image_caption", lang)
            )
            name = chara["Parameter"]["fullname"]

        case "【SVChara】" | "【ACChara】":
            if header == "【SVChara】":
                chara = svcd.load(file.getvalue())
                icon_image = chara["GameParameter_SV"]["imageData"]
            elif header == "【ACChara】":
                chara = acd.load(file.getvalue())
                icon_image = chara["GameParameter_AC"]["imageData"]

            col1, col2 = st.columns(2)
            with col1:
                st.image(
                    io.BytesIO(chara.image),
                    caption=get_text("card_image_caption", lang),
                )
            with col2:
                if icon_image is not None:
                    st.image(
                        io.BytesIO(icon_image),
                        caption=get_text("icon_image_caption", lang),
                    )
            name = " ".join(
                [chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]]
            )

        case "【HCChara】" | "【HCPChara】":
            chara = hcd.load(file.getvalue())
            col1, col2 = st.columns(2)
            with col1:
                st.image(
                    io.BytesIO(chara.image),
                    caption=get_text("card_image_caption", lang),
                )
            with col2:
                st.image(
                    io.BytesIO(chara.face_image),
                    caption=get_text("face_image_caption", lang),
                )
            name = " ".join(
                [chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]]
            )

        case _:
            st.error(f"{get_text('error_unsupported', lang)} {header}", icon="🚨")
            st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmpfile:
        chara.save_json(tmpfile.name)
        tmpfile.seek(0)
        file_bytes = tmpfile.read()
    st.download_button(
        get_text("download_json", lang),
        file_bytes,
        file_name=f"{name}.json",
        mime="application/json",
    )

    tabs = st.tabs(chara.blockdata)
    for b, t in zip(chara.blockdata, tabs):
        t.json(chara[b].jsonalizable(), expanded=1)
