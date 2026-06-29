import { useEffect, useMemo, useRef, useState } from "react";
import { buildReport, sendAnswer, startSession, synthesizeSpeech, transcribeAudio } from "./api.js";
import { WavRecorder } from "./recorder.js";

const DEFAULT_SETTINGS = {
  practice_mode: true,
  answer_expansion_mode: true,
  voice_playback_enabled: true,
};

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
  const chatPanelRef = useRef(null);
  const bottomRef = useRef(null);
  const recorderRef = useRef(null);
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
    createFreshSession();
    return () => {
      recorderRef.current?.cleanup?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    }

    window.addEventListener("pagehide", cleanupRecorder);
    return () => window.removeEventListener("pagehide", cleanupRecorder);
  }, []);

  async function createFreshSession() {
    recorderRef.current?.cleanup?.();
    recorderRef.current = null;
    setRecording(false);
    setElapsed(0);
    setError("");
    setReport("");
    setDraft("");
    setBusy("starting");
    try {
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
    try {
      const blob = await synthesizeSpeech(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.addEventListener("ended", () => URL.revokeObjectURL(url), { once: true });
      await audio.play();
    } catch (_) {
      // Browsers may block autoplay; text still remains the source of truth.
    }
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">IELTS Speaking Coach</div>
          <h1>Examiner Victoria</h1>
        </div>
        <div className="top-actions">
          <button className="ghost-button" type="button" onClick={() => setAudioEnabled((v) => !v)}>
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
