import os
import json

# 1. Force FastMCP to use Render's assigned dynamic port
os.environ["MCP_PORT"] = os.environ.get("PORT", "8000")
os.environ["MCP_HOST"] = "0.0.0.0"

from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery
from google.oauth2 import service_account

mcp = FastMCP("BigQueryRequestManager")

# 2. Authenticate with Google Cloud securely
creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if creds_json:
    info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(info)
    client = bigquery.Client(project=info.get("project_id"), credentials=credentials)
else:
    # Fallback if testing locally
    client = bigquery.Client()

@mcp.tool()
def get_table_schema(project_id: str, dataset_id: str, table_id: str) -> str:
    """Fetches the schema of a BigQuery table."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    try:
        table = client.get_table(table_ref)
        schema_output = f"Current Schema for {table_ref}:\n"
        
        for field in table.schema:
            schema_output += f"- Column: {field.name} | Type: {field.field_type}\n"
            if field.field_type == "RECORD":
                schema_output += f"  *(Note: '{field.name}' is a nested RECORD structure.)*\n"
                
        return schema_output
    except Exception as e:
        return f"Error fetching table {table_ref}: {str(e)}"

@mcp.tool()
def generate_update_script(project_id: str, dataset_id: str, table_id: str, new_column_name: str, column_type: str, location_notes: str = "end") -> str:
    """Generates the SQL script needed to add a column, for the DE team."""
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    sql_command = f"ALTER TABLE `{table_ref}`\nADD COLUMN `{new_column_name}` {column_type.upper()};"
    
    if location_notes.lower() != "end":
        sql_command += f"\n\n/* URGENT NOTE FOR DE TEAM: Requestor asked for insertion at: '{location_notes}'. BigQuery requires manual struct recreation for nested insertions. */"
        
    return f"I have collated the request! Here is the script for the DE team:\n\n```sql\n{sql_command}\n```"

if __name__ == "__main__":
    mcp.run(transport="sse")
