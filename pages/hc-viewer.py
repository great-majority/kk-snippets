import io
import streamlit as st
from kkloader import HoneycomeCharaData as hcd

title = "ハニカムキャラデータビューア"
st.set_page_config(page_title=title)
st.title(title)

description = """
ハニカムのキャラ画像に含まれている色々なデータを一覧表示するツールです。
入っているデータが大きめなのでちょっと動作が重いかもしれません。

↓は表示されるタブとその値の中身の説明です。

| タブ名           | 値の中身                                                                                       | 
| ---------------- | ---------------------------------------------------------------------------------------------- | 
| Custom           | 体型・顔つき・瞳の設定値が入っています。                                                       | 
| Coordinate       | 私服/部屋着/風呂着のコーデ情報が入っています。髪型もここにあります。                           | 
| Parameter        | 名前や性格、誕生日などの設定値が入っています。                                                 | 
| Status           | ゲーム中の動作の状態(アクセサリーを表示するか、カメラ目線にするかなど)を表す値が入っています。 | 
| Graphic          | 影の表現・影の濃さ・アウトラインの幅の設定値が入っています。                                   | 
| About            | キャラクターの作者のIDとキャラデータ自体のIDが入っています。                                   | 
| Gameparameter_HC | "綺麗好き"や"一目惚れ"などのキャラクターのメンタルの設定値です。                               | 
| Gameinfo_HC      | ゲーム中のステータス(隷属や好感など)が保存されています。                                       | 
"""
st.markdown(description)

st.divider()

file = st.file_uploader("ハニカムのキャラ画像を選択")
if file is not None:

    try:
        hc = hcd.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        st.stop()

    st.success("正常にデータを読み込めました。(↓に結果が表示されるまでちょっと時間がかかります)", icon="✅")
    st.download_button("データをダウンロード", bytes(hc), file_name="converted.png")

    col1, col2 = st.columns(2)

    with col1:
        st.image(io.BytesIO(hc.image), caption="カード画像")

    with col2:
        st.image(io.BytesIO(hc.face_image), caption="顔画像")

    tabs = st.tabs(hc.blockdata)
    for b, t in zip(hc.blockdata, tabs):
        t.json(hc[b].jsonalizable(), expanded=False)
