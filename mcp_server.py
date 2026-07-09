import os
import json

from fastmcp import FastMCP
from google.cloud import bigquery
from google.oauth2 import service_account

# Initialize the FastMCP server
mcp = FastMCP("BigQueryRequestManager")

def get_bq_client():
    """Helper to initialize the BigQuery client securely using the env variable."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_json:
        raise RuntimeError(
            "CRITICAL ERROR: 'GOOGLE_CREDENTIALS_JSON' environment variable is missing."
        )
        
    try:
        info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(project=info.get("project_id"), credentials=credentials)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Google Credentials JSON: {str(e)}")

@mcp.tool()
def get_table_schema(project_id: str, dataset_id: str, table_id: str) -> str:
    """Fetches the schema of an existing BigQuery table. Use this when a user wants to modify an existing table."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    try:
        client = get_bq_client()
        table = client.get_table(table_ref)
        schema_output = f"Current Schema for {table_ref}:\n"
        
        for field in table.schema:
            schema_output += f"- Column: {field.name} | Type: {field.field_type}\n"
            if field.field_type == "RECORD":
                schema_output += f"  *(Note: '{field.name}' is a nested RECORD structure.)*\n"
                
        return schema_output
    except Exception as e:
        return f"Error fetching table {table_ref} (it might not exist yet): {str(e)}"

@mcp.tool()
def generate_update_script(project_id: str, dataset_id: str, table_id: str, new_column_name: str, column_type: str, location_notes: str = "end") -> str:
    """Generates the SQL script needed to alter an existing table by adding a column."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    sql_command = f"ALTER TABLE `{table_ref}`\nADD COLUMN `{new_column_name}` {column_type.upper()};"
    
    if location_notes.lower() != "end":
        sql_command += f"\n\n/* URGENT NOTE FOR DE TEAM: Requestor asked for insertion at: '{location_notes}'. BigQuery requires manual struct recreation for nested insertions. */"
        
    return f"I have collated the request! Here is the script for the DE team:\n\n```sql\n{sql_command}\n```"

@mcp.tool()
def generate_create_table_script(project_id: str, dataset_id: str, table_id: str, columns_definition: str) -> str:
    """Generates a CREATE TABLE SQL script for the DE team when a user wants to build a brand new table. 
    Accepts a raw string list or description of columns and structures provided by the user."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    sql_command = f"CREATE TABLE `{table_ref}` (\n"
    sql_command += f"  /* TODO: Review and format the user's requested columns below */\n"
    sql_command += f"  {columns_definition}\n"
    sql_command += f");"
    
    return (
        f"I have collated the new table request! Here is the setup script for the DE team:\n\n"
        f"```sql\n{sql_command}\n```\n\n"
        f"@Data_Engineering_Team: Please provision this table in project `{project_id}` under dataset `{dataset_id}`. Reply with 'complete' when done."
    )

if __name__ == "__main__":
    render_port = int(os.environ.get("PORT", "10000"))
    mcp.run(transport="sse", host="0.0.0.0", port=render_port)
