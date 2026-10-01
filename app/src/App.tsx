import React, { useState, useEffect } from "react";
import {
  Truck,
  TrendingUp,
  BarChart3,
  DollarSign,
  Clock,
  FileText,
  Play,
  Terminal,
  RefreshCw,
  Award,
  Compass,
  FileSpreadsheet,
  BookOpen,
  Copy,
  Check,
  ChevronRight,
  Sparkles,
  Download,
  Archive,
  Eye,
  Activity,
  Zap,
  FolderSync,
  Radio,
  FileJson,
  CheckCircle2,
  AlertCircle,
  Package,
} from "lucide-react";

interface StatusResponse {
  hasInput: boolean;
  hasReports: boolean;
  summaryText: string;
  regressionText: string;
  charts: string[];
  csvFiles: string[];
  inputFiles: string[];
  isWatcherRunning: boolean;
}

interface CsvData {
  headers: string[];
  rows: Record<string, string>[];
}

interface RunInfo {
  run_id: string;
  created_at: string;
  artifacts_count: number;
  artifacts: string[];
  zip_exists: boolean;
  zip_filename: string;
  zip_size_kb: number;
}

interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  action?: string;
  message: string;
  [key: string]: any;
}

export default function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "charts" | "tables" | "runs" | "logs" | "watcher" | "terminal" | "docs"
  >("dashboard");
  const [selectedCsv, setSelectedCsv] = useState<string>("route_analysis.csv");
  const [csvData, setCsvData] = useState<CsvData | null>(null);
  const [activeFile, setActiveFile] = useState<string>("HOWTO.md");
  const [fileContent, setFileContent] = useState<string>("");
  const [terminalOutput, setTerminalOutput] = useState<string>("");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  // Observability & Artifacts states
  const [runsList, setRunsList] = useState<RunInfo[]>([]);
  const [logsList, setLogsList] = useState<LogEntry[]>([]);
  const [logFilter, setLogFilter] = useState<string>("ALL");
  const [autoRefreshLogs, setAutoRefreshLogs] = useState<boolean>(true);

  // Fetch initial status
  const fetchStatus = async () => {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch status", e);
    }
  };

  // Fetch runs and archives
  const fetchRuns = async () => {
    try {
      const res = await fetch("/api/runs");
      if (res.ok) {
        const data = await res.json();
        setRunsList(data.runs || []);
      }
    } catch (e) {
      console.error("Failed to fetch runs", e);
    }
  };

  // Fetch structured JSON logs
  const fetchLogs = async () => {
    try {
      const res = await fetch("/api/logs");
      if (res.ok) {
        const data = await res.json();
        setLogsList(data.logs || []);
      }
    } catch (e) {
      console.error("Failed to fetch logs", e);
    }
  };

  // Fetch CSV data
  const fetchCsv = async (filename: string) => {
    try {
      const res = await fetch(`/api/reports/csv/${filename}`);
      if (res.ok) {
        const data = await res.json();
        setCsvData(data);
      }
    } catch (e) {
      console.error("Failed to fetch CSV", e);
    }
  };

  // Fetch source file content
  const fetchFile = async (filename: string) => {
    try {
      const res = await fetch(`/api/files/${filename}`);
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content);
      }
    } catch (e) {
      console.error("Failed to fetch file", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchRuns();
    fetchLogs();
  }, []);

  useEffect(() => {
    if (activeTab === "tables" && selectedCsv) {
      fetchCsv(selectedCsv);
    }
    if (activeTab === "runs") {
      fetchRuns();
    }
    if (activeTab === "logs") {
      fetchLogs();
    }
  }, [activeTab, selectedCsv]);

  useEffect(() => {
    if (activeTab === "docs" && activeFile) {
      fetchFile(activeFile);
    }
  }, [activeTab, activeFile]);

  // Periodic log refresh
  useEffect(() => {
    if (!autoRefreshLogs) return;
    const timer = setInterval(() => {
      if (activeTab === "logs" || activeTab === "dashboard") {
        fetchLogs();
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [autoRefreshLogs, activeTab]);

  // Run script
  const handleRunScript = async (script: string, flags: string = "") => {
    setIsRunning(true);
    setTerminalOutput(`\n> Executing: python ${script}.py ${flags} ...\n`);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script, flags }),
      });
      const data = await res.json();
      setTerminalOutput(
        (prev) =>
          prev +
          (data.stdout || "") +
          (data.stderr ? `\n[STDERR]:\n${data.stderr}` : "") +
          `\n\nProcess exited with status code: ${data.exitCode}\n`
      );
      await fetchStatus();
      await fetchRuns();
      await fetchLogs();
      if (selectedCsv) fetchCsv(selectedCsv);
    } catch (err: any) {
      setTerminalOutput((prev) => prev + `\nExecution error: ${err.message}\n`);
    } finally {
      setIsRunning(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(id);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  const chartMeta: Record<string, { title: string; desc: string }> = {
    "monthly_cost_trend.png": {
      title: "Monthly Cost Trend & Volume",
      desc: "Tracks total logistics expenditure and shipment counts over time.",
    },
    "top_routes.png": {
      title: "Top 10 Routes by Spending",
      desc: "Ranks highest transportation cost corridors across Philippine logistics hubs.",
    },
    "carrier_cost_comparison.png": {
      title: "Average Cost per Carrier",
      desc: "Benchmarks average landed freight spend across all evaluated carriers.",
    },
    "cost_vs_distance.png": {
      title: "Cost vs. Distance (km)",
      desc: "Linear regression fit and scatter of route distance against shipment cost.",
    },
    "cost_vs_weight.png": {
      title: "Cost vs. Cargo Weight (kg)",
      desc: "Linear regression fit and scatter of payload mass against shipment cost.",
    },
    "cost_distribution.png": {
      title: "Cost Distribution & Density",
      desc: "Histogram of shipment cost frequency with mean and median markers.",
    },
    "on_time_delivery_by_carrier.png": {
      title: "Carrier Reliability & Score",
      desc: "On-time delivery percentages and composite performance scores (0-100).",
    },
  };

  const filteredLogs = logsList.filter((l) => {
    if (logFilter === "ALL") return true;
    return l.level?.toUpperCase() === logFilter;
  });

  return (
    <div className="min-h-screen bg-[#F7F9F6] text-[#1E2922] flex flex-col font-sans selection:bg-emerald-600 selection:text-white">
      {/* Top Header */}
      <header id="main-header" className="border-b border-[#E2EBE4] bg-white/95 backdrop-blur sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="h-10 w-10 rounded-xl bg-emerald-700 flex items-center justify-center shadow-md shadow-emerald-900/15 text-white font-bold">
              <Truck className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-bold tracking-tight text-[#0F1F15]">Logistics Cost Analyzer</h1>
                <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300/80 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Activity className="h-3 w-3 text-emerald-700" /> Automated Pipeline
                </span>
              </div>
              <p className="text-xs text-[#52665B]">Automated Ingestion • Debounced Watcher • Run Packaging & Observability</p>
            </div>
          </div>

          {/* Header Quick Action Buttons */}
          <div className="flex items-center gap-2.5">
            <button
              id="btn-package-artifacts"
              onClick={() => {
                setActiveTab("terminal");
                handleRunScript("artifacts_handler");
              }}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#EBF2EC] hover:bg-[#DEE9E0] text-xs font-semibold text-[#183623] border border-[#CAD8CD] transition disabled:opacity-50 cursor-pointer"
              title="Organizes current artifacts into reports/runs/ and packages a timestamped ZIP"
            >
              <Package className="h-3.5 w-3.5 text-emerald-700" />
              Package ZIP
            </button>
            <button
              id="btn-run-generator"
              onClick={() => {
                setActiveTab("terminal");
                handleRunScript("generate_sample_data");
              }}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[#EBF2EC] hover:bg-[#DEE9E0] text-xs font-semibold text-[#183623] border border-[#CAD8CD] transition disabled:opacity-50 cursor-pointer"
              title="Runs python generate_sample_data.py to create 1,250 realistic shipments"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-emerald-700 ${isRunning ? "animate-spin" : ""}`} />
              Generate CSV
            </button>
            <button
              id="btn-run-analyzer"
              onClick={() => {
                setActiveTab("terminal");
                handleRunScript("logistics_cost_analyzer");
              }}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 cursor-pointer"
              title="Runs full 8-step Python analytics engine and updates reports/"
            >
              <Play className="h-3.5 w-3.5 fill-current text-white" />
              Run Full Analyzer
            </button>
          </div>
        </div>

        {/* Modern Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 border-t border-[#E8EFEA] overflow-x-auto">
          {[
            { id: "dashboard", label: "Executive Dashboard", icon: BarChart3 },
            { id: "charts", label: "Generated Charts (7)", icon: TrendingUp },
            { id: "tables", label: "Data Tables & CSVs", icon: FileSpreadsheet },
            { id: "runs", label: "Packaged Runs & ZIPs", icon: Archive, badge: runsList.length },
            { id: "logs", label: "Observability", icon: FileJson, badge: logsList.length },
            { id: "watcher", label: "Debounced Files", icon: Radio },
            { id: "terminal", label: "Terminal & CLI Output", icon: Terminal },
            { id: "docs", label: "User Guide & Code", icon: BookOpen },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 transition whitespace-nowrap cursor-pointer ${
                  isActive
                    ? "border-emerald-700 text-emerald-800 bg-emerald-50/70"
                    : "border-transparent text-[#5B6E62] hover:text-[#183623] hover:border-[#CAD8CD]"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-emerald-700" : "text-[#778B7F]"}`} />
                {tab.label}
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 font-mono">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* DASHBOARD TAB */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            {/* Automation & Artifact Banner */}
            <div className="bg-white border border-[#E0E9E2] rounded-xl p-4 shadow-[0_1px_3px_rgba(0,0,0,0.04)] flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
                  <FolderSync className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#0F2217]">Automated Data Ingestion & Artifact Packager</h3>
                  <p className="text-[11px] text-[#52665B]">
                    New CSVs in <code className="font-mono text-emerald-800">input/</code> trigger debounced executions and generate timestamped ZIP archives in <code className="font-mono text-emerald-800">reports/archives/</code>.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab("runs")}
                  className="px-3 py-1.5 rounded-lg bg-[#EBF2EC] hover:bg-[#DEE9E0] text-xs font-semibold text-[#183623] border border-[#CAD8CD] inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <Archive className="h-3.5 w-3.5 text-emerald-700" />
                  View {runsList.length} Archived Runs
                </button>
                <button
                  onClick={() => setActiveTab("logs")}
                  className="px-3 py-1.5 rounded-lg bg-[#EBF2EC] hover:bg-[#DEE9E0] text-xs font-semibold text-[#183623] border border-[#CAD8CD] inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <FileJson className="h-3.5 w-3.5 text-emerald-700" />
                  Live JSON Logs
                </button>
              </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-[#E0E9E2] rounded-xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center justify-between text-[#5C7063] mb-2">
                  <span className="text-xs font-semibold">Total Logistics Spend</span>
                  <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700 border border-emerald-200">
                    <DollarSign className="h-4 w-4" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-[#0F2217] tracking-tight">₱22,291,225</div>
                <div className="text-xs text-[#5C7063] mt-1.5 flex items-center gap-1">
                  <span className="text-emerald-800 font-bold">1,246</span> shipments analyzed
                </div>
              </div>

              <div className="bg-white border border-[#E0E9E2] rounded-xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center justify-between text-[#5C7063] mb-2">
                  <span className="text-xs font-semibold">Avg. Cost / Shipment</span>
                  <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700 border border-emerald-200">
                    <Truck className="h-4 w-4" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-[#0F2217] tracking-tight">₱17,890</div>
                <div className="text-xs text-[#5C7063] mt-1.5 flex items-center gap-1">
                  Median: <span className="text-[#1A3324] font-semibold">₱16,396</span>
                </div>
              </div>

              <div className="bg-white border border-[#E0E9E2] rounded-xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center justify-between text-[#5C7063] mb-2">
                  <span className="text-xs font-semibold">On-Time Delivery Rate</span>
                  <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700 border border-emerald-200">
                    <Clock className="h-4 w-4" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-emerald-800 tracking-tight">90.4%</div>
                <div className="text-xs text-[#5C7063] mt-1.5 flex items-center gap-1">
                  Avg transit: <span className="text-[#1A3324] font-semibold">3.4 days</span>
                </div>
              </div>

              <div className="bg-white border border-[#E0E9E2] rounded-xl p-4.5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center justify-between text-[#5C7063] mb-2">
                  <span className="text-xs font-semibold">ML Model Accuracy (R²)</span>
                  <div className="h-7 w-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700 border border-emerald-200">
                    <Sparkles className="h-4 w-4" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-emerald-800 tracking-tight">98.5%</div>
                <div className="text-xs text-[#5C7063] mt-1.5 flex items-center gap-1">
                  MAE error: <span className="text-[#1A3324] font-semibold">±₱806</span>
                </div>
              </div>
            </div>

            {/* Strategic Insights & Findings */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Key Findings */}
              <div className="bg-white border border-[#E0E9E2] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center gap-2 mb-4 border-b border-[#EEF4EF] pb-3">
                  <Award className="h-4 w-4 text-emerald-700" />
                  <h2 className="text-xs font-bold text-[#0F2217] uppercase tracking-wider">Key Analytical Findings</h2>
                </div>
                <ul className="space-y-3 text-xs text-[#35483C]">
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-[#F5F8F5] border border-[#E2EAE3]">
                    <span className="flex-shrink-0 h-5 w-5 rounded-full bg-emerald-700 text-white font-bold flex items-center justify-center text-[11px]">
                      1
                    </span>
                    <span>
                      <strong className="text-[#0F2217]">Manila → Davao</strong> represents the largest share of transportation spending (₱1.91M across 74 shipments, or 8.6% of total spend).
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-[#F5F8F5] border border-[#E2EAE3]">
                    <span className="flex-shrink-0 h-5 w-5 rounded-full bg-emerald-700 text-white font-bold flex items-center justify-center text-[11px]">
                      2
                    </span>
                    <span>
                      Logistics costs surged by <strong className="text-[#0F2217]">+7.4% MoM</strong> during the April → May period due to freight volume recovery and fuel index adjustments.
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-[#F5F8F5] border border-[#E2EAE3]">
                    <span className="flex-shrink-0 h-5 w-5 rounded-full bg-emerald-700 text-white font-bold flex items-center justify-center text-[11px]">
                      3
                    </span>
                    <span>
                      <strong className="text-[#0F2217]">Carrier B</strong> provides the lowest average unit price (₱16,387), but exhibits lower on-time reliability (82.5%) compared to <strong className="text-[#0F2217]">Carrier C</strong> (96.3% on-time at ₱19,293).
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-[#F5F8F5] border border-[#E2EAE3]">
                    <span className="flex-shrink-0 h-5 w-5 rounded-full bg-emerald-700 text-white font-bold flex items-center justify-center text-[11px]">
                      4
                    </span>
                    <span>
                      <strong className="text-[#0F2217]">Cargo Weight & Handling</strong> exhibit the strongest correlation with total cost (r = +0.78), followed by route distance (r = +0.61).
                    </span>
                  </li>
                </ul>
              </div>

              {/* Strategic Recommendations */}
              <div className="bg-white border border-[#E0E9E2] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
                <div className="flex items-center gap-2 mb-4 border-b border-[#EEF4EF] pb-3">
                  <Compass className="h-4 w-4 text-emerald-700" />
                  <h2 className="text-xs font-bold text-[#0F2217] uppercase tracking-wider">Strategic Recommendations</h2>
                </div>
                <ul className="space-y-3 text-xs text-[#35483C]">
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
                    <ChevronRight className="h-4 w-4 text-emerald-700 flex-shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-emerald-950 font-bold">Target High-Spend Corridors:</strong> Prioritize volume rate renegotiation and shipment consolidation on Manila → Davao and Manila → Cagayan de Oro routes.
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
                    <ChevronRight className="h-4 w-4 text-emerald-700 flex-shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-emerald-950 font-bold">Implement Tiered Carrier Dispatch:</strong> Route SLA-critical priority cargo to Carrier C (96.3% on-time) while assigning non-urgent bulk cargo to Carrier B for maximum cost savings.
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
                    <ChevronRight className="h-4 w-4 text-emerald-700 flex-shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-emerald-950 font-bold">Fuel Surcharge Hedging:</strong> Monitor seasonal fuel trends to negotiate index caps prior to peak Q2 surcharge escalations.
                    </span>
                  </li>
                  <li className="flex items-start gap-2.5 p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
                    <ChevronRight className="h-4 w-4 text-emerald-700 flex-shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-emerald-950 font-bold">Utilize Regression Predictor:</strong> Use the validated OLS model (MAE ±₱806) for budgeting new shipping lane expansions.
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* PACKAGED RUNS & ARCHIVES TAB */}
        {activeTab === "runs" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E0E9E2] p-4 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div>
                <h2 className="text-sm font-bold text-[#0F2217]">Run-Specific Artifacts & Packaged ZIP Archives</h2>
                <p className="text-xs text-[#52665B]">
                  Each execution organizes output reports, CSV datasets, and charts into <code className="font-mono text-emerald-800">reports/runs/&lt;run_id&gt;/</code> and builds a timestamped ZIP in <code className="font-mono text-emerald-800">reports/archives/</code>.
                </p>
              </div>
              <button
                onClick={() => handleRunScript("artifacts_handler")}
                disabled={isRunning}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 cursor-pointer"
              >
                <Package className={`h-3.5 w-3.5 ${isRunning ? "animate-spin" : ""}`} />
                Package Current Run
              </button>
            </div>

            {/* Runs Table */}
            <div className="bg-white border border-[#E0E9E2] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="p-3.5 border-b border-[#E8EFEA] bg-[#FAFBF9] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Archive className="h-4 w-4 text-emerald-700" />
                  <h3 className="text-xs font-bold text-[#0F2217] uppercase tracking-wider">Archived Runs History</h3>
                  <span className="text-[11px] text-[#5C7063]">({runsList.length} total runs)</span>
                </div>
                <button
                  onClick={fetchRuns}
                  className="text-xs text-emerald-800 hover:text-emerald-950 font-semibold bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 inline-flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className="h-3 w-3" /> Refresh
                </button>
              </div>

              <div className="overflow-x-auto">
                {runsList.length > 0 ? (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F4F7F4] border-b border-[#E0E8E1] text-[#142A1D] font-bold">
                      <tr>
                        <th className="px-4 py-3 whitespace-nowrap">Run ID</th>
                        <th className="px-4 py-3 whitespace-nowrap">Timestamp</th>
                        <th className="px-4 py-3 whitespace-nowrap">Artifacts Count</th>
                        <th className="px-4 py-3 whitespace-nowrap">ZIP Package</th>
                        <th className="px-4 py-3 whitespace-nowrap">Package Size</th>
                        <th className="px-4 py-3 text-right whitespace-nowrap">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EDF3EE] font-mono text-[11px]">
                      {runsList.map((r) => (
                        <tr key={r.run_id} className="hover:bg-[#F7FAF7] transition">
                          <td className="px-4 py-3 font-semibold text-emerald-900 whitespace-nowrap">
                            {r.run_id}
                          </td>
                          <td className="px-4 py-3 text-[#35483C] whitespace-nowrap">
                            {r.created_at || "N/A"}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5 rounded text-[10px]">
                              {r.artifacts_count} files
                            </span>
                          </td>
                          <td className="px-4 py-3 text-[#35483C] whitespace-nowrap">
                            {r.zip_filename || "Not created"}
                          </td>
                          <td className="px-4 py-3 text-[#35483C] whitespace-nowrap">
                            {r.zip_size_kb ? `${r.zip_size_kb} KB` : "-"}
                          </td>
                          <td className="px-4 py-3 text-right whitespace-nowrap">
                            {r.zip_exists ? (
                              <a
                                href={`/api/archives/download/${r.zip_filename}`}
                                download={r.zip_filename}
                                className="inline-flex items-center gap-1 text-xs text-emerald-800 hover:text-emerald-950 font-semibold bg-emerald-100/70 hover:bg-emerald-200 px-2.5 py-1 rounded border border-emerald-300 transition"
                              >
                                <Download className="h-3 w-3" /> Download ZIP
                              </a>
                            ) : (
                              <span className="text-[10px] text-gray-400">Unavailable</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="p-8 text-center text-xs text-[#73887B]">
                    No packaged runs found yet. Click <strong>"Package Current Run"</strong> or run the analyzer pipeline.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STRUCTURED JSON LOGS TAB */}
        {activeTab === "logs" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E0E9E2] p-4 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div>
                <h2 className="text-sm font-bold text-[#0F2217]">Observability & Structured JSON Logs</h2>
                <p className="text-xs text-[#52665B]">
                  Real-time structured events recorded in <code className="font-mono text-emerald-800">logs/pipeline_operations.json.log</code>
                </p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center bg-[#EEF4EF] p-1 rounded-lg border border-[#CAD8CD]">
                  {["ALL", "INFO", "WARNING", "ERROR"].map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => setLogFilter(lvl)}
                      className={`px-2.5 py-1 text-xs font-semibold rounded cursor-pointer transition ${
                        logFilter === lvl
                          ? "bg-emerald-700 text-white shadow-xs"
                          : "text-[#294232] hover:text-[#183623]"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
                <button
                  onClick={fetchLogs}
                  className="px-3 py-1.5 rounded-lg bg-[#EBF2EC] hover:bg-[#DEE9E0] text-xs font-semibold text-[#183623] border border-[#CAD8CD] inline-flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="h-3.5 w-3.5 text-emerald-700" />
                  Refresh Logs
                </button>
              </div>
            </div>

            {/* Logs Viewer */}
            <div className="bg-[#0B1510] border border-[#1C3224] rounded-xl overflow-hidden shadow-xl">
              <div className="px-4 py-2.5 bg-[#0F2018] border-b border-[#1C3224] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileJson className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-mono text-emerald-300">
                    Live Event Stream ({filteredLogs.length} events loaded)
                  </span>
                </div>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(logsList, null, 2), "jsonlogs")}
                  className="text-xs text-emerald-300 hover:text-white inline-flex items-center gap-1 font-mono cursor-pointer"
                >
                  {copiedCmd === "jsonlogs" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  Copy JSON
                </button>
              </div>
              <div className="p-4 overflow-x-auto max-h-[600px] divide-y divide-[#162B1D] font-mono text-[11px] leading-relaxed">
                {filteredLogs.length > 0 ? (
                  filteredLogs.map((log, idx) => (
                    <div key={idx} className="py-2 hover:bg-[#0E1E14] px-2 rounded transition">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-gray-400 text-[10px]">{log.timestamp}</span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                            log.level === "ERROR"
                              ? "bg-rose-950 text-rose-400 border border-rose-800"
                              : log.level === "WARNING"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          }`}
                        >
                          {log.level}
                        </span>
                        {log.action && (
                          <span className="text-cyan-300 text-[10px] font-semibold">[{log.action}]</span>
                        )}
                      </div>
                      <div className="text-emerald-300 font-semibold">{log.message}</div>
                      {/* Render extra JSON attributes if any */}
                      {Object.keys(log).filter(
                        (k) =>
                          ![
                            "timestamp",
                            "level",
                            "message",
                            "action",
                            "service",
                            "logger",
                            "module",
                            "funcName",
                            "lineNo",
                            "processId",
                          ].includes(k)
                      ).length > 0 && (
                        <div className="mt-1 text-[10px] text-emerald-600/90 pl-3 border-l border-emerald-900">
                          {JSON.stringify(
                            Object.fromEntries(
                              Object.entries(log).filter(
                                ([k]) =>
                                  ![
                                    "timestamp",
                                    "level",
                                    "message",
                                    "action",
                                    "service",
                                    "logger",
                                    "module",
                                    "funcName",
                                    "lineNo",
                                    "processId",
                                  ].includes(k)
                              )
                            )
                          )}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-8 text-center text-emerald-600">No logs matching filter...</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* DEBOUNCED WATCHER TAB */}
        {activeTab === "watcher" && (
          <div className="space-y-6">
            <div className="bg-white border border-[#E0E9E2] rounded-xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-center justify-between mb-4 border-b border-[#EEF4EF] pb-3">
                <div className="flex items-center gap-2">
                  <Radio className="h-5 w-5 text-emerald-700" />
                  <div>
                    <h2 className="text-sm font-bold text-[#0F2217]">Automated Input Folder Watcher & Debouncing</h2>
                    <p className="text-xs text-[#52665B]">
                      Monitors <code className="font-mono text-emerald-800">input/</code> folder, suppresses duplicate burst writes with a 3.0s debounce cooldown, triggers the analyzer, and packages artifacts.
                    </p>
                  </div>
                </div>
              </div>

              {/* Watcher Architecture Specs */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="p-3.5 bg-[#F5F8F5] border border-[#E2EAE3] rounded-xl">
                  <div className="text-[11px] font-bold uppercase text-[#52665B] mb-1">Monitored Directory</div>
                  <div className="font-mono text-xs font-bold text-emerald-900">input/*.csv</div>
                  <div className="text-[11px] text-[#5C7063] mt-1">Automatic discovery & MD5 hash check</div>
                </div>
                <div className="p-3.5 bg-[#F5F8F5] border border-[#E2EAE3] rounded-xl">
                  <div className="text-[11px] font-bold uppercase text-[#52665B] mb-1">Debounce Cooldown</div>
                  <div className="font-mono text-xs font-bold text-emerald-900">3.0 Seconds</div>
                  <div className="text-[11px] text-[#5C7063] mt-1">Prevents duplicate triggers on rapid file writes</div>
                </div>
                <div className="p-3.5 bg-[#F5F8F5] border border-[#E2EAE3] rounded-xl">
                  <div className="text-[11px] font-bold uppercase text-[#52665B] mb-1">Output Action</div>
                  <div className="font-mono text-xs font-bold text-emerald-900">Execute & Package ZIP</div>
                  <div className="text-[11px] text-[#5C7063] mt-1">Saves runs to reports/runs & archives/</div>
                </div>
              </div>

              {/* Interactive Execution Controls */}
              <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h4 className="text-xs font-bold text-emerald-950">Run Watcher Daemon in Foreground / Background:</h4>
                  <p className="text-[11px] text-[#35483C]">
                    You can launch the watcher via CLI or trigger a test run directly below:
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setActiveTab("terminal");
                      handleRunScript("input_watcher", "--run-on-start");
                    }}
                    disabled={isRunning}
                    className="px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-xs font-semibold text-white shadow-xs inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  >
                    <Play className="h-3.5 w-3.5 fill-current" />
                    Test Single Watcher Cycle
                  </button>
                </div>
              </div>

              {/* CLI Command Example */}
              <div className="mt-4 p-3 bg-[#0B1510] border border-[#1C3224] rounded-lg flex items-center justify-between">
                <code className="text-xs font-mono text-[#4ADE80]">
                  python input_watcher.py --debounce 3.0 --interval 1.0
                </code>
                <button
                  onClick={() =>
                    copyToClipboard("python input_watcher.py --debounce 3.0 --interval 1.0", "watcher-cli")
                  }
                  className="text-xs text-emerald-300 hover:text-white inline-flex items-center gap-1 font-mono cursor-pointer"
                >
                  {copiedCmd === "watcher-cli" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  Copy Command
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CHARTS TAB */}
        {activeTab === "charts" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E0E9E2] p-4 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div>
                <h2 className="text-sm font-bold text-[#0F2217]">Publication-Grade Visualizations</h2>
                <p className="text-xs text-[#52665B]">Generated directly via Python's matplotlib & seaborn engine into reports/ (300 DPI)</p>
              </div>
              <button
                id="btn-regenerate-charts"
                onClick={() => handleRunScript("logistics_cost_analyzer", "--charts")}
                disabled={isRunning}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-xs font-semibold text-white shadow-sm transition disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isRunning ? "animate-spin" : ""}`} />
                Regenerate Charts
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {Object.keys(chartMeta).map((chartFile) => {
                const info = chartMeta[chartFile];
                return (
                  <div
                    key={chartFile}
                    id={`chart-card-${chartFile.replace(".png", "")}`}
                    className="bg-white border border-[#E0E9E2] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.04)] flex flex-col"
                  >
                    <div className="p-4 border-b border-[#E8EFEA] bg-[#FAFBF9] flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-xs font-bold text-[#0F2217]">{info.title}</h3>
                        <p className="text-[11px] text-[#52665B] mt-0.5">{info.desc}</p>
                      </div>
                      <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
                        {chartFile}
                      </span>
                    </div>
                    <div className="p-4 bg-white flex-1 flex items-center justify-center min-h-[300px]">
                      <img
                        src={`/reports-media/${chartFile}`}
                        alt={info.title}
                        className="max-h-[380px] w-auto max-w-full rounded object-contain border border-[#EEF2EF]"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TABLES & CSV TAB */}
        {activeTab === "tables" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E0E9E2] p-3.5 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-emerald-700" />
                <span className="text-xs font-bold text-[#142A1D]">Select Exported CSV Report:</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: "route_analysis.csv", label: "Route Analysis" },
                  { id: "carrier_analysis.csv", label: "Carrier Benchmarking" },
                  { id: "monthly_analysis.csv", label: "Monthly Trends" },
                  { id: "cost_driver_analysis.csv", label: "Cost Drivers" },
                ].map((item) => (
                  <button
                    key={item.id}
                    id={`btn-csv-${item.id.replace(".csv", "")}`}
                    onClick={() => setSelectedCsv(item.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                      selectedCsv === item.id
                        ? "bg-emerald-700 text-white shadow-xs"
                        : "bg-[#EEF4EF] text-[#294232] hover:bg-[#E2EBE3]"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Table Container */}
            <div className="bg-white border border-[#E0E9E2] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="p-3.5 border-b border-[#E8EFEA] bg-[#FAFBF9] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-bold text-[#0F2217] uppercase tracking-wider">{selectedCsv}</h3>
                  <span className="text-[11px] text-[#5C7063]">
                    ({csvData?.rows.length ?? 0} records loaded)
                  </span>
                </div>
                <a
                  href={`/reports-media/${selectedCsv}`}
                  download={selectedCsv}
                  className="inline-flex items-center gap-1 text-xs text-emerald-800 hover:text-emerald-950 font-semibold bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200"
                >
                  <Download className="h-3.5 w-3.5" /> Download CSV
                </a>
              </div>

              <div className="overflow-x-auto max-h-[520px]">
                {csvData && csvData.headers.length > 0 ? (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F4F7F4] sticky top-0 border-b border-[#E0E8E1] text-[#142A1D] font-bold">
                      <tr>
                        {csvData.headers.map((h) => (
                          <th key={h} className="px-4 py-2.5 whitespace-nowrap">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EDF3EE] font-mono text-[11px]">
                      {csvData.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-[#F7FAF7] transition">
                          {csvData.headers.map((h) => (
                            <td key={h} className="px-4 py-2 whitespace-nowrap text-[#25392D]">
                              {row[h]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="p-8 text-center text-xs text-[#73887B]">
                    No data found or file still generating...
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TERMINAL & CLI TAB */}
        {activeTab === "terminal" && (
          <div className="space-y-4">
            {/* Quick Command Execution Buttons */}
            <div className="bg-white border border-[#E0E9E2] p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-emerald-700" />
                <span className="text-xs font-bold text-[#142A1D]">Execute CLI Sub-Module:</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleRunScript("logistics_cost_analyzer")}
                  disabled={isRunning}
                  className="px-2.5 py-1 text-xs font-mono bg-emerald-100 hover:bg-emerald-200 text-emerald-950 font-semibold rounded border border-emerald-300 cursor-pointer"
                >
                  python logistics_cost_analyzer.py
                </button>
              </div>
            </div>

            {/* Terminal Console Window */}
            <div className="bg-[#0B1510] border border-[#1C3224] rounded-xl overflow-hidden shadow-xl">
              <div className="px-4 py-2.5 bg-[#0F2018] border-b border-[#1C3224] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                    <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-xs font-mono text-emerald-300 ml-2">Console Live Execution Stream</span>
                </div>
                <button
                  onClick={() => copyToClipboard(terminalOutput || status?.summaryText || "", "term")}
                  className="text-xs text-emerald-300 hover:text-white inline-flex items-center gap-1 font-mono cursor-pointer"
                >
                  {copiedCmd === "term" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  Copy Log
                </button>
              </div>
              <pre className="p-4 text-xs font-mono text-[#4ADE80] overflow-x-auto whitespace-pre leading-relaxed min-h-[420px] max-h-[620px]">
                {terminalOutput || status?.summaryText || "Click 'Run Full Analyzer' or any sub-module above to execute the pipeline..."}
              </pre>
            </div>
          </div>
        )}

        {/* USER GUIDE & CODE VIEWER TAB */}
        {activeTab === "docs" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-[#E0E9E2] p-3.5 rounded-xl shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-700" />
                <span className="text-xs font-bold text-[#142A1D]">Browse Guides & Deliverables:</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: "HOWTO.md", label: "HOWTO.md (UI Guide)" },
                  { id: "README.md", label: "README.md (Full Specs)" },
                ].map((f) => (
                  <button
                    key={f.id}
                    id={`btn-file-${f.id.replace(".", "-")}`}
                    onClick={() => setActiveFile(f.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition cursor-pointer ${
                      activeFile === f.id
                        ? "bg-emerald-700 text-white shadow-xs"
                        : "bg-[#EEF4EF] text-[#294232] hover:bg-[#E2EBE3]"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-white border border-[#E0E9E2] rounded-xl overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="p-3.5 border-b border-[#E8EFEA] bg-[#FAFBF9] flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-[#0F2217]">{activeFile}</span>
                <button
                  onClick={() => copyToClipboard(fileContent, "file")}
                  className="text-xs text-emerald-800 hover:text-emerald-950 inline-flex items-center gap-1 font-mono font-semibold cursor-pointer bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200"
                >
                  {copiedCmd === "file" ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                  Copy Code
                </button>
              </div>
              <pre className="p-4 text-xs font-mono text-[#25392D] bg-white overflow-x-auto whitespace-pre leading-relaxed max-h-[600px]">
                {fileContent || "Loading file..."}
              </pre>
            </div>
          </div>
        )}
      </main>

      {/* Modern Footer */}
      <footer className="border-t border-[#E0E9E2] bg-white py-4 mt-auto text-xs text-[#5C7063]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-2">
          <span className="font-medium text-[#183623]">
            Logistics Cost Analyzer • Automated Ingestion & Artifact Packaging Pipeline
          </span>
          <span className="font-mono text-[#52665B]">input/*.csv → reports/runs/ → reports/archives/*.zip</span>
        </div>
      </footer>
    </div>
  );
}
