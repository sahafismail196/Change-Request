import base64
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import mysql.connector
import streamlit as st

DATA_DIR = Path("data")
CONNECTION_FILE = DATA_DIR / "connections.json"


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONNECTION_FILE.exists():
        CONNECTION_FILE.write_text("[]", encoding="utf-8")


def encode_secret(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def decode_secret(value: str) -> str:
    return base64.b64decode(value.encode("utf-8")).decode("utf-8")


def load_connections() -> list[dict]:
    ensure_storage()
    with CONNECTION_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_connections(connections: list[dict]) -> None:
    ensure_storage()
    with CONNECTION_FILE.open("w", encoding="utf-8") as file:
        json.dump(connections, file, indent=2)


def execute_query(connection: dict, query: str) -> pd.DataFrame:
    db = mysql.connector.connect(
        host=connection["host"],
        port=int(connection["port"]),
        user=connection["username"],
        password=decode_secret(connection["password"]),
        database=connection["database"],
    )
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        db.close()


def export_excel(df: pd.DataFrame) -> tuple[Path, bytes]:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"query-results-{timestamp}.xlsx"
    output_path = DATA_DIR / filename

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Results", index=False)

    file_bytes = output_path.read_bytes()
    return output_path, file_bytes


def render_connections() -> None:
    st.subheader("MySQL Connections")
    connections = load_connections()

    with st.form("new-connection"):
        st.markdown("### Add New Connection")
        name = st.text_input("Connection name", placeholder="example: Reporting DB")
        col1, col2 = st.columns(2)
        host = col1.text_input("Host", value="localhost")
        port = col2.number_input("Port", value=3306, min_value=1, max_value=65535)
        database = st.text_input("Database")
        col3, col4 = st.columns(2)
        username = col3.text_input("Username")
        password = col4.text_input("Password", type="password")
        submitted = st.form_submit_button("Save connection")

        if submitted:
            if not all([name.strip(), host.strip(), database.strip(), username.strip(), password]):
                st.error("All fields are required.")
            else:
                connections.append(
                    {
                        "name": name.strip(),
                        "host": host.strip(),
                        "port": int(port),
                        "database": database.strip(),
                        "username": username.strip(),
                        "password": encode_secret(password),
                    }
                )
                save_connections(connections)
                st.success("Connection saved.")
                st.rerun()

    st.markdown("### Saved Connections")
    if not connections:
        st.info("No connections saved yet.")
        return

    for idx, conn in enumerate(connections):
        with st.container(border=True):
            st.write(f"**{conn['name']}**")
            st.caption(f"{conn['username']}@{conn['host']}:{conn['port']} / {conn['database']}")
            if st.button("Delete", key=f"delete-{idx}"):
                connections.pop(idx)
                save_connections(connections)
                st.success("Connection removed.")
                st.rerun()


def render_sql_runner() -> None:
    st.subheader("SQL Runner")
    connections = load_connections()

    if not connections:
        st.warning("Please add a connection first from the Connections screen.")
        return

    names = [conn["name"] for conn in connections]
    selected_name = st.selectbox("Choose connection", options=names)
    selected = next(conn for conn in connections if conn["name"] == selected_name)

    st.markdown("### Drop SQL File or Paste Query")
    uploaded_file = st.file_uploader("Drop a .sql file here", type=["sql"])
    default_query = uploaded_file.read().decode("utf-8") if uploaded_file else ""

    query = st.text_area(
        "SQL Query",
        value=default_query,
        placeholder="SELECT * FROM your_table LIMIT 100;",
        height=220,
    )

    auto_execute = uploaded_file is not None and query.strip() != ""
    run_now = st.button("Run Query")

    if auto_execute:
        st.info("File detected. Auto-running SQL query.")

    if (auto_execute or run_now) and query.strip():
        query_lower = query.lstrip().lower()
        if not query_lower.startswith("select"):
            st.error("Only SELECT queries are allowed for export.")
            return

        try:
            result_df = execute_query(selected, query)
            st.success(f"Query executed successfully. Rows fetched: {len(result_df)}")
            st.dataframe(result_df, use_container_width=True)

            file_path, file_bytes = export_excel(result_df)
            st.success(f"Excel file saved locally at: {file_path}")
            st.download_button(
                label="Download Excel",
                data=file_bytes,
                file_name=file_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Execution failed: {exc}")


def main() -> None:
    st.set_page_config(page_title="MySQL SQL Runner", page_icon="🗄️", layout="wide")
    ensure_storage()

    st.title("MySQL Query Runner + Excel Export")
    st.caption("Manage DB connections and run dropped SQL files instantly.")

    menu = st.sidebar.radio("Navigation", ["SQL Runner", "Connections"])
    if menu == "SQL Runner":
        render_sql_runner()
    else:
        render_connections()


if __name__ == "__main__":
    main()
