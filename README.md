# JSON to SQL Server Importer

A desktop application built with Python and Tkinter for importing JSON records into a Microsoft SQL Server table.

The application lets you connect to SQL Server, select a database and destination table, load a JSON file, preview matching columns, and import records in a single transaction.

## Features

- Load a JSON file containing:
  - A single JSON object
  - An array of JSON objects
  - An object containing a `data` array
- Connect to SQL Server using either:
  - Windows Authentication
  - SQL Server Authentication
- Automatically detect installed SQL Server ODBC drivers.
- Browse accessible databases, schemas, and tables.
- Match JSON field names to SQL Server column names (case-insensitive).
- Preview JSON fields, matched columns, and sample values before importing.
- Identify unmatched fields and required SQL columns that are missing from the JSON.
- Insert records using parameterized SQL statements.
- Import all records in one transaction. If an insert fails, the transaction is rolled back.

## Requirements

- Windows, Linux, or macOS with a supported Python installation.
- Python 3.10 or later recommended.
- Microsoft SQL Server.
- Microsoft ODBC Driver 17 or 18 for SQL Server.
- Python packages:
  - `pyodbc`
- Tkinter (usually included with the standard Python installer).

> **Windows note:** During Python installation, make sure the Tcl/Tk support option is included so that Tkinter is available.

## Installation and Setup

This project uses **Pipenv** to manage its Python environment and dependencies.

### 1. Install Pipenv

If Pipenv is not already installed, install it with:

```bash
python -m pip install --user pipenv
```

If the `pipenv` command is not recognized, check that Python's user Scripts directory is included in your system `PATH`, or run Pipenv through Python where supported.

### 2. Open the project directory

Open a terminal or command prompt and change to the folder containing the project:

```bash
cd path/to/project
```

### 3. Install the project dependency

Install `pyodbc` into the Pipenv-managed virtual environment:

```bash
pipenv install pyodbc
```

This creates or updates the `Pipfile` and `Pipfile.lock` and installs the required dependency.

### 4. Activate the virtual environment

Run:

```bash
pipenv shell
```

This opens a shell inside the project's virtual environment. Run the application from this shell.

### 5. Run the application

If the Python source file is named `main.py`, run:

```bash
python main.py
```

If your source file has a different name, replace `main.py` with the actual filename.

### Alternative: Run without opening a Pipenv shell

You can also run the application directly through Pipenv:

```bash
pipenv run python main.py
```

## SQL Server ODBC Driver

`pyodbc` requires a Microsoft SQL Server ODBC driver installed on the computer. Installing the Python package alone is not sufficient.

Install either:

- [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- [Microsoft ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

The application checks the installed drivers and prefers Driver 18, then Driver 17.

## How to Use

1. Start the application.
2. Under **1. SQL Server connection**, select the ODBC driver.
3. Enter the SQL Server name or IP address.
   - For a local default SQL Server instance, use `localhost`.
   - For a named instance, use a server value such as `SERVER\\INSTANCE`.
4. Select the authentication method:
   - **Windows**: uses the current Windows account.
   - **SQL Server**: enter the SQL Server username and password.
5. Click **Connect / Load databases**.
6. Under **2. Destination**, select the target database and table.
7. Under **3. JSON file**, click **Choose JSON file** and select your `.json` file.
8. Review **4. Preview and column matching**.
   - JSON keys are matched to SQL Server columns without case sensitivity.
   - Identity columns are not included in the import.
   - Unmatched JSON fields are skipped.
   - Check any required SQL columns reported as missing.
9. Click **Refresh column matching** if you need to refresh the preview.
10. Click **Import records** and confirm the operation.

## Supported JSON Formats

### Single object

```json
{
  "AccountNumber": "000123",
  "ConsumerName": "Juan Dela Cruz",
  "Amount": 1250.50
}
```

### Array of objects

```json
[
  {
    "AccountNumber": "000123",
    "ConsumerName": "Juan Dela Cruz",
    "Amount": 1250.50
  },
  {
    "AccountNumber": "000124",
    "ConsumerName": "Maria Santos",
    "Amount": 980.00
  }
]
```

### Object containing a `data` array

```json
{
  "data": [
    {
      "AccountNumber": "000123",
      "ConsumerName": "Juan Dela Cruz",
      "Amount": 1250.50
    }
  ]
}
```

JSON field names should correspond to destination SQL Server column names. Matching is case-insensitive, but the application does not automatically convert or rename fields.

## Import Behavior and Limitations

- Only matching JSON fields are inserted.
- SQL Server identity columns are excluded from the insert.
- Required columns that are non-nullable, have no default, and are not identity columns must be supplied by the JSON data.
- JSON arrays and objects used as field values are converted to JSON text before insertion. The destination column must support storing that text.
- JSON `null` values are passed as SQL `NULL`.
- SQL Server constraints and triggers remain in effect; the application does not bypass them.
- All records are inserted in one transaction. If an insert fails, the application attempts to roll back the entire import.
- The application does not provide automatic field renaming, data transformation, or type conversion beyond handling JSON arrays and objects.

## Troubleshooting

### No SQL Server ODBC driver was found

Install Microsoft ODBC Driver 17 or 18 for SQL Server, then restart the application.

### `pyodbc` cannot be imported

Make sure you installed the dependency in the project's Pipenv environment:

```bash
pipenv install pyodbc
pipenv shell
python -c "import pyodbc; print(pyodbc.version)"
```

### No databases are listed

Check that:

- The server name or IP address is correct.
- The SQL Server service is running and reachable.
- The selected account has permission to connect to the server and access databases.
- The required network port and firewall rules allow the connection.

### Login or authentication failed

Verify the selected authentication mode and credentials. For Windows Authentication, make sure the current Windows account has SQL Server access.

### Import fails because of a column or data error

Review the SQL Server/ODBC error shown by the application. Check column data types, required fields, constraints, triggers, and whether the JSON values are valid for the destination columns.

## Security Notes

- Use an account with only the database permissions required for the import.
- Avoid storing database passwords in source code or committing them to version control.
- Use a trusted network connection to the SQL Server.
- The current connection string sets `TrustServerCertificate=yes`. Review your SQL Server encryption and certificate configuration before using this application in a production environment.

## Recommended Practice

**Test with a non-production database first.** Confirm the JSON-to-table field matching and validate a small sample before importing production data.
