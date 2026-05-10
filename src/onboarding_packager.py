import io
import zipfile
import yaml
from pathlib import Path

def generate_onboarding_pack(vendor_name: str, vendor_id: str) -> io.BytesIO:
    """Generates a zip file containing blank CSV templates based on schema definitions."""
    mem_zip = io.BytesIO()
    schemas_dir = Path("data/schemas")
    
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Add instructions
        instructions = f"""# Onboarding Data Request: {vendor_name} ({vendor_id})

Please provide historical performance data matching the included CSV templates. 
Once complete, these files should be uploaded to your designated landing zone.

**Required Files:**
- vendor_performance_template.csv
- purchase_orders_template.csv

**Optional Phase 8 Files:**
- inventory_position_template.csv
- demand_forecast_template.csv
- asn_receipts_template.csv
- chargebacks_template.csv
- trade_funds_template.csv
"""
        zf.writestr("instructions.md", instructions)
        
        # 2. Add CSV templates from schemas
        if schemas_dir.exists():
            for schema_file in schemas_dir.glob("*.schema.yaml"):
                try:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        schema = yaml.safe_load(f)
                        
                    # Use column_types (covers all required + optional columns)
                    columns = schema.get("column_types", {})
                    col_names = list(columns.keys())
                    
                    if col_names:
                        csv_content = ",".join(col_names) + "\n"
                        csv_filename = schema_file.stem.replace(".schema", "") + "_template.csv"
                        zf.writestr(f"templates/{csv_filename}", csv_content)
                except Exception:
                    continue
                    
    mem_zip.seek(0)
    return mem_zip
