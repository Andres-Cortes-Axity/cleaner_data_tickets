import pandas as pd
import unicodedata
import re

# ---------- Transformations Registry ----------
def normalize_text(series, lowercase=True, strip_accents=True, trim=True):
    def _norm(x):
        if pd.isna(x):
            return x
        s = str(x)
        if trim:
            s = s.strip()
            s = re.sub(r"\s+", " ", s)
        if lowercase:
            s = s.lower()
        if strip_accents:
            s = ''.join(
                c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn'
            )
        return s
    return series.apply(_norm)


def remove_pattern(series, pattern):
    regex = re.compile(pattern, flags=re.IGNORECASE)

    def _remove(x):
        if pd.isna(x):
            return x
        s = regex.sub("", str(x))
        # eliminamos espacios múltiples y recortamos
        s = re.sub(r"\s+", " ", s).strip()
        return s

    return series.apply(_remove)



def regex_extract(series, pattern, group=1, as_type=None):
    regex = re.compile(pattern, flags=re.IGNORECASE)

    if as_type == 'int':
        # Creamos explícitamente una lista de Python ints/None
        def _extract_int(x):
            if pd.isna(x):
                return None
            m = regex.search(str(x))
            if not m:
                return None
            try:
                return int(m.group(group))
            except:
                return None

        # Devolvemos un Series de dtype object, para que None se mantenga None
        return pd.Series(
            [_extract_int(x) for x in series],
            index=series.index,
            dtype=object
        )

    # Caso por defecto: devolvemos strings y None
    def _extract_str(x):
        if pd.isna(x):
            return None
        m = regex.search(str(x))
        if not m:
            return None
        return m.group(group)

    return series.apply(_extract_str)



def to_datetime(series, format=None):
    return pd.to_datetime(series, format=format, errors='coerce')


def to_isoformat(series):
    return series.apply(lambda x: x.isoformat(sep=' ') if pd.notna(x) else None)


def trim(series):
    return series.apply(lambda x: str(x).strip() if pd.notna(x) else x)


def cast_type(series, to="string"):
    if to == "string":
        return series.astype("string")
    if to == "int":
        return pd.to_numeric(series, errors='coerce').astype("Int64")
    if to == "float":
        return pd.to_numeric(series, errors='coerce')
    return series


def strip_leading_zeros(series):
    return series.apply(lambda x: str(int(x)) if pd.notna(x) and str(x).isdigit() else x)


def split_by(series, delimiter=">", index=0):
    def _split(x):
        if pd.isna(x):
            return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        return parts[index] if len(parts) > index else None
    return series.apply(_split)


def split_by_rest(series, delimiter=">", start_index=2, join_with=" > "):
    def _split_rest(x):
        if pd.isna(x):
            return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        if len(parts) > start_index:
            return join_with.join(parts[start_index:])
        return None
    return series.apply(_split_rest)

# ---------- TRANSFORMS Dictionary ----------
TRANSFORMS = {
    "normalize_text": normalize_text,
    "remove_pattern": remove_pattern,
    "regex_extract": regex_extract,
    "to_datetime": to_datetime,
    "to_isoformat": to_isoformat,
    "trim": trim,
    "cast_type": cast_type,
    "strip_leading_zeros": strip_leading_zeros,
    "split_by": split_by,
    "split_by_rest": split_by_rest,
}

# ---------- Quality Functions ----------
def handle_duplicates(df, key, action, latest_by=None):
    if key not in df.columns:
        return df, 0
    dup_count = df.duplicated(subset=[key]).sum()
    if action == "keep_latest" and latest_by in df.columns:
        df = df.sort_values(by=latest_by).drop_duplicates(subset=[key], keep='last')
    elif action == "drop":
        df = df.drop_duplicates(subset=[key], keep='first')
    elif action == "mark":
        df['duplicado'] = df.duplicated(subset=[key])
    return df, dup_count


def enforce_allowed_values(df, column, allowed):
    if column not in df.columns:
        return df, 0
    mask = ~df[column].isin(allowed) & df[column].notna()
    df.loc[mask, column] = "otro"
    return df, mask.sum()

# ---------- Apply Transforms Function ----------
def apply_transforms(df, config):
    out_df = pd.DataFrame()
    for target_col, rule in config['mappings'].items():
        src = rule['source']
        temp = df[src] if src in df.columns else pd.Series([None]*len(df))
        for t in rule.get('transforms', []):
            func = TRANSFORMS[t['name']]
            params = {k: v for k, v in t.items() if k != 'name'}
            temp = func(temp, **params)
        out_df[target_col] = temp
    return out_df