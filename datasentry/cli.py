"""DataSentry CLI — giriş ve sunum katmanı."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from datasentry import __version__
from datasentry.config import ConfigError, load_config
from datasentry.engine import run_validations
from datasentry.exceptions import DataSentryError, ReportError
from datasentry.loader import get_file_summary, load_csv
from datasentry.models import ValidationReport
from datasentry.reporters import ConsoleReporter, format_rows, get_reporter

__all__ = ["app", "check", "format_rows", "main", "render_report"]

app = typer.Typer(
    name="datasentry",
    help="CSV Data Quality & Validation CLI",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


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


def render_report(report: ValidationReport, summary: dict) -> None:
    """Doğrulama sonuçlarını Rich ile terminale basar (Geriye dönük uyumluluk)."""
    ConsoleReporter(console=console).print_report(report, summary)


def _resolve_format_and_output(
    format_opt: str | None,
    output_opt: Path | None,
) -> tuple[str, Path | None]:
    """Çıktı formatını ve hedef dosya yolunu belirler."""
    valid_formats = {"terminal", "console", "json", "html"}

    if format_opt is not None:
        fmt = format_opt.strip().lower()
        if fmt not in valid_formats:
            err_console.print(
                f"[bold red]HATA:[/bold red] Geçersiz format '{format_opt}'. "
                f"Desteklenen formatlar: terminal, json, html"
            )
            raise typer.Exit(code=2)
    else:
        fmt = None

    target_output = output_opt
    if output_opt is not None:
        suffix = output_opt.suffix.lower()
        if fmt is None:
            if suffix == ".json":
                fmt = "json"
            elif suffix in {".html", ".htm"}:
                fmt = "html"
            else:
                err_console.print(
                    f"[bold red]HATA:[/bold red] Tanınmayan dosya uzantısı '{suffix}'. "
                    f"Desteklenen uzantılar: .html, .json veya --format belirtin."
                )
                raise typer.Exit(code=2)
    else:
        if fmt is None:
            fmt = "terminal"
        elif fmt == "html":
            # -f html verilmiş ama -o verilmemişse mantıklı varsayılan dosya
            target_output = Path("datasentry_report.html")

    return fmt, target_output


@app.command()
def check(
    file: Path = typer.Argument(
        ...,
        help="Kontrol edilecek CSV dosyasının yolu.",
        exists=False,
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="YAML yapılandırma dosyasının yolu.",
        exists=True,
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
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Raporun kaydedileceği dosya yolu (.json veya .html).",
    ),
    format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help=(
            "Çıktı formatı: terminal, json, html (varsayılan: terminal veya -o uzantısına göre). "
            "'-f html' verilip -o belirtilmezse varsayılan 'datasentry_report.html' üretilir."
        ),
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help=(
            "Terminal tablosunu gizler. '-f json' ile -o olmadan kullanılırsa "
            "JSON'u doğrudan stdout'a basar."
        ),
    ),
    show_path: bool = typer.Option(
        False,
        "--show-path",
        help=(
            "Rapor başlığında ve JSON çıktısında tam dosya yolunu gösterir. "
            "Varsayılan olarak yalnızca dosya adı görüntülenir."
        ),
    ),
) -> None:
    """CSV dosyasını yükler, kalite kontrollerinden geçirir ve raporlar."""
    fmt, target_output = _resolve_format_and_output(format, output)
    is_json_stdout = fmt == "json" and target_output is None

    # Terminal başlığını sadece görsel modda bas
    if not quiet and not is_json_stdout:
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
        err_console.print(f"\n[bold red]HATA:[/bold red] {e}\n")
        raise typer.Exit(code=2)

    ds_config = None
    if config:
        try:
            ds_config = load_config(config)
            if not quiet and not is_json_stdout:
                console.print(f"[bold cyan]INFO:[/bold cyan] Yapılandırma yüklendi: {config}")
        except ConfigError as e:
            err_console.print(f"\n[bold red]YAPILANDIRMA HATASI:[/bold red]\n{e}\n")
            raise typer.Exit(code=2)

    summary = get_file_summary(df, str(file))
    report = run_validations(
        df, str(file), max_row_samples=max_samples, config=ds_config
    )

    # 1. Dosyaya rapor kaydetme (varsa)
    if target_output is not None:
        try:
            reporter = get_reporter(fmt, show_path=show_path)
            saved_path = reporter.write(report, target_output)
            if not quiet:
                console.print(f"[bold green]Rapor kaydedildi:[/bold green] {saved_path}")
        except (ReportError, Exception) as e:
            err_console.print(f"\n[bold red]RAPOR YAZMA HATASI:[/bold red]\n{e}\n")
            raise typer.Exit(code=2)

    # 2. JSON stdout basımı (eğer -f json ve -o yoksa)
    if is_json_stdout:
        json_reporter = get_reporter("json", show_path=show_path)
        sys.stdout.write(json_reporter.render(report) + "\n")
        sys.stdout.flush()
    elif not quiet and target_output is None and fmt in {"terminal", "console"}:
        # Terminal çıktısı
        ConsoleReporter(console=console, show_path=show_path).print_report(report, summary)
    elif not quiet and target_output is not None and fmt in {"terminal", "console"}:
        ConsoleReporter(console=console, show_path=show_path).print_report(report, summary)

    if not report.is_valid:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
