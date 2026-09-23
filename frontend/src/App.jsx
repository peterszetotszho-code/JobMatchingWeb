import { useRef, useState } from 'react';
import { parseFile, analyzeStream } from './api.js';

function TextPanel({ title, value, onChange, onUpload, placeholder }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <button className="ghost" onClick={onUpload}>📎 上傳檔案</button>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function Metric({ num, label, color }) {
  return (
    <div className="metric">
      <div className="num" style={{ color }}>{num}</div>
      <div className="label">{label}</div>
    </div>
  );
}

export default function App() {
  const [resume, setResume] = useState('');
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const resumeFileRef = useRef(null);
  const jdFileRef = useRef(null);

  async function handleUpload(file, setText) {
    if (!file) return;
    try {
      setError('');
      const text = await parseFile(file);
      setText(text);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleAnalyze() {
    if (!resume.trim() || !jd.trim()) return;
    setLoading(true);
    setError('');
    setStage('');
    setAnalysis('');
    setResult(null);
    try {
      await analyzeStream(resume, jd, {
        onStage: setStage,
        onChunk: (t) => setAnalysis((prev) => prev + t),
        onResult: setResult,
        onError: (m) => setError(m),
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>💼 求職助手 Job Fit Assistant</h1>
        <p>上傳履歷，貼上 JobsDB 職位描述，即時比對你的符合度與差距。</p>
      </header>

      <div className="grid">
        <TextPanel
          title="📄 你的履歷 Your Resume"
          value={resume}
          onChange={setResume}
          onUpload={() => resumeFileRef.current?.click()}
          placeholder="貼上履歷文字，或上傳 PDF / DOCX / TXT…"
        />
        <TextPanel
          title="📋 職位描述 Job Description"
          value={jd}
          onChange={setJd}
          onUpload={() => jdFileRef.current?.click()}
          placeholder="從 JobsDB 複製 JD 文字貼到這裡，或上傳檔案…"
        />
      </div>

      <input
        ref={resumeFileRef}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        style={{ display: 'none' }}
        onChange={(e) => handleUpload(e.target.files?.[0], setResume)}
      />
      <input
        ref={jdFileRef}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        style={{ display: 'none' }}
        onChange={(e) => handleUpload(e.target.files?.[0], setJd)}
      />

      <div className="actions">
        <button
          className="primary"
          onClick={handleAnalyze}
          disabled={loading || !resume.trim() || !jd.trim()}
        >
          {loading ? '分析中…' : '🔍 開始分析 Analyze'}
        </button>
      </div>

      {error && <div className="error">⚠️ {error}</div>}
      {loading && <div className="stage">⏳ {stage}</div>}

      {(analysis || result) && (
        <div className="result">
          {result && (
            <>
              <div className="metrics">
                <Metric num={`${result.fit_score}%`} label="符合度 Fit Score" color="#2563eb" />
                <Metric num={result.matched} label="匹配 Matched" color="#16a34a" />
                <Metric num={result.partial} label="部分 Partial" color="#d97706" />
                <Metric num={result.gap} label="缺口 Gap" color="#dc2626" />
              </div>
              <div className="bar">
                <div className="bar-fill" style={{ width: `${result.fit_score}%` }} />
              </div>
            </>
          )}
          <h3>📊 分析結果 Analysis</h3>
          <p className="analysis">
            {analysis}
            {loading && <span className="cursor">▌</span>}
          </p>
        </div>
      )}
    </div>
  );
}
