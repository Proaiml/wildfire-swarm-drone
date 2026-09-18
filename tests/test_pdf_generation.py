"""
PyreSwarm - PDF Dokümantasyon Üretim Doğrulama Testleri
"""

import os
import pytest
from docs.generate_pdf_reports import generate_user_guide_pdf, generate_metrics_report_pdf


def test_pdf_reports_exist_and_valid():
    guide_pdf = "docs/PyreSwarm_Kullanim_Kilavuzu.pdf"
    metrics_pdf = "docs/PyreSwarm_Matematiksel_Model_ve_Metrik_Raporu.pdf"

    # Eğer yoksa üret
    if not os.path.exists(guide_pdf):
        generate_user_guide_pdf(guide_pdf)
    if not os.path.exists(metrics_pdf):
        generate_metrics_report_pdf(metrics_pdf)

    assert os.path.exists(guide_pdf)
    assert os.path.exists(metrics_pdf)

    # Dosya boyutları kontrolü (Boş veya bozuk olmamalı)
    assert os.path.getsize(guide_pdf) > 2000
    assert os.path.getsize(metrics_pdf) > 50000  # Grafikli zengin PDF
