
import streamlit as st

title = "kk-snippets"
st.set_page_config(page_title=title)
st.title(title)

text = """
コイカツ/ハニカム/サマすくに関連するツールを置くページです。

動作の不具合などあれば [@tropical_362827](https://twitter.com/tropical_362827) に送っていただけると助かります :bow:

←のメニューからページを選択してください。

<a href="https://github.com/great-majority/kk-snippets">
    <img src="https://opengraph.githubassets.com/24d9aa2fc57ba5cc9c57898c8c43138d09b4ed7e71ede99bbe892ec0b7de6ded/great-majority/kk-snippets" alt="githubリンク" width="80%">
</a>
"""

st.markdown(text, unsafe_allow_html=True)