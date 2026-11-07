import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  ChevronRight,
  FileText,
  Play,
  Upload,
  Workflow,
} from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Button } from "./components/ui/button";
import "./styles/landing.css";

type CsvImport = { name: string; text: string };

const sampleThemes = [
  {
    theme: "Export limits",
    count: 87,
    sentiment: "danger",
    quote: "“We almost churned over the export limits.” — 2★, G2, Nov",
  },
  {
    theme: "Onboarding speed",
    count: 64,
    sentiment: "accent",
    quote: "“Live in a week without an engineer.” — 5★, Capterra, Oct",
  },
  {
    theme: "Reporting depth",
    count: 46,
    sentiment: "warn",
    quote: "“Dashboards are thin for the price.” — 3★, G2, Sep",
  },
];

const sentimentLabels: Record<string, string> = {
  danger: "RISK",
  accent: "POSITIVE",
  warn: "CAUTION",
};

const plays = [
  {
    title: "Steal Your Competitor's Themes",
    replaces: "THE COMPETITIVE INTEL SPREADSHEET + A WEEKEND OF G2",
    points: [
      "Every review of [Competitor] read, none skimmed",
      "Themes counted and ranked, with pull-quotes attached",
      "Pain points your battlecard can quote verbatim",
      "Re-runs identically when their next release lands",
    ],
  },
  {
    title: "What Your Market Actually Hears",
    replaces: "THE VOC SUMMARY NOBODY READS",
    points: [
      "Your claims vs. the market's actual words, side by side",
      "Resonance counted: what buyers repeat back, what they ignore",
      "Every theme traceable to dated, attributed quotes",
      "Runs on your last 800 reviews in three minutes",
    ],
  },
  {
    title: "The Churn Whispers",
    replaces: "SKIMMING ANGRY REVIEWS AND REMEMBERING THREE",
    points: [
      "1–2★ reviews extracted into churn-risk claims",
      "Claims sorted by theme frequency, not by volume of anger",
      "Sales-ready lines with attribution",
      "New reviews re-scanned on demand",
    ],
  },
];

const methodology = [
  ["Theme fidelity", "Does the extracted theme name the real complaint?", "“Export limits” ≠ “performance issues”"],
  ["Quote attribution", "Date, rating, and source attached to every quote", "—"],
  ["Coverage", "Every row classified or explicitly discarded, with the count shown", "940 / 1,178 kept, 238 discarded — visible"],
  ["Schema validity", "Extractions validated; failures repaired or retried", "931 valid, 9 repaired, 0 silent drops"],
  ["Reproducibility", "Same CSV, same rubric, same themes next quarter", "Temperature-0 extraction"],
];

const pipeline = [
  ["IMPORT", "1,200", "1,200"],
  ["CLEAN", "1,200", "1,178"],
  ["FILTER", "1,178", "940"],
  ["EXTRACT", "940", "940"],
  ["AGGREGATE", "940", "46 themes"],
];

export function LandingPage({
  onOpenWorkspace,
  onImportCsv,
}: {
  onOpenWorkspace: () => void;
  onImportCsv: (file: CsvImport) => boolean;
}) {
  const [scrolled, setScrolled] = useState(false);
  const [selectedPlay, setSelectedPlay] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [importError, setImportError] = useState("");
  const [importedName, setImportedName] = useState("");
  const [signalAligned, setSignalAligned] = useState(false);
  const [signalFallback, setSignalFallback] = useState<"failed" | "disabled" | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.setAttribute("data-revealed", "true"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.setAttribute("data-revealed", "true");
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.14, rootMargin: "0px 0px -6% 0px" },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  function tiltElement(event: ReactPointerEvent<HTMLElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    event.currentTarget.style.setProperty("--tilt-x", `${(x - 0.5) * 3}deg`);
    event.currentTarget.style.setProperty("--tilt-y", `${(0.5 - y) * 3}deg`);
  }

  function resetTilt(event: { currentTarget: HTMLElement }) {
    event.currentTarget.style.setProperty("--tilt-x", "0deg");
    event.currentTarget.style.setProperty("--tilt-y", "0deg");
  }

  function goTo(id: string) {
    document.getElementById(id)?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  }

  async function importFile(file: File | undefined) {
    setImportError("");
    if (!file) return;
    if (!file.name.toLocaleLowerCase().endsWith(".csv") && file.type !== "text/csv") {
      setImportError("Choose a CSV file exported from G2 or Capterra.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setImportError("This local import is limited to 2 MB. Split the export and try again.");
      return;
    }
    let text: string;
    try {
      text = await file.text();
    } catch {
      setImportError("The CSV could not be read. Check the file and try again.");
      return;
    }
    if (!text.trim()) {
      setImportError("That file has no rows we can read. Export the full CSV from G2 or Capterra — not the preview.");
      return;
    }
    if (!onImportCsv({ name: file.name.replace(/\.csv$/i, ""), text })) {
      setImportError("The CSV could not be passed to the workspace. Check that browser storage is available.");
      return;
    }
    setImportedName(file.name);
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    void importFile(event.currentTarget.files?.[0]);
    event.currentTarget.value = "";
  }

  function onFileDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    void importFile(event.dataTransfer.files[0]);
  }

  function downloadOnePager() {
    const content = [
      "n3rf · Steal Your Competitor's Themes",
      "",
      "1,200 reviews in → 940 after filters → 46 themes out",
      "",
      ...sampleThemes.map(({ theme, count, quote }) => `${theme} (${count})\n${quote}`),
      "",
      "Built on a published rubric. Your key, your data.",
    ].join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "n3rf-review-intel-one-pager.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="landing-shell">
      <header className={`landing-nav${scrolled ? " is-scrolled" : ""}`}>
        <button className="landing-audience" type="button" onClick={() => goTo("landing-hero")}>
          <Workflow /> <span>FOR: PRODUCT MARKETERS</span>
        </button>
        <nav aria-label="Product page">
          <button type="button" onClick={() => goTo("landing-artifact")}>The report</button>
          <button type="button" onClick={() => goTo("landing-method")}>Methodology</button>
          <button type="button" onClick={() => goTo("landing-plays")}>Plays</button>
        </nav>
        <Button variant="ghost" onClick={onOpenWorkspace}>Workspace <ArrowUpRight /></Button>
      </header>

      <section className="landing-hero" id="landing-hero">
        <SignalField aligned={signalAligned} fallback={signalFallback} onFallback={setSignalFallback} />
        <div className="landing-hero-inner">
          <div className="landing-hero-frame">
            <span className="hero-bracket hero-bracket-tl" />
            <span className="hero-bracket hero-bracket-tr" />
            <span className="hero-bracket hero-bracket-bl" />
            <span className="hero-bracket hero-bracket-br" />
            <div className="landing-hero-copy">
              <p className="landing-qualifier">For product marketers who own the message.</p>
              <h1>Your market already wrote your messaging. It&apos;s sitting in 1,200 reviews.</h1>
              <p className="landing-subhead">
                Paste a review CSV — yours or a competitor&apos;s. One extraction per row, every theme counted,
                quotes with dates and star ratings attached. No signup, no key for the sample run.
              </p>
              <div className="landing-play-picker" role="group" aria-label="Choose a play">
                {plays.slice(0, 2).map((play, index) => (
                  <button
                    className={`landing-play-choice${selectedPlay === index ? " is-selected" : ""}`}
                    type="button"
                    key={play.title}
                    aria-pressed={selectedPlay === index}
                    onClick={() => setSelectedPlay(index)}
                    onPointerEnter={() => setSignalAligned(true)}
                    onPointerLeave={() => setSignalAligned(false)}
                    onPointerMove={tiltElement}
                    onBlur={resetTilt}
                  >
                    <strong><Play /> {play.title}</strong>
                    <span>REPLACES: {play.replaces}</span>
                  </button>
                ))}
              </div>
              <div
                className="landing-hero-actions"
                onPointerEnter={() => setSignalAligned(true)}
                onPointerLeave={() => setSignalAligned(false)}
              >
                <Button
                  variant="primary"
                  onClick={() => goTo("landing-artifact")}
                  onPointerMove={tiltElement}
                  onPointerLeave={resetTilt}
                >
                  <Play /> Run the play
                </Button>
                <p className="landing-sample-note">Sample report uses prepared example data; no account or model key required.</p>
              </div>
              <button
                className={`landing-upload${dragging ? " is-dragging" : ""}`}
                type="button"
                onClick={() => fileInput.current?.click()}
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onFileDrop}
              >
                <Upload />
                <span>{importedName ? `${importedName} · opening workspace…` : "…or drop your review CSV here"}</span>
                <ChevronRight />
              </button>
              <input
                ref={fileInput}
                className="landing-file-input"
                type="file"
                accept=".csv,text/csv"
                aria-label="Choose a review CSV"
                onChange={onFileChange}
              />
              {importError && <p className="landing-import-error" role="alert">{importError}</p>}
            </div>
            <div className="landing-proof" aria-label="Sample run summary">
              <span className="landing-proof-dot" />
              <span><b>1,200</b> ROWS IN</span><ArrowRight />
              <span><b>940</b> AFTER FILTERS</span><ArrowRight />
              <span><b>46</b> THEMES OUT</span>
              <i>· EVERY ROW COUNTED</i>
            </div>
          </div>
        </div>
      </section>

      <div className="landing-content">
        <section className="landing-section landing-artifact" id="landing-artifact" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">SAMPLE REPORT · PREPARED EXAMPLE DATA</span>
            <h2>This is what the play returns. A prepared sample run, row by row.</h2>
          </div>
          <div className="artifact-grid">
            <div className="artifact-table-panel">
              <div className="artifact-panel-heading"><span>COMPETITIVE INTEL / THEMES</span><small>TOP 3 OF 46</small></div>
              <div className="artifact-table-scroll">
                <table className="artifact-table">
                  <thead><tr><th>THEME</th><th>COUNT</th><th>SENTIMENT</th><th>REPRESENTATIVE QUOTE</th></tr></thead>
                  <tbody>
                    {sampleThemes.map((theme) => (
                      <tr key={theme.theme}>
                        <th scope="row">{theme.theme}</th>
                        <td className="artifact-count">{theme.count}</td>
                        <td>
                          <span className={`sentiment-mark ${theme.sentiment}`}>
                            <i aria-hidden="true" />
                            <small>{sentimentLabels[theme.sentiment]}</small>
                          </span>
                        </td>
                        <td className="artifact-quote">{theme.quote}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="theme-chart" aria-label="Theme counts: Export limits 87, Onboarding speed 64, Reporting depth 46">
                <p>THEME FREQUENCY / TOP 3</p>
                {sampleThemes.map((theme, index) => (
                  <div className="theme-bar-row" key={theme.theme}>
                    <span>{theme.theme}</span><div><i className={theme.sentiment} style={{ width: `${(theme.count / 87) * 100}%` }} data-series={index} /></div><b>{theme.count}</b>
                  </div>
                ))}
              </div>
            </div>
            <div
              className="run-trace-glass"
              data-reveal
              onPointerMove={tiltElement}
              onPointerLeave={resetTilt}
            >
              <div className="run-trace-heading"><span>RUN TRACE</span><span className="run-trace-state">SAMPLE · COMPLETE</span></div>
              <p className="run-trace-meta">NODE <span>ROWS IN</span><span>ROWS OUT</span></p>
              {pipeline.map(([name, before, after], index) => (
                <div className={`run-trace-row trace-${name.toLowerCase()}`} key={name}>
                  <span><i>{String(index + 1).padStart(2, "0")}</i>{name}</span><b>{before}</b><b>{after}</b>
                </div>
              ))}
              <div className="run-trace-foot">EXTRACT <span>940 CALLS · 931 VALID · <b className="repair-count">9 REPAIRED</b></span></div>
              <div className="run-trace-micro">Prepared sample trace · no live model calls made</div>
            </div>
          </div>
        </section>

        <section className="landing-section landing-how" id="landing-how" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">THE PLAY, UNDER THE HOOD</span>
            <h2>Three minutes, three moves.</h2>
            <p>Paste the CSV → the play reads every row and extracts against a published rubric → you get the report. The pipeline is a picture you can read — and every row&apos;s journey is visible.</p>
          </div>
          <div className="pipeline-map" aria-label="Import, Clean, Filter, Extract, Aggregate, Report">
            {["Import", "Clean", "Filter", "Extract", "Aggregate", "Report"].map((label, index) => (
              <div className="pipeline-step" key={label}>
                <span>{String(index + 1).padStart(2, "0")}</span><strong>{label}</strong>
                {index < 5 && <ArrowRight aria-hidden="true" />}
              </div>
            ))}
          </div>
          <p className="pipeline-note"><ArrowDown /> Every step shows its input rows, output rows, duration, and sample.</p>
        </section>

        <section className="landing-ritual" data-reveal>
          <span className="landing-kicker">THE QUARTERLY RITUAL</span>
          <h2>The quarterly ritual</h2>
          <p>Export the CSV. Skim the top 50. Feed batches to ChatGPT. Get confident mush you can&apos;t reproduce. Do it again next quarter — different answers. The ritual isn&apos;t lazy; it&apos;s just built for 30 reviews, and you have 1,200.</p>
          <strong className="landing-kill-line">ChatGPT was never designed to read 1,200 reviews. This was.</strong>
        </section>

        <section className="landing-models" aria-label="Your model, your key" data-reveal>
          <article><span className="landing-kicker">YOUR KEY</span><p>Runs on your OpenAI, Groq, or Anthropic key.</p><small>OPENAI · GROQ · ANTHROPIC</small></article>
          <article><span className="landing-kicker">YOUR DATA</span><p>Your key. Your model account. We never train on your rows.</p><small>PRIVATE BY DESIGN</small></article>
          <article><span className="landing-kicker">YOUR ECONOMICS</span><p>Runs cost what the model costs — no markup, no credits.</p><small>PROVIDER PRICING</small></article>
        </section>

        <section className="landing-section landing-method" id="landing-method" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">CHECK OUR MATH</span>
            <h2>Check our math</h2>
            <p>If a theme count looks wrong, you can see exactly which rows produced it.</p>
          </div>
          <div className="method-table-wrap">
            <table className="method-table">
              <thead><tr><th>DIMENSION</th><th>WHAT IT MEASURES</th><th>ANCHOR EXAMPLE</th></tr></thead>
              <tbody>{methodology.map(([dimension, measure, example]) => (
                <tr key={dimension}><th scope="row">{dimension}</th><td>{measure}</td><td>{example}</td></tr>
              ))}</tbody>
            </table>
          </div>
          <pre className="sample-extraction"><span>theme</span>           <b>“Export limits”</b>{"\n"}<span>frequency</span>       <b>87</b>{"\n"}<span>sentiment</span>       <b>“danger”</b>{"\n"}<span>source</span>          <b>“G2”</b>{"\n"}<span>rating</span>          <b>2</b>{"\n"}<span>quote</span>           <b>“We almost churned over the export limits.”</b></pre>
        </section>

        <section className="landing-section landing-plays" id="landing-plays" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">PICK A PLAY</span>
            <h2>Pick a play. It goes live in minutes.</h2>
          </div>
          <div className="landing-play-list">
            {plays.map((play, index) => (
              <article
                className="landing-play-card"
                key={play.title}
                onPointerMove={tiltElement}
                onPointerLeave={resetTilt}
              >
                <div className="landing-play-card-heading">
                  <span className="landing-play-index">PLAY / 0{index + 1}</span>
                  <span className="landing-replaces">REPLACES: {play.replaces}</span>
                </div>
                <h3>{play.title}</h3>
                <ul>{play.points.map((point) => <li key={point}>{point}</li>)}</ul>
                <Button onClick={() => { setSelectedPlay(Math.min(index, 1)); goTo("landing-hero"); }}>Run this play <ArrowRight /></Button>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-onepager">
          <div>
            <span className="landing-kicker">THE ONE-PAGER</span>
            <h2>Want the whole picture before you run anything?</h2>
            <p>What 1,200 reviewers said about [a category everyone recognizes], condensed to one page.</p>
            <small>This local build downloads the sample one-pager directly. It does not collect email addresses.</small>
          </div>
          <Button className="landing-download-button" onClick={downloadOnePager}><FileText /> Download the one-pager</Button>
        </section>

        <footer className="landing-footer">
          <div className="landing-platform-reveal">
            <p>One wedge, done completely. When you want win/loss mining and competitive intel on the same engine <button type="button" onClick={onOpenWorkspace}>→</button></p>
            <Button onClick={onOpenWorkspace}>See what&apos;s on the engine <ArrowUpRight /></Button>
          </div>
          <div className="landing-footer-meta"><span>n3rf · Built on a published rubric · Your key, your data · © 2026</span><button type="button" onClick={onOpenWorkspace}>OPEN WORKSPACE <ChevronRight /></button></div>
        </footer>
      </div>
    </main>
  );
}

function SignalField({
  aligned,
  fallback,
  onFallback,
}: {
  aligned: boolean;
  fallback: "failed" | "disabled" | null;
  onFallback: (fallback: "failed" | "disabled") => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const alignedRef = useRef(aligned);
  alignedRef.current = aligned;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches || window.innerWidth < 640) {
      onFallback("disabled");
      return;
    }
    if (!canvas.getContext("webgl2") && !canvas.getContext("webgl")) {
      onFallback("failed");
      return;
    }

    let disposed = false;
    let initialized = false;
    let visible = false;
    let frame = 0;
    let startTime = 0;
    let signalField: import("./lib/signal-field").SignalField | null = null;
    let resizeObserver: ResizeObserver | null = null;
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      visible = Boolean(entry?.isIntersecting);
      if (!visible) {
        window.cancelAnimationFrame(frame);
        return;
      }
      if (!initialized) {
        initialized = true;
        void initialize();
        return;
      }
      startTime = performance.now();
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(animate);
    });

    function animate(time: number) {
      if (!visible || disposed || !signalField) return;
      signalField.render((time - startTime) / 1000, alignedRef.current);
      frame = window.requestAnimationFrame(animate);
    }

    async function initialize() {
      try {
        const { createSignalField } = await import("./lib/signal-field");
        if (disposed || !canvas) return;
        signalField = createSignalField(canvas);
        resizeObserver = new ResizeObserver(() => signalField?.resize());
        resizeObserver.observe(canvas);
        if (visible) {
          startTime = performance.now();
          frame = window.requestAnimationFrame(animate);
        }
      } catch {
        if (!disposed) onFallback("failed");
      }
    }

    intersectionObserver.observe(canvas);
    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      signalField?.dispose();
    };
  }, [onFallback]);

  return (
    <>
      <canvas
        ref={canvasRef}
        className={`signal-canvas${aligned ? " is-aligned" : ""}${fallback ? ` signal-canvas-${fallback}` : ""}`}
        aria-hidden="true"
      />
      <svg className="signal-field" viewBox="0 0 600 520" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
      <g className="signal-orbits" fill="none" stroke="var(--purple-light)" strokeWidth="1">
        <path d="M110 130h104l34 34h72M190 260h104l34-34h96M135 390h94l36-36h130" />
        <path d="M248 164v54l-42 42 42 42v32M394 164v28l-32 32v64l32 32v34" />
      </g>
      <g className="signal-points" fill="var(--info)">
        {Array.from({ length: 24 }, (_, index) => {
          const x = 180 + ((index * 71 + 13) % 390);
          const y = 45 + ((index * 97 + 29) % 420);
          return <rect key={index} x={x} y={y} width="2" height="2" opacity={index % 2 ? 0.25 : 0.42} />;
        })}
      </g>
      <g className="signal-streams" fill="none" stroke="var(--info)" strokeWidth="1">
        <path d="M110 130h104l34 34h72M190 260h104l34-34h96M135 390h94l36-36h130" />
      </g>
      <rect className="signal-accent-particle" x="110" y="127" width="6" height="6" fill="var(--accent)" />
      </svg>
    </>
  );
}
