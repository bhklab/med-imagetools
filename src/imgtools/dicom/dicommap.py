"""Map CSV column names to DICOM standard keywords.

Provides fuzzy suggestion and interactive mapping, with optional
output of a mapping TOML and a CSV with standardized headers.
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from pydicom.datadict import dictionary_description, tag_for_keyword
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from imgtools.dicom.utils import (
    ALL_DICOM_TAGS,
    search_dicom_keywords,
    similar_tags,
)
from imgtools.loggers import logger

console = Console()

_MODALITY_ALIASES = {
    "PET": "PT",
    "PETCT": "PT",
    "PETMR": "PT",
    "MRI": "MR",
    "MRA": "MR",
    "CAT": "CT",
    "CATSCAN": "CT",
    "COMPUTEDTOMOGRAPHY": "CT",
    "XRAY": "DX",
    "XR": "DX",
    "ULTRASOUND": "US",
    "RTSTRUCTURE": "RTSTRUCT",
    "RTSTRUCTURES": "RTSTRUCT",
}


def canonicalize_modality(value: object) -> Optional[str]:
    """Normalize a raw modality value to a canonical DICOM modality code.

    Parameters
    ----------
    value:
        Raw modality-like value (e.g., "pet", "MRI", "rt_struct").

    Returns
    -------
    str | None
        Canonical DICOM modality code if recognized, otherwise None.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # Remove separators and uppercase for robust matching.
    normalized = text.upper().replace(" ", "").replace("-", "").replace("_", "")

    if normalized in _MODALITY_ALIASES:
        return _MODALITY_ALIASES[normalized]
    return None


def _snake_to_camel(name: str) -> str:
    """Convert snake_case or lowercase to CamelCase."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def _tag_description(keyword: str) -> str:
    """Get the DICOM description for a keyword, or empty string."""
    if (tag := tag_for_keyword(keyword)) is not None:
        try:
            return dictionary_description(tag) or ""
        except Exception:
            pass
    return ""


def suggest_dicom_keyword(
    column_name: str,
    top_n: int = 3,
    threshold: float = 0.6,
) -> list[str]:
    """Suggest DICOM keywords for a CSV column name.

    Tries exact match, CamelCase form, then fuzzy match via similar_tags.
    """
    if column_name in ALL_DICOM_TAGS:
        return [column_name]

    camel = _snake_to_camel(column_name)
    if camel in ALL_DICOM_TAGS:
        return [camel]

    candidates = similar_tags(column_name, n=top_n, threshold=threshold)
    for c in similar_tags(camel, n=top_n, threshold=threshold):
        if c not in candidates:
            candidates.append(c)
    return candidates[:top_n]


# ---------------------------------------------------------------------------
# Rich display helpers
# ---------------------------------------------------------------------------

def _make_suggestion_table(suggestions: list[str]) -> Table:
    """Build a Rich table of numbered DICOM keyword suggestions."""
    tbl = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 2),
        expand=True,
    )
    tbl.add_column("#", style="bold cyan", width=4, justify="right")
    tbl.add_column("DICOM Keyword", style="bold green")
    tbl.add_column("Description", style="dim")
    for i, kw in enumerate(suggestions, 1):
        tbl.add_row(str(i), kw, _tag_description(kw))
    return tbl


def _make_summary_table(mapping: dict[str, Optional[str]]) -> Table:
    """Build a Rich summary table of all column mappings."""
    tbl = Table(
        title="Mapping Summary",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    tbl.add_column("CSV Column", style="bold")
    tbl.add_column("DICOM Keyword", style="green")
    tbl.add_column("Status")
    for csv_col, dicom_kw in mapping.items():
        if dicom_kw:
            tbl.add_row(csv_col, dicom_kw, "[green]mapped[/green]")
        else:
            tbl.add_row(csv_col, "—", "[dim]skipped[/dim]")
    return tbl


def _print_column_header(col: str, idx: int, total: int) -> None:
    """Print column header with progress counter."""
    console.print()
    console.print(Rule(style="dim"))
    console.print(
        f"  [bold cyan]Column {idx}/{total}[/bold cyan]"
        f"  [bold white]{col}[/bold white]"
    )
    console.print()


def _prompt_choice(n_suggestions: int, has_suggestions: bool) -> str:
    """Print action hints and read user input."""
    parts: list[str] = []
    if has_suggestions:
        parts.append(f"[cyan]1-{n_suggestions}[/cyan] accept")
    parts.append("[yellow]?[/yellow] search dicom tags")
    parts.append("[dim]Enter[/dim] skip")
    hint = "  " + "  |  ".join(parts)
    console.print(hint)
    console.print()
    return console.input("  [bold]>[/bold] ").strip().lower()


# ---------------------------------------------------------------------------
# Core interactive mapping
# ---------------------------------------------------------------------------

def run_mapping(  # noqa: PLR0912, PLR0915
    csv_path: Path,
    output_mapping: Optional[Path] = None,
    output_csv: Optional[Path] = None,
    *,
    top_n: int = 3,
    threshold: float = 0.75,
    accept_all: bool = False,
    sep: Optional[str] = None,
    encoding: str = "utf-8-sig",
) -> dict[str, Optional[str]]:
    """Load CSV, run interactive mapping, optionally save mapping and CSV.

    Returns the mapping dict: { csv_column_name: DICOM_keyword or None }.
    """
    df = pd.read_csv(csv_path, sep=sep, engine="python", encoding=encoding)
    columns = list(df.columns)
    mapping: dict[str, Optional[str]] = {}
    total = len(columns)

    if not accept_all:
        console.print()
        console.print(
            Panel(
                f"[bold]Mapping {total} CSV columns to DICOM standard[/bold]\n"
                f"Source: [cyan]{csv_path.name}[/cyan]",
                border_style="blue",
            )
        )

    for col_idx, col in enumerate(columns, 1):
        suggestions = suggest_dicom_keyword(col, top_n=top_n, threshold=threshold)

        if accept_all:
            mapping[col] = suggestions[0] if suggestions else None
            logger.info(f"accept_all=True, automatically mapping {col} to {mapping[col]}")
            continue

        _print_column_header(col, col_idx, total)

        if not suggestions:
            console.print("  [dim]No suggestions found.[/dim]")
            console.print()
        else:
            console.print(_make_suggestion_table(suggestions))
            console.print()

        while True:
            raw = _prompt_choice(len(suggestions), bool(suggestions))

            if raw == "":
                mapping[col] = None
                console.print("  [dim]Skipped.[/dim]")
                break

            if raw in ("?", "search dicom tags"):
                result = _interactive_search_tag()
                mapping[col] = result
                if result:
                    console.print(f"  [green]Mapped → {result}[/green]")
                else:
                    console.print("  [dim]Skipped.[/dim]")
                break

            if raw.isdigit() and suggestions:
                idx = int(raw)
                if 1 <= idx <= len(suggestions):
                    chosen = suggestions[idx - 1]
                    mapping[col] = chosen
                    console.print(f"  [green]Mapped → {chosen}[/green]")
                    break

            console.print("  [red]Invalid choice. Try again.[/red]")

    # Summary
    if not accept_all:
        console.print()
        console.print(Rule(style="dim"))
        console.print()
        console.print(_make_summary_table(mapping))
        console.print()

    # Save mapping
    if output_mapping:
        import tomli_w
        out_path = output_mapping.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        toml_mapping = {k: (v or "") for k, v in mapping.items()}
        with out_path.open("wb") as f:
            tomli_w.dump(toml_mapping, f)
        logger.info("Mapping saved.", path=str(out_path))

    # Save CSV
    if output_csv and mapping:
        rename = {k: v for k, v in mapping.items() if v is not None}
        if rename:
            out_path = output_csv.resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_df = df.rename(columns=rename)

            # If a Modality column exists in the output, canonicalize alias values.
            modality_columns = [c for c in out_df.columns if str(c).strip().lower() == "modality"]
            for col in modality_columns:
                before = out_df[col]
                out_df[col] = out_df[col].map(
                    lambda v: canonicalize_modality(v) or v
                )
                changed = int((before != out_df[col]).sum())
                if changed > 0:
                    logger.info(
                        "Canonicalized Modality aliases.",
                        column=str(col),
                        changed_rows=changed,
                    )

            out_df.to_csv(out_path, index=False, encoding="utf-8")
            logger.info("CSV saved.", path=str(out_path))

    return mapping


# ---------------------------------------------------------------------------
# Key reading for live search
# ---------------------------------------------------------------------------

def _read_key() -> Optional[str]:  # noqa: PLR0911, PLR0912
    """Read one key from raw stdin.

    Returns one of: a printable character, or the tokens
    'enter', 'backspace', 'ctrl_c', 'up', 'down', 'escape', 'tab'.
    """
    if not sys.stdin.isatty():
        return None
    try:
        if sys.platform == "win32":
            import msvcrt
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                return "enter"
            if ch in (b"\x08", b"\x7f"):
                return "backspace"
            if ch == b"\x03":
                return "ctrl_c"
            if ch == b"\t":
                return "tab"
            if ch == b"\x1b":
                return "escape"
            if ch in (b"\x00", b"\xe0"):
                ch2 = msvcrt.getch()
                if ch2 == b"H":
                    return "up"
                if ch2 == b"P":
                    return "down"
                return None
            try:
                return ch.decode("utf-8", errors="replace")
            except Exception:
                return ch.decode("cp1252", errors="replace")
        else:
            import os
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                ch = os.read(fd, 1)
                if ch in (b"\r", b"\n"):
                    return "enter"
                if ch in (b"\x7f", b"\x08"):
                    return "backspace"
                if ch == b"\x03":
                    return "ctrl_c"
                if ch == b"\t":
                    return "tab"
                if ch == b"\x1b":
                    # Detect bare Escape vs. arrow-key escape sequences.
                    import select
                    if not select.select([fd], [], [], 0.03)[0]:
                        return "escape"
                    rest = os.read(fd, 2)
                    if rest == b"[A":
                        return "up"
                    if rest == b"[B":
                        return "down"
                    if rest == b"[C":
                        return "right"
                    if rest == b"[D":
                        return "left"
                    return None  # unknown escape sequence
                return ch.decode("utf-8", errors="replace")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Live search with arrow-key selection (fzf-style)
# ---------------------------------------------------------------------------

def _make_search_panel(
    query: str,
    matches: list[tuple[str, str]],
    cursor: int,
    top_n: int,
) -> Panel:
    """Build the Rich panel for the live search + selection view."""
    tbl = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 2),
        expand=True,
    )
    tbl.add_column(" ", width=3, justify="center")
    tbl.add_column("DICOM Keyword")
    tbl.add_column("Description", style="dim")

    for i, (kw, desc) in enumerate(matches[:top_n]):
        if i == cursor:
            marker = "[bold cyan]>[/bold cyan]"
            kw_styled = f"[bold reverse green] {kw} [/bold reverse green]"
            desc_styled = f"[bold]{desc}[/bold]" if desc else ""
        else:
            marker = " "
            kw_styled = f"[green]{kw}[/green]"
            desc_styled = desc or ""
        tbl.add_row(marker, kw_styled, desc_styled)

    if not matches and query:
        tbl.add_row("", "[dim]No matches[/dim]", "")
    elif not query:
        tbl.add_row("", "[dim]Type to search DICOM tags…[/dim]", "")

    title = Text.assemble(
        ("Search: ", "bold"),
        (query or " ", "underline cyan"),
        ("▌", "blink"),
    )
    subtitle = Text.assemble(
        ("Up/Down", "bold"),
        (" navigate  ", "dim"),
        ("Enter", "bold"),
        (" select  ", "dim"),
        ("Esc", "bold"),
        (" cancel", "dim"),
    )

    return Panel(tbl, title=title, subtitle=subtitle, border_style="blue")


def _interactive_search_tag() -> Optional[str]:  # noqa: PLR0911, PLR0912
    """fzf-style live search: type to filter, arrow keys to move, Enter to select."""
    console.print()

    if not sys.stdin.isatty():
        query = console.input("  Search DICOM tags: ").strip()
        if not query:
            return None
        non_tty_matches = search_dicom_keywords(query, max_results=25)
        if not non_tty_matches:
            return None
        # Fallback for non-tty: number selection
        for i, (kw, desc) in enumerate(non_tty_matches, 1):
            console.print(f"  [{i}] {kw}  {desc}")
        raw = console.input("  Pick (1-N, s=skip): ").strip().lower()
        if raw.isdigit() and 1 <= int(raw) <= len(non_tty_matches):
            return non_tty_matches[int(raw) - 1][0]
        return None

    query = ""
    top_n = 15
    cursor = 0
    matches: list[tuple[str, str]] = []

    try:
        with Live(
            _make_search_panel(query, matches, cursor, top_n),
            refresh_per_second=4,
            transient=True,
            auto_refresh=False,
        ) as live:
            while True:
                key = _read_key()
                if key is None:
                    continue

                if key in {"ctrl_c", "escape"}:
                    raise KeyboardInterrupt

                if key == "enter":
                    if matches and 0 <= cursor < len(matches[:top_n]):
                        return matches[cursor][0]
                    # Enter with no matches = cancel
                    return None

                if key == "up":
                    if cursor > 0:
                        cursor -= 1
                    live.update(
                        _make_search_panel(query, matches, cursor, top_n),
                        refresh=True,
                    )
                    continue

                if key == "down":
                    if cursor < len(matches[:top_n]) - 1:
                        cursor += 1
                    live.update(
                        _make_search_panel(query, matches, cursor, top_n),
                        refresh=True,
                    )
                    continue

                # Typing
                if key == "backspace":
                    query = query[:-1]
                elif len(key) == 1 and key.isprintable():
                    query += key

                matches = search_dicom_keywords(query, max_results=top_n)
                cursor = 0  # reset to top when query changes
                live.update(
                    _make_search_panel(query, matches, cursor, top_n),
                    refresh=True,
                )

    except KeyboardInterrupt:
        return None
