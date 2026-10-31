"""Tekrarlanan (yinelenen) satır kontrol modülü."""

import pandas as pd

from datasentry.models import CheckResult, CheckStatus, Severity, ValidationIssue


def check_duplicate_rows(
    df: pd.DataFrame, max_row_samples: int = 100
) -> CheckResult:
    """CSV veri setindeki yinelenen satırları ve hangi satırla eşleştiklerini analiz eder."""
    total_rows = len(df)
    issues: list[ValidationIssue] = []

    if total_rows == 0:
        return CheckResult(
            name="Tekrarlanan Kayit Kontrolu",
            description="Birebir ayni olan satirlari tespit eder",
            status=CheckStatus.PASSED,
            issues=[],
        )

    # Tüm tekrarların grubunu bulmak için keep=False kullanıyoruz
    duplicate_mask = df.duplicated(keep=False)

    if duplicate_mask.any():
        duplicated_df = df[duplicate_mask]

        # Birebir aynı olan satırları grupluyoruz (NaN'lerin elenmemesi için dropna=False)
        grouped = duplicated_df.groupby(
            list(df.columns), observed=True, sort=False, dropna=False
        )

        matches_dict: dict[int, int] = {}  # {Kopya Satır: Orijinal Satır}
        dup_sample: list[str] = []

        for _, group in grouped:
            # CSV başlık = 1, ilk veri = 2
            positions = (group.index + 2).tolist()
            original_row = positions[0]      # İlk görülen orijinal satır
            duplicate_rows = positions[1:]   # Kopya satırlar

            for dup in duplicate_rows:
                matches_dict[dup] = original_row

            # Örnek olarak ilk tekrarın metin özetini alıyoruz
            if len(dup_sample) < 5:
                sample_str = " | ".join(str(val) for val in group.iloc[0].values)
                dup_sample.append(f"({duplicate_rows[0]} -> {original_row}): [{sample_str}]")

        # Satır numaralarını küçükten büyüğe sıralıyoruz (72, 119, 297)
        dup_rows = sorted(matches_dict.keys())
        dup_count = len(dup_rows)
        pct = round((dup_count / total_rows) * 100, 2)

        # Temiz ve kısa eşleşme formatı: (Kopya -> Orijinal)
        dup_pairs = [f"({dup} -> {matches_dict[dup]})" for dup in dup_rows]

        # Satır sınırlaması
        if max_row_samples and len(dup_rows) > max_row_samples:
            dup_rows = dup_rows[:max_row_samples]
            dup_pairs = dup_pairs[:max_row_samples]
            truncated_msg = f" (İlk {max_row_samples} satır detaylandırıldı)"
        else:
            truncated_msg = ""

        # Detaylı mesaj oluşturma
        pairs_str = ", ".join(dup_pairs[:5])
        if len(dup_pairs) > 5:
            pairs_str += f" ve {len(dup_pairs) - 5} eşleşme daha..."

        issues.append(
            ValidationIssue(
                check_id="duplicate_rows",
                column=None,
                severity=Severity.ERROR,
                message=(
                    f"Veri setinde {dup_count} adet yinelenen satir (%{pct}) bulundu. "
                    f"Eşleşmeler (Kopya -> Orijinal): [{pairs_str}]{truncated_msg}"
                ),
                count=dup_count,
                percentage=pct,
                row_numbers=dup_rows,
                sample_values=dup_sample,
            )
        )

    status = CheckStatus.FAILED if len(issues) > 0 else CheckStatus.PASSED

    return CheckResult(
        name="Tekrarlanan Kayit Kontrolu",
        description="Birebir ayni olan satirlari tespit eder",
        status=status,
        issues=issues,
    )
