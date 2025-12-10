#!/usr/bin/env python3
"""
Comprehensive API test script - tests all endpoints and scenarios
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

BASE_URL = "http://127.0.0.1:8000"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "total": 0
}

# Store created IDs for cleanup and further testing
test_data = {
    "locations": [],
    "assets": [],
    "work_orders": [],
    "inventory_items": [],
    "pm_templates": []
}


def print_response(title, response, show_full=False):
    """Print formatted API response"""
    test_results["total"] += 1
    status_icon = "✅" if 200 <= response.status_code < 300 else "❌"
    
    if 200 <= response.status_code < 300:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    
    print(f"\n{status_icon} {title}")
    print(f"   Status: {response.status_code}")
    
    if show_full or response.status_code >= 400:
        try:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=6)}")
        except:
            print(f"   Response: {response.text}")


def safe_get_id(data_list, index=0, default=None):
    """Safely get ID from test data"""
    try:
        if data_list and len(data_list) > index:
            item = data_list[index]
            if isinstance(item, dict) and "id" in item:
                return item["id"]
        return default
    except (IndexError, KeyError, TypeError):
        return default



def test_section(section_name):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {section_name}")
    print(f"{'='*70}")


def main():
    print("\n" + "="*70)
    print("  🚀 Asset Manager API - Comprehensive Test Suite")
    print("="*70)
    print(f"  Testing against: {BASE_URL}")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # ========================================
    # 1. ROOT & HEALTH CHECKS
    # ========================================
    test_section("1. ROOT & HEALTH CHECKS")
    
    response = requests.get(f"{BASE_URL}/")
    print_response("1.1 Root Endpoint", response)
    
    # ========================================
    # 2. LOCATION TESTS
    # ========================================
    test_section("2. LOCATION MANAGEMENT")
    
    # Create parent location
    location1 = {
        "name": "Building A",
        "description": "Main production building"
    }
    response = requests.post(f"{BASE_URL}/locations", json=location1)
    print_response("2.1 Create Parent Location", response)
    if response.status_code == 200:
        test_data["locations"].append(response.json())
    
    # Create child location with parent
    location2 = {
        "name": "Building A - Floor 1",
        "description": "Production Floor 1",
        "parent_id": test_data["locations"][0]["id"] if test_data["locations"] else None
    }
    response = requests.post(f"{BASE_URL}/locations", json=location2)
    print_response("2.2 Create Child Location", response)
    if response.status_code == 200:
        test_data["locations"].append(response.json())
    
    # Create another location
    location3 = {
        "name": "Warehouse",
        "description": "Storage facility"
    }
    response = requests.post(f"{BASE_URL}/locations", json=location3)
    print_response("2.3 Create Warehouse Location", response)
    if response.status_code == 200:
        test_data["locations"].append(response.json())
    
    # Get all locations
    response = requests.get(f"{BASE_URL}/locations")
    print_response("2.4 Get All Locations", response)
    
    # ========================================
    # 3. ASSET TESTS
    # ========================================
    test_section("3. ASSET REGISTRY")
    
    # Create Asset 1 - Pump
    asset1 = {
        "asset_id": f"PUMP-{int(time.time())}",
        "name": "Hydraulic Pump A",
        "category": "Pumps",
        "status": "Active",
        "location_id": test_data["locations"][0]["id"] if test_data["locations"] else 1,
        "vendor": "Acme Industrial",
        "serial_number": f"SN-PUMP-{int(time.time())}",
        "tag_id": f"TAG-PUMP-{int(time.time())}",
        "owner_cost_center": "PROD-001",
        "purchase_cost": 15000.00,
        "meter_reading": 1000.0
    }
    response = requests.post(f"{BASE_URL}/assets", json=asset1)
    print_response("3.1 Create Asset - Pump", response)
    if response.status_code == 200:
        test_data["assets"].append(response.json())
    
    # Create Asset 2 - Conveyor
    asset2 = {
        "asset_id": f"CONV-{int(time.time())}",
        "name": "Conveyor Belt System",
        "category": "Conveyors",
        "status": "Active",
        "location_id": test_data["locations"][1]["id"] if len(test_data["locations"]) > 1 else 1,
        "vendor": "BeltCo",
        "serial_number": f"SN-CONV-{int(time.time())}",
        "owner_cost_center": "PROD-002",
        "purchase_cost": 45000.00
    }
    response = requests.post(f"{BASE_URL}/assets", json=asset2)
    print_response("3.2 Create Asset - Conveyor", response)
    if response.status_code == 200:
        test_data["assets"].append(response.json())
    
    # Create Asset 3 - HVAC
    asset3 = {
        "asset_id": f"HVAC-{int(time.time())}",
        "name": "HVAC Unit",
        "category": "HVAC",
        "status": "Active",
        "location_id": test_data["locations"][0]["id"] if test_data["locations"] else 1,
        "vendor": "CoolAir Systems",
        "serial_number": f"SN-HVAC-{int(time.time())}",
        "owner_cost_center": "FAC-001",
        "purchase_cost": 25000.00
    }
    response = requests.post(f"{BASE_URL}/assets", json=asset3)
    print_response("3.3 Create Asset - HVAC", response)
    if response.status_code == 200:
        test_data["assets"].append(response.json())
    
    # Get all assets
    response = requests.get(f"{BASE_URL}/assets")
    print_response("3.4 Get All Assets", response)
    
    # Get assets with filter - Active status
    response = requests.get(f"{BASE_URL}/assets?status=Active")
    print_response("3.5 Get Active Assets (Filter)", response)
    
    # Get assets with filter - Category
    response = requests.get(f"{BASE_URL}/assets?category=Pumps")
    print_response("3.6 Get Assets by Category (Filter)", response)
    
    # Get assets with search
    response = requests.get(f"{BASE_URL}/assets?search=Pump")
    print_response("3.7 Search Assets", response)
    
    # Get single asset
    if test_data["assets"]:
        asset_id = test_data["assets"][0]["id"]
        response = requests.get(f"{BASE_URL}/assets/{asset_id}")
        print_response("3.8 Get Single Asset", response)
    
    # Update asset
    if test_data["assets"]:
        asset_id = test_data["assets"][0]["id"]
        update_data = {
            **test_data["assets"][0],
            "status": "In Maintenance",
            "notes": "Currently under maintenance"
        }
        response = requests.put(f"{BASE_URL}/assets/{asset_id}", json=update_data)
        print_response("3.9 Update Asset Status", response)
        if response.status_code == 200:
            test_data["assets"][0] = response.json()
    
    # Retire asset
    if len(test_data["assets"]) > 2:
        asset_id = test_data["assets"][2]["id"]
        response = requests.patch(f"{BASE_URL}/assets/{asset_id}/retire")
        print_response("3.10 Retire Asset", response)
    
    # ========================================
    # 4. INVENTORY TESTS
    # ========================================
    test_section("4. INVENTORY MANAGEMENT")
    
    # Create Inventory Item 1 - Filter (High Stock)
    inv1 = {
        "item_name": "Hydraulic Oil Filter",
        "part_number": f"HF-{int(time.time())}",
        "description": "Standard hydraulic filter",
        "stock_on_hand": 50,
        "min_stock": 10,
        "max_stock": 100,
        "unit_cost": 25.50
    }
    response = requests.post(f"{BASE_URL}/inventory", json=inv1)
    print_response("4.1 Create Inventory - Filter (High Stock)", response)
    if response.status_code == 200:
        test_data["inventory_items"].append(response.json())
    
    # Create Inventory Item 2 - Belt (Low Stock)
    inv2 = {
        "item_name": "Conveyor Belt",
        "part_number": f"CB-{int(time.time())}",
        "description": "Replacement conveyor belt",
        "stock_on_hand": 3,
        "min_stock": 5,
        "max_stock": 15,
        "unit_cost": 450.00
    }
    response = requests.post(f"{BASE_URL}/inventory", json=inv2)
    print_response("4.2 Create Inventory - Belt (Low Stock)", response)
    if response.status_code == 200:
        test_data["inventory_items"].append(response.json())
    
    # Create Inventory Item 3 - Bearing
    inv3 = {
        "item_name": "Bearing Set",
        "part_number": f"BR-{int(time.time())}",
        "description": "Universal bearing set",
        "stock_on_hand": 20,
        "min_stock": 5,
        "max_stock": 30,
        "unit_cost": 85.00
    }
    response = requests.post(f"{BASE_URL}/inventory", json=inv3)
    print_response("4.3 Create Inventory - Bearing", response)
    if response.status_code == 200:
        test_data["inventory_items"].append(response.json())
    
    # Get all inventory
    response = requests.get(f"{BASE_URL}/inventory")
    print_response("4.4 Get All Inventory Items", response)
    
    # Get low stock items
    response = requests.get(f"{BASE_URL}/inventory?low_stock=true")
    print_response("4.5 Get Low Stock Items (Filter)", response)
    
    # Get single inventory item
    if test_data["inventory_items"]:
        inv_id = test_data["inventory_items"][0]["id"]
        response = requests.get(f"{BASE_URL}/inventory/{inv_id}")
        print_response("4.6 Get Single Inventory Item", response)
    
    # Update inventory
    if test_data["inventory_items"]:
        inv_id = test_data["inventory_items"][0]["id"]
        update_data = {
            **test_data["inventory_items"][0],
            "stock_on_hand": 45,
            "notes": "Stock reduced"
        }
        response = requests.put(f"{BASE_URL}/inventory/{inv_id}", json=update_data)
        print_response("4.7 Update Inventory Stock", response)
    
    # ========================================
    # 5. WORK ORDER TESTS
    # ========================================
    test_section("5. WORK ORDER MANAGEMENT")
    
    # Create Work Order 1 - High Priority
    wo1 = {
        "wo_number": f"WO-{int(time.time())}-001",
        "summary": "Replace hydraulic pump seal",
        "description": "Seal is leaking, needs immediate replacement",
        "priority": "High",
        "status": "Open"
    }
    asset_ids = [test_data["assets"][0]["id"]] if test_data["assets"] else []
    response = requests.post(
        f"{BASE_URL}/work-orders", 
        json=wo1,
        params={"asset_ids": asset_ids}
    )
    print_response("5.1 Create Work Order - High Priority", response)
    if response.status_code == 200:
        test_data["work_orders"].append(response.json())
    
    # Create Work Order 2 - Medium Priority
    wo2 = {
        "wo_number": f"WO-{int(time.time())}-002",
        "summary": "Conveyor belt alignment",
        "description": "Belt is running off-center",
        "priority": "Medium",
        "status": "Open"
    }
    asset_ids = [test_data["assets"][1]["id"]] if len(test_data["assets"]) > 1 else []
    response = requests.post(
        f"{BASE_URL}/work-orders",
        json=wo2,
        params={"asset_ids": asset_ids}
    )
    print_response("5.2 Create Work Order - Medium Priority", response)
    if response.status_code == 200:
        test_data["work_orders"].append(response.json())
    
    # Create Work Order 3 - Critical, multiple assets
    wo3 = {
        "wo_number": f"WO-{int(time.time())}-003",
        "summary": "Emergency maintenance",
        "description": "Multiple systems affected",
        "priority": "Critical",
        "status": "Open"
    }
    asset_ids = [a["id"] for a in test_data["assets"][:2]]
    response = requests.post(
        f"{BASE_URL}/work-orders",
        json=wo3,
        params={"asset_ids": asset_ids}
    )
    print_response("5.3 Create Work Order - Critical (Multiple Assets)", response)
    if response.status_code == 200:
        test_data["work_orders"].append(response.json())
    
    # Get all work orders
    response = requests.get(f"{BASE_URL}/work-orders")
    print_response("5.4 Get All Work Orders", response)
    
    # Get work orders by status
    response = requests.get(f"{BASE_URL}/work-orders?status=Open")
    print_response("5.5 Get Open Work Orders (Filter)", response)
    
    # Get work orders by priority
    response = requests.get(f"{BASE_URL}/work-orders?priority=High")
    print_response("5.6 Get High Priority Work Orders (Filter)", response)
    
    # Get single work order
    wo_id = safe_get_id(test_data["work_orders"], 0)
    if wo_id:
        response = requests.get(f"{BASE_URL}/work-orders/{wo_id}")
        print_response("5.7 Get Single Work Order", response)
    
    # Assign technician to work order
    wo_id = safe_get_id(test_data["work_orders"], 0)
    if wo_id:
        response = requests.patch(f"{BASE_URL}/work-orders/{wo_id}/assign?technician=John Smith")
        print_response("5.8 Assign Technician to Work Order", response)
    
    # Update work order status to In Progress
    wo_id = safe_get_id(test_data["work_orders"], 1)
    if wo_id:
        response = requests.patch(
            f"{BASE_URL}/work-orders/{wo_id}/status",
            params={"status": "In Progress"}
        )
        print_response("5.9 Update Work Order to In Progress", response)
    
    # Link additional asset to work order
    wo_id = safe_get_id(test_data["work_orders"], 0)
    asset_id = safe_get_id(test_data["assets"], 2)
    if wo_id and asset_id:
        response = requests.post(f"{BASE_URL}/work-orders/{wo_id}/assets/{asset_id}")
        print_response("5.10 Link Additional Asset to Work Order", response)
    
    # Get work order assets
    wo_id = safe_get_id(test_data["work_orders"], 0)
    if wo_id:
        response = requests.get(f"{BASE_URL}/work-orders/{wo_id}/assets")
        print_response("5.11 Get Work Order Assets", response)
    
    # Add parts to work order
    wo_id = safe_get_id(test_data["work_orders"], 0)
    inv_id = safe_get_id(test_data["inventory_items"], 0)
    if wo_id and inv_id:
        response = requests.post(
            f"{BASE_URL}/work-orders/{wo_id}/parts",
            params={"inventory_item_id": inv_id, "quantity": 2}
        )
        print_response("5.12 Add Parts to Work Order", response)
    
    # Get work order parts
    wo_id = safe_get_id(test_data["work_orders"], 0)
    if wo_id:
        response = requests.get(f"{BASE_URL}/work-orders/{wo_id}/parts")
        print_response("5.13 Get Work Order Parts", response)
    
    # Complete work order with notes and time
    wo_id = safe_get_id(test_data["work_orders"], 2)
    if wo_id:
        response = requests.patch(
            f"{BASE_URL}/work-orders/{wo_id}/status",
            params={
                "status": "Completed",
                "time_spent": 3.5,
                "completion_notes": "Work completed successfully. All systems tested and operational."
            }
        )
        print_response("5.14 Complete Work Order (with notes & time)", response)
    
    # ========================================
    # 6. PREVENTIVE MAINTENANCE TESTS
    # ========================================
    test_section("6. PREVENTIVE MAINTENANCE")
    
    # Create PM Template 1 - Days based
    asset_id = safe_get_id(test_data["assets"], 0)
    if asset_id:
        pm1 = {
            "name": "Quarterly Pump Inspection",
            "description": "Regular quarterly inspection of hydraulic pump",
            "frequency_value": 90,
            "frequency_unit": "Days",
            "asset_id": asset_id,
            "wo_summary_template": "Quarterly Inspection - Hydraulic Pump",
            "wo_description_template": "Perform complete inspection:\n- Check oil levels\n- Inspect seals\n- Test pressure\n- Replace filters",
            "default_priority": "Medium",
            "is_active": True
        }
        response = requests.post(f"{BASE_URL}/pm-templates", json=pm1)
        print_response("6.1 Create PM Template - Days Based", response)
        if response.status_code == 200:
            test_data["pm_templates"].append(response.json())
    
    # Create PM Template 2 - Monthly
    asset_id = safe_get_id(test_data["assets"], 1)
    if asset_id:
        pm2 = {
            "name": "Monthly Conveyor Check",
            "description": "Monthly conveyor maintenance",
            "frequency_value": 1,
            "frequency_unit": "Months",
            "asset_id": asset_id,
            "wo_summary_template": "Monthly Maintenance - Conveyor Belt",
            "wo_description_template": "Monthly checks:\n- Belt tension\n- Roller alignment\n- Lubrication\n- Safety guards",
            "default_priority": "Medium",
            "is_active": True
        }
        response = requests.post(f"{BASE_URL}/pm-templates", json=pm2)
        print_response("6.2 Create PM Template - Monthly", response)
        if response.status_code == 200:
            test_data["pm_templates"].append(response.json())
    
    # Create PM Template 3 - Hours based
    asset_id = safe_get_id(test_data["assets"], 0)
    if asset_id:
        pm3 = {
            "name": "1000-Hour Service",
            "description": "Service every 1000 operating hours",
            "frequency_value": 1000,
            "frequency_unit": "Hours",
            "asset_id": asset_id,
            "wo_summary_template": "1000-Hour Service - Hydraulic Pump",
            "wo_description_template": "Complete service required",
            "default_priority": "High",
            "is_active": True
        }
        response = requests.post(f"{BASE_URL}/pm-templates", json=pm3)
        print_response("6.3 Create PM Template - Hours Based", response)
        if response.status_code == 200:
            test_data["pm_templates"].append(response.json())
    
    # Get all PM templates
    response = requests.get(f"{BASE_URL}/pm-templates")
    print_response("6.4 Get All PM Templates", response)
    
    # Get PM templates by asset
    asset_id = safe_get_id(test_data["assets"], 0)
    if asset_id:
        response = requests.get(f"{BASE_URL}/pm-templates?asset_id={asset_id}")
        print_response("6.5 Get PM Templates by Asset (Filter)", response)
    
    # Get active PM templates
    response = requests.get(f"{BASE_URL}/pm-templates?is_active=true")
    print_response("6.6 Get Active PM Templates (Filter)", response)
    
    # Get due soon PMs (7 days)
    response = requests.get(f"{BASE_URL}/pm-templates/due-soon?days=7")
    print_response("6.7 Get PMs Due in Next 7 Days", response)
    
    # Get due soon PMs (30 days)
    response = requests.get(f"{BASE_URL}/pm-templates/due-soon?days=30")
    print_response("6.8 Get PMs Due in Next 30 Days", response)
    
    # Generate work order from PM template
    pm_id = safe_get_id(test_data["pm_templates"], 0)
    if pm_id:
        response = requests.post(f"{BASE_URL}/pm-templates/{pm_id}/generate-wo")
        print_response("6.9 Generate Work Order from PM Template", response)
        if response.status_code == 200:
            test_data["work_orders"].append(response.json())
    
    # ========================================
    # 7. DASHBOARD & STATISTICS
    # ========================================
    test_section("7. DASHBOARD & STATISTICS")
    
    # Get dashboard stats
    response = requests.get(f"{BASE_URL}/stats/dashboard")
    print_response("7.1 Get Dashboard Statistics", response, show_full=True)
    
    # ========================================
    # 8. EDGE CASES & ERROR HANDLING
    # ========================================
    test_section("8. EDGE CASES & ERROR HANDLING")
    
    # Try to get non-existent asset
    response = requests.get(f"{BASE_URL}/assets/99999")
    print_response("8.1 Get Non-Existent Asset (Should Fail)", response)
    
    # Try to get non-existent work order
    response = requests.get(f"{BASE_URL}/work-orders/99999")
    print_response("8.2 Get Non-Existent Work Order (Should Fail)", response)
    
    # Try to create asset with duplicate asset_id
    asset_data = test_data["assets"][0] if test_data["assets"] else None
    if asset_data:
        duplicate_asset = {
            **asset_data,
            "id": None
        }
        response = requests.post(f"{BASE_URL}/assets", json=duplicate_asset)
        print_response("8.3 Create Duplicate Asset ID (Should Fail)", response)
    
    # Try to add more parts than available in stock
    wo_id = safe_get_id(test_data["work_orders"], 0)
    inv_id = safe_get_id(test_data["inventory_items"], 0)
    if wo_id and inv_id:
        response = requests.post(
            f"{BASE_URL}/work-orders/{wo_id}/parts",
            params={"inventory_item_id": inv_id, "quantity": 10000}
        )
        print_response("8.4 Add Excessive Parts (Should Fail)", response)
    
    # ========================================
    # 9. FILTERING & SEARCH TESTS
    # ========================================
    test_section("9. ADVANCED FILTERING & SEARCH")
    
    # Multiple filters on assets
    response = requests.get(f"{BASE_URL}/assets?status=Active&category=Pumps")
    print_response("9.1 Get Assets with Multiple Filters", response)
    
    # Work orders by technician
    response = requests.get(f"{BASE_URL}/work-orders?technician=John Smith")
    print_response("9.2 Get Work Orders by Technician", response)
    
    # Search assets by serial number
    asset_data = test_data["assets"][0] if test_data["assets"] else None
    if asset_data:
        serial = asset_data.get("serial_number", "")
        if serial:
            response = requests.get(f"{BASE_URL}/assets?search={serial[:10]}")
            print_response("9.3 Search Assets by Serial Number", response)
    
    # ========================================
    # FINAL SUMMARY
    # ========================================
    print("\n" + "="*70)
    print("  📊 TEST SUMMARY")
    print("="*70)
    print(f"  Total Tests: {test_results['total']}")
    print(f"  ✅ Passed: {test_results['passed']}")
    print(f"  ❌ Failed: {test_results['failed']}")
    print(f"  Success Rate: {(test_results['passed']/test_results['total']*100):.1f}%")
    print("="*70)
    
    print(f"\n📊 Created Test Data:")
    print(f"   - Locations: {len(test_data['locations'])}")
    print(f"   - Assets: {len(test_data['assets'])}")
    print(f"   - Inventory Items: {len(test_data['inventory_items'])}")
    print(f"   - Work Orders: {len(test_data['work_orders'])}")
    print(f"   - PM Templates: {len(test_data['pm_templates'])}")
    
    print(f"\n📚 Resources:")
    print(f"   API Documentation: {BASE_URL}/docs")
    print(f"   Dashboard: {BASE_URL}/stats/dashboard")
    print(f"   ReDoc: {BASE_URL}/redoc")
    
    print(f"\n✅ Test suite completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server!")
        print("Please make sure the server is running with:")
        print("  cd backend && uvicorn main:app --reload --port 8003\n")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user\n")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
