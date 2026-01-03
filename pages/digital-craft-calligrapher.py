#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Honeycome Scene Text Generator - Streamlit App

このアプリケーションは、テキストを3D空間にピクセルアートとして描画する
Honeycomeシーンを生成します。
"""

import streamlit as st
import io
import json
import struct
from pathlib import Path
from typing import Any, BinaryIO, Dict, Union

from kkloader.funcs import get_png, load_string, load_type, write_string
from PIL import Image, ImageDraw, ImageFont
import copy
import numpy as np

SPACING_RATIO = 0.2
FONT_SIZE = 200
FONT_DIR = Path(__file__).parent / "digital-craft-calligrapher-data"

def list_available_fonts():
    return sorted(FONT_DIR.glob("*.ttf"))


def format_font_option(font_path):
    impressions = {
        "NotoSansJP-Regular.ttf": "ゴシック体",
        "NotoSerifJP-Regular.ttf": "明朝体",
        "YujiSyuku-Regular.ttf": "毛筆風",
        "MPLUSRounded1c-Regular.ttf": "やわらかい",
        "KleeOne-SemiBold.ttf": "手書き風",
    }
    note = impressions.get(font_path.name)
    if note:
        return f"{font_path.name} ({note})"
    return font_path.name

TEMPLATE_SCENE_META = {'version': '1.0.0',
 'data_id_1': 'deadbeef-dead-beef-dead-beefdeadbeef',
 'data_id_2': 'deadbeef-dead-beef-dead-beefdeadbeef',
 'title': 'テンプレート',
 'unknown_1': 1,
 'unknown_2': 32,
 'unknown_3': b'#\\d7\xf1l\xf3\xdb?v\xe0X\xf8\x1cJ\xae\xfc\x10I\x96\x15k*P\xbf*u\x91.Yr\xbe',
 'unknown_tail': b"0\x00\x00\x00\xee\xaa|\xcfZ\xdc\x97>\x14A\xf6\xfagp'\x84PB\xd3ze_7\xba\xad\xb5\x15\xa8O\xc3F\xd3"
                 b'\x18\x8b\x13&i0\xc9\xa2\x94?\xdcm\\7\x05\xdc\xe0\x00\x00\x00\x9a\xd9\x0e\x878|>=k\x1e\x930'
                 b"S\xe9\xdf\x14e\xf3\x00\xb3b?\xcd\xf5\xa1UW{\x01\x98\xd3ob\xbd\x87\xba\xbf\xa3p\xfd.%\xaf'"
                 b'\xa3\x9d\x10>\x81s\xf2\xc7\x8f\x88\x8b.\x96e%\xc8\x1ba;\x0f[\x1e\xa8\xa2\xdd\xf6(\xea\xeaV\xe9\xa6'
                 b'\x0f\xb8\x15^\xde!X\x8e\xb0\x81\xfb\x87d\x89\x9d\xea\x14R\x988\xb7\xa2s\xba\x0e\xf1x2\xed\xd5U\xf6'
                 b'D\x9bJ\x82\xb9L\x8c\xed\xc3B\xd5\xc25\xe2%Z\xba@sN\x9f/\xac\x15\xedj\xabj\xe7\xed\xc2\xec'
                 b'\xdd\xb83\x11l\xf9?\x95B\xdf\r\x15rb<|V\xe7k~\xf1<Q,*@\tD\x97\x01,s\x1d\x8c\xfe!a\t\xfb6\\:2\xfd'
                 b"7\x00Q\x87\x05\x94*@kk!y\x05\xbf5\xef\x0e's\x03\xf5\t{wTa\xeb\xd65\xbc\xd9\xef\xb1\xabQ\xc2"
                 b'I\xec\x1a50\x00\x00\x00\xf8\xe8\x14J\x87\xe2\x8f8v\x07q\x1d\xf1?v\xf14(% \xea\xcb\xaex=lAln\x01{C'
                 b'\xfd\xe9\xb4\xe4\x8e\xfd\x96\xd7;\x85\xff-fr\x16\xfe`\x00\x00\x00\xa0\x15a\t\x08\x07J\x0c\xac\xe0C>'
                 b'i\x99\xec\xe0y\xd1[MJ\x05\x0c\xa2\xfc\x96\xf6\xee&\x0c\xe1\x00)r)\xb9\xdf\xaa\xb4nV\x10\x0b\xec'
                 b'\xb6t\xa1\xd3\x95AP\xc2\xf0\x8aBd\x83\xd4\xb4p\xf5B\xce\xb7;k\xed\xf6\xfa\xbc\x1eJF\xcbt1\x87=\xebz'
                 b'\xac\xec^\xf7\x15 8i:QUh\x90!1v0\x00\x00\x00`)g\xf9\x1cN\x99\xfb\xc1\x9e\x80\x19\x0c\x96\x16\xe0)t>,'
                 b'\xc8\xc2\xd4t\x89\x98\x91\xd1\xd1\xc4\xd8\xbc\xdf\x92\xcf*b\x0c\x1d\xbaM\xd1\x8a\xf4\x12\x87!\x18'
                 b'@\x00\x00\x00\xaa\xf3\xff\xfb\xf4S\x80R\xda]7\x99\xdeig\xc6&\xd4\x187\x80\n\x80\xcf\x80\xd6Ch'
                 b'\x9amy\xb3X\x18\x88;\xce\xdb\x11&`\x89\x8c\x1c\xb7\x8a\xd8\xfe\x1e\x17\xa9l\x1f\xe4#\xb7'
                 b'\xf4\xdc\xc6kh\xaf\x9aB\x10\x00\x00\x00b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE'
                 b'\x10\x00\x00\x00b\xad\xc5\xdc\xeeXz\xb2\x90\xfb\xa5\xfd\x84b\xafE\x10\x00\x00\x00\xf4+\x98\x84'
                 b'\xde\xc3-\x15\xb0M<\xe2!"\xd5\xa5\x10\x00\x00\x00sR?\xa4b\xb8\t\xa6~\xb0\x10\xd3\xa0\xc9u\x16'
                 b'\x00\x10\x00\x00\x00D\xaa\xee\x9b\xe40^\xf6+\xe7*d\x08H\xe1]\x12\xe3\x80\x90DigitalCraft\xe3\x80\x91'}
TEMPLATE_FOLDER_KEY = 0
TEMPLATE_FOLDER_DATA = {'dicKey': 0,
 'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
 'rotation': {'x': 0.0, 'y': 0.0, 'z': 0.0},
 'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0},
 'treeState': 1,
 'visible': True,
 'name': 'フォルダー',
 'child': []}
TEMPLATE_PLANE_DATA = {'dicKey': 1,
 'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
 'rotation': {'x': 0.0, 'y': 0.0, 'z': 0.0},
 'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0},
 'treeState': 1,
 'visible': True,
 'group': 0,
 'category': 0,
 'no': 0,
 'anime_pattern': 0,
 'anime_speed': 3.0127916982983567e-43,
 'unknown_1': b'\x00\x00\x00\x00\x00\x00\x80?',
 'colors': [{'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 0.5, 'g': 0.5, 'b': 0.5, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
            {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0}],
 'unknown_2': -1,
 'unknown_3': False,
 'patterns': [{'unknown_float': 1.0,
               'key': 0,
               'clamp': False,
               'unknown_bool': False,
               'uv': {'x': 0.0, 'y': 0.0, 'z': 1.0, 'w': 1.0}},
              {'unknown_float': 0.0,
               'key': 0,
               'clamp': False,
               'unknown_bool': False,
               'uv': {'x': 0.0, 'y': 0.0, 'z': 1.0, 'w': 1.0}},
              {'unknown_float': 0.0,
               'key': 0,
               'clamp': False,
               'unknown_bool': False,
               'uv': {'x': 0.0, 'y': 0.0, 'z': 1.0, 'w': 1.0}}],
 'unknown_4': b'\x00\x00\x00\x00',
 'alpha': 1.0,
 'line_color': {'r': 0.0, 'g': 0.0, 'b': 0.0, 'a': 1.0},
 'line_width': 1.0,
 'emission_color': {'r': 1.0, 'g': 1.0, 'b': 1.0, 'a': 1.0},
 'emission_power': 0.0,
 'light_cancel': 0.0,
 'unknown_5': b'\x00\x00\x00\x00\x00\x00',
 'unknown_6': '{"x":0.0,"y":0.0,"z":1.0,"w":1.0}',
 'unknown_7': b'\x00\x00\x00\x00',
 'enable_fk': False,
 'bones': {},
 'enable_dynamic_bone': True,
 'unknown_8': True,
 'anime_normalized_time': 0.0,
 'child': []}


def build_template_scene() -> "HoneycomeSceneDataSimple":
    scene = HoneycomeSceneDataSimple()
    scene.image = None
    scene.version = TEMPLATE_SCENE_META["version"]
    scene.dataVersion = TEMPLATE_SCENE_META["version"]
    scene.data_id_1 = TEMPLATE_SCENE_META["data_id_1"]
    scene.data_id_2 = TEMPLATE_SCENE_META["data_id_2"]
    scene.title = TEMPLATE_SCENE_META["title"]
    scene.unknown_1 = TEMPLATE_SCENE_META["unknown_1"]
    scene.unknown_2 = TEMPLATE_SCENE_META["unknown_2"]
    scene.unknown_3 = TEMPLATE_SCENE_META["unknown_3"]
    scene.unknown_tail = TEMPLATE_SCENE_META["unknown_tail"]

    folder_obj = {"type": 3, "data": copy.deepcopy(TEMPLATE_FOLDER_DATA)}
    folder_obj["data"]["child"] = [{"type": 1, "data": copy.deepcopy(TEMPLATE_PLANE_DATA)}]
    scene.dicObject = {TEMPLATE_FOLDER_KEY: folder_obj}
    return scene


class HoneycomeSceneObjectLoader:
    """Minimal loader/saver for Honeycome items and folders."""

    _LOAD_DISPATCH = {
        1: "load_item_info",
        3: "load_folder_info",
    }

    _SAVE_DISPATCH = {
        1: "save_item_info",
        3: "save_folder_info",
    }

    @staticmethod
    def _dispatch_load(data_stream: BinaryIO, obj_type: int, obj_info: Dict[str, Any], version: str = None) -> None:
        method_name = HoneycomeSceneObjectLoader._LOAD_DISPATCH.get(obj_type)
        if method_name is None:
            return
        method = getattr(HoneycomeSceneObjectLoader, method_name)
        method(data_stream, obj_info, version)

    @staticmethod
    def _dispatch_save(data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None) -> None:
        obj_type = obj_info.get("type", -1)
        method_name = HoneycomeSceneObjectLoader._SAVE_DISPATCH.get(obj_type)
        if method_name is None:
            raise ValueError(f"Unknown object type: {obj_type}")
        method = getattr(HoneycomeSceneObjectLoader, method_name)
        method(data_stream, obj_info, version)

    @staticmethod
    def _load_vector3(data_stream: BinaryIO) -> Dict[str, float]:
        return {
            "x": struct.unpack("f", data_stream.read(4))[0],
            "y": struct.unpack("f", data_stream.read(4))[0],
            "z": struct.unpack("f", data_stream.read(4))[0],
        }

    @staticmethod
    def _save_vector3(data_stream: BinaryIO, vector3: Dict[str, float], default: float = 0.0) -> None:
        data_stream.write(struct.pack("f", vector3.get("x", default)))
        data_stream.write(struct.pack("f", vector3.get("y", default)))
        data_stream.write(struct.pack("f", vector3.get("z", default)))

    @staticmethod
    def _load_object_info_base(data_stream: BinaryIO) -> Dict[str, Any]:
        return {
            "dicKey": struct.unpack("i", data_stream.read(4))[0],
            "position": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "rotation": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "scale": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "treeState": struct.unpack("i", data_stream.read(4))[0],
            "visible": bool(struct.unpack("b", data_stream.read(1))[0]),
        }

    @staticmethod
    def _save_object_info_base(data_stream: BinaryIO, data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("i", data.get("dicKey", 0)))

        pos = data.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, pos, default=0.0)

        rot = data.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, rot, default=0.0)

        scale = data.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0})
        HoneycomeSceneObjectLoader._save_vector3(data_stream, scale, default=1.0)

        data_stream.write(struct.pack("i", data.get("treeState", 0)))
        data_stream.write(struct.pack("b", int(data.get("visible", True))))

    @staticmethod
    def load_bone_info(data_stream: BinaryIO) -> Dict[str, Any]:
        bone_data = {}
        bone_data["dicKey"] = struct.unpack("i", data_stream.read(4))[0]
        bone_data["changeAmount"] = {
            "position": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "rotation": HoneycomeSceneObjectLoader._load_vector3(data_stream),
            "scale": HoneycomeSceneObjectLoader._load_vector3(data_stream),
        }
        return bone_data

    @staticmethod
    def save_bone_info(data_stream: BinaryIO, bone_data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("i", bone_data.get("dicKey", 0)))
        change_amount = bone_data.get("changeAmount", {})
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("position", {"x": 0.0, "y": 0.0, "z": 0.0})
        )
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("rotation", {"x": 0.0, "y": 0.0, "z": 0.0})
        )
        HoneycomeSceneObjectLoader._save_vector3(
            data_stream, change_amount.get("scale", {"x": 1.0, "y": 1.0, "z": 1.0})
        )

    @staticmethod
    def load_pattern_info(data_stream: BinaryIO) -> Dict[str, Any]:
        pattern_data = {}
        pattern_data["unknown_float"] = struct.unpack("f", data_stream.read(4))[0]
        pattern_data["key"] = struct.unpack("i", data_stream.read(4))[0]
        pattern_data["clamp"] = bool(struct.unpack("b", data_stream.read(1))[0])
        pattern_data["unknown_bool"] = bool(struct.unpack("b", data_stream.read(1))[0])
        uv_json = load_string(data_stream).decode("utf-8")
        pattern_data["uv"] = json.loads(uv_json)
        return pattern_data

    @staticmethod
    def save_pattern_info(data_stream: BinaryIO, pattern_data: Dict[str, Any]) -> None:
        data_stream.write(struct.pack("f", pattern_data.get("unknown_float", 1.0)))
        data_stream.write(struct.pack("i", pattern_data["key"]))
        data_stream.write(struct.pack("b", int(pattern_data["clamp"])))
        data_stream.write(struct.pack("b", int(pattern_data.get("unknown_bool", False))))
        write_string(data_stream, json.dumps(pattern_data["uv"], separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def load_item_info(data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None) -> None:
        data = HoneycomeSceneObjectLoader._load_object_info_base(data_stream)
        data["group"] = struct.unpack("i", data_stream.read(4))[0]
        data["category"] = struct.unpack("i", data_stream.read(4))[0]
        data["no"] = struct.unpack("i", data_stream.read(4))[0]

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.1.1.0") >= 0:
            data["anime_pattern"] = struct.unpack("i", data_stream.read(4))[0]
        else:
            data["anime_pattern"] = 0

        data["anime_speed"] = struct.unpack("f", data_stream.read(4))[0]
        data["unknown_1"] = data_stream.read(8)

        data["colors"] = []
        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.3") >= 0:
            num_colors = 8
        else:
            num_colors = 7
        for _ in range(num_colors):
            color_bytes = load_string(data_stream)
            if len(color_bytes) > 0:
                data["colors"].append(json.loads(color_bytes.decode("utf-8")))
            else:
                data["colors"].append(None)
        if num_colors == 7:
            data["colors"].append({"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})

        data["unknown_2"] = struct.unpack("i", data_stream.read(4))[0]
        data["unknown_3"] = bool(struct.unpack("b", data_stream.read(1))[0])

        data["patterns"] = []
        for _ in range(3):
            data["patterns"].append(HoneycomeSceneObjectLoader.load_pattern_info(data_stream))

        data["unknown_4"] = data_stream.read(4)
        data["alpha"] = struct.unpack("f", data_stream.read(4))[0]

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.4") >= 0:
            line_color_json = load_string(data_stream).decode("utf-8")
            data["line_color"] = json.loads(line_color_json)
            data["line_width"] = struct.unpack("f", data_stream.read(4))[0]
        else:
            data["line_color"] = {"r": 128.0 / 255.0, "g": 128.0 / 255.0, "b": 128.0 / 255.0, "a": 1.0}
            data["line_width"] = 1.0

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.7") >= 0:
            emission_color_json = load_string(data_stream).decode("utf-8")
            data["emission_color"] = json.loads(emission_color_json)
            data["emission_power"] = struct.unpack("f", data_stream.read(4))[0]
            data["light_cancel"] = struct.unpack("f", data_stream.read(4))[0]
        else:
            data["emission_color"] = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
            data["emission_power"] = 0.0
            data["light_cancel"] = 0.0

        data["unknown_5"] = data_stream.read(6)
        data["unknown_6"] = load_string(data_stream).decode("utf-8")
        data["unknown_7"] = data_stream.read(4)

        data["enable_fk"] = bool(struct.unpack("b", data_stream.read(1))[0])

        bones_count = struct.unpack("i", data_stream.read(4))[0]
        data["bones"] = {}
        for _ in range(bones_count):
            bone_key = load_string(data_stream).decode("utf-8")
            data["bones"][bone_key] = HoneycomeSceneObjectLoader.load_bone_info(data_stream)

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.0.1") >= 0:
            data["enable_dynamic_bone"] = bool(struct.unpack("b", data_stream.read(1))[0])
        else:
            data["enable_dynamic_bone"] = True

        data["unknown_8"] = bool(struct.unpack("b", data_stream.read(1))[0])
        data["anime_normalized_time"] = struct.unpack("f", data_stream.read(4))[0]
        data["child"] = HoneycomeSceneObjectLoader.load_child_objects(data_stream, version)
        obj_info["data"] = data

    @staticmethod
    def load_folder_info(data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None) -> None:
        data = HoneycomeSceneObjectLoader._load_object_info_base(data_stream)
        name_bytes = load_string(data_stream)
        data["name"] = name_bytes.decode("utf-8")
        data["child"] = HoneycomeSceneObjectLoader.load_child_objects(data_stream, version)
        obj_info["data"] = data

    @staticmethod
    def save_item_info(data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None) -> None:
        data = obj_info["data"]
        HoneycomeSceneObjectLoader._save_object_info_base(data_stream, data)

        data_stream.write(struct.pack("i", data["group"]))
        data_stream.write(struct.pack("i", data["category"]))
        data_stream.write(struct.pack("i", data["no"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.1.1.0") >= 0:
            data_stream.write(struct.pack("i", data["anime_pattern"]))

        data_stream.write(struct.pack("f", data["anime_speed"]))
        data_stream.write(data["unknown_1"])

        num_colors = 8 if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.3") >= 0 else 7
        for i in range(num_colors):
            color = (
                data["colors"][i]
                if i < len(data["colors"]) and data["colors"][i] is not None
                else {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
            )
            write_string(data_stream, json.dumps(color, separators=(",", ":")).encode("utf-8"))

        data_stream.write(struct.pack("i", data["unknown_2"]))
        data_stream.write(struct.pack("b", int(data["unknown_3"])))

        for pattern in data["patterns"]:
            HoneycomeSceneObjectLoader.save_pattern_info(data_stream, pattern)

        data_stream.write(data["unknown_4"])
        data_stream.write(struct.pack("f", data["alpha"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.4") >= 0:
            write_string(data_stream, json.dumps(data["line_color"], separators=(",", ":")).encode("utf-8"))
            data_stream.write(struct.pack("f", data["line_width"]))

        if HoneycomeSceneObjectLoader._compare_versions(version, "0.0.7") >= 0:
            write_string(data_stream, json.dumps(data["emission_color"], separators=(",", ":")).encode("utf-8"))
            data_stream.write(struct.pack("f", data["emission_power"]))
            data_stream.write(struct.pack("f", data["light_cancel"]))

        data_stream.write(data["unknown_5"])
        write_string(data_stream, data["unknown_6"].encode("utf-8"))
        data_stream.write(data["unknown_7"])

        data_stream.write(struct.pack("b", int(data["enable_fk"])))
        data_stream.write(struct.pack("i", len(data["bones"])))
        for bone_key, bone_data in data["bones"].items():
            write_string(data_stream, bone_key.encode("utf-8"))
            HoneycomeSceneObjectLoader.save_bone_info(data_stream, bone_data)

        if HoneycomeSceneObjectLoader._compare_versions(version, "1.0.1") >= 0:
            data_stream.write(struct.pack("b", int(data["enable_dynamic_bone"])))

        data_stream.write(struct.pack("b", int(data["unknown_8"])))
        data_stream.write(struct.pack("f", data["anime_normalized_time"]))

        data_stream.write(struct.pack("i", len(data.get("child", []))))
        for child in data.get("child", []):
            HoneycomeSceneObjectLoader.save_child_objects(data_stream, child, version)

    @staticmethod
    def save_folder_info(data_stream: BinaryIO, obj_info: Dict[str, Any], version: str = None) -> None:
        data = obj_info["data"]
        HoneycomeSceneObjectLoader._save_object_info_base(data_stream, data)
        name = data.get("name", "")
        name_bytes = name.encode("utf-8") if isinstance(name, str) else name
        write_string(data_stream, name_bytes)

        child_list = data.get("child", [])
        data_stream.write(struct.pack("i", len(child_list)))
        for child in child_list:
            HoneycomeSceneObjectLoader.save_child_objects(data_stream, child, version)

    @staticmethod
    def load_child_objects(data_stream: BinaryIO, version: str = None) -> list:
        child_list = []
        count = struct.unpack("i", data_stream.read(4))[0]
        for _ in range(count):
            obj_type = struct.unpack("i", data_stream.read(4))[0]
            obj_info = {"type": obj_type, "data": {}}
            HoneycomeSceneObjectLoader._dispatch_load(data_stream, obj_type, obj_info, version)
            child_list.append(obj_info)
        return child_list

    @staticmethod
    def save_child_objects(data_stream: BinaryIO, child_data: Dict[str, Any], version: str = None) -> None:
        obj_type = child_data.get("type", -1)
        data_stream.write(struct.pack("i", obj_type))
        HoneycomeSceneObjectLoader._dispatch_save(data_stream, child_data, version)

    @staticmethod
    def _compare_versions(version_str: str, target: str) -> int:
        if version_str is None:
            return 1
        version_parts = [int(x) for x in version_str.split(".")]
        target_parts = [int(x) for x in target.split(".")]
        while len(version_parts) < len(target_parts):
            version_parts.append(0)
        while len(target_parts) < len(version_parts):
            target_parts.append(0)
        for v, t in zip(version_parts, target_parts):
            if v < t:
                return -1
            if v > t:
                return 1
        return 0


class HoneycomeSceneDataSimple:
    """Minimal Honeycome scene loader/saver for items and folders."""

    def __init__(self):
        self.image = None
        self.version = None
        self.dataVersion = None
        self.data_id_1 = None
        self.data_id_2 = None
        self.title = None
        self.unknown_1 = None
        self.unknown_2 = None
        self.unknown_3 = None
        self.dicObject = {}
        self.unknown_tail = b""

    @classmethod
    def load(cls, filelike: Union[str, bytes, io.BytesIO]) -> "HoneycomeSceneDataSimple":
        hs = cls()
        if isinstance(filelike, str):
            with open(filelike, "br") as f:
                data = f.read()
            data_stream = io.BytesIO(data)
        elif isinstance(filelike, bytes):
            data_stream = io.BytesIO(filelike)
        elif isinstance(filelike, io.BytesIO):
            data_stream = filelike
        else:
            raise ValueError(f"Unsupported input type: {type(filelike)}")

        hs.image = get_png(data_stream)
        version_str = load_string(data_stream).decode("utf-8")
        hs.data_id_1 = load_string(data_stream).decode("utf-8")
        hs.data_id_2 = load_string(data_stream).decode("utf-8")
        hs.title = load_string(data_stream).decode("utf-8")
        hs.unknown_1 = load_type(data_stream, "i")
        hs.unknown_2 = load_type(data_stream, "i")
        hs.unknown_3 = data_stream.read(32)
        hs.version = version_str
        hs.dataVersion = version_str

        obj_count = load_type(data_stream, "i")
        for _ in range(obj_count):
            key = load_type(data_stream, "i")
            obj_type = load_type(data_stream, "i")
            obj_info = {"type": obj_type, "data": {}}
            HoneycomeSceneObjectLoader._dispatch_load(data_stream, obj_type, obj_info, version_str)
            hs.dicObject[key] = obj_info

        hs.unknown_tail = data_stream.read()
        return hs

    def __bytes__(self) -> bytes:
        data_stream = io.BytesIO()
        if self.image:
            data_stream.write(self.image)

        version_bytes = self.version.encode("utf-8")
        data_stream.write(struct.pack("b", len(version_bytes)))
        data_stream.write(version_bytes)

        write_string(data_stream, self.data_id_1.encode("utf-8"))
        write_string(data_stream, self.data_id_2.encode("utf-8"))
        write_string(data_stream, self.title.encode("utf-8"))

        data_stream.write(struct.pack("i", self.unknown_1))
        data_stream.write(struct.pack("i", self.unknown_2))
        data_stream.write(self.unknown_3)

        data_stream.write(struct.pack("i", len(self.dicObject)))
        for key, obj_info in self.dicObject.items():
            data_stream.write(struct.pack("i", key))
            data_stream.write(struct.pack("i", obj_info["type"]))
            HoneycomeSceneObjectLoader._dispatch_save(data_stream, obj_info, self.version)

        data_stream.write(self.unknown_tail)
        return data_stream.getvalue()

# ============================
# Streamlit App
# ============================
# ページ設定
st.set_page_config(
    page_title="Digital Craft Calligrapher",
    page_icon="✨",
    layout="wide"
)

st.title("✨ Digital Craft Calligrapher")
st.markdown("テキストをデジタルクラフト内で平面を並べて再現します")


# セッション状態の初期化
if 'template_loaded' not in st.session_state:
    st.session_state.template_loaded = False
    st.session_state.template_scene = None
    st.session_state.plane_template = None
    st.session_state.folder_key = None
    st.session_state.folder_obj = None


# テンプレートの読み込み
@st.cache_resource
def load_template():
    """テンプレートシーンを読み込む"""
    template_scene = build_template_scene()
    folder_key = TEMPLATE_FOLDER_KEY
    folder_obj = template_scene.dicObject[folder_key]
    plane_template = folder_obj['data']['child'][0]

    return template_scene, plane_template, folder_key, folder_obj


# 関数定義
def load_font(font_size, font_path=None):
    font = None
    if font_path is not None:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except Exception:
            font = None
    if font is None:
        for candidate in list_available_fonts():
            try:
                font = ImageFont.truetype(str(candidate), font_size)
                break
            except Exception:
                font = None
    if font is None:
        font = ImageFont.load_default()
        st.warning("デフォルトフォントを使用しています")
    return font


def text_to_image(
    text,
    font_size=100,
    canvas_width=None,
    canvas_height=None,
    font_path=None,
    font=None,
    padding=10,
    vertical_align="center",
):
    """テキストを画像に描画"""
    if font is None:
        font = load_font(font_size, font_path)

    dummy_img = Image.new('L', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    if canvas_width is None:
        canvas_width = text_width + padding * 2
    if canvas_height is None:
        canvas_height = text_height + padding * 2

    img = Image.new('L', (canvas_width, canvas_height), color=0)
    draw = ImageDraw.Draw(img)

    x = (canvas_width - text_width) // 2 - bbox[0]
    if vertical_align == "bottom":
        y = canvas_height - padding - bbox[3]
    elif vertical_align == "top":
        y = padding - bbox[1]
    else:
        y = (canvas_height - text_height) // 2 - bbox[1]
    draw.text((x, y), text, fill=255, font=font)

    return img


def resample_image(img, target_width, target_height, vertical_align="center"):
    """画像を指定サイズにリサンプル"""
    scale = min(target_width / img.width, target_height / img.height)
    resized_width = max(1, int(img.width * scale))
    resized_height = max(1, int(img.height * scale))
    resized = img.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
    canvas = Image.new('L', (target_width, target_height), color=0)
    x = (target_width - resized_width) // 2
    if vertical_align == "bottom":
        y = target_height - resized_height
    elif vertical_align == "top":
        y = 0
    else:
        y = (target_height - resized_height) // 2
    canvas.paste(resized, (x, y))
    pixels = np.array(canvas)
    return pixels


def create_plane(template, x, y, z, color, scale=1.0):
    """平面オブジェクトを作成"""
    plane = copy.deepcopy(template)
    plane['data']['position']['x'] = x
    plane['data']['position']['y'] = y
    plane['data']['position']['z'] = z
    plane['data']['scale']['x'] = scale
    plane['data']['scale']['y'] = scale
    plane['data']['scale']['z'] = scale
    plane['data']['colors'][0] = color
    return plane


def hex_to_color(hex_color):
    """#RRGGBB to color dict with 0-1 floats."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return {"r": r, "g": g, "b": b, "a": 1.0}


def blend_colors(fg_color, bg_color, pixel_value):
    """Blend foreground and background using grayscale brightness."""
    t = pixel_value / 255.0
    return {
        "r": bg_color["r"] * (1.0 - t) + fg_color["r"] * t,
        "g": bg_color["g"] * (1.0 - t) + fg_color["g"] * t,
        "b": bg_color["b"] * (1.0 - t) + fg_color["b"] * t,
        "a": 1.0,
    }


def resolve_pixel_color(pixel_value, fg_color, bg_color, antialias):
    """Return per-pixel color based on antialias setting."""
    if not antialias:
        return fg_color
    return blend_colors(fg_color, bg_color, pixel_value)


def pixels_to_planes(pixels, plane_template, spacing=0.05, threshold=1, color=None,
                     edge_color=None, antialias=True,
                     scale=1.0, start_x=None, start_z=None):
    """ピクセルデータから平面オブジェクトを生成"""
    height, width = pixels.shape
    planes = []
    if color is None:
        color = {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}
    if edge_color is None:
        edge_color = {"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0}

    if start_x is None:
        start_x = -((width - 1) * spacing) / 2
    if start_z is None:
        start_z = -((height - 1) * spacing) / 2

    effective_threshold = 1 if antialias else 128

    for row in range(height):
        for col in range(width):
            pixel_value = pixels[row, col]

            if pixel_value >= effective_threshold:
                x = start_x + (width - 1 - col) * spacing
                z = start_z + row * spacing
                y = 0.0

                shaded_color = resolve_pixel_color(pixel_value, color, edge_color, antialias)
                plane = create_plane(plane_template, x, y, z, shaded_color, scale)
                planes.append(plane)

    return planes


def generate_text_scene(text, template_scene, plane_template, folder_key, folder_obj,
                       grid_width=80, grid_height=60, font_size=100,
                       text_scale=0.25, spacing=None, threshold=1, color=None, edge_color=None,
                       antialias=True, font_path=None):
    """テキストから3Dシーンを生成"""
    # spacing = scale × 0.2 の関係を利用
    if spacing is None:
        spacing = text_scale * SPACING_RATIO
    plane_scale = text_scale

    # 1. テキストを画像に変換（プレビュー用）
    font = load_font(font_size, font_path)
    img = text_to_image(text, font_size=font_size, font=font)
    padding = 5
    max_char_height = 0
    dummy_img = Image.new("L", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    for char in text:
        bbox = dummy_draw.textbbox((0, 0), char, font=font)
        max_char_height = max(max_char_height, bbox[3] - bbox[1])
    canvas_height = max_char_height + padding * 2

    # 2. 1文字ごとに平面を生成
    per_char_resolution = grid_height
    text_length = len(text)
    grid_width = per_char_resolution * max(1, text_length)
    pixels = np.zeros((grid_height, grid_width), dtype=np.uint8)

    global_start_x = -((grid_width - 1) * spacing) / 2
    global_start_z = -((grid_height - 1) * spacing) / 2

    char_folders = []
    plane_count = 0
    effective_threshold = 1 if antialias else 128

    for index, char in enumerate(text):
        display_index = text_length - 1 - index
        char_img = text_to_image(
            char,
            font_size=font_size,
            font=font,
            canvas_height=canvas_height,
            vertical_align="bottom",
        )
        char_pixels = resample_image(
            char_img,
            per_char_resolution,
            per_char_resolution,
            vertical_align="bottom",
        )

        start_col = display_index * per_char_resolution
        pixels[:, start_col:start_col + per_char_resolution] = char_pixels

        char_start_x = global_start_x + start_col * spacing
        nonzero_cols = np.where(char_pixels >= effective_threshold)[1]
        if nonzero_cols.size == 0:
            center_col = (per_char_resolution - 1) / 2
        else:
            center_col = (nonzero_cols.min() + nonzero_cols.max()) / 2
        center_x = char_start_x + (per_char_resolution - 1 - center_col) * spacing
        planes = pixels_to_planes(
                char_pixels,
                plane_template,
                spacing=spacing,
                threshold=threshold,
                color=color,
                edge_color=edge_color,
                antialias=antialias,
                scale=plane_scale,
                start_x=char_start_x,
                start_z=global_start_z
        )
        for plane in planes:
            plane['data']['position']['x'] -= center_x
        plane_count += len(planes)

        char_folder = copy.deepcopy(folder_obj)
        char_label = char if char.strip() else "空白"
        char_folder['data']['name'] = f"文字_{index + 1}_{char_label}"
        char_folder['data']['position']['x'] = center_x
        char_folder['data']['child'] = planes
        char_folder['data']['treeState'] = 1
        char_folders.append(char_folder)

    # 3. シーンを作成
    scene = HoneycomeSceneDataSimple()
    scene.version = template_scene.version
    scene.dataVersion = template_scene.dataVersion
    scene.data_id_1 = template_scene.data_id_1
    scene.data_id_2 = template_scene.data_id_2
    scene.title = f"テキスト: {text}"
    scene.unknown_1 = template_scene.unknown_1
    scene.unknown_2 = template_scene.unknown_2
    scene.unknown_3 = template_scene.unknown_3
    scene.unknown_tail = template_scene.unknown_tail
    scene.image = template_scene.image

    new_folder = copy.deepcopy(folder_obj)
    new_folder['data']['name'] = f"テキスト_{text}"
    new_folder['data']['child'] = char_folders
    new_folder['data']['treeState'] = 1
    scene.dicObject = {folder_key: new_folder}

    return scene, img, pixels, plane_count


# メイン UI
try:
    # テンプレート読み込み
    template_scene, plane_template, folder_key, folder_obj = load_template()

    if template_scene is None:
        st.stop()

    # メインページでパラメータ設定
    st.header("⚙️ パラメータ設定")

    # テキスト入力
    text_input = st.text_input("📝 テキスト", value="愛", max_chars=50)
    available_fonts = list_available_fonts()
    font_options = available_fonts
    default_font = FONT_DIR / "NotoSansJP-Regular.ttf"
    if default_font in available_fonts:
        default_index = font_options.index(default_font)
    else:
        default_index = 0
    selected_font = st.selectbox(
        "🔤 フォント",
        font_options,
        format_func=format_font_option,
        index=default_index,
    )

    st.markdown("---")

    # 文字の大きさ（縦幅）
    st.subheader("📏 文字の大きさ")
    st.text("文字の縦幅。0.1でキャラの手のひらほどの大きさ、1.7でキャラの身長ほどの大きさになります。")
    text_height = st.slider(
        "縦幅",
        min_value=0.1, max_value=2.0, value=0.5, step=0.05
    )

    st.markdown("---")

    # 詳細設定（エキスパンダーで折りたたみ）
    with st.expander("🎨 詳細設定", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            # 1文字あたりの解像度設定
            per_char_resolution = st.slider(
                "一文字あたり細かさ",
                min_value=10,
                max_value=100,
                value=40,
                step=5,
                help="この値を大きくするほど文字が綺麗になる一方、シーンが重くなります",
            )
            font_size = FONT_SIZE

        with col2:
            grid_height = per_char_resolution
            threshold = 1

        # 色モード
        color_hex = st.color_picker("色", value="#FFFFFF")
        edge_color_hex = st.color_picker("縁の色", value="#000000")
        antialias = st.checkbox("アンチエイリアスを使う", value=True)
        plane_size_factor = st.slider(
            "平面の大きさ",
            min_value=0.5, max_value=1.0, value=1.0, step=0.05,
            help="1.0が現在の大きさ。小さくすると文字がスカスカになります"
        )

    st.markdown("---")

    grid_width = max(1, per_char_resolution * max(1, len(text_input)))
    pixel_size = text_height / per_char_resolution
    text_scale = (pixel_size / SPACING_RATIO) * plane_size_factor
    spacing = pixel_size

    # 設定情報表示
    st.subheader("📊 現在の設定")
    info_col1, info_col2, info_col3 = st.columns(3)

    with info_col1:
        st.metric("文字の縦幅", f"{text_height:.2f}")
        st.metric("1pixelの大きさ", f"{pixel_size:.3f}")
        st.metric("平面の大きさ", f"{plane_size_factor:.2f}")

    with info_col2:
        st.metric("一文字あたり細かさ", f"{per_char_resolution}")
        st.metric("グリッドサイズ", f"{grid_width}×{grid_height}")
        st.metric("全体サイズ", f"{(grid_width-1)*spacing:.2f}×{(grid_height-1)*spacing:.2f}")

    with info_col3:
        st.metric("色", color_hex)
        st.metric("縁の色", edge_color_hex)
        st.metric("推定平面数", f"〜{int(grid_width*grid_height*0.3)}")

    st.markdown("---")

    # 生成ボタン
    generate_button = st.button("🚀 シーンを生成", type="primary", use_container_width=True)

    # 生成処理
    if generate_button:
        if not text_input:
            st.error("テキストを入力してください")
        else:
            with st.spinner("シーンを生成中..."):
                try:
                    color = hex_to_color(color_hex)
                    edge_color = hex_to_color(edge_color_hex)
                    scene, original_img, pixels, plane_count = generate_text_scene(
                        text=text_input,
                        template_scene=template_scene,
                        plane_template=plane_template,
                        folder_key=folder_key,
                        folder_obj=folder_obj,
                        grid_width=grid_width,
                        grid_height=grid_height,
                        font_size=font_size,
                        text_scale=text_scale,
                        spacing=spacing,
                        threshold=threshold,
                        color=color,
                        edge_color=edge_color,
                        antialias=antialias,
                        font_path=selected_font,
                    )

                    st.success(f"✅ 生成完了！ ({plane_count} 個の平面)")

                    # プレビュー表示
                    st.subheader("🖼️ プレビュー")

                    blocks = np.split(pixels, max(1, len(text_input)), axis=1)
                    preview_pixels = np.concatenate(list(reversed(blocks)), axis=1)

                    preview_col1, preview_col2 = st.columns(2)

                    with preview_col1:
                        st.markdown("**元のテキスト画像**")
                        st.image(original_img, use_container_width=True)

                    with preview_col2:
                        st.markdown(f"**ピクセルデータ ({grid_width}×{grid_height})**")
                        st.image(Image.fromarray(preview_pixels), use_container_width=True)

                    # シーン情報
                    st.subheader("📝 シーン情報")
                    st.markdown(f"""
                    - **タイトル**: {scene.title}
                    - **バージョン**: {scene.version}
                    - **平面数**: {plane_count}
                    - **推定ファイルサイズ**: 約 {len(bytes(scene)) / 1024:.1f} KB
                    """)

                    # ダウンロードボタン
                    safe_text = "".join(c if c.isalnum() else "_" for c in text_input)
                    filename = f"digitalcraft_scene_text_{safe_text}.png"

                    preview_buf = io.BytesIO()
                    Image.fromarray(preview_pixels).save(preview_buf, format="PNG")
                    scene.image = preview_buf.getvalue()

                    scene_bytes = bytes(scene)

                    st.download_button(
                        label="💾 シーンファイルをダウンロード",
                        data=scene_bytes,
                        file_name=filename,
                        mime="image/png",
                        type="primary",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    st.exception(e)


except Exception as e:
    st.error(f"アプリケーションの初期化に失敗しました: {str(e)}")
    st.exception(e)
