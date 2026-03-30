# Expense Screenshot Recording Tool Design

## Goal

Build a local web tool that accepts one phone screenshot at a time, extracts expense information from the image, lets the user correct the result, and saves the record into an Excel file.

## Day-One Scope

- Single screenshot only per extraction flow
- Input methods:
  - Paste screenshot from clipboard
  - Upload an image file manually
- Output table columns:
  - `date`
  - `merchant/item`
  - `amount`
- Keep extracted text in the original language, including Chinese
- Require user review and editing before saving
- Save records to a local Excel file
- Show saved records in the web page

## Out of Scope

- Batch import of multiple screenshots
- Translation into English
- Automatic categorization
- Cloud sync
- Mobile app packaging
- Generic support for every bank layout from day one

## Recommended Approach

Use a small local web app with a lightweight backend.

This approach keeps the user experience simple while giving the implementation a stable place for OCR, field extraction logic, Excel writing, and future layout-specific parsing improvements. It is a better fit than a browser-only app because OCR quality and spreadsheet writing are easier to control on the server side.

## Architecture

### Frontend

The frontend is a single local web page with:

- an image paste area
- a file upload control
- a preview of the selected screenshot
- an `Extract` action
- an editable form for `date`, `merchant/item`, and `amount`
- a `Save` action
- a table showing rows already saved in the Excel file

### Backend

The backend is a local HTTP service responsible for:

- receiving one uploaded image at a time
- running OCR on the image
- parsing OCR text into the three target fields
- returning extracted values to the frontend
- creating the Excel file if it does not exist
- appending approved rows to the Excel file
- reading existing rows so the frontend can display them

### Storage

Persist records in one local Excel file with a single worksheet and a header row:

| date | merchant/item | amount |
| --- | --- | --- |

The first save creates the workbook if needed. Later saves append rows without rewriting the header.

## User Flow

1. Open the local web page.
2. Paste a screenshot from the clipboard or upload an image file.
3. The page shows the selected image.
4. The user clicks `Extract`.
5. The backend runs OCR and returns one extracted row.
6. The page shows the row in an editable form.
7. The user corrects any OCR mistakes.
8. The user clicks `Save`.
9. The backend appends the row to the Excel file.
10. The page refreshes the saved-records table.

## OCR and Extraction Behavior

### OCR

The system should process screenshots locally and support Chinese text without translation. OCR output is preserved in its original language.

### Field Extraction

The parser should extract:

- `date`: transaction date as shown in the screenshot
- `merchant/item`: the most relevant merchant or expense description text
- `amount`: the transaction amount as displayed

The first version should prioritize a practical heuristic parser rather than trying to perfectly understand every possible banking layout.

### Incomplete Results

If OCR or parsing cannot confidently determine one or more fields:

- return blank values for the uncertain fields
- still show the editable form
- let the user complete the missing fields manually before saving

## Error Handling

The system should handle these cases clearly:

- no image provided
- unsupported or unreadable image
- OCR returns little or no usable text
- extracted fields are incomplete
- Excel file is locked or cannot be written

In each case, show a direct error message in the page and keep the current image so the user can retry or edit manually.

## Initial Parsing Strategy

The day-one parser should be simple and upgradeable:

- identify likely date patterns from OCR text
- identify likely amount patterns from currency-style number strings
- treat the remaining most relevant descriptive text as `merchant/item`

This is intentionally modest. The design should make it easy to add bank-specific parsing rules later without replacing the whole app.

## Testing Focus

Verify the first implementation with these cases:

- paste a screenshot from the clipboard
- upload a screenshot image file
- extract Chinese-language screenshot text into the three fields
- manually correct extracted values before saving
- create the Excel file on first save
- append multiple saved rows without duplicating the header
- reload the page and show existing saved rows

## Implementation Notes

- Keep processing local on the user's machine
- Optimize for a fast manual-review workflow rather than fully automatic accuracy
- Favor readable code boundaries so OCR, parsing, and Excel writing can evolve independently

## Suggested Module Boundaries

- frontend upload and preview
- frontend extracted-row editor
- frontend saved-records table
- backend OCR service
- backend field parser
- backend Excel storage service

## Success Criteria

The first version is successful if the user can:

- open a local web page
- paste or upload one phone screenshot
- extract one candidate expense row
- correct OCR mistakes
- save the row into an Excel file
- see saved rows in a table
