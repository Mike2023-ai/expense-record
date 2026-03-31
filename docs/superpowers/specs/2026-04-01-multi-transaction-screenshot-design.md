# Multi-Transaction Screenshot Design

## Goal

Support one screenshot that contains multiple visible transaction rows and let the user review them in one editable table before saving.

## Scope

- Accept one screenshot that may contain multiple transaction rows
- Extract multiple candidate rows from one OCR result
- Replace the single-row review form with one editable review table
- Add a checkbox per extracted row
- Save only the checked rows into Excel

## Out of Scope

- Batch upload of multiple screenshots at once
- OCR bounding-box editing in the UI
- Automatic row grouping across multiple screenshots
- New Excel columns beyond `date`, `merchant/item`, and `amount`

## Approach

Keep the existing one-screenshot upload flow, but change extraction from a single parsed row to a list of parsed row candidates.

The backend should:

1. Run OCR on the screenshot as today
2. Group OCR text into multiple transaction-like row candidates
3. Parse each candidate into `date`, `merchant/item`, and `amount`
4. Return a list of extracted rows plus raw OCR lines

The frontend should:

1. Always show one editable review table instead of the current single-row form
2. Render one extracted row per table row
3. Include a checkbox per row, checked by default
4. Save only checked rows

## Review Table

Columns:

- `use`
- `date`
- `merchant/item`
- `amount`

Behavior:

- one extracted row still appears as one row in the table
- multiple extracted rows appear in the same table
- every cell stays editable before save
- unchecked rows are ignored on save

## Error Handling

- If OCR finds no usable rows, show the warning state and an empty review table
- If some rows are incomplete, still show them in the table for manual correction
- If no rows are checked at save time, return a validation error instead of writing blank data

## Success Criteria

- A list screenshot with multiple transactions produces multiple editable rows
- A single-row screenshot still works through the same table UI
- Unchecked rows are not written to Excel
- Checked rows are appended to Excel in one save action
