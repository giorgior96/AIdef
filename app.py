from __future__ import annotations

import streamlit as st
import polars as pl
import json
from pathlib import Path
from typing import List, Set, Any, Tuple
import re
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Boat Filter AI",
    page_icon="🚤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .boat-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .price-highlight {
        font-weight: bold;
        color: #28a745;
    }
    .year-highlight {
        font-weight: bold;
        color: #007bff;
    }
    .stButton > button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #0056b3;
    }
    mark {
        background-color: #fffa65;
        padding: 0 4px;
    }
</style>
""", unsafe_allow_html=True)

###############################################################################
# Data Loading and Processing Functions
###############################################################################

@st.cache_data
def load_dataset(fp: str | Path = "output_with_contact.json") -> pl.DataFrame:
    """Load the boat dataset with caching for performance."""
    try:
        data = json.loads(Path(fp).read_text(encoding="utf-8"))
        return pl.DataFrame(data)
    except FileNotFoundError:
        st.error(f"Dataset file '{fp}' not found. Please ensure the file exists in the same directory.")
        return pl.DataFrame()
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return pl.DataFrame()

# Column mappings for consistent display
NAME_COLS = ["boat_name", "Nome della barca", "boatName", "name", "title"]
PRICE_COLS = ["price", "Price", "prezzo", "cost"]
YEAR_COLS = ["year", "Year", "anno", "build_year", "construction_year"]
BRAND_COLS = ["brand", "Brand", "marca", "manufacturer", "make"]
LOCATION_COLS = ["location", "Location", "luogo", "region", "area", "port"]

def extract_cols(expr: str) -> List[str]:
    """Extract column names from Polars expression."""
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

def format_value(value: Any, col_name: str) -> str:
    """Format values for display with special handling for price and year."""
    if value is None:
        return "N/A"
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        
        # Special formatting for price
        if col_name in PRICE_COLS:
            if value >= 1000000:
                return f"€{value/1000000:.1f}M"
            elif value >= 1000:
                return f"€{value/1000:.0f}K"
            else:
                return f"€{value:,.0f}"
        
        # Special formatting for year
        elif col_name in YEAR_COLS:
            return str(value)
        
        return str(value)
    else:
        return str(value)

def extract_number_spans(text: str) -> List[Tuple[str, int, int]]:
    """Return numbers in the text along with their spans."""
    pattern = r"\b\d+(?:[.,]\d+)?\b"
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(pattern, text)]


def highlight_numbers_html(text: str) -> str:
    """Wrap numbers in <mark> tags for highlighting."""
    pattern = r"(\b\d+(?:[.,]\d+)?\b)"
    return re.sub(pattern, r"<mark>\1</mark>", text)


###############################################################################
# Session State Helpers
###############################################################################

def apply_pending_query_update() -> None:
    """Apply pending query update before widgets are created."""
    if "updated_query" in st.session_state:
        st.session_state["query_input"] = st.session_state.pop("updated_query")

###############################################################################
# AI Integration Functions
###############################################################################

INSTRUCTION_STR = (
    "1. Convert the query to executable Python code using **Polars** (not pandas). DO NOT use the option case sensitive\n"
    "2. The final line must be a Python expression that can be passed to eval().\n"
    "3. DO NOT use the option case sensitive\n"
    "3. It **must return a pl.DataFrame** (use head() if necessary).\n"
    "4. PRINT ONLY THE EXPRESSION, no extra text or formatting.\n"
    "5. Do not wrap the expression in quotes or markdown.\n"
    "6. Use `df.filter(<boolean>)`, `pl.lit`, or the lazy API; **avoid** `df[bool_mask]` row‑filter syntax.\n"
    "7. **IMPORTANT**: If the query mentions a specific brand name (like 'Azimut', 'Ferretti', 'Princess', etc.), "
    "you MUST filter by that brand. Look for brand information in columns like 'brand', 'manufacturer', 'make', "
    "or check if the brand name appears in the boat name. Use case-insensitive matching with `str.contains()`.\n"
    "8. For brand filtering, use: `df.filter(pl.col('brand').str.contains('brand_name'))` "
    "or similar pattern matching.\n"
    "9. For location filtering, use: `df.filter(pl.col('location').str.contains('location_name'))` do not use the option case sensitive "
    "or similar pattern matching.\n"
    "10. Combine filters using `&` (AND) operator.\n"
    "11. For case-insensitive substring search in Polars, use a regex pattern with (?i) at the start, e.g. pl.col('brand').str.contains('(?i)azimut'). Do NOT use a case_insensitive argument in .str.contains.\n"
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

def get_polars_expression(
    query: str,
    df_sample: str,
    model: str = "gemini-2.5-flash",
    error: str | None = None,
) -> str:
    """Generate Polars expression from natural language query using Gemini.

    If ``error`` is provided, it will be shown to the model so that it can
    correct the previous attempt.
    """
    try:
        prompt = PROMPT_TEMPLATE.format(
            df_str=df_sample, instructions=INSTRUCTION_STR, query=query
        )
        if error:
            prompt += (
                "\nThe previous expression produced the following error:\n"
                f"{error}\nPlease provide a corrected Polars expression."
            )

        model_obj = genai.GenerativeModel(model)
        resp = model_obj.generate_content(prompt, generation_config={"temperature": 0})
        expr = resp.text.strip()
        if expr.startswith("```"):
            expr = expr.strip("`\n").removeprefix("python").strip()
        return expr
    except Exception as e:
        st.error(f"Error generating expression: {e}")
        return ""

def query_boats(
    df: pl.DataFrame,
    query: str,
    model: str = "gemini-2.5-flash",
    max_retries: int = 2,
) -> Tuple[str, pl.DataFrame, List[str]]:
    """Query boats using AI and return results.

    The function will attempt to regenerate the Polars expression if the first
    attempt fails due to a Python or Polars error.
    """
    if df.is_empty():
        return "", pl.DataFrame(), []

    df_head_str = df.head().to_pandas().to_string(index=False)

    error: str | None = None
    expr = ""

    for _ in range(max_retries + 1):
        expr = get_polars_expression(query, df_head_str, model, error)

        if not expr:
            return "", pl.DataFrame(), []

        try:
            compile(expr, "<string>", "eval")
            local_ns = {"df": df, "pl": pl}
            res = eval(expr, {}, local_ns)

            if isinstance(res, pl.LazyFrame):
                res = res.collect()
            elif not isinstance(res, pl.DataFrame):
                res = pl.DataFrame({"result": [res]})

            cols_used = extract_cols(expr)
            show_cols = get_display_columns(res, cols_used)

            # Limit results to top 20 for better performance
            res = res.head(20)

            return expr, res, show_cols
        except Exception as e:
            error = str(e)

    # If we reach here, all attempts failed
    with st.expander("🔍 Generated Query", expanded=False):
        st.code(expr or "", language="python")
    st.error(f"Error executing query: {error}")
    return expr, pl.DataFrame(), []

###############################################################################
# UI Components
###############################################################################

def display_boat_card(row: dict, display_cols: List[str]):
    """Display a single boat as a card."""
    name_col = next((c for c in NAME_COLS if c in display_cols), None)
    boat_name = row.get(name_col, "Boat") if name_col else "Boat"
    
    with st.container():
        st.markdown(f"""
        <div class="boat-card">
            <h4 style="color: #1f77b4; margin-bottom: 0.5rem;">{boat_name}</h4>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        col_idx = 0
        
        for col in display_cols:
            if col == name_col:
                continue
                
            if col in row and row[col] is not None:
                value = format_value(row[col], col)
                col_display = col.replace('_', ' ').title()
                
                # Determine styling based on column type
                if col in PRICE_COLS:
                    value_display = f"<span class='price-highlight'>{value}</span>"
                elif col in YEAR_COLS:
                    value_display = f"<span class='year-highlight'>{value}</span>"
                else:
                    value_display = value
                
                with cols[col_idx % 3]:
                    st.markdown(f"**{col_display}:** {value_display}", unsafe_allow_html=True)
                
                col_idx += 1
        
        st.markdown("</div>", unsafe_allow_html=True)

def display_results(expr: str, results_df: pl.DataFrame, display_cols: List[str]):
    """Display query results in a nice format."""
    if results_df.is_empty():
        st.warning("No boats found matching your criteria.")
        return
    
    # Show the generated expression
    with st.expander("🔍 Generated Query", expanded=False):
        st.code(expr, language="python")
    
    # Show results count
    st.success(f"Found {len(results_df)} boats matching your criteria")
    
    # Display results
    for row in results_df.rows(named=True):
        display_boat_card(row, display_cols)

###############################################################################
# Main Application
###############################################################################

def main():
    # Apply pending query updates before widgets are created
    apply_pending_query_update()

    # Configure Gemini API key from environment
    api_key = os.getenv("GEMINI_API_KEYS")
    genai.configure(api_key=api_key)
    
    # Header
    st.markdown('<h1 class="main-header">🚤 Boat Filter AI</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Find your perfect boat using natural language queries</p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        model = st.selectbox(
            "AI Model",
            ["gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"],
            help="Choose the Gemini model to use"
        )
        
        # Dataset info
        st.header("📊 Dataset Info")
        df = load_dataset()
        if not df.is_empty():
            st.write(f"**Total boats:** {len(df)}")
            st.write(f"**Columns:** {len(df.columns)}")
            
            # Show available columns
            with st.expander("Available Columns"):
                for col in df.columns:
                    st.write(f"• {col}")
    
    # Main content area
    if df.is_empty():
        st.error("Unable to load boat dataset. Please check the file path.")
        return
    
    # Query input
    st.header("🔍 Search Boats")
    
    # Example queries
    with st.expander("💡 Example Queries"):
        st.write("Try these example queries:")
        examples = [
            "Show me boats under €500,000",
            "Find boats built after 2020",
            "Show me boats with max speed over 30 knots",
            "Find boats between 10 and 15 meters long",
            "Show me the most expensive boats",
            "Find boats with diesel engines",
            "Best Azimut boat under 500k",
            "Show me Ferretti boats",
            "Princess boats under 1 million",
            "Boats in Liguria",
            "Boats in Sardinia"
        ]
        for example in examples:
            if st.button(example, key=f"example_{example}"):
                st.session_state["query"] = example
                st.session_state["query_input"] = example

    # Query input
    query = st.text_area(
        "Describe what you're looking for:",
        value=st.session_state.get("query_input", ""),
        key="query_input",
        placeholder="e.g., Best Azimut boat under €500,000 or boats in Liguria",
        height=100,
        help="Describe your boat requirements in natural language"
    )

    # Detect and highlight numeric values so they can be edited
    numbers = extract_number_spans(st.session_state.get("query_input", ""))
    if numbers:
        st.markdown("**Edit numeric values:**")
        new_vals = []
        for idx, (num, _start, _end) in enumerate(numbers):
            key = f"num_input_{idx}"
            try:
                val = float(num.replace(",", "."))
            except ValueError:
                val = 0.0
            new_val = st.number_input(f"Value {idx+1}", value=val, key=key)
            if float(new_val).is_integer():
                new_vals.append(str(int(new_val)))
            else:
                new_vals.append(str(new_val))

        updated_query = st.session_state["query_input"]
        for (num, start, end), new_val in zip(reversed(numbers), reversed(new_vals)):
            updated_query = updated_query[:start] + new_val + updated_query[end:]

        if updated_query != st.session_state["query_input"]:
            st.session_state["updated_query"] = updated_query
            st.experimental_rerun()

        st.markdown(highlight_numbers_html(st.session_state.get("query_input", "")), unsafe_allow_html=True)
    
    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔍 Search Boats", use_container_width=True)
    
    # Process query
    if search_button and st.session_state["query_input"].strip():
        with st.spinner("🤖 AI is analyzing your query..."):
            expr, results_df, display_cols = query_boats(df, st.session_state["query_input"].strip(), model)
            display_results(expr, results_df, display_cols)
    elif not search_button:
        st.header("📋 Sample Data")
        st.write("Here's a preview of the available boat data:")
        st.dataframe(df.head(5), use_container_width=True)

if __name__ == "__main__":
    main() 