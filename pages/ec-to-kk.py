import copy
import io
import uuid

import streamlit as st
from kkloader.EmocreCharaData import EmocreCharaData  # noqa
from kkloader.funcs import get_png, load_length, load_type
from kkloader.KoikatuCharaData import BlockData, Coordinate, KoikatuCharaData  # noqa

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "コイカツシリーズキャラクター変換ツール",
        "description": """
コイカツ↔コイカツサンシャイン↔エモーションクリエイターズのキャラクターを相互変換するツールです。

**⚠️注意事項**: 完全互換ではありません。変換前のデータはバックアップしておきましょう。
""",
        "expander_title": "変換時の注意とデータ差分",
        "expander_content": """
- 各シリーズで互換性のない部分は、そのまま削除するか、既定値で補完します。
- KK/KKS → EC では一番目のコーディネートを採用します。
- EC → KK/KKS では 1つのコーデを複製して出力します。
- KK ↔ KKS では `Coordinate` はそのまま保持し、主にヘッダ、`Parameter`、`Custom`、`Status`、`About` を調整します。
- `KKEx` はチェックボックスを有効にするとそのままコピーします。MOD環境が双方で異なっている場合、読み込めない可能性があります。
  - どのMODを使っているのかは [こちらのページ](/chara-data-viewer) を使って調べることができます。

| 項目 | エモーションクリエイターズ | コイカツ | コイカツサンシャイン |
| --- | --- | --- | --- |
| ヘッダ | `【EroMakeChara】` | `【KoiKatuChara】` | `【KoiKatuCharaSun】` |
| コーデ構造 | 単一 `Coordinate` | 複数 `Coordinate` | 複数 `Coordinate` |
| 名前フィールド | `fullname` | `lastname` + `firstname` | `lastname` + `firstname` |
| ヘッダ固有メタデータ | `language` / `userid` / `dataid` / `packages` | なし | なし |
| `About` ブロック | 使用しない前提 | 任意 | 使用 |
| このツールでの補完 | KK/KKS 由来データを既定値で補完 | EC 由来データをKK形式へ展開 | KK形式をベースにSunshine向け項目を追加 |
| `KKEx` | 任意でコピー | 任意でコピー | 任意でコピー |
""",
        "file_uploader": "コイカツ/コイカツサンシャイン/エモクリのキャラクター画像を選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "error_unsupported": "このヘッダのファイルには対応していません:",
        "header_label": "ヘッダ:",
        "name_label": "キャラクター名:",
        "card_image_caption": "カード画像",
        "file_is_ec": "このファイルは **エモーションクリエイターズ** のキャラデータです。",
        "file_is_kk": "このファイルは **コイカツ** のキャラデータです。",
        "file_is_kks": "このファイルは **コイカツサンシャイン** のキャラデータです。",
        "target_select": "変換先を選択",
        "target_ec": "エモーションクリエイターズ",
        "target_kk": "コイカツ",
        "target_kks": "コイカツサンシャイン",
        "copy_kkex": "MODデータ(KKExブロック)をそのままコピーする",
        "success_convert": "正常にデータを変換しました。",
        "download_button": "{target}のキャラとしてダウンロード",
    },
    "en": {
        "title": "Koikatsu Series Character Converter",
        "description": """
A tool to convert characters between Koikatsu ↔ Koikatsu Sunshine ↔ Emotion Creators.

**⚠️Caution**: This is not a perfect round-trip conversion. Back up your data before converting.
""",
        "expander_title": "Conversion Notes and Data Differences",
        "expander_content": """
- Parts that are not compatible between series are either removed or filled with default values.
- For KK/KKS → EC, the first coordinate is used.
- For EC → KK/KKS, the single EC coordinate is duplicated.
- For KK ↔ KKS, `Coordinate` is preserved as-is. The converter mainly adjusts the header, `Parameter`, `Custom`, `Status`, and `About`.
- `KKEx` can be copied as-is via the checkbox. If the MOD environment differs between the two sides, it may fail to load.
  - You can check which MODs are used with [this page](/chara-data-viewer).

| Item | Emotion Creators | Koikatsu | Koikatsu Sunshine |
| --- | --- | --- | --- |
| Header | `【EroMakeChara】` | `【KoiKatuChara】` | `【KoiKatuCharaSun】` |
| Coordinate structure | Single `Coordinate` | Multiple `Coordinate` entries | Multiple `Coordinate` entries |
| Name fields | `fullname` | `lastname` + `firstname` | `lastname` + `firstname` |
| Header-specific metadata | `language` / `userid` / `dataid` / `packages` | None | None |
| `About` block | Assumed unused | Optional | Used |
| Tool-side fallback | Fills EC-only fields with defaults when converting from KK/KKS | Expands EC data into KK format | Adds Sunshine-oriented fields on top of KK-style data |
| `KKEx` | Optionally copied | Optionally copied | Optionally copied |
""",
        "file_uploader": "Select a character image (Koikatsu / Koikatsu Sunshine / Emotion Creators)",
        "error_load": "Failed to load file. Unsupported file format.",
        "error_unsupported": "This header file is not supported:",
        "header_label": "Header:",
        "name_label": "Character name:",
        "card_image_caption": "Card image",
        "file_is_ec": "This file is an **Emotion Creators** character.",
        "file_is_kk": "This file is a **Koikatsu** character.",
        "file_is_kks": "This file is a **Koikatsu Sunshine** character.",
        "target_select": "Select conversion target",
        "target_ec": "Emotion Creators",
        "target_kk": "Koikatsu",
        "target_kks": "Koikatsu Sunshine",
        "copy_kkex": "Copy MOD data (KKEx block).",
        "success_convert": "Data converted successfully.",
        "download_button": "Download as {target} character",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


class CharacterHeader:
    @classmethod
    def load(cls, filelike, contains_png=True):
        header = cls()

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

        header.image = None
        if contains_png:
            header.image = get_png(data_stream)

        header.product_no = load_type(data_stream, "i")
        header.header = load_length(data_stream, "b")
        header.version = load_length(data_stream, "b")

        return header


class StubBlockData(BlockData):
    def __init__(self, name, version, data=None):
        self.name = name
        self.version = version
        self.data = {} if data is None else data


KK_ATTRIBUTE_KEYS = [
    "hinnyo",
    "harapeko",
    "donkan",
    "choroi",
    "bitch",
    "mutturi",
    "dokusyo",
    "ongaku",
    "kappatu",
    "ukemi",
    "friendly",
    "kireizuki",
    "taida",
    "sinsyutu",
    "hitori",
    "undo",
    "majime",
    "likeGirls",
]
KKS_ATTRIBUTE_KEYS = [
    "harapeko",
    "choroi",
    "dokusyo",
    "ongaku",
    "okute",
    "friendly",
    "kireizuki",
    "sinsyutu",
    "hitori",
    "active",
    "majime",
    "info",
    "love",
    "talk",
    "nakama",
    "nonbiri",
    "hinnyo",
    "likeGirls",
    "bitch",
    "mutturi",
    "lonely",
    "ukemi",
    "undo",
]
EC_PARAMETER_FIELDS_REMOVED_BY_KK = [
    "lastname",
    "firstname",
    "nickname",
    "callType",
    "clubActivities",
    "weakPoint",
    "awnser",
    "denial",
    "attribute",
    "aggressive",
    "diligence",
    "kindness",
]


def _sync_blockdata_order(chara):
    chara.serialized_lstinfo_order = copy.deepcopy(chara.blockdata)
    chara.original_lstinfo_order = copy.deepcopy(chara.blockdata)


def _add_about_block(chara):
    if "About" not in chara.blockdata:
        insert_at = (
            chara.blockdata.index("KKEx")
            if "KKEx" in chara.blockdata
            else len(chara.blockdata)
        )
        chara.blockdata.insert(insert_at, "About")
    chara.About = StubBlockData(
        "About",
        "0.0.0",
        {
            "version": "0.0.0",
            "language": 0,
            "userID": str(uuid.uuid4()),
            "dataID": str(uuid.uuid4()),
        },
    )
    _sync_blockdata_order(chara)


def _remove_block(chara, block_name):
    if block_name in chara.blockdata:
        chara.blockdata.remove(block_name)
    if hasattr(chara, block_name):
        delattr(chara, block_name)
    _sync_blockdata_order(chara)


def _convert_attributes_kk_to_kks(attributes):
    converted = {key: False for key in KKS_ATTRIBUTE_KEYS}
    shared_keys = set(KK_ATTRIBUTE_KEYS) & set(KKS_ATTRIBUTE_KEYS)
    for key in shared_keys:
        converted[key] = bool(attributes.get(key, False))
    converted["active"] = bool(attributes.get("kappatu", False))
    converted["nonbiri"] = bool(attributes.get("taida", False))
    return converted


def _convert_attributes_kks_to_kk(attributes):
    converted = {key: False for key in KK_ATTRIBUTE_KEYS}
    shared_keys = set(KK_ATTRIBUTE_KEYS) & set(KKS_ATTRIBUTE_KEYS)
    for key in shared_keys:
        converted[key] = bool(attributes.get(key, False))
    converted["kappatu"] = bool(attributes.get("active", False))
    converted["taida"] = bool(attributes.get("nonbiri", False))
    return converted


def _build_ec_fullname(parameter):
    firstname = str(parameter.data.get("firstname", "")).strip()
    lastname = str(parameter.data.get("lastname", "")).strip()
    if lastname and firstname:
        return f"{lastname} {firstname}"
    return firstname or lastname


def _get_character_name(chara, source_type):
    if source_type == "EC":
        return chara["Parameter"]["fullname"]

    lastname = str(chara["Parameter"]["lastname"]).strip()
    firstname = str(chara["Parameter"]["firstname"]).strip()
    return f"{lastname} {firstname}".strip() or firstname or lastname


def _apply_kkex_policy(chara, copy_kkex):
    if not copy_kkex:
        _remove_block(chara, "KKEx")


def kk_to_kks(kk, copy_kkex=False):
    assert isinstance(kk, KoikatuCharaData)

    default_kks_interest = {"answer": [-1, -1]}
    default_kks_hair_gloss_color = [
        0.8509804010391235,
        0.8509804010391235,
        0.8509804010391235,
        1.0,
    ]

    converted = copy.deepcopy(kk)
    converted.header = "【KoiKatuCharaSun】".encode("utf-8")
    converted.version = "0.0.0".encode("ascii")

    _add_about_block(converted)

    converted.Parameter.version = "0.0.6"
    converted.Parameter["version"] = "0.0.6"
    converted.Parameter["interest"] = copy.deepcopy(default_kks_interest)
    converted.Parameter["attribute"] = _convert_attributes_kk_to_kks(
        converted.Parameter["attribute"]
    )

    converted.Custom["face"]["version"] = "0.0.3"
    converted.Custom["face"]["hlUpX"] = 0.5
    converted.Custom["face"]["hlDownX"] = 0.5
    converted.Custom["hair"]["version"] = "0.0.5"
    for part in converted.Custom["hair"]["parts"]:
        part["glossColor"] = copy.deepcopy(default_kks_hair_gloss_color)

    converted.Status["eyesBlink"] = True
    converted.Status["eyesLookPtn"] = 0
    converted.Status["mouthFixed"] = False
    converted.Status["mouthOpenMax"] = 1.0
    converted.Status["mouthPtn"] = 0
    converted.Status["neckLookPtn"] = 0
    converted.Status["visibleSonAlways"] = True

    _apply_kkex_policy(converted, copy_kkex)

    return converted


def kks_to_kk(kks, copy_kkex=False):
    assert isinstance(kks, KoikatuCharaData)

    converted = copy.deepcopy(kks)
    converted.header = "【KoiKatuChara】".encode("utf-8")
    converted.version = "0.0.0".encode("ascii")

    _remove_block(converted, "About")

    converted.Parameter.version = "0.0.5"
    converted.Parameter["version"] = "0.0.5"
    if "interest" in converted.Parameter.data:
        del converted.Parameter["interest"]
    converted.Parameter["attribute"] = _convert_attributes_kks_to_kk(
        converted.Parameter["attribute"]
    )

    converted.Custom["face"]["version"] = "0.0.2"
    converted.Custom["face"].pop("hlUpX", None)
    converted.Custom["face"].pop("hlDownX", None)
    converted.Custom["hair"]["version"] = "0.0.4"
    for part in converted.Custom["hair"]["parts"]:
        part.pop("glossColor", None)

    converted.Status["eyesBlink"] = False
    converted.Status["eyesLookPtn"] = 1
    converted.Status["mouthFixed"] = True
    converted.Status["mouthOpenMax"] = 0.0
    converted.Status["mouthPtn"] = 1
    converted.Status["neckLookPtn"] = 3
    converted.Status["visibleSonAlways"] = False

    _apply_kkex_policy(converted, copy_kkex)

    return converted


def ec_to_kk(ec, copy_kkex=False):
    assert isinstance(ec, EmocreCharaData)

    kk = KoikatuCharaData()

    kk.image = ec.image
    kk.face_image = ec.image
    kk.product_no = 100
    kk.header = "【KoiKatuChara】".encode("utf-8")
    kk.version = "0.0.0".encode("ascii")
    kk.blockdata = copy.deepcopy(ec.blockdata)
    kk.serialized_lstinfo_order = copy.deepcopy(kk.blockdata)
    kk.original_lstinfo_order = copy.deepcopy(kk.blockdata)

    kk.Custom = copy.deepcopy(ec.Custom)
    kk.Coordinate = Coordinate(data=None, version="0.0.0")
    kk.Parameter = copy.deepcopy(ec.Parameter)
    kk.Status = copy.deepcopy(ec.Status)

    if "About" in ec.blockdata:
        kk.About = copy.deepcopy(ec.About)
    if "KKEx" in ec.blockdata and copy_kkex:
        kk.KKEx = copy.deepcopy(ec.KKEx)

    kk.Custom["face"]["version"] = "0.0.2"
    kk.Custom["face"]["pupilHeight"] *= 1.08
    kk.Custom["face"]["hlUpY"] = (kk.Custom["face"]["hlUpY"] - 0.25) * 2
    del kk.Custom["face"]["hlUpX"]
    del kk.Custom["face"]["hlDownX"]
    del kk.Custom["face"]["hlUpScale"]
    del kk.Custom["face"]["hlDownScale"]
    kk.Custom["body"]["version"] = "0.0.2"
    kk.Custom["hair"]["version"] = "0.0.4"

    ec_coordinate = copy.deepcopy(ec.Coordinate.data)
    ec_coordinate["clothes"]["hideBraOpt"] = [False, False]
    ec_coordinate["clothes"]["hideShortsOpt"] = [False, False]
    for i, p in enumerate(ec_coordinate["clothes"]["parts"]):
        a = {
            "emblemeId": p["emblemeId"][0],
            "emblemeId2": p["emblemeId"][1],
        }
        ec_coordinate["clothes"]["parts"][i].update(a)
    ec_coordinate["clothes"]["parts"].append(ec_coordinate["clothes"]["parts"][-1])
    for i, _ in enumerate(ec_coordinate["accessory"]["parts"]):
        del ec_coordinate["accessory"]["parts"][i]["hideTiming"]
    makeup = copy.deepcopy(ec.Custom["face"]["baseMakeup"])
    kk.Coordinate.data = [
        {
            "clothes": ec_coordinate["clothes"],
            "accessory": ec_coordinate["accessory"],
            "enableMakeup": False,
            "makeup": makeup,
        }
    ] * 7

    kk.Parameter["version"] = "0.0.5"
    kk.Parameter["lastname"] = " "
    kk.Parameter["firstname"] = ec.Parameter["fullname"]
    kk.Parameter["nickname"] = " "
    kk.Parameter["callType"] = -1
    kk.Parameter["clubActivities"] = 0
    kk.Parameter["weakPoint"] = 0
    items = [
        "animal",
        "eat",
        "cook",
        "exercise",
        "study",
        "fashionable",
        "blackCoffee",
        "spicy",
        "sweet",
    ]
    kk.Parameter["awnser"] = dict.fromkeys(items, True)
    items = ["kiss", "aibu", "anal", "massage", "notCondom"]
    kk.Parameter["denial"] = dict.fromkeys(items, False)
    items = [
        "hinnyo",
        "harapeko",
        "donkan",
        "choroi",
        "bitch",
        "mutturi",
        "dokusyo",
        "ongaku",
        "kappatu",
        "ukemi",
        "friendly",
        "kireizuki",
        "taida",
        "sinsyutu",
        "hitori",
        "undo",
        "majime",
        "likeGirls",
    ]
    kk.Parameter["attribute"] = dict.fromkeys(items, True)
    kk.Parameter["aggressive"] = 0
    kk.Parameter["diligence"] = 0
    kk.Parameter["kindness"] = 0
    del kk.Parameter["fullname"]
    kk.Parameter["personality"] = 0

    kk.Status["version"] = "0.0.0"
    kk.Status["clothesState"] = b"\x00" * 9
    kk.Status["eyesBlink"] = False
    kk.Status["mouthPtn"] = 1
    kk.Status["mouthOpenMax"] = 0
    kk.Status["mouthFixed"] = True
    kk.Status["eyesLookPtn"] = 1
    kk.Status["neckLookPtn"] = 3
    kk.Status["visibleSonAlways"] = False
    del kk.Status["mouthOpenMin"]
    del kk.Status["enableSonDirection"]
    del kk.Status["sonDirectionX"]
    del kk.Status["sonDirectionY"]
    kk.Status["coordinateType"] = 4
    kk.Status["backCoordinateType"] = 0
    kk.Status["shoesType"] = 1

    _apply_kkex_policy(kk, copy_kkex)

    return kk


def kk_to_ec(kk, copy_kkex=False):
    assert isinstance(kk, KoikatuCharaData)

    default_ec_hl_x = 0.5
    default_ec_hl_down_y = 0.75
    default_ec_hl_scale = 0.5
    default_ec_hide_timing = 1
    default_ec_personality = 0
    default_ec_ex_type = 0
    default_ec_mouth_open_min = 0
    default_ec_mouth_open_max = 1
    default_ec_mouth_ptn = 0
    default_ec_eyes_look_ptn = 0
    default_ec_neck_look_ptn = 0
    default_ec_visible_son_always = True
    default_ec_enable_son_direction = False
    default_ec_son_direction_x = 0
    default_ec_son_direction_y = 0
    default_ec_enable_shape_hand = [False, False]
    default_ec_shape_hand_ptn = [2, 2, [0, 0, 0, 0]]
    default_ec_shape_hand_blend_value = [0, 0]

    ec = EmocreCharaData()

    ec.image = kk.image
    ec.product_no = 200
    ec.header = "【EroMakeChara】".encode("utf-8")
    ec.version = "0.0.1".encode("ascii")
    ec.language = 0
    ec.userid = str(uuid.uuid4()).encode("ascii")
    ec.dataid = str(uuid.uuid4()).encode("ascii")
    ec.packages = [0]
    ec.blockdata = copy.deepcopy(kk.blockdata)
    ec.serialized_lstinfo_order = copy.deepcopy(ec.blockdata)
    ec.original_lstinfo_order = copy.deepcopy(ec.blockdata)

    ec.Custom = copy.deepcopy(kk.Custom)
    ec.Parameter = copy.deepcopy(kk.Parameter)
    ec.Status = copy.deepcopy(kk.Status)

    _remove_block(ec, "About")
    if "KKEx" in kk.blockdata and copy_kkex:
        ec.KKEx = copy.deepcopy(kk.KKEx)

    ec.Custom.version = "0.0.0"
    ec.Custom["face"]["version"] = "0.0.1"
    ec.Custom["face"]["pupilHeight"] *= 0.92
    ec.Custom["face"]["hlUpY"] = ec.Custom["face"]["hlUpY"] / 2 + 0.25
    ec.Custom["face"]["hlUpX"] = default_ec_hl_x
    ec.Custom["face"]["hlDownX"] = default_ec_hl_x
    ec.Custom["face"]["hlDownY"] = default_ec_hl_down_y
    ec.Custom["face"]["hlUpScale"] = default_ec_hl_scale
    ec.Custom["face"]["hlDownScale"] = default_ec_hl_scale
    ec.Custom["body"]["version"] = "0.0.0"
    ec.Custom["body"]["typeBone"] = 0
    ec.Custom["hair"]["version"] = "0.0.1"
    for part in ec.Custom["hair"]["parts"]:
        part["noShake"] = False

    coordinate = copy.deepcopy(
        kk.Coordinate.data[0]
        if isinstance(kk.Coordinate.data, list)
        else kk.Coordinate.data
    )
    clothes = coordinate["clothes"]
    accessory = coordinate["accessory"]

    clothes.pop("hideBraOpt", None)
    clothes.pop("hideShortsOpt", None)
    if len(clothes["parts"]) >= 2:
        del clothes["parts"][-2]
    for part in clothes["parts"]:
        part["emblemeId"] = [part.pop("emblemeId", 0), part.pop("emblemeId2", 0)]
        part["hideOpt"] = [False, False]
        part["sleevesType"] = 0

    for part in accessory["parts"]:
        part["hideTiming"] = default_ec_hide_timing
        part["noShake"] = False

    ec.Coordinate = Coordinate(data=None, version="0.0.1")
    ec.Coordinate.data = {
        "clothes": clothes,
        "accessory": accessory,
    }

    ec.Parameter.version = "0.0.0"
    ec.Parameter["version"] = "0.0.0"
    ec.Parameter["fullname"] = " ".join(
        [str(kk.Parameter["lastname"]), str(kk.Parameter["firstname"])]
    )
    for field in EC_PARAMETER_FIELDS_REMOVED_BY_KK:
        ec.Parameter.data.pop(field, None)
    ec.Parameter["personality"] = default_ec_personality
    ec.Parameter["exType"] = default_ec_ex_type

    ec.Status.version = "0.0.1"
    ec.Status["version"] = "0.0.1"
    ec.Status["clothesState"] = b"\x00" * 8
    ec.Status["eyesBlink"] = True
    ec.Status["mouthPtn"] = default_ec_mouth_ptn
    ec.Status["mouthOpenMin"] = default_ec_mouth_open_min
    ec.Status["mouthOpenMax"] = default_ec_mouth_open_max
    ec.Status["mouthFixed"] = False
    ec.Status["eyesLookPtn"] = default_ec_eyes_look_ptn
    ec.Status["neckLookPtn"] = default_ec_neck_look_ptn
    ec.Status["visibleSonAlways"] = default_ec_visible_son_always
    ec.Status["enableSonDirection"] = default_ec_enable_son_direction
    ec.Status["sonDirectionX"] = default_ec_son_direction_x
    ec.Status["sonDirectionY"] = default_ec_son_direction_y
    ec.Status["enableShapeHand"] = copy.deepcopy(default_ec_enable_shape_hand)
    ec.Status["shapeHandPtn"] = copy.deepcopy(default_ec_shape_hand_ptn)
    ec.Status["shapeHandBlendValue"] = copy.deepcopy(default_ec_shape_hand_blend_value)
    ec.Status.data.pop("coordinateType", None)
    ec.Status.data.pop("backCoordinateType", None)
    ec.Status.data.pop("shoesType", None)

    _apply_kkex_policy(ec, copy_kkex)

    return ec


def ec_to_kks(ec, copy_kkex=False):
    assert isinstance(ec, EmocreCharaData)
    return kk_to_kks(ec_to_kk(ec, copy_kkex=copy_kkex), copy_kkex=copy_kkex)


def kks_to_ec(kks, copy_kkex=False):
    assert isinstance(kks, KoikatuCharaData)
    return kk_to_ec(kks_to_kk(kks, copy_kkex=copy_kkex), copy_kkex=copy_kkex)


def _load_character(source, source_type):
    if source_type == "EC":
        return EmocreCharaData.load(source)
    return KoikatuCharaData.load(source)


def _convert_character(chara, source_type, target_type, copy_kkex=False):
    if source_type == "EC" and target_type == "KK":
        return ec_to_kk(chara, copy_kkex=copy_kkex)
    if source_type == "EC" and target_type == "KKS":
        return ec_to_kks(chara, copy_kkex=copy_kkex)
    if source_type == "KK" and target_type == "EC":
        return kk_to_ec(chara, copy_kkex=copy_kkex)
    if source_type == "KK" and target_type == "KKS":
        return kk_to_kks(chara, copy_kkex=copy_kkex)
    if source_type == "KKS" and target_type == "KK":
        return kks_to_kk(chara, copy_kkex=copy_kkex)
    if source_type == "KKS" and target_type == "EC":
        return kks_to_ec(chara, copy_kkex=copy_kkex)
    raise ValueError(f"unsupported conversion: {source_type} -> {target_type}")


def _get_target_options(source_type):
    mapping = {
        "EC": ["KK", "KKS"],
        "KK": ["EC", "KKS"],
        "KKS": ["EC", "KK"],
    }
    return mapping[source_type]


def main():
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
    if file is None:
        return

    try:
        header_info = CharacterHeader.load(file.getvalue())
    except Exception:
        st.error(get_text("error_load", lang), icon="🚨")
        st.stop()

    header = header_info.header.decode("utf-8")
    source_type_map = {
        "【EroMakeChara】": "EC",
        "【KoiKatuChara】": "KK",
        "【KoiKatuCharaSun】": "KKS",
    }
    if header not in source_type_map:
        st.error(f"{get_text('error_unsupported', lang)} {header}", icon="🚨")
        st.stop()

    source_type = source_type_map[header]
    chara = _load_character(file.getvalue(), source_type)
    name = _get_character_name(chara, source_type)

    st.write(get_text("header_label", lang), header)
    st.write(get_text("name_label", lang), name)
    st.write(get_text(f"file_is_{source_type.lower()}", lang))
    st.image(io.BytesIO(chara.image), caption=get_text("card_image_caption", lang))

    target = st.radio(
        get_text("target_select", lang),
        options=_get_target_options(source_type),
        format_func=lambda x: get_text(f"target_{x.lower()}", lang),
        horizontal=True,
    )
    copy_kkex = False
    if "KKEx" in chara.blockdata:
        copy_kkex = st.checkbox(get_text("copy_kkex", lang), value=True)
    converted = _convert_character(
        chara,
        source_type,
        target,
        copy_kkex=copy_kkex,
    )

    st.success(get_text("success_convert", lang), icon="✅")
    st.download_button(
        get_text("download_button", lang).format(
            target=get_text(f"target_{target.lower()}", lang)
        ),
        bytes(converted),
        file_name=f"{target.lower()}_converted_{name}.png",
    )


if __name__ == "__main__":
    main()
