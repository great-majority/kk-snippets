import streamlit as st

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "kk-snippets",
        "description": """
illusion/ILLGAMESのゲームに関連するツールを置くページです。

動作の不具合などあれば [@tropical_362827](https://twitter.com/tropical_362827) か [GitHub](https://github.com/great-majority/kk-snippets/issues) に送っていただけると助かります🙇

←のメニューからページを選択してください。

<a href="https://github.com/great-majority/kk-snippets">
    <img src="https://opengraph.githubassets.com/24d9aa2fc57ba5cc9c57898c8c43138d09b4ed7e71ede99bbe892ec0b7de6ded/great-majority/kk-snippets" alt="githubリンク" width="80%">
</a>
""",
    },
    "en": {
        "title": "kk-snippets",
        "description": """
A collection of tools related to illusion/ILLGAMES titles.

If you find any bugs or strange translations, please let us know via [GitHub Issues](https://github.com/great-majority/kk-snippets/issues) or [@tropical_362827](https://twitter.com/tropical_362827).🙇

Please select a page from the menu on the left.

<a href="https://github.com/great-majority/kk-snippets">
    <img src="https://opengraph.githubassets.com/24d9aa2fc57ba5cc9c57898c8c43138d09b4ed7e71ede99bbe892ec0b7de6ded/great-majority/kk-snippets" alt="GitHub link" width="80%">
</a>
""",
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

st.markdown(get_text("description", lang), unsafe_allow_html=True)
