
import os
import sys
from typing import Callable, Dict, List
import pandas as pd
from rich.console import Console
from rich.table import Table

"""
conteo_tokens.py

This script calculates token counts and input costs for text data contained
in Excel files within a specified directory, using different tokenizer models.
It reads all sheets and cells in Excel files, counts tokens per model,
computes costs based on per-1K-token pricing, and displays results in a
rich-formatted table.
"""

def display_rich(df):
    console = Console()
    table = Table(show_header=True, header_style="bold")
    for col in df.columns:
        table.add_column(str(col))
    for _, row in df.iterrows():
        table.add_row(*[str(x) for x in row.tolist()])
    console.print(table)


# CONFIGURA AQUÍ lo mínimo: modelos y precios (USD/1K)
MODELOS = [
    "openai:gpt-4o",
    "anthropic:claude-3.5-sonnet",
    "xai:grok-2",
]

PRECIOS = {
    "openai:gpt-4o":               {"input": 0.005,   "output": 0.015},
    "anthropic:claude-3.5-sonnet":    {"input": 0.003,   "output": 0.015},
    "xai:grok-2":               {"input": 0.003,   "output": 0.012},
}

# Tokenizers (aprox/official)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    from anthropic._tokenizers import Tokenizer as AnthropicTokenizer
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def _fallback_tiktoken():
    """
    Fallback to the base CL100K tokenizer if specific model encoding is unsupported.

    Returns:
        Encoding: The cl100k_base tiktoken encoding instance.
    Raises:
        RuntimeError: If tiktoken library is not installed.
    """
    if not TIKTOKEN_AVAILABLE:
        raise RuntimeError("Instala tiktoken: pip install tiktoken")
    return tiktoken.get_encoding("cl100k_base")


def openai_tokenizer(model_real: str) -> Callable[[str], int]:
    """
    Create a token counting function for OpenAI models using tiktoken.

    Args:
        model_real (str): Model identifier to retrieve specific encoding.

    Returns:
        Callable[[str], int]: Function that takes text and returns token count.

    Raises:
        RuntimeError: If tiktoken is not installed.
    """
    if not TIKTOKEN_AVAILABLE:
        raise RuntimeError("tiktoken no está instalado. pip install tiktoken")
    try:
        enc = tiktoken.encoding_for_model(model_real)
    except KeyError:
        enc = _fallback_tiktoken()

    return lambda txt: len(enc.encode(txt if isinstance(txt, str) else str(txt)))


def anthropic_tokenizer(_model_real: str) -> Callable[[str], int]:
    """
    Create a token counting function for Anthropic models.

    If the Anthropic tokenizer library is unavailable, falls back to OpenAI's cl100k_base.

    Args:
        _model_real (str): Model identifier (unused internally).

    Returns:
        Callable[[str], int]: Function that takes text and returns token count.
    """
    if ANTHROPIC_AVAILABLE:
        tok = AnthropicTokenizer()
        return lambda txt: len(tok.encode(txt if isinstance(txt, str) else str(txt)))
    else:
        return openai_tokenizer("cl100k_base")


def grok_tokenizer(_model_real: str) -> Callable[[str], int]:
    """
    Approximate token counting for xAI Grok models using OpenAI's cl100k_base.

    Args:
        _model_real (str): Model identifier (unused internally).

    Returns:
        Callable[[str], int]: Function that takes text and returns token count.
    """
    # No hay tokenizer público. Aproximamos con cl100k_base.
    return openai_tokenizer("cl100k_base")


TOKENIZERS: Dict[str, Callable[[str], int]] = {}


def registrar_tokenizers():
    """
    Populate the TOKENIZERS registry with token counting functions for each model.
    """
    # OpenAI
    TOKENIZERS["openai:gpt-4o"] = openai_tokenizer("gpt-4o")
    # Anthropic
    TOKENIZERS["anthropic:claude-3.5-sonnet"] = anthropic_tokenizer("claude-3.5-sonnet")
    # xAI
    TOKENIZERS["xai:grok-2"] = grok_tokenizer("grok-2")


registrar_tokenizers()


# Funciones de conteo y costo
def leer_excel_como_textos(path_excel: str) -> List[str]:
    """
    Read all sheets and cells from an Excel file, returning their contents as text.

    Args:
        path_excel (str): Path to the Excel (.xlsx or .xls) file.

    Returns:
        List[str]: List of cell values converted to strings.

    Notes:
        Errors during reading will be printed and result in an empty list.
    """
    try:
        xl = pd.ExcelFile(path_excel)
        textos = []
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            for _, row in df.iterrows():
                for celda in row:
                    textos.append(str(celda))
        return textos
    except Exception as e:
        print(f"Error leyendo {path_excel}: {e}")
        return []


def contar_tokens(textos: List[str], modelo: str) -> int:
    """
    Read all sheets and cells from an Excel file, returning their contents as text.

    Args:
        path_excel (str): Path to the Excel (.xlsx or .xls) file.

    Returns:
        List[str]: List of cell values converted to strings.

    Notes:
        Errors during reading will be printed and result in an empty list.
    """
    count_fn = TOKENIZERS.get(modelo)
    if not count_fn:
        raise ValueError(f"Modelo no soportado: {modelo}")
    return sum(count_fn(t) for t in textos)


def costo_input(tokens: int, modelo: str) -> float:
    """
    Calculate the input cost in USD for a given token count and model.

    Args:
        tokens (int): Number of input tokens.
        modelo (str): Model identifier (must be a key in PRECIOS).

    Returns:
        float: Cost rounded to two decimals; returns 0.0 if model not found.
    """
    info = PRECIOS.get(modelo)
    if not info:
        return 0.0
    return round((tokens / 1000.0) * info["input"], 2)


def main():
    """
    Main entry point: iterate over Excel files in a directory, compute token counts and costs.

    Reads an optional directory path from command-line arguments (default current directory),
    processes each .xlsx/.xls file, and displays a rich-formatted summary table with columns:
    archivo, tokens_<model>, costo_<model> for each configured model.
    """
    # Directorio: primer argumento opcional; por defecto "."
    directorio = sys.argv[1] if len(sys.argv) > 1 else "."

    filas = []
    for archivo in os.listdir(directorio):
        if archivo.lower().endswith((".xlsx", ".xls")):
            ruta = os.path.join(directorio, archivo)
            textos = leer_excel_como_textos(ruta)
            fila = {"archivo": archivo}
            for m in MODELOS:
                toks = contar_tokens(textos, m)
                fila[f"tokens_{m}"] = toks
                fila[f"costo_{m}"] = costo_input(toks, m)
            filas.append(fila)

    if not filas:
        print("No se encontraron archivos Excel en el directorio.")
        return

    df = pd.DataFrame(filas)

    # Orden de columnas: archivo primero y luego cada modelo (tokens/costo)
    cols = ["archivo"]
    for m in MODELOS:
        cols += [f"tokens_{m}", f"costo_{m}"]
    df = df[cols]

    # Imprimir
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print("\nResumen de tokens y costos (input):\n")
    display_rich(df)


    # Descomenta si quieres guardar:
    # df.to_csv("resultado_tokens.csv", index=False)
    # df.to_excel("resultado_tokens.xlsx", index=False)
    # print("\nGuardado resultado_tokens.csv y resultado_tokens.xlsx")


if __name__ == "__main__":
    main()
