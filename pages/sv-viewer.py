import io
import streamlit as st
from kkloader import SummerVacationCharaData as svcd

title = "サマすくキャラデータビューア"
st.set_page_config(page_title=title)
st.title(title)

description = """
サマすくのキャラ画像に含まれている色々なデータを一覧表示するツールです。

↓は表示されるタブとその値の中身の説明です。

| タブ名           | 値の中身                                                                                       | 
| ---------------- | ---------------------------------------------------------------------------------------------- | 
| Custom           | 体型・顔つき・瞳の設定値が入っています。                                                       | 
| Coordinate       | 私服/役職服/水着のコーデ情報が入っています。髪型もここにあります。                           | 
| Parameter        | 名前や性格、誕生日などの設定値が入っています。                                                 | 
| Status           | ゲーム中の動作の状態(アクセサリーを表示するか、カメラ目線にするかなど)を表す値が入っています。 | 
| Graphic          | 影の表現・影の濃さ・アウトラインの幅の設定値が入っています。                                   | 
| About            | キャラクターの作者のIDとキャラデータ自体のIDが入っています。                                   | 
| Gameparameter_SV | キャラクターの個性や特性、性愛対象などの情報が入っています。                                | 
| Gameinfo_SV      | 特にデータが入っていないブロックです。                                                      | 
"""
st.markdown(description)

st.divider()

file = st.file_uploader("サマすくのキャラ画像を選択")
if file is not None:

    try:
        svc = svcd.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        st.stop()

    st.success("正常にデータを読み込めました。", icon="✅")
    st.download_button("データをダウンロード", bytes(svc), file_name="converted.png")

    col1, col2 = st.columns(2)

    with col1:
        st.image(io.BytesIO(svc.image), caption="カード画像")

    with col2:
        st.image(io.BytesIO(svc["GameParameter_SV"]["imageData"]), caption="アイコン画像")

    tabs = st.tabs(svc.blockdata)
    for b, t in zip(svc.blockdata, tabs):
        t.json(svc[b].jsonalizable(), expanded=False)
