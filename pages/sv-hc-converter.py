import copy
import io

import streamlit as st
from kkloader import AicomiCharaData, HoneycomeCharaData, SummerVacationCharaData
from kkloader.funcs import get_png, load_length, load_type
from kkloader.KoikatuCharaData import BlockData

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "ILLGAMESキャラクターコンバータ",
        "description": """
ハニカム↔サマすく↔アイコミでキャラクターデータを相互変換するツールです。キャラデータ読み込み後、選択したタイトルへキャラ変換を行わうことができます。

**⚠️注意事項**: バグなどあるかもしれませんので、変換前のデータのバックアップはとっておきましょう!
""",
        "expander_title": "各ゲームごとのキャラデータの違い",
        "expander_content": """
- 各ゲーム間で互換性のない部分は、そのまま削除したり、無なデータでの埋め合わせを行います。
- ハニカム、アイコミのポートレート画像はサマすくの立ち絵画像で代用、逆にサマすくからのコンバートでは立ち絵画像を代用します。見た目が気になる場合はキャラメイクから再保存してください。

|                            | ハニカム | サマすく | アイコミ |
| -------------------------- | -------- | -------- | -------- |
| 着衣補正                   | ❌️     | ⭕️     | ⭕️     |
| コーディネート数           | 3        | 3        | 4        |
| アクセサリー切り替えフラグ | ❌️     | ❌️     | ⭕️     |
| ニックネーム               | ❌️     | ❌️     | ⭕️     |
| アクセサリー数             | 20       | 20       | 40       |
| ポートレート画像           | ⭕️     | ❌️     | ⭕️     |
| 立ち絵画像                 | ❌️     | ⭕️     | ❌️     |
| ハニカム固有データ         | ⭕️     | ❌️     | ❌️     |
| サマすく固有データ         | ❌️     | ⭕️     | ❌️     |
| アイコミ固有データ         | ❌️     | ❌️     | ⭕️     |
""",
        "file_uploader": "サマすく/ハニカム/アイコミのキャラ画像を選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "success_load": "正常にデータを読み込めました。",
        "error_unsupported": "このヘッダのファイルには対応していません:",
        "file_is_hc": "このファイルは **ハニカム** のキャラデータです。",
        "file_is_sv": "このファイルは **サマすく** のキャラデータです。",
        "file_is_ac": "このファイルは **アイコミ** のキャラデータです。",
        "target_select": "変換先を選択",
        "target_hc": "ハニカム",
        "target_sv": "サマすく",
        "target_ac": "アイコミ",
        "download_sv": "サマすくのキャラとしてダウンロード",
        "download_hc": "ハニカムのキャラとしてダウンロード",
        "download_ac": "アイコミのキャラとしてダウンロード",
        "language_selector": "言語 / Language",
    },
    "en": {
        "title": "ILLGAMES Character Converter",
        "description": """
This tool allows you to convert character data between Honey Come, Summer Vacation Scramble, and Aicomi. After loading character data, you can convert the character to the selected title.

**⚠️Caution**: There may be bugs, so please back up your data before conversion!
""",
        "expander_title": "Differences in character data between games",
        "expander_content": """
- Incompatible parts between games will be deleted or filled with empty data.
- Portrait images for Honey Come and Aicomi will be substituted with standing images from Summer Vacation Scramble, and vice versa. If you are concerned about the appearance, please re-save from character creation.

|                                | Honey Come | Summer Vacation | Aicomi |
| ------------------------------ | ---------- | --------------- | ------ |
| Clothing adjustment            | ❌️        | ⭕️            | ⭕️   |
| Number of coordinates          | 3          | 3               | 4      |
| Accessory toggle flag          | ❌️        | ❌️            | ⭕️   |
| Nickname                       | ❌️        | ❌️            | ⭕️   |
| Number of accessories          | 20         | 20              | 40     |
| Portrait image                 | ⭕️        | ❌️            | ⭕️   |
| Standing image                 | ❌️        | ⭕️            | ❌️   |
| Honey Come specific data       | ⭕️        | ❌️            | ❌️   |
| Summer Vacation Scramble specific data  | ❌️        | ⭕️            | ❌️   |
| Aicomi specific data           | ❌️        | ❌️            | ⭕️   |
""",
        "file_uploader": "Select a character image (Summer Vacation Scramble / Honey Come / Aicomi)",
        "error_load": "Failed to load file. Unsupported file format.",
        "success_load": "Data loaded successfully.",
        "error_unsupported": "This header file is not supported:",
        "file_is_hc": "This file is a **Honey Come** character.",
        "file_is_sv": "This file is a **Summer Vacation Scramble** character.",
        "file_is_ac": "This file is an **Aicomi** character.",
        "target_select": "Select conversion target",
        "target_hc": "Honey Come",
        "target_sv": "Summer Vacation Scramble",
        "target_ac": "Aicomi",
        "download_sv": "Download as Summer Vacation Scramble character",
        "download_hc": "Download as Honey Come character",
        "download_ac": "Download as Aicomi character",
        "language_selector": "Language / 言語",
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


class StubBlockData(BlockData):
    def __init__(self, name, version):
        self.name = name
        self.data = {}
        self.version = version


# ========================================
# それぞれのタイトル固有パラメータのデフォルト値
# ========================================

GAME_CONFIG = {
    "HC": {
        "class": HoneycomeCharaData,
        "header": "【HCChara】",
        "product_no": 200,
        "blocks": ["GameParameter_HC", "GameInfo_HC"],
    },
    "SV": {
        "class": SummerVacationCharaData,
        "header": "【SVChara】",
        "product_no": 100,
        "blocks": ["GameParameter_SV", "GameInfo_SV"],
    },
    "AC": {
        "class": AicomiCharaData,
        "header": "【ACChara】",
        "product_no": 100,
        "blocks": ["GameParameter_AC", "GameInfo_AC"],
    },
}

COMMON_BLOCKS = ["Custom", "Coordinate", "Parameter", "Status", "Graphic", "About"]

# ハニカム

DEFAULT_GAMEPARAMETER_HC = {"trait": 0, "mind": 0, "hAttribute": 10}

DEFAULT_GAMEINFO_HC = {
    "Favor": 0,
    "Enjoyment": 0,
    "Aversion": 0,
    "Slavery": 0,
    "Broken": 0,
    "Dependence": 0,
    "Dirty": 0,
    "Tiredness": 0,
    "Toilet": 0,
    "Libido": 0,
    "nowState": 0,
    "nowDrawState": 0,
    "lockNowState": False,
    "lockBroken": False,
    "lockDependence": False,
    "alertness": 0,
    "calcState": 0,
    "escapeFlag": 0,
    "escapeExperienced": False,
    "firstHFlag": False,
    "genericVoice": [
        [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ],
        [
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        ],
    ],
    "genericBrokenVoice": False,
    "genericDependencepVoice": False,
    "genericAnalVoice": False,
    "genericPainVoice": False,
    "genericFlag": False,
    "genericBefore": False,
    "inviteVoice": [False, False, False, False, False],
    "hCount": 0,
    "map": [],
    "arriveRoom50": False,
    "arriveRoom80": False,
    "arriveRoomHAfter": False,
    "resistH": 0,
    "resistPain": 0,
    "resistAnal": 0,
    "usedItem": 0,
    "isChangeParameter": False,
    "isConcierge": False,
    "TalkFlag": False,
    "ResistedH": False,
    "ResistedPain": False,
    "ResistedAnal": False,
}

# サマすく

DEFAULT_GAMEPARAMETER_SV = {
    "imageData": None,
    "job": 0,
    "sexualTarget": 0,
    "lvChastity": 0,
    "lvSociability": 0,
    "lvTalk": 0,
    "lvStudy": 0,
    "lvLiving": 0,
    "lvPhysical": 0,
    "lvDefeat": 0,
    "belongings": [0, 0],
    "isVirgin": True,
    "isAnalVirgin": True,
    "isMaleVirgin": True,
    "isMaleAnalVirgin": True,
    "individuality": {"answer": [-1, -1]},
    "preferenceH": {"answer": [-1, -1]},
}

# アイコミ

DEFAULT_GAMEPARAMETER_AC = {
    "version": "0.0.0",
    "imageData": None,
    "clubActivities": 3,
    "individuality": [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ],
    "characteristics": {"answer": [-1, -1]},
    "hobby": {"answer": [-1, -1, -1]},
    "erogenousZone": 0,
}

DEFAULT_ACCCESORY_AC = {
    "type": 120,
    "id": 0,
    "parentKeyType": 0,
    "addMove": [
        2,
        3,
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
        ],
    ],
    "color": [
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
    ],
    "colorInfo": [
        {
            "pattern": 0,
            "tiling": [0.0, 0.0],
            "patternColor": [1.0, 1.0, 1.0, 1.0],
            "offset": [0.5, 0.5],
            "rotate": 0.5,
        },
        {
            "pattern": 0,
            "tiling": [0.0, 0.0],
            "patternColor": [1.0, 1.0, 1.0, 1.0],
            "offset": [0.5, 0.5],
            "rotate": 0.5,
        },
        {
            "pattern": 0,
            "tiling": [0.0, 0.0],
            "patternColor": [1.0, 1.0, 1.0, 1.0],
            "offset": [0.5, 0.5],
            "rotate": 0.5,
        },
    ],
    "hideCategory": 0,
    "noShake": False,
    "fkInfo": {"use": False, "bones": []},
}

# ========================================
# ヘルパー関数
# ========================================


def init_chara_base(target_class, source, header, product_no, face_image=None):
    """キャラクターデータの基本初期化"""
    chara = target_class()
    chara.image = source.image
    chara.face_image = face_image if face_image is not None else b""
    chara.product_no = product_no
    chara.header = header.encode("utf-8")
    chara.version = "0.0.0".encode("utf-8")
    return chara


def setup_blockdata(chara, common_blocks, game_blocks):
    """ブロックデータの設定"""
    chara.blockdata = common_blocks + game_blocks
    chara.serialized_lstinfo_order = chara.blockdata
    chara.original_lstinfo_order = chara.blockdata


def copy_common_blocks(target, source, blocks=None):
    """共通ブロックのコピー"""
    if blocks is None:
        blocks = COMMON_BLOCKS
    for block in blocks:
        setattr(target, block, getattr(source, block))
    return blocks


def create_default_sv_gameparameter(image_data):
    """GameParameter_SV のデフォルト値を生成"""
    data = copy.deepcopy(DEFAULT_GAMEPARAMETER_SV)
    data["imageData"] = image_data
    return data


def swap_coordinates(chara, idx1, idx2):
    """コスチュームの順序を入れ替え"""
    coord1 = copy.deepcopy(chara.Coordinate.data[idx1])
    coord2 = copy.deepcopy(chara.Coordinate.data[idx2])
    chara.Coordinate.data[idx1] = coord2
    chara.Coordinate.data[idx2] = coord1


def expand_accessories(chara, from_count, to_count, num_costumes):
    """アクセサリー数を拡張（20→40など）"""
    for _ in range(to_count - from_count):
        chara.Status.data["showAccessory"].append(True)

    for i in range(num_costumes):
        for _ in range(to_count - from_count):
            chara.Coordinate[i]["accessory"]["parts"].append(
                copy.deepcopy(DEFAULT_ACCCESORY_AC)
            )


def shrink_accessories(chara, from_count, to_count, num_costumes):
    """アクセサリー数を縮小（40→20など）"""
    if len(chara.Status.data["showAccessory"]) > to_count:
        chara.Status.data["showAccessory"] = chara.Status.data["showAccessory"][
            :to_count
        ]

    for i in range(num_costumes):
        if len(chara.Coordinate[i]["accessory"]["parts"]) > to_count:
            chara.Coordinate[i]["accessory"]["parts"] = chara.Coordinate[i][
                "accessory"
            ]["parts"][:to_count]


def transform_paint_scale_hc_to_sv(chara, num_costumes=3):
    """ペイントスケールをHC→SV変換"""
    for i in range(num_costumes):
        for n in range(3):
            original_scale = chara["Coordinate"][i]["makeup"]["paintInfos"][n][
                "layout"
            ][3]
            chara["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = (
                0.5 * original_scale + 0.25
            )


def transform_paint_scale_sv_to_hc(chara, num_costumes=3):
    """ペイントスケールをSV→HC変換"""
    for i in range(num_costumes):
        for n in range(3):
            original_scale = chara["Coordinate"][i]["makeup"]["paintInfos"][n][
                "layout"
            ][3]
            chara["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = (
                2 * original_scale - 0.5
            )


def add_sv_specific_fields(chara, num_costumes=3):
    """SVにしかないフィールドを追加"""
    for i in range(num_costumes):
        chara["Coordinate"][i]["isSteamLimited"] = False
        chara["Coordinate"][i]["coverInfos"] = [
            {"use": False, "infoTable": {}} for _ in range(8)
        ]


def remove_sv_specific_fields(chara, num_costumes=3):
    """SVにしかないフィールドを削除"""
    for i in range(num_costumes):
        if "isSteamLimited" in chara["Coordinate"][i]:
            del chara["Coordinate"][i]["isSteamLimited"]
        if "coverInfos" in chara["Coordinate"][i]:
            del chara["Coordinate"][i]["coverInfos"]


def add_ac_specific_accessory_fields(chara, num_costumes=4):
    """ACのアクセサリー固有フィールドを追加"""
    for i in range(num_costumes):
        for n in range(40):
            chara.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"] = -1
            chara.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"] = [
                True for _ in range(3)
            ]


def remove_ac_specific_accessory_fields(chara, num_costumes=3):
    """ACのアクセサリー固有フィールドを削除"""
    for i in range(num_costumes):
        for n in range(len(chara.Coordinate[i]["accessory"]["parts"])):
            if "hideCategoryClothes" in chara.Coordinate[i]["accessory"]["parts"][n]:
                del chara.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"]
            if "visibleTimings" in chara.Coordinate[i]["accessory"]["parts"][n]:
                del chara.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"]


# ========================================
# 変換関数
# ========================================


# ハニカムキャラ->サマすくキャラへの変換
def hc_to_sv(hc: HoneycomeCharaData) -> SummerVacationCharaData:
    assert isinstance(hc, HoneycomeCharaData)

    # 基本初期化
    config = GAME_CONFIG["SV"]
    svc = init_chara_base(config["class"], hc, config["header"], config["product_no"])

    # ブロックデータの設定と共通ブロックのコピー
    common_blocks = copy_common_blocks(svc, hc)
    setup_blockdata(svc, common_blocks, config["blocks"])

    # ゲーム固有データの初期化
    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")
    svc.GameParameter_SV.data = create_default_sv_gameparameter(svc.image)
    svc.GameInfo_SV.data = {}

    # SV固有のフィールド追加
    add_sv_specific_fields(svc)

    # ペイントスケール変換
    transform_paint_scale_hc_to_sv(svc)

    # 性格を"普通"にする
    svc["Parameter"]["personality"] = 0

    return svc


# サマすくキャラ->ハニカムキャラへの変換
def sv_to_hc(svc: SummerVacationCharaData) -> HoneycomeCharaData:
    assert isinstance(svc, SummerVacationCharaData)

    # 基本初期化（サマすくに顔データはないため通常画像で代用）
    config = GAME_CONFIG["HC"]
    hc = init_chara_base(
        config["class"],
        svc,
        config["header"],
        config["product_no"],
        face_image=svc.image,
    )

    # ブロックデータの設定と共通ブロックのコピー
    common_blocks = copy_common_blocks(hc, svc)
    setup_blockdata(hc, common_blocks, config["blocks"])

    # ゲーム固有データの初期化
    hc.GameParameter_HC = StubBlockData("GameParameter_HC", "0.0.0")
    hc.GameInfo_HC = StubBlockData("GameInfo_HC", "0.0.0")
    hc.GameParameter_HC.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_HC)
    hc.GameInfo_HC.data = copy.deepcopy(DEFAULT_GAMEINFO_HC)

    # SV固有のフィールド削除
    remove_sv_specific_fields(hc)

    # ペイントスケール変換
    transform_paint_scale_sv_to_hc(hc)

    # 性格を"明るい"にする
    hc["Parameter"]["personality"] = 0

    return hc


# サマすくキャラ->アイコミキャラへの変換
def sv_to_ac(svc: SummerVacationCharaData) -> AicomiCharaData:
    assert isinstance(svc, SummerVacationCharaData)

    # 基本初期化
    config = GAME_CONFIG["AC"]
    ac = init_chara_base(config["class"], svc, config["header"], config["product_no"])

    # ブロックデータの設定と共通ブロックのコピー
    common_blocks = copy_common_blocks(ac, svc)
    setup_blockdata(ac, common_blocks, config["blocks"])

    # ゲーム固有データの初期化
    ac.GameParameter_AC = StubBlockData("GameParameter_AC", "0.0.0")
    ac.GameInfo_AC = StubBlockData("GameInfo_AC", "0.0.0")
    ac.GameParameter_AC.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_AC)
    ac.GameParameter_AC.data["imageData"] = svc.GameParameter_SV.data["imageData"]
    ac.GameInfo_AC.data = {"version": "0.0.0"}

    # ニックネーム追加
    ac.Parameter.data["nickname"] = ""

    # 4番目のコスチューム(祭り衣装)を追加
    ac.Coordinate.data.append(copy.deepcopy(ac.Coordinate.data[-1]))

    # 私服と役職服の順序を入れ替え（サマすくの私服がアイコミの私服になる）
    swap_coordinates(ac, 0, 1)

    # アクセサリー拡張(20->40対応)
    expand_accessories(ac, 20, 40, 4)

    # AC固有のアクセサリーフィールドを追加
    add_ac_specific_accessory_fields(ac, 4)

    return ac


# アイコミキャラ->サマすくキャラへの変換
def ac_to_sv(ac: AicomiCharaData) -> SummerVacationCharaData:
    assert isinstance(ac, AicomiCharaData)

    # 基本初期化
    config = GAME_CONFIG["SV"]
    svc = init_chara_base(config["class"], ac, config["header"], config["product_no"])

    # ブロックデータの設定と共通ブロックのコピー
    common_blocks = copy_common_blocks(svc, ac)
    setup_blockdata(svc, common_blocks, config["blocks"])

    # ゲーム固有データの初期化
    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")
    svc.GameParameter_SV.data = create_default_sv_gameparameter(
        ac.GameParameter_AC.data["imageData"]
    )
    svc.GameInfo_SV.data = {"version": "0.0.0"}

    # 私服と役職服の順序を元に戻す（ACの私服→SVSの役職服、ACの制服→SVSの私服）
    swap_coordinates(svc, 0, 1)

    # 4番目のコスチューム（祭り衣装）を削除（SVSは3つのコスチュームのみ）
    if len(svc.Coordinate.data) > 3:
        svc.Coordinate.data = svc.Coordinate.data[:3]

    # アクセサリー縮小(40->20対応)
    shrink_accessories(svc, 40, 20, 3)

    # AC固有のアクセサリーフィールドを削除
    remove_ac_specific_accessory_fields(svc, 3)

    # ニックネーム（ACにしかないフィールド）を削除
    if "nickname" in svc.Parameter.data:
        del svc.Parameter.data["nickname"]

    return svc


# ========================================
# Streamlit UI
# ========================================

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

# 説明文
st.markdown(get_text("description", lang))

# 各ゲームごとの違いを展開可能なセクションに
with st.expander(get_text("expander_title", lang)):
    st.markdown(get_text("expander_content", lang))

st.divider()

# ファイルアップローダー
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

    if header not in ["【HCChara】", "【SVChara】", "【ACChara】"]:
        st.error(f"{get_text('error_unsupported', lang)} {header}", icon="🚨")
        st.stop()

    source = file.getvalue()

    if header == "【HCChara】":
        st.write(get_text("file_is_hc", lang))
        hc = HoneycomeCharaData.load(source)
        name = " ".join([hc["Parameter"]["lastname"], hc["Parameter"]["firstname"]])
        target = st.radio(
            get_text("target_select", lang),
            options=["SV", "AC"],
            format_func=lambda x: get_text(f"target_{x.lower()}", lang),
            horizontal=True,
        )
        converted = hc_to_sv(hc) if target == "SV" else sv_to_ac(hc_to_sv(hc))
        st.download_button(
            get_text(f"download_{target.lower()}", lang),
            bytes(converted),
            file_name=f"{target.lower()}_converted_{name}.png",
        )

    elif header == "【SVChara】":
        st.write(get_text("file_is_sv", lang))
        svc = SummerVacationCharaData.load(source)
        name = " ".join([svc["Parameter"]["lastname"], svc["Parameter"]["firstname"]])
        target = st.radio(
            get_text("target_select", lang),
            options=["HC", "AC"],
            format_func=lambda x: get_text(f"target_{x.lower()}", lang),
            horizontal=True,
        )
        converted = sv_to_hc(svc) if target == "HC" else sv_to_ac(svc)
        st.download_button(
            get_text(f"download_{target.lower()}", lang),
            bytes(converted),
            file_name=f"{target.lower()}_converted_{name}.png",
        )

    elif header == "【ACChara】":
        st.write(get_text("file_is_ac", lang))
        ac = AicomiCharaData.load(source)
        name = " ".join([ac["Parameter"]["lastname"], ac["Parameter"]["firstname"]])
        target = st.radio(
            get_text("target_select", lang),
            options=["SV", "HC"],
            format_func=lambda x: get_text(f"target_{x.lower()}", lang),
            horizontal=True,
        )
        converted = ac_to_sv(ac) if target == "SV" else sv_to_hc(ac_to_sv(ac))
        st.download_button(
            get_text(f"download_{target.lower()}", lang),
            bytes(converted),
            file_name=f"{target.lower()}_converted_{name}.png",
        )
