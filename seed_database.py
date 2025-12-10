"""
Seed script to populate the database with sample data
Run this after starting the FastAPI server
"""

import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8000"

def create_vendors():
    """Create sample vendors"""
    print("Creating vendors...")
    vendors = [
        {
            "name": "Acme Industrial Solutions",
            "contact_person": "John Anderson",
            "email": "john.anderson@acmeindustrial.com",
            "phone": "+1-555-0101",
            "address": "123 Industrial Ave, Manufacturing City, MC 12345",
            "vendor_type": "Equipment Supplier",
            "is_active": True
        },
        {
            "name": "BeltCo Manufacturing",
            "contact_person": "Sarah Miller",
            "email": "sarah.miller@beltco.com",
            "phone": "+1-555-0102",
            "address": "456 Conveyor Road, Belt Town, BT 67890",
            "vendor_type": "Parts Supplier",
            "is_active": True
        },
        {
            "name": "CoolAir Systems Ltd",
            "contact_person": "Michael Johnson",
            "email": "michael.johnson@coolairsystems.com",
            "phone": "+1-555-0103",
            "address": "789 Climate Control Blvd, Cool City, CC 13579",
            "vendor_type": "HVAC Specialist",
            "is_active": True
        },
        {
            "name": "MachinePro Technologies",
            "contact_person": "Lisa Chen",
            "email": "lisa.chen@machinepro.com",
            "phone": "+1-555-0104",
            "address": "321 Precision Dr, Tech Valley, TV 24680",
            "vendor_type": "Equipment Manufacturer",
            "is_active": True
        },
        {
            "name": "LiftCo Equipment Rental",
            "contact_person": "Robert Wilson",
            "email": "robert.wilson@liftco.com",
            "phone": "+1-555-0105",
            "address": "654 Heavy Equipment St, Lift City, LC 97531",
            "vendor_type": "Equipment Rental",
            "is_active": True
        },
        {
            "name": "HydroParts Supply Co",
            "contact_person": "Emily Davis",
            "email": "emily.davis@hydroparts.com",
            "phone": "+1-555-0106",
            "address": "987 Hydraulic Lane, Fluid City, FC 86420",
            "vendor_type": "Parts Supplier",
            "is_active": True
        }
    ]
    
    created_vendors = []
    for vendor in vendors:
        response = requests.post(f"{BASE_URL}/vendors", json=vendor)
        if response.status_code == 200:
            created_vendors.append(response.json())
            print(f"✓ Created vendor: {vendor['name']}")
        else:
            # If vendor already exists, try to fetch it
            if "already exists" in response.text:
                print(f"⚠ Vendor already exists: {vendor['name']} - fetching existing...")
                get_response = requests.get(f"{BASE_URL}/vendors")
                if get_response.status_code == 200:
                    existing_vendors = get_response.json()
                    existing = next((v for v in existing_vendors if v['name'] == vendor['name']), None)
                    if existing:
                        created_vendors.append(existing)
                        print(f"  ✓ Using existing vendor: {vendor['name']}")
            else:
                print(f"✗ Failed to create vendor: {vendor['name']} - {response.text}")
    
    return created_vendors


def create_locations():
    """Create sample locations"""
    print("Creating locations...")
    locations = [
        {"name": "Building A - Production Floor", "description": "Main production area with heavy machinery"},
        {"name": "Building A - Office", "description": "Administrative offices and meeting rooms"},
        {"name": "Building B - Warehouse", "description": "Storage and inventory management area"},
        {"name": "Building C - Maintenance Shop", "description": "Maintenance and repair workshop"},
        {"name": "Building D - Quality Control", "description": "Quality testing and inspection lab"},
        {"name": "Outdoor Yard", "description": "External equipment and vehicle parking"},
        {"name": "Utility Room", "description": "Electrical panels and utility connections"},
        {"name": "Loading Dock", "description": "Material receiving and shipping area"}
    ]
    
    created_locations = []
    for loc in locations:
        response = requests.post(f"{BASE_URL}/locations", json=loc)
        if response.status_code == 200:
            created_locations.append(response.json())
            print(f"✓ Created location: {loc['name']}")
        else:
            # If location already exists, try to fetch it
            if "already exists" in response.text:
                print(f"⚠ Location already exists: {loc['name']} - fetching existing...")
                get_response = requests.get(f"{BASE_URL}/locations")
                if get_response.status_code == 200:
                    existing_locations = get_response.json()
                    existing = next((l for l in existing_locations if l['name'] == loc['name']), None)
                    if existing:
                        created_locations.append(existing)
                        print(f"  ✓ Using existing location: {loc['name']}")
            else:
                print(f"✗ Failed to create location: {loc['name']} - {response.text}")
    
    return created_locations


def create_assets(locations, vendors):
    """Create sample assets"""
    print("\nCreating assets...")
    assets = [
        {
            "asset_id": "PUMP-001",
            "name": "Hydraulic Pump A",
            "category": "Pumps",
            "status": "Active",
            "location_id": locations[0]["id"],
            "station_id": locations[1]["id"],
            "owner_cost_center": "PROD-001",
            "vendor_id": vendors[0]["id"],  # Acme Industrial Solutions
            "vendor_name": vendors[0]["name"],
            "serial_number": "SN-PUMP-001",
            "tag_id": "TAG-P001",
            "sap_id": "10001001",
            "purchase_date": "2023-01-15",
            "warranty_expiry": "2025-01-15",
            "warranty_date": "2025-01-15",
            "purchase_cost": 15000.00,
            "invoice_number": "INV-2023-0001",
            "invoice_date": "2023-01-10",
            "capitalised_on": "2023-01-20",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        },
        {
            "asset_id": "CONV-001",
            "name": "Conveyor Belt System",
            "category": "Conveyors",
            "status": "Active",
            "location_id": locations[0]["id"],
            "station_id": locations[2]["id"],
            "owner_cost_center": "PROD-002",
            "vendor_id": vendors[1]["id"],  # BeltCo Manufacturing
            "vendor_name": vendors[1]["name"],
            "serial_number": "SN-CONV-001",
            "tag_id": "TAG-C001",
            "sap_id": "10001002",
            "purchase_date": "2022-06-10",
            "warranty_expiry": "2024-06-10",
            "warranty_date": "2024-06-10",
            "purchase_cost": 45000.00,
            "invoice_number": "INV-2022-0045",
            "invoice_date": "2022-06-05",
            "capitalised_on": "2022-06-15",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        },
        {
            "asset_id": "HVAC-001",
            "name": "HVAC Unit - Building A",
            "category": "HVAC",
            "status": "Active",
            "location_id": locations[1]["id"],
            "owner_cost_center": "FAC-001",
            "vendor_id": vendors[2]["id"],  # CoolAir Systems
            "vendor_name": vendors[2]["name"],
            "serial_number": "SN-HVAC-001",
            "tag_id": "TAG-H001",
            "sap_id": "10001003",
            "purchase_date": "2021-03-05",
            "warranty_expiry": "2026-03-05",
            "warranty_date": "2026-03-05",
            "purchase_cost": 25000.00,
            "invoice_number": "INV-2021-0012",
            "invoice_date": "2021-03-01",
            "capitalised_on": "2021-03-10",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        },
        {
            "asset_id": "MACH-001",
            "name": "CNC Machine",
            "category": "Production Equipment",
            "status": "Active",
            "location_id": locations[0]["id"],
            "owner_cost_center": "PROD-003",
            "vendor_id": vendors[3]["id"],  # MachinePro Technologies
            "vendor_name": vendors[3]["name"],
            "serial_number": "SN-MACH-001",
            "tag_id": "TAG-M001",
            "sap_id": "10001004",
            "purchase_date": "2023-08-15",
            "warranty_expiry": "2026-08-15",
            "warranty_date": "2026-08-15",
            "purchase_cost": 120000.00,
            "invoice_number": "INV-2023-0087",
            "invoice_date": "2023-08-10",
            "capitalised_on": "2023-08-20",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        },
        {
            "asset_id": "FORK-001",
            "name": "Forklift 1",
            "category": "Material Handling",
            "status": "Active",
            "location_id": locations[2]["id"],
            "owner_cost_center": "WARE-001",
            "vendor_id": vendors[4]["id"],  # LiftCo Equipment Rental
            "vendor_name": vendors[4]["name"],
            "serial_number": "SN-FORK-001",
            "tag_id": "TAG-F001",
            "sap_id": "10001005",
            "purchase_date": "2023-05-25",
            "warranty_expiry": "2025-05-25",
            "warranty_date": "2025-05-25",
            "purchase_cost": 35000.00,
            "invoice_number": "INV-2023-0056",
            "invoice_date": "2023-05-20",
            "capitalised_on": "2023-05-30",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        },
        {
            "asset_id": "PUMP-002",
            "name": "Hydraulic Pump B",
            "category": "Pumps",
            "status": "In Maintenance",
            "location_id": locations[3]["id"],  # Maintenance Shop
            "owner_cost_center": "PROD-001",
            "vendor_id": vendors[5]["id"],  # HydroParts Supply Co
            "vendor_name": vendors[5]["name"],
            "serial_number": "SN-PUMP-002",
            "tag_id": "TAG-P002",
            "sap_id": "10001006",
            "purchase_date": "2022-11-12",
            "warranty_expiry": "2024-11-12",
            "warranty_date": "2024-11-12",
            "purchase_cost": 18000.00,
            "invoice_number": "INV-2022-0098",
            "invoice_date": "2022-11-08",
            "capitalised_on": "2022-11-15",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Bad"
        },
        {
            "asset_id": "COMP-001",
            "name": "Air Compressor",
            "category": "Compressed Air",
            "status": "Active",
            "location_id": locations[0]["id"],
            "owner_cost_center": "UTIL-001",
            "vendor_id": vendors[0]["id"],  # Acme Industrial Solutions
            "vendor_name": vendors[0]["name"],
            "serial_number": "SN-COMP-001",
            "tag_id": "TAG-COMP001",
            "sap_id": "10001007",
            "purchase_date": "2023-03-22",
            "warranty_expiry": "2025-03-22",
            "warranty_date": "2025-03-22",
            "purchase_cost": 8500.00,
            "invoice_number": "INV-2023-0034",
            "invoice_date": "2023-03-18",
            "capitalised_on": "2023-03-25",
            "company_code": "IN07",
            "plant_code": "IN08",
            "currency": "INR",
            "location_name": "Plant - Bangalore",
            "state": "Good"
        }
    ]
    
    created_assets = []
    for asset in assets:
        response = requests.post(f"{BASE_URL}/assets", json=asset)
        if response.status_code == 200:
            created_assets.append(response.json())
            print(f"✓ Created asset: {asset['name']}")
        else:
            # If asset already exists, try to fetch it
            if "already exists" in response.text:
                print(f"⚠ Asset already exists: {asset['name']} - fetching existing...")
                # Try to get the existing asset by asset_id
                get_response = requests.get(f"{BASE_URL}/assets")
                if get_response.status_code == 200:
                    existing_assets = get_response.json()
                    existing = next((a for a in existing_assets if a['asset_id'] == asset['asset_id']), None)
                    if existing:
                        created_assets.append(existing)
                        print(f"  ✓ Using existing asset: {asset['name']}")
                    else:
                        print(f"  ⚠ Could not find existing asset with ID: {asset['asset_id']}")
                else:
                    print(f"  ✗ Failed to fetch existing assets: {get_response.status_code}")
            else:
                print(f"✗ Failed to create asset: {asset['name']} - {response.text}")
    
    if len(created_assets) == 0:
        print("\n⚠ WARNING: No assets were created or found. Attempting to fetch all existing assets...")
        get_response = requests.get(f"{BASE_URL}/assets")
        if get_response.status_code == 200:
            created_assets = get_response.json()
            print(f"  ✓ Retrieved {len(created_assets)} existing assets")
    
    return created_assets


def create_inventory():
    """Create sample inventory items"""
    print("\nCreating inventory items...")
    items = [
        {
            "item_name": "Hydraulic Oil Filter",
            "part_number": "HF-001",
            "description": "Standard hydraulic filter for pumps",
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
        {
            "item_name": "Motor Oil",
            "part_number": "MO-001",
            "description": "Industrial motor oil - 5L",
            "stock_on_hand": 25,
            "min_stock": 15,
            "max_stock": 60,
            "unit_cost": 42.00
        },
        {
            "item_name": "Safety Valves",
            "part_number": "SV-001",
            "description": "Pressure safety valves",
            "stock_on_hand": 12,
            "min_stock": 8,
            "max_stock": 25,
            "unit_cost": 150.00
        },
        {
            "item_name": "Electrical Cables",
            "part_number": "EC-001",
            "description": "Industrial electrical cables - 100m",
            "stock_on_hand": 6,
            "min_stock": 3,
            "max_stock": 15,
            "unit_cost": 125.00
        },
        {
            "item_name": "Grease",
            "part_number": "GR-001",
            "description": "High-temperature bearing grease - 1kg",
            "stock_on_hand": 40,
            "min_stock": 20,
            "max_stock": 80,
            "unit_cost": 18.50
        },
        {
            "item_name": "Control Panel Components",
            "part_number": "CP-001",
            "description": "Electrical control panel spare parts kit",
            "stock_on_hand": 4,
            "min_stock": 2,
            "max_stock": 10,
            "unit_cost": 320.00
        }
    ]
    
    created_items = []
    for item in items:
        response = requests.post(f"{BASE_URL}/inventory", json=item)
        if response.status_code == 200:
            created_items.append(response.json())
            print(f"✓ Created inventory item: {item['item_name']}")
        else:
            # If item already exists, try to fetch it
            if "already exists" in response.text or "UNIQUE constraint" in response.text:
                print(f"⚠ Item already exists: {item['item_name']} - fetching existing...")
                # Try to get the existing item by part_number
                get_response = requests.get(f"{BASE_URL}/inventory")
                if get_response.status_code == 200:
                    existing_items = get_response.json()
                    existing = next((i for i in existing_items if i['part_number'] == item['part_number']), None)
                    if existing:
                        created_items.append(existing)
                        print(f"  ✓ Using existing item: {item['item_name']}")
            else:
                print(f"✗ Failed to create item: {item['item_name']} - {response.text}")
    
    return created_items


def create_pm_templates(assets):
    """Create sample PM templates"""
    print("\nCreating PM templates...")
    
    # Check if we have enough assets
    if len(assets) < 3:
        print(f"⚠ WARNING: Not enough assets ({len(assets)}) to create PM templates. Skipping...")
        return []
    
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
            # If template already exists, try to fetch it
            if "already exists" in response.text:
                print(f"⚠ Template already exists: {template['name']} - fetching existing...")
                get_response = requests.get(f"{BASE_URL}/pm-templates")
                if get_response.status_code == 200:
                    existing_templates = get_response.json()
                    existing = next((t for t in existing_templates if t['name'] == template['name']), None)
                    if existing:
                        created_templates.append(existing)
                        print(f"  ✓ Using existing template: {template['name']}")
            else:
                print(f"✗ Failed to create PM template: {template['name']} - {response.text}")
    
    return created_templates


def create_work_orders(assets):
    """Create sample work orders"""
    print("\nCreating work orders...")
    
    # Check if we have enough assets
    if len(assets) < 7:
        print(f"⚠ WARNING: Not enough assets ({len(assets)}) to create all work orders. Will create what we can...")
    
    work_orders = [
        # Work Order 1 - High Priority Open
        {
            "wo_number": "WO-2024-001",
            "summary": "Replace hydraulic pump seal",
            "description": "Customer reported leak in hydraulic pump. Need to replace seal and test system.",
            "priority": "High",
            "status": "Open",
            "due_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "asset_id": assets[0]['id']  # PUMP-001
        },
        # Work Order 2 - Medium Priority In Progress
        {
            "wo_number": "WO-2024-002",
            "summary": "Conveyor belt alignment adjustment",
            "description": "Belt is running off-center causing tracking issues. Need to adjust alignment and check tensioning.",
            "priority": "Medium",
            "status": "In Progress",
            "technician": "John Smith",
            "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "asset_id": assets[1]['id']  # CONV-001
        },
        # Work Order 3 - Completed
        {
            "wo_number": "WO-2024-003",
            "summary": "HVAC filter replacement",
            "description": "Scheduled quarterly filter replacement for Building A HVAC system.",
            "priority": "Low",
            "status": "Completed",
            "technician": "Jane Doe",
            "time_spent_hours": 1.5,
            "completion_notes": "Filters replaced successfully. System tested and operating normally. Airflow improved by 15%.",
            "due_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "asset_id": assets[2]['id']  # HVAC-001
        },
        # Work Order 4 - Emergency High Priority
        {
            "wo_number": "WO-2024-004",
            "summary": "CNC Machine Emergency Stop",
            "description": "Emergency stop button triggered during operation. Safety inspection required before restart.",
            "priority": "Critical",
            "status": "Open",
            "due_date": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "asset_id": assets[3]['id']  # MACH-001
        },
        # Work Order 5 - Preventive Maintenance
        {
            "wo_number": "WO-2024-005",
            "summary": "Forklift Monthly Inspection",
            "description": "Monthly safety inspection: check brakes, hydraulics, forks, and safety equipment.",
            "priority": "Medium",
            "status": "Open",
            "due_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            "asset_id": assets[4]['id']  # FORK-001
        },
        # Work Order 6 - Pump B Maintenance
        {
            "wo_number": "WO-2024-006",
            "summary": "Hydraulic Pump B Overhaul",
            "description": "Complete overhaul of pump in maintenance shop. Replace seals, bearings, and test all components.",
            "priority": "Medium",
            "status": "In Progress",
            "technician": "Mike Rodriguez",
            "time_spent_hours": 8.5,
            "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            "asset_id": assets[5]['id']  # PUMP-002
        },
        # Work Order 7 - Compressor Service
        {
            "wo_number": "WO-2024-007",
            "summary": "Air Compressor Service",
            "description": "Routine service: change oil, replace filters, check belts and pressure settings.",
            "priority": "Low",
            "status": "Open",
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "asset_id": assets[6]['id']  # COMP-001
        }
    ]
    
    created_orders = []
    for wo in work_orders:
        asset_id = wo.pop('asset_id')  # Remove asset_id from wo dict
        response = requests.post(f"{BASE_URL}/work-orders?asset_ids={asset_id}", json=wo)
        if response.status_code == 200:
            created_orders.append(response.json())
            print(f"✓ Created work order: {wo['wo_number']}")
        else:
            # If work order already exists, try to fetch it
            if "already exists" in response.text:
                print(f"⚠ Work order already exists: {wo['wo_number']} - fetching existing...")
                get_response = requests.get(f"{BASE_URL}/work-orders")
                if get_response.status_code == 200:
                    existing_orders = get_response.json()
                    existing = next((w for w in existing_orders if w['wo_number'] == wo['wo_number']), None)
                    if existing:
                        created_orders.append(existing)
                        print(f"  ✓ Using existing work order: {wo['wo_number']}")
            else:
                print(f"✗ Failed to create work order: {wo['wo_number']} - {response.text}")
    
    return created_orders


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
        
        # Seed data in correct order (vendors and locations first, then assets that reference them)
        vendors = create_vendors()
        locations = create_locations()
        assets = create_assets(locations, vendors)
        inventory = create_inventory()
        pm_templates = create_pm_templates(assets)
        work_orders = create_work_orders(assets)
        
        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print(f"\nCreated:")
        print(f"  - {len(vendors)} vendors")
        print(f"  - {len(locations)} locations")
        print(f"  - {len(assets)} assets")
        print(f"  - {len(inventory)} inventory items")
        print(f"  - {len(pm_templates)} PM templates")
        print(f"  - {len(work_orders)} work orders")
        
        print(f"\n📊 View dashboard stats: {BASE_URL}/stats/dashboard")
        print(f"📖 API Documentation: {BASE_URL}/docs")
        print(f"👥 Vendors: {BASE_URL}/vendors")
        print(f"🏭 Assets: {BASE_URL}/assets")
        print(f"📦 Inventory: {BASE_URL}/inventory")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("Please make sure the server is running with: uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error during seeding: {str(e)}")
        print("This might be due to existing data. Try deleting the database file first:")
        print("rm asset_manager.db && python seed_database.py")


if __name__ == "__main__":
    main()
