import streamlit as st

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "サマすく→アイコミキャラクターコンバータ",
        "info": """
このページの機能は **sv-hc-converter** へ統合しました！

サマすく・ハニカム・アイコミの3つのゲーム間でキャラクターデータを相互変換できるようになりました。
""",
        "link_label": "📄 sv-hc-converter へ移動",
    },
    "en": {
        "title": "Summer Vacation → Aicomi Character Converter",
        "info": """
This page's functionality has been merged into **sv-hc-converter**!

You can now convert character data between Summer Vacation Scramble, Honey Come, and Aicomi.
""",
        "link_label": "📄 Go to sv-hc-converter",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title)

lang = st.session_state.get("lang", "ja")

st.title(get_text("title", lang))

st.info(get_text("info", lang))

st.page_link("pages/sv-hc-converter.py", label=get_text("link_label", lang), icon="🔗")

st.divider()
