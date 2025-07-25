import pytest
import pandas as pd
import os
import sys

# Añade la carpeta padre de 'tests/' al path de búsqueda de módulos
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)
    )
)
from backend.transforms import (
    normalize_text, remove_pattern, regex_extract,
    to_datetime, to_isoformat, trim, cast_type,
    strip_leading_zeros, split_by, split_by_rest,
    handle_duplicates, enforce_allowed_values,
    apply_transforms, TRANSFORMS
)


def test_normalize_text_basic():
    s = pd.Series([" Héllo  Wörld ", None, "TeST"])
    out = normalize_text(s)
    assert out.tolist() == ["hello world", None, "test"]

def test_remove_pattern():
    s = pd.Series(["abc123def", "XYZ456", None])
    out = remove_pattern(s, r"\d+")
    assert out.tolist() == ["abcdef", "XYZ", None]

@pytest.mark.parametrize("as_type,expected", [
    (None, ["123", None, None]),
    ("int", [123, None, None]),
])
def test_regex_extract(as_type, expected):
    s = pd.Series(["foo123bar", "no digits", None])
    out = regex_extract(s, r"(\d+)", as_type=as_type)
    assert out.tolist() == expected

def test_to_datetime_and_isoformat():
    s = pd.Series(["2025-07-25 13:15", "invalid", None])
    dt = to_datetime(s, format="%Y-%m-%d %H:%M")
    # El segundo y tercero se convierten a NaT
    assert pd.notna(dt.iloc[0]) and dt.iloc[0].hour == 13
    assert pd.isna(dt.iloc[1])
    # Isoformat
    iso = to_isoformat(dt)
    assert iso.iloc[0].startswith("2025-07-25 13:15")
    assert iso.iloc[1] is None

def test_trim():
    s = pd.Series(["  hello ", None])
    out = trim(s)
    assert out.tolist() == ["hello", None]

def test_cast_type():
    s = pd.Series(["1", "2", None])
    assert cast_type(s, to="int").dtype == "Int64"
    assert cast_type(s, to="float").dtype == float
    assert cast_type(s, to="string").dtype == "string"

def test_strip_leading_zeros():
    s = pd.Series(["00123", "0456", "abc", 0, None])
    out = strip_leading_zeros(s)
    assert out.tolist() == ["123", "456", "abc", "0", None]

def test_split_by_and_rest():
    s = pd.Series(["a>b>c>d", "onlyone", None])
    # split_by
    assert split_by(s, ">", index=0).tolist() == ["a", "onlyone", None]
    assert split_by(s, ">", index=1).tolist() == ["b", None, None]
    # split_by_rest
    assert split_by_rest(s).tolist() == ["c > d", None, None]
    # custom delimiter/join
    assert split_by_rest(s, delimiter=">", start_index=1, join_with="|").tolist() == ["b|c|d", None, None]

def test_transforms_registry():
    # Asegurarnos de que todas las funciones estén en TRANSFORMS y sean llamables
    for name, func in TRANSFORMS.items():
        assert callable(func), f"{name} debería ser callable"

def test_handle_duplicates_drop_and_count():
    df = pd.DataFrame({
        "key": [1, 1, 2, 3, 3, 3],
        "val": [10, 20, 30, 40, 50, 60]
    })
    # drop
    df2, cnt = handle_duplicates(df.copy(), "key", "drop")
    assert cnt == 3  # hay 3 filas duplicadas
    assert df2["key"].tolist() == [1, 2, 3]
    # keep_latest
    df3, cnt3 = handle_duplicates(df.copy(), "key", "keep_latest", latest_by="val")
    assert cnt3 == 3
    # para key=1 se queda con val=20, para 3 con 60
    assert df3.set_index("key")["val"].to_dict() == {1: 20, 2: 30, 3: 60}
    # mark
    df4, cnt4 = handle_duplicates(df.copy(), "key", "mark")
    assert cnt4 == 3
    assert "duplicado" in df4.columns
    # hay exactamente 3 True en duplicado
    assert df4["duplicado"].sum() == 3

def test_enforce_allowed_values():
    df = pd.DataFrame({
        "col": ["a", "b", "x", None]
    })
    df2, cnt = enforce_allowed_values(df.copy(), "col", allowed=["a", "b"])
    assert cnt == 1
    assert df2["col"].tolist() == ["a", "b", "otro", None]

def test_apply_transforms_end_to_end():
    df = pd.DataFrame({
        "raw_text": ["  Dígito 123  ", "TEST"],
        "code": ["A-001", "B-002"]
    })
    config = {
        "mappings": {
            "text": {
                "source": "raw_text",
                "transforms": [
                    {"name": "normalize_text"},
                    {"name": "remove_pattern", "pattern": r"\d+"}
                ]
            },
            "code_num": {
                "source": "code",
                "transforms": [
                    {"name": "regex_extract", "pattern": r"-(\d+)", "group": 1, "as_type": "int"}
                ]
            }
        }
    }
    out = apply_transforms(df, config)
    assert out["text"].tolist() == ["digito", "test"]
    assert out["code_num"].tolist() == [1, 2]
