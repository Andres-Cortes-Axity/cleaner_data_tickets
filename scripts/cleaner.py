import pandas as pd
import yaml
import unicodedata
import re
from datetime import datetime
from pathlib import Path
import sys

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
    if column not in df.columns:
        return df, 0
    mask = ~df[column].isin(allowed) & df[column].notna()
    df.loc[mask, column] = "otro"
    return df, mask.sum()

# ---------- Transformation Runner ----------
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

# ---------- Main Execution ----------
def main(config_path):
    # Carga configuración
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    input_paths = config.get('input_files', [])
    if not input_paths:
        raise ValueError("Debe especificar 'input_files' en el archivo de configuración.")

    # Expandir directorios y archivos
    files_to_process = []
    for path_str in input_paths:
        p = Path(path_str)
        if p.is_dir():
            for ext in ('*.xlsx', '*.xls', '*.csv'):
                files_to_process.extend(p.glob(ext))
        elif p.is_file():
            files_to_process.append(p)
        else:
            print(f"Ruta no encontrada: {p}")

    # Procesar cada archivo encontrado
    for input_path in files_to_process:
        # Leer datos
        if input_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path, sep=None, engine='python')

        # Transformaciones
        clean_df = apply_transforms(df, config)

        # Calidad: duplicados
        dup_cfg = config.get('quality', {}).get('duplicates', {})
        if dup_cfg:
            clean_df, _ = handle_duplicates(
                clean_df,
                dup_cfg.get('key'),
                dup_cfg.get('action'),
                dup_cfg.get('latest_by')
            )
        # Calidad: valores permitidos
        for col, allowed in config.get('quality', {}).get('allowed_values', {}).items():
            clean_df, _ = enforce_allowed_values(clean_df, col, allowed)

        # Preparar salida
        suffix = config.get('output', {}).get('suffix', '_clean')
        out_dir = Path(config.get('output', {}).get('dir', input_path.parent))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{input_path.stem}{suffix}{input_path.suffix}"
        out_path = out_dir / out_name

        # Guardar según formato
        fmt = config['output'].get('format', 'xlsx')
        if fmt == 'xlsx':
            clean_df.to_excel(out_path, index=False, sheet_name=config['output'].get('sheet_name', 'Sheet1'))
        else:
            clean_df.to_csv(out_path, index=False, sep=';')

        print(f"Archivo generado: {out_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python script.py ruta/al/config.yaml")
        sys.exit(1)
    main(sys.argv[1])
