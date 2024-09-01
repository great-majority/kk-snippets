import struct
import io
import math
import pandas as pd
import streamlit as st
from msgpack import packb, unpackb

from kkloader import SummerVacationCharaData as svcd


############################################
# データ読み込み用関数(funcs.pyからコピペ)
############################################
def load_length(data_stream, struct_type):
    length = struct.unpack(struct_type, data_stream.read(struct.calcsize(struct_type)))[0]
    return data_stream.read(length)


def msg_unpack(data):
    return unpackb(data, raw=False, strict_map_key=False)


def msg_pack(data):
    serialized = packb(data, use_single_float=True, use_bin_type=True)
    return serialized, len(serialized)


############################################
# サマすくセーブデータのシリアライザー
############################################
class SVSSaveData:
    def __init__(self) -> None:
        pass

    @classmethod
    def _unsigned_int(cls, data_stream):
        return struct.unpack("<I", data_stream.read(4))[0]

    @classmethod
    def _unsigned_int64(cls, data_stream):
        return struct.unpack("<Q", data_stream.read(8))[0]

    @classmethod
    def load(cls, filelike):
        svs = cls()

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

        # セーブデータのメタ情報
        svs.meta = msg_unpack(load_length(data_stream, "<I"))
        # データ全長 - 12 が入っている
        svs.data_length = cls._unsigned_int64(data_stream)
        # 登録しているキャラの人数
        svs.chara_num = cls._unsigned_int(data_stream)

        svs.chara_details = []
        svs.charas = []
        # キャラ一人づつのデータ
        for i in range(svs.chara_num):
            # データの長さ パラメータの長さ(とその長さを表す4バイト) + キャラデータの長さ
            cls._unsigned_int(data_stream)
            # キャラ同士の関係とかのデータ
            svs.chara_details.append(msg_unpack(load_length(data_stream, "<I")))
            # キャラデータ
            svs.charas.append(svcd.load(data_stream))

        # `1` だったが詳細不明
        svs.unknown = cls._unsigned_int(data_stream)
        # プレイヤーのキャラデータが入っているオフセット位置
        svs.player_offset = cls._unsigned_int64(data_stream)

        svs.names = {x["charasGameParam"]["Index"]: x["charasGameParam"]["onesPropertys"][0]["name"] for x in svs.chara_details}
        svs.index_to_array = {x["charasGameParam"]["Index"]: i for i, x in enumerate(svs.chara_details)}

        return svs

    # セーブデータのシリアライズ
    def __bytes__(self):
        ipack = struct.Struct("<I").pack
        qpack = struct.Struct("<Q").pack

        meta_b, meta_i = msg_pack(self.meta)
        meta_i_b = ipack(meta_i)

        chara_byte, player_offset = self._bytes_charas()
        chara_l_b = ipack(len(self.charas))

        # セーブデータの先頭からプレイヤーキャラ部分までのオフセットを計算したい
        # メタ部分の長さ + メタ部分の長さの数字(4byte) + データ全長の数字(8byte) + キャラ数の数字(4byte)
        player_offset += len(meta_b) + 4 + 8 + 4 
        player_offset_b = qpack(player_offset)

        data_length = len(meta_b) + len(chara_byte) + 4 + 8 + 4
        data_length_b = qpack(data_length)

        unknown_b = ipack(self.unknown)

        data_chunks = [
            meta_i_b,
            meta_b,
            data_length_b,
            chara_l_b,
            chara_byte,
            unknown_b,
            player_offset_b,
        ]

        return b"".join(data_chunks)

    # キャラデータ部分のbytesを作る
    def _bytes_charas(self):
        ipack = struct.Struct("<I")

        player_offset = 0
        after_player = False

        chara_bytes = []
        for chara, chara_detail in zip(self.charas, self.chara_details):
            chara_detail_b, chara_detail_i = msg_pack(chara_detail) 
            chara_detail_i_b = ipack.pack(chara_detail_i)
            chara_b = bytes(chara)

            # キャラクターデータの長さを整数値に変換
            chara_length = sum(map(lambda x: len(x), [chara_detail_i_b, chara_detail_b, chara_b]))
            chara_length_b = ipack.pack(chara_length)

            chara_byte = b"".join([
                chara_length_b,
                chara_detail_i_b,
                chara_detail_b,
                chara_b
            ])

            if chara_detail["charasGameParam"]["isPC"]:
                after_player = True

            # 今までプレイヤーキャラがでてなければ、オフセットを加算していく
            if not after_player:
                player_offset += len(chara_byte)

            chara_bytes.append(chara_byte)

        return b"".join(chara_bytes), player_offset

    def save(self, filename):
        with open(filename, "wb") as f:
            f.write(bytes(self))

    # 二者間の交流のログを隣接行列として取得する
    def generate_interract_matrix(self, command: int = 0, active: bool = True, decision: str = "yes"):

        names = {x["charasGameParam"]["Index"]: x["charasGameParam"]["onesPropertys"][0]["name"] for x in self.chara_details}
        interract = "activeCommand" if active else "passiveCommand"

        assert interract in ["activeCommand", "passiveCommand"]
        assert decision in ["yes", "no"]

        rows = {}
        for c in self.chara_details:

            from_index = c["charasGameParam"]["Index"]
            row = {}
            table = c["charasGameParam"]["memory"][interract]["DeadTable"]

            for d in self.chara_details:

                to_index = d["charasGameParam"]["Index"]

                if to_index in table and command in table[to_index]["save"]["infos"]:
                    value = table[to_index]["save"]["infos"][command]["countInfo"][decision]
                else:
                    value = None

                row[f"{to_index}:{names[to_index]}"] = value

            rows[f"{from_index}:{names[from_index]}"] = row

        return pd.DataFrame.from_dict(rows).T

    # `generate_interract_matrix` から得た行列を編集したものを反映させる関数
    def apply_interract_matrix(self, matrix: pd.DataFrame, command: int = 0, decision: str = "yes"):
        index_to_array = {x["charasGameParam"]["Index"]: i for i, x in enumerate(self.chara_details)}

        decisions = ["yes", "no"]
        assert decision in decisions
        decisions.remove(decision)
        flipped_decision = decisions[0]

        def set_value(from_idx: int, to_idx: int, interract: str, value: int):
            # これまでに交流がない場合、新たに辞書のkeyを初期化する
            if to_idx not in self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"]:
                self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"][to_idx] = {
                    "save": {"infos": {}}
                }

            # これまでに指定した交流をしていない場合、交流のkeyを初期化する
            if command not in self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"][to_idx]["save"]["infos"]:
                self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"][to_idx]["save"]["infos"][command] = {
                    "countInfo": {
                        "command": command,
                        "count": 0,
                        "yes": 0,
                        "no": 0,
                        "ambiguous": 0,
                    }
                }

            stats = self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"][to_idx]["save"]["infos"][command]["countInfo"]
            stats[decision] = value
            stats["count"] = stats[decision] + stats[flipped_decision] + stats["ambiguous"]

            for k, v in stats.items():
                stats[k] = int(v)

            self.chara_details[index_to_array[from_idx]]["charasGameParam"]["memory"][interract]["DeadTable"][to_idx]["save"]["infos"][command]["countInfo"] = stats

        for i, row in matrix.iterrows():

            row_idx = int(i.split(":")[0])

            for j, col in row.items():

                col_idx = int(j.split(":")[0])
                col = int(col) if isinstance(col, str) else col

                if col is None or math.isnan(col) or row_idx == col_idx:
                    continue

                # from -> to へのactiveな交流
                set_value(row_idx, col_idx, "activeCommand", col)
                # to -> from へのpassiveな交流
                set_value(col_idx, row_idx, "passiveCommand", col)

    def generate_correlation_matrix(self):

        rows = {}
        for c in self.chara_details:
            from_index = c["charasGameParam"]["Index"]
            table = c["charasGameParam"]["correlationTable"]
            row = {}

            for k, v in table.items():
                row[f"{k}:{names[k]}"] = v

            rows[f"{from_index}:{names[from_index]}"] = row

        return pd.DataFrame.from_dict(rows).T

    def update_correlation_matrix(self):
        for i, c in enumerate(self.chara_details):
            from_index = c["charasGameParam"]["Index"]
            for d in self.chara_details:
                to_index = d["charasGameParam"]["Index"]
                if from_index == to_index:
                    continue

                table = c["charasGameParam"]["memory"]["passiveCommand"]["DeadTable"]
                if to_index not in table:
                    continue

                commands = table[to_index]["save"]["infos"]
                counts = map(lambda v: v["countInfo"]["count"], commands.values())
                counts = sum(counts)

                self.chara_details[i]["charasGameParam"]["correlationTable"][to_index] = counts

############################################
# Streamlitのロジック部分
############################################
title = "サマすくキャラ特性エディター"
st.set_page_config(page_title=title, layout="wide")
st.title(title)
st.divider()

description = """
[サマバケ！すくらんぶる](https://www.illgames.jp/product/svs/)のセーブデータを編集するツールです。
"""
st.markdown(description)

file = st.file_uploader("サマすくのセーブデータを選択")
if file is not None:

    try:
        svs = SVSSaveData.load(file.getvalue())
    except Exception as e:
        st.error("ファイルの読み込みに失敗しました。未対応のファイルです。", icon="🚨")
        st.stop()
    st.success("正常にデータを読み込めました。", icon="✅")

    download = st.empty()

    categorical_columns = [
        "job",               # 仕事
        "sexualTarget",      # 性愛対象
        "lvChastity",        # 貞操観念
        "lvSociability",     # 社交性
        "lvTalk",            # 話術
        "lvStudy",           # 学力
        "lvLiving",          # 生活
        "lvPhysical",        # 体力
        "lvDefeat",          # 貶し方
    ]

    categorical_labels = {
        "job":           "仕事",
        "sexualTarget":  "性愛対象",
        "lvChastity":    "貞操観念",
        "lvSociability": "社交性",
        "lvTalk":        "話術",
        "lvStudy":       "学力",
        "lvLiving":      "生活",
        "lvPhysical":    "体力",
        "lvDefeat":      "貶し方",
    }

    categorical_label_maps = {
        "job": {
            0: "0:なし",
            1: "1:ビーチ監視員",
            2: "2:カフェ店員",
            3: "3:巫女・男巫",
        },
        "sexualTarget": {
            0: "0:異性のみ",
            1: "1:異性寄り",
            2: "2:両方",
            3: "3:同性寄り",
            4: "4:同性のみ",
        },
        "lvChastity": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvSociability": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvTalk": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvStudy": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvLiving": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvPhysical": {
            0: "0:低い",
            1: "1:低め",
            2: "2:普通",
            3: "3:高め",
            4: "4:高い",
        },
        "lvDefeat": {
            0: "0:叫喚",
            1: "1:皮肉",
            2: "2:論破",
        },
    }

    trait_label_maps = {
        "individuality": {
            -1: "-1:なし",
            0: "0:チョロイ",
            1: "1:熱血友情",
            2: "2:男性苦手",
            3: "3:女性苦手",
            4: "4:チャーム",
            5: "5:侠気",
            6: "6:ミーハー",
            7: "7:素直",
            8: "8:前向き",
            9: "9:照れ屋",
            10: "10:ヤキモチ",
            11: "11:豆腐精神",
            12: "12:スケベ",
            13: "13:真面目",
            14: "14:平常心",
            15: "15:神経質",
            16: "16:直情的",
            17: "17:ぽややん",
            18: "18:短気",
            19: "19:肉食系",
            20: "20:草食系",
            21: "21:世話焼き",
            22: "22:まとめ役",
            23: "23:筋肉愛",
            24: "24:お喋り",
            25: "25:ハラペコ",
            26: "26:勤勉",
            27: "27:恋愛脳",
            28: "28:一方的",
            29: "29:一途",
            30: "30:優柔不断",
            31: "31:腹黒",
            32: "32:世渡り上手",
            33: "33:勤労",
            34: "34:奔放",
            35: "35:M気質",
            36: "36:心の闇",
            37: "37:鈍感",
            38: "38:節穴",
            39: "39:強運",
        },
        "preferenceH": {
            -1: "-1:なし",
            0: "0:受け",
            1: "1:攻め",
            2: "2:愛撫好き",
            3: "3:奉仕好き",
            4: "4:口上手",
            5: "5:アナル好き",
            6: "6:対面好き",
            7: "7:背面好き",
            8: "8:中出し好き",
            9: "9:ぶっかけ好き",
            10: "10:口内射精好き",
        },
    }

    value_columns = list(categorical_labels.values()) + ["個性1", "個性2", "H特性1", "H特性2"]

    rows = []
    for i, c in enumerate(svs.charas):
        row = {"名前": f"{i}:{c["Parameter"]['lastname']} {c["Parameter"]['firstname']}"}
        row.update({k: c["GameParameter_SV"][k] for k in categorical_columns})
        row["individuality"] = c["GameParameter_SV"]["individuality"]["answer"] # 特性 -> 個性
        row["preferenceH"] = c["GameParameter_SV"]["preferenceH"]["answer"]     # H特性
        rows.append(row)

    df_params = pd.DataFrame.from_dict(rows)

    # ここからカテゴリカル変数の設定
    # 0 -> "0:なし" とかにする置換
    for m in categorical_label_maps:
        df_params[m] = df_params[m].replace(categorical_label_maps[m])

    # カラム名を日本語にする
    df_params = df_params.rename(columns=categorical_labels)

    # streamlitでのUI装飾の設定
    categorical_column_configs = {}
    for k, v in categorical_label_maps.items():
        categorical_column_configs[categorical_labels[k]] = st.column_config.SelectboxColumn(
            categorical_labels[k],
            options=[w for w in sorted(v.values(), key=lambda x: int(x.split(":")[0]))],
            required=True
        )

    # ここから特性部分の設定
    # 特性は埋まってないこともあるのでNaNになる。その場合は-1として扱う。
    df_params[["個性1", "個性2"]] = pd.DataFrame(df_params["individuality"].apply(lambda x: (x + [-1] * 2)[:2]).to_list(), index=df_params.index)
    df_params[["H特性1", "H特性2"]] = pd.DataFrame(df_params["preferenceH"].apply(lambda x: (x + [-1] * 2)[:2]).to_list(), index=df_params.index)
    df_params.drop(["individuality", "preferenceH"], inplace=True, axis=1)

    # 0 -> "0:チョロイ" とかにする置換
    for m in ["個性1", "個性2", "H特性1", "H特性2"]:
        if "個性" in m:
            df_params[m] = df_params[m].replace(trait_label_maps["individuality"])
        else:
            df_params[m] = df_params[m].replace(trait_label_maps["preferenceH"])

    # streamlitでのUI装飾の設定
    trait_column_configs = {}
    for m in ["個性1", "個性2", "H特性1", "H特性2"]:
        if "個性" in m:
            trait_column_configs[m] = st.column_config.SelectboxColumn(
                m,
                options=[w for w in sorted(trait_label_maps["individuality"].values(), key=lambda x: int(x.split(":")[0]))],
                required=True,
            )
        else:
            trait_column_configs[m] = st.column_config.SelectboxColumn(
                m,
                options=[w for w in sorted(trait_label_maps["preferenceH"].values(), key=lambda x: int(x.split(":")[0]))],
                required=True,
            )

    column_configs = categorical_column_configs | trait_column_configs
    df_modified = st.data_editor(df_params, hide_index=True, column_config=column_configs)

    # 変更の反映
    df_modified[value_columns] = df_modified[value_columns].apply(lambda col: col.map(lambda x: int(x.split(":")[0])))

    for _, row in df_modified.iterrows():
        i, name = row["名前"].split(":")
        for k, v in categorical_labels.items():
            svs.charas[int(i)]["GameParameter_SV"][k] = int(row[v])

        svs.charas[int(i)]["GameParameter_SV"]["individuality"]["answer"] = list(set([x for x in row[["個性1", "個性2"]] if x != -1]))
        svs.charas[int(i)]["GameParameter_SV"]["preferenceH"]["answer"] = list(set([x for x in row[["H特性1", "H特性2"]] if x != -1]))

    download.download_button("改変後のセーブデータをダウンロード", bytes(svs), "modified.dat")
