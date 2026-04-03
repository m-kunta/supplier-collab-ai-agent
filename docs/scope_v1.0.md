# Supplier Collaboration Briefing Agent — Scope Document v1.0

**Project:** `supplier-collab-ai-agent`
**Repository:** `m-kunta/supplier-collab-ai-agent`
**Description:** Pre-meeting intelligence agent for supplier collaboration — turns scattered vendor performance data into synthesized, actionable briefing documents in seconds
**Author:** Mohith Kunta ([@m-kunta](https://github.com/m-kunta))
**Date:** March 26, 2026
**Status:** Scoping Complete — Ready for MVP Build

---

## 1. Problem Statement

Buyer and supply planning meetings with vendors are among the highest-leverage touchpoints in the supply chain — yet the pre-meeting prep is one of the most fragmented, manual workflows in the enterprise. A typical buyer preparing for a vendor review must:

- Pull vendor scorecard data from the supplier performance system
- Check open POs and inbound pipeline status across WMS/OMS
- Review recent OOS events and trace them back to vendor root causes
- Cross-reference upcoming promo commitments against confirmed inventory
- Benchmark the vendor's metrics against category peers and best-in-class performers

This scavenger hunt across 4–6 systems takes 30–90 minutes per vendor, produces inconsistent outputs, and — critically — generates *data* without *insight*. The buyer walks into the meeting with numbers but not a narrative: no synthesized view of what matters most, what to push on, what to acknowledge as improving.

**The gap is not data access. It's contextual synthesis at the speed of the meeting cadence.**

---

## 2. Solution Overview

The **Supplier Collaboration Briefing Agent** is a pre-meeting intelligence tool that ingests vendor scorecards, open POs, OOS events, and promo commitments from standardized CSV file exports, then generates a structured buyer briefing document via Claude — synthesized, benchmarked, and ready to drive a productive vendor conversation.

### What Makes This an AI Problem (Not a Dashboard)

| Capability | Dashboard / BI Tool | Briefing Agent (Claude) |
|---|---|---|
| Show fill rate trend | ✅ Static chart | ✅ Trend + narrative ("fill rate dropped 4pts after DC consolidation in Week 12") |
| Open PO list | ✅ Table | ✅ POs flagged by risk: late vs. promo-dependent vs. routine |
| OOS events | ✅ Count/list | ✅ Root-cause attribution: "62% of OOS tied to vendor shorts, not demand spikes" |
| Promo readiness | ❌ Separate system | ✅ Cross-referenced: "Easter TPR on SKU 4421 depends on PO #8812 landing by 4/2 — currently 3 days late" |
| Benchmarking | ✅ Peer avg | ✅ Contextual: "Lead time variability is 2.1x the category best-in-class — the single biggest driver of your safety stock cost" |
| Talking points | ❌ | ✅ Prioritized agenda: top 3 issues, top 1 recognition, suggested ask |

### Key Design Principle: System-Agnostic Integration

The agent does not connect directly to ERPs or planning systems. Instead, it reads **standardized CSV files** dropped into a data landing zone. This means:

- Works with any source system that can export flat files (all of them can)
- Zero API development required for initial deployment
- Mock data and production data use the exact same file format
- Every briefing is traceable to the exact source files that fed it
- New data domains are added by defining a new file schema, not building a new connector

---

## 3. User Personas

### Primary: Category Buyer / Merchandiser

- **Goal:** Walk into vendor meetings prepared, with leverage and context
- **Pain:** Prep is manual, inconsistent, and data-heavy but insight-light
- **Briefing emphasis:** Promo compliance, cost/price competitiveness, OOS impact on sales, negotiation talking points

### Secondary: Supply Planning Manager

- **Goal:** Align with buyers on vendor performance issues that drive replenishment exceptions
- **Pain:** Planners see the symptoms (exceptions, phantom inventory) but lack vendor-level rollup
- **Briefing emphasis:** Fill rate & OTD trends, lead time variability, order accuracy, ASN timeliness, DC impact

### Output Design: Unified Document, Dual Emphasis

The briefing is a single document with clearly labeled sections so both personas can scan to their priority areas. Shared sections (scorecard summary, risk flags) appear first; persona-specific deep-dives follow.

---

## 4. Trigger Model

### Manual Trigger (v1)

Buyer or planner requests a briefing via the agent interface:

```
python cli.py --vendor "Kelloggs" --date "2026-04-03" --data-dir /data/inbound/prod/
```

The agent reads the data landing zone, filters to the requested vendor, and generates the briefing for a configurable lookback window (default: trailing 13 weeks).

### Calendar-Driven Trigger (v1.5)

Agent monitors the buyer's meeting calendar for vendor-tagged events. When a vendor meeting is detected:

1. **T-24h:** Auto-generates a draft briefing and delivers via email/Teams notification
2. **T-2h:** Refreshes with any intraday PO/receipt updates and sends final version
3. **Post-meeting (stretch):** Buyer logs action items → agent archives the briefing + outcomes for longitudinal tracking

### Trigger Metadata

| Field | Description | Required |
|---|---|---|
| `vendor_id` | Vendor number or name (resolved to canonical ID via vendor_master.csv) | Yes |
| `meeting_date` | Scheduled meeting date | Yes (manual) / Auto (calendar) |
| `data_dir` | Path to data landing zone (default: `/data/inbound/`) | No |
| `lookback_weeks` | Data window for trends (default: 13) | No |
| `category_filter` | Limit to specific categories if vendor spans multiple | No |
| `include_benchmarks` | Include best-in-class comparison (default: true) | No |
| `persona_emphasis` | `buyer`, `planner`, or `both` (default: `both`) | No |
| `output_format` | `docx`, `md`, or `both` (default: `docx`) | No |

---

## 5. Data Integration Layer

### 5.1 Architecture

The agent uses a **file-based integration layer** as its universal data interface. Source systems export standardized CSV files to a landing zone; the agent reads them through a manifest-driven loader with schema validation.

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCE SYSTEMS                               │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Blue     │ │  SAP     │ │  Oracle  │ │Manhattan │  ...       │
│  │ Yonder   │ │  MM/SD   │ │  Retail  │ │  WMS     │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │             │             │             │                 │
│       ▼             ▼             ▼             ▼                 │
│  ┌──────────────────────────────────────────────────┐            │
│  │          EXPORT / ETL / SCHEDULED EXTRACT         │            │
│  │     (existing ERP export jobs or new queries)     │            │
│  └──────────────────────┬───────────────────────────┘            │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼  CSV files in standardized schema
                ┌─────────────────────┐
                │   DATA LANDING ZONE │
                │   /data/inbound/    │
                │                     │
                │  manifest.yaml      │
                │  vendor_master.csv  │
                │  purchase_orders.csv│
                │  vendor_perf.csv    │
                │  inventory_pos.csv  │
                │  oos_events.csv     │
                │  promo_calendar.csv │
                │  asn_receipts.csv   │
                │  demand_forecast.csv│
                │  chargebacks.csv    │
                │  trade_funds.csv    │
                └────────┬────────────┘
                         │
                         ▼
                ┌─────────────────────┐
                │   VALIDATION LAYER  │
                │                     │
                │  Schema checks      │
                │  Type coercion      │
                │  Range validation   │
                │  Referential checks │
                │  Freshness checks   │
                └────────┬────────────┘
                         │
                         ▼
                ┌─────────────────────┐
                │   BRIEFING AGENT    │
                │   PIPELINE          │
                └─────────────────────┘
```

### 5.2 File Format Standards

| Rule | Specification |
|------|---------------|
| **Format** | CSV (RFC 4180 compliant) with UTF-8 encoding |
| **Delimiter** | Comma (`,`) — fields containing commas must be quoted |
| **Header row** | Required — first row is always column names |
| **Date format** | `YYYY-MM-DD` (ISO 8601) |
| **Datetime format** | `YYYY-MM-DDTHH:MM:SS` (ISO 8601, local time) |
| **Numeric format** | No thousands separators; decimal point (`.`) not comma |
| **Currency** | Raw numeric (e.g., `3.50` not `$3.50`) |
| **Percentage** | Decimal (e.g., `0.942` for 94.2%) — NOT `94.2` |
| **Null/missing** | Empty string (`,,`) — not `NULL`, `N/A`, or `0` |
| **Boolean** | `true` / `false` (lowercase) |
| **File naming** | `{domain}_{YYYYMMDD}.csv` for dated extracts; `{domain}.csv` for current-state snapshots |

### 5.3 File Inventory

The agent consumes 10 standardized CSV files. Three are required; seven are optional and enable additional briefing sections when present.

| File | Domain | Required | Refresh | Enables |
|------|--------|----------|---------|---------|
| `vendor_master.csv` | Vendor reference data | **Yes** | Weekly | Vendor resolution, contact info, category assignment |
| `purchase_orders.csv` | Open and recent POs | **Yes** | Daily | PO pipeline, risk tiering, fill analysis |
| `vendor_performance.csv` | Weekly KPI metrics | **Yes** | Weekly | Scorecard, benchmarking, trend analysis |
| `inventory_position.csv` | Current inventory snapshot | No | Daily | Promo readiness, days-of-supply, OOS context |
| `oos_events.csv` | Out-of-stock occurrences | No | Daily | OOS impact analysis, vendor attribution |
| `promo_calendar.csv` | Promotional events | No | Weekly | Promo readiness, PO×Promo linkage |
| `asn_receipts.csv` | ASN and receiving data | No | Daily | ASN quality metrics, receipt accuracy |
| `demand_forecast.csv` | Weekly demand forecasts | No | Weekly | OOS attribution accuracy, forecast bias |
| `chargebacks.csv` | Vendor chargebacks | No | Weekly | Compliance cost analysis |
| `trade_funds.csv` | Trade fund commitments | No | Weekly | Trade fund compliance in buyer section |

---

## 6. Data Contract — File Schemas

### 6.1 Vendor Master (`vendor_master.csv`)

The canonical vendor reference. One row per vendor.

| Column | Type | Required | Description | ERP Source Example |
|--------|------|----------|-------------|--------------------|
| `vendor_id` | string | Yes | Unique vendor identifier | SAP: LIFNR; BY: supplier_id; Oracle: vendor_id |
| `vendor_name` | string | Yes | Legal / trading name | SAP: NAME1; BY: supplier_name |
| `vendor_status` | enum | Yes | `active`, `inactive`, `on_hold`, `new` | SAP: LOEVM/SPERM flags |
| `primary_category` | string | Yes | Main merchandise category | SAP: MATKL; BY: category_code |
| `secondary_categories` | string | No | Pipe-delimited additional categories | Derived from item-vendor assignments |
| `buyer_name` | string | No | Assigned category buyer | Internal assignment system |
| `planner_name` | string | No | Assigned supply planner | Internal assignment system |
| `vendor_contact_name` | string | No | Primary vendor rep | Vendor portal / CRM |
| `vendor_contact_email` | string | No | Vendor rep email | Vendor portal / CRM |
| `lead_time_days_contracted` | integer | No | Contractual standard lead time | SAP: PLIFZ; BY: lead_time |
| `payment_terms` | string | No | e.g., `NET30`, `2/10NET30` | SAP: ZTERM |
| `ship_from_location` | string | No | Vendor DC or plant location | SAP: WERKS |
| `onboarding_date` | date | No | Date vendor was first active | SAP: ERDAT |

### 6.2 Purchase Orders (`purchase_orders.csv`)

Open and recently closed POs. One row per PO line. Refreshed daily.

| Column | Type | Required | Description | ERP Source Example |
|--------|------|----------|-------------|--------------------|
| `po_number` | string | Yes | Purchase order number | SAP: EBELN; BY: order_id |
| `po_line` | integer | Yes | Line number within PO | SAP: EBELP |
| `vendor_id` | string | Yes | FK to vendor_master | SAP: LIFNR |
| `sku` | string | Yes | Item/SKU identifier | SAP: MATNR; BY: item_id |
| `sku_description` | string | Yes | Item description | SAP: MAKTX |
| `uom` | string | Yes | Unit of measure (`EA`, `CS`, `PL`) | SAP: BSTME |
| `qty_ordered` | numeric | Yes | Quantity ordered | SAP: MENGE |
| `qty_shipped` | numeric | No | Quantity shipped per ASN | ASN / goods receipt |
| `qty_received` | numeric | No | Quantity received at DC | WMS / SAP: WEMNG |
| `po_create_date` | date | Yes | PO creation date | SAP: BEDAT |
| `requested_delivery_date` | date | Yes | Agreed delivery date | SAP: EINDT |
| `actual_ship_date` | date | No | Actual vendor ship date | ASN / TMS |
| `actual_receipt_date` | date | No | Actual DC receipt date | WMS goods receipt |
| `po_status` | enum | Yes | `open`, `confirmed`, `shipped`, `in_transit`, `received`, `late`, `cancelled` | Derived |
| `ship_to_dc` | string | Yes | Destination DC identifier | SAP: WERKS |
| `unit_cost` | numeric | Yes | PO unit cost | SAP: NETPR |
| `extended_cost` | numeric | Yes | qty_ordered × unit_cost | Derived |
| `promo_flag` | boolean | No | PO supports a promo event | Derived from promo_calendar |
| `promo_event_id` | string | No | FK to promo_calendar | Trade promo system |
| `need_date` | date | No | Date inventory must arrive | Replenishment system |
| `carrier` | string | No | Carrier/transport provider | TMS / ASN |
| `asn_number` | string | No | Linked ASN identifier | EDI 856 |
| `notes` | string | No | PO notes or buyer comments | ERP notes field |

**Agent-computed derived fields:**
- `days_late` = `actual_receipt_date` - `requested_delivery_date` (or `today` - `requested_delivery_date` if not received)
- `days_until_need_date` = `need_date` - `today`
- `fill_pct` = `qty_shipped` / `qty_ordered`

### 6.3 Vendor Performance Metrics (`vendor_performance.csv`)

Weekly aggregated KPIs. One row per vendor per metric per week. This "long format" means adding a new metric is just adding rows, not altering the schema.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `vendor_id` | string | Yes | FK to vendor_master |
| `week_ending` | date | Yes | Saturday end of measurement week |
| `metric_code` | enum | Yes | See metric code table below |
| `metric_value` | numeric | Yes | Metric value (decimal for %, integer for counts, numeric for $) |
| `metric_uom` | enum | Yes | `pct`, `days`, `count`, `usd`, `ratio` |
| `denominator` | numeric | No | Denominator for rate metrics (e.g., total POs for OTD) |
| `numerator` | numeric | No | Numerator for rate metrics (e.g., on-time POs for OTD) |

**Metric Code Reference:**

| `metric_code` | Metric Name | `metric_uom` | Tier |
|----------------|-------------|--------------|------|
| `OTD` | On-Time Delivery | `pct` | Delivery & Fulfillment |
| `FILL_RATE` | Fill Rate | `pct` | Delivery & Fulfillment |
| `ORDER_ACCURACY` | Order Accuracy | `pct` | Delivery & Fulfillment |
| `LEAD_TIME_AVG` | Lead Time Average | `days` | Delivery & Fulfillment |
| `LEAD_TIME_VAR` | Lead Time Variability (σ) | `days` | Delivery & Fulfillment |
| `ASN_TIMELINESS` | ASN Timeliness | `pct` | Delivery & Fulfillment |
| `ASN_ACCURACY` | ASN Accuracy | `pct` | Delivery & Fulfillment |
| `DEFECT_RATE` | Defect Rate | `pct` | Compliance & Quality |
| `COMPLIANCE_RATE` | Compliance Rate | `pct` | Compliance & Quality |
| `CHARGEBACK_COUNT` | Chargeback Count | `count` | Compliance & Quality |
| `CHARGEBACK_AMT` | Chargeback Amount | `usd` | Compliance & Quality |
| `PRICE_COMP` | Price Competitiveness | `ratio` | Commercial & Cost |
| `PROMO_FUND_COMP` | Promo Funding Compliance | `pct` | Commercial & Cost |
| `COST_VARIANCE` | Cost Variance | `usd` | Commercial & Cost |
| `ORDER_VARIABILITY` | Order Variability (Vendor-side) | `ratio` | Order Behavior |

**ERP Source Mapping:**

| Metric | Blue Yonder / JDA | SAP MM/SD | Oracle Retail | Manhattan WMS |
|--------|-------------------|-----------|---------------|---------------|
| OTD | Delivery perf report → on_time_flag | ME2M + EKBE (GR date vs. EINDT) | PO receipt vs. promised date | Receipt date vs. expected |
| Fill Rate | ASN qty vs PO qty | WEMNG / MENGE from EKPO/EKBE | Shipped qty / ordered qty | ASN vs receipt reconciliation |
| Lead Time | Order date → receipt date | BEDAT → BUDAT (goods receipt) | PO creation → receipt posting | PO release → putaway complete |
| ASN Timeliness | ASN timestamp vs ship date | IDOC/EDI 856 timestamp vs GR | ASN receipt time vs delivery | ASN receipt vs dock appt |
| Defect Rate | Quality holds / total received | QM module: inspection lots | RTV records | Exception/damage at receiving |
| Compliance | Chargeback triggers | Vendor evaluation (ME61) | Vendor scorecard module | Receiving compliance checks |

### 6.4 Inventory Position (`inventory_position.csv`)

Current inventory snapshot. One row per SKU per location. Refreshed daily.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `sku` | string | Yes | Item/SKU identifier |
| `sku_description` | string | Yes | Item description |
| `location_id` | string | Yes | DC or store identifier |
| `location_type` | enum | Yes | `dc`, `store` |
| `vendor_id` | string | Yes | Primary vendor for this SKU |
| `qty_on_hand` | numeric | Yes | Current available inventory |
| `qty_allocated` | numeric | No | Allocated to outbound orders |
| `qty_in_transit` | numeric | No | On inbound POs, shipped not received |
| `qty_on_order` | numeric | No | On open POs, not yet shipped |
| `safety_stock_qty` | numeric | No | Calculated safety stock level |
| `reorder_point` | numeric | No | Reorder point quantity |
| `avg_daily_demand` | numeric | No | Trailing average daily sales |
| `days_of_supply` | numeric | No | qty_on_hand / avg_daily_demand |
| `last_receipt_date` | date | No | Most recent receipt of this SKU |
| `snapshot_date` | date | Yes | Date of this inventory snapshot |

### 6.5 Out-of-Stock Events (`oos_events.csv`)

Historical OOS occurrences. One row per OOS event (SKU × location × occurrence). Refreshed daily.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `oos_event_id` | string | Yes | Unique event identifier |
| `sku` | string | Yes | Affected SKU |
| `sku_description` | string | Yes | Item description |
| `vendor_id` | string | Yes | Primary vendor for this SKU |
| `location_id` | string | Yes | Store or DC where OOS occurred |
| `location_type` | enum | Yes | `dc`, `store` |
| `oos_start_date` | date | Yes | Date OOS condition detected |
| `oos_end_date` | date | No | Date OOS resolved (empty if active) |
| `duration_hours` | numeric | No | Total hours out of stock |
| `root_cause` | enum | Yes | `vendor_short`, `demand_spike`, `dc_miss`, `phantom_inventory`, `receiving_delay`, `allocation_error`, `discontinued`, `other` |
| `root_cause_detail` | string | No | Free-text explanation |
| `estimated_lost_sales_units` | numeric | No | Units of demand missed |
| `estimated_lost_sales_usd` | numeric | No | Revenue impact |
| `demand_forecast_qty` | numeric | No | Forecasted demand for SKU/week |
| `actual_demand_qty` | numeric | No | Actual demand observed |
| `related_po_number` | string | No | PO expected to prevent this OOS |
| `recurrence_flag` | boolean | No | Same SKU OOS >2x in lookback window |

### 6.6 Promotion Calendar (`promo_calendar.csv`)

Upcoming and recent promos. One row per promo event per SKU. Refreshed weekly.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `promo_event_id` | string | Yes | Unique promo event identifier |
| `promo_name` | string | Yes | Event name (e.g., "Easter Cereal TPR") |
| `vendor_id` | string | Yes | FK to vendor_master |
| `sku` | string | Yes | Promoted SKU |
| `sku_description` | string | Yes | Item description |
| `promo_type` | enum | Yes | `tpr`, `bogo`, `display`, `ad_feature`, `coupon`, `bundle`, `clearance` |
| `promo_start_date` | date | Yes | In-store start date |
| `promo_end_date` | date | Yes | In-store end date |
| `promo_status` | enum | Yes | `planned`, `confirmed`, `active`, `completed`, `cancelled` |
| `committed_qty` | numeric | Yes | Vendor-committed supply quantity |
| `committed_funding_usd` | numeric | No | Vendor-committed trade funds |
| `actual_qty_delivered` | numeric | No | Actual quantity delivered (post-promo) |
| `actual_funding_usd` | numeric | No | Actual trade funds invoiced/paid |
| `promo_fill_pct` | numeric | No | actual_qty / committed_qty (post-promo) |
| `inventory_need_date` | date | No | Date inventory must be in DC |
| `store_count` | integer | No | Stores participating |
| `expected_lift_pct` | numeric | No | Forecasted demand lift |
| `category` | string | No | Merchandise category |

### 6.7 ASN & Receipt Data (`asn_receipts.csv`)

Advance ship notices and receiving records. One row per ASN line. Refreshed daily.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `asn_number` | string | Yes | ASN identifier |
| `asn_line` | integer | Yes | Line number within ASN |
| `vendor_id` | string | Yes | FK to vendor_master |
| `po_number` | string | Yes | Related PO number |
| `po_line` | integer | Yes | Related PO line |
| `sku` | string | Yes | Shipped SKU |
| `qty_shipped` | numeric | Yes | Quantity vendor shipped |
| `qty_received` | numeric | No | Quantity actually received |
| `qty_damaged` | numeric | No | Quantity damaged/rejected |
| `ship_date` | date | Yes | Date vendor shipped |
| `expected_arrival_date` | date | No | Estimated arrival at DC |
| `actual_arrival_date` | date | No | Actual arrival at DC |
| `asn_sent_datetime` | datetime | Yes | Timestamp ASN transmitted |
| `asn_received_datetime` | datetime | No | Timestamp ASN received by retailer |
| `receipt_datetime` | datetime | No | Timestamp goods checked in |
| `carrier` | string | No | Carrier/SCAC code |
| `tracking_number` | string | No | Shipment tracking ID |
| `lot_number` | string | No | Lot/batch number |
| `expiry_date` | date | No | Product expiration date |
| `pallet_count` | integer | No | Number of pallets |
| `weight_lbs` | numeric | No | Shipment weight |
| `asn_accuracy_flag` | boolean | No | ASN matched receipt? |

### 6.8 Demand Forecast (`demand_forecast.csv`)

Demand forecasts for OOS attribution and promo readiness. One row per SKU per location per week. Refreshed weekly.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `sku` | string | Yes | Item/SKU identifier |
| `vendor_id` | string | Yes | Primary vendor |
| `location_id` | string | Yes | DC or store |
| `week_ending` | date | Yes | Forecast week (Saturday) |
| `forecast_qty` | numeric | Yes | Forecasted demand quantity |
| `actual_qty` | numeric | No | Actual sales/consumption |
| `forecast_accuracy_pct` | numeric | No | 1 - abs(actual - forecast) / actual |
| `forecast_bias` | numeric | No | (forecast - actual) / actual |
| `is_promo_period` | boolean | No | During a promo event |
| `base_demand_qty` | numeric | No | Non-promotional baseline |

### 6.9 Chargebacks (`chargebacks.csv`)

Vendor chargebacks and compliance violations. One row per chargeback. Refreshed weekly.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `chargeback_id` | string | Yes | Unique chargeback identifier |
| `vendor_id` | string | Yes | FK to vendor_master |
| `po_number` | string | No | Related PO if applicable |
| `chargeback_date` | date | Yes | Date chargeback issued |
| `chargeback_type` | enum | Yes | `routing_violation`, `labeling_error`, `pallet_noncompliance`, `late_delivery`, `overage`, `shortage`, `asn_missing`, `asn_inaccurate`, `quality_defect`, `unauthorized_substitution`, `other` |
| `chargeback_amount_usd` | numeric | Yes | Dollar amount |
| `chargeback_status` | enum | Yes | `issued`, `disputed`, `resolved_paid`, `resolved_waived` |
| `description` | string | No | Detail of violation |
| `resolution_date` | date | No | Date resolved |

### 6.10 Trade Funds (`trade_funds.csv`)

Promotional funding commitments and actuals. One row per fund commitment. Refreshed weekly.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `fund_id` | string | Yes | Unique fund identifier |
| `vendor_id` | string | Yes | FK to vendor_master |
| `promo_event_id` | string | No | FK to promo_calendar if event-specific |
| `fund_type` | enum | Yes | `scan_allowance`, `off_invoice`, `billback`, `lump_sum`, `display_fee`, `slotting`, `coop_ad`, `other` |
| `fund_period_start` | date | Yes | Fund start date |
| `fund_period_end` | date | Yes | Fund end date |
| `committed_amount_usd` | numeric | Yes | Vendor-committed amount |
| `accrued_amount_usd` | numeric | No | Amount accrued to date |
| `invoiced_amount_usd` | numeric | No | Amount invoiced |
| `paid_amount_usd` | numeric | No | Amount collected |
| `fund_status` | enum | Yes | `committed`, `active`, `invoiced`, `paid`, `expired`, `disputed` |
| `compliance_pct` | numeric | No | paid / committed |

---

## 7. Manifest & Validation

### 7.1 Manifest File (`manifest.yaml`)

The manifest is the agent's contract with the data team. It tells the agent what files are available, where to find them, and how fresh they are.

```yaml
version: "1.0"
generated_at: "2026-03-26T08:00:00"
source_system: "Blue Yonder + SAP ECC"
environment: "production"                  # production | staging | mock

data_directory: "./"

files:
  vendor_master:
    filename: "vendor_master.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-25T06:00:00"
    row_count: 142
    required: true

  purchase_orders:
    filename: "purchase_orders_20260326.csv"
    refresh_frequency: "daily"
    last_refreshed: "2026-03-26T05:30:00"
    row_count: 4823
    required: true

  vendor_performance:
    filename: "vendor_performance.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-24T06:00:00"
    row_count: 27690
    required: true

  inventory_position:
    filename: "inventory_position_20260326.csv"
    refresh_frequency: "daily"
    last_refreshed: "2026-03-26T05:00:00"
    row_count: 156420
    required: false

  oos_events:
    filename: "oos_events.csv"
    refresh_frequency: "daily"
    last_refreshed: "2026-03-26T05:45:00"
    row_count: 3241
    required: false

  promo_calendar:
    filename: "promo_calendar.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-24T06:00:00"
    row_count: 892
    required: false

  asn_receipts:
    filename: "asn_receipts.csv"
    refresh_frequency: "daily"
    last_refreshed: "2026-03-26T05:30:00"
    row_count: 18456
    required: false

  demand_forecast:
    filename: "demand_forecast.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-24T06:00:00"
    row_count: 82100
    required: false

  chargebacks:
    filename: "chargebacks.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-24T06:00:00"
    row_count: 1456
    required: false

  trade_funds:
    filename: "trade_funds.csv"
    refresh_frequency: "weekly"
    last_refreshed: "2026-03-24T06:00:00"
    row_count: 634
    required: false

benchmarks:
  method: "compute_from_data"              # compute_from_data | external_file
  bic_percentile: 90
```

### 7.2 Validation Rules

The agent validates every file before processing:

| Rule | Check | Severity |
|------|-------|----------|
| Required columns present | Header row matches schema | Error |
| Data types correct | Dates parse, numerics convert, enums match allowed values | Error |
| Referential integrity | Every `vendor_id` exists in vendor_master.csv | Error |
| PO-promo linkage | If `promo_flag=true`, `promo_event_id` exists in promo_calendar | Warning |
| Percentage range | `pct` values between 0.0 and 1.0 (auto-correct if 0-100 detected) | Warning |
| Positive quantities | qty_ordered, qty_shipped, etc. ≥ 0 | Error |
| Date sequence | `po_create_date` ≤ `requested_delivery_date` | Warning |
| Freshness | `last_refreshed` within expected frequency window | Warning |
| Row count | Manifest `row_count` matches actual file | Warning |
| Duplicates | No duplicate rows on primary key columns | Warning |

### 7.3 Graceful Degradation

The agent generates the best possible briefing with whatever data is available:

| Files Available | Briefing Capability |
|-----------------|---------------------|
| vendor_master + vendor_performance + purchase_orders (minimum) | Exec summary, scorecard, risk flags, PO pipeline, talking points |
| + oos_events | + OOS impact analysis with vendor attribution |
| + promo_calendar | + Promo readiness section with PO linkage |
| + inventory_position | Enhanced risk tiering with current inventory context |
| + asn_receipts | + ASN timeliness/accuracy detail in scorecard |
| + demand_forecast | More accurate vendor vs. demand-driven OOS classification |
| + chargebacks | + Chargeback detail in compliance section |
| + trade_funds | + Trade fund compliance in buyer section |

Missing optional files result in skipped sections with a note: *"[ASN receipt data unavailable — ASN timeliness metrics excluded from this briefing]"*

---

## 8. Scorecard & Benchmarking Engine

### 8.1 Metric Computation

The scorecard engine transforms raw `vendor_performance.csv` data into computed metrics:

- **Current value:** Latest 4-week weighted average
- **4-week trend:** Direction over last 4 weeks (improving / stable / declining)
- **13-week trend:** Direction over full lookback window
- **Trend classification:** Improving (3+ consecutive weeks of improvement >0.5pts), Declining (3+ weeks of decline >0.5pts), Stable (all other)

### 8.2 Benchmarking Layer

| Benchmark Type | Source | Description |
|---|---|---|
| **Category Peer Average** | Computed from all vendors in `vendor_performance.csv` for the same category | Mean performance across all category vendors |
| **Best-in-Class (BIC)** | Top-decile (90th percentile) from `benchmarks.bic_percentile` in manifest | Aspirational target per metric |
| **Vendor's Own Trend** | 13-week and 52-week self-comparison | Historical trajectory |
| **Gap-to-BIC** | Current value − BIC value | Quantified opportunity |

### 8.3 Dollar-Impact Translation

The agent translates benchmark gaps into business terms:

| Gap Type | Formula | Example |
|---|---|---|
| Fill rate gap → lost sales | `gap_pct × weekly_units × avg_selling_price × 52` | "2pt gap = ~$180K annual lost sales" |
| Lead time variability gap → excess safety stock | `(vendor_σ - BIC_σ) × z_score × daily_demand × unit_cost` | "1.7-day σ gap = ~$48K excess safety stock" |
| OTD gap → expedite cost | `late_PO_pct × avg_PO_value × expedite_premium` | "8pt OTD gap = ~$32K annual expedite spend" |
| Defect rate gap → waste cost | `gap_pct × received_units × unit_cost × disposal_factor` | "0.5pt gap = ~$15K annual waste" |

---

## 9. AI Differentiation Layer — Where Claude Adds Value

### 9.1 Contextual Narrative Generation

Claude doesn't just list metrics — it tells the story:

> "Kellogg's fill rate dropped from 96.2% to 91.8% over the past 6 weeks, coinciding with their Atlanta DC consolidation announced in Q4. 73% of shorts are concentrated in 4 cereal SKUs (Frosted Flakes 18oz, Rice Krispies 12oz, Froot Loops 14.7oz, Raisin Bran 18.7oz). This pattern is consistent with a capacity transition rather than a systemic decline — expect normalization by Week 16 if their consolidation timeline holds. Recommended ask: written confirmation of recovery timeline with weekly fill rate targets."

A dashboard shows "91.8%." Claude shows *why* and *what to do about it*.

### 9.2 Cross-Domain Linkage

The highest-value synthesis connects data domains that live in different source files:

- **PO × Promo** (purchase_orders.csv + promo_calendar.csv): "Easter TPR on Frosted Flakes (SKU 4421) depends on PO #8812 — currently 3 days behind ETA. If it misses the 4/2 need date, 142 stores lose ad inventory."
- **Scorecard × OOS** (vendor_performance.csv + oos_events.csv): "62% of this vendor's OOS events trace to fill rate shorts, not demand variability — this is a vendor-controllable problem."
- **Lead Time × Safety Stock** (vendor_performance.csv + inventory_position.csv): "Lead time variability of 3.2 days (σ) vs. category BIC of 1.5 days is the single largest driver of your $214K excess safety stock in this category."

### 9.3 Benchmark Contextualization

Raw benchmarks are table stakes. Claude adds *impact translation*:

- "The 2-point fill rate gap to peer average represents ~$180K in annual lost sales at current velocity."
- "Closing the lead time variability gap to BIC would reduce safety stock by an estimated 1.8 DOH (~$52K working capital release)."

### 9.4 Meeting Prep Recommendations

Claude generates role-specific talking points:

- **For Buyer:** "Lead with the promo fill compliance issue (88% vs. 95% target) — this has direct trade fund clawback implications. Acknowledge the 12% improvement in ASN timeliness since Q4."
- **For Planner:** "Raise the lead time variability trend — propose a joint root-cause session with their logistics team. Share the safety stock impact analysis to frame it as a mutual cost issue."

---

## 10. Output Specification — The Briefing Document

### Document Structure

```
┌─────────────────────────────────────────────────────┐
│  SUPPLIER COLLABORATION BRIEFING                     │
│  Vendor: [Name] (#[ID])                              │
│  Meeting Date: [Date]   Generated: [Timestamp]       │
│  Prepared for: [Buyer Name] / [Planner Name]         │
│  Data sources: [file list + freshness from manifest] │
├─────────────────────────────────────────────────────┤
│                                                       │
│  1. EXECUTIVE SUMMARY (3-5 sentences)                │
│     Overall vendor health + #1 issue + #1 win        │
│                                                       │
│  2. SCORECARD SNAPSHOT                               │
│     Metric | Current | Trend | Peer Avg | BIC | Gap  │
│     Gap-to-BIC callouts with business $ impact       │
│                                                       │
│  3. RISK FLAGS (Prioritized)                         │
│     🔴 Critical issues requiring vendor action       │
│     🟡 Watch items with trend context                │
│                                                       │
│  4. OPEN PO & INBOUND PIPELINE                       │
│     Risk-tiered PO summary table                     │
│     Promo-dependent PO callouts                      │
│                                                       │
│  5. OOS IMPACT ANALYSIS                              │
│     Vendor-attributable OOS summary                  │
│     Repeat offender SKUs                             │
│     Estimated lost sales ($)                         │
│                                                       │
│  6. PROMO READINESS                                  │
│     Upcoming promo supply status (🟢🟡🔴)           │
│     At-risk events with specific PO linkage          │
│     Past promo compliance scorecard                  │
│                                                       │
│  7. BUYER FOCUS: COMMERCIAL & NEGOTIATION            │
│     Price competitiveness insights                   │
│     Trade fund compliance                            │
│     Suggested asks / leverage points                 │
│                                                       │
│  8. PLANNER FOCUS: OPERATIONAL & REPLENISHMENT       │
│     Lead time & variability impact                   │
│     ASN quality and receiving efficiency             │
│     Safety stock / DOH implications                  │
│                                                       │
│  9. RECOMMENDED TALKING POINTS                       │
│     Top 3 issues to raise (with data citations)      │
│     Top 1 vendor win to acknowledge                  │
│     Specific ask with proposed resolution            │
│                                                       │
│  10. APPENDIX                                        │
│      Full metric tables, PO detail, SKU lists        │
│      Data source lineage: files, dates, row counts   │
│                                                       │
│  FOOTER: "Generated by Supplier Collab AI |          │
│  Confidential — Internal Use Only"                   │
└─────────────────────────────────────────────────────┘
```

### Tone & Style

- **Executive, not academic** — every sentence earns its place
- **Data-backed assertions** — no vague "performance needs improvement"; instead: "Fill rate declined from 96.2% → 91.8% over 6 weeks, with 73% of shorts concentrated in 4 SKUs"
- **Balanced** — acknowledge improvements, not just problems. Vendors respond better to fair assessments
- **Actionable** — every flag includes a suggested resolution or ask

---

## 11. Technical Architecture

```
                          ┌──────────────────┐
                          │  Calendar System  │
                          │  (Outlook/Teams)  │
                          └────────┬─────────┘
                                   │ T-24h trigger
                                   ▼
┌──────────┐  manual    ┌─────────────────────────────────────┐
│  Buyer / │  request   │         BRIEFING AGENT              │
│  Planner │──────────▶│         ORCHESTRATOR                │
└──────────┘            │                                     │
                        │  1. Read manifest.yaml              │
                        │  2. Validate & load CSVs            │
                        │  3. Filter to vendor                │
                        │  4. Compute scorecard + benchmarks  │
                        │  5. Compute cross-domain linkages   │
                        │  6. Assemble prompt + call Claude   │
                        │  7. Render DOCX / markdown          │
                        └──────┬──────────────────────────────┘
                               │
          ┌────────────────────┼───────────────────┐
          ▼                    ▼                    ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────────┐
│  Data Layer    │  │  Compute Layer │  │  AI Layer          │
│                │  │                │  │                    │
│ data_loader.py │  │ scorecard_     │  │  Claude API        │
│   ↓            │  │   engine.py    │  │   ↓                │
│ Reads manifest │  │ benchmark_     │  │  Narrative gen     │
│ Loads CSVs     │  │   engine.py    │  │  Cross-domain      │
│ Validates      │  │ po_risk_       │  │    synthesis       │
│ Filters vendor │  │   engine.py    │  │  Talking points    │
│                │  │ oos_           │  │  Risk flags        │
│ 10 CSV schemas │  │   attribution  │  │                    │
│ manifest.yaml  │  │   .py          │  │  briefing_         │
│                │  │ promo_         │  │   system_prompt.md │
│                │  │   readiness.py │  │                    │
└────────────────┘  └────────────────┘  └────────────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Output Layer        │
                    │                      │
                    │  doc_renderer.js      │
                    │  briefing_template.js │
                    │                      │
                    │  → DOCX / Markdown   │
                    │  → Email / Teams     │
                    │  → Shared drive      │
                    └──────────────────────┘
```

---

## 12. ERP Integration Patterns

Three patterns for getting data from source systems into the landing zone, ordered by deployment complexity:

### Pattern A: Scheduled File Export (Recommended for v1)

Every enterprise ERP supports scheduled reports or data extracts to CSV. Configure existing report variants or create lightweight custom reports.

| System | Extract Method |
|--------|---------------|
| **SAP ECC/S4** | Custom ABAP reports, ALV exports, or BW extractors to application server |
| **Blue Yonder / JDA** | Scheduled report exports from DM/Fulfillment; BY Luminate REST APIs |
| **Oracle Retail** | BI Publisher reports or PL/SQL extracts to flat file |
| **Manhattan WMS** | Reporting module exports or scheduled database queries |
| **Microsoft Dynamics** | Data management framework exports or Power Automate flows |

### Pattern B: API-to-File Adapter (Future)

For systems with REST/SOAP APIs, build lightweight adapters that query the API and write standardized CSVs to the landing zone on a schedule.

### Pattern C: Database Direct Query (Advanced)

For environments with data warehouse access, SQL queries run directly against the DW and produce the standardized files. Sample SQL templates are provided in `/adapters/sql_templates/`.

---

## 13. Build Plan — MVP-First Parallel Sprints

### Sprint Overview

| Sprint | Focus | Effort | Cumulative Capability |
|--------|-------|--------|-----------------------|
| **MVP** | Thin vertical slice — prove end-to-end | ~3-4h | 1 vendor, 5 metrics, 5 sections, markdown |
| **Sprint 1** | Full scorecard + benchmarking | ~3-4h | 3 vendors, 14 metrics, BIC with $ impact, dual persona |
| **Sprint 2** | Cross-domain synthesis | ~2-3h | PO×Promo linkage, OOS attribution, promo readiness |
| **Sprint 3** | Polished output + pipeline | ~2-3h | DOCX output, orchestrated pipeline, CLI, error handling |
| **Sprint 4** | Calendar integration + demo | ~2-3h | Auto-trigger, leadership demo package, pilot plan |

**Total estimated effort:** ~14-17 hours across 5 sprints.

### MVP — Thin Vertical Slice (~3-4h)

**Goal:** Vendor ID in → readable briefing out. Prove the pipeline end-to-end.

**Data layer:**
- [ ] Generate mock CSVs for 1 vendor (Kellogg's): vendor_master.csv, purchase_orders.csv, vendor_performance.csv (5 metrics), oos_events.csv, promo_calendar.csv
- [ ] Generate manifest.yaml with `environment: mock`
- [ ] Build `src/data_loader.py`: reads manifest, loads CSVs, filters to requested vendor, returns structured dict

**Prompt layer** (parallel with data):
- [ ] Single mega-prompt: inject loaded data, generate 5 sections (exec summary, scorecard, risk flags, OOS highlights, talking points)
- [ ] Basic tone instructions: executive, data-backed, balanced

**Output layer:**
- [ ] Raw markdown output — no DOCX, no formatting engine

**Exit criteria:** A readable briefing where the exec summary correctly identifies the top issue, metrics match underlying data, and at least 1 talking point cites a specific PO or SKU.

### Sprint 1 — Full Scorecard + Benchmarking (~3-4h)

**Data layer:**
- [ ] Add 2 vendors (General Mills: declining; Conagra: erratic) with distinct behavioral patterns
- [ ] Expand to all 14 metric codes × 13-week lookback
- [ ] Add benchmark reference values

**Compute layer** (parallel with data):
- [ ] Scorecard engine: current value, 4-week trend, 13-week trend, trend classification
- [ ] Benchmark engine: peer avg, BIC, gap-to-BIC, dollar-impact translation
- [ ] Schema validation with auto-correction (percentage range fix)

**Prompt layer:**
- [ ] Feed computed scorecard (not raw data) to Claude
- [ ] Add buyer focus and planner focus sections (dual persona)
- [ ] Iterate on narrative quality (2-3 revisions)

### Sprint 2 — Cross-Domain Synthesis (~2-3h)

**Compute layer:**
- [ ] PO risk tiering: 🔴 critical / 🟡 watch / 🟢 on-track with rules-based classification
- [ ] OOS attribution: vendor-controllable vs. demand-driven vs. other
- [ ] Promo readiness scoring: green/yellow/red with specific PO dependencies
- [ ] Repeat offender SKU detection

**Data layer** (parallel with compute):
- [ ] Enrich POs with promo_flag, promo_event_id, need_date
- [ ] Add inventory_position.csv and demand_forecast.csv
- [ ] Add past promo compliance data

**Prompt layer** (parallel with compute):
- [ ] Add cross-domain narrative examples (PO×Promo, OOS attribution)
- [ ] Add OOS impact analysis and promo readiness sections
- [ ] Upgrade talking points with data citations and vendor win acknowledgment

### Sprint 3 — Polished Output + Pipeline (~2-3h)

**Output layer:**
- [ ] DOCX template with tables, conditional formatting, visual indicators
- [ ] Markdown-to-DOCX renderer with professional styling
- [ ] Data lineage in footer (source files + freshness from manifest)

**Pipeline layer** (parallel with output):
- [ ] Orchestrator: vendor ID → data load → validate → compute → prompt → render
- [ ] CLI: `python cli.py --vendor "Kelloggs" --date "2026-04-03" --data-dir /data/inbound/mock/`
- [ ] Config file (agent_config.yaml) for thresholds and defaults
- [ ] Full validation report generation
- [ ] Graceful degradation for missing optional files
- [ ] Error handling: missing data, API failures, token budget management

### Sprint 4 — Calendar Integration + Demo (~2-3h)

**Pipeline layer:**
- [ ] Calendar event detection for vendor-tagged meetings
- [ ] T-24h auto-generation with email/Teams delivery
- [ ] T-2h refresh if data has materially changed

**Demo package** (parallel with calendar):
- [ ] Leadership demo deck with live generation walkthrough
- [ ] Before/after workflow comparison (30-90 min → <30 sec)
- [ ] ROI analysis: time saved × meetings/month × buyer cost
- [ ] Pilot plan: 5 vendors × 2 categories × 8 weeks
- [ ] ERP export setup guide per system in `/adapters/`

---

## 14. Key Design Decisions

### Decided

| Decision | Choice | Rationale |
|---|---|---|
| **Repo name** | `supplier-collab-ai-agent` | Broad framing allows agent to evolve beyond briefings |
| **Integration model** | File-based CSV with manifest | System-agnostic, zero API dev, auditable, same format mock→prod |
| **Performance data format** | Long/tall table (1 row per vendor×metric×week) | Adding a metric = adding rows, not altering schema |
| **Output format** | Unified doc, dual persona sections | Both attendees work from same artifact |
| **Trigger model** | Manual + calendar (phased) | Manual proves value fast; calendar adds scale |
| **Lookback window** | 13 weeks default, configurable | Aligns with quarterly business rhythm |
| **Benchmarking** | Peer avg + BIC + self-trend + gap-to-BIC with $ impact | Four reference points give fullest picture |
| **Tone** | Balanced (issues + wins) | Vendor relationships are long-term; fairness builds credibility |
| **Linkage computation** | Pre-computed, not Claude in-context | Deterministic + lower token cost; Claude narrates, doesn't compute |
| **Build approach** | MVP-first vertical slices | Every sprint delivers a working, demoable briefing |

### Open Questions

| # | Question | Impact | Decision Needed By |
|---|---|---|---|
| 1 | **Data freshness SLA** — How stale can scorecard data be? | Caching strategy and compute cost | Sprint 1 |
| 2 | **Vendor-facing version?** — Sanitized briefing the vendor can also see? | Changes tone/content strategy significantly | Sprint 3 |
| 3 | **Action item tracking** — Post-meeting outcome capture and follow-through? | Extends agent into meeting lifecycle management | Sprint 4+ |
| 4 | **Multi-vendor briefing** — Category-level briefings spanning multiple vendors? | Different document structure, more complex synthesis | Post-pilot |
| 5 | **Agent mesh integration** — OOS/exception data flow from Replenishment Triage Agent? | Creates cross-agent dependency; powerful but complex | Post-pilot |
| 6 | **Prompt architecture** — Single mega-prompt vs. section-by-section generation? | Quality vs. simplicity tradeoff | MVP (test and decide) |

---

## 15. Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Prep time reduction** | 30-90 min → <5 min (manual), 0 min (calendar) | Time study pre/post |
| **Briefing completeness** | >90% of sections populated on first generation | Automated quality check |
| **Data validation pass rate** | >95% of files pass validation without errors | Validation report |
| **User satisfaction** | >4.2/5 from buyers and planners | Post-meeting survey |
| **Meeting outcome quality** | Increase in documented action items per meeting | Meeting notes analysis |
| **Vendor metric awareness** | >80% of attendees can cite top vendor issue without looking at doc | Spot check |
| **Adoption rate** | >70% of scheduled vendor meetings use agent briefings by Week 20 | Usage telemetry |
| **Generation time** | <30 seconds end-to-end | Pipeline performance logging |

---

## 16. Relationship to Replenishment Exception Triage Agent

These two agents form the first nodes of an **agent mesh** for supply chain intelligence:

| Dimension | Replenishment Triage Agent | Supplier Briefing Agent |
|---|---|---|
| **Repo** | `m-kunta/replenishment-triage-ai` | `m-kunta/supplier-collab-ai-agent` |
| **Persona** | Supply Planner | Buyer + Planner |
| **Trigger** | Exception event (reactive) | Meeting cadence (proactive) |
| **Time horizon** | Real-time / same-day | Trailing 13 weeks + forward-looking |
| **Unit of analysis** | SKU-DC exception | Vendor relationship |
| **Data integration** | Real-time event stream | File-based CSV landing zone |
| **Shared data** | OOS events, fill rate, phantom inventory | OOS events, fill rate, vendor scorecard |
| **Integration point** | Triage agent's OOS root-cause feeds briefing agent's vendor attribution | Briefing agent's vendor insights inform triage agent's priority scoring |

**Future state:** The triage agent detects a pattern of vendor-attributable exceptions → automatically escalates to the briefing agent → buyer gets an ad-hoc briefing with the issue pre-loaded → vendor meeting is scheduled with data-backed agenda. This is the agent mesh vision.

---

## 17. File Structure (Target State)

```
supplier-collab-ai-agent/
├── README.md
├── cli.py                                  # CLI entry point
├── config/
│   └── agent_config.yaml                   # Thresholds, defaults, dollar-impact params
├── data/
│   ├── inbound/
│   │   ├── mock/                           # Mock data for development
│   │   │   ├── manifest.yaml
│   │   │   ├── vendor_master.csv
│   │   │   ├── purchase_orders.csv
│   │   │   ├── vendor_performance.csv
│   │   │   ├── inventory_position.csv
│   │   │   ├── oos_events.csv
│   │   │   ├── promo_calendar.csv
│   │   │   ├── asn_receipts.csv
│   │   │   ├── demand_forecast.csv
│   │   │   ├── chargebacks.csv
│   │   │   └── trade_funds.csv
│   │   └── prod/                           # Production data landing zone
│   │       └── manifest.yaml
│   └── schemas/                            # YAML schema definitions per file
│       ├── vendor_master.schema.yaml
│       ├── purchase_orders.schema.yaml
│       ├── vendor_performance.schema.yaml
│       └── ...
├── adapters/                               # ERP-specific export guides
│   ├── sap_extract_guide.md
│   ├── blueyonder_extract_guide.md
│   ├── oracle_extract_guide.md
│   └── sql_templates/
│       ├── vendor_performance_dw.sql
│       ├── purchase_orders_dw.sql
│       └── oos_events_dw.sql
├── prompts/
│   ├── briefing_v0.md                      # MVP prompt
│   ├── briefing_v1.md                      # Sprint 1: scorecard + persona
│   └── briefing_v2.md                      # Sprint 2: cross-domain synthesis
├── src/
│   ├── data_loader.py                      # Manifest reader + CSV loader
│   ├── data_validator.py                   # Schema + quality validation
│   ├── agent.py                            # Orchestrator
│   ├── scorecard_engine.py                 # Metric computation
│   ├── benchmark_engine.py                 # Peer avg, BIC, gap analysis
│   ├── po_risk_engine.py                   # PO risk tiering
│   ├── oos_attribution.py                  # OOS root cause attribution
│   ├── promo_readiness.py                  # Promo supply readiness
│   ├── doc_renderer.js                     # DOCX generation
│   └── calendar_trigger.py                 # Calendar integration
├── templates/
│   └── briefing_template.js                # DOCX template definition
├── output/                                 # Generated briefings
├── demo/
│   ├── supplier_collab_demo.pptx           # Leadership demo deck
│   ├── roi_analysis.md                     # ROI calculation
│   └── pilot_plan.md                       # Pilot proposal
└── docs/
    ├── scope_v1.0.md                       # This document
    ├── sprint_plan.md                      # Detailed sprint plan
    ├── data_integration_spec.md            # Full integration specification
    ├── data_dictionary.md                  # Field definitions and enums
    └── error_handling.md                   # Failure modes and behaviors
```

---

## 18. Security & Data Handling

| Concern | Requirement |
|---------|-------------|
| **File access** | Landing zone restricted to agent service account (read-only) |
| **Data at rest** | Files may contain vendor pricing and trade fund details — encrypt landing zone volume |
| **Data in transit** | SFTP/S3 transfers use TLS/encryption |
| **PII** | Vendor contact names/emails in vendor_master — handle per company PII policy |
| **Retention** | Retain source files 90 days for audit trail; archive to cold storage after |
| **Briefing output** | Footer: "Generated by Supplier Collab AI · Confidential — Internal Use Only" |
| **Logging** | Agent logs file names, row counts, validation issues — never logs raw data values |

---

*v1.0 — Scope complete with file-based data integration layer, CSV schemas, ERP mapping, manifest-driven validation, graceful degradation, and MVP-first sprint plan. Ready for MVP build.*
