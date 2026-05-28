# SQLite Persistence Design

## Goal

Add a production-hardening persistence layer for notification settings and registered vendors while preserving the existing FastAPI response shapes and frontend behavior.

## Scope

This slice covers DB-backed storage for:

- Notification settings currently handled by `src/settings_store.py`.
- Registered vendor onboarding records currently handled by `src/vendor_store.py`.

This slice does not cover real calendar OAuth, notification retry/dead-letter queues, or richer onboarding workflows.

## Design

Use SQLite as the first production-like backend because it is available in the Python standard library, works in local development and tests without external services, and creates a clean seam for a future Postgres implementation.

Keep the current store method contracts stable:

- `SettingsStore.load() -> NotificationSettings`
- `SettingsStore.save(settings: NotificationSettings) -> None`
- `SettingsStore.update(partial: dict[str, Any]) -> NotificationSettings`
- `VendorStore.list_vendors() -> list[dict]`
- `VendorStore.get_vendor(id_or_vendor_id: str) -> dict | None`
- `VendorStore.add_vendor(vendor: VendorRecord) -> dict`
- `VendorStore.update_vendor_status(vendor_id: str, new_status: str) -> dict`

Add SQLite-backed store classes and a small factory layer selected by environment variables:

- `SUPPLIER_COLLAB_STORE_BACKEND=json|sqlite`, default `json` for backwards compatibility.
- `SUPPLIER_COLLAB_DB_PATH=config/supplier_collab.db`, used when backend is `sqlite`.

The FastAPI app and scheduler should construct stores through the factory, not by directly instantiating JSON-backed classes. Tests can still instantiate concrete classes directly with temporary paths.

## SQLite Schema

`notification_settings`

- `id TEXT PRIMARY KEY`, fixed value `default`
- `payload_json TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

The payload remains the Pydantic `NotificationSettings` JSON document. This avoids premature table design for fields that are still evolving.

`vendors`

- `id TEXT PRIMARY KEY`
- `vendor_id TEXT NOT NULL UNIQUE`
- `vendor_name TEXT NOT NULL`
- `category TEXT NOT NULL`
- `tier TEXT NOT NULL`
- `status TEXT NOT NULL`
- `created_at TEXT NOT NULL`

## Error Handling

- Loading settings with no DB row returns `NotificationSettings()` defaults.
- Unknown settings keys are ignored, matching current JSON behavior.
- Adding a duplicate `vendor_id` raises `ValueError` with the same "already exists" wording expected by API tests.
- Looking up an unknown vendor returns `None`.
- Updating an unknown vendor status raises `ValueError` with "not found" wording.

## Testing

Add tests that instantiate SQLite stores with a temporary DB path and prove:

- Settings default load works with an empty DB.
- Settings save/reload survives a new store instance.
- Partial update ignores unknown keys.
- Vendor list starts empty.
- Vendor add/list/get survives a new store instance.
- Duplicate vendor ID is rejected.
- Vendor status update persists.
- The factory selects JSON by default and SQLite when env vars are set.

Existing API tests should continue to pass because route behavior and response shapes do not change.

## Documentation

Update README/AGENTS/CLAUDE/TODO or implementation docs to note that Phase 10 has started with selectable JSON/SQLite persistence.
