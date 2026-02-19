import copy
import io
from collections import Counter
from typing import Any, Literal

import streamlit as st
from kkloader import (
    AicomiCharaData,
    HoneycomeCharaData,
    HoneycomeSceneData,
    SummerVacationCharaData,
)
from kkloader.KoikatuCharaData import BlockData

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "デジクラキャラクター統一コンバータ",
        "subtitle": "シーン内の全キャラクターを、ハニカム / サマすく / アイコミ のいずれかに一括統一します。キャラクターを差し替える手間を大幅に削減します。",
        "usage_title": "使い方",
        "usage_content": """
1. シーンデータ（.png）をアップロードします
2. 統一先（ハニカム / サマすく / アイコミ）を選択します
3. 「変換を実行」を押します
4. 変換済みシーンをダウンロードします

**補足**
- キャラクターの使用している髪型や服装などのパーツをそのまま(存在するかのチェックなく)コピーするため、変換先のゲームにないパーツはうまく表示されません。
""",
        "file_uploader": "シーンデータ（PNG）をアップロード",
        "file_uploader_help": "デジタルクラフトのシーンデータ（.png）をアップロードしてください",
        "success_load": "シーンデータを読み込みました",
        "error_load": "ファイルの読み込みに失敗しました。シーンデータではない可能性があります。",
        "info_upload": "シーンデータ（.png）をアップロードしてください。",
        "target_title": "統一先",
        "target_label": "キャラクターの統一先を選択",
        "target_hc": "ハニカム",
        "target_sv": "サマすく",
        "target_ac": "アイコミ",
        "execute_button": "変換を実行",
        "download_button": "変換済みシーンをダウンロード",
        "stats_title": "キャラクター統計",
        "stats_total": "キャラクター総数",
        "stats_converted": "実際に形式変換した数",
        "stats_failed": "変換失敗数",
        "headers_before": "変換前のヘッダー内訳",
        "headers_after": "変換後のヘッダー内訳",
        "no_characters": "キャラクターが見つかりませんでした。",
        "success_convert": "変換完了: {converted} / {total} 体を変換しました。",
        "warning_failed": "一部のキャラクターは変換できませんでした（{count}件）。詳細は下を確認してください。",
        "failed_table_title": "変換失敗一覧",
    },
    "en": {
        "title": "Digital Craft Character Unifier",
        "subtitle": "Unify all characters in a scene to Honeycome / Summer Vacation Scramble / Aicomi in one batch, greatly reducing the effort of replacing characters.",
        "usage_title": "How to use",
        "usage_content": """
1. Upload a scene file (.png)
2. Select the unified target (Honeycome / Summer Vacation Scramble / Aicomi)
3. Click "Execute Conversion"
4. Download the converted scene

**Notes**
- Character parts (hairstyles, outfits, etc.) are copied as-is without checking whether they exist in the target game, so parts that do not exist in the target game may not display correctly.
""",
        "file_uploader": "Upload scene data (PNG)",
        "file_uploader_help": "Please upload a Digital Craft scene data (.png)",
        "success_load": "Scene data loaded successfully",
        "error_load": "Failed to load file. It may not be a scene data file.",
        "info_upload": "Please upload a scene data (.png).",
        "target_title": "Target",
        "target_label": "Select unified character format",
        "target_hc": "Honeycome",
        "target_sv": "Summer Vacation Scramble",
        "target_ac": "Aicomi",
        "execute_button": "Execute Conversion",
        "download_button": "Download converted scene",
        "stats_title": "Character Stats",
        "stats_total": "Total characters",
        "stats_converted": "Actually converted",
        "stats_failed": "Failed conversions",
        "headers_before": "Headers before conversion",
        "headers_after": "Headers after conversion",
        "no_characters": "No characters found.",
        "success_convert": "Completed: converted {converted} / {total} characters.",
        "warning_failed": "Some characters failed to convert ({count}). See details below.",
        "failed_table_title": "Failed conversions",
    },
}


def get_text(key: str, lang: str = "ja") -> str:
    """指定言語の文言辞書からキーに対応するテキストを返す。"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


class StubBlockData(BlockData):
    def __init__(self, name: str, version: str) -> None:
        """空データを持つ簡易BlockDataを初期化する。"""
        self.name = name
        self.data = {}
        self.version = version


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
HONEYCOME_HEADERS = {"【HCChara】", "【HCPChara】", "【DCChara】"}

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

DEFAULT_GAMEPARAMETER_AC = {
    "version": "0.0.0",
    "imageData": None,
    "clubActivities": 3,
    "individuality": [False] * 18,
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

DEFAULT_GAMEINFO_SV = {}
DEFAULT_GAMEINFO_AC = {"version": "0.0.0"}


def decode_header(chara: Any) -> str:
    """キャラクターのヘッダーをUTF-8文字列として取得する。"""
    header = getattr(chara, "header", b"")
    if isinstance(header, bytes):
        return header.decode("utf-8", errors="replace")
    return str(header)


def get_character_name(chara: Any) -> str:
    """Parameterブロックから姓名を取得し、表示名を返す。"""
    try:
        if "Parameter" in chara.blockdata:
            param = chara["Parameter"]
            lastname = param.data.get("lastname", "")
            firstname = param.data.get("firstname", "")
            name = f"{lastname} {firstname}".strip()
            if name:
                return name
    except Exception:
        pass
    return "Unknown"


def init_chara_base(
    target_class: type,
    source: Any,
    header: str,
    product_no: int,
    face_image: bytes | None = None,
) -> Any:
    """変換先キャラクターのヘッダー・基本メタ情報を初期化する。"""
    chara = target_class()
    # シーン埋め込みキャラは画像未保持前提のため常に None にする。
    chara.image = None
    chara.face_image = face_image if face_image is not None else b""
    chara.product_no = product_no
    chara.header = header.encode("utf-8")
    chara.version = "0.0.0".encode("utf-8")
    return chara


def setup_blockdata(
    chara: Any, common_blocks: list[str], game_blocks: list[str]
) -> None:
    """blockdata配列とシリアライズ順序を設定する。"""
    chara.blockdata = common_blocks + game_blocks
    chara.serialized_lstinfo_order = chara.blockdata
    chara.original_lstinfo_order = chara.blockdata


def copy_common_blocks(
    target: Any, source: Any, blocks: list[str] | None = None
) -> list[str]:
    """共通ブロックをsourceからtargetへコピーする。"""
    if blocks is None:
        blocks = COMMON_BLOCKS
    for block in blocks:
        setattr(target, block, getattr(source, block))
    return blocks


def create_default_sv_gameparameter(image_data: bytes | None) -> dict[str, Any]:
    """SV用GameParameterデフォルト辞書を作成する。"""
    data = copy.deepcopy(DEFAULT_GAMEPARAMETER_SV)
    data["imageData"] = image_data
    return data


def swap_coordinates(chara: Any, idx1: int, idx2: int) -> None:
    """指定した2つのコーディネート要素を入れ替える。"""
    coord1 = copy.deepcopy(chara.Coordinate.data[idx1])
    coord2 = copy.deepcopy(chara.Coordinate.data[idx2])
    chara.Coordinate.data[idx1] = coord2
    chara.Coordinate.data[idx2] = coord1


def expand_accessories(
    chara: Any, from_count: int, to_count: int, num_costumes: int
) -> None:
    """アクセサリー枠を拡張し、必要な空パーツを追加する。"""
    for _ in range(to_count - from_count):
        chara.Status.data["showAccessory"].append(True)

    for i in range(num_costumes):
        for _ in range(to_count - from_count):
            chara.Coordinate[i]["accessory"]["parts"].append(
                copy.deepcopy(DEFAULT_ACCCESORY_AC)
            )


def shrink_accessories(
    chara: Any, from_count: int, to_count: int, num_costumes: int
) -> None:
    """アクセサリー枠を縮小し、余剰パーツを切り詰める。"""
    if len(chara.Status.data["showAccessory"]) > to_count:
        chara.Status.data["showAccessory"] = chara.Status.data["showAccessory"][
            :to_count
        ]

    for i in range(num_costumes):
        if len(chara.Coordinate[i]["accessory"]["parts"]) > to_count:
            chara.Coordinate[i]["accessory"]["parts"] = chara.Coordinate[i][
                "accessory"
            ]["parts"][:to_count]


def transform_paint_scale_hc_to_sv(chara: Any, num_costumes: int = 3) -> None:
    """HC形式のペイントスケールをSV形式へ変換する。"""
    for i in range(num_costumes):
        for n in range(3):
            original_scale = chara["Coordinate"][i]["makeup"]["paintInfos"][n][
                "layout"
            ][3]
            chara["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = (
                0.5 * original_scale + 0.25
            )


def transform_paint_scale_sv_to_hc(chara: Any, num_costumes: int = 3) -> None:
    """SV形式のペイントスケールをHC形式へ変換する。"""
    for i in range(num_costumes):
        for n in range(3):
            original_scale = chara["Coordinate"][i]["makeup"]["paintInfos"][n][
                "layout"
            ][3]
            chara["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = (
                2 * original_scale - 0.5
            )


def add_sv_specific_fields(chara: Any, num_costumes: int = 3) -> None:
    """SVで必要な専用フィールドを各コーディネートへ追加する。"""
    for i in range(num_costumes):
        chara["Coordinate"][i]["isSteamLimited"] = False
        chara["Coordinate"][i]["coverInfos"] = [
            {"use": False, "infoTable": {}} for _ in range(8)
        ]


def remove_sv_specific_fields(chara: Any, num_costumes: int = 3) -> None:
    """SV専用フィールドを各コーディネートから削除する。"""
    for i in range(num_costumes):
        if "isSteamLimited" in chara["Coordinate"][i]:
            del chara["Coordinate"][i]["isSteamLimited"]
        if "coverInfos" in chara["Coordinate"][i]:
            del chara["Coordinate"][i]["coverInfos"]


def add_ac_specific_accessory_fields(chara: Any, num_costumes: int = 4) -> None:
    """AC専用のアクセサリーフィールドを追加する。"""
    for i in range(num_costumes):
        for n in range(40):
            chara.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"] = -1
            chara.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"] = [
                True for _ in range(3)
            ]


def remove_ac_specific_accessory_fields(chara: Any, num_costumes: int = 3) -> None:
    """AC専用のアクセサリーフィールドを削除する。"""
    for i in range(num_costumes):
        for n in range(len(chara.Coordinate[i]["accessory"]["parts"])):
            if "hideCategoryClothes" in chara.Coordinate[i]["accessory"]["parts"][n]:
                del chara.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"]
            if "visibleTimings" in chara.Coordinate[i]["accessory"]["parts"][n]:
                del chara.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"]


def hc_to_sv(hc: HoneycomeCharaData) -> SummerVacationCharaData:
    """HCキャラクターをSVキャラクターへ変換する。"""
    assert isinstance(hc, HoneycomeCharaData)

    config = GAME_CONFIG["SV"]
    svc = init_chara_base(config["class"], hc, config["header"], config["product_no"])
    common_blocks = copy_common_blocks(svc, hc)
    setup_blockdata(svc, common_blocks, config["blocks"])

    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")
    svc.GameParameter_SV.data = create_default_sv_gameparameter(svc.image)
    svc.GameInfo_SV.data = {}

    add_sv_specific_fields(svc)
    transform_paint_scale_hc_to_sv(svc)
    svc["Parameter"]["personality"] = 0

    return svc


def sv_to_hc(svc: SummerVacationCharaData) -> HoneycomeCharaData:
    """SVキャラクターをHCキャラクターへ変換する。"""
    assert isinstance(svc, SummerVacationCharaData)

    config = GAME_CONFIG["HC"]
    hc = init_chara_base(
        config["class"],
        svc,
        config["header"],
        config["product_no"],
        face_image=svc.image,
    )
    common_blocks = copy_common_blocks(hc, svc)
    setup_blockdata(hc, common_blocks, config["blocks"])

    hc.GameParameter_HC = StubBlockData("GameParameter_HC", "0.0.0")
    hc.GameInfo_HC = StubBlockData("GameInfo_HC", "0.0.0")
    hc.GameParameter_HC.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_HC)
    hc.GameInfo_HC.data = copy.deepcopy(DEFAULT_GAMEINFO_HC)

    remove_sv_specific_fields(hc)
    transform_paint_scale_sv_to_hc(hc)
    hc["Parameter"]["personality"] = 0

    return hc


def sv_to_ac(svc: SummerVacationCharaData) -> AicomiCharaData:
    """SVキャラクターをACキャラクターへ変換する。"""
    assert isinstance(svc, SummerVacationCharaData)

    config = GAME_CONFIG["AC"]
    ac = init_chara_base(config["class"], svc, config["header"], config["product_no"])
    common_blocks = copy_common_blocks(ac, svc)
    setup_blockdata(ac, common_blocks, config["blocks"])

    ac.GameParameter_AC = StubBlockData("GameParameter_AC", "0.0.0")
    ac.GameInfo_AC = StubBlockData("GameInfo_AC", "0.0.0")
    ac.GameParameter_AC.data = copy.deepcopy(DEFAULT_GAMEPARAMETER_AC)
    ac.GameParameter_AC.data["imageData"] = None
    ac.GameInfo_AC.data = {"version": "0.0.0"}

    ac.Parameter.data["nickname"] = ""
    ac.Coordinate.data.append(copy.deepcopy(ac.Coordinate.data[-1]))
    swap_coordinates(ac, 0, 1)
    expand_accessories(ac, 20, 40, 4)
    add_ac_specific_accessory_fields(ac, 4)

    return ac


def ac_to_sv(ac: AicomiCharaData) -> SummerVacationCharaData:
    """ACキャラクターをSVキャラクターへ変換する。"""
    assert isinstance(ac, AicomiCharaData)

    config = GAME_CONFIG["SV"]
    svc = init_chara_base(config["class"], ac, config["header"], config["product_no"])
    common_blocks = copy_common_blocks(svc, ac)
    setup_blockdata(svc, common_blocks, config["blocks"])

    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")
    svc.GameParameter_SV.data = create_default_sv_gameparameter(None)
    svc.GameInfo_SV.data = {"version": "0.0.0"}

    swap_coordinates(svc, 0, 1)
    if len(svc.Coordinate.data) > 3:
        svc.Coordinate.data = svc.Coordinate.data[:3]

    shrink_accessories(svc, 40, 20, 3)
    remove_ac_specific_accessory_fields(svc, 3)
    if "nickname" in svc.Parameter.data:
        del svc.Parameter.data["nickname"]

    return svc


def _sync_block_order(chara: Any) -> None:
    """blockdata配列をシリアライズ順・元順の両方へ同期する。"""
    chara.serialized_lstinfo_order = chara.blockdata
    chara.original_lstinfo_order = chara.blockdata


def _ensure_blockdata_entry(chara: Any, block_name: str) -> None:
    """blockdata配列に指定ブロック名が無ければ追加する。"""
    if block_name not in chara.blockdata:
        chara.blockdata.append(block_name)


def _remove_block_entry(chara: Any, block_name: str) -> None:
    """blockdata配列から指定ブロック名をすべて削除する。"""
    while block_name in chara.blockdata:
        chara.blockdata.remove(block_name)


def normalize_scene_game_blocks(chara: Any) -> None:
    """シーン埋め込み仕様に合わせてGame系ブロック構成を正規化する。"""
    # シーン埋め込みキャラ向けに、接尾辞なし GameParameter/GameInfo のみを残す。
    for block_name in list(chara.blockdata):
        if block_name.startswith("GameParameter_") or block_name.startswith(
            "GameInfo_"
        ):
            if hasattr(chara, block_name):
                delattr(chara, block_name)
            _remove_block_entry(chara, block_name)

    for block_name in ("GameParameter", "GameInfo"):
        block = getattr(chara, block_name, None)
        if (
            block is None
            or not hasattr(block, "data")
            or not isinstance(block.data, dict)
        ):
            setattr(chara, block_name, StubBlockData(block_name, "0.0.0"))
            block = getattr(chara, block_name)
        block.data = {}
        _ensure_blockdata_entry(chara, block_name)

    _sync_block_order(chara)


def set_character_image(chara: Any, name: str = "", scene_title: str = "") -> None:
    """シーン用途の画像状態を適用し、Game系ブロックを正規化する。"""
    # シーン用途では card image は不要なので常に None。
    chara.image = None

    normalize_scene_game_blocks(chara)


def convert_character_to_target(
    chara: Any, target: Literal["HC", "SV", "AC"]
) -> tuple[Any, bool]:
    """キャラクターを指定形式へ変換し、実変換有無を返す。"""
    header = decode_header(chara)

    if target == "HC":
        if header == "【HCChara】":
            return chara, False
        if header in HONEYCOME_HEADERS:
            return sv_to_hc(hc_to_sv(chara)), True
        if header == "【SVChara】":
            return sv_to_hc(chara), True
        if header == "【ACChara】":
            return sv_to_hc(ac_to_sv(chara)), True

    if target == "SV":
        if header == "【SVChara】":
            return chara, False
        if header in HONEYCOME_HEADERS:
            return hc_to_sv(chara), True
        if header == "【ACChara】":
            return ac_to_sv(chara), True

    if target == "AC":
        if header == "【ACChara】":
            return chara, False
        if header in HONEYCOME_HEADERS:
            return sv_to_ac(hc_to_sv(chara)), True
        if header == "【SVChara】":
            return sv_to_ac(chara), True

    raise ValueError(f"Unsupported character header: {header}")


def count_character_headers(scene: HoneycomeSceneData) -> tuple[Counter[str], int]:
    """シーン内キャラクターのヘッダー内訳と総数を集計する。"""
    headers: Counter[str] = Counter()
    total = 0
    for _, obj in scene.walk(object_type=HoneycomeSceneData.CHARACTER):
        chara = obj.get("data", {}).get("character")
        if chara is None:
            continue
        headers[decode_header(chara)] += 1
        total += 1
    return headers, total


def unify_scene_characters(
    scene: HoneycomeSceneData, target: Literal["HC", "SV", "AC"]
) -> dict[str, Any]:
    """シーン内の全キャラクターを指定形式へ統一変換する。"""
    before_headers: Counter[str] = Counter()
    after_headers: Counter[str] = Counter()
    converted_count = 0
    failed: list[dict[str, str]] = []
    processed = 0

    for key, obj in scene.walk(object_type=HoneycomeSceneData.CHARACTER):
        data = obj.get("data", {})
        chara = data.get("character")
        if chara is None:
            continue

        processed += 1
        name = get_character_name(chara)
        old_header = decode_header(chara)
        before_headers[old_header] += 1

        try:
            converted_chara, changed = convert_character_to_target(chara, target)
            set_character_image(
                converted_chara, name=name, scene_title=scene.title or ""
            )
            data["character"] = converted_chara
            new_header = decode_header(converted_chara)
            after_headers[new_header] += 1
            if changed or old_header != new_header:
                converted_count += 1
        except Exception as e:
            failed.append(
                {
                    "key": str(key),
                    "name": name,
                    "header": old_header,
                    "error": str(e),
                }
            )
            after_headers[old_header] += 1

    return {
        "processed": processed,
        "converted": converted_count,
        "failed": failed,
        "before": before_headers,
        "after": after_headers,
    }


def render_header_metrics(title: str, header_counter: Counter[str]) -> None:
    """ヘッダーごとの件数メトリクスを画面に表示する。"""
    st.write(f"**{title}**")
    if not header_counter:
        st.write("-")
        return
    cols = st.columns(len(header_counter))
    for i, (header, count) in enumerate(sorted(header_counter.items())):
        cols[i].metric(header, count)


def main() -> None:
    """Streamlit画面を描画し、シーン内キャラクターの統一変換を実行する。"""
    page_title = get_text("title", "ja")
    st.set_page_config(page_title=page_title, page_icon=":arrows_counterclockwise:")

    with st.sidebar:
        lang = st.selectbox(
            "Language / 言語",
            options=["ja", "en"],
            format_func=lambda x: "日本語" if x == "ja" else "English",
            index=0,
        )

    st.title(get_text("title", lang))
    st.write(get_text("subtitle", lang))

    with st.expander(get_text("usage_title", lang)):
        st.markdown(get_text("usage_content", lang))

    uploaded_file = st.file_uploader(
        get_text("file_uploader", lang),
        type=["png"],
        help=get_text("file_uploader_help", lang),
    )

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            hs = HoneycomeSceneData.load(io.BytesIO(file_bytes))
            st.success(get_text("success_load", lang))

            headers_before, total_characters = count_character_headers(hs)
            st.subheader(get_text("stats_title", lang))
            render_header_metrics(get_text("headers_before", lang), headers_before)

            if total_characters == 0:
                st.info(get_text("no_characters", lang))
                st.stop()

            st.subheader(get_text("target_title", lang))
            target = st.radio(
                get_text("target_label", lang),
                options=["HC", "SV", "AC"],
                format_func=lambda x: get_text(
                    {"HC": "target_hc", "SV": "target_sv", "AC": "target_ac"}[x], lang
                ),
                horizontal=True,
            )

            if st.button(get_text("execute_button", lang), type="primary"):
                hs_converted = HoneycomeSceneData.load(io.BytesIO(file_bytes))
                result = unify_scene_characters(hs_converted, target)

                st.success(
                    get_text("success_convert", lang).format(
                        converted=result["converted"], total=result["processed"]
                    )
                )

                if result["failed"]:
                    st.warning(
                        get_text("warning_failed", lang).format(
                            count=len(result["failed"])
                        )
                    )
                    with st.expander(
                        get_text("failed_table_title", lang), expanded=False
                    ):
                        st.dataframe(result["failed"], width="stretch")

                output = io.BytesIO()
                hs_converted.save(output)
                output.seek(0)

                original_name = uploaded_file.name.rsplit(".", 1)[0]
                output_filename = (
                    f"{original_name}_characters_unified_{target.lower()}.png"
                )

                st.download_button(
                    label=get_text("download_button", lang),
                    data=output,
                    file_name=output_filename,
                    mime="image/png",
                )

        except Exception as e:
            st.error(get_text("error_load", lang))
            st.exception(e)
    else:
        st.info(get_text("info_upload", lang))


if __name__ == "__main__":
    main()
