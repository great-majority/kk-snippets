import io
import copy

import streamlit as st
from kkloader.EmocreCharaData import EmocreCharaData  # noqa
from kkloader.KoikatuCharaData import Coordinate, KoikatuCharaData  # noqa

title = "エモクリ→コイカツキャラクター変換ツール"
st.set_page_config(page_title=title)
st.title(title)

st.markdown("""エモーションクリエイターズで作成されたキャラクターを無印コイカツで読めるように変換するツールです。""")

st.divider()

file = st.file_uploader("エモーション・クリエイターズのキャラクター画像を選択")
if file is not None:

    try:
        ec = EmocreCharaData.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        st.stop()

    st.write("ヘッダ:", ec.header.decode('utf-8'))
    st.write("キャラクター名:", ec['Parameter']['fullname'])
    st.image(io.BytesIO(ec.image), caption="カード画像")

    kk = KoikatuCharaData()

    kk.image = ec.image
    kk.face_image = ec.image
    kk.product_no = 100
    kk.header = "【KoiKatuChara】".encode("utf-8")
    kk.version = "0.0.0".encode("ascii")
    kk.blockdata = copy.deepcopy(ec.blockdata)

    kk.Custom = copy.deepcopy(ec.Custom)
    kk.Coordinate = Coordinate(data=None, version="0.0.0")
    kk.Parameter = copy.deepcopy(ec.Parameter)
    kk.Status = copy.deepcopy(ec.Status)
    
    if "KKEx" in ec.blockdata:
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

    ec.Coordinate["clothes"]["hideBraOpt"] = [False, False]
    ec.Coordinate["clothes"]["hideShortsOpt"] = [False, False]
    for i, p in enumerate(ec.Coordinate["clothes"]["parts"]):
        a = {
            "emblemeId": p["emblemeId"][0],
            "emblemeId2": p["emblemeId"][1],
        }
        ec.Coordinate["clothes"]["parts"][i].update(a)
    ec.Coordinate["clothes"]["parts"].append(ec.Coordinate["clothes"]["parts"][-1])
    for i, a in enumerate(ec.Coordinate["accessory"]["parts"]):
        del ec.Coordinate["accessory"]["parts"][i]["hideTiming"]
    makeup = copy.deepcopy(ec.Custom["face"]["baseMakeup"])
    kk.Coordinate.data = [
        {
            "clothes": ec.Coordinate["clothes"],
            "accessory": ec.Coordinate["accessory"],
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

    st.success("正常にデータを変換しました。", icon="✅")
    st.download_button("データをダウンロード", bytes(kk), file_name="converted.png")
