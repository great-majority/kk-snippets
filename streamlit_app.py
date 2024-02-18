
import streamlit as st

title = "トップページ"
st.set_page_config(page_title=title)
st.title(title)

text = """
# このページは?
コイカツ/ハニカムに関連するちょっとしたツールを置くページです。

動作の不具合などあれば [@tropical_362827](https://twitter.com/tropical_362827) に送っていただけると助かります :bow:

←のメニューからページを選択してください。
"""

st.markdown(text)