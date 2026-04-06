# Statement Import Design

Date: 2026-04-06
Branch: `feature/statement-import`

## Goal

Add a second import path for exported payment statement files without using OCR. This path should support both WeChat and Alipay statement exports, detect which source format was uploaded, extract rows into a shared review table, and save selected rows into the local workbook.

## Scope

This design covers:

- importing one statement file at a time
- detecting whether the uploaded file is a supported WeChat or Alipay export
- parsing statement rows from the supported file type
- normalizing rows into a shared 4-column structure
- reviewing, editing, selecting, and saving imported rows

This design does not cover:

- OCR for statement files
- batch import of multiple files at once
- row deduplication
- automatic merge of screenshot rows and statement rows in one extraction action
- support for unknown third-party statement formats

## Supported Sources

### WeChat

- input file type: `.xlsx`
- known sample: `微信支付账单流水文件(20260301-20260331)_20260401223428.xlsx`
- structure:
  - summary/header block at the top
  - detail table begins later in the sheet
  - detected detail headers include:
    - `交易时间`
    - `交易类型`
    - `交易对方`
    - `商品`
    - `收/支`
    - `金额(元)`

### Alipay

- input file type: `.csv`
- known sample: `支付宝交易明细(20260305-20260405).csv`
- encoding: `gb18030`
- structure:
  - summary/header block at the top
  - detail table begins later in the file
  - detected detail headers include:
    - `交易时间`
    - `交易分类`
    - `交易对方`
    - `商品说明`
    - `收/支`
    - `金额`

## Detection

The import flow must identify the uploaded file type before parsing any rows.

Detection order:

1. Inspect file extension
2. Inspect early file content for known platform markers
3. Inspect the detail header row for a supported schema

Supported outcomes:

- WeChat statement
- Alipay statement

Unsupported outcomes:

- unknown extension
- unsupported header layout
- ambiguous format

If detection is unsupported or ambiguous, the app must stop and show a clear error instead of guessing.

## Normalized Output

Both sources normalize into the same editable review-table columns:

- `交易时间`
- `交易对方`
- `收/支`
- `金额(元)`

Field mapping rules:

### WeChat mapping

- `交易时间` <- `交易时间`
- `交易对方` <- `交易对方`
- `收/支` <- `收/支`
- `金额(元)` <- `金额(元)`

### Alipay mapping

- `交易时间` <- `交易时间`
- `交易对方` <- `交易对方`
- `收/支` <- `收/支`
- `金额(元)` <- `金额`

The first version should not combine `交易对方` with `商品` or `商品说明`. It should use only `交易对方`.

## Row Inclusion Rules

The importer should include all statement rows from the supported detail table, including:

- `支出`
- `收入`
- `中性交易`
- `不计收支`

The importer should preserve original statement order.

The importer should skip:

- summary text above the detail table
- explanatory note sections
- blank rows

## UI

The existing screenshot import flow remains unchanged.

Add a second mode for statement file import:

- upload one file
- detect supported source type
- parse rows with the source-specific parser
- show normalized rows in the same editable checkbox review table
- save only checked rows

The review table should remain editable before saving.

## Error Handling

The app should show clear import errors for:

- unsupported file type
- unsupported encoding
- missing detail header row
- known source file with missing required columns
- empty detail table

Errors should be explicit about whether the failure happened during:

- source detection
- file reading
- header discovery
- row normalization

## Architecture

Add a statement import path that is separate from OCR extraction.

Expected responsibilities:

- source detection module or function:
  - identify WeChat vs Alipay from extension and headers
- WeChat parser:
  - locate detail header row in `.xlsx`
  - extract statement rows
  - normalize fields
- Alipay parser:
  - decode `.csv`
  - locate detail header row
  - extract statement rows
  - normalize fields
- shared review/save flow:
  - reuse the existing review-table behavior where possible

This branch should not call OCR for statement files.

## Testing

Add tests for:

- WeChat source detection
- Alipay source detection
- WeChat header discovery
- Alipay header discovery with `gb18030`
- normalization into the shared 4-column structure
- inclusion of `支出`, `收入`, and `中性交易` or `不计收支`
- unsupported-file errors
- save path with selected rows only

Use fixtures based on real sample structures from the provided WeChat and Alipay exports.

## Success Criteria

The first version is successful if:

- a supported WeChat export file imports correctly
- a supported Alipay export file imports correctly
- the app chooses the correct parser based on detected source type
- no OCR is used for statement files
- imported rows appear in the editable checkbox review table
- only checked rows are saved
