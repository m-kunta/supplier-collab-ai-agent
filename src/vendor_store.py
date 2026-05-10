from __future__ import annotations

import json
import logging
import uuid
import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class VendorRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vendor_id: str
    vendor_name: str
    category: str
    tier: str
    status: str = "pending_data"
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

class VendorStore:
    """Persistent store for dynamically onboarded vendors."""
    
    def __init__(self, path: str = "config/vendors.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"vendors": []})

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error reading vendor store: {}", e)
            return {"vendors": []}

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_vendors(self) -> List[dict]:
        """Return all registered vendors."""
        data = self._read()
        return data.get("vendors", [])
        
    def get_vendor(self, id_or_vendor_id: str) -> dict | None:
        """Find a vendor by uuid or string vendor_id."""
        for v in self.list_vendors():
            if v["id"] == id_or_vendor_id or v["vendor_id"] == id_or_vendor_id:
                return v
        return None

    def add_vendor(self, vendor: VendorRecord) -> dict:
        """Register a new vendor."""
        data = self._read()
        vendors = data.get("vendors", [])
        
        # Check if exists by vendor_id
        for v in vendors:
            if v["vendor_id"] == vendor.vendor_id:
                raise ValueError(f"Vendor with ID {vendor.vendor_id} already exists.")
                
        rec = vendor.model_dump()
        vendors.append(rec)
        data["vendors"] = vendors
        self._write(data)
        return rec

    def update_vendor_status(self, vendor_id: str, new_status: str) -> dict:
        """Update the onboarding status of a vendor."""
        data = self._read()
        vendors = data.get("vendors", [])
        updated = None
        for v in vendors:
            if v["vendor_id"] == vendor_id or v["id"] == vendor_id:
                v["status"] = new_status
                updated = v
                break
                
        if updated:
            self._write(data)
            return updated
        raise ValueError(f"Vendor {vendor_id} not found.")
