# run.sh Launcher Design

## Goal

Add a single root-level shell script that starts the local expense screenshot tool with minimal setup friction.

## Scope

- Create `run.sh` at the repository root
- Use the existing `.venv` if present
- Create `.venv` if it does not exist
- Install the project in editable mode with `.[dev]` if dependencies are not yet available
- Start the Flask app with `expense_record.app`
- Preserve support for `EXPENSE_RECORD_EXCEL_PATH` if the user exports it before launch
- Print the local app URL before starting

## Out of Scope

- Windows `.bat` or PowerShell launcher
- Process management or background daemon behavior
- Auto-opening a browser
- Production deployment behavior

## Approach

Use one small POSIX shell script, `run.sh`, at the repo root.

The script should:

1. Change into the repository root
2. Check for `.venv`
3. Create `.venv` with `python3 -m venv .venv` if missing
4. Check whether Flask and the package are available in the virtualenv
5. Run `.venv/bin/python -m pip install -e ".[dev]"` if dependencies are missing
6. Print the URL, such as `http://127.0.0.1:5000`
7. Start the app with `.venv/bin/flask --app expense_record.app run`

## Error Handling

- Fail fast if `python3` is not available
- Exit on shell errors
- Avoid silently ignoring dependency-install failures

## Success Criteria

The launcher is successful if the user can run:

```bash
./run.sh
```

and get a working local app without needing to remember the setup and Flask commands manually.
