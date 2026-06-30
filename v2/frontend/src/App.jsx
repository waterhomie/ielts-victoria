import { useEffect, useMemo, useRef, useState } from "react";
import {
  buildReport,
  fetchPracticeOptions,
  healthCheck,
  sendAnswer,
  startSession,
  synthesizeSpeech,
  transcribeAudio,
} from "./api.js";
import { WavRecorder } from "./recorder.js";

const DEFAULT_SETTINGS = {
  voice_playback_enabled: true,
};
const TRAINING_MODES = [
  { value: "practice", label: "Practice" },
  { value: "mock", label: "Mock" },
];
const PRACTICE_TYPES = [
  { value: "full", label: "Full" },
  { value: "part1", label: "Part 1" },
  { value: "part2", label: "Part 2" },
  { value: "part3", label: "Part 3" },
];
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

function phaseNameForRecord(phase) {
  const names = {
    identity: "Identity check",
    part1: "Part 1",
    part2_long: "Part 2 long turn",
    part2_followup: "Part 2 follow-up",
    part3: "Part 3",
    complete: "Complete",
  };
  return names[phase] || phase || "Unknown";
}

function formatSecondsForRecord(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) return "N/A";
  return `${Number(seconds).toFixed(1)}s`;
}

function buildPracticeRecordText(session, report) {
  const answers = session?.candidate_answers || [];
  const stats = session?.answer_stats || [];
  const answeredStats = stats.filter((item) => item.phase !== "identity");
  const totalWords = answeredStats.reduce((sum, item) => sum + (item.word_count || 0), 0);
  const totalSeconds = answeredStats.reduce((sum, item) => sum + (Number(item.duration) || 0), 0);
  const audioCount = answeredStats.filter((item) => item.source === "audio").length;
  const textCount = answeredStats.filter((item) => item.source === "text").length;
  const wpmValues = answeredStats
    .map((item) => Number(item.words_per_minute))
    .filter((value) => Number.isFinite(value) && value > 0);
  const averageWpm = wpmValues.length
    ? `${Math.round(wpmValues.reduce((sum, value) => sum + value, 0) / wpmValues.length)} WPM`
    : "N/A";
  const cueCard = session?.cue_card || {};

  const lines = [
    "Examiner Victoria V2 - Practice Record",
    `Generated at: ${new Date().toLocaleString()}`,
    `Session ID: ${session?.session_id || "unknown"}`,
    "",
    "## Session summary",
    `Practice type: ${session?.practice_type || "full"}`,
    `Current phase: ${phaseNameForRecord(session?.phase)}`,
    `Part 1 topic: ${session?.part1_topic || "Random / not selected"}`,
    `Cue card: ${cueCard.title || "Random / not reached yet"}`,
    `Candidate answers: ${answers.length}`,
    `Audio answers: ${audioCount}`,
    `Text answers: ${textCount}`,
    `Total spoken/recorded duration: ${formatSecondsForRecord(totalSeconds)}`,
    `Total words: ${totalWords}`,
    `Average WPM: ${averageWpm}`,
  ];

  if (cueCard.prompt) {
    lines.push("", "## Part 2 cue card", cueCard.prompt);
  }

  lines.push("", "## Timing and fluency stats");
  if (stats.length) {
    stats.forEach((item, index) => {
      lines.push(
        `${index + 1}. ${phaseNameForRecord(item.phase)} | ${item.source} | duration ${formatSecondsForRecord(item.duration)} | ${item.word_count || 0} words | ${item.words_per_minute ? `${Math.round(item.words_per_minute)} WPM` : "WPM N/A"}`,
      );
    });
  } else {
    lines.push("No timing stats saved yet.");
  }

  lines.push("", "## Question-by-question answers");
  if (answers.length) {
    answers.forEach((item, index) => {
      const stat = stats[index] || {};
      lines.push(
        `${index + 1}. ${phaseNameForRecord(item.phase)} (${item.source || stat.source || "text"}, ${formatSecondsForRecord(item.duration ?? stat.duration)})`,
        `Q: ${item.question || "N/A"}`,
        `A: ${item.answer || ""}`,
        "",
      );
    });
  } else {
    lines.push("No candidate answers saved yet.");
  }

  lines.push(
    "",
    "## Full transcript",
    buildTranscriptText(session).trim(),
    "",
    "## Report",
    report?.trim() || "No score report generated yet. Tap Score when you want Victoria to create one.",
  );

  return lines.join("\n").replace(/\n{4,}/g, "\n\n\n").trim() + "\n";
}

function friendlyError(err, fallback) {
  const message = err?.message || "";
  if (/secure HTTPS|secure context|local network HTTP|isSecureContext/i.test(message)) {
    return "iPhone Safari needs HTTPS before it can ask for microphone permission. This local Wi-Fi address can be used for text testing, but voice recording needs an HTTPS preview or public deployment.";
  }
  if (/secure HTTPS|secure context|local network HTTP|isSecureContext/i.test(message)) {
    return "iPhone Safari needs HTTPS before it can ask for microphone permission. This local Wi‑Fi address can be used for text testing, but voice recording needs an HTTPS preview or public deployment.";
  }
  if (/microphone|permission|notallowed|denied/i.test(message)) {
    return "Microphone access was blocked. Please allow microphone permission, or switch to Text.";
  }
  if (/recording is too short|too short/i.test(message)) {
    return "That recording was too short. Tap again and answer in a complete sentence.";
  }
  if (/too many requests/i.test(message)) {
    return "Too many requests. Please wait a moment before trying again.";
  }
  if (/too long|too large|session is too large|voice playback text/i.test(message)) {
    return message;
  }
  if (/transcription|audio|whisper|duration/i.test(message)) {
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

function isLikelyIOSDevice() {
  if (typeof navigator === "undefined") return false;
  const userAgent = navigator.userAgent || "";
  const platform = navigator.platform || "";
  return /iPad|iPhone|iPod/i.test(userAgent) || (platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function renderInline(text, keyPrefix) {
  return String(text || "")
    .split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
    .map((part, index) => {
      const key = `${keyPrefix}-${index}`;
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={key}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={key}>{part.slice(1, -1)}</code>;
      }
      return <span key={key}>{part}</span>;
    });
}

function RichMessage({ content }) {
  const lines = String(content || "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  const isHeading = (line) => /^#{1,4}\s+/.test(line.trim());
  const isRule = (line) => /^-{3,}$/.test(line.trim());
  const isQuote = (line) => /^>\s?/.test(line.trim());
  const isBullet = (line) => /^[-*]\s+/.test(line.trim());
  const isOrdered = (line) => /^\d+[.)]\s+/.test(line.trim());
  const isBlockStart = (line) =>
    !line.trim() || isHeading(line) || isRule(line) || isQuote(line) || isBullet(line) || isOrdered(line);

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (isRule(line)) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }

    if (isHeading(line)) {
      const match = trimmed.match(/^(#{1,4})\s+(.*)$/);
      blocks.push({ type: "heading", level: match[1].length, text: match[2] });
      index += 1;
      continue;
    }

    if (isQuote(line)) {
      const quoteLines = [];
      while (index < lines.length && isQuote(lines[index])) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", lines: quoteLines });
      continue;
    }

    if (isBullet(line) || isOrdered(line)) {
      const ordered = isOrdered(line);
      const items = [];
      while (index < lines.length && (ordered ? isOrdered(lines[index]) : isBullet(lines[index]))) {
        items.push(lines[index].trim().replace(ordered ? /^\d+[.)]\s+/ : /^[-*]\s+/, ""));
        index += 1;
      }
      blocks.push({ type: ordered ? "ordered-list" : "bullet-list", items });
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;
    while (index < lines.length && !isBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", lines: paragraphLines });
  }

  return (
    <div className="rich-message">
      {blocks.map((block, blockIndex) => {
        if (block.type === "rule") {
          return <hr key={blockIndex} />;
        }
        if (block.type === "heading") {
          const HeadingTag = block.level <= 2 ? "h3" : "h4";
          return <HeadingTag key={blockIndex}>{renderInline(block.text, `h-${blockIndex}`)}</HeadingTag>;
        }
        if (block.type === "quote") {
          return (
            <blockquote key={blockIndex}>
              {block.lines.map((quoteLine, lineIndex) => (
                <span key={lineIndex}>
                  {renderInline(quoteLine, `q-${blockIndex}-${lineIndex}`)}
                  {lineIndex < block.lines.length - 1 ? <br /> : null}
                </span>
              ))}
            </blockquote>
          );
        }
        if (block.type === "bullet-list" || block.type === "ordered-list") {
          const ListTag = block.type === "ordered-list" ? "ol" : "ul";
          return (
            <ListTag key={blockIndex}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInline(item, `li-${blockIndex}-${itemIndex}`)}</li>
              ))}
            </ListTag>
          );
        }
        return (
          <p key={blockIndex}>
            {block.lines.map((paragraphLine, lineIndex) => (
              <span key={lineIndex}>
                {renderInline(paragraphLine, `p-${blockIndex}-${lineIndex}`)}
                {lineIndex < block.lines.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

function reportSectionMeta(title) {
  const lowered = String(title || "").toLowerCase();
  if (lowered.includes("band") || lowered.includes("overall")) {
    return { label: "Score", tone: "score" };
  }
  if (lowered.includes("skill")) {
    return { label: "Skills", tone: "skills" };
  }
  if (lowered.includes("problem") || lowered.includes("weakness")) {
    return { label: "Issues", tone: "issues" };
  }
  if (lowered.includes("correct")) {
    return { label: "Examples", tone: "examples" };
  }
  if (lowered.includes("task") || lowered.includes("focus")) {
    return { label: "Next", tone: "tasks" };
  }
  if (lowered.includes("summary")) {
    return { label: "Summary", tone: "summary" };
  }
  return { label: "Report", tone: "default" };
}

function splitReportSections(report) {
  const text = String(report || "").replace(/\r\n/g, "\n").trim();
  if (!text) return [];
  const sections = [];
  const headingRegex = /^##\s+(.+)$/gm;
  const matches = [...text.matchAll(headingRegex)];

  if (!matches.length) {
    return [{ title: "Report", body: text, ...reportSectionMeta("Report") }];
  }

  const intro = text.slice(0, matches[0].index).trim();
  if (intro) {
    sections.push({ title: "Report note", body: intro, ...reportSectionMeta("Report note") });
  }

  matches.forEach((match, index) => {
    const start = match.index + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
    const title = match[1].trim();
    const body = text.slice(start, end).trim();
    if (body) {
      sections.push({ title, body, ...reportSectionMeta(title) });
    }
  });

  return sections;
}

function reportSectionId(title, index) {
  const slug = String(title || "section")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 42);
  return `report-section-${index}-${slug || "section"}`;
}

function ReportView({ report }) {
  const sections = splitReportSections(report);
  if (!sections.length) return null;
  return (
    <div className="report-sections">
      {sections.length > 1 ? (
        <nav className="report-nav" aria-label="Report sections">
          {sections.map((section, index) => (
            <button
              type="button"
              key={`${section.title}-nav-${index}`}
              onClick={() => document.getElementById(reportSectionId(section.title, index))?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              })}
            >
              {section.label}
            </button>
          ))}
        </nav>
      ) : null}
      {sections.map((section, index) => {
        const sectionId = reportSectionId(section.title, index);
        return (
          <section className={`report-section ${section.tone}`} id={sectionId} key={`${section.title}-${index}`}>
            <div className="report-section-header">
              <span className="report-section-chip">{section.label}</span>
              <h3>{section.title}</h3>
            </div>
            <RichMessage content={section.body} />
          </section>
        );
      })}
    </div>
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
  const [trainingMode, setTrainingMode] = useState("practice");
  const [practiceType, setPracticeType] = useState("full");
  const [practiceOptions, setPracticeOptions] = useState({ part1_topics: [], cue_cards: [] });
  const [selectedPart1Topic, setSelectedPart1Topic] = useState("");
  const [selectedCueCardTitle, setSelectedCueCardTitle] = useState("");
  const [healthInfo, setHealthInfo] = useState(null);
  const [storageReady, setStorageReady] = useState(false);
  const [prepEndsAt, setPrepEndsAt] = useState(null);
  const [clockTick, setClockTick] = useState(Date.now());
  const [pendingSpeechUrl, setPendingSpeechUrl] = useState("");
  const [pendingSpeechText, setPendingSpeechText] = useState("");
  const [canRetryRecording, setCanRetryRecording] = useState(false);
  const chatPanelRef = useRef(null);
  const bottomRef = useRef(null);
  const recorderRef = useRef(null);
  const audioRef = useRef(null);
  const audioUrlRef = useRef("");
  const pendingSpeechUrlRef = useRef("");
  const lastRecordingRef = useRef(null);
  const startedAtRef = useRef(0);
  const startupRecoveryAttemptedRef = useRef(false);

  const messages = session?.messages || [];
  const currentPhase = phaseLabel(session?.phase);
  const isPracticeMode = trainingMode === "practice";
  const canAnswer = Boolean(session?.test_active) && !busy && !recording;
  const canStartRecording = Boolean(session?.test_active) && !busy;
  const canScoreNow = Boolean(session?.candidate_answers?.some((item) => item.phase !== "identity")) && !busy;
  const canExportRecord = Boolean(session?.candidate_answers?.length) && !busy;
  const recordButtonDisabled = recording ? false : !canStartRecording;
  const recordButtonText = !session
    ? "Starting..."
    : session.test_active
      ? recording
        ? "Tap to send"
        : "Tap to record"
      : "Test complete";
  const prepRemaining = prepEndsAt
    ? Math.max(0, Math.ceil((prepEndsAt - clockTick) / 1000))
    : 0;

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

  const sessionStats = useMemo(() => {
    const answers = (session?.candidate_answers || []).filter((item) => item.phase !== "identity");
    const stats = (session?.answer_stats || []).filter((item) => item.phase !== "identity");
    const totalSeconds = stats.reduce((sum, item) => sum + (Number(item.duration) || 0), 0);
    const wpmValues = stats
      .map((item) => Number(item.words_per_minute))
      .filter((value) => Number.isFinite(value) && value > 0);
    const averageWpm = wpmValues.length
      ? Math.round(wpmValues.reduce((sum, value) => sum + value, 0) / wpmValues.length)
      : null;
    return {
      answered: answers.length,
      audio: stats.filter((item) => item.source === "audio").length,
      text: stats.filter((item) => item.source === "text").length,
      totalDuration: formatDuration(totalSeconds),
      averageWpm: averageWpm ? `${averageWpm}` : "-",
    };
  }, [session?.answer_stats, session?.candidate_answers]);

  const configWarning = healthInfo?.config?.api_key_configured === false
    ? "Preview mode: the backend is running, but API_KEY is not configured. You can inspect the interface and type answers, but AI replies, transcription, TTS, and scoring need the backend API key."
    : "";
  const stageDescription = isPracticeMode
    ? "Practice mode: instant spoken feedback and natural answer upgrades."
    : "Mock mode: fewer interruptions, final score after the test.";
  const showPart1TopicSelect = practiceType === "part1" && practiceOptions.part1_topics.length;
  const showCueCardSelect =
    (practiceType === "part2" || practiceType === "part3") && practiceOptions.cue_cards.length;
  const hasStageControls = Boolean(prepRemaining > 0 || showPart1TopicSelect || showCueCardSelect);

  useEffect(() => {
    let restored = false;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const saved = raw ? JSON.parse(raw) : null;
      if (saved?.session?.messages?.length) {
        setSession(saved.session);
        setReport(saved.report || "");
        setAudioEnabled(saved.audioEnabled ?? true);
        setTrainingMode(saved.trainingMode || (saved.session.practice_mode ? "practice" : "mock"));
        setPracticeType(saved.practiceType || saved.session.practice_type || "full");
        setSelectedPart1Topic(saved.selectedPart1Topic || "");
        setSelectedCueCardTitle(saved.selectedCueCardTitle || "");
        setReviewBeforeSend(Boolean(saved.reviewBeforeSend));
        if (saved.prepEndsAt && saved.prepEndsAt > Date.now()) {
          setPrepEndsAt(saved.prepEndsAt);
        }
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
    let cancelled = false;
    healthCheck()
      .then((health) => {
        if (!cancelled) {
          setHealthInfo(health);
        }
      })
      .catch(() => {
        // createFreshSession also performs a health check; this is only for restored sessions.
      });
    fetchPracticeOptions()
      .then((options) => {
        if (!cancelled) {
          setPracticeOptions({
            part1_topics: options.part1_topics || [],
            cue_cards: options.cue_cards || [],
          });
        }
      })
      .catch(() => {
        // Practice can still start with random topics if the option endpoint is unavailable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!storageReady || session || busy || startupRecoveryAttemptedRef.current) return;
    startupRecoveryAttemptedRef.current = true;
    createFreshSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy, session, storageReady]);

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
        trainingMode,
        practiceType,
        selectedPart1Topic,
        selectedCueCardTitle,
        reviewBeforeSend,
        prepEndsAt,
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    } catch (_) {
      // Storage can be blocked in private mode or embedded mobile WebViews.
      // The app should still work; it will just skip refresh recovery.
    }
  }, [
    audioEnabled,
    trainingMode,
    practiceType,
    prepEndsAt,
    report,
    reviewBeforeSend,
    selectedCueCardTitle,
    selectedPart1Topic,
    session,
    storageReady,
  ]);

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
    if (!prepEndsAt) return undefined;
    const timer = window.setInterval(() => {
      const now = Date.now();
      setClockTick(now);
      if (prepEndsAt <= now) {
        setPrepEndsAt(null);
      }
    }, 500);
    return () => window.clearInterval(timer);
  }, [prepEndsAt]);

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
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
    }
    audioRef.current = null;
    audioUrlRef.current = "";
  }

  function clearPendingSpeech() {
    if (pendingSpeechUrlRef.current) {
      URL.revokeObjectURL(pendingSpeechUrlRef.current);
    }
    pendingSpeechUrlRef.current = "";
    setPendingSpeechUrl("");
    setPendingSpeechText("");
  }

  async function playAudioUrl(url) {
    const audio = new Audio(url);
    audio.playsInline = true;
    audio.preload = "auto";
    audioRef.current = audio;
    audioUrlRef.current = url;
    audio.addEventListener(
      "ended",
      () => {
        if (audioRef.current === audio) {
          URL.revokeObjectURL(url);
          audioRef.current = null;
          audioUrlRef.current = "";
        }
      },
      { once: true },
    );
    await audio.play();
  }

  async function createFreshSession(
    nextPracticeType = practiceType,
    nextPart1Topic = selectedPart1Topic,
    nextCueCardTitle = selectedCueCardTitle,
    nextTrainingMode = trainingMode,
  ) {
    recorderRef.current?.cleanup?.();
    recorderRef.current = null;
    stopCurrentAudio();
    clearPendingSpeech();
    lastRecordingRef.current = null;
    setCanRetryRecording(false);
    const nextIsPracticeMode = nextTrainingMode === "practice";
    setTrainingMode(nextTrainingMode);
    setPracticeType(nextPracticeType);
    setSelectedPart1Topic(nextPart1Topic);
    setSelectedCueCardTitle(nextCueCardTitle);
    setSession(null);
    setRecording(false);
    setElapsed(0);
    setError("");
    setReport("");
    setDraft("");
    setPrepEndsAt(null);
    setBusy("starting");
    try {
      const health = await healthCheck();
      setHealthInfo(health);
      const data = await startSession({
        ...DEFAULT_SETTINGS,
        practice_mode: nextIsPracticeMode,
        answer_expansion_mode: nextIsPracticeMode,
        practice_type: nextPracticeType,
        part1_topic: nextPart1Topic || null,
        cue_card_title: nextCueCardTitle || null,
      });
      setSession(data.session);
      setAudioEnabled(data.session.voice_playback_enabled);
      if (data.session.phase === "part2_long") {
        const endsAt = Date.now() + 60_000;
        setClockTick(Date.now());
        setPrepEndsAt(endsAt);
      }
    } catch (err) {
      setError(friendlyError(err, "Failed to start session."));
    } finally {
      setBusy("");
    }
  }

  async function playSpeech(text) {
    if (!audioEnabled || !text) return;
    stopCurrentAudio();
    clearPendingSpeech();
    let url = "";
    try {
      const blob = await synthesizeSpeech(text);
      url = URL.createObjectURL(blob);
      if (isLikelyIOSDevice()) {
        pendingSpeechUrlRef.current = url;
        setPendingSpeechUrl(url);
        setPendingSpeechText(text);
        return;
      }
      await playAudioUrl(url);
    } catch (err) {
      if (!url) {
        setError(friendlyError(err, "Voice playback is temporarily unavailable. You can continue with the visible text."));
        return;
      }
      if (url) {
        audioRef.current = null;
        audioUrlRef.current = "";
        pendingSpeechUrlRef.current = url;
        setPendingSpeechUrl(url);
        setPendingSpeechText(text);
      }
      if (/play|autoplay|notallowed/i.test(err?.message || "")) {
        return;
        setError("iPhone Safari blocked autoplay. Tap “Play Victoria” to hear this reply.");
      }
    }
  }

  async function playPendingSpeech() {
    if (!pendingSpeechUrl) return;
    setError("");
    stopCurrentAudio();
    const url = pendingSpeechUrl;
    const text = pendingSpeechText;
    pendingSpeechUrlRef.current = "";
    setPendingSpeechUrl("");
    setPendingSpeechText("");
    try {
      await playAudioUrl(url);
    } catch (_) {
      pendingSpeechUrlRef.current = url;
      setPendingSpeechUrl(url);
      setPendingSpeechText(text);
      setError("Audio still could not play. Please check Safari's sound mode and tap Play Victoria again.");
    }
  }

  function toggleAudioEnabled() {
    setAudioEnabled((value) => {
      if (value) {
        stopCurrentAudio();
        clearPendingSpeech();
      }
      return !value;
    });
  }

  function changePracticeType(event) {
    const nextPracticeType = event.target.value;
    if (nextPracticeType === practiceType && session) return;
    createFreshSession(nextPracticeType, selectedPart1Topic, selectedCueCardTitle, trainingMode);
  }

  function changeTrainingMode(event) {
    const nextTrainingMode = event.target.value;
    if (nextTrainingMode === trainingMode && session) return;
    createFreshSession(practiceType, selectedPart1Topic, selectedCueCardTitle, nextTrainingMode);
  }

  function changePart1Topic(event) {
    const nextTopic = event.target.value;
    setSelectedPart1Topic(nextTopic);
    createFreshSession(practiceType, nextTopic, selectedCueCardTitle, trainingMode);
  }

  function changeCueCardTitle(event) {
    const nextTitle = event.target.value;
    setSelectedCueCardTitle(nextTitle);
    createFreshSession(practiceType, selectedPart1Topic, nextTitle, trainingMode);
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
    setCanRetryRecording(false);
    lastRecordingRef.current = null;
    setReport("");
    setPrepEndsAt(null);
    stopCurrentAudio();
    clearPendingSpeech();
    resetComposerAfterAnswer();
    try {
      const data = await sendAnswer({
        session,
        answer: cleaned,
        source,
        duration,
      });
      setSession(data.session);
      if (data.start_prep_timer) {
        const endsAt = Date.now() + 60_000;
        setClockTick(Date.now());
        setPrepEndsAt(endsAt);
      }
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

  function handleTextComposerKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent?.isComposing) return;
    event.preventDefault();
    if (draft.trim() && canAnswer) {
      void submitAnswer(draft, "text", null);
    }
  }

  async function handleTranscribedAudio(text, duration) {
    if (reviewBeforeSend) {
      setDraft(text);
      setMode("text");
      setBusy("");
    } else {
      await submitAnswer(text, "audio", duration);
    }
    lastRecordingRef.current = null;
    setCanRetryRecording(false);
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
        setCanRetryRecording(false);
        lastRecordingRef.current = null;
      } catch (err) {
        recorderRef.current?.cleanup?.();
        recorderRef.current = null;
        setMode("text");
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
      lastRecordingRef.current = result;
      const transcription = await transcribeAudio(result.blob);
      const text = transcription.text || "";
      if (!text.trim()) {
        throw new Error("No clear speech was detected.");
      }
      await handleTranscribedAudio(text, result.duration);
    } catch (err) {
      recorderRef.current?.cleanup?.();
      recorderRef.current = null;
      setElapsed(0);
      setMode("text");
      setCanRetryRecording(Boolean(lastRecordingRef.current?.blob));
      setError(friendlyError(err, "Recording could not be sent."));
      setBusy("");
    }
  }

  async function retryLastRecording() {
    const result = lastRecordingRef.current;
    if (!result?.blob || busy) return;
    setError("");
    setBusy("transcribing");
    try {
      const transcription = await transcribeAudio(result.blob);
      const text = transcription.text || "";
      if (!text.trim()) {
        throw new Error("No clear speech was detected.");
      }
      await handleTranscribedAudio(text, result.duration);
    } catch (err) {
      setCanRetryRecording(true);
      setError(friendlyError(err, "Recording could not be sent."));
      setBusy("");
    }
  }

  async function requestReport() {
    if (!session) return;
    setError("");
    stopCurrentAudio();
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

  function downloadPracticeRecord() {
    if (!session) return;
    downloadTextFile(
      `examiner-victoria-practice-record-${safeDateStamp()}.txt`,
      buildPracticeRecordText(session, report),
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="eyebrow">IELTS Speaking Coach</div>
          <h1>Examiner Victoria</h1>
          <div className="mobile-stage-summary" aria-label="Current IELTS practice status">
            <div className="mobile-stage-row">
              <div className="stage-line">
                <span className="stage-pill">{currentPhase}</span>
                <span className={`training-pill ${isPracticeMode ? "practice" : "mock"}`}>
                  {isPracticeMode ? "Practice" : "Mock"}
                </span>
              </div>
              {session ? (
                <div className="mobile-stats" aria-label="Current practice summary">
                  <strong>{sessionStats.answered}</strong> ans
                  <span>·</span>
                  <strong>{sessionStats.averageWpm}</strong> WPM
                  <span>·</span>
                  <strong>{sessionStats.totalDuration}</strong>
                </div>
              ) : null}
            </div>
            <div className="progress-track">
              <div style={{ width: `${stageProgress}%` }} />
            </div>
          </div>
        </div>
        <div className="top-actions">
          <label className="practice-select">
            <span>Training</span>
            <select value={trainingMode} onChange={changeTrainingMode} disabled={Boolean(busy) || recording}>
              {TRAINING_MODES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="practice-select">
            <span>Flow</span>
            <select value={practiceType} onChange={changePracticeType} disabled={Boolean(busy) || recording}>
              {PRACTICE_TYPES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <button className="ghost-button" type="button" onClick={toggleAudioEnabled}>
            {audioEnabled ? "Sound on" : "Sound off"}
          </button>
          {canScoreNow ? (
            <button className="ghost-button" type="button" onClick={requestReport}>
              Score
            </button>
          ) : null}
          {canExportRecord ? (
            <button className="ghost-button" type="button" onClick={downloadPracticeRecord}>
              Export
            </button>
          ) : null}
          <button className="ghost-button" type="button" onClick={() => createFreshSession()}>
            Restart
          </button>
        </div>
        <div className="mobile-stage-summary mobile-stage-summary-wide" aria-label="Current IELTS practice status">
          <div className="mobile-stage-row">
            <div className="stage-line">
              <span className="stage-pill">{currentPhase}</span>
              <span className={`training-pill ${isPracticeMode ? "practice" : "mock"}`}>
                {isPracticeMode ? "Practice" : "Mock"}
              </span>
            </div>
            {session ? (
              <div className="mobile-stats" aria-label="Current practice summary">
                <strong>{sessionStats.answered}</strong> ans
                <span>·</span>
                <strong>{sessionStats.averageWpm}</strong> WPM
                <span>·</span>
                <strong>{sessionStats.totalDuration}</strong>
              </div>
            ) : null}
          </div>
          <div className="progress-track">
            <div style={{ width: `${stageProgress}%` }} />
          </div>
        </div>
      </header>

      <aside className={`stage-card ${hasStageControls ? "has-stage-controls" : ""}`}>
        <div className="stage-main">
          <div className="stage-copy">
            <div className="stage-line">
              <span className="stage-pill">{currentPhase}</span>
              <span className={`training-pill ${isPracticeMode ? "practice" : "mock"}`}>
                {isPracticeMode ? "Practice" : "Mock"}
              </span>
            </div>
            <p>{session?.phase === "part3" ? "Dynamic follow-up loop" : stageDescription}</p>
          </div>
          {session ? (
            <div className="session-mini" aria-label="Current practice summary">
              <span><strong>{sessionStats.answered}</strong> answers</span>
              <span><strong>{sessionStats.averageWpm}</strong> WPM</span>
              <span><strong>{sessionStats.totalDuration}</strong></span>
            </div>
          ) : null}
        </div>
        {prepRemaining > 0 ? (
          <div className="prep-timer" aria-live="polite">
            Part 2 prep time <strong>{formatDuration(prepRemaining)}</strong>
          </div>
        ) : null}
        {showPart1TopicSelect ? (
          <label className="topic-select">
            <span>Topic</span>
            <select
              value={selectedPart1Topic}
              onChange={changePart1Topic}
              disabled={Boolean(busy) || recording}
            >
              <option value="">Random topic</option>
              {practiceOptions.part1_topics.map((topic) => (
                <option key={topic} value={topic}>
                  {topic}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {showCueCardSelect ? (
          <label className="topic-select">
            <span>Cue card</span>
            <select
              value={selectedCueCardTitle}
              onChange={changeCueCardTitle}
              disabled={Boolean(busy) || recording}
            >
              <option value="">Random cue card</option>
              {practiceOptions.cue_cards.map((card) => (
                <option key={card.title} value={card.title}>
                  {card.title}
                </option>
              ))}
            </select>
          </label>
        ) : null}
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

        {error ? (
          <div className="error-card">
            <span>{error}</span>
            {canRetryRecording ? (
              <button type="button" onClick={retryLastRecording} disabled={Boolean(busy)}>
                Retry transcription
              </button>
            ) : null}
          </div>
        ) : null}

        {pendingSpeechUrl ? (
          <div className="audio-card">
            <div>
              <strong>Victoria's voice is ready</strong>
              <span>iPhone Safari needs a tap before playing audio.</span>
            </div>
            <button type="button" onClick={playPendingSpeech}>
              Play Victoria
            </button>
          </div>
        ) : null}

        {configWarning ? <div className="notice-card">{configWarning}</div> : null}

        {report ? (
          <section className="report-card">
            <h2>Final report</h2>
            <ReportView report={report} />
            <div className="report-actions">
              <button type="button" className="ghost-button" onClick={downloadReport}>
                Download report
              </button>
              <button type="button" className="ghost-button" onClick={downloadTranscript}>
                Download transcript
              </button>
              <button type="button" className="ghost-button" onClick={downloadPracticeRecord}>
                Download practice record
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
              <textarea
                value={draft}
                disabled={!canAnswer && !draft}
                placeholder="Type your answer..."
                autoComplete="off"
                rows={1}
                aria-label="Type your answer. Press Enter to send, Shift Enter for a new line."
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleTextComposerKeyDown}
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
