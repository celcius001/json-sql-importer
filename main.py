"""
JSON to SQL Server Importer
--------------------------
Requirements:
    pip install pyodbc

You also need Microsoft ODBC Driver 17 or 18 for SQL Server installed.

Features:
- Select a JSON file containing an object or an array of objects.
- Connect using SQL Server authentication or Windows authentication.
- Choose a database, schema, and table.
- Preview records and automatically match JSON keys to table columns.
- Import in one transaction (all rows commit, or all roll back on error).
- Uses parameterized SQL values and safely quotes metadata-derived identifiers.

Note:
- Test against a non-production database first.
- This program does not attempt to bypass table constraints or triggers.
"""

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pyodbc

APP_TITLE = "JSON to SQL Server Importer"


class JsonSqlImporter:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x760")
        self.root.minsize(850, 620)

        self.connection = None
        self.json_path = None
        self.records = []
        self.table_columns = []
        self.matched_columns = []

        self.server_var = tk.StringVar(value="localhost")
        self.auth_var = tk.StringVar(value="Windows")
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.driver_var = tk.StringVar(value=self._default_driver())
        self.database_var = tk.StringVar()
        self.table_var = tk.StringVar()
        self.file_var = tk.StringVar(value="No JSON file selected")
        self.status_var = tk.StringVar(value="Not connected")

        self._build_ui()

    @staticmethod
    def _default_driver():
        installed = list(pyodbc.drivers())
        preferred = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server",
        ]
        for name in preferred:
            if name in installed:
                return name
        return installed[-1] if installed else ""

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        # Connection
        conn = ttk.LabelFrame(outer, text="1. SQL Server connection", padding=10)
        conn.pack(fill="x")

        ttk.Label(conn, text="Driver").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.driver_combo = ttk.Combobox(
            conn, textvariable=self.driver_var,
            values=list(pyodbc.drivers()), width=31, state="readonly"
        )
        self.driver_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(conn, text="Server").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(conn, textvariable=self.server_var, width=25).grid(
            row=0, column=3, sticky="ew", padx=4, pady=4
        )

        ttk.Label(conn, text="Authentication").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        auth = ttk.Combobox(
            conn, textvariable=self.auth_var,
            values=["Windows", "SQL Server"], state="readonly", width=18
        )
        auth.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        auth.bind("<<ComboboxSelected>>", self._toggle_auth_fields)

        ttk.Label(conn, text="Username").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        self.username_entry = ttk.Entry(conn, textvariable=self.username_var, width=25)
        self.username_entry.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(conn, text="Password").grid(row=2, column=2, sticky="w", padx=4, pady=4)
        self.password_entry = ttk.Entry(conn, textvariable=self.password_var, show="*", width=25)
        self.password_entry.grid(row=2, column=3, sticky="ew", padx=4, pady=4)

        ttk.Button(conn, text="Connect / Load databases", command=self.connect_server).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=4, pady=6
        )
        conn.columnconfigure(1, weight=1)
        conn.columnconfigure(3, weight=1)
        self._toggle_auth_fields()

        # Target
        target = ttk.LabelFrame(outer, text="2. Destination", padding=10)
        target.pack(fill="x", pady=(10, 0))

        ttk.Label(target, text="Database").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.database_combo = ttk.Combobox(
            target, textvariable=self.database_var, state="readonly", width=35
        )
        self.database_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.database_combo.bind("<<ComboboxSelected>>", self.load_tables)

        ttk.Label(target, text="Table (schema.table)").grid(
            row=0, column=2, sticky="w", padx=4, pady=4
        )
        self.table_combo = ttk.Combobox(
            target, textvariable=self.table_var, state="readonly", width=40
        )
        self.table_combo.grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        self.table_combo.bind("<<ComboboxSelected>>", self.load_table_columns)
        target.columnconfigure(1, weight=1)
        target.columnconfigure(3, weight=1)

        # JSON file
        file_frame = ttk.LabelFrame(outer, text="3. JSON file", padding=10)
        file_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(file_frame, text="Choose JSON file", command=self.choose_json).pack(
            side="left", padx=(0, 10)
        )
        ttk.Label(file_frame, textvariable=self.file_var).pack(side="left", fill="x", expand=True)

        # Preview
        preview_frame = ttk.LabelFrame(outer, text="4. Preview and column matching", padding=10)
        preview_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.match_label = ttk.Label(
            preview_frame, text="Load a JSON file and select a destination table."
        )
        self.match_label.pack(anchor="w", pady=(0, 6))

        columns = ("json_field", "sql_column", "sample_value")
        self.preview = ttk.Treeview(preview_frame, columns=columns, show="headings", height=12)
        self.preview.heading("json_field", text="JSON field")
        self.preview.heading("sql_column", text="Matched SQL column")
        self.preview.heading("sample_value", text="First record value")
        self.preview.column("json_field", width=220)
        self.preview.column("sql_column", width=220)
        self.preview.column("sample_value", width=480)
        self.preview.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        scrollbar.pack(side="right", fill="y")
        self.preview.configure(yscrollcommand=scrollbar.set)

        # Import
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Refresh column matching", command=self.refresh_preview).pack(
            side="left"
        )
        ttk.Button(bottom, text="Import records", command=self.import_records).pack(
            side="right"
        )
        ttk.Label(outer, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", pady=(8, 0)
        )

    def _toggle_auth_fields(self, _event=None):
        is_sql = self.auth_var.get() == "SQL Server"
        state = "normal" if is_sql else "disabled"
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)

    def _connection_string(self, database="master"):
        driver = self.driver_var.get().strip()
        server = self.server_var.get().strip()
        if not driver:
            raise ValueError("No SQL Server ODBC driver was found. Install ODBC Driver 17 or 18.")
        if not server:
            raise ValueError("Enter the SQL Server name or IP address.")

        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={database}",
            "TrustServerCertificate=yes",
            "Connection Timeout=15",
        ]

        if self.auth_var.get() == "Windows":
            parts.append("Trusted_Connection=yes")
        else:
            user = self.username_var.get().strip()
            password = self.password_var.get()
            if not user:
                raise ValueError("Enter the SQL Server username.")
            parts.extend([f"UID={user}", f"PWD={password}"])

        # ODBC connection-string values containing semicolons or braces need quoting.
        return ";".join(parts) + ";"

    def connect_server(self):
        try:
            if self.connection:
                self.connection.close()
                self.connection = None

            self.connection = pyodbc.connect(self._connection_string("master"), autocommit=True)
            cursor = self.connection.cursor()
            rows = cursor.execute("""
                SELECT name
                FROM sys.databases
                WHERE state_desc = 'ONLINE'
                  AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """).fetchall()

            databases = [row[0] for row in rows]
            self.database_combo["values"] = databases
            if databases:
                preferred = self.database_var.get()
                self.database_var.set(preferred if preferred in databases else databases[0])
                self.load_tables()
            self.status_var.set(f"Connected. {len(databases)} accessible database(s) found.")
            messagebox.showinfo("Connected", f"Connected to SQL Server.\nFound {len(databases)} database(s).")
        except pyodbc.Error as exc:
            self.status_var.set("Connection failed.")
            messagebox.showerror("Connection error", str(exc))

    def _connect_database(self):
        database = self.database_var.get().strip()
        if not database:
            raise ValueError("Select a database first.")
        if self.connection:
            try:
                self.connection.close()
            except pyodbc.Error:
                pass
        self.connection = pyodbc.connect(self._connection_string(database), autocommit=False)
        return self.connection

    def load_tables(self, _event=None):
        try:
            conn = self._connect_database()
            rows = conn.cursor().execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """).fetchall()

            tables = [f"{r[0]}.{r[1]}" for r in rows]
            self.table_combo["values"] = tables
            self.table_var.set("")
            self.table_columns = []
            if tables:
                self.table_var.set(tables[0])
                self.load_table_columns()
            self.status_var.set(f"Loaded {len(tables)} table(s) from {self.database_var.get()}.")
        except pyodbc.Error as exc:
            messagebox.showerror("Table loading error", str(exc))

    def load_table_columns(self, _event=None):
        try:
            schema, table = self._selected_table()
            conn = self._connect_database()
            rows = conn.cursor().execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE,
                       COLUMN_DEFAULT, CHARACTER_MAXIMUM_LENGTH,
                       NUMERIC_PRECISION, NUMERIC_SCALE,
                       COLUMNPROPERTY(OBJECT_ID(QUOTENAME(TABLE_SCHEMA) + '.' +
                           QUOTENAME(TABLE_NAME)), COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, schema, table).fetchall()

            self.table_columns = [
                {
                    "name": r[0],
                    "type": r[1],
                    "nullable": r[2] == "YES",
                    "default": r[3],
                    "identity": bool(r[7]),
                }
                for r in rows
            ]
            self.refresh_preview()
        except pyodbc.Error as exc:
            messagebox.showerror("Column loading error", str(exc))

    def _selected_table(self):
        value = self.table_var.get().strip()
        if "." not in value:
            raise ValueError("Select a table in schema.table format.")
        schema, table = value.split(".", 1)
        if not schema or not table:
            raise ValueError("Invalid table selection.")
        return schema, table

    def choose_json(self):
        path = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8-sig") as file:
                payload = json.load(file)

            if isinstance(payload, dict):
                # Accept either one record or an object containing a "data" array.
                if isinstance(payload.get("data"), list):
                    payload = payload["data"]
                else:
                    payload = [payload]

            if not isinstance(payload, list) or not payload:
                raise ValueError("JSON must contain one object or a non-empty array of objects.")

            if not all(isinstance(item, dict) for item in payload):
                raise ValueError("Every item in the JSON array must be an object.")

            self.records = payload
            self.json_path = Path(path)
            self.file_var.set(f"{self.json_path.name} — {len(self.records)} record(s)")
            self.refresh_preview()
            self.status_var.set(f"Loaded {len(self.records)} JSON record(s).")
        except pyodbc.Error as exc:
            messagebox.showerror("JSON file error", str(exc))

    def refresh_preview(self):
        for item in self.preview.get_children():
            self.preview.delete(item)

        if not self.records:
            self.match_label.config(text="Choose a JSON file to preview its fields.")
            return
        if not self.table_columns:
            self.match_label.config(text="Select a destination table to match its columns.")
            return

        # Match names case-insensitively, preserving SQL Server's actual column spelling.
        sql_by_lower = {c["name"].lower(): c for c in self.table_columns}
        json_keys = list(dict.fromkeys(k for record in self.records for k in record))

        self.matched_columns = []
        unmatched = []
        for key in json_keys:
            column = sql_by_lower.get(key.lower())
            sample = self.records[0].get(key)
            sample_text = json.dumps(sample, ensure_ascii=False, default=str)
            if len(sample_text) > 110:
                sample_text = sample_text[:107] + "..."

            if column and not column["identity"]:
                self.matched_columns.append((key, column["name"]))
                self.preview.insert("", "end", values=(key, column["name"], sample_text))
            else:
                unmatched.append(key)
                self.preview.insert("", "end", values=(key, "(not matched / identity)", sample_text))

        missing_required = [
            c["name"] for c in self.table_columns
            if not c["nullable"] and c["default"] is None and not c["identity"]
            and c["name"].lower() not in {sql_name.lower() for _, sql_name in self.matched_columns}
        ]

        info = (
            f"{len(self.records)} record(s) | "
            f"{len(self.matched_columns)} matched field(s) | "
            f"{len(unmatched)} unmatched field(s)"
        )
        if missing_required:
            info += " | Required SQL columns not supplied: " + ", ".join(missing_required)
        self.match_label.config(text=info)

    @staticmethod
    def _quote_identifier(name):
        # SQL Server identifier quoting; closing brackets are escaped.
        return "[" + name.replace("]", "]]") + "]"

    def import_records(self):
        if not self.records:
            messagebox.showwarning("No JSON data", "Choose a JSON file first.")
            return
        if not self.table_columns or not self.matched_columns:
            messagebox.showwarning("No matching columns", "Select a table with matching JSON fields.")
            return

        schema, table = self._selected_table()

        # Verify that every required non-identity/no-default column is supplied.
        matched_sql_names = {sql_name.lower() for _, sql_name in self.matched_columns}
        missing_required = [
            c["name"] for c in self.table_columns
            if not c["nullable"] and c["default"] is None and not c["identity"]
            and c["name"].lower() not in matched_sql_names
        ]
        if missing_required:
            messagebox.showerror(
                "Required columns missing",
                "The table requires columns not present in the JSON:\n\n"
                + "\n".join(missing_required)
            )
            return

        confirm = messagebox.askyesno(
            "Confirm import",
            f"Import {len(self.records)} record(s) into "
            f"{self.database_var.get()}.[{schema}].[{table}]?\n\n"
            "The import runs in one transaction. If a row fails, all rows will be rolled back."
        )
        if not confirm:
            return

        conn = None
        try:
            conn = self._connect_database()
            cursor = conn.cursor()
            cursor.fast_executemany = True

            quoted_table = (
                self._quote_identifier(schema) + "." + self._quote_identifier(table)
            )
            quoted_columns = ", ".join(
                self._quote_identifier(sql_name) for _, sql_name in self.matched_columns
            )
            placeholders = ", ".join("?" for _ in self.matched_columns)

            sql_text = (
                f"INSERT INTO {quoted_table} ({quoted_columns}) "
                f"VALUES ({placeholders})"
            )

            values = []
            for record in self.records:
                row = []
                for json_key, _sql_name in self.matched_columns:
                    value = record.get(json_key)
                    # pyodbc accepts None for SQL NULL. JSON objects/arrays are stored as JSON text.
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    row.append(value)
                values.append(tuple(row))

            cursor.executemany(sql_text, values)
            conn.commit()

            self.status_var.set(f"Import complete: {len(values)} record(s) inserted.")
            messagebox.showinfo(
                "Import successful",
                f"Successfully inserted {len(values)} record(s) into {schema}.{table}."
            )
        except pyodbc.Error as exc:
            if conn:
                try:
                    conn.rollback()
                except pyodbc.Error:
                    pass
            self.status_var.set("Import failed. Transaction rolled back.")
            messagebox.showerror(
                "Import failed",
                "No records were committed. The transaction was rolled back.\n\n"
                f"SQL Server / ODBC error:\n{exc}"
            )
        finally:
            if conn:
                try:
                    conn.close()
                except pyodbc.Error:
                    pass
                self.connection = None


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except pyodbc.Error:
        pass
    JsonSqlImporter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
