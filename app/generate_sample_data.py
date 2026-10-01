#!/usr/bin/env python3
"""
Logistics Cost Analyzer - Sample Data Generator
Generates realistic synthetic shipment data for logistics cost analysis.
Output: input/shipments.csv
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path
import csv

# Realistic Philippine logistics route distances (in km)
ROUTE_DISTANCES = {
    ("Manila", "Cebu"): 780,
    ("Manila", "Davao"): 1500,
    ("Manila", "Baguio"): 250,
    ("Manila", "Iloilo"): 650,
    ("Manila", "Cagayan de Oro"): 1350,
    ("Manila", "Clark"): 90,
    ("Manila", "Bacolod"): 700,
    ("Manila", "General Santos"): 1650,
    ("Manila", "Zamboanga"): 1400,
    ("Cebu", "Davao"): 450,
    ("Cebu", "Iloilo"): 180,
    ("Cebu", "Cagayan de Oro"): 240,
    ("Cebu", "Bacolod"): 110,
    ("Cebu", "Zamboanga"): 520,
    ("Davao", "Cagayan de Oro"): 260,
    ("Davao", "General Santos"): 150,
    ("Clark", "Baguio"): 160,
    ("Clark", "Cebu"): 850,
    ("Clark", "Davao"): 1580,
    ("Iloilo", "Bacolod"): 50,
}

# Fill symmetric routes if not defined
ALL_ROUTES = {}
for (orig, dest), dist in ROUTE_DISTANCES.items():
    ALL_ROUTES[(orig, dest)] = dist
    ALL_ROUTES[(dest, orig)] = dist

# Carriers and their operational profiles
CARRIER_PROFILES = {
    "Carrier A": {"base_rate_km": 14.5, "base_rate_kg": 8.0, "on_time_prob": 0.93, "speed_factor": 1.0},
    "Carrier B": {"base_rate_km": 12.0, "base_rate_kg": 6.8, "on_time_prob": 0.82, "speed_factor": 1.3}, # Cheaper but slower & lower on-time
    "Carrier C": {"base_rate_km": 16.2, "base_rate_kg": 9.2, "on_time_prob": 0.96, "speed_factor": 0.85}, # Premium, fast & high reliability
    "Carrier D": {"base_rate_km": 13.8, "base_rate_kg": 7.5, "on_time_prob": 0.89, "speed_factor": 1.1},
    "Carrier E": {"base_rate_km": 15.0, "base_rate_kg": 8.5, "on_time_prob": 0.91, "speed_factor": 0.95},
}

# Monthly fuel cost multipliers (simulating seasonal fuel surcharge increase in March-April)
MONTHLY_FUEL_MULTIPLIER = {
    1: 1.00,  # Jan
    2: 1.04,  # Feb
    3: 1.12,  # Mar
    4: 1.25,  # Apr (Fuel spike)
    5: 1.18,  # May
    6: 1.10,  # Jun
}

def generate_shipment_dataset(num_records: int = 1250, output_path: str = "input/shipments.csv") -> Path:
    """
    Generates a realistic synthetic shipment dataset and writes it to CSV.
    """
    random.seed(42)  # For reproducible yet realistic data
    
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 30)
    total_days = (end_date - start_date).days
    
    route_keys = list(ALL_ROUTES.keys())
    # Assign higher traffic probability to major hubs like Manila -> Cebu/Davao
    route_weights = []
    for orig, dest in route_keys:
        if orig == "Manila" and dest in ["Cebu", "Davao", "Iloilo", "Baguio", "Cagayan de Oro"]:
            route_weights.append(5)
        elif "Manila" in (orig, dest):
            route_weights.append(3)
        elif "Cebu" in (orig, dest):
            route_weights.append(2)
        else:
            route_weights.append(1)

    carrier_keys = list(CARRIER_PROFILES.keys())
    carrier_weights = [0.28, 0.24, 0.20, 0.16, 0.12]

    records = []
    
    for i in range(1, num_records + 1):
        shipment_id = f"S{i:04d}"
        
        # Random date within Jan - Jun 2026 with slight seasonal volume increase in Q2
        day_offset = random.randint(0, total_days)
        shipment_date = start_date + timedelta(days=day_offset)
        month = shipment_date.month
        
        # Route & Distance
        route = random.choices(route_keys, weights=route_weights, k=1)[0]
        origin, destination = route
        distance_km = ALL_ROUTES[route]
        # Slight variation in actual route distance due to detours/stops
        actual_distance = int(distance_km * random.uniform(0.96, 1.05))
        
        # Carrier
        carrier = random.choices(carrier_keys, weights=carrier_weights, k=1)[0]
        profile = CARRIER_PROFILES[carrier]
        
        # Cargo Weight (log-normal distribution for realistic cargo sizes: 50kg to 2500kg)
        weight_kg = int(random.expovariate(1/450) + 40)
        weight_kg = max(30, min(3500, weight_kg))
        
        # Cost Components (in Philippine Pesos ₱)
        # 1. Base shipping cost: function of distance, weight, and carrier rate
        base_shipping_cost = (
            (actual_distance * profile["base_rate_km"] * 0.45) +
            (weight_kg * profile["base_rate_kg"] * 1.8) +
            random.uniform(500, 1500)
        )
        shipping_cost = round(base_shipping_cost, 2)
        
        # 2. Fuel cost: tied to distance, carrier, and monthly fuel surcharge index
        fuel_multiplier = MONTHLY_FUEL_MULTIPLIER.get(month, 1.05)
        base_fuel_cost = (actual_distance * 3.8) * fuel_multiplier * random.uniform(0.92, 1.08)
        fuel_cost = round(base_fuel_cost, 2)
        
        # 3. Handling cost: tied to cargo weight and special handling
        base_handling_cost = (weight_kg * 2.2) + random.uniform(300, 900)
        handling_cost = round(base_handling_cost, 2)
        
        # Delivery Days: calculated from distance and carrier speed factor
        # e.g., <200km ~ 1-2 days, 200-800km ~ 2-4 days, >1000km ~ 4-7 days
        expected_days = max(1, int((actual_distance / 300) * profile["speed_factor"] + random.uniform(0.5, 1.5)))
        delivery_days = max(1, expected_days)
        
        # On-Time Delivery Flag
        is_on_time = 1 if random.random() <= profile["on_time_prob"] else 0
        if is_on_time == 0:
            # Late shipments take extra days
            delivery_days += random.randint(1, 3)
            
        record = {
            "shipment_id": shipment_id,
            "date": shipment_date.strftime("%Y-%m-%d"),
            "origin": origin,
            "destination": destination,
            "carrier": carrier,
            "distance_km": actual_distance,
            "weight_kg": weight_kg,
            "shipping_cost": shipping_cost,
            "fuel_cost": fuel_cost,
            "handling_cost": handling_cost,
            "delivery_days": delivery_days,
            "on_time": is_on_time,
        }
        records.append(record)
        
    # Inject a realistic small set of dirty records (e.g. 13 records) for the data cleaning stage to detect & handle
    # 4 invalid records to be removed (e.g. negative distance, zero weight, negative cost)
    records[12]["distance_km"] = 0
    records[45]["weight_kg"] = 0
    records[180]["shipping_cost"] = -1500
    records[310]["distance_km"] = -250
    
    # 9 records with missing/imputable values (e.g. null fuel_cost or handling_cost or string whitespace)
    records[88]["fuel_cost"] = ""
    records[142]["handling_cost"] = ""
    records[255]["fuel_cost"] = None
    records[402]["origin"] = " Manila "
    records[512]["destination"] = "Cebu  "
    records[620]["handling_cost"] = ""
    records[735]["fuel_cost"] = ""
    records[840]["handling_cost"] = None
    records[950]["carrier"] = " Carrier A "
    
    # Write to CSV
    headers = [
        "shipment_id", "date", "origin", "destination", "carrier",
        "distance_km", "weight_kg", "shipping_cost", "fuel_cost",
        "handling_cost", "delivery_days", "on_time"
    ]
    
    with open(out_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in records:
            # Handle None representation
            clean_r = {k: ("" if v is None else v) for k, v in r.items()}
            writer.writerow(clean_r)
            
    print("=" * 52)
    print("      LOGISTICS COST ANALYZER - DATA GENERATOR      ")
    print("=" * 52)
    print(f"✓ Generated {len(records):,} realistic shipment records")
    print(f"✓ Date range: 2026-01-01 to 2026-06-30 (H1 2026)")
    print(f"✓ Target file saved: {out_file.as_posix()}")
    print("=" * 52)
    print("Ready to run: python logistics_cost_analyzer.py")
    print("=" * 52)
    
    return out_file

if __name__ == "__main__":
    generate_shipment_dataset()
