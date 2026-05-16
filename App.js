import React, { useState, useRef } from "react";
import axios from "axios";

import {
  Bar,
  Pie
} from "react-chartjs-2";

import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  ArcElement,
  Tooltip,
  Legend
} from "chart.js";

import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Button,
  TextField,
  CircularProgress,
  Card,
  Chip,
  Grid,
  Switch,
  FormControlLabel
} from "@mui/material";

import {
  createTheme,
  ThemeProvider
} from "@mui/material/styles";

import "./App.css";

ChartJS.register(
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

function App() {

  const [files, setFiles] = useState([]);
  const [jobDesc, setJobDesc] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const [loggedIn, setLoggedIn] = useState(false);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [darkMode, setDarkMode] = useState(true);

  const fileInputRef = useRef(null);

  const theme = createTheme({
    palette: {
      mode: darkMode ? "dark" : "light"
    }
  });

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,

    plugins: {
      legend: {
        labels: {
          color: "#ffffff"
        }
      }
    },

    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: "#ffffff"
        },
        grid: {
          color: "rgba(255,255,255,0.08)"
        }
      },

      x: {
        ticks: {
          color: "#ffffff"
        },
        grid: {
          color: "rgba(255,255,255,0.08)"
        }
      }
    }
  };

  // LOGIN
  const handleLogin = async () => {

    try {

      await axios.post(
        "http://127.0.0.1:5000/login",
        {
          username,
          password
        }
      );

      setLoggedIn(true);

    } catch {

      alert("Login Failed");

    }
  };

  // ANALYZE
  const handleSubmit = async () => {

    if (!files.length || !jobDesc) {
      return alert("Upload resumes & job description");
    }

    const formData = new FormData();

    files.forEach((f) => {
      formData.append("resumes", f);
    });

    formData.append("job_description", jobDesc);

    try {

      setLoading(true);

      const res = await axios.post(
        "http://127.0.0.1:5000/compare",
        formData
      );

      setResults(res.data.comparison);

    } catch {

      alert("Error analyzing resumes");

    } finally {

      setLoading(false);

    }
  };

  // RESET
  const handleNewAnalysis = () => {

    setResults([]);
    setFiles([]);
    setJobDesc("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // DOWNLOAD
  const handleDownload = async (resume) => {

    const res = await axios.post(
      "http://127.0.0.1:5000/download",
      resume,
      {
        responseType: "blob"
      }
    );

    const url = window.URL.createObjectURL(
      new Blob([res.data])
    );

    const link = document.createElement("a");

    link.href = url;

    link.setAttribute(
      "download",
      `${resume.filename}_report.pdf`
    );

    document.body.appendChild(link);

    link.click();
  };

  // LOGIN PAGE
  if (!loggedIn) {

    return (

      <ThemeProvider theme={theme}>

        <div className="login-page">

          <Card className="glass-card login-card">

            <Typography
              variant="h4"
              className="login-title"
            >
              AI Resume Analyzer
            </Typography>

            <Typography className="login-subtitle">
              Login to continue
            </Typography>

            <TextField
              label="Username"
              onChange={(e) =>
                setUsername(e.target.value)
              }
            />

            <TextField
              label="Password"
              type="password"
              onChange={(e) =>
                setPassword(e.target.value)
              }
            />

            <Button
              variant="contained"
              onClick={handleLogin}
            >
              Login
            </Button>

          </Card>

        </div>

      </ThemeProvider>
    );
  }

  // MAIN UI
  return (

    <ThemeProvider theme={theme}>

      <div className="app-bg">

        {/* NAVBAR */}

        <AppBar
          position="static"
          className="glass-nav"
        >

          <Toolbar className="toolbar-custom">

            <Typography
              variant="h5"
              className="logo-text"
            >
              AI Resume Analyzer
            </Typography>

            <div className="nav-right">

              <FormControlLabel
                className="dark-toggle"
                control={
                  <Switch
                    checked={darkMode}
                    onChange={() =>
                      setDarkMode(!darkMode)
                    }
                  />
                }
                label="Dark Mode"
                labelPlacement="start"
              />

            </div>

          </Toolbar>

        </AppBar>

        <Container className="main-container">

          {/* UPLOAD */}

          <Card className="glass-card upload-card">

            <input
              type="file"
              multiple
              ref={fileInputRef}
              onChange={(e) =>
                setFiles(Array.from(e.target.files))
              }
            />

            <TextField
              multiline
              rows={5}
              fullWidth
              placeholder="Paste Job Description"
              value={jobDesc}
              onChange={(e) =>
                setJobDesc(e.target.value)
              }
            />

            <div className="button-group">

              <Button
                variant="contained"
                onClick={handleSubmit}
                className="analyze-btn"
              >
                Analyze
              </Button>

              <Button
                variant="outlined"
                onClick={handleNewAnalysis}
                className="new-analysis-btn"
              >
                New Resume Analysis
              </Button>

            </div>

            {loading && (
              <div className="loader-wrapper">
                <CircularProgress />
              </div>
            )}

          </Card>

          {/* RESULTS */}

          {results.length > 0 && (

            <>

              {results.map((resume, index) => {

                const barData = {
                  labels: ["Matched", "Missing"],

                  datasets: [
                    {
                      label: "Skills",

                      data: [
                        resume.matched_skills.length,
                        resume.missing_skills.length
                      ],

                      backgroundColor: [
                        "#4fa3ff",
                        "#ff5c7a"
                      ],

                      borderRadius: 10
                    }
                  ]
                };

                const pieData = {
                  labels: [
                    "Matched",
                    "Missing"
                  ],

                  datasets: [
                    {
                      data: [
                        resume.matched_skills.length,
                        resume.missing_skills.length
                      ],

                      backgroundColor: [
                        "#8dd65f",
                        "#ff5c7a"
                      ],

                      borderWidth: 2
                    }
                  ]
                };

                return (

                  <div
                    key={index}
                    className="resume-wrapper"
                  >

                    {/* HEADER */}

                    <div className="resume-header">

                      <Typography
                        variant="h4"
                        className="resume-title"
                      >
                        {resume.filename}
                      </Typography>

                      <Typography className="experience-text">
                        Experience:
                        {" "}
                        {resume.experience_level}
                      </Typography>

                    </div>

                    {/* SCORE CARDS */}

                    <Grid
                      container
                      spacing={4}
                      className="section-grid"
                    >

                      <Grid item xs={12} sm={6} md={3}>

                        <Card className="glass-card score-card">

                          <div className="score-icon">
                            📄
                          </div>

                          <div>

                            <Typography className="score-label">
                              ATS Score
                            </Typography>

                            <Typography className="score-value">
                              {resume.score}%
                            </Typography>

                          </div>

                        </Card>

                      </Grid>

                      <Grid item xs={12} sm={6} md={3}>

                        <Card className="glass-card score-card">

                          <div className="score-icon ai-icon">
                            🧠
                          </div>

                          <div>

                            <Typography className="score-label">
                              AI Resume Score
                            </Typography>

                            <Typography className="score-value">
                              {resume.ml_score}%
                            </Typography>

                            <Typography className="small-text">
                              {resume.ml_confidence}
                            </Typography>

                          </div>

                        </Card>

                      </Grid>

                      <Grid item xs={12} sm={6} md={3}>

                        <Card className="glass-card score-card">

                          <div className="score-icon job-icon">
                            💼
                          </div>

                          <div>

                            <Typography className="score-label">
                              Job Prediction
                            </Typography>

                            <Typography className="score-value">
                              {resume.job_fit_score || 0}%
                            </Typography>

                            <Typography className="small-text">
                              {resume.selection_probability || "N/A"}
                            </Typography>

                          </div>

                        </Card>

                      </Grid>

                      <Grid item xs={12} sm={6} md={3}>

                        <Card className="glass-card score-card">

                          <div className="score-icon semantic-icon">
                            🎯
                          </div>

                          <div>

                            <Typography className="score-label">
                              Semantic Match
                            </Typography>

                            <Typography className="score-value">
                              {resume.semantic_similarity || 0}%
                            </Typography>

                            <Typography className="small-text">
                              Resume ↔ JD
                            </Typography>

                          </div>

                        </Card>

                      </Grid>

                    </Grid>

                    {/* ANALYSIS TITLE */}

                    <div className="analysis-title">
                      ✦ ANALYSIS INSIGHTS ✦
                    </div>

                    {/* CHARTS */}

                    <Grid
                      container
                      spacing={4}
                      className="chart-grid"
                    >

                      <Grid item xs={12} md={6}>

                        <Card className="glass-card chart-card">

                          <Typography className="section-title">
                            Skills Match Overview
                          </Typography>

                          <div className="chart-wrapper">

                            <Pie
                              data={pieData}
                              options={chartOptions}
                            />

                          </div>

                        </Card>

                      </Grid>

                      <Grid item xs={12} md={6}>

                        <Card className="glass-card chart-card">

                          <Typography className="section-title">
                            Top Skills Analysis
                          </Typography>

                          <div className="chart-wrapper">

                            <Bar
                              data={barData}
                              options={chartOptions}
                            />

                          </div>

                        </Card>

                      </Grid>

                    </Grid>

                    {/* SKILLS */}

                    <Grid
                      container
                      spacing={4}
                      className="section-grid"
                    >

                      <Grid item xs={12} md={6}>

                        <Card className="glass-card skill-card">

                          <Typography className="section-title">
                            Matched Skills
                          </Typography>

                          <div className="chip-container">

                            {resume.matched_skills.map((s, i) => (

                              <Chip
                                key={i}
                                label={s}
                                color="success"
                              />

                            ))}

                          </div>

                        </Card>

                      </Grid>

                      <Grid item xs={12} md={6}>

                        <Card className="glass-card skill-card">

                          <Typography className="section-title">
                            Missing Skills
                          </Typography>

                          <div className="chip-container">

                            {resume.missing_skills.map((s, i) => (

                              <Chip
                                key={i}
                                label={s}
                                color="error"
                              />

                            ))}

                          </div>

                        </Card>

                      </Grid>

                    </Grid>

                    {/* RECOMMENDATIONS */}

                    <Card className="glass-card recommendation-card">

                      <Typography className="section-title">
                        AI Recommendations
                      </Typography>

                      {resume.suggestions.map((s, i) => (

                        <Typography
                          key={i}
                          className="recommendation-item"
                        >
                          • {s}
                        </Typography>

                      ))}

                    </Card>

                    {/* DOWNLOAD */}

                    <div className="download-section">

                      <Button
                        variant="contained"
                        onClick={() =>
                          handleDownload(resume)
                        }
                      >
                        Download PDF
                      </Button>

                    </div>

                  </div>
                );
              })}

            </>

          )}

        </Container>

      </div>

    </ThemeProvider>
  );
}

export default App;