const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch (_) {
      // Some endpoints return plain text or binary.
    }
    throw new Error(message);
  }

  return response;
}

export async function startSession(settings) {
  const response = await request("/api/sessions", {
    method: "POST",
    body: JSON.stringify(settings),
  });
  return response.json();
}

export async function sendAnswer({ session, answer, source, duration }) {
  const response = await request("/api/answer", {
    method: "POST",
    body: JSON.stringify({ session, answer, source, duration }),
  });
  return response.json();
}

export async function transcribeAudio(blob) {
  const form = new FormData();
  form.append("file", blob, "answer.wav");
  const response = await request("/api/transcribe", {
    method: "POST",
    body: form,
  });
  return response.json();
}

export async function synthesizeSpeech(text) {
  const response = await request("/api/tts", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  return response.blob();
}

export async function buildReport(session) {
  const response = await request("/api/report", {
    method: "POST",
    body: JSON.stringify({ session }),
  });
  return response.json();
}
