import argparse
import pandas as pd
import yaml
import unicodedata
import re
from datetime import datetime

# ---------- Transformations Registry ----------
def normalize_text(series, lowercase=True, strip_accents=True, trim=True):
    def _norm(x):
        if pd.isna(x): return x
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
    return series.apply(lambda x: regex.sub("", str(x)) if pd.notna(x) else x)

def regex_extract(series, pattern, group=1, as_type=None):
    regex = re.compile(pattern, flags=re.IGNORECASE)
    def _extract(x):
        if pd.isna(x): return None
        m = regex.search(str(x))
        if not m: return None
        val = m.group(group)
        if as_type == 'int':
            try: return int(val)
            except: return None
        return val
    return series.apply(_extract)

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
        if pd.isna(x): return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        return parts[index] if len(parts) > index else None
    return series.apply(_split)

def split_by_rest(series, delimiter=">", start_index=2, join_with=" > "):
    def _split_rest(x):
        if pd.isna(x): return None
        parts = [p.strip() for p in str(x).split(delimiter)]
        if len(parts) > start_index:
            return join_with.join(parts[start_index:])
        return None
    return series.apply(_split_rest)

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
    if column not in df.columns: return df, 0
    mask = ~df[column].isin(allowed) & df[column].notna()
    df.loc[mask, column] = "otro"
    return df, mask.sum()

# ---------- Main Runner ----------
def apply_transforms(df, config):
    out_df = pd.DataFrame()
    for target_col, rule in config['mappings'].items():
        src_col = rule['source']
        temp_series = df[src_col] if src_col in df.columns else pd.Series([None]*len(df))
        for t in rule.get('transforms', []):
            func = TRANSFORMS[t['name']]
            params = {k: v for k, v in t.items() if k != 'name'}
            temp_series = func(temp_series, **params)
        out_df[target_col] = temp_series
    return out_df

def main(input_path, config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Ingesta
    if input_path.lower().endswith(".xlsx"):
        df = pd.read_excel(input_path)
    else:
        df = pd.read_csv(input_path, sep=None, engine='python')

    # Transformación
    clean_df = apply_transforms(df, config)

    # Calidad
    logs = {}
    # Duplicados
    dup_cfg = config.get('quality', {}).get('duplicates', {})
    if dup_cfg:
        clean_df, dup_count = handle_duplicates(clean_df, dup_cfg.get('key'), dup_cfg.get('action'), dup_cfg.get('latest_by'))
        logs['duplicados'] = dup_count

    # Valores permitidos
    allowed_cfg = config.get('quality', {}).get('allowed_values', {})
    invalid_counts = {}
    for col, allowed in allowed_cfg.items():
        clean_df, invalid_count = enforce_allowed_values(clean_df, col, allowed)
        invalid_counts[col] = invalid_count
    logs['valores_fuera_de_catalogo'] = invalid_counts

    # Nulos
    null_counts = clean_df.isna().sum().to_dict()
    logs['nulos_por_columna'] = null_counts

    # Salida
    out = config['output']
    if out['format'] == 'xlsx':
        clean_df.to_excel(out['file_name'], index=False, sheet_name=out.get('sheet_name', 'Sheet1'))
    else:
        clean_df.to_csv(out['file_name'], index=False, sep=';')

    # Reporte simple
    summary_df = pd.DataFrame([{
    "registros_totales": len(clean_df),
    "duplicados_eliminados_o_marcados": logs.get("duplicados", 0)
    }])

    # --- Nulos por columna ---
    nulls_df = (
        pd.Series(logs.get("nulos_por_columna", {}), name="nulos")
        .reset_index()
        .rename(columns={"index": "columna"})
        .sort_values("nulos", ascending=False)
    )

    # --- Valores fuera de catálogo ---
    invalid_df = (
        pd.Series(logs.get("valores_fuera_de_catalogo", {}), name="fuera_de_catalogo")
        .reset_index()
        .rename(columns={"index": "columna"})
        .sort_values("fuera_de_catalogo", ascending=False)
    )

    print("Transformación completada.")
    print("Archivo generado:", out['file_name'])
    print("\n=== RESUMEN ===")
    print(summary_df.to_string(index=False, justify="center", col_space=15))

    print("\n=== NULOS POR COLUMNA ===")
    print(nulls_df.to_string(index=False, justify="center", col_space=20))

    print("\n=== FUERA DE CATÁLOGO ===")
    print(invalid_df.to_string(index=False, justify="center", col_space=20))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Ruta del dataset original.")
    parser.add_argument("-c", "--config", required=True, help="Ruta del archivo YAML de configuración.")
    args = parser.parse_args()

    main(args.input, args.config)
