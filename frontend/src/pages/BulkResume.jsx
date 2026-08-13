import React, { useState, useMemo, useRef } from "react";
import axios from "axios";

import {
  Button,
  TextField,
  Chip,
  Snackbar,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Checkbox,
  LinearProgress,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip
} from "@mui/material";

import "./Bulkresume.css";

const API_BASE = "http://127.0.0.1:5000";

function BulkResume() {

  // ---------------- STATE ----------------
  const [mode, setMode] = useState("bulk");
  const [files, setFiles] = useState([]);
  const [jobDesc, setJobDesc] = useState("");
  const [results, setResults] = useState([]);
  const [singleResult, setSingleResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  const [toast, setToast] = useState({ open: false, msg: "", severity: "info" });

  const [orderBy, setOrderBy] = useState("job_fit_score");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selected, setSelected] = useState([]);

  const inputRef = useRef(null);
  const abortRef = useRef(null);

  // ---------------- HELPERS ----------------
  const notify = (msg, severity = "error") =>
    setToast({ open: true, msg, severity });

  const closeToast = (_e, reason) => {
    if (reason === "clickaway") return;
    setToast((t) => ({ ...t, open: false }));
  };

  const toNumber = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : -Infinity;
  };

  const hasScore = (v) =>
    v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));

  const showScore = (v) => (hasScore(v) ? Math.round(Number(v)) : "—");

  const barValue = (v) =>
    hasScore(v) ? Math.max(0, Math.min(100, Number(v))) : 0;

  // returns a css modifier class, not a color
  const toneClass = (v) => {
    if (!hasScore(v)) return "";
    const n = Number(v);
    if (n >= 75) return "tone-good";
    if (n >= 50) return "tone-mid";
    return "tone-bad";
  };

  const errorText = (err) =>
    err?.response?.data?.error ||
    err?.response?.data?.message ||
    err?.message ||
    "Unknown error";

  const recTone = (rec) => {
    const r = String(rec || "").toLowerCase();
    if (r.includes("reject") || r.includes("not ")) return "error";
    if (r.includes("strong") || r.includes("shortlist") || r.includes("hire"))
      return "success";
    if (r.includes("maybe") || r.includes("consider") || r.includes("review"))
      return "warning";
    return "default";
  };

  const rankLabel = (n) => String(n).padStart(2, "0");

  const clearResults = () => {
    setResults([]);
    setSingleResult(null);
    setSelected([]);
    setPage(0);
  };

  const resetInput = () => {
    if (inputRef.current) inputRef.current.value = "";
  };

  // ---------------- FILE HANDLING ----------------
  const addFiles = (incoming) => {

    const list = Array.from(incoming || []);
    if (!list.length) return;

    setFiles((prev) => {

      const next = mode === "single" ? [] : [...prev];

      list.forEach((f) => {
        const dup = next.some((x) => x.name === f.name && x.size === f.size);
        if (!dup) next.push(f);
      });

      return mode === "single" ? next.slice(0, 1) : next;
    });

    resetInput();
  };

  const removeFile = (name, size) =>
    setFiles((prev) => prev.filter((f) => !(f.name === name && f.size === size)));

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (loading) return;
    addFiles(e.dataTransfer.files);
  };

  const openPicker = () => {
    if (!loading && inputRef.current) inputRef.current.click();
  };

  // ---------------- MODE SWITCH ----------------
  const handleModeChange = (_e, nextMode) => {

    if (!nextMode || nextMode === mode || loading) return;

    setMode(nextMode);
    clearResults();
    setFiles([]);
    resetInput();
  };

  // ---------------- REQUESTS ----------------
  const runRequest = async (url, formData, onDone) => {

    abortRef.current = new AbortController();

    setLoading(true);
    setUploadProgress(0);

    try {

      const res = await axios.post(url, formData, {
        signal: abortRef.current.signal,
        onUploadProgress: (evt) => {
          if (!evt.total) return;
          setUploadProgress(Math.round((evt.loaded * 100) / evt.total));
        }
      });

      onDone(res);

    } catch (err) {

      if (axios.isCancel?.(err) || err?.name === "CanceledError") {
        notify("Analysis cancelled", "info");
      } else {
        notify(errorText(err));
      }

    } finally {

      setLoading(false);
      setUploadProgress(0);
      abortRef.current = null;

    }
  };

  const handleCancel = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const handleSingleAnalyze = () => {

    if (loading) return;

    if (!files.length || !jobDesc.trim()) {
      return notify("Add one resume and a job description", "warning");
    }

    const formData = new FormData();
    formData.append("resume", files[0]);
    formData.append("job_description", jobDesc.trim());

    runRequest(`${API_BASE}/analyze`, formData, (res) => {

      if (!res.data || typeof res.data !== "object") {
        return notify("The server returned an empty response");
      }

      setSingleResult(res.data);
      setResults([]);
      setSelected([]);
      notify("Resume analyzed", "success");
    });
  };

  const handleBulkAnalyze = () => {

    if (loading) return;

    if (!files.length || !jobDesc.trim()) {
      return notify("Add resumes and a job description", "warning");
    }

    const formData = new FormData();
    files.forEach((f) => formData.append("resumes", f));
    formData.append("job_description", jobDesc.trim());

    runRequest(`${API_BASE}/compare`, formData, (res) => {

      const comparison = Array.isArray(res.data?.comparison)
        ? res.data.comparison
        : [];

      if (!comparison.length) {
        clearResults();
        return notify("The server returned no candidates", "warning");
      }

      const sorted = [...comparison]
        .sort((a, b) => toNumber(b.job_fit_score) - toNumber(a.job_fit_score))
        .map((r, i) => ({ ...r, _id: `${r.filename || "resume"}-${i}` }));

      setResults(sorted);
      setSingleResult(null);
      setSelected([]);
      setPage(0);
      setOrderBy("job_fit_score");
      setOrder("desc");

      notify(`Ranked ${sorted.length} candidates`, "success");
    });
  };

  // ---------------- SORT / PAGE / SELECT ----------------
  const handleSort = (field) => {

    if (orderBy === field) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setOrderBy(field);
      setOrder("desc");
    }

    setPage(0);
  };

  const sortedResults = useMemo(() => {

    const dir = order === "asc" ? 1 : -1;

    return [...results].sort((a, b) => {

      if (orderBy === "filename" || orderBy === "recommendation") {
        return (
          dir * String(a[orderBy] || "").localeCompare(String(b[orderBy] || ""))
        );
      }

      return dir * (toNumber(a[orderBy]) - toNumber(b[orderBy]));
    });

  }, [results, orderBy, order]);

  const pagedResults = useMemo(
    () => sortedResults.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage),
    [sortedResults, page, rowsPerPage]
  );

  const isSelected = (id) => selected.indexOf(id) !== -1;

  const toggleRow = (id) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  const toggleAll = (checked) =>
    setSelected(checked ? results.map((r) => r._id) : []);

  // ---------------- SUMMARY ----------------
  const stats = useMemo(() => {

    const fits = results
      .map((r) => Number(r.job_fit_score))
      .filter(Number.isFinite);

    return {
      total: results.length,
      avg: fits.length
        ? Math.round(fits.reduce((a, b) => a + b, 0) / fits.length)
        : null,
      best: fits.length ? Math.round(Math.max(...fits)) : null,
      strong: fits.filter((n) => n >= 75).length
    };
  }, [results]);

  // ---------------- CSV ----------------
  const csvCell = (v) => {
    const s = v === null || v === undefined ? "" : String(v);
    return `"${s.replace(/"/g, '""')}"`;
  };

  const handleExportCSV = () => {

    const rows = selected.length
      ? sortedResults.filter((r) => isSelected(r._id))
      : sortedResults;

    if (!rows.length) return notify("Nothing to export", "warning");

    const header = [
      "Rank",
      "Filename",
      "ATS Score",
      "ML Score",
      "Job Fit Score",
      "Recommendation"
    ];

    const body = rows.map((r, i) =>
      [i + 1, r.filename, r.score, r.ml_score, r.job_fit_score, r.recommendation]
        .map(csvCell)
        .join(",")
    );

    const csv = [header.map(csvCell).join(","), ...body].join("\r\n");

    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = `shortlist_${new Date().toISOString().slice(0, 10)}.csv`;

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    notify(`Exported ${rows.length} candidates`, "success");
  };

  const top5 = results.slice(0, 5);
  const canRun = !loading && files.length > 0 && jobDesc.trim().length > 0;

  const columns = [
    ["filename", "Candidate"],
    ["score", "ATS"],
    ["ml_score", "ML"],
    ["job_fit_score", "Job fit"],
    ["recommendation", "Recommendation"]
  ];

  // ---------------- SUB COMPONENTS ----------------
  const ScoreMeter = ({ value, wide }) => (
    <div className={wide ? "ra-meter is-wide" : "ra-meter"}>

      <p className={hasScore(value) ? "ra-meter-value" : "ra-meter-value is-empty"}>
        {showScore(value)}
        {hasScore(value) && <small>%</small>}
      </p>

      <div className="ra-meter-track">
        <div
          className={`ra-meter-fill ${toneClass(value)}`}
          style={{ width: `${barValue(value)}%` }}
        />
      </div>

    </div>
  );

  const StatTile = ({ label, value, suffix }) => (
    <div className="ra-stat">
      <p className="ra-stat-label">{label}</p>
      <p className="ra-stat-value">
        {value === null || value === undefined ? "—" : value}
        {suffix && value !== null && value !== undefined && <small>{suffix}</small>}
      </p>
    </div>
  );

  // ---------------- RENDER ----------------
  return (

    <div className="ra-page">

      <div className="ra-shell">

        {/* HEADER */}
        <header className="ra-header">

          <div>
            <p className="ra-eyebrow">Resume analyzer</p>
            <h1 className="ra-title">Screen candidates against a role</h1>
          </div>

          <ToggleButtonGroup
            className="ra-mode"
            size="small"
            exclusive
            value={mode}
            onChange={handleModeChange}
            disabled={loading}
            aria-label="Analysis mode"
          >
            <ToggleButton value="single" aria-label="Single resume mode">
              Single
            </ToggleButton>
            <ToggleButton value="bulk" aria-label="Bulk resume mode">
              Bulk
            </ToggleButton>
          </ToggleButtonGroup>

        </header>

        {/* INPUT PANEL */}
        <section className="ra-panel">

          <div className="ra-split">

            {/* FILES */}
            <div>

              <span className="ra-label">
                {mode === "single" ? "Resume" : "Resumes"}
              </span>

              <div
                className={
                  "ra-dropzone" +
                  (dragOver ? " is-dragging" : "") +
                  (loading ? " is-disabled" : "")
                }
                role="button"
                tabIndex={0}
                onClick={openPicker}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    openPicker();
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!loading) setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <p className="ra-drop-main">
                  Drop {mode === "single" ? "a resume" : "resumes"} here
                </p>
                <p className="ra-drop-sub">
                  or click to browse · PDF, DOC, DOCX, TXT
                </p>
              </div>

              <input
                ref={inputRef}
                type="file"
                hidden
                accept=".pdf,.doc,.docx,.txt"
                multiple={mode === "bulk"}
                onChange={(e) => addFiles(e.target.files)}
              />

              {files.length > 0 && (
                <div className="ra-chips">
                  {files.map((f) => (
                    <Chip
                      key={`${f.name}-${f.size}`}
                      size="small"
                      variant="outlined"
                      label={f.name}
                      onDelete={loading ? undefined : () => removeFile(f.name, f.size)}
                    />
                  ))}
                </div>
              )}

              <span className="ra-hint">
                {files.length} file{files.length === 1 ? "" : "s"} ready
              </span>

            </div>

            {/* JOB DESCRIPTION */}
            <div>

              <span className="ra-label">Job description</span>

              <TextField
                multiline
                rows={6}
                fullWidth
                size="small"
                disabled={loading}
                placeholder="Paste the full job description — responsibilities, required skills, experience level"
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
              />

              <span className="ra-hint">
                {jobDesc.trim().split(/\s+/).filter(Boolean).length} words
              </span>

            </div>

          </div>

          <hr className="ra-rule" />

          <div className="ra-actions">

            <Button
              variant="contained"
              disabled={!canRun}
              onClick={mode === "single" ? handleSingleAnalyze : handleBulkAnalyze}
            >
              {mode === "single" ? "Analyze resume" : "Rank candidates"}
            </Button>

            {loading && (
              <Button variant="outlined" color="error" onClick={handleCancel}>
                Cancel
              </Button>
            )}

            <span className="ra-spacer" />

            {!loading && !canRun && (
              <span className="ra-hint">
                Add {files.length ? "a job description" : "files"} to continue
              </span>
            )}

          </div>

          {loading && (
            <div className="ra-progress">
              <LinearProgress
                variant={uploadProgress < 100 ? "determinate" : "indeterminate"}
                value={uploadProgress}
              />
              <span className="ra-hint">
                {uploadProgress < 100
                  ? `Uploading ${uploadProgress}%`
                  : `Analyzing ${files.length} file${files.length === 1 ? "" : "s"} — this can take a minute`}
              </span>
            </div>
          )}

        </section>

        {/* SINGLE RESULT */}
        {singleResult && (
          <section className="ra-panel">

            <h2 className="ra-section ra-section-flush">
              {files[0]?.name || "Result"}
            </h2>

            <div className="ra-scores">

              {[
                ["ATS score", singleResult.score],
                ["ML score", singleResult.ml_score],
                ["Job fit", singleResult.job_fit_score]
              ].map(([label, value]) => (
                <div className="ra-score-block" key={label}>
                  <p className="ra-stat-label">{label}</p>
                  <ScoreMeter value={value} wide />
                </div>
              ))}

            </div>

            {singleResult.recommendation && (
              <div className="ra-chips">
                <Chip
                  size="small"
                  variant="outlined"
                  label={singleResult.recommendation}
                  color={recTone(singleResult.recommendation)}
                />
              </div>
            )}

          </section>
        )}

        {/* BULK RESULTS */}
        {results.length > 0 && (

          <>

            <div className="ra-stats">
              <StatTile label="Candidates" value={stats.total} />
              <StatTile label="Average fit" value={stats.avg} suffix="%" />
              <StatTile label="Best fit" value={stats.best} suffix="%" />
              <StatTile label="Strong (75+)" value={stats.strong} />
            </div>

            <h2 className="ra-section">Shortlist</h2>

            <div className="ra-shortlist">

              {top5.map((r, i) => (

                <article
                  className={`ra-card ${toneClass(r.job_fit_score)}`}
                  key={`top-${r._id}`}
                >

                  <div className="ra-card-head">
                    <span className="ra-rank">{rankLabel(i + 1)}</span>
                    <Tooltip title={r.filename || ""}>
                      <span className="ra-name">{r.filename || "Untitled"}</span>
                    </Tooltip>
                  </div>

                  <ScoreMeter value={r.job_fit_score} wide />

                  {r.recommendation && (
                    <Chip
                      size="small"
                      variant="outlined"
                      label={r.recommendation}
                      color={recTone(r.recommendation)}
                    />
                  )}

                </article>

              ))}

            </div>

            <div className="ra-table-panel">

              <div className="ra-toolbar">

                <p className="ra-toolbar-title">
                  {selected.length
                    ? `${selected.length} selected`
                    : `All candidates (${results.length})`}
                </p>

                <Button size="small" variant="outlined" onClick={handleExportCSV}>
                  Export CSV
                </Button>

              </div>

              <TableContainer className="ra-table-scroll">

                <Table size="small" stickyHeader>

                  <TableHead>
                    <TableRow>

                      <TableCell padding="checkbox">
                        <Checkbox
                          size="small"
                          indeterminate={
                            selected.length > 0 && selected.length < results.length
                          }
                          checked={
                            results.length > 0 && selected.length === results.length
                          }
                          onChange={(e) => toggleAll(e.target.checked)}
                        />
                      </TableCell>

                      <TableCell>#</TableCell>

                      {columns.map(([field, label]) => (
                        <TableCell key={field}>
                          <TableSortLabel
                            active={orderBy === field}
                            direction={orderBy === field ? order : "desc"}
                            onClick={() => handleSort(field)}
                          >
                            {label}
                          </TableSortLabel>
                        </TableCell>
                      ))}

                    </TableRow>
                  </TableHead>

                  <TableBody>

                    {pagedResults.map((r, i) => (

                      <TableRow
                        hover
                        key={r._id}
                        selected={isSelected(r._id)}
                        onClick={() => toggleRow(r._id)}
                      >

                        <TableCell padding="checkbox">
                          <Checkbox size="small" checked={isSelected(r._id)} />
                        </TableCell>

                        <TableCell className="ra-cell-rank">
                          {rankLabel(page * rowsPerPage + i + 1)}
                        </TableCell>

                        <TableCell>
                          <Tooltip title={r.filename || ""}>
                            <div className="ra-cell-name">
                              {r.filename || "Untitled"}
                            </div>
                          </Tooltip>
                        </TableCell>

                        <TableCell><ScoreMeter value={r.score} /></TableCell>
                        <TableCell><ScoreMeter value={r.ml_score} /></TableCell>
                        <TableCell><ScoreMeter value={r.job_fit_score} /></TableCell>

                        <TableCell>
                          {r.recommendation ? (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={r.recommendation}
                              color={recTone(r.recommendation)}
                            />
                          ) : (
                            <span className="ra-dash">—</span>
                          )}
                        </TableCell>

                      </TableRow>

                    ))}

                  </TableBody>

                </Table>

              </TableContainer>

              <TablePagination
                component="div"
                count={results.length}
                page={page}
                onPageChange={(_e, p) => setPage(p)}
                rowsPerPage={rowsPerPage}
                rowsPerPageOptions={[10, 25, 50]}
                onRowsPerPageChange={(e) => {
                  setRowsPerPage(parseInt(e.target.value, 10));
                  setPage(0);
                }}
              />

            </div>

          </>
        )}

        {/* EMPTY STATE */}
        {!loading && !results.length && !singleResult && (
          <div className="ra-empty">
            <p className="ra-empty-title">No results yet</p>
            <p className="ra-empty-body">
              Add {mode === "single" ? "a resume" : "resumes"} and a job description,
              then run the analysis.
            </p>
          </div>
        )}

      </div>

      <Snackbar
        open={toast.open}
        autoHideDuration={5000}
        onClose={closeToast}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={closeToast}
          severity={toast.severity}
          variant="filled"
          className="ra-alert"
        >
          {toast.msg}
        </Alert>
      </Snackbar>

    </div>
  );
}

export default BulkResume;
