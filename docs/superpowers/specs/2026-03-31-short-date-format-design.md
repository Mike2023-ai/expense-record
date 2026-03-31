# Short Date Format Design

## Goal

Store extracted dates as `MM-DD` only and ignore any OCR time suffix.

## Scope

- Parse OCR date text like `3月29日`, `3月29日 08:42`, and `3月29日08:42`
- Ignore the time portion entirely when present
- Save the extracted `date` field as `MM-DD`
- Update the review form placeholder so it matches the new format

## Out of Scope

- Adding a separate time column
- Storing hidden full-year normalized dates
- Changing merchant or amount parsing
- Backfilling existing saved rows

## Approach

Keep the parser focused on month-day extraction only for this screenshot workflow.

The parser should:

1. Recognize Chinese month-day date strings with or without a trailing time
2. Strip any trailing time-like suffix from the matched date text
3. Normalize the result to zero-padded `MM-DD`

The UI should:

1. Show the date input as `MM-DD`
2. Stop implying a year is required

## Success Criteria

- OCR text `3月29日` extracts as `03-29`
- OCR text `3月29日 08:42` extracts as `03-29`
- OCR text `3月29日08:42` extracts as `03-29`
- The review form placeholder matches the saved format
