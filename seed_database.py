"""
Seed script to populate the database with sample data
Run this after starting the FastAPI server
"""

import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8000"

def create_locations():
    """Create sample locations"""
    print("Creating locations...")
    locations = [
        {"name": "Building A - Production Floor", "description": "Main production area"},
        {"name": "Building A - Office", "description": "Administrative offices"},
        {"name": "Building B - Warehouse", "description": "Storage and inventory"},
        {"name": "Building C - Maintenance Shop", "description": "Maintenance and repairs"},
    ]
    
    created_locations = []
    for loc in locations:
        response = requests.post(f"{BASE_URL}/locations", json=loc)
        if response.status_code == 200:
            created_locations.append(response.json())
            print(f"✓ Created location: {loc['name']}")
        else:
            print(f"✗ Failed to create location: {loc['name']}")
    
    return created_locations


def create_assets(locations):
    """Create sample assets"""
    print("\nCreating assets...")
    assets = [
        {
            "asset_id": "PUMP-001",
            "name": "Hydraulic Pump A",
            "category": "Pumps",
            "status": "Active",
            "location_id": locations[0]["id"],
            "owner_cost_center": "PROD-001",
            "vendor": "Acme Industrial",
            "serial_number": "SN-PUMP-001",
            "tag_id": "TAG-P001",
            "purchase_date": "2023-01-15",
            "warranty_expiry": "2025-01-15",
            "purchase_cost": 15000.00
        },
        {
            "asset_id": "CONV-001",
            "name": "Conveyor Belt System",
            "category": "Conveyors",
            "status": "Active",
            "location_id": locations[0]["id"],
            "owner_cost_center": "PROD-002",
            "vendor": "BeltCo",
            "serial_number": "SN-CONV-001",
            "tag_id": "TAG-C001",
            "purchase_date": "2022-06-10",
            "warranty_expiry": "2024-06-10",
            "purchase_cost": 45000.00
        },
        {
            "asset_id": "HVAC-001",
            "name": "HVAC Unit - Building A",
            "category": "HVAC",
            "status": "Active",
            "location_id": locations[1]["id"],
            "owner_cost_center": "FAC-001",
            "vendor": "CoolAir Systems",
            "serial_number": "SN-HVAC-001",
            "tag_id": "TAG-H001",
            "purchase_date": "2021-03-05",
            "warranty_expiry": "2026-03-05",
            "purchase_cost": 25000.00
        },
        {
            "asset_id": "MACH-001",
            "name": "CNC Machine",
            "category": "Production Equipment",
            "status": "Active",
            "location_id": locations[0]["id"],
            "owner_cost_center": "PROD-003",
            "vendor": "MachinePro",
            "serial_number": "SN-MACH-001",
            "tag_id": "TAG-M001",
            "purchase_date": "2023-08-15",
            "warranty_expiry": "2026-08-15",
            "purchase_cost": 120000.00
        },
        {
            "asset_id": "FORK-001",
            "name": "Forklift 1",
            "category": "Material Handling",
            "status": "Active",
            "location_id": locations[2]["id"],
            "owner_cost_center": "WARE-001",
            "vendor": "LiftCo",
            "serial_number": "SN-FORK-001",
            "tag_id": "TAG-F001",
            "purchase_date": "2023-05-25",
            "warranty_expiry": "2025-05-25",
            "purchase_cost": 35000.00
        },
    ]
    
    created_assets = []
    for asset in assets:
        response = requests.post(f"{BASE_URL}/assets", json=asset)
        if response.status_code == 200:
            created_assets.append(response.json())
            print(f"✓ Created asset: {asset['name']}")
        else:
            print(f"✗ Failed to create asset: {asset['name']} - {response.text}")
    
    return created_assets


def create_inventory():
    """Create sample inventory items"""
    print("\nCreating inventory items...")
    items = [
        {
            "item_name": "Hydraulic Oil Filter",
            "part_number": "HF-001",
            "description": "Standard hydraulic filter",
            "stock_on_hand": 50,
            "min_stock": 10,
            "max_stock": 100,
            "unit_cost": 25.50
        },
        {
            "item_name": "Conveyor Belt",
            "part_number": "CB-001",
            "description": "Replacement conveyor belt - 10m",
            "stock_on_hand": 5,
            "min_stock": 2,
            "max_stock": 10,
            "unit_cost": 450.00
        },
        {
            "item_name": "HVAC Air Filter",
            "part_number": "AF-001",
            "description": "HVAC system air filter",
            "stock_on_hand": 30,
            "min_stock": 15,
            "max_stock": 50,
            "unit_cost": 35.00
        },
        {
            "item_name": "Bearing Set",
            "part_number": "BR-001",
            "description": "Universal bearing set",
            "stock_on_hand": 8,
            "min_stock": 5,
            "max_stock": 20,
            "unit_cost": 85.00
        },
        {
            "item_name": "Hydraulic Hose",
            "part_number": "HH-001",
            "description": "High-pressure hydraulic hose - 2m",
            "stock_on_hand": 3,
            "min_stock": 10,
            "max_stock": 30,
            "unit_cost": 65.00
        },
    ]
    
    created_items = []
    for item in items:
        response = requests.post(f"{BASE_URL}/inventory", json=item)
        if response.status_code == 200:
            created_items.append(response.json())
            print(f"✓ Created inventory item: {item['item_name']}")
        else:
            print(f"✗ Failed to create item: {item['item_name']}")
    
    return created_items


def create_pm_templates(assets):
    """Create sample PM templates"""
    print("\nCreating PM templates...")
    templates = [
        {
            "name": "Hydraulic Pump - Quarterly Inspection",
            "description": "Regular quarterly maintenance for hydraulic pump",
            "frequency_value": 90,
            "frequency_unit": "Days",
            "asset_id": assets[0]["id"],
            "wo_summary_template": "Quarterly Inspection - Hydraulic Pump A",
            "wo_description_template": "Perform regular quarterly inspection:\n- Check oil levels\n- Inspect for leaks\n- Test pressure\n- Replace filters if needed",
            "default_priority": "Medium",
            "is_active": True
        },
        {
            "name": "Conveyor Belt - Monthly Check",
            "description": "Monthly conveyor belt inspection",
            "frequency_value": 30,
            "frequency_unit": "Days",
            "asset_id": assets[1]["id"],
            "wo_summary_template": "Monthly Check - Conveyor Belt System",
            "wo_description_template": "Monthly maintenance:\n- Check belt tension\n- Inspect rollers\n- Lubricate bearings\n- Check alignment",
            "default_priority": "Medium",
            "is_active": True
        },
        {
            "name": "HVAC - Filter Replacement",
            "description": "HVAC filter replacement every 3 months",
            "frequency_value": 3,
            "frequency_unit": "Months",
            "asset_id": assets[2]["id"],
            "wo_summary_template": "Filter Replacement - HVAC Unit Building A",
            "wo_description_template": "Replace HVAC filters:\n- Remove old filters\n- Install new filters\n- Check airflow\n- Test system operation",
            "default_priority": "Low",
            "is_active": True
        },
    ]
    
    created_templates = []
    for template in templates:
        response = requests.post(f"{BASE_URL}/pm-templates", json=template)
        if response.status_code == 200:
            created_templates.append(response.json())
            print(f"✓ Created PM template: {template['name']}")
        else:
            print(f"✗ Failed to create PM template: {template['name']}")
    
    return created_templates


def create_work_orders(assets):
    """Create sample work orders"""
    print("\nCreating work orders...")
    
    # Work Order 1
    wo1 = {
        "wo_number": "WO-2024-001",
        "summary": "Replace hydraulic pump seal",
        "description": "Customer reported leak in hydraulic pump. Need to replace seal.",
        "priority": "High",
        "status": "Open",
        "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
    }
    response = requests.post(f"{BASE_URL}/work-orders?asset_ids={assets[0]['id']}", json=wo1)
    if response.status_code == 200:
        print(f"✓ Created work order: {wo1['wo_number']}")
    
    # Work Order 2
    wo2 = {
        "wo_number": "WO-2024-002",
        "summary": "Conveyor belt alignment adjustment",
        "description": "Belt is running off-center. Need to adjust alignment.",
        "priority": "Medium",
        "status": "In Progress",
        "technician": "John Smith",
        "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }
    response = requests.post(f"{BASE_URL}/work-orders?asset_ids={assets[1]['id']}", json=wo2)
    if response.status_code == 200:
        wo2_data = response.json()
        print(f"✓ Created work order: {wo2['wo_number']}")
    
    # Work Order 3 - Completed
    wo3 = {
        "wo_number": "WO-2024-003",
        "summary": "HVAC filter replacement",
        "description": "Scheduled filter replacement",
        "priority": "Low",
        "status": "Completed",
        "technician": "Jane Doe",
        "time_spent_hours": 1.5,
        "completion_notes": "Filters replaced successfully. System tested and operating normally.",
        "due_date": (datetime.utcnow() - timedelta(days=1)).isoformat()
    }
    response = requests.post(f"{BASE_URL}/work-orders?asset_ids={assets[2]['id']}", json=wo3)
    if response.status_code == 200:
        print(f"✓ Created work order: {wo3['wo_number']}")


def main():
    print("=" * 60)
    print("Asset Manager - Database Seeding Script")
    print("=" * 60)
    print("\nMake sure the FastAPI server is running at http://localhost:8000")
    print("\nStarting seed process...\n")
    
    try:
        # Test connection
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Cannot connect to API server!")
            return
        
        # Seed data
        locations = create_locations()
        assets = create_assets(locations)
        inventory = create_inventory()
        pm_templates = create_pm_templates(assets)
        create_work_orders(assets)
        
        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print(f"\nCreated:")
        print(f"  - {len(locations)} locations")
        print(f"  - {len(assets)} assets")
        print(f"  - {len(inventory)} inventory items")
        print(f"  - {len(pm_templates)} PM templates")
        print(f"  - 3 work orders")
        
        print(f"\n📊 View dashboard stats: {BASE_URL}/stats/dashboard")
        print(f"📖 API Documentation: {BASE_URL}/docs")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("Please make sure the server is running with: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")


if __name__ == "__main__":
    main()
