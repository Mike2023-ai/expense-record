# Month-Day Date Parser Design

## Goal

Improve the parser so cropped transaction screenshots that show dates like `3月29日 08:42` or `3月29日` can still extract a usable `date` field.

## Scope

- Extend parser date extraction to support month-day formats without a visible year
- Assume the current year when normalizing those dates
- Preserve the existing full-year date parsing behavior
- Add regression tests for the newly supported date formats

## Out of Scope

- Multi-row transaction-list extraction
- OCR engine changes
- Month inference from surrounding UI context
- Translation or category inference

## Approach

Use a small parser extension only.

The parser should:

1. Keep existing support for full-year formats like `2026-03-29` and `2026年3月29日`
2. Add support for:
   - `3月29日 08:42`
   - `3月29日`
   - common OCR-like variants such as `3/29 08:42` and `3.29`
3. Normalize those matches to `YYYY-MM-DD` using the current year
4. Leave merchant and amount parsing unchanged

## Testing

Add parser regression tests for:

- `3月29日 08:42`
- `3月29日`
- a realistic cropped row combining:
  - merchant text
  - amount
  - month-day date without year

## Success Criteria

The fix is successful if a screenshot row like:

- `扫二维码付款-给早餐`
- `3月29日 08:42`
- `-5.00`

can produce:

- `date`: current-year `YYYY-03-29`
- `merchant/item`: `扫二维码付款-给早餐`
- `amount`: `5.00`
