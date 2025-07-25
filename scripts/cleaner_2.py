import pandas as pd
import yaml
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from backend.transforms import apply_transforms, handle_duplicates, enforce_allowed_values

def main(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    input_paths = config.get('input_files', [])
    if not input_paths:
        raise ValueError("Debe especificar 'input_files' en el archivo de configuración.")

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

    for input_path in files_to_process:
        # Leer datos
        if input_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path, sep=None, engine='python')

        # Transformaciones
        clean_df = apply_transforms(df, config)

        # Calidad
        dup_cfg = config.get('quality', {}).get('duplicates', {})
        if dup_cfg:
            clean_df, _ = handle_duplicates(
                clean_df,
                dup_cfg.get('key'),
                dup_cfg.get('action'),
                dup_cfg.get('latest_by')
            )
        for col, allowed in config.get('quality', {}).get('allowed_values', {}).items():
            clean_df, _ = enforce_allowed_values(clean_df, col, allowed)

        # Salida
        suffix = config.get('output', {}).get('suffix', '_clean')
        out_dir = Path(config.get('output', {}).get('dir', input_path.parent))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{input_path.stem}{suffix}{input_path.suffix}"
        out_path = out_dir / out_name

        fmt = config['output'].get('format', 'xlsx')
        if fmt == 'xlsx':
            clean_df.to_excel(out_path, index=False, sheet_name=config['output'].get('sheet_name', 'Sheet1'))
        else:
            clean_df.to_csv(out_path, index=False, sep=';')

        print(f"Archivo generado: {out_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python main_script.py ruta/al/config.yaml")
        sys.exit(1)
    main(sys.argv[1])