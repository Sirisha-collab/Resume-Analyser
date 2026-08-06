import React, {
  useState,
  useRef,
  useMemo,
  useEffect,
  useCallback,
} from "react";
import axios from "axios";

import { Bar, Pie } from "react-chartjs-2";
import {
  Chart as ChartJS, BarElement, CategoryScale,
  LinearScale, ArcElement, Tooltip, Legend,
} from "chart.js";

import {
  Alert, AppBar, Box,
  Button, Chip, CircularProgress,
  Container, Divider, IconButton,
  InputAdornment, LinearProgress, Link,
  Paper, Skeleton, Snackbar,
  Stack, TextField, Toolbar,
  Tooltip as MuiTooltip, Typography,
} from "@mui/material";

import { createTheme, ThemeProvider, alpha } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CloseIcon from "@mui/icons-material/Close";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import DownloadIcon from "@mui/icons-material/Download";
import SendIcon from "@mui/icons-material/Send";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
// import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
// import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

ChartJS.register(
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

/* ------------------------------------------------------------------ *
 * Config
 * ------------------------------------------------------------------ */

const API_BASE =
  process.env.REACT_APP_API_BASE || "http://127.0.0.1:5000";

const api = axios.create({ baseURL: API_BASE, timeout: 120000 });

const ACCEPTED_TYPES = ".pdf,.doc,.docx";
const MAX_FILE_MB = 10;

/* ------------------------------------------------------------------ *
 * Design tokens
 * ------------------------------------------------------------------ */

const tokens = {
  light: {
    accent: "#0D7C74",
    accentSoft: "#E6F2F1",
    bg: "#F6F6F4",
    paper: "#FFFFFF",
    border: "#E3E3DF",
    text: "#000000",
    muted: "#000000",
    success: "#15803D",
    warning: "#B45309",
    danger: "#B91C1C",
  },
  dark: {
    accent: "#2DD4BF",
    accentSoft: "#122A28",
    bg: "#0D0F0E",
    paper: "#15181A",
    border: "#262A2C",
    text: "#ECEDEC",
    muted: "#9199A0",
    success: "#4ADE80",
    warning: "#FBBF24",
    danger: "#F87171",
  },
};

const MONO = '"JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace';
const SANS =
  '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

function buildTheme(mode) {
  const t = tokens[mode];

  return createTheme({
    palette: {
      mode,
      primary: { main: t.accent },
      success: { main: t.success },
      warning: { main: t.warning },
      error: { main: t.danger },
      background: { default: t.bg, paper: t.paper },
      text: { primary: t.text, secondary: t.muted },
      divider: t.border,
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: SANS,
      h1: { fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em" },
      h2: { fontSize: 20, fontWeight: 600, letterSpacing: "-0.01em" },
      h3: { fontSize: 16, fontWeight: 600 },
      body1: { fontSize: 14.5, lineHeight: 1.6 },
      body2: { fontSize: 13, lineHeight: 1.55 },
      caption: { fontSize: 11.5, letterSpacing: "0.04em" },
      button: { textTransform: "none", fontWeight: 500, fontSize: 14 },
    },
    components: {
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            backgroundImage: "none",
            border: `1px solid ${t.border}`,
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 8, paddingInline: 16, minHeight: 38 },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 6, fontWeight: 500, fontSize: 12.5 },
        },
      },
      MuiTextField: { defaultProps: { size: "small" } },
      MuiOutlinedInput: {
        styleOverrides: { root: { borderRadius: 8, background: t.paper } },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            background: t.paper,
            color: t.text,
            borderBottom: `1px solid ${t.border}`,
          },
        },
      },
    },
  });
}

/* ------------------------------------------------------------------ *
 * Helpers
 * ------------------------------------------------------------------ */

const num = (v) => (typeof v === "number" && !Number.isNaN(v) ? v : 0);

function band(value) {
  if (value >= 70) return "success";
  if (value >= 40) return "warning";
  return "error";
}

function bandLabel(value) {
  if (value >= 70) return "Strong";
  if (value >= 40) return "Needs work";
  return "Weak";
}

function useFontLoader() {
  useEffect(() => {
    const id = "resume-analyzer-fonts";
    if (document.getElementById(id)) return;
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap";
    document.head.appendChild(link);
  }, []);
}

/* ------------------------------------------------------------------ *
 * Small presentational pieces
 * ------------------------------------------------------------------ */

function SectionLabel({ children, sx }) {
  return (
    <Typography
      variant="caption"
      sx={{
        display: "block",
        textTransform: "uppercase",
        fontWeight: 600,
        color: "text.secondary",
        mb: 1.5,
        ...sx,
      }}
    >
      {children}
    </Typography>
  );
}

/**
 * Score rail — the value, a track, and a threshold tick at 70%.
 * A weak score should look weak without reading the number.
 */
function ScoreRail({ label, value, caption, threshold = 70 }) {
  const v = Math.max(0, Math.min(100, num(value)));
  const tone = band(v);

  return (
    <Paper sx={{ p: 2.25, borderRadius: 2.5, height: "100%" }}>
      <Typography
        variant="caption"
        sx={{ color: "text.secondary", fontWeight: 500 }}
      >
        {label}
      </Typography>

      <Stack direction="row" alignItems="baseline" spacing={0.75} sx={{ mt: 0.75 }}>
        <Typography
          sx={{
            fontFamily: MONO,
            fontSize: 26,
            fontWeight: 500,
            lineHeight: 1,
            color: `${tone}.main`,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {v.toFixed(1)}
        </Typography>
        <Typography sx={{ fontFamily: MONO, fontSize: 13, color: "text.secondary" }}>
          %
        </Typography>
      </Stack>

      <Box
        sx={{
          position: "relative",
          height: 6,
          borderRadius: 3,
          mt: 1.75,
          bgcolor: (th) => alpha(th.palette.text.primary, 0.07),
          overflow: "visible",
        }}
      >
        <Box
          sx={{
            width: `${v}%`,
            height: "100%",
            borderRadius: 3,
            bgcolor: `${tone}.main`,
            transition: "width .5s cubic-bezier(.4,0,.2,1)",
          }}
        />
        <MuiTooltip title={`Target ${threshold}%`} arrow>
          <Box
            sx={{
              position: "absolute",
              left: `${threshold}%`,
              top: -3,
              width: 1.5,
              height: 12,
              bgcolor: "text.secondary",
              opacity: 0.55,
            }}
          />
        </MuiTooltip>
      </Box>

      <Typography
        variant="caption"
        sx={{ display: "block", mt: 1.25, color: "text.secondary" }}
      >
        {caption || bandLabel(v)}
      </Typography>
    </Paper>
  );
}

function EmptyState({ icon, title, body }) {
  return (
    <Stack alignItems="center" spacing={1.25} sx={{ py: 6, px: 3 }}>
      <Box sx={{ color: "text.secondary", opacity: 0.5, display: "flex" }}>
        {icon}
      </Box>
      <Typography variant="h3">{title}</Typography>
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", textAlign: "center", maxWidth: 380 }}
      >
        {body}
      </Typography>
    </Stack>
  );
}

/* ------------------------------------------------------------------ *
 * Upload dropzone
 * ------------------------------------------------------------------ */

function Dropzone({ files, onChange, inputRef }) {
  const [dragging, setDragging] = useState(false);

  const accept = (list) => {
    const next = Array.from(list).filter((f) => {
      const ok = /\.(pdf|docx?|)$/i.test(f.name);
      const small = f.size <= MAX_FILE_MB * 1024 * 1024;
      return ok && small;
    });
    onChange(next);
  };

  return (
    <Box>
      <Box
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          accept(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        role="button"
        tabIndex={0}
        sx={{
          border: "1px dashed",
          borderColor: dragging ? "primary.main" : "divider",
          bgcolor: (th) =>
            dragging ? alpha(th.palette.primary.main, 0.05) : "transparent",
          borderRadius: 2.5,
          py: 3.5,
          px: 2,
          textAlign: "center",
          cursor: "pointer",
          transition: "all .18s ease",
          "&:hover": { borderColor: "primary.main" },
          "&:focus-visible": {
            outline: "2px solid",
            outlineColor: "primary.main",
            outlineOffset: 2,
          },
        }}
      >
        <UploadFileIcon sx={{ color: "text.secondary", mb: 0.5 }} />
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          Drop resumes here, or click to browse
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          PDF or Word, up to {MAX_FILE_MB} MB each
        </Typography>
      </Box>

      <input
        id="resume-upload"
        type="file"
        multiple
        hidden
        accept={ACCEPTED_TYPES}
        ref={inputRef}
        onChange={(e) => accept(e.target.files)}
      />

      {files.length > 0 && (
        <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1.5 }}>
          {files.map((f, i) => (
            <Chip
              key={`${f.name}-${i}`}
              icon={<DescriptionOutlinedIcon sx={{ fontSize: 16 }} />}
              label={f.name}
              variant="outlined"
              onDelete={() => onChange(files.filter((_, idx) => idx !== i))}
              deleteIcon={<CloseIcon />}
            />
          ))}
        </Stack>
      )}
    </Box>
  );
}

/* ------------------------------------------------------------------ *
 * Resume chat — one instance per resume, own message history
 * ------------------------------------------------------------------ */

function ResumeChat({ resumeId, notify }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  const ask = async (preset) => {
    const texting = (typeof preset === "string" ? preset : question).trim();
    if (!texting || loading) return;

    if (!resumeId) {
      notify("This resume has no index yet, so chat is unavailable.", "warning");
      return;
    }

    setMessages((m) => [...m, { role: "user", text: texting }]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await api.post("/resume-chat", {
        resume_id: resumeId,
        question: texting,
      });
      setMessages((m) => [
        ...m,
        { role: "bot", text: res.data?.answer || "No answer found." },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "bot",
          text: "That question could not be answered. Check the backend is running.",
          failed: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper
      sx={{
        borderRadius: 2.5,
        overflow: "hidden",
        maxWidth: 760,
        mx: "auto",
        width: "100%",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={1.25}
        sx={{ px: 2.25, py: 1.75, borderBottom: 1, borderColor: "divider" }}
      >
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            display: "grid",
            placeItems: "center",
            fontSize: 13,
            fontWeight: 600,
            color: "primary.main",
            bgcolor: (th) => alpha(th.palette.primary.main, 0.12),
          }}
        >
          AI
        </Box>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
            Ask about this resume
          </Typography>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            Answers come from the indexed resume text only
          </Typography>
        </Box>
      </Stack>

      <Box
        ref={scrollRef}
        role="log"
        aria-live="polite"
        sx={{
          height: 360,
          overflowY: "auto",
          px: 2.25,
          py: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
          bgcolor: (th) => alpha(th.palette.text.primary, 0.02),
        }}
      >
        {messages.length === 0 && !loading && (
          <Stack sx={{ m: "auto", maxWidth: 380 }} spacing={1.5}>
            <Typography
              variant="body2"
              sx={{ color: "text.secondary", textAlign: "center" }}
            >
              Ask anything about this resume.
            </Typography>
            <Stack spacing={0.75}>
              {[
                "How many years of React experience?",
                "List every company worked at.",
                "Biggest skill gaps for this JD?",
              ].map((s) => (
                <Chip
                  key={s}
                  label={s}
                  variant="outlined"
                  onClick={() => ask(s)}
                  sx={{ justifyContent: "flex-start", borderRadius: 1.5 }}
                />
              ))}
            </Stack>
          </Stack>
        )}

        {messages.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <Stack
              key={m.id ?? i}
              direction={isUser ? "row-reverse" : "row"}
              spacing={1.25}
              alignItems="flex-start"
              sx={{ flexShrink: 0 }}
            >
              <Box
                sx={{
                  flexShrink: 0,
                  width: 28,
                  height: 28,
                  mt: 0.25,
                  borderRadius: "50%",
                  display: "grid",
                  placeItems: "center",
                  fontSize: 11,
                  fontWeight: 600,
                  color: isUser ? "primary.main" : "text.secondary",
                  bgcolor: (th) =>
                    isUser
                      ? alpha(th.palette.primary.main, 0.12)
                      : alpha(th.palette.text.primary, 0.07),
                }}
              >
                {isUser ? "You" : "AI"}
              </Box>

              <Stack spacing={0.5} sx={{ maxWidth: "78%", minWidth: 0 }}>
                <Box
                  sx={{
                    px: 1.75,
                    py: 1.25,
                    fontSize: 14,
                    lineHeight: 1.55,
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    border: 1,
                    borderColor: m.failed ? "error.main" : "divider",
                    borderRadius: 2,
                    borderTopRightRadius: isUser ? 4 : 16,
                    borderTopLeftRadius: isUser ? 16 : 4,
                    bgcolor: (th) =>
                      isUser
                        ? alpha(th.palette.primary.main, 0.12)
                        : th.palette.background.paper,
                    color: m.failed ? "error.main" : "text.primary",
                  }}
                >
                  {m.text}
                </Box>

                {m.failed && m.retryOf && (
                  <Chip
                    label="↻ Try again"
                    size="small"
                    variant="outlined"
                    onClick={() => ask(m.retryOf)}
                    sx={{ alignSelf: "flex-start" }}
                  />
                )}

                {m.sources?.length > 0 && (
                  <Box
                    component="details"
                    sx={{
                      fontSize: 12,
                      color: "text.secondary",
                      "& summary": { cursor: "pointer" },
                    }}
                  >
                    <summary>{m.sources.length} matched sections</summary>
                    <Stack spacing={0.5} sx={{ pt: 0.75 }}>
                      {m.sources.map((s, j) => (
                        <Box
                          key={j}
                          sx={{
                            px: 1,
                            py: 0.75,
                            borderRadius: 1,
                            bgcolor: (th) => alpha(th.palette.text.primary, 0.04),
                            whiteSpace: "pre-wrap",
                            overflowWrap: "anywhere",
                          }}
                        >
                          {s.text}
                        </Box>
                      ))}
                    </Stack>
                  </Box>
                )}
              </Stack>
            </Stack>
          );
        })}

        {loading && (
          <Stack direction="row" spacing={1.25} sx={{ flexShrink: 0 }}>
            <Box
              sx={{
                flexShrink: 0,
                width: 28,
                height: 28,
                mt: 0.25,
                borderRadius: "50%",
                display: "grid",
                placeItems: "center",
                fontSize: 11,
                fontWeight: 600,
                color: "text.secondary",
                bgcolor: (th) => alpha(th.palette.text.primary, 0.07),
              }}
            >
              AI
            </Box>
            <Box
              sx={{
                display: "flex",
                gap: 0.5,
                px: 1.75,
                py: 1.5,
                border: 1,
                borderColor: "divider",
                borderRadius: 2,
                borderTopLeftRadius: 4,
                bgcolor: "background.paper",
                "@keyframes blink": {
                  "0%,80%,100%": { opacity: 0.2 },
                  "40%": { opacity: 1 },
                },
              }}
            >
              {[0, 1, 2].map((d) => (
                <Box
                  key={d}
                  sx={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    bgcolor: "text.secondary",
                    animation: "blink 1.4s infinite both",
                    animationDelay: `${d * 0.16}s`,
                  }}
                />
              ))}
            </Box>
          </Stack>
        )}
      </Box>

      <Stack
        direction="row"
        spacing={1}
        alignItems="flex-end"
        sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={4}
          size="small"
          placeholder="Ask a question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
          sx={{ "& .MuiOutlinedInput-root": { borderRadius: 5, px: 1 } }}
        />
        <IconButton
          onClick={() => ask()}
          disabled={loading || !question.trim()}
          sx={{
            width: 40,
            height: 40,
            color: "primary.contrastText",
            bgcolor: "primary.main",
            "&:hover": { bgcolor: "primary.dark" },
            "&.Mui-disabled": { bgcolor: (th) => alpha(th.palette.text.primary, 0.1) },
          }}
        >
          {loading ? (
            <CircularProgress size={16} color="inherit" />
          ) : (
            <Box component="span" sx={{ fontSize: 15, lineHeight: 1 }}>➤</Box>
          )}
        </IconButton>
      </Stack>
    </Paper>
  );
}

/* ------------------------------------------------------------------ *
 * Single resume result
 * ------------------------------------------------------------------ */

function ResumeResult({ resume, chartOptions, palette, onDownload, notify }) {
  const [downloading, setDownloading] = useState(false);

  const matched = resume.matched_skills?.length || 0;
  const missing = resume.missing_skills?.length || 0;

  const pieData = {
    labels: ["Matched", "Missing"],
    datasets: [
      {
        data: [matched, missing],
        backgroundColor: [palette.success, palette.danger],
        borderColor: palette.paper,
        borderWidth: 2,
      },
    ],
  };

  const barData = {
    labels: ["Matched", "Missing"],
    datasets: [
      {
        label: "Skills",
        data: [matched, missing],
        backgroundColor: [palette.accent, palette.danger],
        borderRadius: 6,
        barThickness: 46,
      },
    ],
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await onDownload(resume);
    } finally {
      setDownloading(false);
    }
  };

  const roadmap = resume.learning_roadmap;
  const hasRoadmap =
    roadmap && typeof roadmap === "object" && Object.keys(roadmap).length > 0;

  return (
    <Box sx={{ mb: 6 }}>
      {/* Header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={2}
        sx={{ mb: 2.5 }}
      >
        <Box>
          <Typography variant="h1">{resume.filename}</Typography>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.75 }}>
            <Chip
              size="small"
              label={`${resume.experience_level || "Unknown"} level`}
              variant="outlined"
            />
            {resume.resume_id && (
              <Typography
                variant="caption"
                sx={{ fontFamily: MONO, color: "text.secondary" }}
              >
                {resume.resume_id}
              </Typography>
            )}
          </Stack>
        </Box>

        <Button
          variant="outlined"
          startIcon={
            downloading ? (
              <CircularProgress size={15} color="inherit" />
            ) : (
              <DownloadIcon />
            )
          }
          onClick={handleDownload}
          disabled={downloading}
        >
          Download report
        </Button>
      </Stack>

      {/* Score rails */}
      <Box
        sx={{
          display: "grid",
          gap: 1.5,
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            md: "repeat(4, 1fr)",
          },
          mb: 3,
        }}
      >
        <ScoreRail label="ATS score" value={resume.score} />
        <ScoreRail
          label="AI resume score"
          value={resume.ml_score}
          caption={resume.ml_confidence}
        />
        <ScoreRail
          label="Job fit prediction"
          value={resume.job_fit_score}
          caption={resume.selection_probability}
        />
        <ScoreRail
          label="Semantic match"
          value={resume.semantic_similarity}
          caption="Resume against JD"
        />
      </Box>

      {/* Charts + skills */}
      <Box
        sx={{
          display: "grid",
          gap: 1.5,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          mb: 1.5,
        }}
      >
        <Paper sx={{ p: 2.5, borderRadius: 2.5 }}>
          <SectionLabel>Skill coverage</SectionLabel>
          <Box sx={{ height: 240 }}>
            <Pie data={pieData} options={chartOptions.pie} />
          </Box>
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: 2.5 }}>
          <SectionLabel>Matched against missing</SectionLabel>
          <Box sx={{ height: 240 }}>
            <Bar data={barData} options={chartOptions.bar} />
          </Box>
        </Paper>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 1.5,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          mb: 1.5,
        }}
      >
        <Paper sx={{ p: 2.5, borderRadius: 2.5 }}>
          <SectionLabel>Matched skills ({matched})</SectionLabel>
          {matched === 0 ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              No overlap found with the job description.
            </Typography>
          ) : (
            <Stack direction="row" flexWrap="wrap" gap={0.75}>
              {resume.matched_skills.map((s, i) => (
                <Chip
                  key={i}
                  label={s}
                  size="small"
                  sx={{
                    bgcolor: (th) => alpha(th.palette.success.main, 0.14),
                    color: "success.main",
                  }}
                />
              ))}
            </Stack>
          )}
        </Paper>

        <Paper sx={{ p: 2.5, borderRadius: 2.5 }}>
          <SectionLabel>Missing skills ({missing})</SectionLabel>
          {missing === 0 ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Every required skill is covered.
            </Typography>
          ) : (
            <Stack direction="row" flexWrap="wrap" gap={0.75}>
              {resume.missing_skills.map((s, i) => (
                <Chip
                  key={i}
                  label={s}
                  size="small"
                  sx={{
                    bgcolor: (th) => alpha(th.palette.error.main, 0.14),
                    color: "error.main",
                  }}
                />
              ))}
            </Stack>
          )}
        </Paper>
      </Box>

      {/* Recommendations */}
      <Paper sx={{ p: 2.5, borderRadius: 2.5, mb: 1.5 }}>
        <SectionLabel>What to fix</SectionLabel>
        {resume.suggestions?.length ? (
          <Stack spacing={1.25}>
            {resume.suggestions.map((s, i) => (
              <Stack key={i} direction="row" spacing={1.25} alignItems="flex-start">
                <ArrowForwardIcon
                  sx={{ fontSize: 15, mt: 0.4, color: "primary.main", flexShrink: 0 }}
                />
                <Typography variant="body1">{s}</Typography>
              </Stack>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No recommendations returned.
          </Typography>
        )}
      </Paper>

      {/* Action verbs */}
      <Paper sx={{ p: 2.5, borderRadius: 2.5, mb: 1.5 }}>
        <SectionLabel>Stronger phrasing</SectionLabel>
        {resume.action_verb_suggestions?.length ? (
          <Stack divider={<Divider flexItem />} spacing={2}>
            {resume.action_verb_suggestions.map((item, i) => (
              <Box key={i}>
                <Typography variant="body1" sx={{ mb: 0.75 }}>
                  {item.line}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ color: "text.secondary", display: "block", mb: 1 }}
                >
                  Weak phrase:{" "}
                  <Box component="span" sx={{ fontFamily: MONO, color: "warning.main" }}>
                    {item.weak_verb}
                  </Box>
                </Typography>
                <Stack direction="row" flexWrap="wrap" gap={0.75}>
                  {item.suggestions?.map((v, idx) => (
                    <Chip key={idx} label={v} size="small" variant="outlined" />
                  ))}
                </Stack>
              </Box>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            This resume uses few weak verbs, so there is nothing to swap.
          </Typography>
        )}
      </Paper>

      {/* Roadmap */}
      <Paper sx={{ p: 2.5, borderRadius: 2.5, mb: 1.5 }}>
        <SectionLabel>Learning roadmap</SectionLabel>
        {hasRoadmap ? (
          <Stack spacing={2.5}>
            {Object.entries(roadmap).map(([skill, data], i) => (
              <Box key={i}>
                <Typography variant="h3" sx={{ mb: 1 }}>
                  {data.display_name || skill}
                </Typography>
                <Stack spacing={0.75}>
                  {data.resources?.map((res, idx) => (
                    <Stack
                      key={idx}
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      spacing={2}
                      sx={{
                        px: 1.75,
                        py: 1.25,
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 2,
                      }}
                    >
                      <Typography variant="body2">{res.name}</Typography>
                      <Button
                        size="small"
                        variant="text"
                        endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
                        component={Link}
                        href={res.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ flexShrink: 0 }}
                      >
                        Open
                      </Button>
                    </Stack>
                  ))}
                </Stack>
              </Box>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No gaps to close, so no roadmap was generated.
          </Typography>
        )}
      </Paper>

      <ResumeChat resumeId={resume.resume_id} notify={notify} />
    </Box>
  );
}

/* ------------------------------------------------------------------ *
 * Login
 * ------------------------------------------------------------------ */

function LoginView({ onLogin, busy, error }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);

  const submit = () => {
    if (!username.trim() || !password) return;
    onLogin(username.trim(), password);
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 2,
        bgcolor: "background.default",
      }}
    >
      <Paper sx={{ p: 4, borderRadius: 3, width: "100%", maxWidth: 400 }}>
        <Typography
          variant="caption"
          sx={{
            fontFamily: MONO,
            color: "primary.main",
            textTransform: "uppercase",
            fontWeight: 500,
          }}
        >
          Resume Analyzer
        </Typography>
        <Typography variant="h1" sx={{ mt: 1, mb: 0.5 }}>
          Sign in
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
          Score resumes against a job description and see what is missing.
        </Typography>

        <Stack spacing={1.75}>
          <TextField
            id="username"
            label="Username"
            fullWidth
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <TextField
            id="password"
            label="Password"
            fullWidth
            autoComplete="current-password"
            type={show ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => setShow((s) => !s)}
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? (
                      <VisibilityOffIcon fontSize="small" />
                    ) : (
                      <VisibilityIcon fontSize="small" />
                    )}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {error && (
            <Alert severity="error" sx={{ borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <Button
            variant="contained"
            size="large"
            onClick={submit}
            disabled={busy || !username.trim() || !password}
          >
            {busy ? <CircularProgress size={18} color="inherit" /> : "Sign in"}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}

/* ------------------------------------------------------------------ *
 * App
 * ------------------------------------------------------------------ */

export default function App() {
  useFontLoader();

  const [darkMode, setDarkMode] = useState(true);
  const theme = useMemo(() => buildTheme(darkMode ? "dark" : "light"), [darkMode]);
  const t = tokens[darkMode ? "dark" : "light"];

  const [loggedIn, setLoggedIn] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");

  const [files, setFiles] = useState([]);
  const [jobDesc, setJobDesc] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const [fakeResults, setFakeResults] = useState([]);
  const [fakeLoading, setFakeLoading] = useState(false);

  const [toast, setToast] = useState(null);
  const fileInputRef = useRef(null);

  const notify = useCallback(
    (message, severity = "info") => setToast({ message, severity }),
    []
  );

  /* Chart options derived from the theme, so both modes stay readable */
  const chartOptions = useMemo(() => {
    const text = t.muted;
    const grid = alpha(t.text, 0.08);
    const base = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: text,
            usePointStyle: true,
            pointStyle: "circle",
            boxWidth: 8,
            padding: 16,
            font: { family: SANS, size: 12 },
          },
        },
        tooltip: {
          backgroundColor: t.paper,
          titleColor: t.text,
          bodyColor: t.muted,
          borderColor: t.border,
          borderWidth: 1,
          padding: 10,
          displayColors: false,
        },
      },
    };

    return {
      pie: base,
      bar: {
        ...base,
        plugins: { ...base.plugins, legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: text, precision: 0, font: { family: MONO, size: 11 } },
            grid: { color: grid, drawBorder: false },
          },
          x: {
            ticks: { color: text, font: { family: SANS, size: 12 } },
            grid: { display: false },
          },
        },
      },
    };
  }, [t]);

  const chartPalette = {
    accent: t.accent,
    success: t.success,
    danger: t.danger,
    paper: t.paper,
  };

  /* ---------------- actions ---------------- */

  const handleLogin = async (username, password) => {
    setAuthBusy(true);
    setAuthError("");
    try {
      await api.post("/login", { username, password });
      setLoggedIn(true);
    } catch (err) {
      setAuthError(
        err.response?.status === 401
          ? "That username and password do not match."
          : "Cannot reach the server. Check the backend is running."
      );
    } finally {
      setAuthBusy(false);
    }
  };

  const handleLogout = () => {
    setLoggedIn(false);
    setFiles([]);
    setJobDesc("");
    setResults([]);
    setFakeResults([]);
  };

  const handleAnalyze = async () => {
    if (!files.length) return notify("Add at least one resume first.", "warning");
    if (!jobDesc.trim())
      return notify("Paste the job description first.", "warning");

    const formData = new FormData();
    files.forEach((f) => formData.append("resumes", f));
    formData.append("job_description", jobDesc);

    setLoading(true);
    setFakeResults([]);
    try {
      const res = await api.post("/compare", formData);
      const list = res.data?.comparison || [];
      setResults(list);
      notify(`Analyzed ${list.length} resume${list.length === 1 ? "" : "s"}.`, "success");
    } catch (err) {
      notify(
        err.response?.data?.error || "Analysis failed. Check the server logs.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFakeDetection = async () => {
    if (!files.length) return notify("Add at least one resume first.", "warning");

    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));

    setFakeLoading(true);
    try {
      const res = await api.post("/detect_fake_pdf", formData);
      setFakeResults(res.data?.results || []);
    } catch (err) {
      notify("Fake detection failed. Check the server logs.", "error");
    } finally {
      setFakeLoading(false);
    }
  };

  const handleReset = () => {
    setResults([]);
    setFakeResults([]);
    setFiles([]);
    setJobDesc("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleDownload = async (resume) => {
    let url;
    try {
      const res = await api.post("/download", resume, { responseType: "blob" });
      url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${resume.filename}_report.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      notify("Report downloaded.", "success");
    } catch (err) {
      notify("Could not generate the report.", "error");
    } finally {
      if (url) setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    }
  };

  /* ---------------- render ---------------- */

  if (!loggedIn) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LoginView onLogin={handleLogin} busy={authBusy} error={authError} />
      </ThemeProvider>
    );
  }

  const busy = loading || fakeLoading;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
        <AppBar position="sticky">
          {busy && (
            <LinearProgress
              sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2 }}
            />
          )}
          <Toolbar sx={{ gap: 2 }}>
            <Stack direction="row" alignItems="center" spacing={1.25} sx={{ flex: 1 }}>
              <Box
                sx={{
                  width: 26,
                  height: 26,
                  borderRadius: 1.5,
                  bgcolor: "primary.main",
                  display: "grid",
                  placeItems: "center",
                  fontFamily: MONO,
                  fontSize: 13,
                  fontWeight: 500,
                  color: darkMode ? "#0D0F0E" : "#FFFFFF",
                }}
              >
                R
              </Box>
              <Typography variant="h3">Resume Analyzer</Typography>
            </Stack>

            <MuiTooltip title={darkMode ? "Light mode" : "Dark mode"}>
              <IconButton onClick={() => setDarkMode((d) => !d)} size="small">
                {darkMode ? (
                  <LightModeOutlinedIcon fontSize="small" />
                ) : (
                  <DarkModeOutlinedIcon fontSize="small" />
                )}
              </IconButton>
            </MuiTooltip>

            <Button
              size="small"
              variant="text"
              color="inherit"
              startIcon={<LogoutIcon sx={{ fontSize: 16 }} />}
              onClick={handleLogout}
            >
              Sign out
            </Button>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ py: 4 }}>
          {/* Input panel */}
          <Paper sx={{ p: 3, borderRadius: 3, mb: 4 }}>
            <Box
              sx={{
                display: "grid",
                gap: 2.5,
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              }}
            >
              <Box>
                <SectionLabel>Resumes</SectionLabel>
                <Dropzone
                  files={files}
                  onChange={setFiles}
                  inputRef={fileInputRef}
                />
              </Box>

              <Box>
                <SectionLabel>Job description</SectionLabel>
                <TextField
                  id="jd-input"
                  multiline
                  rows={6}
                  fullWidth
                  placeholder="Paste the full job description, including required skills"
                  value={jobDesc}
                  onChange={(e) => setJobDesc(e.target.value)}
                />
              </Box>
            </Box>

            <Divider sx={{ my: 2.5 }} />

            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.25}
              alignItems={{ sm: "center" }}
            >
              <Button
                id="analyze-btn"
                variant="contained"
                onClick={handleAnalyze}
                disabled={busy}
                startIcon={
                  loading ? <CircularProgress size={15} color="inherit" /> : null
                }
              >
                {loading ? "Analyzing" : "Analyze resumes"}
              </Button>

              <Button
                variant="outlined"
                onClick={handleFakeDetection}
                disabled={busy}
                startIcon={<ShieldOutlinedIcon sx={{ fontSize: 17 }} />}
              >
                {fakeLoading ? "Checking" : "Check authenticity"}
              </Button>

              <Button
                variant="text"
                href="/bulk"
                startIcon={<LayersOutlinedIcon sx={{ fontSize: 17 }} />}
              >
                Bulk analyzer
              </Button>

              <Box sx={{ flex: 1 }} />

              <Button
                variant="text"
                color="inherit"
                onClick={handleReset}
                startIcon={<RestartAltIcon sx={{ fontSize: 17 }} />}
              >
                Clear
              </Button>
            </Stack>
          </Paper>

          {/* Authenticity results */}
          {fakeResults.length > 0 && (
            <Paper sx={{ p: 2.5, borderRadius: 3, mb: 4 }}>
              <SectionLabel>Authenticity check</SectionLabel>
              <Stack spacing={0.75}>
                {fakeResults.map((r, i) => {
                  const suspicious = String(r.result || "")
                    .toLowerCase()
                    .includes("fake");
                  return (
                    <Stack
                      key={i}
                      direction="row"
                      alignItems="center"
                      spacing={1.5}
                      sx={{
                        px: 1.75,
                        py: 1.25,
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 2,
                      }}
                    >
                      {/* {suspicious ? (
                        <ErrorOutlineIcon sx={{ fontSize: 18, color: "error.main" }} />
                      ) : (
                        // <CheckCircleOutlineIcon
                        //   sx={{ fontSize: 18, color: "success.main" }}
                        // />
                      )} */}
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {r.filename}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{ fontFamily: MONO, color: "text.secondary" }}
                      >
                        {num(r.score).toFixed(2)}
                      </Typography>
                      <Chip
                        size="small"
                        label={r.result}
                        sx={{
                          bgcolor: (th) =>
                            alpha(
                              suspicious ? th.palette.error.main : th.palette.success.main,
                              0.14
                            ),
                          color: suspicious ? "error.main" : "success.main",
                        }}
                      />
                    </Stack>
                  );
                })}
              </Stack>
            </Paper>
          )}

          {/* Analysis results */}
          {loading && results.length === 0 && (
            <Stack spacing={1.5}>
              <Skeleton variant="rounded" height={40} width={260} />
              <Box
                sx={{
                  display: "grid",
                  gap: 1.5,
                  gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
                }}
              >
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} variant="rounded" height={128} />
                ))}
              </Box>
              <Skeleton variant="rounded" height={300} />
            </Stack>
          )}

          {!loading && results.length === 0 && fakeResults.length === 0 && (
            <Paper sx={{ borderRadius: 3 }}>
              <EmptyState
                icon={<DescriptionOutlinedIcon sx={{ fontSize: 40 }} />}
                title="No analysis yet"
                body="Add one or more resumes and paste a job description, then run the analysis to see scores, skill gaps, and a learning roadmap."
              />
            </Paper>
          )}

          {results.length > 0 && (
            <Box id="results">
              {results.map((resume, i) => (
                <ResumeResult
                  key={resume.resume_id || `${resume.filename}-${i}`}
                  resume={resume}
                  chartOptions={chartOptions}
                  palette={chartPalette}
                  onDownload={handleDownload}
                  notify={notify}
                />
              ))}
            </Box>
          )}
        </Container>
      </Box>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={4500}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={toast?.severity || "info"}
          variant="filled"
          onClose={() => setToast(null)}
          sx={{ borderRadius: 2 }}
        >
          {toast?.message}
        </Alert>
      </Snackbar>
    </ThemeProvider>
  );
}