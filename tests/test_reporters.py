"""DataSentry raporlayıcı ve CLI entegrasyon testleri."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from datasentry.cli import app
from datasentry.exceptions import ReportError
from datasentry.models import (
    CheckResult,
    CheckStatus,
    Severity,
    ValidationIssue,
    ValidationReport,
    calculate_quality_score,
    format_percentage,
)
from datasentry.reporters import (
    ConsoleReporter,
    HtmlReporter,
    JsonReporter,
    get_reporter,
)
from datasentry.reporters.html_reporter import score_color_class


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dummy_report():
    """Testler için örnek bir ValidationReport üretir."""
    issue1 = ValidationIssue(
        check_id="missing_values",
        column="yas",
        severity=Severity.ERROR,
        message="1 eksik değer bulundu",
        count=1,
        percentage=10.0,
        row_numbers=[2],
        sample_values=[None],
    )
    issue2 = ValidationIssue(
        check_id="outliers",
        column="maas",
        severity=Severity.WARNING,
        message="1 aykırı değer tespit edildi",
        count=1,
        percentage=10.0,
        row_numbers=[4],
        sample_values=[99999],
    )
    res1 = CheckResult(
        name="Eksik Değer Analizi",
        description="Boş hücreleri kontrol eder",
        status=CheckStatus.FAILED,
        issues=[issue1],
    )
    res2 = CheckResult(
        name="Aykırı Değer Analizi",
        description="Uç değerleri kontrol eder",
        status=CheckStatus.WARNING,
        issues=[issue2],
    )
    return ValidationReport(
        file_name="test.csv",
        file_path="/tmp/test.csv",
        file_size_bytes=1024,
        total_rows=10,
        total_columns=2,
        results=[res1, res2],
        execution_time_ms=12.5,
        quality_score=94.5,
    )


# --- 1. Quality Score Testleri ---


def test_quality_score_clean_data():
    """Sıfır hata ve uyarı durumunda skor 100 olmalıdır."""
    res = CheckResult(
        name="Temiz Kontrol",
        description="Sorun yok",
        status=CheckStatus.PASSED,
        issues=[],
    )
    score = calculate_quality_score(total_rows=100, results=[res])
    assert score == 100.0


def test_quality_score_with_errors():
    """Hatalar (ERROR) orantılı olarak 40 katsayısıyla ceza keser."""
    issue = ValidationIssue(
        check_id="missing_values",
        column="ad",
        severity=Severity.ERROR,
        message="Hata",
        count=10,  # 10 / 100 = %10 -> 0.1 * 40 = 4 ceza
    )
    res = CheckResult(
        name="Eksik Kontrol",
        description="Eksik veri",
        status=CheckStatus.FAILED,
        issues=[issue],
    )
    score = calculate_quality_score(total_rows=100, results=[res])
    assert score == 96.0


def test_quality_score_with_warnings():
    """Uyarılar (WARNING) orantılı olarak 15 katsayısıyla ceza keser."""
    issue = ValidationIssue(
        check_id="outliers",
        column="maas",
        severity=Severity.WARNING,
        message="Aykırı değer",
        count=20,  # 20 / 100 = %20 -> 0.2 * 15 = 3 ceza
    )
    res = CheckResult(
        name="Aykırı Kontrol",
        description="Aykırı değerler",
        status=CheckStatus.WARNING,
        issues=[issue],
    )
    score = calculate_quality_score(total_rows=100, results=[res])
    assert score == 97.0


def test_quality_score_schema_level_error():
    """count == 0 olan genel/şema hatalarında sabit 20 puan ceza kesilir."""
    issue = ValidationIssue(
        check_id="schema",
        column="id",
        severity=Severity.ERROR,
        message="Zorunlu sütun bulunamadı",
        count=0,
    )
    res = CheckResult(
        name="Şema Kontrolü",
        description="Şema doğrulaması",
        status=CheckStatus.FAILED,
        issues=[issue],
    )
    score = calculate_quality_score(total_rows=50, results=[res])
    assert score == 80.0


def test_quality_score_bounds():
    """Çok fazla hata durumunda skor 0.0'ın altına düşmemelidir."""
    issues = [
        ValidationIssue(
            check_id="massive_error",
            column=f"col_{i}",
            severity=Severity.ERROR,
            message="Kritik hata",
            count=100,
        )
        for i in range(5)  # 5 * 40 = 200 ceza puanı
    ]
    res = CheckResult(
        name="Büyük Hata",
        description="Tüm satırlar hatalı",
        status=CheckStatus.FAILED,
        issues=issues,
    )
    score = calculate_quality_score(total_rows=100, results=[res])
    assert score == 0.0


# --- 2. Kalite Skoru Renk Sınıfı Testleri ---


def test_score_color_class_valid_high():
    """Geçerli raporda yüksek skor yeşil olmalıdır."""
    assert score_color_class(95.0, is_valid=True) == "score-pass"


def test_score_color_class_valid_medium():
    """Geçerli raporda orta skor sarı olmalıdır."""
    assert score_color_class(75.0, is_valid=True) == "score-warn"


def test_score_color_class_valid_low():
    """Geçerli raporda düşük skor kırmızı olmalıdır."""
    assert score_color_class(60.0, is_valid=True) == "score-fail"


def test_score_color_class_invalid_high_never_green():
    """Kritik hata varken yüksek skor yeşil olmamalıdır (en fazla sarı)."""
    assert score_color_class(95.0, is_valid=False) == "score-warn"


def test_score_color_class_invalid_medium():
    """Kritik hata varken orta skor sarı olmalıdır."""
    assert score_color_class(75.0, is_valid=False) == "score-warn"


def test_score_color_class_invalid_low():
    """Kritik hata varken düşük skor kırmızı kalmalıdır."""
    assert score_color_class(60.0, is_valid=False) == "score-fail"


def test_score_color_class_boundary_90():
    """90.0 eşiğinde (dahil) yeşil olmalıdır."""
    assert score_color_class(90.0, is_valid=True) == "score-pass"
    assert score_color_class(90.0, is_valid=False) == "score-warn"


def test_score_color_class_boundary_70():
    """70.0 eşiğinde (dahil) sarı olmalıdır."""
    assert score_color_class(70.0, is_valid=True) == "score-warn"
    assert score_color_class(70.0, is_valid=False) == "score-warn"


# --- 3. Benzersiz Etkilenen Satır Sayısı Testleri ---


def test_total_affected_rows_unique_deduplication():
    """Aynı satırda iki farklı sütun eksikse, satır bir kez sayılmalıdır."""
    issue_col_a = ValidationIssue(
        check_id="missing_values",
        column="ad",
        severity=Severity.ERROR,
        message="Eksik ad",
        count=2,
        row_numbers=[3, 5],  # 3. satır etkilendi
    )
    issue_col_b = ValidationIssue(
        check_id="missing_values",
        column="yas",
        severity=Severity.ERROR,
        message="Eksik yas",
        count=2,
        row_numbers=[3, 7],  # 3. satır yine etkilendi (aynı satır!)
    )
    res = CheckResult(
        name="Eksik Değer",
        description="Test",
        status=CheckStatus.FAILED,
        issues=[issue_col_a, issue_col_b],
    )
    # Benzersiz satırlar: {3, 5, 7} → 3 satır; naif toplam 4 olurdu
    assert res.total_affected_rows == 3


def test_total_affected_rows_no_row_numbers_uses_count():
    """row_numbers boşsa (şema/tablo düzeyi), count değeri yedek olarak kullanılmalıdır."""
    issue = ValidationIssue(
        check_id="schema",
        column="id",
        severity=Severity.ERROR,
        message="Sütun eksik",
        count=5,
        row_numbers=[],
    )
    res = CheckResult(
        name="Şema",
        description="Test",
        status=CheckStatus.FAILED,
        issues=[issue],
    )
    assert res.total_affected_rows == 5


def test_total_affected_rows_mixed():
    """row_numbers olan ve olmayan bulgular bir arada doğru toplanmalıdır."""
    issue_with_rows = ValidationIssue(
        check_id="missing_values",
        column="email",
        severity=Severity.ERROR,
        message="Eksik",
        count=2,
        row_numbers=[2, 4],
    )
    issue_schema_level = ValidationIssue(
        check_id="schema",
        column="id",
        severity=Severity.ERROR,
        message="Sütun eksik",
        count=3,
        row_numbers=[],
    )
    res = CheckResult(
        name="Karma",
        description="Test",
        status=CheckStatus.FAILED,
        issues=[issue_with_rows, issue_schema_level],
    )
    # row_numbers'dan 2 benzersiz satır + count yedek 3 = 5
    assert res.total_affected_rows == 5


def test_total_affected_rows_single_issue():
    """Tek bir bulgu için basit benzersiz satır sayısı doğru çalışmalıdır."""
    issue = ValidationIssue(
        check_id="duplicates",
        column=None,
        severity=Severity.ERROR,
        message="Yinelenen satır",
        count=3,
        row_numbers=[2, 4, 6],
    )
    res = CheckResult(
        name="Tekrar",
        description="Test",
        status=CheckStatus.FAILED,
        issues=[issue],
    )
    assert res.total_affected_rows == 3


# --- 4. Yüzde Biçimi Tutarlılığı Testleri ---


def test_format_percentage_two_decimal():
    """format_percentage her zaman 2 ondalık basamak döndürür."""
    assert format_percentage(10.0) == "10.00"
    assert format_percentage(0.95) == "0.95"
    assert format_percentage(100.0) == "100.00"
    assert format_percentage(33.333) == "33.33"


def test_format_percentage_none():
    """None girişi None döndürmelidir."""
    assert format_percentage(None) is None


def test_json_reporter_percentage_format(dummy_report):
    """JSON raporundaki percentage değeri 2 ondalık basamaklı dizi olmalıdır."""
    reporter = JsonReporter()
    data = json.loads(reporter.render(dummy_report))
    for result in data["results"]:
        for issue in result["issues"]:
            if issue["percentage"] is not None:
                # "10.00" gibi olmalı, "10.0" veya 10 değil
                pct_str = issue["percentage"]
                assert isinstance(pct_str, str)
                parts = pct_str.split(".")
                assert len(parts) == 2
                assert len(parts[1]) == 2


def test_html_reporter_percentage_format(dummy_report):
    """HTML raporunda yüzde değerleri %.2f formatında yer almalıdır."""
    reporter = HtmlReporter()
    html = reporter.render(dummy_report)
    # dummy_report'taki issue percentage=10.0 → "%10.00" biçiminde görünmeli
    assert "10.00" in html
    # Eski %.1f formatı olan "10.0)" kalıbı OLMAMALI (parantez içinde)
    assert "(10.0)" not in html


def test_html_score_format(dummy_report):
    """HTML raporu kalite skoru %94.50 biçiminde (2 ondalık) içermelidir."""
    reporter = HtmlReporter()
    html = reporter.render(dummy_report)
    assert "94.50" in html


# --- 5. Dosya Yolu Gizliliği Testleri ---


def test_json_reporter_default_hides_path(dummy_report):
    """JSON raporu varsayılan olarak file_path yerine file_name göstermelidir."""
    reporter = JsonReporter()
    data = json.loads(reporter.render(dummy_report))
    assert data["summary"]["file_path"] == "test.csv"  # file_name değeri
    assert "/tmp/test.csv" not in data["summary"]["file_path"]


def test_json_reporter_show_path(dummy_report):
    """show_path=True olunca JSON tam yolu göstermelidir."""
    reporter = JsonReporter(show_path=True)
    data = json.loads(reporter.render(dummy_report))
    assert data["summary"]["file_path"] == "/tmp/test.csv"


def test_html_reporter_default_hides_path(dummy_report):
    """HTML raporu varsayılan olarak başlıkta yalnızca dosya adı göstermelidir."""
    reporter = HtmlReporter()
    html = reporter.render(dummy_report)
    # Dosya adı görünmeli
    assert "test.csv" in html
    # Tam yol görünmemeli
    assert "/tmp/test.csv" not in html


def test_html_reporter_show_path(dummy_report):
    """show_path=True olunca HTML tam yolu göstermelidir."""
    reporter = HtmlReporter(show_path=True)
    html = reporter.render(dummy_report)
    assert "/tmp/test.csv" in html


def test_cli_show_path_flag(tmp_path, runner):
    """--show-path bayrağıyla JSON çıktısında tam yol yer almalıdır."""
    out_file = tmp_path / "report.json"
    csv_path = Path("samples/valid_sample.csv").resolve()
    result = runner.invoke(
        app,
        ["check", str(csv_path), "-o", str(out_file), "--show-path"],
    )
    assert result.exit_code == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    # Tam yol içermeli (dosya adından uzun)
    assert len(data["summary"]["file_path"]) > len("valid_sample.csv")


# --- 6. Registry ve Reporter Testleri ---


def test_get_reporter_registry():
    """Kayıtlı formatların doğru sınıfları döndürdüğünü doğrular."""
    assert isinstance(get_reporter("json"), JsonReporter)
    assert isinstance(get_reporter("JSON"), JsonReporter)
    assert isinstance(get_reporter("html"), HtmlReporter)
    assert isinstance(get_reporter("terminal"), ConsoleReporter)
    assert isinstance(get_reporter("console"), ConsoleReporter)


def test_get_reporter_unknown():
    """Bilinmeyen format istendiğinde ReportError fırlatılır."""
    with pytest.raises(ReportError, match="Bilinmeyen rapor formatı: 'pdf'"):
        get_reporter("pdf")


def test_json_reporter_render_and_write(dummy_report, tmp_path):
    """JSON raporunun doğru şemayla ve geçerli JSON olarak üretildiğini doğrular."""
    reporter = JsonReporter(indent=2)
    rendered = reporter.render(dummy_report)

    data = json.loads(rendered)
    assert data["datasentry_version"] == "0.4.0"
    assert "timestamp" in data
    assert data["execution_time_ms"] == 12.5
    assert data["quality_score"] == 94.5
    assert data["is_valid"] is False
    assert data["summary"]["total_rows"] == 10
    assert data["summary"]["total_errors"] == 1
    assert data["summary"]["total_warnings"] == 1
    assert len(data["results"]) == 2

    # Dosyaya yazma testi
    out_file = tmp_path / "sub" / "report.json"
    written_path = reporter.write(dummy_report, out_file)
    assert written_path.exists()
    assert json.loads(written_path.read_text(encoding="utf-8")) == data


def test_html_reporter_render_and_offline(dummy_report, tmp_path):
    """HTML raporunun harici CDN bağlantısı olmadan, offline çalıştığını doğrular."""
    reporter = HtmlReporter()
    html_content = reporter.render(dummy_report)

    assert "<!DOCTYPE html>" in html_content
    assert "DataSentry" in html_content
    assert "Kalite Skoru" in html_content
    assert "94.50" in html_content
    assert "Eksik Değer Analizi" in html_content
    assert "Aykırı Değer Analizi" in html_content

    # Çevrimdışı kontrol: harici HTTP/HTTPS linkleri olmamalı
    assert "http://" not in html_content
    assert "https://" not in html_content

    # Dosyaya yazma testi
    out_file = tmp_path / "report.html"
    written_path = reporter.write(dummy_report, out_file)
    assert written_path.exists()
    assert "<!DOCTYPE html>" in written_path.read_text(encoding="utf-8")


def test_html_reporter_xss_protection():
    """CSV'den gelen zararlı girdilerin HTML entity olarak escape edildiğini doğrular."""
    malicious_issue = ValidationIssue(
        check_id="injection_check",
        column="<script>alert('xss')</script>",
        severity=Severity.ERROR,
        message="Hata: <img src=x onerror=alert(1)>",
        count=1,
        row_numbers=[1],
        sample_values=["<svg onload=alert(2)>"],
    )
    res = CheckResult(
        name="Güvenlik Kontrolü",
        description="Açıklama",
        status=CheckStatus.FAILED,
        issues=[malicious_issue],
    )
    report = ValidationReport(
        file_name="malicious.csv",
        file_path="/tmp/malicious.csv",
        total_rows=1,
        total_columns=1,
        results=[res],
    )

    reporter = HtmlReporter()
    html = reporter.render(report)

    # Ham zararlı script tagları yer almamalı, escape edilmeli
    assert "<script>alert('xss')</script>" not in html
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "<svg onload=alert(2)>" not in html
    assert "&lt;svg onload=alert(2)&gt;" in html


def test_console_reporter_render(dummy_report):
    """ConsoleReporter.render metodunun okunabilir metin döndürdüğünü doğrular."""
    reporter = ConsoleReporter()
    text = reporter.render(dummy_report)
    assert "Dosya Ozeti" in text
    assert "Kalite Kontrolleri" in text
    assert "test.csv" in text


# --- 7. CLI Entegrasyon Testleri ---


def test_cli_check_valid_csv(runner):
    """Geçerli CSV kontrol edildiğinde exit code 0 döner."""
    result = runner.invoke(app, ["check", "samples/valid_sample.csv"])
    assert result.exit_code == 0
    assert "0 Kritik Hata" in result.stdout


def test_cli_check_invalid_csv(runner):
    """Hatalı CSV kontrol edildiğinde exit code 1 döner."""
    result = runner.invoke(app, ["check", "samples/invalid_sample.csv"])
    assert result.exit_code == 1
    assert "DOGRULAMA BASARISIZ" in result.stdout


def test_cli_output_auto_detect_html(tmp_path, runner):
    """-o report.html verildiğinde uzantıdan HTML tespit edilip kaydedilir."""
    out_file = tmp_path / "custom_report.html"
    result = runner.invoke(
        app,
        ["check", "samples/valid_sample.csv", "-o", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    assert "<!DOCTYPE html>" in out_file.read_text(encoding="utf-8")


def test_cli_output_auto_detect_json(tmp_path, runner):
    """-o report.json verildiğinde uzantıdan JSON tespit edilip kaydedilir."""
    out_file = tmp_path / "custom_report.json"
    result = runner.invoke(
        app,
        ["check", "samples/valid_sample.csv", "-o", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["is_valid"] is True
    assert data["datasentry_version"] == "0.4.0"


def test_cli_output_unknown_extension(tmp_path, runner):
    """Tanınmayan bir uzantı ve format belirtilmediğinde exit 2 döner."""
    out_file = tmp_path / "report.xyz"
    result = runner.invoke(
        app,
        ["check", "samples/valid_sample.csv", "-o", str(out_file)],
    )
    assert result.exit_code == 2
    output = result.stderr or result.stdout
    assert "Tanınmayan dosya uzantısı" in output


def test_cli_invalid_format(runner):
    """Geçersiz bir format adı verildiğinde exit 2 döner."""
    result = runner.invoke(
        app,
        ["check", "samples/valid_sample.csv", "-f", "xml"],
    )
    assert result.exit_code == 2
    output = result.stderr or result.stdout
    assert "Geçersiz format" in output


def test_cli_json_stdout_pure(runner):
    """-f json ve -q ile -o olmadan çalıştırıldığında stdout sadece saf JSON içermelidir."""
    result = runner.invoke(
        app,
        ["check", "samples/valid_sample.csv", "-f", "json", "-q"],
    )
    assert result.exit_code == 0
    # stdout doğrudan parse edilebilmeli, hiçbir Rich tablosu karışmamalı
    data = json.loads(result.stdout)
    assert data["datasentry_version"] == "0.4.0"
    assert data["is_valid"] is True
    assert data["quality_score"] == 98.5


def test_cli_html_default_output(tmp_path, monkeypatch, runner):
    """-f html verilip -o verilmediğinde varsayılan datasentry_report.html üretilir."""
    sample_file = Path("samples/valid_sample.csv").resolve()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["check", str(sample_file), "-f", "html"],
    )
    assert result.exit_code == 0
    default_html = tmp_path / "datasentry_report.html"
    assert default_html.exists()
    assert "<!DOCTYPE html>" in default_html.read_text(encoding="utf-8")


def test_cli_file_not_found(runner):
    """Olmayan dosya için exit code 2 döner."""
    result = runner.invoke(app, ["check", "samples/non_existent.csv"])
    assert result.exit_code == 2
    output = result.stderr or result.stdout
    assert "Dosya bulunamadı" in output


def test_cli_report_write_error(tmp_path, runner):
    """Rapor yazma esnasında hata oluşursa exit code 2 döner."""
    out_file = tmp_path / "test.json"
    with patch("datasentry.reporters.json_reporter.JsonReporter.write") as mock_write:
        mock_write.side_effect = ReportError("Yazma izni yok")
        result = runner.invoke(
            app,
            ["check", "samples/valid_sample.csv", "-o", str(out_file)],
        )
        assert result.exit_code == 2
        output = result.stderr or result.stdout
        assert "RAPOR YAZMA HATASI" in output
