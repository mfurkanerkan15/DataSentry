"""DataSentry terminal/konsol raporlayıcısı (Rich tabanlı)."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datasentry.models import CheckStatus, Severity, ValidationReport, format_percentage
from datasentry.reporters.base import BaseReporter, register_reporter


def format_rows(row_numbers: list[int], max_display: int = 5) -> str:
    """Satır numaralarını okunabilir formatta biçimlendirir."""
    if not row_numbers:
        return "-"
    if len(row_numbers) <= max_display:
        return ", ".join(str(r) for r in row_numbers)
    displayed = ", ".join(str(r) for r in row_numbers[:max_display])
    remaining = len(row_numbers) - max_display
    return f"{displayed} ... (+{remaining} satir)"


@register_reporter("terminal", "console")
class ConsoleReporter(BaseReporter):
    """Terminal çıktısı üreten Rich tabanlı raporlayıcı."""

    def __init__(self, console: Console | None = None, show_path: bool = False) -> None:
        self.console = console or Console()
        self.show_path = show_path

    def print_report(
        self, report: ValidationReport, summary: dict | None = None
    ) -> None:
        """Raporu mevcut konsola renkli tablolar halinde yazdırır."""
        self._render_to_console(self.console, report, summary)

    def render(self, report: ValidationReport) -> str:
        """Raporu düz metin formatında oluşturur."""
        buffer_console = Console(record=True, width=100)
        self._render_to_console(buffer_console, report, None)
        return buffer_console.export_text()

    def _render_to_console(
        self,
        cons: Console,
        report: ValidationReport,
        summary: dict | None = None,
    ) -> None:
        file_name = summary["dosya_adi"] if summary else report.file_name
        row_count = str(summary["satir_sayisi"]) if summary else str(report.total_rows)
        col_count = str(summary["sutun_sayisi"]) if summary else str(report.total_columns)
        display_path = report.file_path if self.show_path else report.file_name

        # 1. Dosya Özeti Tablosu
        info_table = Table(
            title="Dosya Ozeti",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
        )
        info_table.add_column("Ozellik", style="bold")
        info_table.add_column("Deger", style="white")

        info_table.add_row("Dosya Adi", file_name)
        info_table.add_row("Yol", display_path)
        info_table.add_row("Boyut", report.file_size_human)
        info_table.add_row("Satir Sayisi", row_count)
        info_table.add_row("Sutun Sayisi", col_count)
        info_table.add_row("Kalite Skoru", f"%{report.quality_score:.2f}")
        cons.print()
        cons.print(info_table)

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

        cons.print()
        cons.print(check_table)

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
                pct = format_percentage(issue.percentage)
                already_in = pct is not None and pct in issue.message
                msg = issue.message if already_in else (
                    f"{issue.message} ({pct}%)" if pct else issue.message
                )

                issues_table.add_row(sev_text, col_name, msg, rows_text)

            cons.print()
            cons.print(issues_table)

        # 4. Genel Sonuç Paneli
        cons.print()
        score_str = f"%{report.quality_score:.2f}"
        if report.is_valid:
            if report.total_warnings > 0:
                cons.print(
                    Panel(
                        f"[bold yellow]DOGRULAMA TAMAMLANDI (UYARILARLA):[/bold yellow] "
                        f"0 Kritik Hata, {report.total_warnings} Uyari. "
                        f"(Kalite Skoru: {score_str})",
                        border_style="yellow",
                    )
                )
            else:
                cons.print(
                    Panel(
                        f"[bold green]TUM KONTROLLER BASARILI:[/bold green] "
                        f"Veri setinde kalite sorunu bulunamadi. "
                        f"(Kalite Skoru: {score_str})",
                        border_style="green",
                    )
                )
        else:
            cons.print(
                Panel(
                    f"[bold red]DOGRULAMA BASARISIZ:[/bold red] "
                    f"{report.total_errors} Kritik Hata, {report.total_warnings} Uyari. "
                    f"(Kalite Skoru: {score_str})",
                    border_style="red",
                )
            )
        cons.print()
