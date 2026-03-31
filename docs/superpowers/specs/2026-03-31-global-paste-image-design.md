# Global Paste Image Design

## Goal

Make `Ctrl+V` image paste work anywhere on the page instead of only when the paste box has focus.

## Scope

- Listen for image paste events at the document level
- Accept pasted screenshots from anywhere on the page
- Preserve normal text paste behavior inside editable text inputs
- Update the upload helper copy so it matches the actual behavior

## Out of Scope

- Drag-and-drop support
- Clipboard-read buttons or permission prompts
- Changes to OCR, parsing, or save behavior

## Approach

Use one document-level `paste` handler in the existing frontend script.

The handler should:

1. Inspect clipboard items for an image
2. If no image exists, leave the event alone
3. If an image exists and the current target is a text input used for row editing, do not intercept it
4. Otherwise, prevent the default paste behavior and load the pasted image as the current screenshot selection

The page copy should stop telling the user to focus the paste box first, because that requirement will no longer exist.

## Success Criteria

- Pressing `Ctrl+V` with an image in the clipboard loads the screenshot even if the paste zone is not focused
- Pasting text into the `date`, `merchant/item`, or `amount` inputs still works normally
- The upload instructions describe the updated behavior accurately
