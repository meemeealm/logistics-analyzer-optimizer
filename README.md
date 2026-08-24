# Logistics Cost Analyzer

A high-performance, professional Python command-line data science toolkit engineered for supply chain and transportation logistics cost optimization, carrier performance evaluation, route cost tracking, cost driver analysis, and predictive cost estimation.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [What This Tool Is / What It Is Not](#what-this-tool-is--what-it-is-not)
3. [Target Audience](#target-audience)
4. [Business Applications](#business-applications)
5. [Project Structure](#project-structure)
6. [Installation & Requirements](#installation--requirements)
7. [Quickstart Workflow](#quickstart-workflow)
8. [Command-Line Arguments & Flags](#command-line-arguments--flags)
9. [Data Cleaning Pipeline](#data-cleaning-pipeline)
10. [Feature Engineering Rationale](#feature-engineering-rationale)
11. [Analytical Methodology](#analytical-methodology)
    - [Carrier Scoring System](#carrier-scoring-system)
    - [Cost Driver Correlation](#cost-driver-correlation)
    - [Linear Regression Modeling](#linear-regression-modeling)
12. [Generated Reports & Visualizations](#generated-reports--visualizations)
13. [Limitations & Assumptions](#limitations--assumptions)

---

## Project Overview

Transportation and logistics costs frequently represent 40% to 60% of total operational expenditure in modern supply chains. Due to decentralized freight data, seasonal fuel fluctuations, cargo weight variances, and carrier performance disparities, logistics managers struggle to isolate inefficiencies and make data-driven contracting decisions.

**Logistics Cost Analyzer** solves this by offering an automated, reproducible end-to-end data science pipeline. By placing your shipment ledger into `input/` and running a single command, the system validates the dataset, executes robust data cleaning, computes derived unit metrics, analyzes route and carrier costs, identifies primary cost drivers, trains an interpretable predictive regression model, creates publication-quality charts, and generates executive business recommendations.

---

## What This Tool Is / What It Is Not

| What This Tool Is | What This Tool Is NOT |
| :--- | :--- |
| **A robust local CLI analytics engine** written in Python (pandas, numpy, scikit-learn, matplotlib, seaborn). | **Not a bloated web server or cloud database system**. Requires no API keys, cloud tokens, or active internet. |
| **An automated reporting and visualization pipeline** producing clean CSV exports, markdown summaries, and high-resolution PNG charts. | **Not an anomaly detection system**. It does not perform Isolation Forest, Z-score, or IQR outlier filtering. |
| **A rigorous data cleaner & feature engineering tool** designed for shipment log data. | **Not an ERP or TMS replacement**. It consumes CSV shipment records exported from existing TMS/WMS software. |
| **An interpretable statistical & regression modeling tool** evaluating cost drivers and price predictions. | **Not a black-box deep neural network**. All statistical models and scoring formulas are transparent and explainable. |

---

## Target Audience

- **Logistics & Supply Chain Managers**: To benchmark freight spending across shipping lanes and negotiate carrier contracts.
- **Operations & Procurement Specialists**: To evaluate carrier reliability vs. cost trade-offs and consolidate low-efficiency shipments.
- **Financial & Data Analysts**: To analyze month-over-month freight cost trends and provide data-backed budget forecasts to leadership.

---

## Business Applications

1. **Freight Contract Renegotiation**: Identify the highest-spending lanes (e.g., Manila → Davao) and renegotiate baseline rates based on verified historical volume.
2. **Carrier Allocation Optimization**: Strategically assign time-critical cargo to high-reliability carriers while dispatching non-urgent bulk cargo to low-cost carriers.
3. **Budget Variance Analysis**: Pinpoint the root drivers of seasonal cost spikes (e.g., fuel price shocks in April vs. shipment volume surges).
4. **Predictive Cost Budgeting**: Estimate transportation budgets for prospective shipping routes and volume forecasts using the regression model.

---

## Project Structure

```text
logistics-cost-analyzer/
│
├── logistics_cost_analyzer.py    # Main CLI analytics pipeline engine
├── input_watcher.py              # Automated folder watcher with debouncing daemon
├── artifacts_handler.py          # Run-specific packaging & ZIP manager
├── structured_logger.py          # Structured JSON logging & observability
├── generate_sample_data.py       # Realistic synthetic shipment data generator
├── pyproject.toml                # uv & modern packaging configuration
├── requirements.txt              # Standard pip dependencies
├── HOWTO.md                      # Complete Web Dashboard & Automation user guide
├── README.md                     # Comprehensive technical documentation
│
├── input/
│   └── shipments.csv             # Input shipment dataset (monitored by watcher)
│
├── logs/
│   └── pipeline_operations.json.log # Structured JSON event logs
│
└── reports/                      # Automated analytical outputs
    ├── summary.txt               # Executive summary with KPIs and recommendations
    ├── route_analysis.csv        # Origin-Destination corridor metrics
    ├── carrier_analysis.csv      # Carrier performance scores and costs
    ├── monthly_analysis.csv      # Month-over-month trend data
    ├── cost_driver_analysis.csv  # Pearson correlation coefficients
    ├── regression_results.txt    # OLS model metrics (R², MAE, RMSE, coefficients)
    │
    ├── monthly_cost_trend.png    # Monthly spending and shipment volume chart
    ├── top_routes.png            # Horizontal bar chart of top 10 expensive routes
    ├── carrier_cost_comparison.png # Average shipment cost comparison by carrier
    ├── cost_vs_distance.png      # Scatter plot & trendline for distance vs. cost
    ├── cost_vs_weight.png        # Scatter plot & trendline for cargo weight vs. cost
    ├── cost_distribution.png     # Total cost histogram and kernel density estimate
    ├── on_time_delivery_by_carrier.png # Carrier on-time rate vs. performance score
    │
    ├── runs/                     # Run-specific output snapshots
    │   └── run_YYYYMMDD_HHMMSS/  # Isolated run artifacts & run_manifest.json
    │
    └── archives/                 # Compressed ZIP archives
        └── logistics_reports_run_YYYYMMDD_HHMMSS.zip
```

---

## Installation & Environment Setup

You can manage your environment using **`uv`** (ultra-fast, modern Python package runner) or standard **`venv` + `pip`**.

### Option A: Using `uv` (Recommended)

1. **Install `uv`** (if not already installed):
   - **Windows (PowerShell)**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS / Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Or via pip: `pip install uv`

2. **Run instantly without manual activation**:
   ```cmd
   # Sync dependencies into an isolated virtual environment automatically:
   uv sync

   # Run the generator and analyzer directly:
   uv run python generate_sample_data.py
   uv run python logistics_cost_analyzer.py
   ```

### Option B: Using Standard Python `venv` & `pip`

1. **Create and activate a virtual environment**:
   - **Windows CMD**:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```
   - **Windows PowerShell**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

### Dependencies
- `pandas >= 2.0.0`: High-performance DataFrame operations and time-series aggregation.
- `numpy >= 1.24.0`: Mathematical computations and vectorized array calculations.
- `matplotlib >= 3.7.0`: Core plotting library for publication-quality visual reports.
- `seaborn >= 0.12.0`: Statistical data visualization and formatting aesthetics.
- `scikit-learn >= 1.2.0`: Linear regression modeling, train-test splitting, and evaluation metrics.

---

## Quickstart Workflow

Run the entire pipeline in 2 simple commands directly from **Windows CMD**, PowerShell, or Linux bash:

### Step 1: Generate the Sample Dataset
```cmd
python generate_sample_data.py
```
*Creates `input/shipments.csv` containing 1,250 realistic shipment records spanning Philippine logistics hubs with seasonal freight characteristics.*

### Step 2: Run the Cost Analyzer
```cmd
python logistics_cost_analyzer.py
```
*Automatically locates the dataset, cleans data, computes features, generates terminal dashboards, and saves all outputs to `reports/`.*

---

## Command-Line Arguments & Flags

The default command (`python logistics_cost_analyzer.py`) runs the complete end-to-end data pipeline. You can also run targeted analytical modules using command-line flags:

```cmd
# Run only Route Analysis
python logistics_cost_analyzer.py --routes

# Run only Carrier Benchmarking
python logistics_cost_analyzer.py --carriers

# Run only Monthly Trend Analysis
python logistics_cost_analyzer.py --trends

# Train and display Regression Modeling metrics
python logistics_cost_analyzer.py --model

# Regenerate all visual charts in reports/
python logistics_cost_analyzer.py --charts

# Export all CSV datasets and summary reports to reports/
python logistics_cost_analyzer.py --export

# Specify a custom input CSV file path
python logistics_cost_analyzer.py --input "data/my_custom_shipments.csv"
```

---

## Data Cleaning Pipeline

The data cleaning stage implements defensive validation to guarantee that corrupted data never contaminates downstream modeling:

1. **Categorical Normalization**: Strips leading and trailing whitespace from string columns (`origin`, `destination`, `carrier`, `shipment_id`).
2. **Type Coercion**: Coerces numeric columns (`distance_km`, `weight_kg`, `shipping_cost`, `fuel_cost`, `handling_cost`, `delivery_days`, `on_time`) to numeric formats, converting invalid text tokens to `NaN`.
3. **Date Parsing**: Converts date strings to timezone-agnostic `datetime` objects.
4. **Missing Value Imputation**: Missing secondary cost items (`fuel_cost`, `handling_cost`) are imputed using the cohort median to preserve valid shipment observations.
5. **Physical Sanity Filtering**: Removes logically impossible records (e.g., negative distance, zero cargo weight, negative shipping costs, or missing origin/destination).
6. **Audit Reporting**: Outputs an explicit cleaning audit in the terminal tracking the exact number of rows loaded, valid rows retained, missing values imputed, and invalid records filtered.

---

## Feature Engineering Rationale

The system creates domain-specific derived features:

| Feature Name | Calculation | Business Rationale |
| :--- | :--- | :--- |
| `total_cost` | `shipping_cost + fuel_cost + handling_cost` | Captures true landed transportation expenditure per shipment. |
| `cost_per_km` | `total_cost / distance_km` | Evaluates route unit efficiency across varying lane distances. |
| `cost_per_kg` | `total_cost / weight_kg` | Measures freight density and cargo cost effectiveness. |
| `fuel_cost_ratio` | `fuel_cost / total_cost` | Tracks sensitivity to fuel surcharge volatility. |
| `handling_cost_ratio` | `handling_cost / total_cost` | Identifies cargo handling and terminal surcharge overhead. |
| `month` | `date.strftime('%Y-%m')` | Enables discrete monthly time-series aggregation and MoM tracking. |
| `route` | `origin + " → " + destination` | Groups directional shipping lanes for corridor benchmarking. |
| `delivery_delay` | `1 if on_time == 0 else 0` | Binary indicator for transit service reliability evaluation. |

---

## Analytical Methodology

### Carrier Scoring System
Rather than ranking carriers solely by lowest rate, the system computes a composite **Carrier Performance Score (0 - 100)**:
- **On-Time Reliability (40% weight)**: Normalized based on carrier on-time delivery percentage (`on_time_pct * 0.40`).
- **Transit Speed Efficiency (30% weight)**: Normalized ratio of fleet average delivery duration against carrier delivery speed.
- **Cost Competitiveness (30% weight)**: Normalized ratio of fleet average cost/km against carrier cost/km.

### Cost Driver Correlation
Computes Pearson correlation coefficients ($r$) of all numeric features with `total_cost`. 

> **Important Data Science Principle**: *Correlation indicates numerical association, not direct causation.* The program surfaces variables with strong statistical relationships without making unwarranted causal claims.

### Linear Regression Modeling
Implements an Ordinary Least Squares (OLS) Linear Regression model using scikit-learn:
$$\text{total\_cost} = \beta_0 + \beta_1(\text{distance}) + \beta_2(\text{weight}) + \beta_3(\text{fuel}) + \beta_4(\text{handling}) + \beta_5(\text{delivery\_days})$$
- **Train/Test Split**: 80% training data, 20% holdout test data (`random_state=42`).
- **Metrics Computed**:
  - $R^2$ (Coefficient of Determination): Measures proportion of cost variance explained.
  - $\text{MAE}$ (Mean Absolute Error): Average monetary prediction error on unseen shipments.
  - $\text{RMSE}$ (Root Mean Squared Error): Penalizes larger forecasting errors.

---

## Generated Reports & Visualizations

All outputs are saved to `reports/`:

1. **`summary.txt`**: Consolidated executive overview, KPI table, top spenders, carrier scorecards, key findings, and strategic recommendations.
2. **`route_analysis.csv`**: Full route-level breakdown (count, spend, average cost, average distance, cost/km, cost/kg, on-time %).
3. **`carrier_analysis.csv`**: Carrier performance ranking with composite scores.
4. **`monthly_analysis.csv`**: Time-series table with Month-over-Month (MoM) % changes.
5. **`cost_driver_analysis.csv`**: Pearson correlation matrix with `total_cost`.
6. **`regression_results.txt`**: Detailed statistical report with model formula, intercept, and feature coefficients.
7. **Visual Charts (PNG, 300 DPI)**:
   - `monthly_cost_trend.png`
   - `top_routes.png`
   - `carrier_cost_comparison.png`
   - `cost_vs_distance.png`
   - `cost_vs_weight.png`
   - `cost_distribution.png`
   - `on_time_delivery_by_carrier.png`

---

## Limitations & Assumptions

1. **Synthetic Data**: The sample dataset provided by `generate_sample_data.py` is simulated for demonstration and benchmarking purposes.
2. **Correlation vs. Causation**: Strong correlation between distance/weight and cost reflects freight rate structures rather than proof of external causation.
3. **Linearity Assumptions**: The linear regression model assumes linear relationships between input variables and costs. Nonlinearities (e.g. step-function freight tiers or LTL pricing breaks) may require polynomial or segmented models in production.
4. **Unit Metric Nuances**: `cost_per_km` and `cost_per_kg` can fluctuate significantly between light, bulky air cargo and heavy sea freight. Cargo category should be accounted for when interpreting unit costs.
5. **Historical Projection**: Historical monthly trends and fuel price indices do not guarantee future freight price trajectories.
