# Webpage Version Display Design

## Goal

Show the current app version on the webpage under the main title.

## Scope

- Expose the app version from Flask configuration
- Pass the version into the index template
- Render a small version line under the page title
- Style it as lightweight metadata

## Out of Scope

- Build-time asset versioning
- API endpoint for version info
- Footer redesign
- Version badge in another location

## Approach

Use dynamic template rendering instead of hardcoding the version string.

The app should:

1. Keep the project version in one source of truth
2. Make that version available through Flask config
3. Pass it into the `/` template render call
4. Render text like `Version 0.1.0` directly below the main heading

## Success Criteria

When the webpage loads, the header should show:

- `Expense Screenshot Tool`
- `Version 0.1.0`

with the version styled as secondary text.
