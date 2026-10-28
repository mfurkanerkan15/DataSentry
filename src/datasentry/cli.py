"""DataSentry CLI — giriş ve sunum katmanı."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datasentry import __version__
from datasentry.exceptions import DataSentryError
from datasentry.loader import get_file_summary, load_csv

app = typer.Typer(
    name="datasentry",
    help="CSV Data Quality & Validation CLI",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool) -> None:
    """Sürüm bilgisini gösterir ve çıkar."""
    if value:
        console.print(f"[bold green]DataSentry[/bold green] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Sürüm bilgisini göster.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """[bold green]DataSentry[/bold green] — CSV Data Quality & Validation CLI."""


@app.command()
def check(
    file: Path = typer.Argument(
        ...,
        help="Kontrol edilecek CSV dosyasının yolu.",
        exists=False,  # Kendi hata mesajlarımızı kullanacağız
    ),
    encoding: str = typer.Option(
        "utf-8",
        "--encoding",
        "-e",
        help="Dosya karakter kodlaması.",
    ),
    delimiter: str = typer.Option(
        ",",
        "--delimiter",
        "-d",
        help="Sütun ayırıcı karakter.",
    ),
) -> None:
    """CSV dosyasını yükler ve temel bilgileri gösterir."""
    console.print()
    console.print(
        Panel(
            f"[bold]Dosya:[/bold] {file}",
            title="[bold green]DataSentry Check[/bold green]",
            border_style="green",
        )
    )

    # CSV yükleme
    try:
        df = load_csv(str(file), encoding=encoding, delimiter=delimiter)
    except DataSentryError as e:
        console.print(f"\n[bold red]HATA:[/bold red] {e}")
        raise typer.Exit(code=1)

    # Dosya özeti
    summary = get_file_summary(df, str(file))

    # Özet tablosu
    info_table = Table(
        title="Dosya Özeti",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    info_table.add_column("Özellik", style="bold")
    info_table.add_column("Değer", style="white")

    info_table.add_row("Dosya Adı", summary["dosya_adi"])
    info_table.add_row("Boyut", f"{summary['dosya_boyutu_kb']} KB")
    info_table.add_row("Satır Sayısı", str(summary["satir_sayisi"]))
    info_table.add_row("Sütun Sayısı", str(summary["sutun_sayisi"]))

    console.print()
    console.print(info_table)

    # Sütun listesi
    col_table = Table(
        title="Sütunlar",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    col_table.add_column("#", style="dim", width=4)
    col_table.add_column("Sütun Adı", style="bold")
    col_table.add_column("Veri Tipi", style="yellow")

    for i, col in enumerate(df.columns, 1):
        col_table.add_row(str(i), col, str(df[col].dtype))

    console.print()
    console.print(col_table)
    console.print()
    console.print("[bold green]OK[/bold green] Dosya basariyla yuklendi.\n")


if __name__ == "__main__":
    app()
