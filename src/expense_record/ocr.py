from __future__ import annotations


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def run_ocr_lines(image_bytes: bytes) -> list[str]:
    engine = _get_engine()
    result, _ = engine(image_bytes)
    if not result:
        return []

    lines: list[str] = []
    for entry in result:
        if not entry or len(entry) < 2:
            continue
        text = str(entry[1]).strip()
        if text:
            lines.append(text)
    return lines
