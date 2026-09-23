import { useEffect, useRef, useState } from 'react';
import {
  parseFile, analyzeStream, askStream,
  saveRecord, listRecords, getRecord, deleteRecord, addMessage,
} from './api.js';

function getUserId() {
  let id = localStorage.getItem('jobfit_user_id');
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID())
      || 'u_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem('jobfit_user_id', id);
  }
  return id;
}

function TextPanel({ title, value, onChange, onUpload, placeholder }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <button className="ghost" onClick={onUpload}>📎 上傳檔案</button>
      </div>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
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
  const userId = getUserId();

  const [resume, setResume] = useState('');
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const [session, setSession] = useState({ resume: '', jd: '' });

  const [records, setRecords] = useState([]);
  const [currentRecordId, setCurrentRecordId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatDraft, setChatDraft] = useState('');
  const [chatStage, setChatStage] = useState('');

  const resumeFileRef = useRef(null);
  const jdFileRef = useRef(null);

  useEffect(() => { refreshRecords(); }, []);

  async function refreshRecords() {
    try { setRecords(await listRecords(userId)); } catch { /* ignore */ }
  }

  function handleNewAnalysis() {
    setResume('');
    setJd('');
    setResult(null);
    setAnalysis('');
    setMessages([]);
    setCurrentRecordId(null);
    setSession({ resume: '', jd: '' });
    setError('');
  }

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
    setMessages([]);
    setCurrentRecordId(null);
    try {
      await analyzeStream(resume, jd, {
        onStage: setStage,
        onChunk: (t) => setAnalysis((prev) => prev + t),
        onResult: async (data) => {
          setResult(data);
          setAnalysis(data.analysis || '');
          setSession({ resume, jd });
          try {
            const saved = await saveRecord({
              user_id: userId,
              resume,
              jd,
              analysis: data.analysis || '',
              title: data.title || '',
              fit_score: data.fit_score,
              matched: data.matched,
              partial: data.partial,
              gap: data.gap,
            });
            setCurrentRecordId(saved.record_id);
          } catch { /* ignore save errors */ }
          refreshRecords();
        },
        onError: (m) => setError(m),
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function openRecord(id) {
    try {
      const rec = await getRecord(userId, id);
      if (rec.error) { setError(rec.error); return; }
      setCurrentRecordId(id);
      setResult({ fit_score: rec.fit_score, matched: rec.matched, partial: rec.partial, gap: rec.gap });
      setAnalysis(rec.analysis);
      setSession({ resume: rec.resume, jd: rec.jd });
      setMessages(rec.messages || []);
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }

  async function loadRecordToInputs(id) {
    try {
      const rec = await getRecord(userId, id);
      if (rec.error) { setError(rec.error); return; }
      setResume(rec.resume);
      setJd(rec.jd);
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteRecord(userId, id);
      if (currentRecordId === id) {
        setCurrentRecordId(null);
        setResult(null);
        setAnalysis('');
        setMessages([]);
        setSession({ resume: '', jd: '' });
      }
      refreshRecords();
    } catch (e) {
      setError(e.message);
    }
  }

  async function sendMessage() {
    const q = input.trim();
    if (!q || chatLoading || !result) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: q }]);
    setChatLoading(true);
    setChatDraft('');
    setChatStage('');
    let answerText = '';
    try {
      if (currentRecordId) {
        await addMessage(userId, currentRecordId, 'user', q).catch(() => {});
      }
      await askStream(
        { question: q, resume: session.resume, jd: session.jd, analysis },
        {
          onStage: setChatStage,
          onChunk: (t) => { answerText += t; setChatDraft((p) => p + t); },
          onResult: () => {},
          onError: (m) => { answerText += `\n⚠️ ${m}`; },
        },
      );
      setMessages((m) => [...m, { role: 'assistant', content: answerText }]);
      if (currentRecordId) {
        await addMessage(userId, currentRecordId, 'assistant', answerText).catch(() => {});
      }
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: '⚠️ ' + e.message }]);
    } finally {
      setChatLoading(false);
      setChatDraft('');
      setChatStage('');
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-head">
          <button className="primary" onClick={handleNewAnalysis}>➕ 新建分析 New</button>
        </div>
        <h3 className="sidebar-title">📂 歷史記錄 History</h3>
        {records.length === 0 ? (
          <p className="sidebar-empty">尚無記錄</p>
        ) : (
          <div className="history-list">
            {records.map((r) => (
              <div key={r.id} className={`history-item ${r.id === currentRecordId ? 'active' : ''}`}>
                <div className="history-title">{r.title}</div>
                <div className="history-meta">{r.fit_score}% · {new Date(r.created_at).toLocaleString()}</div>
                <div className="history-actions">
                  <button className="ghost" title="繼續對話" onClick={() => openRecord(r.id)}>💬</button>
                  <button className="ghost" title="載入履歷/JD 到輸入框" onClick={() => loadRecordToInputs(r.id)}>📋</button>
                  <button className="ghost danger" title="刪除記錄" onClick={() => handleDelete(r.id)}>🗑</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </aside>

      <main className="main">
        <header>
          <h1>💼 求職助手 Job Fit Assistant</h1>
          <p>上傳履歷，貼上 JobsDB 職位描述，比對符合度；分析後還可追問、聯網查公司資訊。</p>
          <a className="repo-link" href="https://github.com/peterszetotszho-code/JobMatchingWeb" target="_blank" rel="noreferrer">
            ⭐ View on GitHub
          </a>
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

        <input ref={resumeFileRef} type="file" accept=".pdf,.docx,.txt,.md" style={{ display: 'none' }}
          onChange={(e) => handleUpload(e.target.files?.[0], setResume)} />
        <input ref={jdFileRef} type="file" accept=".pdf,.docx,.txt,.md" style={{ display: 'none' }}
          onChange={(e) => handleUpload(e.target.files?.[0], setJd)} />

        <div className="actions">
          <button className="primary" onClick={handleAnalyze}
            disabled={loading || !resume.trim() || !jd.trim()}>
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

        {result && (
          <div className="chat">
            <h3>💬 求職追問 Ask Follow-up</h3>
            <div className="chat-log">
              {messages.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <div className="msg-content">{m.content}</div>
                </div>
              ))}
              {chatLoading && (
                <div className="msg assistant">
                  <div className="chat-stage">⏳ {chatStage}</div>
                  <div className="msg-content">{chatDraft}<span className="cursor">▌</span></div>
                </div>
              )}
            </div>
            <div className="chat-input">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
                placeholder="例如：這間公司是做什麼的？／我該怎麼補強才能提高符合度？"
              />
              <button onClick={sendMessage} disabled={chatLoading || !input.trim()}>送出</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
