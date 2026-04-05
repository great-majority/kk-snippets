import streamlit as st

st.set_page_config(page_title="kk-snippets", layout="wide")

NAV_TITLES = {
    "ja": {
        "home": "ホーム",
        "sec_koikatsu": "コイカツ関連",
        "sec_honeycomb": "ハニカム関連",
        "sec_digcraft": "デジクラ関連",
        "sec_common": "共通ツール",
        "ec_to_kk": "コイカツシリーズキャラクター変換ツール",
        "sv_hc_converter": "ハニカムシリーズキャラクター変換ツール",
        "sv_chara_trait_editor": "サマすくキャラ特性エディター",
        "sv_stat": "サマすく行動ログビューア",
        "dc_calligrapher": "デジクラカリグラファー",
        "dc_chara_converter": "デジクラキャラクター統一コンバータ",
        "dc_data_viewer": "デジクラシーンデータビューア",
        "dc_item_converter": "デジクラ基本形アイテム変換ツール",
        "chara_data_viewer": "illusion/ILLGAMESキャラ情報表示",
    },
    "en": {
        "home": "Home",
        "sec_koikatsu": "Koikatsu",
        "sec_honeycomb": "Honeycome",
        "sec_digcraft": "Digital Craft",
        "sec_common": "Common Tools",
        "ec_to_kk": "Koikatsu Character Data Converter",
        "sv_hc_converter": "Honeycome Series Character Converter",
        "sv_chara_trait_editor": "Summer Vacation Scramble Trait Editor",
        "sv_stat": "Summer Vacation Scramble Action Log Viewer",
        "dc_calligrapher": "Digital Craft Calligrapher",
        "dc_chara_converter": "Digital Craft Character Converter",
        "dc_data_viewer": "Digital Craft Scene Data Viewer",
        "dc_item_converter": "Digital Craft Primitive Item Converter",
        "chara_data_viewer": "illusion/ILLGAMES Character Data Viewer",
    },
}

with st.sidebar:
    lang = st.selectbox(
        "Language / 言語",
        options=["ja", "en"],
        format_func=lambda x: "日本語" if x == "ja" else "English",
        index=0,
        key="lang",
    )

t = NAV_TITLES.get(lang, NAV_TITLES["ja"])

pg = st.navigation(
    {
        "": [
            st.Page("pages/home.py", title=t["home"], default=True),
            st.Page(
                "pages/convert-to-aicomi.py",
                title="convert-to-aicomi",
                visibility="hidden",
            ),  # type: ignore[call-arg]
        ],
        t["sec_koikatsu"]: [
            st.Page("pages/ec-to-kk.py", title=t["ec_to_kk"]),
        ],
        t["sec_honeycomb"]: [
            st.Page("pages/sv-hc-converter.py", title=t["sv_hc_converter"]),
            st.Page("pages/sv-chara-trait-editor.py", title=t["sv_chara_trait_editor"]),
            st.Page("pages/sv-stat.py", title=t["sv_stat"]),
        ],
        t["sec_digcraft"]: [
            st.Page("pages/digital-craft-calligrapher.py", title=t["dc_calligrapher"]),
            st.Page(
                "pages/digital-craft-character-converter.py",
                title=t["dc_chara_converter"],
            ),
            st.Page("pages/digital-craft-data-viewer.py", title=t["dc_data_viewer"]),
            st.Page(
                "pages/digital-craft-item-converter.py", title=t["dc_item_converter"]
            ),
        ],
        t["sec_common"]: [
            st.Page("pages/chara-data-viewer.py", title=t["chara_data_viewer"]),
        ],
    }
)
pg.run()
