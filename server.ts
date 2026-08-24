import express from "express";
import path from "path";
import fs from "fs";
import { exec, ChildProcess } from "child_process";
import { createServer as createViteServer } from "vite";

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  const reportsDir = path.join(process.cwd(), "reports");
  const inputDir = path.join(process.cwd(), "input");
  const logsDir = path.join(process.cwd(), "logs");
  const archivesDir = path.join(reportsDir, "archives");
  const runsDir = path.join(reportsDir, "runs");

  // Ensure primary directories exist
  [reportsDir, inputDir, logsDir, archivesDir, runsDir].forEach((d) => {
    if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true });
  });

  // Keep track of background watcher process if started from UI
  let watcherProcess: ChildProcess | null = null;
  let watcherLogs: string[] = [];

  // API 1: Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  // API 2: Get pipeline status & overview
  app.get("/api/status", (req, res) => {
    const hasInput = fs.existsSync(path.join(inputDir, "shipments.csv"));
    const hasReports = fs.existsSync(path.join(reportsDir, "summary.txt"));

    let summaryText = "";
    if (hasReports) {
      try {
        summaryText = fs.readFileSync(path.join(reportsDir, "summary.txt"), "utf-8");
      } catch {
        summaryText = "";
      }
    }

    let regressionText = "";
    if (fs.existsSync(path.join(reportsDir, "regression_results.txt"))) {
      try {
        regressionText = fs.readFileSync(path.join(reportsDir, "regression_results.txt"), "utf-8");
      } catch {
        regressionText = "";
      }
    }

    // List generated charts
    const charts = [
      "monthly_cost_trend.png",
      "top_routes.png",
      "carrier_cost_comparison.png",
      "cost_vs_distance.png",
      "cost_vs_weight.png",
      "cost_distribution.png",
      "on_time_delivery_by_carrier.png",
    ].filter((img) => fs.existsSync(path.join(reportsDir, img)));

    // List CSVs
    const csvFiles = [
      "route_analysis.csv",
      "carrier_analysis.csv",
      "monthly_analysis.csv",
      "cost_driver_analysis.csv",
    ].filter((f) => fs.existsSync(path.join(reportsDir, f)));

    // List input files
    let inputFiles: string[] = [];
    if (fs.existsSync(inputDir)) {
      inputFiles = fs.readdirSync(inputDir).filter((f) => f.endsWith(".csv"));
    }

    res.json({
      hasInput,
      hasReports,
      summaryText,
      regressionText,
      charts,
      csvFiles,
      inputFiles,
      isWatcherRunning: watcherProcess !== null && !watcherProcess.killed,
    });
  });

  // API 3: Fetch parsed CSV report data
  app.get("/api/reports/csv/:filename", (req, res) => {
    const filename = req.params.filename;
    const safeFilename = path.basename(filename);
    const filePath = path.join(reportsDir, safeFilename);

    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: "File not found" });
    }

    try {
      const content = fs.readFileSync(filePath, "utf-8");
      const lines = content.trim().split("\n");
      if (lines.length === 0) return res.json({ headers: [], rows: [] });

      const headers = lines[0].split(",").map((h) => h.trim());
      const rows = lines.slice(1).map((line) => {
        const values = line.split(",").map((v) => v.trim());
        const rowObj: Record<string, string> = {};
        headers.forEach((h, idx) => {
          rowObj[h] = values[idx] ?? "";
        });
        return rowObj;
      });

      res.json({ headers, rows });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // API 4: Serve generated report images and files
  app.use("/reports-media", express.static(reportsDir));

  // API 5: Execute Python scripts with fallback for cross-platform support (Linux/Mac/Windows)
  app.post("/api/run", (req, res) => {
    const { script, flags = "" } = req.body;

    const scriptFile =
      script === "generate_sample_data"
        ? "generate_sample_data.py"
        : script === "logistics_cost_analyzer"
        ? "logistics_cost_analyzer.py"
        : script === "artifacts_handler"
        ? "artifacts_handler.py"
        : script === "input_watcher"
        ? "input_watcher.py"
        : null;

    if (!scriptFile) {
      return res.status(400).json({ error: "Invalid script request" });
    }

    const sanitizedFlags = String(flags || "")
      .replace(/[^a-zA-Z0-9_\-\s\.]/g, "")
      .trim();

    // Check potential python commands
    const tryCommands = [
      `python3 ${scriptFile} ${sanitizedFlags}`.trim(),
      `python ${scriptFile} ${sanitizedFlags}`.trim(),
      `py -3 ${scriptFile} ${sanitizedFlags}`.trim(),
      `uv run python ${scriptFile} ${sanitizedFlags}`.trim(),
    ];

    const runWithFallback = (index: number) => {
      if (index >= tryCommands.length) {
        return res.json({
          command: tryCommands[0],
          exitCode: 1,
          stdout: "",
          stderr:
            "Python executable was not found on your system PATH. Please ensure Python (or uv) is installed and available.",
          success: false,
        });
      }

      const cmd = tryCommands[index];
      exec(cmd, { cwd: process.cwd() }, (error, stdout, stderr) => {
        if (
          error &&
          (error.code === 9009 ||
            error.code === 127 ||
            (stderr && stderr.includes("Python was not found")) ||
            (stderr && stderr.includes("command not found")))
        ) {
          return runWithFallback(index + 1);
        }

        res.json({
          command: cmd,
          exitCode: error ? error.code || 1 : 0,
          stdout: stdout || "",
          stderr: stderr || "",
          success: !error,
        });
      });
    };

    runWithFallback(0);
  });

  // API 6: Read source/doc files
  app.get("/api/files/:filename", (req, res) => {
    const validFiles = [
      "README.md",
      "HOWTO.md",
      "pyproject.toml",
      "requirements.txt",
      "logistics_cost_analyzer.py",
      "artifacts_handler.py",
      "input_watcher.py",
      "structured_logger.py",
      "generate_sample_data.py",
    ];
    const filename = req.params.filename;
    if (!validFiles.includes(filename)) {
      return res.status(403).json({ error: "Forbidden file" });
    }
    const filePath = path.join(process.cwd(), filename);
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: "File not found" });
    }
    const content = fs.readFileSync(filePath, "utf-8");
    res.json({ filename, content });
  });

  // API 7: Fetch Structured JSON Logs
  app.get("/api/logs", (req, res) => {
    const logFile = path.join(logsDir, "pipeline_operations.json.log");
    if (!fs.existsSync(logFile)) {
      return res.json({ logs: [] });
    }

    try {
      const rawContent = fs.readFileSync(logFile, "utf-8");
      const lines = rawContent
        .trim()
        .split("\n")
        .filter((line) => line.trim().length > 0);

      const logs = lines
        .map((line) => {
          try {
            return JSON.parse(line);
          } catch {
            return { raw: line };
          }
        })
        .reverse(); // Newest first

      res.json({ logs });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // API 8: Fetch Historical Runs and Timestamped ZIP Archives
  app.get("/api/runs", (req, res) => {
    try {
      const runFolders = fs.existsSync(runsDir)
        ? fs
            .readdirSync(runsDir, { withFileTypes: true })
            .filter((dirent) => dirent.isDirectory())
            .map((dirent) => dirent.name)
            .sort()
            .reverse()
        : [];

      const runs = runFolders.map((runId) => {
        const runPath = path.join(runsDir, runId);
        const manifestPath = path.join(runPath, "run_manifest.json");
        let manifest: any = {};
        if (fs.existsSync(manifestPath)) {
          try {
            manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
          } catch {}
        }

        const zipFilename = `logistics_reports_${runId}.zip`;
        const zipPath = path.join(archivesDir, zipFilename);
        const zipExists = fs.existsSync(zipPath);
        const zipSizeKb = zipExists ? Math.round((fs.statSync(zipPath).size / 1024) * 100) / 100 : 0;

        const files = fs.existsSync(runPath) ? fs.readdirSync(runPath) : [];

        return {
          run_id: runId,
          created_at: manifest.created_at_local || manifest.timestamp_utc || "",
          artifacts_count: manifest.artifacts_count || files.length,
          artifacts: files,
          zip_exists: zipExists,
          zip_filename: zipFilename,
          zip_size_kb: zipSizeKb,
        };
      });

      res.json({ runs });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // API 9: Download specific run ZIP archive
  app.get("/api/archives/download/:filename", (req, res) => {
    const filename = path.basename(req.params.filename);
    const zipPath = path.join(archivesDir, filename);

    if (!fs.existsSync(zipPath)) {
      return res.status(404).json({ error: "Archive not found" });
    }

    res.download(zipPath, filename);
  });

  // API 10: Toggle/Control Watcher Daemon
  app.post("/api/watcher/toggle", (req, res) => {
    const { action } = req.body;

    if (action === "start") {
      if (watcherProcess && !watcherProcess.killed) {
        return res.json({ status: "already_running" });
      }

      const pythonCmd = "python3";
      watcherProcess = exec(
        `python3 input_watcher.py --debounce 3.0 --interval 1.0`,
        { cwd: process.cwd() }
      );

      watcherProcess.stdout?.on("data", (data) => {
        watcherLogs.push(data.toString());
        if (watcherLogs.length > 200) watcherLogs.shift();
      });

      watcherProcess.stderr?.on("data", (data) => {
        watcherLogs.push(`[ERR] ${data.toString()}`);
        if (watcherLogs.length > 200) watcherLogs.shift();
      });

      watcherProcess.on("exit", (code) => {
        watcherLogs.push(`[SYSTEM] Watcher process exited with code ${code}`);
        watcherProcess = null;
      });

      return res.json({ status: "started" });
    } else if (action === "stop") {
      if (watcherProcess && !watcherProcess.killed) {
        watcherProcess.kill();
        watcherProcess = null;
      }
      return res.json({ status: "stopped" });
    }

    res.status(400).json({ error: "Invalid action" });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
