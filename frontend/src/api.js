const BASE = '/api';

// 上傳檔案 → 抽取文字
export async function parseFile(file) {
  const form = new FormData();
  form.append('file', file);
  const resp = await fetch(`${BASE}/parse`, { method: 'POST', body: form });
  if (!resp.ok) throw new Error(`上傳失敗 (${resp.status})`);
  const data = await resp.json();
  return data.text || '';
}

// 解析 SSE 串流
async function readSSE(resp, { onStage, onChunk, onResult, onError }) {
  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      let event;
      try { event = JSON.parse(payload); } catch { continue; }
      if (event.type === 'stage') onStage?.(event.message);
      else if (event.type === 'chunk') onChunk?.(event.text);
      else if (event.type === 'result') onResult?.(event.data);
      else if (event.type === 'error') onError?.(event.message);
    }
  }
}

export async function analyzeStream(resume, jd, handlers) {
  const resp = await fetch(`${BASE}/analyze/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume, jd }),
  });
  if (!resp.ok) throw new Error(`請求失敗 (${resp.status})`);
  await readSSE(resp, handlers);
}

export async function askStream(payload, handlers) {
  const resp = await fetch(`${BASE}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`請求失敗 (${resp.status})`);
  await readSSE(resp, handlers);
}
