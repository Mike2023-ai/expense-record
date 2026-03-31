# Negative Amount Preference Design

## Goal

Prefer the actual charged expense amount when OCR returns both a current amount and an old crossed-out amount.

## Scope

- Update amount selection when multiple amount-like OCR lines are present
- Prefer a negative amount over a positive amount when both exist
- Add regression coverage for the crossed-out old-price screenshot pattern

## Out of Scope

- Image-based strikethrough detection
- Using OCR bounding boxes or visual positions
- Changing date parsing
- Changing merchant extraction

## Approach

Keep the parser text-based, but improve amount ranking.

The parser should:

1. Scan all amount-like lines in OCR order
2. If one or more negative amounts are present, choose the first negative amount
3. Otherwise, keep the current fallback amount selection behavior

This is a practical first pass for screenshots where OCR reads both:

- the real charged amount like `-28.00`
- the old crossed-out amount like `31.00`

## Success Criteria

- OCR lines `滴滴出行`, `-28.00`, `3月28日11:44`, `31.00` extract amount `28.00`
- Existing single-amount screenshots still parse as before
