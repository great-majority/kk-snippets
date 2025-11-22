import copy
import io

import streamlit as st
from kkloader import AicomiCharaData, HoneycomeCharaData, SummerVacationCharaData
from kkloader.funcs import get_png, load_length, load_type
from kkloader.KoikatuCharaData import BlockData

DEFAULT_ACCCESORY = {
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
            ValueError("unsupported input. type:{}".format(type(filelike)))

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


# ハニカムキャラ->サマすくキャラへの変換
def hc_to_sv(hc: HoneycomeCharaData) -> SummerVacationCharaData:
    assert isinstance(hc, HoneycomeCharaData)

    svc = SummerVacationCharaData()
    svc.image = hc.image
    svc.face_image = b""
    svc.product_no = 100
    svc.header = "【SVChara】".encode("utf-8")
    svc.version = "0.0.0".encode("utf-8")

    common_blocks = ["Custom", "Coordinate", "Parameter", "Status", "Graphic", "About"]
    sv_blocks = ["GameParameter_SV", "GameInfo_SV"]
    svc.blockdata = common_blocks + sv_blocks
    svc.serialized_lstinfo_order = svc.blockdata
    svc.original_lstinfo_order = svc.blockdata

    # まずは全部そのままコピーする
    for block in common_blocks:
        setattr(svc, block, getattr(hc, block))

    # SVにしかないデータを初期化する
    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")

    # この初期値はサマすく本体のコンバータに基づく
    svc.GameParameter_SV.data = {
        "imageData": svc.image,
        "job": 0,
        "sexualTarget": 0,
        "lvChastity": 0,
        "lvSociability": 0,
        "lvTalk": 0,
        "lvStudy": 0,
        "lvLiving": 0,
        "lvPhysical": 0,
        "lvDefeat": 0,
        "belongings": [
            0,
            0
        ],
        "isVirgin": True,
        "isAnalVirgin": True,
        "isMaleVirgin": True,
        "isMaleAnalVirgin": True,
        "individuality": {
            "answer": [
                -1,
                -1
            ]
            },
            "preferenceH": {
            "answer": [
                -1,
                -1
            ]
        }
    }
    svc.GameInfo_SV.data = {}

    # 3データ -> それぞれ私服, 役職服, 水着に対応する
    for i in range(3):
        svc["Coordinate"][i]["isSteamLimited"] = False  # 🤔

        # 着衣補正 `8` はトップス～靴それぞれを表す
        svc["Coordinate"][i]["coverInfos"] = [{"use": False, "infoTable": {}} for j in range(8)]

        # この`3`は化粧->ペイントの01~03に対応する
        for n in range(3):
            # ハニカムでのペイントサイズ[0, 1]はサマすくでの[0.25, 0.75]になる
            original_scale = hc["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3]
            svc["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = 0.5 * original_scale + 0.25

    # 性格を"普通"にする
    svc["Parameter"]["personality"] = 0

    return svc


# サマすくキャラ->ハニカムキャラへの変換
def sv_to_hc(svc: SummerVacationCharaData) -> HoneycomeCharaData:
    assert isinstance(svc, SummerVacationCharaData)

    hc = HoneycomeCharaData()
    hc.image = svc.image
    hc.face_image = svc.image  # サマすくに顔データはないため通常画像で代用している
    hc.product_no = 200
    hc.header = "【HCChara】".encode("utf-8")
    hc.version = "0.0.0".encode("utf-8")

    common_blocks = ["Custom", "Coordinate", "Parameter", "Status", "Graphic", "About"]
    hc_blocks = ["GameParameter_HC", "GameInfo_HC"]
    hc.blockdata = common_blocks + hc_blocks
    hc.serialized_lstinfo_order = hc.blockdata
    hc.original_lstinfo_order = hc.blockdata

    # まずは全部そのままコピーする
    for block in common_blocks:
        setattr(hc, block, getattr(svc, block))

    # HCにしかないデータを初期化する
    hc.GameParameter_HC = StubBlockData("GameParameter_HC", "0.0.0")
    hc.GameInfo_HC = StubBlockData("GameInfo_HC", "0.0.0")

    hc.GameParameter_HC.data = {
        "trait": 0,
        "mind": 0,
        "hAttribute": 10  # `10` -> "なし"
    }

    hc.GameInfo_HC.data = {
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
            ]
        ],
        "genericBrokenVoice": False,
        "genericDependencepVoice": False,
        "genericAnalVoice": False,
        "genericPainVoice": False,
        "genericFlag": False,
        "genericBefore": False,
        "inviteVoice": [
            False,
            False,
            False,
            False,
            False,
        ],
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

    # 3データ -> それぞれ私服, 役職服, 水着に対応する
    for i in range(3):
        if "isSteamLimited" in hc["Coordinate"][i]:
            del hc["Coordinate"][i]["isSteamLimited"]
        if "coverInfos" in hc["Coordinate"][i]:
            del hc["Coordinate"][i]["coverInfos"]

        # この`3`は化粧->ペイントの01~03に対応する
        for n in range(3):
            original_scale = svc["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3]
            hc["Coordinate"][i]["makeup"]["paintInfos"][n]["layout"][3] = 2 * original_scale - 0.5

    # 性格を"明るい"にする
    hc["Parameter"]["personality"] = 0

    return hc


def convert_svs_to_ac(svc: SummerVacationCharaData) -> AicomiCharaData:
    assert isinstance(svc, SummerVacationCharaData)

    ac = AicomiCharaData()

    ac.image = svc.image
    ac.face_image = b""
    ac.product_no = 100
    ac.header = "【ACChara】".encode("utf-8")
    ac.version = "0.0.0".encode("utf-8")

    common_blocks = ["Custom", "Coordinate", "Parameter", "Status", "Graphic", "About"]
    ac_blocks = ["GameParameter_AC", "GameInfo_AC"]
    ac.blockdata = common_blocks + ac_blocks
    ac.serialized_lstinfo_order = ac.blockdata
    ac.original_lstinfo_order = ac.blockdata

    # まずは全部そのままコピーする
    for block in common_blocks:
        setattr(ac, block, getattr(svc, block))

    # ACにしかないデータを初期化する
    ac.GameParameter_AC = StubBlockData("GameParameter_AC", "0.0.0")
    ac.GameInfo_AC = StubBlockData("GameInfo_AC", "0.0.0")

    ac.GameParameter_AC.data = DEFAULT_GAMEPARAMETER_AC
    # Noneにしてもいいかもしれないが、とりあえずSVSのをコピーする
    ac.GameParameter_AC.data["imageData"] = svc.GameParameter_SV.data["imageData"]

    ac.GameInfo_AC.data = {"version": "0.0.0"}

    # SVSとACで違う部分を修正する

    # アクセサリー表示フラグ(20->40対応)
    for _ in range(20):
        ac.Status.data["showAccessory"].append(True)

    # ニックネーム
    ac.Parameter.data["nickname"] = ""

    # 4番目のコスチューム(祭り衣装)を追加する
    # 公式通りに浴衣にしてもいいが、ここではとりあえず3番目のコピペにする
    ac.Coordinate.data.append(copy.deepcopy(ac.Coordinate.data[-1]))

    # 私服と役職服の順序を入れ替える これでサマすくの私服がそのままアイコミの私服になる
    casual_coordinate = copy.deepcopy(ac.Coordinate.data[0])
    workwear_coordinate = copy.deepcopy(ac.Coordinate.data[1])
    ac.Coordinate.data[0] = workwear_coordinate
    ac.Coordinate.data[1] = casual_coordinate

    # アクセサリーのパーツ数(20->40対応)
    for i in range(4):
        for _ in range(20):
            ac.Coordinate[i]["accessory"]["parts"].append(DEFAULT_ACCCESORY)

    # 新たに加わったアクセサリーの設定(どのタイミングで非表示にするか)
    for i in range(4):
        for n in range(40):
            ac.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"] = -1
            ac.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"] = [
                True for _ in range(3)
            ]

    return ac


def convert_ac_to_svs(ac: AicomiCharaData) -> SummerVacationCharaData:
    assert isinstance(ac, AicomiCharaData)

    svc = SummerVacationCharaData()
    svc.image = ac.image
    svc.face_image = b""
    svc.product_no = 100
    svc.header = "【SVChara】".encode("utf-8")
    svc.version = "0.0.0".encode("utf-8")

    common_blocks = ["Custom", "Coordinate", "Parameter", "Status", "Graphic", "About"]
    sv_blocks = ["GameParameter_SV", "GameInfo_SV"]
    svc.blockdata = common_blocks + sv_blocks
    svc.serialized_lstinfo_order = svc.blockdata
    svc.original_lstinfo_order = svc.blockdata

    # まずは全部そのままコピーする
    for block in common_blocks:
        setattr(svc, block, getattr(ac, block))

    # SVにしかないデータを初期化する
    svc.GameParameter_SV = StubBlockData("GameParameter_SV", "0.0.0")
    svc.GameInfo_SV = StubBlockData("GameInfo_SV", "0.0.0")

    # この初期値はサマすく本体のコンバータに基づく
    svc.GameParameter_SV.data = {
        "imageData": ac.GameParameter_AC.data["imageData"],
        "job": 0,
        "sexualTarget": 0,
        "lvChastity": 0,
        "lvSociability": 0,
        "lvTalk": 0,
        "lvStudy": 0,
        "lvLiving": 0,
        "lvPhysical": 0,
        "lvDefeat": 0,
        "belongings": [
            0,
            0
        ],
        "isVirgin": True,
        "isAnalVirgin": True,
        "isMaleVirgin": True,
        "isMaleAnalVirgin": True,
        "individuality": {
            "answer": [
                -1,
                -1
            ]
            },
            "preferenceH": {
            "answer": [
                -1,
                -1
            ]
        }
    }
    svc.GameInfo_SV.data = {"version": "0.0.0"}

    # ACとSVSで違う部分を修正する

    # 私服と役職服の順序を元に戻す（ACの私服→SVSの役職服、ACの制服→SVSの私服）
    casual_coordinate = copy.deepcopy(svc.Coordinate.data[0])
    workwear_coordinate = copy.deepcopy(svc.Coordinate.data[1])
    svc.Coordinate.data[0] = workwear_coordinate
    svc.Coordinate.data[1] = casual_coordinate

    # 4番目のコスチューム（祭り衣装）を削除（SVSは3つのコスチュームのみ）
    if len(svc.Coordinate.data) > 3:
        svc.Coordinate.data = svc.Coordinate.data[:3]

    # アクセサリーのパーツ数(40->20対応)
    for i in range(3):
        if len(svc.Coordinate[i]["accessory"]["parts"]) > 20:
            svc.Coordinate[i]["accessory"]["parts"] = svc.Coordinate[i]["accessory"]["parts"][:20]

    # ACにしかないアクセサリーのフィールドを削除
    for i in range(3):
        for n in range(len(svc.Coordinate[i]["accessory"]["parts"])):
            if "hideCategoryClothes" in svc.Coordinate[i]["accessory"]["parts"][n]:
                del svc.Coordinate[i]["accessory"]["parts"][n]["hideCategoryClothes"]
            if "visibleTimings" in svc.Coordinate[i]["accessory"]["parts"][n]:
                del svc.Coordinate[i]["accessory"]["parts"][n]["visibleTimings"]

    # アクセサリー表示フラグ(40->20対応)
    if len(svc.Status.data["showAccessory"]) > 20:
        svc.Status.data["showAccessory"] = svc.Status.data["showAccessory"][:20]

    # ニックネーム（ACにしかないフィールド）を削除
    if "nickname" in svc.Parameter.data:
        del svc.Parameter.data["nickname"]

    return svc


title = "サマすく/ハニカム/アイコミキャラクターコンバータ"
st.set_page_config(page_title=title)
st.title(title)

description = """
サマすく/ハニカム/アイコミでキャラクターデータを相互変換するツールです。キャラデータ読み込み後、
- ハニカムのキャラデータはサマすくへ
- サマすくのキャラデータはハニカムとアイコミへ
- アイコミのキャラデータはサマすくへ

変換が行われます。

**⚠️注意事項**: バグなどあるかもしれませんので、変換前のデータのバックアップはとっておきましょう!
"""
st.markdown(description)

with st.expander("さらに詳しい説明を見る"):
    description = """
    **サマすく⇔ハニカム変換:**
    - 「キャラ設定」のパラメータは全てリセットされます。例えば、"キャラ特性"や"H属性"などの設定情報はすべてキャラメイクのデフォルトになります。
    - サマすくの「ゲーム内表示」画像(キャラ一覧などの画像)はキャラカード画像で代用されます。そのため引き伸ばされたような表示になります。
        - 気になる場合はキャラメイクから上書き保存してください。
    - サマすくにしか無いパーツ(髪型、服装など)はサマすくでしか読み込めません。

    **サマすく⇔アイコミ変換:**

    **サマすく→アイコミ変換時のコスチューム対応:**
    - 私服 → 私服
    - 役職服 → 制服
    - 水着 → 水着
    - (なし) → 祭り衣装（3番目のコスチュームのコピー）

    **アイコミ→サマすく変換時のコスチューム対応:**
    - 私服 → 役職服
    - 制服 → 私服
    - 水着 → 水着
    - 祭り衣装 → (削除)

    - 内部のサムネイル画像の縮尺がサマすくとアイコミで異なるため、ゲームに登場させる前にキャラメイクでサムネイル更新&上書き保存しておくことを推奨します。
    """
    st.markdown(description)

st.divider()

file = st.file_uploader("サマすく/ハニカム/アイコミのキャラ画像を選択")
if file is not None:

    try:
        kch = KoikatuCharaHeader.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        # st.write(e)
        st.stop()

    st.success("正常にデータを読み込めました。", icon="✅")

    header = kch.header.decode("utf-8")

    if header not in ["【HCChara】", "【SVChara】", "【ACChara】"]:
        st.error(f"このヘッダのファイルには対応していません: {header}", icon="🚨")
        st.stop()

    if header == "【HCChara】":
        st.write("このファイルは **ハニカム** のキャラデータです。")
        hc = HoneycomeCharaData.load(file.getvalue())
        name = " ".join([hc['Parameter']['lastname'], hc['Parameter']['firstname']])
        svc = hc_to_sv(hc)
        st.download_button("サマすくのキャラとしてダウンロード", bytes(svc), file_name=f"sv_converted_{name}.png")

    elif header == "【SVChara】":
        st.write("このファイルは **サマすく** のキャラデータです。")
        svc = SummerVacationCharaData.load(file.getvalue())
        name = " ".join([svc['Parameter']['lastname'], svc['Parameter']['firstname']])
        hc = sv_to_hc(svc)
        ac = convert_svs_to_ac(svc)
        st.download_button("ハニカムのキャラとしてダウンロード", bytes(hc), file_name=f"hc_converted_{name}.png")
        st.download_button("アイコミのキャラとしてダウンロード", bytes(ac), file_name=f"ac_converted_{name}.png")

    elif header == "【ACChara】":
        st.write("このファイルは **アイコミ** のキャラデータです。")
        ac = AicomiCharaData.load(file.getvalue())
        name = " ".join([ac["Parameter"]["lastname"], ac["Parameter"]["firstname"]])
        svc = convert_ac_to_svs(ac)
        st.download_button(
            "サマすくのキャラとしてダウンロード",
            bytes(svc),
            file_name=f"sv_converted_{name}.png",
        )
