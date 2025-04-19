import io

import streamlit as st
from kkloader import SummerVacationCharaData
from kkloader import HoneycomeCharaData
from kkloader.KoikatuCharaData import BlockData
from kkloader.funcs import get_png, load_length, load_type


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


title = "サマすく/ハニカムキャラクターコンバータ"
st.set_page_config(page_title=title)
st.title(title)

description = """
サマすくとハニカムでキャラクターデータを相互変換するツールです。キャラデータ読み込み後、
- ハニカムのキャラデータはサマすくへ
- サマすくのキャラデータはハニカムへ

変換が行われます。

**⚠️注意事項**: バグなどあるかもしれませんので、変換前のデータのバックアップはとっておきましょう!
"""
st.markdown(description)

with st.expander("さらに詳しい説明を見る"):
    description = """
    - 「キャラ設定」のパラメータは全てリセットされます。例えば、"キャラ特性"や"H属性"などの設定情報はすべてキャラメイクのデフォルトになります。
    - サマすくの「ゲーム内表示」画像(キャラ一覧などの画像)はキャラカード画像で代用されます。そのため引き伸ばされたような表示になります。
        - 気になる場合はキャラメイクから上書き保存してください。
    - サマすくにしか無いパーツ(髪型、服装など)はサマすくでしか読み込めません。
    """
    st.markdown(description)

st.divider()

file = st.file_uploader("サマすく/ハニカムのキャラ画像を選択")
if file is not None:

    try:
        kch = KoikatuCharaHeader.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        # st.write(e)
        st.stop()

    st.success("正常にデータを読み込めました。", icon="✅")

    header = kch.header.decode("utf-8")

    if header not in ["【HCChara】", "【SVChara】"]:
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
        st.download_button("ハニカムのキャラとしてダウンロード", bytes(hc), file_name=f"hc_converted_{name}.png")
