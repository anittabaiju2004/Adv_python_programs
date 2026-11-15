"""QR code helpers.

PDFs use ReportLab's built-in QR generator, so issue slips and member cards
work without extra packages. PNG export uses the `qrcode` package when it is
installed (pip install qrcode[pil]).
"""
from __future__ import annotations

from pathlib import Path

from .utils import LibraryError


def qr_drawing(data: str, size: float):
    """A ReportLab Drawing containing a QR code, `size` points square."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    widget = QrCodeWidget(data)
    x1, y1, x2, y2 = widget.getBounds()
    w, h = x2 - x1, y2 - y1
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(widget)
    return d


def qrcode_available() -> bool:
    try:
        import qrcode  # noqa: F401
        return True
    except ImportError:
        return False


def save_qr_png(data: str, path: Path | str) -> Path:
    try:
        import qrcode
    except ImportError:
        raise LibraryError("PNG QR codes need the 'qrcode' package: pip install qrcode[pil]. "
                           "(QR codes inside PDFs work without it.)")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    qrcode.make(data).save(path)
    return path
