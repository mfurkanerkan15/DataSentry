"""DataSentry JSON raporlayıcısı."""

import json

from datasentry import __version__
from datasentry.models import ValidationReport, format_percentage
from datasentry.reporters.base import BaseReporter, register_reporter


@register_reporter("json")
class JsonReporter(BaseReporter):
    """JSON formatında rapor üreten raporlayıcı."""

    def __init__(self, indent: int = 2, show_path: bool = False) -> None:
        self.indent = indent
        self.show_path = show_path

    def render(self, report: ValidationReport) -> str:
        """Raporu okunabilir ve kararlı şemalı bir JSON dizgisine dönüştürür."""
        display_path = report.file_path if self.show_path else report.file_name
        data = {
            "datasentry_version": __version__,
            "timestamp": report.timestamp.isoformat(),
            "execution_time_ms": report.execution_time_ms,
            "quality_score": report.quality_score,
            "is_valid": report.is_valid,
            "summary": {
                "file_name": report.file_name,
                "file_path": display_path,
                "file_size_bytes": report.file_size_bytes,
                "file_size_human": report.file_size_human,
                "total_rows": report.total_rows,
                "total_columns": report.total_columns,
                "total_errors": report.total_errors,
                "total_warnings": report.total_warnings,
            },
            "results": [
                {
                    "name": r.name,
                    "description": r.description,
                    "status": r.status.value,
                    "total_affected_rows": r.total_affected_rows,
                    "issues": [
                        {
                            "check_id": i.check_id,
                            "column": i.column,
                            "severity": i.severity.value,
                            "message": i.message,
                            "count": i.count,
                            "percentage": format_percentage(i.percentage),
                            "row_numbers": i.row_numbers,
                            "sample_values": i.sample_values,
                        }
                        for i in r.issues
                    ],
                }
                for r in report.results
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=self.indent)
