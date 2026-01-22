import io
import struct

import networkx as nx
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from kkloader import SummerVacationCharaData as svcd
from msgpack import packb, unpackb
from pyvis.network import Network

# ========================================
# i18n対応: 多言語辞書
# ========================================

TRANSLATIONS = {
    "ja": {
        "title": "サマすく行動ログビューア",
        "description": "[サマバケ！すくらんぶる](https://www.illgames.jp/product/svs/)のセーブデータに残っている行動ログを表示するツールです。",
        "expander_title": "表示についての詳しい説明はこちらをクリック",
        "expander_content": """
行列は行のキャラ→列のキャラ向けで行動があったことを示しています。例えば、
|           | 青山 祐樹 | 天宮 心音 |
| --------- | --------- | --------- |
| パル      | 0         | 1         |
| 川澄 結衣 | 0         | 0         |

のような結果が得られた場合は「パル」が「天宮 心音」に行動をとったということになります。
""",
        "file_uploader": "サマすくのセーブデータを選択",
        "error_load": "ファイルの読み込みに失敗しました。未対応のファイルです。",
        "success_load": "正常にデータを読み込めました。",
        "single_chara_warning": "このデータにはキャラクターが一人しか登録されていないようです。",
        "tab_sexual_graph": "性的関係グラフ",
        "tab_sexual_log": "性的関係ログ",
        "tab_emotion_graph": "感情グラフ",
        "tab_emotion": "感情値",
        "tab_command": "コマンドログ",
        "select_command": "表示するコマンドを選択:",
        "select_sexual_action": "表示する行動を選択:",
        "select_graph_action": "グラフを表示する行動を選択:",
        "select_emotion": "表示する感情を選択:",
        "select_emotion_graph": "グラフを表示する感情を選択:",
        "graph_help": "グラフが見えない場合は、表示位置がずれている可能性があります。その場合は右下の - + の上のボタンを押してみてください。",
        "emotion_graph_help": "このグラフでは`0`から`30`まである感情値を4段階で表しています。値が大きいほど線は太くなります。",
        "none_caption": "`None` は一度もその行動が行われなかったことを表し、`0` は行動が行われたものの違った返答となったことを表します。",
        "action_success": "行動成功",
        "action_fail": "行動失敗",
        "action_ambiguous": "あいまい返答",
    },
    "en": {
        "title": "Summer Vacation Action Log Viewer",
        "description": "A tool to display action logs saved in [Summer Vacation Scramble](https://www.illgames.jp/product/svs/) save data.",
        "expander_title": "Click here for detailed explanation",
        "expander_content": """
The matrix shows actions from row character → column character. For example,
|           | Aoyama Yuki | Amamiya Kokone |
| --------- | ----------- | -------------- |
| Pal       | 0           | 1              |
| Kawasumi Yui | 0        | 0              |

This result indicates that "Pal" took action toward "Amamiya Kokone".
""",
        "file_uploader": "Select Summer Vacation save data",
        "error_load": "Failed to load file. Unsupported file format.",
        "success_load": "Data loaded successfully.",
        "single_chara_warning": "This data only has one character registered.",
        "tab_sexual_graph": "Sexual Relationship Graph",
        "tab_sexual_log": "Sexual Relationship Log",
        "tab_emotion_graph": "Emotion Graph",
        "tab_emotion": "Emotion Values",
        "tab_command": "Command Log",
        "select_command": "Select command to display:",
        "select_sexual_action": "Select action to display:",
        "select_graph_action": "Select action to display in graph:",
        "select_emotion": "Select emotion to display:",
        "select_emotion_graph": "Select emotion to display in graph:",
        "graph_help": "If the graph is not visible, the display position may be offset. Try clicking the button above the - + in the lower right.",
        "emotion_graph_help": "This graph represents emotion values from 0 to 30 in 4 levels. Thicker lines indicate higher values.",
        "none_caption": "`None` indicates the action was never performed, `0` indicates the action was performed but received a different response.",
        "action_success": "Action Success",
        "action_fail": "Action Failed",
        "action_ambiguous": "Ambiguous Response",
    },
}


def get_text(key, lang="ja"):
    """指定した言語のテキストを取得"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["ja"]).get(key, key)


############################################
# データ読み込み用関数(funcs.pyからコピペ)
############################################
def load_length(data_stream, struct_type):
    length = struct.unpack(struct_type, data_stream.read(struct.calcsize(struct_type)))[
        0
    ]
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

        svs.names = {}
        for c, d in zip(svs.charas, svs.chara_details):
            svs.names[d["charasGameParam"]["Index"]] = (
                f"{c['Parameter']['lastname']} {c['Parameter']['firstname']}"
            )

        svs.index_to_array = {
            x["charasGameParam"]["Index"]: i for i, x in enumerate(svs.chara_details)
        }

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
            chara_length = sum(
                map(lambda x: len(x), [chara_detail_i_b, chara_detail_b, chara_b])
            )
            chara_length_b = ipack.pack(chara_length)

            chara_byte = b"".join(
                [chara_length_b, chara_detail_i_b, chara_detail_b, chara_b]
            )

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
    def generate_memory_matrix(
        self, command: int = 0, active: bool = True, decision: str = "yes"
    ):
        interract = "activeCommand" if active else "passiveCommand"

        assert interract in ["activeCommand", "passiveCommand"]
        assert decision in ["yes", "no", "ambiguous"]

        rows = {}
        for c in self.chara_details:
            from_index = c["charasGameParam"]["Index"]
            row = {}
            table = c["charasGameParam"]["memory"][interract]["DeadTable"]

            for d in self.chara_details:
                to_index = d["charasGameParam"]["Index"]

                if to_index in table and command in table[to_index]["save"]["infos"]:
                    value = table[to_index]["save"]["infos"][command]["countInfo"][
                        decision
                    ]
                else:
                    value = None

                row[f"{to_index}:{self.names[to_index]}"] = value

            rows[f"{from_index}:{self.names[from_index]}"] = row

        df = pd.DataFrame.from_dict(rows).T
        sorted_columns = sorted(df.columns, key=lambda x: int(x.split(":")[0]))
        df = df[sorted_columns]
        sorted_index = sorted(df.index, key=lambda x: int(x.split(":")[0]))
        df = df.loc[sorted_index]

        return df

    # 二者間の性的な関係のログの隣接行列
    def generate_sexual_memory_matrix(self, command):
        rows = {}
        for c in self.chara_details:
            from_index = c["charasGameParam"]["Index"]
            row = {}
            table = c["charasGameParam"]["memory"]["pairTable"]

            for d in self.chara_details:
                to_index = d["charasGameParam"]["Index"]
                if from_index == to_index:
                    continue
                value = table[to_index]["saveInfo"][command]
                row[f"{to_index}:{self.names[to_index]}"] = value

            rows[f"{from_index}:{self.names[from_index]}"] = row

        df = pd.DataFrame.from_dict(rows).T
        sorted_columns = sorted(df.columns, key=lambda x: int(x.split(":")[0]))
        df = df[sorted_columns]
        sorted_index = sorted(df.index, key=lambda x: int(x.split(":")[0]))
        df = df.loc[sorted_index]

        return df

    # 二者の感情を表す値の行列を取得
    def generate_emotion_matrix(self, emotion=0):
        assert emotion in [0, 1, 2, 3]

        rows = {}
        for c in self.chara_details:
            from_index = c["charasGameParam"]["Index"]
            row = {}
            table = c["charasGameParam"]["sensitivity"]["tableFavorabiliry"]

            for d in self.chara_details:
                to_index = d["charasGameParam"]["Index"]

                if to_index in table:
                    matrix = table[to_index]["longSensitivityCounts"]
                else:
                    matrix = [0, 0, 0, 0]

                row[f"{to_index}:{self.names[to_index]}"] = matrix

            rows[f"{from_index}:{self.names[from_index]}"] = row

        df = pd.DataFrame.from_dict(rows).T
        sorted_columns = sorted(df.columns, key=lambda x: int(x.split(":")[0]))
        df = df[sorted_columns]
        sorted_index = sorted(df.index, key=lambda x: int(x.split(":")[0]))
        df = df.loc[sorted_index]

        return df.map(lambda x: x[emotion])


############################################
# Streamlitのロジック部分
############################################
# ページ設定とタイトル
title = get_text("title", "ja")
st.set_page_config(page_title=title, layout="wide")

# サイドバーに言語選択を配置
with st.sidebar:
    lang = st.selectbox(
        "Language / 言語",
        options=["ja", "en"],
        format_func=lambda x: "日本語" if x == "ja" else "English",
        index=0,
    )

st.title(get_text("title", lang))
st.write(get_text("description", lang))

with st.expander(get_text("expander_title", lang)):
    st.markdown(get_text("expander_content", lang))

file = st.file_uploader(get_text("file_uploader", lang))
if file is not None:
    try:
        svs = SVSSaveData.load(file.getvalue())
    except Exception as e:
        st.error(get_text("error_load", lang), icon="🚨")
        st.stop()
    st.success(get_text("success_load", lang), icon="✅")

    if len(svs.charas) == 1:
        st.write(get_text("single_chara_warning", lang))
        st.stop()

    tab_graph, tab_sexual, tab_emotion_graph, tab_emotion, tab_command = st.tabs(
        [
            get_text("tab_sexual_graph", lang),
            get_text("tab_sexual_log", lang),
            get_text("tab_emotion_graph", lang),
            get_text("tab_emotion", lang),
            get_text("tab_command", lang),
        ]
    )

    with tab_command:
        commands = {
            # 話をしよう
            0: "0:日常的な話題",
            1: "1:恋愛的な話題",
            2: "2:エッチな話題",
            # 聞いてほしい
            3: "3:励ます",
            4: "4:なだめる",
            5: "5:褒める",
            6: "6:愚痴をこぼす",
            7: "7:謝る",
            8: "8:もの申す",
            # アドバイスする
            10: "10:食事を勧める",
            11: "11:勉強を勧める",
            12: "12:運動を勧める",
            13: "13:バイトを勧める",
            14: "14:人間関係を反省させる",
            15: "15:色恋沙汰を反省させる",
            16: "16:エッチを反省させる",
            # 相談する
            87: "87:食事の相談",
            88: "88:勉強の相談",
            89: "89:運動の相談",
            90: "90:バイトの相談",
            91: "91:人間関係の相談",
            92: "92:恋愛の相談",
            93: "93:エッチの相談",
            # あの人について
            17: "17:良い噂がある",
            18: "18:悪い噂がある",
            19: "19:仲良くしてほしい",
            20: "20:仲良くしたい",
            21: "21:どう思う？",
            # 一緒にしよう
            22: "22:食事しよう",
            23: "23:勉強しよう",
            24: "24:運動しよう",
            25: "25:バイトしよう",
            26: "26:部屋に来ない？",
            # 想いを伝える
            27: "27:好意を示す",
            28: "28:日曜昼に遊ぼう",
            29: "29:交際を申し込む",
            30: "30:別れてくれ",
            # スキンシップ
            31: "31:なでなでする",
            32: "32:抱きしめる",
            33: "33:キスする",
            34: "34:おさわりする",
            35: "35:エッチしよう",
            # 移動を頼む
            36: "36:ちょっと来てほしい",
            37: "37:NPC用?",
            38: "38:後でここに来てほしい",
            39: "39:なんでもない",
            # オネガイゴト
            78: "78:オネガイゴトをする",
            79: "79:あの人を避けてほしい",
            80: "80:アレを見せてほしい",
            81: "81:抱かせてほしい",
            82: "82:解放してあげる",
            9: "9:解放してほしい",  # これだけインデックスが離れているがこれで正しい
            # ログには残っている
            71: "71:?",
            72: "72:?",
            54: "54:?",
            55: "55:?",
            56: "56:?",
            57: "57:?",
            59: "59:?",
        }

        option = st.selectbox(
            get_text("select_command", lang),
            [v for v in sorted(commands.values(), key=lambda x: int(x.split(":")[0]))],
        )
        selected_command = int(option.split(":")[0])
        df_relations_yes = svs.generate_memory_matrix(
            command=selected_command, active=True, decision="yes"
        )
        df_relations_no = svs.generate_memory_matrix(
            command=selected_command, active=True, decision="no"
        )
        df_relations_ambiguous = svs.generate_memory_matrix(
            command=selected_command, active=True, decision="ambiguous"
        )

        st.caption(get_text("none_caption", lang))

        st.write(f"### {get_text('action_success', lang)}")
        st.dataframe(df_relations_yes)
        st.write(f"### {get_text('action_fail', lang)}")
        st.dataframe(df_relations_no)
        st.write(f"### {get_text('action_ambiguous', lang)}")
        st.dataframe(df_relations_ambiguous)

    with tab_sexual:
        sexual_commands = {
            "totalH": "totalH:総エッチ回数",
            "caress": "caress:愛撫行為回数",
            "service": "service:奉仕行為回数",
            "insertion": "insertion:挿入行為回数",
            "anal": "anal:アナル行為回数",
            "finish": "finish:イった回数",
            "hide": "hide:隠れてエッチした回数",
        }

        sexual_command_option = st.selectbox(
            get_text("select_sexual_action", lang),
            [v for v in sorted(sexual_commands.values())],
        )
        selected_sexual_command = sexual_command_option.split(":")[0]

        df_relations = svs.generate_sexual_memory_matrix(
            command=selected_sexual_command
        )
        df_relations = df_relations.replace(0, np.nan)

        st.dataframe(df_relations)

    with tab_graph:
        graph_option = st.selectbox(
            get_text("select_graph_action", lang),
            [v for v in sorted(sexual_commands.values())],
            index=6,
        )
        selected_command_graph = graph_option.split(":")[0]

        st.caption(get_text("graph_help", lang))

        gender = {}
        for c, cd in zip(svs.charas, svs.chara_details):
            index = cd["charasGameParam"]["Index"]
            name = f"{c['Parameter']['lastname']} {c['Parameter']['firstname']}"
            gender[f"{index}:{name}"] = c["Parameter"]["sex"]

        df_sexual_relations = svs.generate_sexual_memory_matrix(
            command=selected_command_graph
        )

        sorted_columns = sorted(
            df_sexual_relations.columns, key=lambda x: int(x.split(":")[0])
        )
        df_sexual_relations = df_sexual_relations[sorted_columns]
        df_sexual_relations = df_sexual_relations.fillna(0)

        # グラフの作成
        G = nx.from_pandas_adjacency(df_sexual_relations, create_using=nx.DiGraph())

        if selected_command_graph == "finish":
            net = Network(
                cdn_resources="in_line", height="600px", width="100%", directed=True
            )
        else:
            net = Network(cdn_resources="in_line", height="600px", width="100%")

        net.from_nx(G)
        for node in net.nodes:
            if gender[node["label"]] == 0:
                node["color"] = "#4f55ff"
            else:
                node["color"] = "#ff8080"
        for edge in net.edges:
            edge["color"] = "#4B4B4B"

        net.set_options("""
            var options = {
                "interaction": {
                    "navigationButtons": true
                }
            }
        """)
        html = net.generate_html()
        components.html(html, height=610)

    with tab_emotion:
        emotions = {
            0: "0:愛情値",
            1: "1:友情値",
            2: "2:無関心",
            3: "3:敵意",
        }

        emotion_option = st.selectbox(
            get_text("select_emotion", lang),
            [v for v in sorted(emotions.values())],
        )
        selected_emotion = int(emotion_option.split(":")[0])

        df_emotion = svs.generate_emotion_matrix(emotion=selected_emotion)

        st.dataframe(df_emotion)

    with tab_emotion_graph:
        emotion_graph_option = st.selectbox(
            get_text("select_emotion_graph", lang),
            [v for v in sorted(emotions.values())],
            index=0,
        )
        selected_emotion_graph = int(emotion_graph_option.split(":")[0])

        st.caption(get_text("graph_help", lang))
        st.caption(get_text("emotion_graph_help", lang))

        gender = {}
        for c, cd in zip(svs.charas, svs.chara_details):
            index = cd["charasGameParam"]["Index"]
            name = f"{c['Parameter']['lastname']} {c['Parameter']['firstname']}"
            gender[f"{index}:{name}"] = c["Parameter"]["sex"]

        df_emotion_graph = svs.generate_emotion_matrix(emotion=selected_emotion_graph)
        df_emotion_graph = df_emotion_graph // 7.5

        # グラフの作成
        G_emotion = nx.from_pandas_adjacency(
            df_emotion_graph, create_using=nx.DiGraph()
        )

        net_emotion = Network(
            cdn_resources="in_line", height="600px", width="100%", directed=True
        )

        net_emotion.from_nx(G_emotion)
        for node in net_emotion.nodes:
            if gender[node["label"]] == 0:
                node["color"] = "#4f55ff"
            else:
                node["color"] = "#ff8080"
        for edge in net_emotion.edges:
            edge["color"] = "#4B4B4B"

        net_emotion.set_options("""
            var options = {
                "interaction": {
                    "navigationButtons": true
                }
            }
        """)
        html = net_emotion.generate_html()
        components.html(html, height=610)
