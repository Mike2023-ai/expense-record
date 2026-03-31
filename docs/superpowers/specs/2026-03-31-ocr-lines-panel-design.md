# OCR Lines Panel Design

## Goal

Show the raw OCR text lines on the webpage after extraction so OCR problems can be diagnosed directly from the UI.

## Scope

- Reuse the existing `lines` field already returned by `/api/extract`
- Add a small read-only OCR lines section to the page
- Render OCR lines after a successful extract
- Clear the OCR lines section when extraction fails or when a new screenshot is selected

## Out of Scope

- New API endpoints
- Toggleable debug mode
- Editing OCR lines in the browser
- OCR confidence visualization

## Approach

Use one lightweight debug panel in the existing page.

The UI should:

1. Add a small section labeled `OCR lines`
2. Render each extracted OCR line as plain text in order
3. Show the panel only when there is OCR output to display
4. Clear the displayed lines when a new image is selected or extraction fails

## Success Criteria

After clicking `Extract`, the page should show the exact OCR lines returned by the backend so we can compare:

- what OCR actually read
- what the parser extracted into `date`, `merchant/item`, and `amount`
