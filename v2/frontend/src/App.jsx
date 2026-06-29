import { useEffect, useMemo, useRef, useState } from "react";
import { buildReport, healthCheck, sendAnswer, startSession, synthesizeSpeech, transcribeAudio } from "./api.js";
import { WavRecorder } from "./recorder.js";

const DEFAULT_SETTINGS = {
  practice_mode: true,
  answer_expansion_mode: true,
  voice_playback_enabled: true,
};
const STORAGE_KEY = "examiner-victoria-v2-state";

function phaseLabel(phase) {
  const labels = {
    identity: "Part 1",
    part1: "Part 1",
    part2_long: "Part 2",
    part2_followup: "Part 2",
    part3: "Part 3",
    complete: "Complete",
  };
  return labels[phase] || "Part 1";
}

function busyLabel(busy) {
  if (busy === "starting") return "Starting Victoria...";
  if (busy === "transcribing") return "Transcribing your answer...";
  if (busy === "thinking") return "Victoria is thinking...";
  if (busy === "report") return "Preparing your report...";
  return "";
}

function formatDuration(seconds) {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  const rest = String(safe % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function safeDateStamp() {
  return new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildTranscriptText(session) {
  const lines = [
    "Examiner Victoria V2 - IELTS Speaking Transcript",
    `Session ID: ${session?.session_id || "unknown"}`,
    "",
  ];

  (session?.messages || []).forEach((message, index) => {
    const speaker = message.role === "assistant" ? "Victoria" : "Candidate";
    const phase = message.phase ? ` [${message.phase}]` : "";
    lines.push(`${index + 1}. ${speaker}${phase}`);
    lines.push(String(message.content || "").replace(/\n{3,}/g, "\n\n"));
    lines.push("");
  });

  return lines.join("\n").trim() + "\n";
}

function friendlyError(err, fallback) {
  const message = err?.message || "";
  if (/microphone|permission|notallowed|denied/i.test(message)) {
    return "Microphone access was blocked. Please allow microphone permission, or switch to Text.";
  }
  if (/recording is too short|too short/i.test(message)) {
    return "That recording was too short. Tap again and answer in a complete sentence.";
  }
  if (/transcription|audio|whisper|duration|500|502/i.test(message)) {
    return "Audio transcription is temporarily unavailable. You can switch to Text and type your answer.";
  }
  if (/not reachable|VITE_API_BASE|backend service/i.test(message)) {
    return "Victoria's server is not reachable. Please try again in a moment, or check whether the backend is running.";
  }
  if (/timed out|waking up/i.test(message)) {
    return "Victoria's server is taking too long to respond. It may be waking up, so please try again in a moment.";
  }
  if (/network|failed to fetch|load failed/i.test(message)) {
    return "Network connection is unstable. Please try again in a moment.";
  }
  return message || fallback;
}

function RichMessage({ content }) {
  const blocks = String(content || "").split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, index) => {
        const trimmed = block.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith(">")) {
          return (
            <blockquote key={index}>
              {trimmed.replace(/^>\s?/, "").replace(/\*\*/g, "")}
            </blockquote>
          );
        }
        return (
          <p key={index}>
            {trimmed.split(/(\*\*[^*]+\*\*)/g).map((part, partIndex) => {
              if (part.startsWith("**") && part.endsWith("**")) {
                return <strong key={partIndex}>{part.slice(2, -2)}</strong>;
              }
              return <span key={partIndex}>{part}</span>;
            })}
          </p>
        );
      })}
    </>
  );
}

function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <article className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="avatar" aria-hidden="true">
        {isUser ? "Y" : "V"}
      </div>
      <div className="bubble">
        <RichMessage content={message.content} />
      </div>
    </article>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState("voice");
  const [reviewBeforeSend, setReviewBeforeSend] = useState(false);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [busy, setBusy] = useState("starting");
  const [error, setError] = useState("");
  const [report, setReport] = useState("");
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [storageReady, setStorageReady] = useState(false);
  const chatPanelRef = useRef(null);
  const bottomRef = useRef(null);
  const recorderRef = useRef(null);
  const audioRef = useRef(null);
  const startedAtRef = useRef(0);

  const messages = session?.messages || [];
  const currentPhase = phaseLabel(session?.phase);
  const canAnswer = Boolean(session?.test_active) && !busy && !recording;
  const canStartRecording = Boolean(session?.test_active) && !busy;
  const recordButtonDisabled = recording ? false : !canStartRecording;
  const recordButtonText = !session
    ? "Starting..."
    : session.test_active
      ? recording
        ? "Tap to send"
        : "Tap to record"
      : "Test complete";

  const stageProgress = useMemo(() => {
    const map = {
      identity: 8,
      part1: 28,
      part2_long: 52,
      part2_followup: 68,
      part3: 84,
      complete: 100,
    };
    return map[session?.phase] || 8;
  }, [session?.phase]);

  useEffect(() => {
    let restored = false;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const saved = raw ? JSON.parse(raw) : null;
      if (saved?.session?.messages?.length) {
        setSession(saved.session);
        setReport(saved.report || "");
        setAudioEnabled(saved.audioEnabled ?? true);
        setReviewBeforeSend(Boolean(saved.reviewBeforeSend));
        restored = true;
      }
    } catch (_) {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch (_) {
        // Ignore storage failures in restricted/private browsing contexts.
      }
    }
    setStorageReady(true);
    if (!restored) {
      createFreshSession();
    } else {
      setBusy("");
    }
    return () => {
      recorderRef.current?.cleanup?.();
      stopCurrentAudio();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    try {
      if (!session) {
        window.localStorage.removeItem(STORAGE_KEY);
        return;
      }
      const saved = {
        version: 1,
        savedAt: new Date().toISOString(),
        session,
        report,
        audioEnabled,
        reviewBeforeSend,
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    } catch (_) {
      // Storage can be blocked in private mode or embedded mobile WebViews.
      // The app should still work; it will just skip refresh recovery.
    }
  }, [audioEnabled, report, reviewBeforeSend, session, storageReady]);

  useEffect(() => {
    const panel = chatPanelRef.current;
    if (panel) {
      panel.scrollTo({ top: panel.scrollHeight, behavior: "smooth" });
    } else {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages.length, busy, report]);

  useEffect(() => {
    if (!recording) return undefined;
    const timer = window.setInterval(() => {
      setElapsed((Date.now() - startedAtRef.current) / 1000);
    }, 120);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => {
    function cleanupRecorder() {
      recorderRef.current?.cleanup?.();
      recorderRef.current = null;
      stopCurrentAudio();
    }

    window.addEventListener("pagehide", cleanupRecorder);
    return () => window.removeEventListener("pagehide", cleanupRecorder);
  }, []);

  function stopCurrentAudio() {
    if (!audioRef.current) return;
    audioRef.current.pause();
    audioRef.current.removeAttribute("src");
    audioRef.current.load();
    audioRef.current = null;
  }

  async function createFreshSession() {
    recorderRef.current?.cleanup?.();
    recorderRef.current = null;
    stopCurrentAudio();
    setSession(null);
    setRecording(false);
    setElapsed(0);
    setError("");
    setReport("");
    setDraft("");
    setBusy("starting");
    try {
      await healthCheck();
      const data = await startSession(DEFAULT_SETTINGS);
      setSession(data.session);
      setAudioEnabled(data.session.voice_playback_enabled);
    } catch (err) {
      setError(friendlyError(err, "Failed to start session."));
    } finally {
      setBusy("");
    }
  }

  async function playSpeech(text) {
    if (!audioEnabled || !text) return;
    stopCurrentAudio();
    let url = "";
    try {
      const blob = await synthesizeSpeech(text);
      url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.addEventListener(
        "ended",
        () => {
          URL.revokeObjectURL(url);
          if (audioRef.current === audio) {
            audioRef.current = null;
          }
        },
        { once: true },
      );
      await audio.play();
    } catch (_) {
      if (url) URL.revokeObjectURL(url);
      if (audioRef.current) {
        audioRef.current = null;
      }
      // Browsers may block autoplay; text still remains the source of truth.
    }
  }

  function toggleAudioEnabled() {
    setAudioEnabled((value) => {
      if (value) {
        stopCurrentAudio();
      }
      return !value;
    });
  }

  function resetComposerAfterAnswer() {
    setDraft("");
    setElapsed(0);
    recorderRef.current = null;
  }

  async function submitAnswer(answer, source = "text", duration = null) {
    const cleaned = answer.trim();
    if (!cleaned || !session) return;
    setError("");
    setBusy("thinking");
    stopCurrentAudio();
    resetComposerAfterAnswer();
    try {
      const data = await sendAnswer({
        session,
        answer: cleaned,
        source,
        duration,
      });
      setSession(data.session);
      await playSpeech(data.spoken_text);
    } catch (err) {
      setError(friendlyError(err, "Victoria could not respond."));
    } finally {
      setBusy("");
    }
  }

  async function submitTypedAnswer(event) {
    event?.preventDefault();
    await submitAnswer(draft, "text", null);
  }

  async function toggleRecording() {
    if (busy) return;
    setError("");

    if (!recording) {
      try {
        recorderRef.current?.cleanup?.();
        recorderRef.current = new WavRecorder({ targetSampleRate: 16000 });
        await recorderRef.current.start();
        startedAtRef.current = Date.now();
        setElapsed(0);
        setRecording(true);
      } catch (err) {
        recorderRef.current?.cleanup?.();
        recorderRef.current = null;
        setError(friendlyError(err, "Microphone permission was blocked."));
      }
      return;
    }

    setRecording(false);
    setBusy("transcribing");
    try {
      const result = await recorderRef.current.stop();
      recorderRef.current = null;
      setElapsed(0);
      if (!result) return;
      if (!result.blob || result.blob.size < 1024 || !Number.isFinite(result.duration)) {
        throw new Error("Recording is too short.");
      }
      const transcription = await transcribeAudio(result.blob);
      const text = transcription.text || "";
      if (!text.trim()) {
        throw new Error("No clear speech was detected.");
      }
      if (reviewBeforeSend) {
        setDraft(text);
        setMode("text");
        setBusy("");
      } else {
        await submitAnswer(text, "audio", result.duration);
      }
    } catch (err) {
      recorderRef.current?.cleanup?.();
      recorderRef.current = null;
      setElapsed(0);
      setError(friendlyError(err, "Recording could not be sent."));
      setBusy("");
    }
  }

  async function requestReport() {
    if (!session) return;
    setError("");
    setBusy("report");
    try {
      const data = await buildReport(session);
      setReport(data.report);
    } catch (err) {
      setError(friendlyError(err, "Report could not be generated."));
    } finally {
      setBusy("");
    }
  }

  function downloadReport() {
    if (!report) return;
    downloadTextFile(`examiner-victoria-report-${safeDateStamp()}.txt`, report);
  }

  function downloadTranscript() {
    if (!session) return;
    downloadTextFile(`examiner-victoria-transcript-${safeDateStamp()}.txt`, buildTranscriptText(session));
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">IELTS Speaking Coach</div>
          <h1>Examiner Victoria</h1>
        </div>
        <div className="top-actions">
          <button className="ghost-button" type="button" onClick={toggleAudioEnabled}>
            {audioEnabled ? "Sound on" : "Sound off"}
          </button>
          <button className="ghost-button" type="button" onClick={createFreshSession}>
            Restart
          </button>
        </div>
      </header>

      <aside className="stage-card">
        <div>
          <span className="stage-pill">{currentPhase}</span>
          <p>{session?.phase === "part3" ? "Dynamic follow-up loop" : "Structured IELTS flow"}</p>
        </div>
        <div className="progress-track">
          <div style={{ width: `${stageProgress}%` }} />
        </div>
      </aside>

      <main className="chat-panel" ref={chatPanelRef}>
        {messages.map((message, index) => (
          <MessageBubble key={`${message.role}-${index}`} message={message} />
        ))}

        {busy ? (
          <div className="status-card">
            <span className="spinner" />
            {busyLabel(busy)}
          </div>
        ) : null}

        {error ? <div className="error-card">{error}</div> : null}

        {report ? (
          <section className="report-card">
            <h2>Final report</h2>
            <RichMessage content={report} />
            <div className="report-actions">
              <button type="button" className="ghost-button" onClick={downloadReport}>
                Download report
              </button>
              <button type="button" className="ghost-button" onClick={downloadTranscript}>
                Download transcript
              </button>
            </div>
          </section>
        ) : null}

        <div ref={bottomRef} />
      </main>

      <footer className="composer-wrap">
        <div className="composer">
          <button
            className="mode-button"
            type="button"
            disabled={Boolean(busy) || recording || !session?.test_active}
            onClick={() => setMode((value) => (value === "voice" ? "text" : "voice"))}
            aria-label={mode === "voice" ? "Switch to text input" : "Switch to voice input"}
          >
            {mode === "voice" ? "Text" : "Voice"}
          </button>

          {mode === "voice" ? (
            <div className="voice-composer">
              <button
                className={`record-button ${recording ? "recording" : ""}`}
                type="button"
                disabled={recordButtonDisabled}
                onClick={toggleRecording}
                aria-pressed={recording}
                aria-label={recording ? "Stop recording and send" : "Start recording"}
              >
                {recordButtonText}
              </button>
              <span className="timer">{recording ? formatDuration(elapsed) : "ready"}</span>
              <label className="review-toggle">
                <input
                  type="checkbox"
                  checked={reviewBeforeSend}
                  onChange={(event) => setReviewBeforeSend(event.target.checked)}
                />
                <span>review</span>
              </label>
            </div>
          ) : (
            <form className="text-composer" onSubmit={submitTypedAnswer}>
              <input
                value={draft}
                disabled={!canAnswer && !draft}
                placeholder="Type your answer..."
                autoComplete="off"
                onChange={(event) => setDraft(event.target.value)}
              />
              <button type="submit" disabled={!draft.trim() || Boolean(busy)}>
                Send
              </button>
            </form>
          )}

          {session?.phase === "complete" ? (
            <button className="score-button" type="button" onClick={requestReport} disabled={Boolean(busy)}>
              Get Score
            </button>
          ) : null}
        </div>
      </footer>
    </div>
  );
}
