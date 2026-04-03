import os
import csv
import yaml
from datetime import date, timedelta

MOCK_DIR = os.path.join("data", "inbound", "mock")

def ensure_dir():
    os.makedirs(MOCK_DIR, exist_ok=True)

def write_csv(filename, fieldnames, rows):
    filepath = os.path.join(MOCK_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Generated {filepath} with {len(rows)} rows.")
    return len(rows)

def generate_vendor_master():
    fieldnames = ['vendor_id', 'vendor_name', 'vendor_status', 'primary_category', 'buyer_name', 'planner_name']
    rows = [
        {
            'vendor_id': 'V1001',
            'vendor_name': 'Kelloggs',
            'vendor_status': 'active',
            'primary_category': 'Cereal',
            'buyer_name': 'John Doe',
            'planner_name': 'Jane Smith'
        }
    ]
    return write_csv('vendor_master.csv', fieldnames, rows)

def generate_purchase_orders():
    # po_number, po_line, vendor_id, sku, qty_ordered, requested_delivery_date
    today = date(2026, 4, 3)
    fieldnames = ['po_number', 'po_line', 'vendor_id', 'sku', 'sku_description', 'qty_ordered', 'requested_delivery_date', 'po_status', 'ship_to_dc']
    rows = [
        {'po_number': 'PO-9991', 'po_line': 1, 'vendor_id': 'V1001', 'sku': 'SKU-001', 'sku_description': 'Frosted Flakes 18oz', 'qty_ordered': 500, 'requested_delivery_date': (today - timedelta(days=2)).isoformat(), 'po_status': 'shipped', 'ship_to_dc': 'DC-Atlanta'},
        {'po_number': 'PO-9992', 'po_line': 1, 'vendor_id': 'V1001', 'sku': 'SKU-002', 'sku_description': 'Rice Krispies 12oz', 'qty_ordered': 300, 'requested_delivery_date': (today + timedelta(days=4)).isoformat(), 'po_status': 'open', 'ship_to_dc': 'DC-Atlanta'},
        {'po_number': 'PO-9993', 'po_line': 1, 'vendor_id': 'V1001', 'sku': 'SKU-003', 'sku_description': 'Froot Loops 14.7oz', 'qty_ordered': 450, 'requested_delivery_date': (today + timedelta(days=7)).isoformat(), 'po_status': 'open', 'ship_to_dc': 'DC-Dallas'},
    ]
    return write_csv('purchase_orders.csv', fieldnames, rows)

def generate_vendor_performance():
    fieldnames = ['vendor_id', 'week_ending', 'metric_code', 'metric_value', 'metric_uom']
    rows = []
    
    # 5 metrics over last 13 weeks ending 2026-03-28 (a Saturday)
    end_date = date(2026, 3, 28)
    
    # Let's simulate a declining fill rate, starting at 96% down to 91%
    fill_rate_trend = [0.962, 0.958, 0.960, 0.955, 0.950, 0.948, 0.942, 0.940, 0.935, 0.930, 0.925, 0.920, 0.918]
    otif_trend =      [0.94, 0.93, 0.94, 0.92, 0.90, 0.89, 0.88, 0.88, 0.87, 0.86, 0.85, 0.84, 0.83]
    
    for i in range(13):
        week_end = end_date - timedelta(days=(12-i)*7)
        rows.append({'vendor_id': 'V1001', 'week_ending': week_end.isoformat(), 'metric_code': 'FILL_RATE', 'metric_value': fill_rate_trend[i], 'metric_uom': 'pct'})
        rows.append({'vendor_id': 'V1001', 'week_ending': week_end.isoformat(), 'metric_code': 'OTIF', 'metric_value': otif_trend[i], 'metric_uom': 'pct'})
        rows.append({'vendor_id': 'V1001', 'week_ending': week_end.isoformat(), 'metric_code': 'LEAD_TIME_COMPLIANCE', 'metric_value': 0.88, 'metric_uom': 'pct'})
        rows.append({'vendor_id': 'V1001', 'week_ending': week_end.isoformat(), 'metric_code': 'FORECAST_ACCURACY', 'metric_value': 0.85, 'metric_uom': 'pct'})
        rows.append({'vendor_id': 'V1001', 'week_ending': week_end.isoformat(), 'metric_code': 'PROMO_FILL_RATE', 'metric_value': 0.88, 'metric_uom': 'pct'})

    return write_csv('vendor_performance.csv', fieldnames, rows)

def generate_oos_events():
    fieldnames = ['vendor_id', 'sku', 'oos_start_date', 'oos_end_date', 'oos_units_lost', 'root_cause_code']
    today = date(2026, 4, 3)
    rows = [
        {'vendor_id': 'V1001', 'sku': 'SKU-001', 'oos_start_date': (today - timedelta(days=5)).isoformat(), 'oos_end_date': '', 'oos_units_lost': 120, 'root_cause_code': 'short_fill'},
        {'vendor_id': 'V1001', 'sku': 'SKU-003', 'oos_start_date': (today - timedelta(days=10)).isoformat(), 'oos_end_date': (today - timedelta(days=8)).isoformat(), 'oos_units_lost': 80, 'root_cause_code': 'late_shipment'}
    ]
    return write_csv('oos_events.csv', fieldnames, rows)

def generate_promo_calendar():
    fieldnames = ['promo_id', 'event_name', 'vendor_id', 'sku', 'start_date', 'end_date', 'promoted_volume', 'promo_type']
    today = date(2026, 4, 3)
    rows = [
        {'promo_id': 'PRM-001', 'event_name': 'Easter TPR', 'vendor_id': 'V1001', 'sku': 'SKU-001', 'start_date': (today + timedelta(days=1)).isoformat(), 'end_date': (today + timedelta(days=8)).isoformat(), 'promoted_volume': 1500, 'promo_type': 'tpr'}
    ]
    return write_csv('promo_calendar.csv', fieldnames, rows)

def generate_manifest(counts):
    manifest = {
        'version': '1.0',
        'generated_at': '2026-04-03T08:00:00',
        'source_system': 'Mock Generator',
        'environment': 'mock',
        'data_directory': './',
        'files': {
            'vendor_master': {'filename': 'vendor_master.csv', 'row_count': counts[0], 'required': True},
            'purchase_orders': {'filename': 'purchase_orders.csv', 'row_count': counts[1], 'required': True},
            'vendor_performance': {'filename': 'vendor_performance.csv', 'row_count': counts[2], 'required': True},
            'oos_events': {'filename': 'oos_events.csv', 'row_count': counts[3], 'required': False},
            'promo_calendar': {'filename': 'promo_calendar.csv', 'row_count': counts[4], 'required': False}
        }
    }
    
    filepath = os.path.join(MOCK_DIR, 'manifest.yaml')
    with open(filepath, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)
    print(f"Generated {filepath}")

def main():
    ensure_dir()
    c1 = generate_vendor_master()
    c2 = generate_purchase_orders()
    c3 = generate_vendor_performance()
    c4 = generate_oos_events()
    c5 = generate_promo_calendar()
    
    generate_manifest((c1,c2,c3,c4,c5))
    print("Mock data generation complete!")

if __name__ == '__main__':
    main()
