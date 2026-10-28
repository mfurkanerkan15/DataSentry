"""DataSentry CLI — giriş ve sunum katmanı."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datasentry import __version__
from datasentry.engine import run_validations
from datasentry.exceptions import DataSentryError
from datasentry.loader import get_file_summary, load_csv
from datasentry.models import CheckStatus, Severity, ValidationReport

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


def format_rows(row_numbers: list[int], max_display: int = 5) -> str:
    """Satır numaralarını okunabilir formatta biçimlendirir."""
    if not row_numbers:
        return "-"
    if len(row_numbers) <= max_display:
        return ", ".join(str(r) for r in row_numbers)
    displayed = ", ".join(str(r) for r in row_numbers[:max_display])
    remaining = len(row_numbers) - max_display
    return f"{displayed} ... (+{remaining} satir)"


def render_report(report: ValidationReport, summary: dict) -> None:
    """Doğrulama sonuçlarını Rich ile terminale basar."""
    # 1. Dosya Özeti Tablosu
    info_table = Table(
        title="Dosya Ozeti",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    info_table.add_column("Ozellik", style="bold")
    info_table.add_column("Deger", style="white")

    info_table.add_row("Dosya Adi", summary["dosya_adi"])
    info_table.add_row("Boyut", report.file_size_human)
    info_table.add_row("Satir Sayisi", str(summary["satir_sayisi"]))
    info_table.add_row("Sutun Sayisi", str(summary["sutun_sayisi"]))
    console.print()
    console.print(info_table)

    # 2. Kalite Kontrol Özeti Tablosu
    check_table = Table(
        title="Kalite Kontrolleri",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    check_table.add_column("Kontrol", style="bold")
    check_table.add_column("Durum", justify="center")
    check_table.add_column("Etkilenen Kayit", justify="right")

    for result in report.results:
        if result.status == CheckStatus.PASSED:
            status_text = "[bold green]PASSED[/bold green]"
            count_text = "[green]0 kayit[/green]"
        elif result.status == CheckStatus.WARNING:
            status_text = "[bold yellow]WARNING[/bold yellow]"
            count_text = f"[yellow]{result.total_affected_rows} kayit[/yellow]"
        else:
            status_text = "[bold red]FAILED[/bold red]"
            count_text = f"[red]{result.total_affected_rows} kayit[/red]"

        check_table.add_row(
            result.name,
            status_text,
            count_text,
        )

    console.print()
    console.print(check_table)

    # 3. Bulunan Sorunların Detay Tablosu (varsa)
    all_issues = [issue for r in report.results for issue in r.issues]
    if all_issues:
        issues_table = Table(
            title="Tespit Edilen Bulgular, Uyarilar ve Satir Konumlari",
            show_header=True,
            header_style="bold magenta",
            border_style="dim",
        )
        issues_table.add_column("Onem", justify="center", width=8)
        issues_table.add_column("Sutun", style="bold", width=12)
        issues_table.add_column("Mesaj", min_width=30)
        issues_table.add_column("Satirlar (Excel/CSV)", style="cyan", width=24)

        for issue in all_issues:
            if issue.severity == Severity.ERROR:
                sev_text = "[bold red]ERROR[/bold red]"
            elif issue.severity == Severity.WARNING:
                sev_text = "[bold yellow]WARN[/bold yellow]"
            else:
                sev_text = "[bold cyan]INFO[/bold cyan]"

            col_name = issue.column if issue.column else "-"
            rows_text = format_rows(issue.row_numbers)

            issues_table.add_row(sev_text, col_name, issue.message, rows_text)

        console.print()
        console.print(issues_table)

    # 4. Genel Sonuç Paneli
    console.print()
    if report.is_valid:
        if report.total_warnings > 0:
            console.print(
                Panel(
                    f"[bold yellow]DOGRULAMA TAMAMLANDI (UYARILARLA):[/bold yellow] 0 Kritik Hata, {report.total_warnings} Uyari.",
                    border_style="yellow",
                )
            )
        else:
            console.print(
                Panel(
                    "[bold green]TUM KONTROLLER BASARILI:[/bold green] Veri setinde kalite sorunu bulunamadi.",
                    border_style="green",
                )
            )
    else:
        console.print(
            Panel(
                f"[bold red]DOGRULAMA BASARISIZ:[/bold red] {report.total_errors} Kritik Hata, {report.total_warnings} Uyari tespit edildi.",
                border_style="red",
            )
        )
    console.print()


@app.command()
def check(
    file: Path = typer.Argument(
        ...,
        help="Kontrol edilecek CSV dosyasının yolu.",
        exists=False,
    ),
    encoding: str = typer.Option(
        "utf-8-sig",
        "--encoding",
        "-e",
        help="Dosya karakter kodlaması (varsayılan: utf-8-sig).",
    ),
    delimiter: str = typer.Option(
        ",",
        "--delimiter",
        "-d",
        help="Sütun ayırıcı karakter.",
    ),
    max_samples: int = typer.Option(
        100,
        "--max-samples",
        "-m",
        help="Raporda gösterilecek maksimum örnek/satır sayısı.",
    ),
) -> None:
    """CSV dosyasını yükler, kalite kontrollerinden geçirir ve raporlar."""
    console.print()
    console.print(
        Panel(
            f"[bold]Dosya:[/bold] {file}",
            title="[bold green]DataSentry Check[/bold green]",
            border_style="green",
        )
    )

    try:
        df = load_csv(str(file), encoding=encoding, delimiter=delimiter)
    except DataSentryError as e:
        console.print(f"\n[bold red]HATA:[/bold red] {e}\n")
        raise typer.Exit(code=1)

    summary = get_file_summary(df, str(file))
    report = run_validations(df, str(file), max_row_samples=max_samples)
    render_report(report, summary)

    if not report.is_valid:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()