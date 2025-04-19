import io
import tempfile

import streamlit as st
from kkloader import (
    SummerVacationCharaData as svcd,
    HoneycomeCharaData as hcd,
    KoikatuCharaData as kcd,
    EmocreCharaData as ecd,
)
from kkloader.KoikatuCharaData import BlockData
from kkloader.funcs import get_png, load_length, load_type


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
            ValueError("unsupported input. type:{}".format(type(filelike)))   
        
        kch.image = None
        if contains_png:
            kch.image = get_png(data_stream)

        kch.product_no = load_type(data_stream, "i")  # 100
        kch.header = load_length(data_stream, "b")  # 【KoiKatuChara】
        kch.version = load_length(data_stream, "b")  # 0.0.0
        kch.face_image = load_length(data_stream, "i")

        return kch


title = "illusion/ILLGAMESキャラ情報表示"
st.set_page_config(page_title=title)
st.title(title)

description = """
illusion/ILLGAMESのキャラ画像に含まれている色々なデータを一覧表示するツールです。

対応しているゲームは以下の通りです。
- illusion
    - コイカツ/コイカツサンシャイン
    - エモーションクリエイターズ
- ILLGAMES
    - ハニカム
    - サマバケすくらんぶる
"""
st.markdown(description)

with st.expander("さらに詳しい説明を見る"):
    description = """
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
"""
    st.markdown(description)

st.divider()

file = st.file_uploader("コイカツ/サマすく/ハニカムのキャラ画像を選択")
if file is not None:

    try:
        kch = KoikatuCharaHeader.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        # st.write(e)
        st.stop()

    st.success("正常にデータを読み込めました。", icon="✅")

    header = kch.header.decode("utf-8")
    st.write(header)

    match header:
        case "【KoiKatuChara】" | "【KoiKatuCharaSun】":
            chara = kcd.load(file.getvalue())
            col1, col2 = st.columns(2)
            with col1:
                st.image(io.BytesIO(chara.image), caption="カード画像")
            with col2:
                st.image(io.BytesIO(chara.face_image), caption="顔画像")
            name = " ".join([chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]])

        case "【EroMakeChara】":
            chara = ecd.load(file.getvalue())
            st.image(io.BytesIO(chara.image), caption="カード画像")
            name = chara["Parameter"]["fullname"]

        case "【SVChara】":
            chara = svcd.load(file.getvalue())
            col1, col2 = st.columns(2)
            with col1:
                st.image(io.BytesIO(chara.image), caption="カード画像")
            with col2:
                st.image(io.BytesIO(chara["GameParameter_SV"]["imageData"]), caption="アイコン画像")
            name = " ".join([chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]])

        case "【HCChara】" | "【HCPChara】":
            chara = hcd.load(file.getvalue())
            col1, col2 = st.columns(2)
            with col1:
                st.image(io.BytesIO(chara.image), caption="カード画像")
            with col2:
                st.image(io.BytesIO(chara.face_image), caption="顔画像")
            name = " ".join([chara["Parameter"]["lastname"], chara["Parameter"]["firstname"]])

        case _:
            st.error(f"このヘッダのファイルには対応していません: {header}", icon="🚨")
            st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmpfile:
        chara.save_json(tmpfile.name)
        tmpfile.seek(0)
        file_bytes = tmpfile.read()
    st.download_button("データをjsonとしてダウンロード", file_bytes, file_name=f"{name}.json", mime="application/json")

    tabs = st.tabs(chara.blockdata)
    for b, t in zip(chara.blockdata, tabs):
        t.json(chara[b].jsonalizable(), expanded=1)
