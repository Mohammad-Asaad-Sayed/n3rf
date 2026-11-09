import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  ChevronRight,
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
import { apiFetch } from "./lib/workflow";
import "./styles/landing.css";

type CsvImport = { name: string; text: string };

const enrichedCompanies = [
  {
    company: "Apple",
    domain: "apple.com",
    industry: "technology",
    signal: "Services growth narrative on company site",
  },
  {
    company: "Microsoft",
    domain: "microsoft.com",
    industry: "technology",
    signal: "Cloud + AI positioning on homepage",
  },
  {
    company: "Shopify",
    domain: "shopify.com",
    industry: "ecommerce",
    signal: "Headcount band 5,001–10,000 in source",
  },
  {
    company: "Notion",
    domain: "notion.so",
    industry: "software",
    signal: "Product-led positioning on site",
  },
  {
    company: "Stripe",
    domain: "stripe.com",
    industry: "fintech",
    signal: "Tax expansion note on site",
  },
];

const useCases = [
  { tag: "COMPANIES", title: "Companies", desc: "CEO, funding raised, headcount, tech stack, recent news", cols: "CEO · Funding · Headcount · News" },
  { tag: "PEOPLE", title: "People", desc: "Current employer, job title, published work", cols: "Title · Employer · Published work" },
  { tag: "STARTUPS", title: "Startups", desc: "Latest round, investors, product summary, competitors", cols: "Round · Investors · Summary" },
  { tag: "UNIVERSITIES", title: "Universities", desc: "Ranking, acceptance rate, tuition, notable alumni", cols: "Rank · Tuition · Acceptance" },
  { tag: "PRODUCTS", title: "Products", desc: "Pricing, reviews, feature set, competitors, G2 rating", cols: "Price · Reviews · Features" },
  { tag: "REVIEWS", title: "Reviews", desc: "Theme, sentiment, representative quote + count", cols: "Theme · Sentiment · Quote" },
];

const steps = [
  { n: "01", title: "Load your spreadsheet", desc: "Drop a CSV, TSV or Excel (.xlsx) file at /app. Headers become snake_case columns (Company Name → company_name) instantly, parsed in Python with no new JavaScript libraries." },
  { n: "02", title: "Say what you need", desc: "Smart columns surface first (company, domain, name). Ask AI takes a plain-English prompt; output columns are schema-checked. Drag column chips into prompts — no expression syntax to memorize." },
  { n: "03", title: "Pick a model, check the cost", desc: "Published list prices via GET /pricing (May 2026). Estimate a batch before you run, then Test 5 rows for exact usage. Keys live in the backend environment, never in workflow JSON." },
  { n: "04", title: "Test 5 rows, then run", desc: "Run slices every input chain to 5 rows. Check the sample + rows-in → rows-out + tokens, then run the full batch with concurrency and on_error." },
];

const compareRows = [
  ["Platform fee", "$0, self-hosted", "$149–$800/mo (public page)", "Subscription", "Your time"],
  ["AI research per row", "Paid to provider directly", "Uses Clay credits", "Per-action pricing", "Manual paste"],
  ["500 rows researched", "Provider rate, tokens visible", "Eats credit quota", "Per-action costs", "An afternoon"],
  ["Model choice", "Any OpenAI-compatible + local Ollama", "Claygent's model", "Provider-locked", "One chat model"],
  ["Web search / reader", "Separate SEARCH nodes", "Via Claygent", "Extra apps", "Manual browsing"],
  ["Rows in → out per step", "Yes — the core UI", "No", "No", "No"],
  ["Where rows live", "Your machine (local SQLite)", "Their servers", "Their servers", "Your sheet + chat"],
  ["Rate-limit handling", "Concurrency cap + on_error", "Managed for you", "Managed for you", "You, manually"],
  ["Account required", "No", "Yes, plus a card", "Yes", "Account"],
];

const methodology = [
  ["Row-level traceability", "Which input rows produced this output?", "Every enriched row links back to dated source rows"],
  ["Coverage", "What was kept, dropped, or set aside?", "341 / 498 kept, 157 set aside — visible per node"],
  ["Schema validity", "Did the model return clean JSON?", "489 valid, 9 repaired, 0 silent drops (sample)"],
  ["Cost honesty", "What did this run actually call?", "Call count and tokens shown per run"],
  ["Reproducibility", "Does it run the same next quarter?", "Same CSV, same prompt, same schema + nodes"],
];

const pipeline = [
  ["IMPORT", "500", "500"],
  ["FILTER", "500", "498"],
  ["SEARCH", "498", "498"],
  ["EXTRACT", "498", "498"],
  ["RANK", "498", "341"],
];

const retained = [
  { label: "IMPORT", value: 500, cls: "accent" },
  { label: "FILTER", value: 498, cls: "accent" },
  { label: "SEARCH", value: 498, cls: "warn" },
  { label: "RANK", value: 341, cls: "accent" },
];

const faqs = [
  {
    q: "What is n3rf?",
    a: "A local-first, AI-first workflow builder. Messy rows in, structured rows out, on your own model and key. You wire a graph of nodes, press run, and watch rows in → rows out at every node until the data is the shape you wanted.",
  },
  {
    q: "Is n3rf free?",
    a: "The platform fee is $0 — you run it on your machine. You pay your model provider directly at their published rates. Local Ollama is $0. SEARCH nodes use replenishing free tiers (for example Tavily, Exa, Jina Reader) with no card required to start.",
  },
  {
    q: "How is n3rf different from Clay?",
    a: "Clay is two products: a data aggregator querying 150+ providers in a waterfall, plus an AI research agent. n3rf does the research half as explicit nodes — one LLM node per question plus SEARCH nodes that read the live web per row — with per-step counts, schema repair, and capped concurrency. For licensed contact records, pair it with HTTP Request to your contact provider.",
  },
  {
    q: "Is my data safe with n3rf?",
    a: "This is an architectural claim, not a policy promise. Runs execute in your local FastAPI app with workflows and runs in your local SQLite on your disk. Keys live in environment variables, never in workflow JSON. If the backend is unreachable the editor simulates and says so three ways (amber banner, amber LED, “· simulated”). Nothing is uploaded off your machine except the provider calls you configure.",
  },
  {
    q: "What models does n3rf support?",
    a: "Any provider in one Ask AI node: OpenAI, Groq, Gemini, OpenRouter, Mistral, Hugging Face, Ollama (local) and Cloudflare. Pick a provider in the inspector — model and key name fill in automatically. Custom keeps any OpenAI-compatible endpoint.",
  },
  {
    q: "What if I hit rate limits?",
    a: "Each AI and SEARCH node has tunable concurrency and on_error (error_item / skip / fail) plus max_output_rows caps. The LLM client retries and validates schema, repairing once on failure. The run meta shows llm_calls and token counts so you see the burn.",
  },
  {
    q: "What file formats does n3rf support?",
    a: "CSV, TSV, spreadsheet paste, Manual JSON, Text Lines, File Upload, Field Builder and the sample dataset at /app. Excel (.xlsx) is parsed in Python (standard library only, up to 10 MB) via POST /parse-file and opened as the same CSV canvas — legacy .xls should be resaved as .xlsx. The landing-page import accepts .csv/.tsv/.xlsx up to 10 MB.",
  },
  {
    q: "How much will a run cost before I commit?",
    a: "GET /pricing serves published list prices per 1M tokens (May 2026, $0 platform markup) and POST /pricing/estimate answers a batch. In the editor, Test 5 rows runs only the first 5 rows of every input chain and shows tokens/call counts — then run the full batch with that exact usage in hand.",
  },
  {
    q: "Do I need to create an account?",
    a: "No. n3rf is a single-operator, self-hosted workspace. No sign-up, no card for n3rf itself. You only add provider keys in your shell environment if you want live model calls — the prepared sample needs none.",
  },
  {
    q: "What kind of data can I enrich?",
    a: "Any list where the answer exists in public and the question is specific to you: companies, people, startups, universities, products, reviews. Smart columns lead the pickers, so you click a column and the prompt reads {{company}} — no syntax to memorize.",
  },
];

export function LandingPage({
  onOpenWorkspace,
  onImportCsv,
}: {
  onOpenWorkspace: () => void;
  onImportCsv: (file: CsvImport) => boolean;
}) {
  const [scrolled, setScrolled] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [importError, setImportError] = useState("");
  const [importedName, setImportedName] = useState("");
  const [signalAligned, setSignalAligned] = useState(false);
  const [signalFallback, setSignalFallback] = useState<"failed" | "disabled" | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 24);
      const hero = document.querySelector<HTMLElement>(".landing-hero-frame");
      if (hero) hero.style.setProperty("--hero-shift", String(Math.min(window.scrollY, 600)));
    };
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
    const name = file.name.toLocaleLowerCase();
    const isCsv = name.endsWith(".csv") || name.endsWith(".tsv") || file.type === "text/csv";
    const isXlsx = name.endsWith(".xlsx");
    if (!isCsv && !isXlsx) {
      setImportError("Choose a .csv, .tsv or .xlsx file to try a live run.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setImportError("This local import is limited to 10 MB. Split the file and try again.");
      return;
    }
    if (isXlsx) {
      try {
        const form = new FormData();
        form.append("file", file);
        const response = await apiFetch("/parse-file", { method: "POST", body: form });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Excel file could not be read.");
        const csvText = payload.csvText as string;
        if (!csvText?.trim()) {
          setImportError("That spreadsheet has no rows we can read. Export the full sheet and try again.");
          return;
        }
        if (!onImportCsv({ name: file.name.replace(/\.xlsx$/i, ""), text: csvText })) {
          setImportError("The spreadsheet could not be passed to the workspace.");
          return;
        }
        setImportedName(file.name);
      } catch (error) {
        setImportError(error instanceof Error ? error.message : "The spreadsheet could not be read.");
      }
      return;
    }
    let text: string;
    try {
      text = await file.text();
    } catch {
      setImportError("The file could not be read. Check the file and try again.");
      return;
    }
    if (!text.trim()) {
      setImportError("That file has no rows we can read. Export the full CSV — not just a preview.");
      return;
    }
    if (!onImportCsv({ name: file.name.replace(/\.(csv|tsv)$/i, ""), text })) {
      setImportError("The file could not be passed to the workspace. Check that browser storage is available.");
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

  function downloadSample() {
    const content = [
      "n3rf · Sample run (prepared example data)",
      "",
      "500 rows in → 498 after filters → 341 kept",
      "",
      ...enrichedCompanies.map(
        (c) => `${c.company},${c.domain},${c.industry},${c.signal}`,
      ),
      "",
      "489 valid, 9 repaired, 0 silent drops. Your key, your data. Runs on your machine.",
      "Illustrative example. Real output varies, so always verify.",
    ].join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "n3rf-sample-run.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="landing-shell">
      <header className={`landing-nav${scrolled ? " is-scrolled" : ""}`}>
        <button className="landing-audience" type="button" onClick={() => goTo("landing-hero")}>
          <Workflow /> <span>FOR: OPS ANALYSTS WITH MESSY SHEETS</span>
        </button>
        <nav aria-label="Product page">
          <button type="button" onClick={() => goTo("landing-what")}>What it does</button>
          <button type="button" onClick={() => goTo("landing-how")}>How it works</button>
          <button type="button" onClick={() => goTo("landing-pricing")}>Pricing</button>
          <button type="button" onClick={() => goTo("landing-why")}>Why n3rf</button>
          <button type="button" onClick={() => goTo("landing-faq")}>FAQ</button>
        </nav>
        <Button variant="primary" onClick={onOpenWorkspace}><Upload /> Drop CSV &amp; run <ArrowUpRight /></Button>
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
              <p className="landing-qualifier">$0 platform fee · No sign-up · No card · Python-only backend</p>
              <h1>Enrich a spreadsheet with your own key. Every row counted.</h1>
              <p className="landing-subhead">
                Point it at a CSV or Excel (.xlsx) file, pick the columns you mean,
                check the cost, and every row is researched with AI and live web
                search. You pay the model provider directly and n3rf takes nothing —
                and you see rows-in → rows-out at every node.
              </p>
              <div
                className="landing-hero-actions"
                onPointerEnter={() => setSignalAligned(true)}
                onPointerLeave={() => setSignalAligned(false)}
              >
                <Button
                  variant="primary"
                  onClick={() => fileInput.current?.click()}
                  onPointerMove={tiltElement}
                  onPointerLeave={resetTilt}
                >
                  <Upload /> {importedName ? `${importedName} · opening…` : "Start enriching for free"}
                </Button>
                <Button variant="ghost" onClick={() => goTo("landing-how")}>See how it works <ArrowDown /></Button>
                <p className="landing-sample-note">No signup · no key for the sample · .csv / .tsv / .xlsx up to 10 MB. <button type="button" onClick={() => goTo("landing-artifact")}>See the sample run instead ↓</button></p>
              </div>
              <button
                className={`landing-upload${dragging ? " is-dragging" : ""}`}
                type="button"
                onClick={() => fileInput.current?.click()}
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onFileDrop}
                aria-label="Drop your CSV here"
              >
                <Upload />
                <span>{dragging ? "Release to run your file" : "Drop a .csv / .tsv / .xlsx to open it at /app"}</span>
                <ChevronRight />
              </button>
              <input
                ref={fileInput}
                className="landing-file-input"
                type="file"
                accept=".csv,.tsv,.xlsx,text/csv"
                aria-label="Choose a CSV file"
                onChange={onFileChange}
              />
              {importError && <p className="landing-import-error" role="alert">{importError}</p>}
            </div>
            <div className="landing-proof" aria-label="Sample run summary">
              <span className="landing-proof-dot" />
              <span><b>500</b> ROWS IN</span><ArrowRight />
              <span><b>498</b> AFTER FILTERS</span><ArrowRight />
              <span><b>341</b> KEPT</span>
              <i>· EVERY ROW COUNTED · WE CHARGE $0, ALWAYS</i>
            </div>
            <div className="node-marquee" aria-hidden="true">
              <div className="node-marquee-track">
                {[
                  "Manual JSON",
                  "Tavily Search",
                  "Jina Reader",
                  "Ask AI",
                  "Filter",
                  "Set Fields",
                  "Ask AI",
                  "Exa Search",
                  "Sort",
                  "Ask AI",
                ].map((name) => (
                  <span key={name}>{name} <b>→</b></span>
                ))}
                {[
                  "Manual JSON",
                  "Tavily Search",
                  "Jina Reader",
                  "Ask AI",
                  "Filter",
                  "Set Fields",
                  "Ask AI",
                  "Exa Search",
                  "Sort",
                  "Ask AI",
                ].map((name) => (
                  <span key={`dup-${name}`}>{name} <b>→</b></span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="landing-content">
        <section className="landing-section" id="landing-pain" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">01 · You recognise this before you scroll</span>
            <h2>At 500 rows, the old ways break.</h2>
            <p>Your spreadsheet takes an afternoon. The errors hide where nobody can see them. And credit-based research burns fast.</p>
          </div>
          <section className="landing-models" aria-label="The problem">
            <article><span className="landing-kicker">SPREADSHEET + CHAT WINDOW</span><p>You paste chunks into a chat, paste back prose, and lose track of which row became which.</p><small>NO TRACEABILITY</small></article>
            <article><span className="landing-kicker">ZAPIER / N8N</span><p>Built for triggers and events. Poor at a batch of rows, at per-step counts, at showing where rows disappeared.</p><small>WRONG UNIT OF WORK</small></article>
            <article><span className="landing-kicker">A PYTHON SCRIPT</span><p>Does the job, then becomes the problem. Not inspectable. No per-step visibility. No cost control.</p><small>NOT INSPECTABLE</small></article>
          </section>
        </section>

        <section className="landing-section" id="landing-what" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">02 · What it does</span>
            <h2>Research for any dataset.</h2>
            <p>Every row gets its own prompt, its own web search and its own answer, so it works for any kind of list — not just companies.</p>
          </div>
          <div className="datasets-grid" aria-label="Datasets n3rf can enrich">
            {useCases.map((u) => (
              <article key={u.tag} className="dataset-card">
                <span className="landing-kicker">{u.tag}</span>
                <h3>{u.title}</h3>
                <p>{u.desc}</p>
                <small>{u.cols}</small>
              </article>
            ))}
          </div>
          <div className="built-note">
            <h3>Built for pipelines, not directory lookups</h3>
            <p>
              Clay queries 150+ data providers for structured records. n3rf does the other half of
              the job: it reads the live web via SEARCH nodes and answers a question you write
              yourself, per row — with rows-in → rows-out at every step. That makes it the right
              tool whenever the answer exists in public and the question is specific to you.
            </p>
            <ul>
              <li>Company overviews, funding, leadership, headcount and recent news</li>
              <li>Custom questions no data-provider schema has a field for</li>
              <li>Any list at all: products, universities, competitors, countries, reviews</li>
              <li>Live answers, researched at the moment you run them</li>
            </ul>
            <p><ArrowRight /> Pair it with HTTP Request when you also need verified emails and phone numbers from a licensed provider.</p>
          </div>
        </section>

        <section className="landing-section landing-artifact" id="landing-artifact" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">03 · Sample · prepared example data</span>
            <h2>prospect_list.csv, enriched.</h2>
            <p>One prompt per row, live web search per row, schema-checked answers. The counts below are the product.</p>
          </div>
          <div className="artifact-grid">
            <div className="artifact-table-panel">
              <div className="artifact-panel-heading"><span>PROSPECT_LIST.CSV, ENRICHED</span><small>ILLUSTRATIVE · 5 OF 500</small></div>
              <div className="artifact-table-scroll">
                <table className="artifact-table">
                  <thead><tr><th>COMPANY</th><th>DOMAIN</th><th>INDUSTRY</th><th>ENRICHED SIGNAL</th></tr></thead>
                  <tbody>
                    {enrichedCompanies.map((c) => (
                      <tr key={c.company}>
                        <th scope="row">{c.company}</th>
                        <td className="artifact-quote">{c.domain}</td>
                        <td>{c.industry}</td>
                        <td className="artifact-quote">{c.signal}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="enriched-note">
                <span>AI-generated columns</span>
                <small>Illustrative example. Real output varies, so always verify.</small>
              </div>
              <div className="theme-chart" aria-label="Rows kept per stage: Import 500, Filter 498, Search 498, Rank 341">
                <p>ROWS KEPT / STAGE</p>
                {retained.map((r) => (
                  <div className="theme-bar-row" key={r.label}>
                    <span>{r.label}</span><div><i className={r.cls} style={{ width: `${(r.value / 500) * 100}%` }} /></div><b>{r.value}</b>
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
              <div className="run-trace-foot">EXTRACT <span>498 CALLS · 489 VALID · <b className="repair-count">9 REPAIRED</b></span></div>
              <div className="run-trace-micro">Prepared example · no live calls · tokens shown per real run</div>
            </div>
          </div>
        </section>

        <section className="landing-section landing-how" id="landing-how" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">04 · How it works</span>
            <h2>Four steps, about two minutes.</h2>
            <p>Drop in a CSV, TSV or Excel file, say what columns you need, check the cost, test three rows, then run the batch. Every node shows its work.</p>
          </div>
          <div className="steps-grid" aria-label="Four steps">
            {steps.map((s, index) => (
              <article className="step-card" key={s.n}>
                <span className="step-num">{s.n}</span>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
                {index < steps.length - 1 && <ArrowRight aria-hidden="true" className="step-arrow" />}
              </article>
            ))}
          </div>
          <p className="pipeline-note"><ArrowDown /> Every node shows rows in, rows out, duration, and a 5-row sample. Errors appear where they happen.</p>
        </section>

        <section className="landing-section" id="landing-pricing" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">05 · Pricing</span>
            <h2>We charge nothing. Here is what the model costs.</h2>
            <p>No markup, no credits, no seats. You are billed by your provider at their published rates, and the run meta shows the number before you commit.</p>
          </div>
          <div className="pricing-grid" aria-label="Cost breakdown">
            <article><span className="landing-kicker">N3RF FEE</span><h3>$0.00</h3><p>Always. Self-hosted on your machine.</p><small>NO MARKUP · NO SEATS</small></article>
            <article><span className="landing-kicker">MODEL</span><h3>Billed direct</h3><p>Any OpenAI-compatible endpoint at published rates. Run shows llm_calls + tokens.</p><small>YOUR KEY · PROVIDER PRICING</small></article>
            <article><span className="landing-kicker">SEARCH / READER</span><h3>Free tiers</h3><p>Tavily 1,000 credits/month · Jina Reader 20 RPM no key · Exa $10/month — replenishing, no card to start.</p><small>SEPARATE NODES · NO WATERFALL</small></article>
            <article><span className="landing-kicker">LOCAL</span><h3>Ollama $0</h3><p>Run llama3.1:8b locally. Unlimited, data never leaves your machine.</p><small>TOKEN COST $0</small></article>
          </div>
          <p className="pipeline-note"><ArrowRight /> Test 5 rows first — the per-node sample, token counts and list prices give you the batch cost before you run 500.</p>
        </section>

        <section className="landing-section" id="landing-why" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">06 · Why n3rf</span>
            <h2>The same AI research, without the subscription.</h2>
            <p>Swap in a rival’s name. This table stops working — if another tool could say the same, it is not a differentiator.</p>
          </div>
          <div className="method-table-wrap">
            <table className="method-table">
              <thead><tr><th>CAPABILITY</th><th>N3RF</th><th>CLAY (CLAYGENT)</th><th>ZAPIER / N8N</th><th>CHAT + SHEET</th></tr></thead>
              <tbody>{compareRows.map(([cap, n3rf, clay, alt1, alt2]) => (
                <tr key={cap}><th scope="row">{cap}</th><td>{n3rf}</td><td>{clay}</td><td>{alt1}</td><td>{alt2}</td></tr>
              ))}</tbody>
            </table>
          </div>
          <p className="table-foot">Clay pricing from their public pricing page and subject to change. Comparison covers AI-research features only, not Clay’s data-provider integrations. The wedge is AI-native data pipelines — not 400 integrations. Thirty-five nodes make the pipeline complete.</p>
        </section>

        <section className="landing-section" id="landing-proof" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">07 · Privacy &amp; trust</span>
            <h2>We cannot see your rows. Runs on your machine.</h2>
            <p>This is an architectural claim, not a policy promise. CSVs are parsed on your machine, keys live in the environment — never in workflow JSON. A simulated run is labelled three ways, never passed off as real.</p>
          </div>
          <section className="landing-models" aria-label="Where data lives">
            <article><span className="landing-kicker">YOUR MACHINE</span><p>FastAPI + local SQLite on your disk. Workflows, runs and samples stay local.</p><small>NO REMOTE DATABASE</small></article>
            <article><span className="landing-kicker">MODEL PROVIDER</span><p>Your key, billed direct. Only the prompts you configure leave your machine.</p><small>YOUR KEY · PROVIDER PRICING</small></article>
            <article><span className="landing-kicker">YOUR EXPORT</span><p>Your rows, your download. No account, no card, no upload off-machine except configured calls.</p><small>NO ACCOUNT · NO CARD</small></article>
          </section>
          <section className="landing-models trust-chips" aria-label="Guarantees">
            <article><span className="landing-kicker">WILL IT FAKE RESULTS?</span><p>No. If the API is unreachable the editor simulates — amber banner, amber LED, “· simulated” in the meta.</p><small>NO SILENT FAKES</small></article>
            <article><span className="landing-kicker">CAN I CHECK IT?</span><p>35 nodes, offline test suite under 10s, schema repair counts visible — 489 valid, 9 repaired in the sample.</p><small>REPRODUCIBLE</small></article>
            <article><span className="landing-kicker">KEYS NEVER IN JSON</span><p>Secrets live in environment variables. Workflow JSON stores only the variable name.</p><small>SECRET-SAFE BY DESIGN</small></article>
          </section>
          <div className="method-table-wrap" style={{ marginTop: "var(--space-4)" }}>
            <table className="method-table">
              <thead><tr><th>DIMENSION</th><th>WHAT IT MEASURES</th><th>ANCHOR EXAMPLE</th></tr></thead>
              <tbody>{methodology.map(([dimension, measure, example]) => (
                <tr key={dimension}><th scope="row">{dimension}</th><td>{measure}</td><td>{example}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>

        <section className="landing-section" id="landing-faq" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">08 · FAQ</span>
            <h2>Frequently asked questions</h2>
            <p>Short answers. Longer ones live in the repo — every claim here is verifiable in the workflow inspector.</p>
          </div>
          <div className="faq-list">
            {faqs.map((f) => (
              <details key={f.q} className="faq-item">
                <summary>{f.q}<ChevronRight aria-hidden="true" /></summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="landing-onepager">
          <div>
            <span className="landing-kicker">09 · Next step</span>
            <h2>Your rows. Your key. Zero platform fee.</h2>
            <p>No account, no card, no catch. Drop a CSV or Excel file, wire the nodes, test three rows, run the batch. The prepared sample needs no key — live calls need only your provider key in the backend environment.</p>
            <small>Prepared sample figures are labelled as such. No email. <button type="button" onClick={downloadSample}>Download the sample output</button> (txt).</small>
          </div>
          <Button className="landing-download-button" onClick={onOpenWorkspace}><Play /> Open the workspace <ArrowUpRight /></Button>
        </section>

        <footer className="landing-footer">
          <div className="landing-platform-reveal">
            <p>Every claim on this page is verifiable in the repo — 35 nodes, FastAPI + SQLite, samples labelled. <button type="button" onClick={() => goTo("landing-artifact")}>See the sample once more →</button></p>
            <Button onClick={onOpenWorkspace}>Open the workspace <ArrowUpRight /></Button>
          </div>
          <div className="landing-footer-meta">
            <span>n3rf · Messy rows in, structured rows out · Your key, your data · © 2026 · Provided as-is without warranty. AI-generated data can be inaccurate, so always verify results.</span>
            <button type="button" onClick={onOpenWorkspace}>OPEN WORKSPACE <ChevronRight /></button>
          </div>
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
