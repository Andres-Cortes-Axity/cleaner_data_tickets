import pandas as pd
import unicodedata
import re

# ---------- Transformations Registry ----------
def normalize_text(series, lowercase=True, strip_accents=True, trim=True):
    """
    Normalize text values in a pandas Series.

    This function applies trimming, lowercase conversion, and accent
    stripping to each element in the Series.

    Parameters:
        series (pd.Series): The Series containing text values.
        lowercase (bool): If True, convert text to lowercase. Default is True.
        strip_accents (bool): If True, remove accent characters. Default is True.
        trim (bool): If True, strip leading/trailing whitespace and collapse multiple spaces. Default is True.

    Returns:
        pd.Series: A new Series with normalized text values.
    """
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
    """
    Remove all occurrences of a regex pattern from a pandas Series of strings.

    Parameters:
        series (pd.Series): The Series containing text values.
        pattern (str): The regex pattern to remove (case-insensitive).

    Returns:
        pd.Series: A Series with the pattern removed and extra whitespace collapsed.
    """
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
    """
    Extract a regex capture group from each element in a pandas Series.

    Parameters:
        series (pd.Series): The Series containing text values.
        pattern (str): The regex pattern with capture groups.
        group (int): The index of the capture group to extract. Default is 1.
        as_type (str or None): If 'int', convert matches to int; otherwise return strings.

    Returns:
        pd.Series: A Series of extracted values (str or int), or None if no match.
    """
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
    """
    Convert a pandas Series to datetime objects.

    Parameters:
        series (pd.Series): The Series of date-like values.
        format (str or None): The datetime format string. Default is None (inferred).

    Returns:
        pd.Series: A Series of datetime64[ns] values, coercing errors to NaT.
    """
    return pd.to_datetime(series, format=format, errors='coerce')


def to_isoformat(series):
    """
    Convert each datetime value in a Series to an ISO-formatted string.

    Parameters:
        series (pd.Series): The Series of datetime values.

    Returns:
        pd.Series: A Series of ISO-formatted datetime strings, or None for NaT.
    """
    return series.apply(lambda x: x.isoformat(sep=' ') if pd.notna(x) else None)


def trim(series):
    """
    Strip leading and trailing whitespace from each string in a Series.

    Parameters:
        series (pd.Series): The Series of text values.

    Returns:
        pd.Series: A Series with whitespace trimmed, retaining non-null entries.
    """
    return series.apply(lambda x: str(x).strip() if pd.notna(x) else x)


def cast_type(series, to="string"):
    """
    Cast a pandas Series to a specified data type.

    Parameters:
        series (pd.Series): The Series to cast.
        to (str): The target type: 'string', 'int', or 'float'.

    Returns:
        pd.Series: The Series cast to the desired type.
    """
    if to == "string":
        return series.astype("string")
    if to == "int":
        return pd.to_numeric(series, errors='coerce').astype("Int64")
    if to == "float":
        return pd.to_numeric(series, errors='coerce')
    return series


def strip_leading_zeros(series):
    """
    Remove leading zeros from numeric strings in a Series.

    Parameters:
        series (pd.Series): The Series of numeric strings.

    Returns:
        pd.Series: A Series with leading zeros stripped, preserving non-digits.
    """
    return series.apply(lambda x: str(int(x)) if pd.notna(x) and str(x).isdigit() else x)


def split_by(series, delimiter=">", index=0):
    """
    Split each string in a Series by a delimiter and return the part at a given index.

    Parameters:
        series (pd.Series): The Series of text values.
        delimiter (str): The delimiter to split on.
        index (int): The segment index to return (0-based).

    Returns:
        pd.Series: A Series of the selected segments or None if missing.
    """
    def _split(x):
        if pd.isna(x):
            return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        return parts[index] if len(parts) > index else None
    return series.apply(_split)


def split_by_rest(series, delimiter=">", start_index=2, join_with=" > "):
    """
    Split each string in a Series by a delimiter and return the remainder joined.

    Parameters:
        series (pd.Series): The Series of text values.
        delimiter (str): The delimiter to split on.
        start_index (int): The first index to include in the remainder.
        join_with (str): The string used to join remaining segments.

    Returns:
        pd.Series: A Series of joined remainder segments or None if not available.
    """
    def _split_rest(x):
        if pd.isna(x):
            return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        if len(parts) > start_index:
            return join_with.join(parts[start_index:])
        return None
    return series.apply(_split_rest)

def reencode(series, from_enc="utf-16", to_enc="utf-8"):
    """
    Re-encode text values from one encoding to another.

    Parameters:
        series (pd.Series): The Series of bytes or strings to re-encode.
        from_enc (str): The source encoding. Default is 'utf-16'.
        to_enc (str): The target encoding. Default is 'utf-8'.

    Returns:
        pd.Series: A Series of strings in the target encoding.
    """
    def _conv(x):
        if pd.isna(x):
            return x
        # si es bytes, decodifica; si no, conviértelo a str
        if isinstance(x, (bytes, bytearray)):
            try:
                text = x.decode(from_enc)
            except:
                text = x.decode(from_enc, errors="ignore")
        else:
            text = str(x)
        # recodifica a bytes UTF‑8 y de nuevo a str
        try:
            b = text.encode(to_enc, errors="ignore")
            return b.decode(to_enc, errors="ignore")
        except:
            return text

    return series.apply(_conv)

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
    "reencode": reencode,
}

# ---------- Quality Functions ----------
def handle_duplicates(df, key, action, latest_by=None):
    """
    Handle duplicate rows in a DataFrame based on a key column.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        key (str): The column name to identify duplicates.
        action (str): One of 'keep_latest', 'drop', or 'mark'.
        latest_by (str): Column name to sort by when keeping the latest.

    Returns:
        tuple: (pd.DataFrame, int) - the processed DataFrame and count of duplicates found.
    """
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
    """
    Enforce a set of allowed values in a DataFrame column.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        column (str): The column to enforce values on.
        allowed (list): List of allowed values.

    Returns:
        tuple: (pd.DataFrame, int) - the updated DataFrame and count of replacements.
    """
    if column not in df.columns:
        return df, 0
    mask = ~df[column].isin(allowed) & df[column].notna()
    df.loc[mask, column] = "otro"
    return df, mask.sum()

# ---------- Apply Transforms Function ----------
def apply_transforms(df, config):
    """
    Apply a sequence of registered transforms to DataFrame columns based on a mapping config.

    Parameters:
        df (pd.DataFrame): The source DataFrame.
        config (dict): A config dict with 'mappings' that specify target columns and transforms.

    Returns:
        pd.DataFrame: A new DataFrame with transformed columns.
    """
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