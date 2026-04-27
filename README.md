# MySQL Query Runner (Python)

This repository now includes a Python Streamlit application that lets you:

- Manage multiple MySQL connections on a dedicated **Connections** screen.
- Paste or drag-and-drop a `.sql` file in the **SQL Runner** screen.
- Automatically execute the SQL when dropped/uploaded.
- Export query results as an Excel file saved locally and downloadable from the UI.

## Quick Start

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the app:

   ```bash
   streamlit run app.py
   ```

3. Open the URL shown by Streamlit (usually `http://localhost:8501`).

## Notes

- Connections are stored in `data/connections.json` for convenience.
- Passwords are encoded (not encrypted). For production, replace this with a secure secret store.
- Only `SELECT`-style queries are exported to Excel because they return tabular data.
