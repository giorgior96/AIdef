"""Boat Filter – Gemini + Polars
================================

Versione ottimizzata che usa **Polars** al posto di pandas: su dataset
medio‐grandi (100k‑1M righe) può essere 5‑30× più veloce nei filtri, grazie
al motore eseguito in Rust e alla parallelizzazione automatica.

Flusso:
1. Carichiamo `boats.json` in un `pl.DataFrame`.
2. Gemini converte la query utente in **un'unica espressione Polars** che si
   valuta con `eval()` (es. `df.filter((pl.col('price')<5e5) & (pl.col('max_speed').is_max()))`).
3. Il risultato viene trasformato in elenco puntato con le sole colonne
   citate + nome barca.

Requisiti: python‑dotenv, rich, google‑generativeai, **polars>=0.20**
Chiave API: `GEMINI_API_KEYS` in `.env`.

⚠️ eval() è sempre delicato: sandbox raccomandata in prod.
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import List, Set, Any, Tuple

import polars as pl
from rich.console import Console
from dotenv import load_dotenv
import google.generativeai as genai

###############################################################################
# 1. Dataset loader                                                          #
###############################################################################

def load_dataset(fp: str | Path = "output_with_contact.json") -> pl.DataFrame:
    data = json.loads(Path(fp).read_text(encoding="utf-8"))
    return pl.DataFrame(data)

###############################################################################
# 2. Prompt template                                                         #
###############################################################################

INSTRUCTION_STR = (
    "1. Convert the query to executable Python code using **Polars** (not pandas).\n"
    "2. The final line must be a Python expression that can be passed to eval().\n"
    "3. It **must return a pl.DataFrame** (use head() if necessary).\n"
    "4. PRINT ONLY THE EXPRESSION, no extra text or formatting.\n"
    "5. Do not wrap the expression in quotes or markdown.\n"
    "6. Use `df.filter(<boolean>)`, `pl.lit`, or the lazy API; **avoid** `df[bool_mask]` row‑filter syntax.\n"
    "7. **IMPORTANT**: If the query mentions a specific brand name (like 'Azimut', 'Ferretti', 'Princess', etc.), "
    "you MUST filter by that brand. Look for brand information in columns like 'brand', 'manufacturer', 'make', "
    "or check if the brand name appears in the boat name. Use case-insensitive matching with `str.contains()`.\n"
    "8. For brand filtering, use: `df.filter(pl.col('brand').str.contains('brand_name'))` "
    "or similar pattern matching.\n"
    "9. For location filtering, use: `df.filter(pl.col('location').str.contains('location_name'))` "
    "or similar pattern matching.\n"
    "10. Combine filters using `&` (AND) operator."
)

PROMPT_TEMPLATE = (
    "You are working with a Polars DataFrame in Python.\n"
    "The DataFrame variable is named `df`.\n"
    "Here is the output of `print(df.head())`:\n"
    "{df_str}\n\n"
    "Follow these instructions strictly:\n"
    "{instructions}\n"
    "Query: {query}\n\n"
    "Expression:"
)

###############################################################################
# 3. Gemini helper                                                           #
###############################################################################

def get_polars_expression(query: str, df_sample: str, model: str = "gemini-2.5-flash") -> str:
    prompt = PROMPT_TEMPLATE.format(df_str=df_sample, instructions=INSTRUCTION_STR, query=query)
    model_obj = genai.GenerativeModel(model)
    resp = model_obj.generate_content(prompt, generation_config={"temperature": 0})
    expr = resp.text.strip()
    if expr.startswith("```"):
        expr = expr.strip("`\n").removeprefix("python").strip()
    return expr

###############################################################################
# 4. Utilities                                                               #
###############################################################################

# Column mappings for consistent display
NAME_COLS = ["boat_name", "Nome della barca", "boatName", "name", "title"]
PRICE_COLS = ["price", "Price", "prezzo", "cost"]
YEAR_COLS = ["year", "Year", "anno", "build_year", "construction_year"]
BRAND_COLS = ["brand", "Brand", "marca", "manufacturer", "make"]
LOCATION_COLS = ["location", "Location", "luogo", "region", "area", "port"]

# Always display these columns in order
REQUIRED_COLS = ["name", "price", "year"]

def extract_cols(expr: str) -> List[str]:
    cols: Set[str] = set()
    # pl.col('price') or pl.col("price")
    cols.update(re.findall(r"pl\.col\( ?['\"]([^'\"]+)['\"] ?\)", expr))
    # df['price'] style (rare)
    cols.update(re.findall(r"df\[ ?['\"]([^'\"]+)['\"] ?\]", expr))
    return list(cols)

def get_display_columns(df: pl.DataFrame, query_cols: List[str]) -> List[str]:
    """Get the columns to display, ensuring name, price, and year are always included."""
    display_cols = []
    
    # Find the actual column names in the dataframe
    name_col = next((c for c in NAME_COLS if c in df.columns), None)
    price_col = next((c for c in PRICE_COLS if c in df.columns), None)
    year_col = next((c for c in YEAR_COLS if c in df.columns), None)
    
    # Always add name first if available
    if name_col:
        display_cols.append(name_col)
    
    # Add price if available
    if price_col and price_col not in display_cols:
        display_cols.append(price_col)
    
    # Add year if available
    if year_col and year_col not in display_cols:
        display_cols.append(year_col)
    
    # Add other columns from the query that aren't already included
    for col in query_cols:
        if col in df.columns and col not in display_cols:
            display_cols.append(col)
    
    return display_cols

def format_value(value: Any) -> str:
    """Format values for display."""
    if value is None:
        return "N/A"
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    else:
        return str(value)

def bullets(df: pl.DataFrame, cols: List[str]):
    console = Console()
    if df.is_empty():
        console.print("[yellow]Nessun risultato trovato.[/]")
        return

    # Get the columns to display
    display_cols = get_display_columns(df, cols)
    
    if not display_cols:
        console.print("[yellow]Nessuna colonna valida trovata per la visualizzazione.[/]")
        return

    console.print(f"\n[bold green]Risultati trovati: {len(df)}[/]")
    
    for i, row in enumerate(df.rows(named=True), 1):
        console.print(f"\n[bold blue]• Barca #{i}[/]")
        
        for col in display_cols:
            if col in row:
                value = row[col]
                formatted_value = format_value(value)
                
                # Format column names for display
                col_display = col.replace('_', ' ').title()
                
                # Special formatting for price
                if col in PRICE_COLS and isinstance(value, (int, float)):
                    if value >= 1000000:
                        formatted_value = f"€{value/1000000:.1f}M"
                    elif value >= 1000:
                        formatted_value = f"€{value/1000:.0f}K"
                    else:
                        formatted_value = f"€{value:,.0f}"
                
                # Special formatting for year
                elif col in YEAR_COLS and isinstance(value, (int, float)):
                    formatted_value = str(int(value))
                
                console.print(f"   [cyan]{col_display}:[/] {formatted_value}")

###############################################################################
# 5. Main loop                                                               #
###############################################################################

def main():
    # Configure Gemini API key (hardcoded)
    api_key = "AIzaSyBUMXx4ceUhKJanUduKzWrmNauxrYooIIc"
    genai.configure(api_key=api_key)

    df = load_dataset()
    console = Console()
    console.print(f"[green]Dataset caricato: {df.shape[0]} righe[/]")
    console.print(f"[green]Colonne disponibili: {', '.join(df.columns)}[/]")

    df_head_str = df.head().to_pandas().to_string(index=False)

    while True:
        try:
            q = console.input("[bold blue]\nDomanda > [/] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[green]Arrivederci![/]")
            break
        
        q = q.strip()
        if not q:
            continue
            
        try:
            expr = get_polars_expression(q, df_head_str)
            console.print(f"[cyan]Espressione generata:[/] {expr}")
            
            local_ns = {"df": df, "pl": pl}
            res = eval(expr, {}, local_ns)
            
            if isinstance(res, pl.LazyFrame):
                res = res.collect()
            elif not isinstance(res, pl.DataFrame):
                res = pl.DataFrame({"result": [res]})
            
            cols_used = extract_cols(expr)
            bullets(res, cols_used)
            
        except Exception as e:
            console.print(f"[red]Errore:[/] {e}")

if __name__ == "__main__":
    main()
