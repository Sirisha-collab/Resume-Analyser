import React, { useState } from "react";
import axios from "axios";

import {
  Container,
  Typography,
  Card,
  Button,
  CircularProgress,
  TextField,
  Grid,
  Chip
} from "@mui/material";

import "../App.css";

function BulkResume() {

  const [mode, setMode] = useState("bulk"); 
  // "bulk" OR "single"

  const [files, setFiles] = useState([]);
  const [jobDesc, setJobDesc] = useState("");
  const [results, setResults] = useState([]);
  const [singleResult, setSingleResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // ---------------- SINGLE ANALYSIS ----------------
  const handleSingleAnalyze = async () => {

    if (!files.length || !jobDesc) {
      return alert("Upload 1 resume + Job Description");
    }

    const formData = new FormData();

    formData.append("resume", files[0]);
    formData.append("job_description", jobDesc);

    try {

      setLoading(true);

      const res = await axios.post(
        "http://127.0.0.1:5000/analyze",
        formData
      );

      setSingleResult(res.data);
      setResults([]);

    } catch {

      alert("Single analysis failed");

    } finally {

      setLoading(false);

    }
  };

  // ---------------- BULK ANALYSIS ----------------
  const handleBulkAnalyze = async () => {

    if (!files.length || !jobDesc) {
      return alert("Upload resumes + Job Description");
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

      const sorted = res.data.comparison.sort(
        (a, b) =>
          b.job_fit_score - a.job_fit_score
      );

      setResults(sorted);
      setSingleResult(null);

    } catch {

      alert("Bulk analysis failed");

    } finally {

      setLoading(false);

    }
  };

  // ---------------- TOP 5 SHORTLIST ----------------
  const top5 = results.slice(0, 5);

  return (

    <div className="app-bg">

      <Container className="main-container">

        <Typography variant="h3" className="bulk-title">
          Resume Analyzer (Single + Bulk Mode)
        </Typography>

        {/* MODE SWITCH */}
        <div style={{ textAlign: "center", marginBottom: 20 }}>

          <Button
            variant={mode === "single" ? "contained" : "outlined"}
            onClick={() => setMode("single")}
            style={{ marginRight: 10 }}
          >
            Single Resume
          </Button>

          <Button
            variant={mode === "bulk" ? "contained" : "outlined"}
            onClick={() => setMode("bulk")}
          >
            Bulk Resume
          </Button>

        </div>

        {/* UPLOAD */}
        <Card className="glass-card upload-card">

          <input
            type="file"
            multiple
            onChange={(e) =>
              setFiles(Array.from(e.target.files))
            }
          />

          <Typography className="file-count">
            {files.length} file(s) selected
          </Typography>

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

          {/* ACTION BUTTONS */}
          {mode === "single" ? (

            <Button
              variant="contained"
              onClick={handleSingleAnalyze}
            >
              Analyze Single Resume
            </Button>

          ) : (

            <Button
              variant="contained"
              onClick={handleBulkAnalyze}
            >
              Analyze Bulk Resumes
            </Button>

          )}

          {loading && <CircularProgress />}

        </Card>

        {/* SINGLE RESULT UI */}
        {singleResult && (
          <Card className="glass-card" style={{ marginTop: 20 }}>

            <Typography variant="h5">
              Single Resume Result
            </Typography>

            <Typography>
              ATS Score: {singleResult.score}%
            </Typography>

            <Typography>
              ML Score: {singleResult.ml_score}%
            </Typography>

            <Typography>
              Job Fit: {singleResult.job_fit_score}%
            </Typography>

          </Card>
        )}

        {/* BULK RESULTS */}
        {results.length > 0 && (

          <>

            {/* TOP 5 SHORTLIST */}
            <Typography variant="h4" style={{ marginTop: 30 }}>
              🏆 Top 5 Shortlisted Candidates
            </Typography>

            <Grid container spacing={3}>

              {top5.map((r, i) => (

                <Grid item xs={12} md={4} key={i}>

                  <Card className="glass-card">

                    <Typography variant="h6">
                      #{i + 1} {r.filename}
                    </Typography>

                    <Typography>
                      Job Fit: {r.job_fit_score}%
                    </Typography>

                    <Typography>
                      Recommendation:
                    </Typography>

                    <Chip
                      label={r.recommendation}
                      color="success"
                    />

                  </Card>

                </Grid>

              ))}

            </Grid>

            {/* FULL RANKING */}
            <Typography variant="h4" style={{ marginTop: 40 }}>
              Full Ranking
            </Typography>

            <Grid container spacing={3}>

              {results.map((r, i) => (

                <Grid item xs={12} md={6} key={i}>

                  <Card className="glass-card">

                    <Typography>
                      #{i + 1} {r.filename}
                    </Typography>

                    <Typography>
                      ATS: {r.score}% | ML: {r.ml_score}% | Fit: {r.job_fit_score}%
                    </Typography>

                  </Card>

                </Grid>

              ))}

            </Grid>

          </>
        )}

      </Container>

    </div>
  );
}

export default BulkResume;