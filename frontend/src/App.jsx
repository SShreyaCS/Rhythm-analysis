import { useEffect, useMemo, useState } from 'react';
import './App.css';
import LotusDivider from './components/LotusDivider';
import {
  ChevronLeftIcon,
  InfoIcon,
  UploadIcon,
} from './components/Icons';

const ACCEPTED_TYPES = '.mp4,.avi,.mov,.mkv';

/** Empty in dev (Vite proxy). Set VITE_API_URL on Render static site build. */
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const isSubPage = isLoading || Boolean(result);

  const formattedScore = useMemo(() => {
    if (!result || typeof result.rhythm_score !== 'number') {
      return '-';
    }
    return `${Math.round(result.rhythm_score * 100)}%`;
  }, [result]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl('');
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  const handleAnalyze = async (event) => {
    event.preventDefault();
    if (!file) {
      setError('Please select a video file first.');
      return;
    }

    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: formData,
      });

      let data = {};
      try {
        data = await response.json();
      } catch {
        data = {};
      }

      if (!response.ok) {
        if (response.status === 502) {
          throw new Error(
            'The server stopped or timed out while analyzing. Use a shorter video (under 30 seconds) or upgrade your Render API plan.'
          );
        }
        const detail = data?.detail;
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
        throw new Error(message || `Analysis failed (${response.status}).`);
      }

      setResult(data);
    } catch (err) {
      const msg = err?.message || '';
      if (msg === 'Failed to fetch' || msg.includes('NetworkError')) {
        setError(
          'Cannot reach the analysis API. Check that the backend is live, VITE_API_URL is correct, and ALLOWED_ORIGINS includes this site.'
        );
      } else {
        setError(msg || 'Something went wrong while analyzing the video.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectFile = (event) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setError('');
    setResult(null);
  };

  const handleBack = () => {
    setIsLoading(false);
    setResult(null);
    setError('');
  };

  const statusText = result
    ? result.valid_video
      ? `Synchronization: ${formattedScore}`
      : 'Video not valid for Bharatanatyam scoring'
    : 'Synchronization: --';

  return (
    <div className="app-shell">
      <div className="mandala-bg" aria-hidden="true">
        <div className="top-decor" />
        <div className="side-decor side-decor-left" />
        <div className="side-decor side-decor-right" />
      </div>

      <header className="site-header">
        {isSubPage ? (
          <button type="button" className="back-btn" onClick={handleBack} aria-label="Back">
            <ChevronLeftIcon />
          </button>
        ) : (
          <div className="nav-brand">
            <span className="nav-logo-wrap">
              <img src="/nrityaai-logo.png" alt="NrityaAI logo" className="nav-logo-img" />
            </span>
            <div className="nav-text">
              <p className="nav-title">NrityaAI</p>
              <p className="nav-tagline">Preserving Art. Empowering Talent.</p>
            </div>
          </div>
        )}

        {!isSubPage && (
          <button type="button" className="about-btn">
            <InfoIcon />
            About Us
          </button>
        )}
      </header>

      <div className="site-inner">
        <section className="hero">
          <h1 className="page-title">Rhythm Analysis</h1>
          <LotusDivider tagline="Discover the beauty of Bharatiya Natya through AI" />
        </section>

        <main className="page-main">
          <input
            id="video-upload"
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleSelectFile}
            disabled={isLoading}
            hidden
          />

          <section
            className={`dashboard ${result ? 'after-view' : isLoading ? 'loading-view' : 'before-view'}`}
          >
            {isLoading ? (
              <div className="loading-screen">
                <div className="panel-card loading-video-card">
                  {previewUrl ? (
                    <video
                      src={previewUrl}
                      className="loading-video"
                      autoPlay
                      loop
                      controls
                      playsInline
                    />
                  ) : (
                    <div className="preview-placeholder">Preparing preview...</div>
                  )}
                </div>
                <div className="panel-card loading-panel">
                  <div className="loader-ring" />
                  <h2 className="section-label">Analyzing Rhythm</h2>
                  <p>Playing your uploaded video while we calculate beat synchronization.</p>
                  <p className="loading-note">Please keep this tab open until the analysis completes.</p>
                </div>
              </div>
            ) : !result ? (
              <>
                <div className="hero-panel panel-card">
                  <img
                    src="/bharatanatyam-pose.png"
                    alt="Bharatanatyam dancer in traditional pose"
                    className="hero-panel__image"
                  />
                  <div className="hero-glow" aria-hidden="true" />
                </div>

                <form className="upload-section panel-card" onSubmit={handleAnalyze}>
                  <p className="section-label section-label--upper">Upload Your Performance</p>
                  <label htmlFor="video-upload" className="upload-box">
                    <UploadIcon />
                    <strong>Upload Dance Video</strong>
                    <small className="label-small">Supported: MP4, MOV, AVI, MKV</small>
                    <p>Drag and drop your file here or click to browse</p>
                  </label>
                  <div className="waveform" aria-hidden="true" />
                  <p className="hint">
                    Upload a Bharatanatyam performance to analyze rhythm synchronization and beat
                    alignment.
                  </p>
                  {file && <p className="file-name">{file.name}</p>}
                  {error && <p className="error">{error}</p>}
                  <button className="analyze-btn" type="submit" disabled={!file || isLoading}>
                    Analyze
                  </button>
                </form>
              </>
            ) : (
              <>
                <p className="section-label section-label--upper result-page-label">
                  Analysis Results
                </p>

                <div className="result-main-row">
                  <div className="panel-card video-card">
                    {previewUrl ? (
                      <video src={previewUrl} className="result-video" controls />
                    ) : (
                      <div className="preview-placeholder">No preview</div>
                    )}
                  </div>

                  <div className="result-side">
                    <div className="panel-card score-card">
                      <p className="card-title">Synchronization Score</p>
                      <div className="score-ring">{formattedScore}</div>
                      <p className={`score-label ${result.valid_video ? 'score-label--ok' : ''}`}>
                        {result.valid_video ? 'Great' : 'Invalid'}
                      </p>
                    </div>

                    <div className="panel-card viz-card">
                      <p className="card-title">Rhythm Visualization</p>
                      <div className="waveform large" aria-hidden="true" />
                      <div className="legend">
                        <span>
                          <i className="dot dot--gold" /> On Beat
                        </span>
                        <span>
                          <i className="dot dot--accent" /> Ahead of Beat
                        </span>
                      </div>
                    </div>

                    <div className="panel-card feedback-card">
                      <p className="result-line">
                        <strong>{statusText}</strong>
                      </p>
                      <p className="result-line">{result.feedback || 'No feedback available.'}</p>
                      <p className="result-line">
                        Pattern:{' '}
                        {typeof result.pattern_score === 'number'
                          ? result.pattern_score.toFixed(3)
                          : '-'}
                      </p>
                      <p className="result-line">Correct: {result.timing?.correct ?? 0}</p>
                      <p className="result-line">Early: {result.timing?.early ?? 0}</p>
                      <p className="result-line">Late: {result.timing?.late ?? 0}</p>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => {
                    setResult(null);
                    setError('');
                    setFile(null);
                    setPreviewUrl('');
                  }}
                >
                  Upload Another Video
                </button>
              </>
            )}
          </section>
        </main>

        <footer className="page-tip">
          <p>
            NrityaAI honors Bharatiya Natya traditions — upload clear performances with audible tala
            for the most respectful analysis.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
