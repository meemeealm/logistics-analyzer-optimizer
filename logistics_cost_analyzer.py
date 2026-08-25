#!/usr/bin/env python3
"""
==============================================================================
                          LOGISTICS COST ANALYZER
==============================================================================
A professional Python CLI data science tool for logistics and supply-chain
cost optimization, route and carrier analysis, trend tracking, cost driver
identification, and predictive regression modeling.

Usage:
    python logistics_cost_analyzer.py
    python logistics_cost_analyzer.py --routes
    python logistics_cost_analyzer.py --carriers
    python logistics_cost_analyzer.py --trends
    python logistics_cost_analyzer.py --model
    python logistics_cost_analyzer.py --charts
    python logistics_cost_analyzer.py --export
==============================================================================
"""

import argparse
import os
import sys
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Headless file saving without GUI popup
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from structured_logger import get_logger, log_event
from artifacts_handler import organize_and_package_run

logger = get_logger("logistics_analyzer")


# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

REQUIRED_COLUMNS = [
    "shipment_id",
    "date",
    "origin",
    "destination",
    "carrier",
    "distance_km",
    "weight_kg",
    "shipping_cost",
    "fuel_cost",
    "handling_cost",
    "delivery_days",
    "on_time",
]

DEFAULT_INPUT_DIR = Path("input")
DEFAULT_REPORTS_DIR = Path("reports")
DEFAULT_INPUT_FILE = DEFAULT_INPUT_DIR / "shipments.csv"

# Styling configuration for publication-grade matplotlib/seaborn charts
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "figure.titlesize": 14,
    "figure.autolayout": True,
})


# ============================================================================
# FORMATTING & HELPER UTILITIES
# ============================================================================

def format_currency(value: float, decimal_places: int = 0) -> str:
    """Formats numeric values into Philippine Peso string (e.g. ₱8,421,550 or ₱18.42)."""
    if pd.isna(value) or np.isinf(value):
        return "₱0.00" if decimal_places > 0 else "₱0"
    if decimal_places == 0:
        return f"₱{value:,.0f}"
    return f"₱{value:,.{decimal_places}f}"


def format_currency_short(value: float) -> str:
    """Formats large monetary numbers into concise format (e.g. ₱2.84M, ₱450K)."""
    if pd.isna(value) or np.isinf(value):
        return "₱0"
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"₱{value / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"₱{value / 1_000:.1f}K"
    return f"₱{value:,.0f}"


def print_banner() -> None:
    """Prints the application header banner."""
    print("=" * 60)
    print("                 LOGISTICS COST ANALYZER                 ")
    print("          Supply Chain Cost & Efficiency Engine          ")
    print("=" * 60)


def print_section(title: str) -> None:
    """Prints a styled section header in the terminal."""
    print(f"\n{title}")
    print("-" * 60)


# ============================================================================
# DATA PIPELINE FUNCTIONS
# ============================================================================

def load_data(file_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads shipment CSV data from the specified path or discovers it in input/.
    Exits gracefully with a friendly message if the file is missing or invalid.
    """
    DEFAULT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    target_path: Optional[Path] = file_path

    if target_path is None:
        if DEFAULT_INPUT_FILE.exists():
            target_path = DEFAULT_INPUT_FILE
        else:
            # Look for any CSV file inside the input/ folder
            csv_files = list(DEFAULT_INPUT_DIR.glob("*.csv"))
            if csv_files:
                target_path = csv_files[0]
            else:
                print("\n" + "=" * 60)
                print("ERROR: No input shipment dataset found.")
                print(f"Expected file at: {DEFAULT_INPUT_FILE.as_posix()}")
                print("\nPlease place your shipment CSV inside the 'input/' folder,")
                print("or generate synthetic sample data by running:")
                print("\n    python generate_sample_data.py")
                print("=" * 60 + "\n")
                sys.exit(1)

    if not target_path.exists():
        print(f"\nERROR: The specified file does not exist: {target_path.as_posix()}\n")
        sys.exit(1)

    try:
        df = pd.read_csv(target_path, skipinitialspace=True)
        return df
    except Exception as e:
        print(f"\nERROR: Failed to read CSV file '{target_path.as_posix()}': {e}\n")
        sys.exit(1)


def validate_data(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validates that the DataFrame contains all required shipment columns.
    Returns (is_valid, missing_columns_list).
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        print("\n" + "=" * 60)
        print("ERROR: Required columns are missing:")
        for col in missing:
            print(f"  - {col}")
        print("\nPlease check your input CSV and ensure the header names match.")
        print("=" * 60 + "\n")
        return False, missing
    return True, []


def clean_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw shipment data:
      - Strips string whitespace
      - Coerces and converts numeric types
      - Parses datetime strings
      - Handles missing and zero/negative distance, weight, and cost records
      - Returns (cleaned_df, cleaning_summary_dict)
    """
    initial_rows = len(df)
    df_clean = df.copy()

    # 1. Clean string categorical columns
    string_cols = ["shipment_id", "origin", "destination", "carrier"]
    for col in string_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()

    # 2. Coerce numeric columns
    numeric_cols = [
        "distance_km",
        "weight_kg",
        "shipping_cost",
        "fuel_cost",
        "handling_cost",
        "delivery_days",
        "on_time",
    ]

    missing_handled_count = 0
    for col in numeric_cols:
        if col in df_clean.columns:
            missing_before = df_clean[col].isna().sum()
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    # 3. Date parsing
    df_clean["date"] = pd.to_datetime(df_clean["date"], errors="coerce")
    invalid_dates = df_clean["date"].isna().sum()

    # 4. Handle missing numeric costs by imputing with route/carrier medians or 0
    for cost_col in ["fuel_cost", "handling_cost"]:
        if cost_col in df_clean.columns:
            null_count = df_clean[cost_col].isna().sum()
            if null_count > 0:
                missing_handled_count += null_count
                median_val = df_clean[cost_col].median()
                df_clean[cost_col] = df_clean[cost_col].fillna(median_val if not pd.isna(median_val) else 0)

    # 5. Filter out logically impossible/invalid records (zero/negative distance, weight, or shipping cost)
    valid_mask = (
        (df_clean["date"].notna())
        & (df_clean["distance_km"] > 0)
        & (df_clean["weight_kg"] > 0)
        & (df_clean["shipping_cost"] >= 0)
        & (df_clean["fuel_cost"] >= 0)
        & (df_clean["handling_cost"] >= 0)
        & (df_clean["delivery_days"] >= 0)
        & (df_clean["on_time"].isin([0, 1]))
        & (df_clean["origin"] != "")
        & (df_clean["destination"] != "")
        & (df_clean["carrier"] != "")
    )

    invalid_records_removed = initial_rows - valid_mask.sum()
    df_clean = df_clean[valid_mask].copy()

    # Ensure correct data types
    df_clean["distance_km"] = df_clean["distance_km"].astype(float)
    df_clean["weight_kg"] = df_clean["weight_kg"].astype(float)
    df_clean["shipping_cost"] = df_clean["shipping_cost"].astype(float)
    df_clean["fuel_cost"] = df_clean["fuel_cost"].astype(float)
    df_clean["handling_cost"] = df_clean["handling_cost"].astype(float)
    df_clean["delivery_days"] = df_clean["delivery_days"].astype(int)
    df_clean["on_time"] = df_clean["on_time"].astype(int)

    summary = {
        "rows_loaded": initial_rows,
        "rows_cleaned": len(df_clean),
        "missing_handled": missing_handled_count,
        "invalid_removed": invalid_records_removed,
    }

    return df_clean, summary


def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Creates derived logistics domain variables:
      - total_cost
      - cost_per_km
      - cost_per_kg
      - fuel_cost_ratio
      - handling_cost_ratio
      - month (YYYY-MM)
      - month_name (e.g. January 2026)
      - route (Origin → Destination)
      - delivery_delay (1 if late, else 0)
    """
    df_fe = df.copy()

    # 1. total_cost = shipping_cost + fuel_cost + handling_cost
    df_fe["total_cost"] = (
        df_fe["shipping_cost"] + df_fe["fuel_cost"] + df_fe["handling_cost"]
    )

    # 2. cost_per_km (protected against division by zero)
    df_fe["cost_per_km"] = np.where(
        df_fe["distance_km"] > 0,
        df_fe["total_cost"] / df_fe["distance_km"],
        0.0,
    )

    # 3. cost_per_kg (protected against division by zero)
    df_fe["cost_per_kg"] = np.where(
        df_fe["weight_kg"] > 0,
        df_fe["total_cost"] / df_fe["weight_kg"],
        0.0,
    )

    # 4. Cost component ratios
    df_fe["fuel_cost_ratio"] = np.where(
        df_fe["total_cost"] > 0,
        df_fe["fuel_cost"] / df_fe["total_cost"],
        0.0,
    )
    df_fe["handling_cost_ratio"] = np.where(
        df_fe["total_cost"] > 0,
        df_fe["handling_cost"] / df_fe["total_cost"],
        0.0,
    )

    # 5. Time and Route features
    df_fe["month"] = df_fe["date"].dt.strftime("%Y-%m")
    df_fe["month_name"] = df_fe["date"].dt.strftime("%B %Y")
    df_fe["route"] = df_fe["origin"] + " → " + df_fe["destination"]

    # 6. Delivery delay indicator
    df_fe["delivery_delay"] = np.where(df_fe["on_time"] == 0, 1, 0)

    feature_list = [
        "total_cost",
        "cost_per_km",
        "cost_per_kg",
        "fuel_cost_ratio",
        "handling_cost_ratio",
        "month",
        "month_name",
        "route",
        "delivery_delay",
    ]

    return df_fe, feature_list


# ============================================================================
# ANALYTICAL MODULES
# ============================================================================

def calculate_overall_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates overall dataset cost, distance, weight, and delivery KPIs."""
    total_shipments = len(df)
    total_cost = df["total_cost"].sum()
    avg_cost = df["total_cost"].mean()
    median_cost = df["total_cost"].median()
    min_cost = df["total_cost"].min()
    max_cost = df["total_cost"].max()

    total_distance = df["distance_km"].sum()
    avg_distance = df["distance_km"].mean()
    total_weight = df["weight_kg"].sum()
    avg_weight = df["weight_kg"].mean()

    avg_cost_km = df["cost_per_km"].mean()
    avg_cost_kg = df["cost_per_kg"].mean()

    avg_delivery_days = df["delivery_days"].mean()
    on_time_count = df["on_time"].sum()
    on_time_pct = (on_time_count / total_shipments) * 100 if total_shipments > 0 else 0
    late_pct = 100.0 - on_time_pct

    date_min = df["date"].min().strftime("%b %Y") if pd.notna(df["date"].min()) else "N/A"
    date_max = df["date"].max().strftime("%b %Y") if pd.notna(df["date"].max()) else "N/A"

    return {
        "total_shipments": total_shipments,
        "date_range": f"{date_min} - {date_max}",
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "median_cost": median_cost,
        "min_cost": min_cost,
        "max_cost": max_cost,
        "total_distance": total_distance,
        "avg_distance": avg_distance,
        "total_weight": total_weight,
        "avg_weight": avg_weight,
        "avg_cost_km": avg_cost_km,
        "avg_cost_kg": avg_cost_kg,
        "avg_delivery_days": avg_delivery_days,
        "on_time_pct": on_time_pct,
        "late_pct": late_pct,
    }


def analyze_routes(df: pd.DataFrame, output_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs comprehensive route-level logistics analysis.
    Identifies highest spending, highest volume, and most cost-efficient routes.
    Exports reports/route_analysis.csv.
    """
    route_grp = df.groupby("route").agg(
        shipments=("shipment_id", "count"),
        total_cost=("total_cost", "sum"),
        avg_cost=("total_cost", "mean"),
        avg_distance=("distance_km", "mean"),
        avg_weight=("weight_kg", "mean"),
        avg_cost_km=("cost_per_km", "mean"),
        avg_cost_kg=("cost_per_kg", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        on_time_pct=("on_time", lambda x: (x.sum() / len(x)) * 100),
    ).reset_index()

    route_grp = route_grp.sort_values(by="total_cost", ascending=False)
    
    # Save full CSV
    csv_path = output_dir / "route_analysis.csv"
    route_grp.to_csv(csv_path, index=False)

    top_10 = route_grp.head(10).copy()
    return route_grp, top_10


def analyze_carriers(df: pd.DataFrame, output_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Evaluates carrier performance across cost efficiency, speed, and delivery reliability.
    Computes a composite Carrier Performance Score (0 - 100):
      - On-Time Delivery Reliability (40% weight)
      - Delivery Speed Factor (30% weight)
      - Cost Competitiveness (30% weight)
    Exports reports/carrier_analysis.csv.
    """
    carrier_grp = df.groupby("carrier").agg(
        shipments=("shipment_id", "count"),
        total_cost=("total_cost", "sum"),
        avg_cost=("total_cost", "mean"),
        avg_cost_km=("cost_per_km", "mean"),
        avg_cost_kg=("cost_per_kg", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        on_time_pct=("on_time", lambda x: (x.sum() / len(x)) * 100),
    ).reset_index()

    # Calculate transparent normalized performance score
    fleet_avg_cost_km = carrier_grp["avg_cost_km"].mean()
    fleet_avg_days = carrier_grp["avg_delivery_days"].mean()

    scores = []
    for _, row in carrier_grp.iterrows():
        # Component 1: Reliability (0 - 40 pts)
        reliability_score = (row["on_time_pct"] / 100.0) * 40.0

        # Component 2: Speed Efficiency (0 - 30 pts)
        # Faster than fleet average earns higher points
        speed_ratio = fleet_avg_days / max(row["avg_delivery_days"], 0.1)
        speed_score = min(30.0, max(10.0, speed_ratio * 30.0 * 0.95))

        # Component 3: Cost Efficiency (0 - 30 pts)
        # Lower cost/km than fleet average earns higher points
        cost_ratio = fleet_avg_cost_km / max(row["avg_cost_km"], 0.1)
        cost_score = min(30.0, max(10.0, cost_ratio * 30.0 * 0.95))

        total_score = round(reliability_score + speed_score + cost_score, 1)
        # Bound score between 0 and 100
        total_score = min(100.0, max(0.0, total_score))
        scores.append(total_score)

    carrier_grp["score"] = scores
    carrier_grp = carrier_grp.sort_values(by="score", ascending=False)

    csv_path = output_dir / "carrier_analysis.csv"
    carrier_grp.to_csv(csv_path, index=False)

    best_carrier = carrier_grp.iloc[0]["carrier"]
    best_score = carrier_grp.iloc[0]["score"]
    lowest_cost_carrier = carrier_grp.sort_values(by="avg_cost").iloc[0]["carrier"]
    highest_rel_carrier = carrier_grp.sort_values(by="on_time_pct", ascending=False).iloc[0]["carrier"]

    info = {
        "best_carrier": best_carrier,
        "best_score": best_score,
        "lowest_cost_carrier": lowest_cost_carrier,
        "highest_rel_carrier": highest_rel_carrier,
    }

    return carrier_grp, info


def analyze_trends(df: pd.DataFrame, output_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Performs monthly time-series aggregation and computes Month-over-Month (MoM) % changes.
    Identifies significant cost acceleration periods.
    Exports reports/monthly_analysis.csv.
    """
    monthly = df.groupby(["month", "month_name"]).agg(
        shipments=("shipment_id", "count"),
        total_cost=("total_cost", "sum"),
        avg_cost=("total_cost", "mean"),
        avg_cost_km=("cost_per_km", "mean"),
        avg_cost_kg=("cost_per_kg", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        on_time_pct=("on_time", lambda x: (x.sum() / len(x)) * 100),
    ).reset_index()

    monthly = monthly.sort_values(by="month")

    # Calculate MoM percentage changes
    monthly["cost_mom_pct"] = monthly["total_cost"].pct_change() * 100.0
    monthly["avg_cost_mom_pct"] = monthly["avg_cost"].pct_change() * 100.0

    csv_path = output_dir / "monthly_analysis.csv"
    monthly.to_csv(csv_path, index=False)

    # Trend insights
    first_month_cost = monthly.iloc[0]["total_cost"]
    last_month_cost = monthly.iloc[-1]["total_cost"]
    first_month_name = monthly.iloc[0]["month_name"]
    last_month_name = monthly.iloc[-1]["month_name"]

    overall_cost_change_pct = (
        ((last_month_cost - first_month_cost) / first_month_cost) * 100.0
        if first_month_cost > 0
        else 0.0
    )

    # Find highest MoM jump
    valid_mom = monthly.dropna(subset=["cost_mom_pct"])
    if not valid_mom.empty:
        max_jump_idx = valid_mom["cost_mom_pct"].idxmax()
        max_jump_row = monthly.loc[max_jump_idx]
        prev_row = monthly.loc[max_jump_idx - 1]
        largest_surge_period = f"{prev_row['month_name']} → {max_jump_row['month_name']}"
        largest_surge_pct = max_jump_row["cost_mom_pct"]
    else:
        largest_surge_period = "N/A"
        largest_surge_pct = 0.0

    trend_info = {
        "overall_change_pct": overall_cost_change_pct,
        "first_month": first_month_name,
        "last_month": last_month_name,
        "largest_surge_period": largest_surge_period,
        "largest_surge_pct": largest_surge_pct,
    }

    return monthly, trend_info


def analyze_cost_drivers(df: pd.DataFrame, output_dir: Path) -> Tuple[pd.DataFrame, str]:
    """
    Computes Pearson correlation coefficients of numerical attributes against total_cost.
    Identifies top positive and negative cost drivers.
    Exports reports/cost_driver_analysis.csv.
    """
    numeric_candidates = [
        ("distance_km", "Distance (km)"),
        ("weight_kg", "Weight (kg)"),
        ("fuel_cost", "Fuel Cost"),
        ("handling_cost", "Handling Cost"),
        ("shipping_cost", "Shipping Base Cost"),
        ("delivery_days", "Delivery Days"),
        ("cost_per_km", "Cost per km"),
        ("cost_per_kg", "Cost per kg"),
    ]

    records = []
    for col, label in numeric_candidates:
        if col in df.columns:
            corr = df["total_cost"].corr(df[col])
            records.append({
                "variable": label,
                "raw_column": col,
                "correlation": round(corr, 3) if pd.notna(corr) else 0.0,
                "abs_correlation": abs(corr) if pd.notna(corr) else 0.0,
            })

    driver_df = pd.DataFrame(records).sort_values(by="abs_correlation", ascending=False)
    driver_df = driver_df.drop(columns=["abs_correlation"])

    csv_path = output_dir / "cost_driver_analysis.csv"
    driver_df.to_csv(csv_path, index=False)

    top_driver = driver_df.iloc[0]["variable"]
    top_corr = driver_df.iloc[0]["correlation"]

    return driver_df, f"{top_driver} (r = {top_corr:+.2f})"


def train_regression_model(df: pd.DataFrame, output_dir: Path) -> Dict[str, Any]:
    """
    Trains a Linear Regression model to predict shipment total_cost from
    distance, weight, fuel cost, handling cost, and delivery duration.
    Computes R², MAE, and RMSE on an 80/20 train-test split.
    Exports reports/regression_results.txt.
    """
    feature_cols = ["distance_km", "weight_kg", "fuel_cost", "handling_cost", "delivery_days"]
    X = df[feature_cols].copy()
    y = df["total_cost"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    coefficients = dict(zip(feature_cols, model.coef_))
    intercept = model.intercept_

    # Create detailed text report
    report_lines = [
        "=" * 60,
        "              REGRESSION MODEL EVALUATION REPORT            ",
        "=" * 60,
        f"Model Algorithm:        Linear Regression (Ordinary Least Squares)",
        f"Training Observations:  {len(X_train):,}",
        f"Testing Observations:   {len(X_test):,} (20% holdout split)",
        f"Target Variable:        total_cost (₱)",
        "-" * 60,
        "MODEL PERFORMANCE METRICS:",
        f"  • R² (Variance Explained):  {r2:.4f} ({r2*100:.1f}%)",
        f"  • Mean Absolute Error (MAE): {format_currency(mae, 2)}",
        f"  • Root Mean Sq Error (RMSE): {format_currency(rmse, 2)}",
        "-" * 60,
        "FEATURE COEFFICIENTS:",
        f"  • Intercept:                {intercept:+,.2f}",
    ]

    for col, coef in coefficients.items():
        report_lines.append(f"  • {col:<24}: {coef:+,.4f}")

    report_lines.extend([
        "-" * 60,
        "BUSINESS INTERPRETATION:",
        f"  The model accounts for approximately {r2*100:.1f}% of the total",
        "  variation in logistics shipping costs across routes and carriers.",
        f"  On unseen test shipments, the average prediction error is {format_currency(mae, 0)}.",
        "=" * 60,
    ])

    report_content = "\n".join(report_lines)
    txt_path = output_dir / "regression_results.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return {
        "r2": r2,
        "mae": mae,
        "rmse": rmse,
        "coefficients": coefficients,
        "intercept": intercept,
        "report_text": report_content,
    }


# ============================================================================
# DATA VISUALIZATION
# ============================================================================

def generate_charts(
    df: pd.DataFrame,
    route_summary: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    output_dir: Path,
) -> List[str]:
    """
    Generates 7 publication-grade data visualizations in reports/ directory:
      1. monthly_cost_trend.png
      2. top_routes.png
      3. carrier_cost_comparison.png
      4. cost_vs_distance.png
      5. cost_vs_weight.png
      6. cost_distribution.png
      7. on_time_delivery_by_carrier.png
    """
    generated_charts = []

    # Palette setup
    primary_color = "#1E40AF"  # Slate Blue
    accent_color = "#0D9488"   # Teal
    warm_color = "#D97706"     # Amber
    alert_color = "#DC2626"    # Rose Red

    # ------------------------------------------------------------------------
    # 1. Monthly Cost Trend
    # ------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    x_labels = monthly_summary["month"]
    ax1.bar(
        x_labels,
        monthly_summary["total_cost"] / 1_000_000,
        color="#3B82F6",
        alpha=0.85,
        width=0.45,
        label="Total Spending (₱ Millions)",
    )
    ax1.set_xlabel("Month", fontweight="bold", labelpad=8)
    ax1.set_ylabel("Total Cost (₱ Millions)", fontweight="bold", color="#1E3A8A")
    ax1.tick_params(axis="y", labelcolor="#1E3A8A")
    ax1.set_title("Monthly Total Logistics Cost Trend", pad=12)

    # Add data labels
    for i, val in enumerate(monthly_summary["total_cost"] / 1_000_000):
        ax1.text(i, val + 0.05, f"₱{val:.2f}M", ha="center", va="bottom", fontsize=9, fontweight="bold")

    # Secondary axis for shipments
    ax2 = ax1.twinx()
    ax2.plot(
        x_labels,
        monthly_summary["shipments"],
        color="#EF4444",
        marker="o",
        linewidth=2.5,
        markersize=7,
        label="Shipment Count",
    )
    ax2.set_ylabel("Number of Shipments", fontweight="bold", color="#B91C1C")
    ax2.tick_params(axis="y", labelcolor="#B91C1C")
    ax2.grid(False)

    fig.tight_layout()
    chart1_path = output_dir / "monthly_cost_trend.png"
    plt.savefig(chart1_path, dpi=300)
    plt.close()
    generated_charts.append("monthly_cost_trend.png")

    # ------------------------------------------------------------------------
    # 2. Top 10 Routes by Total Spending
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    top10_routes = route_summary.head(10).sort_values(by="total_cost", ascending=True)
    y_pos = np.arange(len(top10_routes))
    
    bars = ax.barh(
        y_pos,
        top10_routes["total_cost"] / 1_000_000,
        color="#0284C7",
        edgecolor="#0369A1",
        alpha=0.9,
    )
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top10_routes["route"], fontsize=10)
    ax.set_xlabel("Total Spend (₱ Millions)", fontweight="bold", labelpad=8)
    ax.set_title("Top 10 Logistics Routes by Total Transportation Cost", pad=12)

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.03, bar.get_y() + bar.get_height()/2, f"₱{w:.2f}M", va="center", fontsize=9, fontweight="bold")

    fig.tight_layout()
    chart2_path = output_dir / "top_routes.png"
    plt.savefig(chart2_path, dpi=300)
    plt.close()
    generated_charts.append("top_routes.png")

    # ------------------------------------------------------------------------
    # 3. Carrier Cost Comparison
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))
    carrier_sorted = carrier_summary.sort_values(by="avg_cost", ascending=False)
    
    bars = ax.bar(
        carrier_sorted["carrier"],
        carrier_sorted["avg_cost"],
        color="#059669",
        edgecolor="#047857",
        alpha=0.88,
        width=0.5,
    )
    ax.set_ylabel("Average Cost per Shipment (₱)", fontweight="bold", labelpad=8)
    ax.set_xlabel("Carrier", fontweight="bold", labelpad=8)
    ax.set_title("Average Shipment Cost by Logistics Carrier", pad=12)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 80, f"₱{h:,.0f}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    fig.tight_layout()
    chart3_path = output_dir / "carrier_cost_comparison.png"
    plt.savefig(chart3_path, dpi=300)
    plt.close()
    generated_charts.append("carrier_cost_comparison.png")

    # ------------------------------------------------------------------------
    # 4. Total Cost vs Distance (km)
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x_dist = df["distance_km"].to_numpy()
    y_cost = df["total_cost"].to_numpy()
    
    ax.scatter(x_dist, y_cost, alpha=0.35, color="#2563EB", s=25, edgecolors="none", label="Shipment Data")
    
    # Calculate OLS fit line directly with numpy
    if len(x_dist) > 1:
        slope, intercept = np.polyfit(x_dist, y_cost, 1)
        x_line = np.linspace(x_dist.min(), x_dist.max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, color="#DC2626", linewidth=2.2, label=f"Trendline (slope = ₱{slope:.2f}/km)")
        
    ax.set_xlabel("Route Distance (km)", fontweight="bold", labelpad=8)
    ax.set_ylabel("Total Shipment Cost (₱)", fontweight="bold", labelpad=8)
    ax.set_title("Logistics Cost vs Route Distance (with Linear Fit)", pad=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"₱{x:,.0f}"))
    ax.legend(frameon=True, loc="upper left")

    fig.tight_layout()
    chart4_path = output_dir / "cost_vs_distance.png"
    plt.savefig(chart4_path, dpi=300)
    plt.close()
    generated_charts.append("cost_vs_distance.png")

    # ------------------------------------------------------------------------
    # 5. Total Cost vs Weight (kg)
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x_wt = df["weight_kg"].to_numpy()
    
    ax.scatter(x_wt, y_cost, alpha=0.35, color="#7C3AED", s=25, edgecolors="none", label="Shipment Data")
    
    if len(x_wt) > 1:
        slope_w, intercept_w = np.polyfit(x_wt, y_cost, 1)
        x_w_line = np.linspace(x_wt.min(), x_wt.max(), 100)
        y_w_line = slope_w * x_w_line + intercept_w
        ax.plot(x_w_line, y_w_line, color="#D97706", linewidth=2.2, label=f"Trendline (slope = ₱{slope_w:.2f}/kg)")
        
    ax.set_xlabel("Cargo Weight (kg)", fontweight="bold", labelpad=8)
    ax.set_ylabel("Total Shipment Cost (₱)", fontweight="bold", labelpad=8)
    ax.set_title("Logistics Cost vs Cargo Weight (with Linear Fit)", pad=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"₱{x:,.0f}"))
    ax.legend(frameon=True, loc="upper left")

    fig.tight_layout()
    chart5_path = output_dir / "cost_vs_weight.png"
    plt.savefig(chart5_path, dpi=300)
    plt.close()
    generated_charts.append("cost_vs_weight.png")

    # ------------------------------------------------------------------------
    # 6. Cost Distribution (Histogram)
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))
    costs = df["total_cost"].to_numpy()
    
    n, bins, patches = ax.hist(
        costs,
        bins=35,
        color="#0891B2",
        edgecolor="white",
        alpha=0.85,
        density=False,
    )
    
    median_val = float(df["total_cost"].median())
    mean_val = float(df["total_cost"].mean())
    ax.axvline(median_val, color="#DC2626", linestyle="--", linewidth=1.8, label=f"Median: ₱{median_val:,.0f}")
    ax.axvline(mean_val, color="#D97706", linestyle=":", linewidth=1.8, label=f"Mean: ₱{mean_val:,.0f}")
    
    ax.set_xlabel("Total Shipment Cost (₱)", fontweight="bold", labelpad=8)
    ax.set_ylabel("Frequency (Shipment Count)", fontweight="bold", labelpad=8)
    ax.set_title("Distribution of Shipment Total Logistics Costs", pad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"₱{x:,.0f}"))
    ax.legend(frameon=True, loc="upper right")

    fig.tight_layout()
    chart6_path = output_dir / "cost_distribution.png"
    plt.savefig(chart6_path, dpi=300)
    plt.close()
    generated_charts.append("cost_distribution.png")

    # ------------------------------------------------------------------------
    # 7. On-Time Delivery & Performance Score by Carrier
    # ------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    carriers = carrier_summary["carrier"]
    x = np.arange(len(carriers))
    width = 0.35

    rects1 = ax.bar(
        x - width/2,
        carrier_summary["on_time_pct"],
        width,
        label="On-Time Delivery Rate (%)",
        color="#2563EB",
        alpha=0.88,
    )
    rects2 = ax.bar(
        x + width/2,
        carrier_summary["score"],
        width,
        label="Performance Score (0-100)",
        color="#10B981",
        alpha=0.88,
    )

    ax.set_ylabel("Percentage / Score", fontweight="bold", labelpad=8)
    ax.set_xlabel("Carrier", fontweight="bold", labelpad=8)
    ax.set_title("Carrier Reliability: On-Time Rate vs Composite Score", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(carriers)
    ax.set_ylim(0, 115)
    ax.legend(loc="upper right", frameon=True)

    for rect in rects1:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 1.5, f"{h:.1f}%", ha="center", va="bottom", fontsize=8.5)

    for rect in rects2:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2, h + 1.5, f"{h:.1f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    fig.tight_layout()
    chart7_path = output_dir / "on_time_delivery_by_carrier.png"
    plt.savefig(chart7_path, dpi=300)
    plt.close()
    generated_charts.append("on_time_delivery_by_carrier.png")

    return generated_charts


# ============================================================================
# BUSINESS INSIGHTS & RECOMMENDATIONS GENERATOR
# ============================================================================

def generate_business_insights(
    metrics: Dict[str, Any],
    route_summary: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    trend_info: Dict[str, Any],
    cost_drivers: pd.DataFrame,
    regression_info: Dict[str, Any],
) -> Tuple[List[str], List[str]]:
    """
    Dynamically generates data-grounded key findings and actionable business recommendations.
    """
    findings = []
    recommendations = []

    # 1. Top Route Finding
    top_route = route_summary.iloc[0]
    top_route_share = (top_route["total_cost"] / metrics["total_cost"]) * 100
    findings.append(
        f"{top_route['route']} represents the largest share of transportation spending "
        f"({format_currency_short(top_route['total_cost'])}, or {top_route_share:.1f}% of total budget)."
    )

    # 2. Trend Finding
    if trend_info["largest_surge_pct"] > 0:
        findings.append(
            f"Logistics costs peaked during {trend_info['largest_surge_period']} with a "
            f"+{trend_info['largest_surge_pct']:.1f}% month-over-month increase."
        )
    else:
        findings.append(
            f"Overall freight spend changed {trend_info['overall_change_pct']:+.1f}% across the analyzed period."
        )

    # 3. Carrier Finding
    lowest_cost_carrier_row = carrier_summary.sort_values(by="avg_cost").iloc[0]
    highest_rel_carrier_row = carrier_summary.sort_values(by="on_time_pct", ascending=False).iloc[0]
    
    if lowest_cost_carrier_row["carrier"] != highest_rel_carrier_row["carrier"]:
        findings.append(
            f"{lowest_cost_carrier_row['carrier']} offers the lowest average cost per shipment ({format_currency(lowest_cost_carrier_row['avg_cost'])}), "
            f"but delivers a lower on-time rate ({lowest_cost_carrier_row['on_time_pct']:.1f}%) compared to "
            f"{highest_rel_carrier_row['carrier']} ({highest_rel_carrier_row['on_time_pct']:.1f}% on-time at {format_currency(highest_rel_carrier_row['avg_cost'])})."
        )
    else:
        findings.append(
            f"{lowest_cost_carrier_row['carrier']} leads both cost-efficiency and delivery reliability."
        )

    # 4. Cost Driver Finding
    top_driver_row = cost_drivers.iloc[0]
    findings.append(
        f"{top_driver_row['variable']} exhibits the strongest numerical relationship with logistics cost "
        f"(Pearson r = {top_driver_row['correlation']:+.2f})."
    )

    # 5. Regression Model Finding
    findings.append(
        f"The model explains {regression_info['r2']*100:.1f}% of cost variance "
        f"with an average prediction accuracy of ±{format_currency(regression_info['mae'], 0)}."
    )

    # Recommendations
    recommendations.append(
        f"Prioritize rate renegotiation and shipment consolidation for high-spend corridor '{top_route['route']}' "
        "to yield the largest absolute monetary savings."
    )

    if trend_info["largest_surge_pct"] > 5.0:
        recommendations.append(
            f"Investigate root drivers of the cost surge during {trend_info['largest_surge_period']} "
            "(e.g., fuel price spikes, surcharges, or peak demand volatility) to build cost hedging strategies."
        )

    recommendations.append(
        f"Adopt a tiered carrier assignment strategy: Allocate time-critical deliveries to {highest_rel_carrier_row['carrier']} "
        f"and bulk/flexible freight to {lowest_cost_carrier_row['carrier']} to balance speed against unit costs."
    )

    recommendations.append(
        "Monitor cost-per-kilometer and cargo density thresholds to optimize truckload capacity and prevent deadhead mileage."
    )

    return findings, recommendations


# ============================================================================
# EXPORT & TERMINAL PRESENTATION
# ============================================================================

def export_reports(
    metrics: Dict[str, Any],
    cleaning_stats: Dict[str, Any],
    route_summary: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    cost_drivers: pd.DataFrame,
    regression_info: Dict[str, Any],
    findings: List[str],
    recommendations: List[str],
    output_dir: Path,
) -> Path:
    """
    Generates summary.txt combining executive overview, KPIs, findings, and recommendations.
    """
    summary_path = output_dir / "summary.txt"

    lines = [
        "=" * 64,
        "           LOGISTICS COST ANALYZER - EXECUTIVE SUMMARY          ",
        "=" * 64,
        f"Generated On:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Analysis Date Range:     {metrics['date_range']}",
        f"Total Shipments:         {metrics['total_shipments']:,}",
        f"Total Logistics Cost:    {format_currency(metrics['total_cost'])}",
        f"Average Shipment Cost:   {format_currency(metrics['avg_cost'], 2)}",
        f"Median Shipment Cost:    {format_currency(metrics['median_cost'], 2)}",
        f"Average Cost / km:       {format_currency(metrics['avg_cost_km'], 2)}",
        f"Average Cost / kg:       {format_currency(metrics['avg_cost_kg'], 2)}",
        f"On-Time Delivery Rate:   {metrics['on_time_pct']:.1f}%",
        f"Average Transit Time:    {metrics['avg_delivery_days']:.1f} days",
        "-" * 64,
        "TOP 5 ROUTES BY EXPENDITURE:",
    ]

    for idx, (_, r) in enumerate(route_summary.head(5).iterrows(), start=1):
        lines.append(
            f"  {idx}. {r['route']:<26} {r['shipments']:>5} shipments | "
            f"Total: {format_currency(r['total_cost']):>12} | Avg: {format_currency(r['avg_cost']):>9}"
        )

    lines.extend([
        "-" * 64,
        "CARRIER PERFORMANCE RANKING:",
    ])

    for idx, (_, c) in enumerate(carrier_summary.iterrows(), start=1):
        lines.append(
            f"  {idx}. {c['carrier']:<16} Score: {c['score']:>4.1f}/100 | "
            f"Avg Cost: {format_currency(c['avg_cost']):>8} | On-Time: {c['on_time_pct']:>5.1f}%"
        )

    lines.extend([
        "-" * 64,
        "KEY FINDINGS:",
    ])
    for idx, finding in enumerate(findings, start=1):
        lines.append(f"  {idx}. {finding}")

    lines.extend([
        "-" * 64,
        "STRATEGIC RECOMMENDATIONS:",
    ])
    for idx, rec in enumerate(recommendations, start=1):
        lines.append(f"  → {rec}")

    lines.extend([
        "=" * 64,
        "END OF SUMMARY",
        "=" * 64,
    ])

    summary_text = "\n".join(lines)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    return summary_path


def display_dashboard(
    metrics: Dict[str, Any],
    route_summary: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    cost_drivers: pd.DataFrame,
    regression_info: Dict[str, Any],
    findings: List[str],
    recommendations: List[str],
) -> None:
    """Prints the comprehensive analysis dashboard to the terminal."""
    print("\n" + "=" * 60)
    print("                    EXECUTIVE DASHBOARD                    ")
    print("=" * 60)
    print(f"DATASET")
    print(f"  Shipments analyzed:     {metrics['total_shipments']:,}")
    print(f"  Date range:             {metrics['date_range']}")
    print(f"\nCOST SUMMARY")
    print(f"  Total logistics cost:   {format_currency(metrics['total_cost'])}")
    print(f"  Average shipment cost:  {format_currency(metrics['avg_cost'], 2)}")
    print(f"  Median shipment cost:   {format_currency(metrics['median_cost'], 2)}")
    print(f"  Min / Max shipment:     {format_currency(metrics['min_cost'])} / {format_currency(metrics['max_cost'])}")
    print(f"\nEFFICIENCY & DELIVERY")
    print(f"  Average cost/km:        {format_currency(metrics['avg_cost_km'], 2)}")
    print(f"  Average cost/kg:        {format_currency(metrics['avg_cost_kg'], 2)}")
    print(f"  Average transit time:   {metrics['avg_delivery_days']:.1f} days")
    print(f"  On-time delivery rate:  {metrics['on_time_pct']:.1f}%")
    print(f"  Late shipments:         {metrics['late_pct']:.1f}%")
    print("=" * 60)

    # Top Routes Table
    print_section("TOP 5 ROUTES BY TOTAL COST")
    print(f"{'Route':<26} {'Shipments':>10} {'Total Cost':>15} {'Avg Cost':>12}")
    print("-" * 66)
    for _, r in route_summary.head(5).iterrows():
        print(f"{r['route']:<26} {r['shipments']:>10,} {format_currency_short(r['total_cost']):>15} {format_currency(r['avg_cost']):>12}")

    # Carrier Performance Table
    print_section("CARRIER PERFORMANCE SUMMARY")
    print(f"{'Carrier':<14} {'Shipments':>10} {'Avg Cost':>12} {'On-Time':>10} {'Avg Days':>10} {'Score':>8}")
    print("-" * 68)
    for _, c in carrier_summary.iterrows():
        print(f"{c['carrier']:<14} {c['shipments']:>10,} {format_currency(c['avg_cost']):>12} {c['on_time_pct']:>9.1f}% {c['avg_delivery_days']:>9.1f} {c['score']:>8.1f}")
    print("\n* Methodology: Performance Score (0-100) incorporates On-Time Reliability (40%),")
    print("  Transit Speed Efficiency (30%), and Unit Cost Competitiveness (30%).")

    # Monthly Trends Table
    print_section("MONTHLY LOGISTICS COST TREND")
    print(f"{'Month':<12} {'Shipments':>10} {'Total Cost':>15} {'Avg Cost':>12} {'MoM Change':>12}")
    print("-" * 65)
    for _, m in monthly_summary.iterrows():
        mom_str = f"{m['cost_mom_pct']:+.1f}%" if pd.notna(m['cost_mom_pct']) else "-"
        print(f"{m['month']:<12} {m['shipments']:>10,} {format_currency_short(m['total_cost']):>15} {format_currency(m['avg_cost']):>12} {mom_str:>12}")

    # Cost Driver Analysis Table
    print_section("COST DRIVER CORRELATION (Pearson r with Total Cost)")
    print(f"{'Variable':<28} {'Correlation':>14}")
    print("-" * 44)
    for _, d in cost_drivers.iterrows():
        print(f"{d['variable']:<28} {d['correlation']:>+14.2f}")
    print("\n* Note: Correlation indicates numerical association and does not imply causation.")

    # Regression Summary
    print_section("PREDICTIVE REGRESSION MODEL (OLS)")
    print(f"  R² (Variance Explained):   {regression_info['r2']:.4f} ({regression_info['r2']*100:.1f}%)")
    print(f"  Mean Absolute Error (MAE): {format_currency(regression_info['mae'], 2)}")
    print(f"  Root Mean Sq Error (RMSE): {format_currency(regression_info['rmse'], 2)}")

    # Business Recommendations
    print("\n" + "=" * 60)
    print("                   BUSINESS INSIGHTS & ACTIONS             ")
    print("=" * 60)
    print("\nKEY FINDINGS:")
    for idx, f in enumerate(findings, start=1):
        print(f"  {idx}. {f}")

    print("\nSTRATEGIC RECOMMENDATIONS:")
    for idx, r in enumerate(recommendations, start=1):
        print(f"  → {r}")
    print("=" * 60 + "\n")


# ============================================================================
# MAIN ENTRY POINT & CLI
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Configures and parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Logistics Cost Analyzer - Comprehensive supply chain transportation analytics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python logistics_cost_analyzer.py                 # Full analysis pipeline
  python logistics_cost_analyzer.py --routes        # Run route-level breakdown
  python logistics_cost_analyzer.py --carriers      # Run carrier benchmarking
  python logistics_cost_analyzer.py --trends        # Run time-series trend analysis
  python logistics_cost_analyzer.py --model         # Train and evaluate regression model
  python logistics_cost_analyzer.py --charts        # Generate visualization PNGs
  python logistics_cost_analyzer.py --export        # Export summary & CSV reports
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Custom path to shipment input CSV file (default: searches in input/ directory)",
    )
    parser.add_argument("--routes", action="store_true", help="Display route cost analysis")
    parser.add_argument("--carriers", action="store_true", help="Display carrier performance evaluation")
    parser.add_argument("--trends", action="store_true", help="Display monthly trend analysis")
    parser.add_argument("--model", action="store_true", help="Display regression modeling metrics")
    parser.add_argument("--charts", action="store_true", help="Generate chart PNGs in reports/")
    parser.add_argument("--export", action="store_true", help="Export analytical reports to reports/")

    return parser.parse_args()


def main() -> None:
    """Coordinates and executes the data science analytics pipeline."""
    args = parse_arguments()

    # Determine execution mode: if no specific sub-flags given, run full pipeline
    specific_flags = [args.routes, args.carriers, args.trends, args.model, args.charts, args.export]
    run_all = not any(specific_flags)

    print_banner()

    # ------------------------------------------------------------------------
    # [1/8] Data Loading
    # ------------------------------------------------------------------------
    input_file_path = Path(args.input) if args.input else None
    print(f"\n[1/8] Loading input data...")
    raw_df = load_data(input_file_path)
    print(f"      ✓ {len(raw_df):,} raw shipments loaded")

    # ------------------------------------------------------------------------
    # [2/8] Data Validation
    # ------------------------------------------------------------------------
    print(f"\n[2/8] Validating data structure...")
    is_valid, missing_cols = validate_data(raw_df)
    if not is_valid:
        sys.exit(1)
    print(f"      ✓ Data validation complete (all required columns present)")

    # ------------------------------------------------------------------------
    # [3/8] Data Cleaning
    # ------------------------------------------------------------------------
    print(f"\n[3/8] Cleaning data...")
    cleaned_df, cleaning_stats = clean_data(raw_df)
    print(f"      ✓ Cleaned data: {cleaning_stats['rows_cleaned']:,} valid rows retained")
    if cleaning_stats["missing_handled"] > 0:
        print(f"      ✓ Handled {cleaning_stats['missing_handled']} missing values")
    if cleaning_stats["invalid_removed"] > 0:
        print(f"      ✓ Filtered {cleaning_stats['invalid_removed']} impossible/corrupt records")

    # ------------------------------------------------------------------------
    # [4/8] Feature Engineering
    # ------------------------------------------------------------------------
    print(f"\n[4/8] Feature engineering...")
    fe_df, engineered_features = engineer_features(cleaned_df)
    print(f"      ✓ {len(engineered_features)} features engineered:")
    for feat in ["total_cost", "cost_per_km", "cost_per_kg", "fuel_cost_ratio", "handling_cost_ratio", "month", "delivery_delay"]:
        print(f"        • {feat}")

    # Ensure output directory exists
    reports_dir = DEFAULT_REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------
    # [5/8] Logistics Core Analysis (Routes, Carriers, Trends)
    # ------------------------------------------------------------------------
    print(f"\n[5/8] Performing logistics analysis...")
    overall_metrics = calculate_overall_metrics(fe_df)
    route_summary, top10_routes = analyze_routes(fe_df, reports_dir)
    print(f"      ✓ Route analysis complete ({len(route_summary)} unique origin-destination pairs)")

    carrier_summary, carrier_info = analyze_carriers(fe_df, reports_dir)
    print(f"      ✓ Carrier benchmarking complete ({len(carrier_summary)} carriers evaluated)")

    monthly_summary, trend_info = analyze_trends(fe_df, reports_dir)
    print(f"      ✓ Trend analysis complete ({len(monthly_summary)} monthly periods)")

    # ------------------------------------------------------------------------
    # [6/8] Statistical & Predictive Analysis
    # ------------------------------------------------------------------------
    print(f"\n[6/8] Running statistical and predictive analysis...")
    cost_drivers, top_driver_desc = analyze_cost_drivers(fe_df, reports_dir)
    print(f"      ✓ Correlation analysis complete (Primary driver: {top_driver_desc})")

    regression_results = train_regression_model(fe_df, reports_dir)
    print(f"      ✓ Linear Regression trained (R² = {regression_results['r2']:.4f}, MAE = {format_currency(regression_results['mae'])})")

    # ------------------------------------------------------------------------
    # [7/8] Data Visualization
    # ------------------------------------------------------------------------
    if run_all or args.charts:
        print(f"\n[7/8] Generating publication-grade charts...")
        charts_created = generate_charts(fe_df, route_summary, carrier_summary, monthly_summary, reports_dir)
        print(f"      ✓ {len(charts_created)} charts generated in '{reports_dir.as_posix()}/'")
    else:
        print(f"\n[7/8] Chart generation skipped (use --charts to generate)")

    # ------------------------------------------------------------------------
    # [8/8] Business Insights & Export
    # ------------------------------------------------------------------------
    findings, recommendations = generate_business_insights(
        overall_metrics, route_summary, carrier_summary, trend_info, cost_drivers, regression_results
    )

    if run_all or args.export:
        print(f"\n[8/8] Generating business reports...")
        summary_file = export_reports(
            overall_metrics, cleaning_stats, route_summary, carrier_summary, monthly_summary,
            cost_drivers, regression_results, findings, recommendations, reports_dir
        )
        print(f"      ✓ Executive summary written to: {summary_file.as_posix()}")
        print(f"      ✓ CSV datasets exported:")
        print(f"        • {reports_dir / 'route_analysis.csv'}")
        print(f"        • {reports_dir / 'carrier_analysis.csv'}")
        print(f"        • {reports_dir / 'monthly_analysis.csv'}")
        print(f"        • {reports_dir / 'cost_driver_analysis.csv'}")
        print(f"        • {reports_dir / 'regression_results.txt'}")

        # Organize artifacts and package into timestamped ZIP
        try:
            pkg = organize_and_package_run(reports_dir=reports_dir, input_file=input_file_path)
            print(f"      ✓ Artifacts organized: {pkg['run_dir']}")
            print(f"      ✓ Packaged ZIP archive: {pkg['zip_path']} ({pkg['zip_size_kb']} KB)")
        except Exception as e:
            log_event(logger, "error", action="artifact_packaging_failure", message=f"Artifact packaging failed: {e}", error=str(e))
    else:
        print(f"\n[8/8] Report export step complete")

    log_event(
        logger,
        "info",
        action="pipeline_run_completed",
        message="Logistics cost analysis completed successfully",
        total_spend=overall_metrics["total_cost"],
        shipments_count=overall_metrics["total_shipments"],
        r2_score=regression_results["r2"],
    )

    # ------------------------------------------------------------------------
    # Terminal Display
    # ------------------------------------------------------------------------
    if run_all:
        display_dashboard(
            overall_metrics, route_summary, carrier_summary, monthly_summary,
            cost_drivers, regression_results, findings, recommendations
        )
    else:
        if args.routes:
            print_section("ROUTE COST BREAKDOWN")
            print(f"{'Route':<26} {'Shipments':>10} {'Total Cost':>15} {'Avg Cost':>12} {'Cost/km':>10}")
            print("-" * 76)
            for _, r in route_summary.head(10).iterrows():
                print(f"{r['route']:<26} {r['shipments']:>10,} {format_currency(r['total_cost']):>15} {format_currency(r['avg_cost']):>12} {format_currency(r['avg_cost_km'], 2):>10}")

        if args.carriers:
            print_section("CARRIER PERFORMANCE BENCHMARKING")
            print(f"{'Carrier':<14} {'Shipments':>10} {'Avg Cost':>12} {'On-Time':>10} {'Avg Days':>10} {'Score':>8}")
            print("-" * 68)
            for _, c in carrier_summary.iterrows():
                print(f"{c['carrier']:<14} {c['shipments']:>10,} {format_currency(c['avg_cost']):>12} {c['on_time_pct']:>9.1f}% {c['avg_delivery_days']:>9.1f} {c['score']:>8.1f}")

        if args.trends:
            print_section("MONTHLY LOGISTICS COST TREND")
            print(f"{'Month':<12} {'Shipments':>10} {'Total Cost':>15} {'Avg Cost':>12} {'MoM Change':>12}")
            print("-" * 65)
            for _, m in monthly_summary.iterrows():
                mom_str = f"{m['cost_mom_pct']:+.1f}%" if pd.notna(m['cost_mom_pct']) else "-"
                print(f"{m['month']:<12} {m['shipments']:>10,} {format_currency_short(m['total_cost']):>15} {format_currency(m['avg_cost']):>12} {mom_str:>12}")

        if args.model:
            print_section("REGRESSION MODEL METRICS")
            print(regression_results["report_text"])

    print("=" * 60)
    print("                     ANALYSIS COMPLETE                     ")
    print("=" * 60)
    print(f"Reports directory:   {reports_dir.resolve().as_posix()}")
    print(f"Executive summary:   {(reports_dir / 'summary.txt').as_posix()}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
