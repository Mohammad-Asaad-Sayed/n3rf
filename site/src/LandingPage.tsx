import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Brain,
  Building2,
  ChevronRight,
  ArrowDownWideNarrow,
  FileSpreadsheet,
  Filter,
  CircleDollarSign,
  Cpu,
  FileCheck2,
  GraduationCap,
  HardDrive,
  KeyRound,
  MessageSquare,
  Rocket,
  Search,
  ShoppingBag,
  Sparkles,
  UserRound,
  Play,
  Upload,
  Workflow,
} from "lucide-react";
import {
  useEffect,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Button } from "./components/ui/button";
import { SELF_HOSTING_URL } from "./links";
import { SiteNav } from "./SiteNav";
import "./styles/landing.css";

const enrichedCompanies = [
  {
    company: "Apple",
    domain: "apple.com",
    industry: "technology",
    aiNote: "Consumer devices, software, and services",
    aiCeo: "Tim Cook",
  },
  {
    company: "Microsoft",
    domain: "microsoft.com",
    industry: "technology",
    aiNote: "Cloud and AI products for businesses",
    aiCeo: "Satya Nadella",
  },
  {
    company: "Shopify",
    domain: "shopify.com",
    industry: "ecommerce",
    aiNote: "Commerce tools for merchants",
    aiCeo: "Tobi Lütke",
  },
  {
    company: "Notion",
    domain: "notion.so",
    industry: "software",
    aiNote: "Docs, wiki, and AI workspace",
    aiCeo: "Ivan Zhao",
  },
  {
    company: "Stripe",
    domain: "stripe.com",
    industry: "fintech",
    aiNote: "Payments infrastructure for businesses",
    aiCeo: "Patrick Collison",
  },
];

const useCases = [
  { tag: "COMPANIES", title: "Companies", desc: "Research leadership, products, hiring, or recent news.", cols: "Leadership · Products · News", icon: Building2 },
  { tag: "PEOPLE", title: "People", desc: "Organize public information around the questions you need answered.", cols: "Role · Work · Public profiles", icon: UserRound },
  { tag: "STARTUPS", title: "Startups", desc: "Summarize what a company does, who backs it, and how it is changing.", cols: "Product · Funding · Signals", icon: Rocket },
  { tag: "UNIVERSITIES", title: "Universities", desc: "Compare institutions against the criteria that matter to your work.", cols: "Programs · Costs · Research", icon: GraduationCap },
  { tag: "PRODUCTS", title: "Products", desc: "Compare features, positioning, pricing, and public reviews.", cols: "Price · Features · Reviews", icon: ShoppingBag },
  { tag: "REVIEWS", title: "Reviews", desc: "Turn unstructured feedback into themes and useful summaries.", cols: "Theme · Sentiment · Summary", icon: MessageSquare },
  { tag: "ANYTHING ELSE", title: "Anything else", desc: "Describe the data and questions that matter to your workflow.", cols: "Your list · Your questions · Your output", icon: Sparkles },
];

const steps = [
  { n: "01", title: "Bring your spreadsheet", desc: "Open a CSV, TSV, or Excel file in your workspace. Your column headers become the starting point for the workflow." },
  { n: "02", title: "Describe the result you need", desc: "Add steps to shape, filter, search, or ask AI about your rows. Use your own columns in plain-language prompts." },
  { n: "03", title: "Choose a model and preview", desc: "Connect a provider with your own key. Test a small sample and review token use before processing the full dataset." },
  { n: "04", title: "Run the batch and inspect", desc: "Follow each step's row counts, status, and sample output. See where data changed or a step needs attention." },
];

const compareRows = [
  ["Best fit", "AI workflows over data batches", "Data enrichment and AI research", "Connecting events and services", "Quick questions and exploration", "One-off or custom data workflows"],
  ["Work starts with", "Rows in a workflow", "Tables and enrichment steps", "A trigger, task, or connected app", "A prompt and pasted data", "A script and its inputs"],
  ["AI and web research", "Your prompts and provider steps", "Claygent and data-provider features", "AI steps depend on integrations", "Manual prompts and browsing", "Whatever you build"],
  ["See what changed", "Row counts and samples at each node", "Enrichment results in the platform", "Run history and task details", "Match answers back by hand", "Logs and inspection you build"],
  ["Provider and model choice", "Configure a supported model/provider", "Options depend on current Clay features", "Depends on the connected apps", "Choose a chat model", "Choose and configure your stack"],
  ["Pricing model", "$0 n3rf fee; provider charges may apply", "Plans and credits; check current pricing", "Plans and task limits vary", "Plan or API charges may apply", "Development and provider costs"],
  ["Where it runs", "Locally, with configured provider calls", "Clay's hosted platform", "Hosted or self-hosted, depending on product", "Depends on the chat provider", "Where you deploy it"],
  ["Setup", "One command or agent-driven", "Account and onboarding", "Account and onboarding", "Account required", "You build and deploy"],
];

const pipeline = [
  ["IMPORT", "500", "500"],
  ["FILTER", "500", "498"],
  ["SEARCH", "498", "498"],
  ["EXTRACT", "498", "498"],
  ["RANK", "498", "341"],
];

const exampleSteps = [
  {
    node: "Manual JSON",
    kind: "INPUT · CSV",
    icon: FileSpreadsheet,
    rows: "1 of 500",
    mono: `company: "Stripe"\ndomain: "stripe.com"\nindustry: "fintech"`,
    note: "The sample sheet the workspace ships with — one row, thousands of the same shape.",
  },
  {
    node: "Filter",
    kind: "TRANSFORM",
    icon: Filter,
    rows: "498 in · 498 out",
    mono: `keep if: {{ $json.domain }} != ""`,
    note: "Rows without a domain are dropped here — two rows fail and are counted in the run trace.",
  },
  {
    node: "Search",
    kind: "RESEARCH · TAVILY",
    icon: Search,
    rows: "498 in · 498 out",
    mono: `query: "{{ $json.company }} CEO\n  latest funding round"`,
    note: "A live web search per row, using your own search provider key.",
  },
  {
    node: "Ask AI",
    kind: "AI STEP · JSON OUT",
    icon: Brain,
    rows: "498 in · 498 out",
    mono: `for {{ $json.company }}, reply with\n{"summary": "…", "ceo": "…",\n "recent": "…"}`,
    note: "Each row gets its own plain-language prompt and its own answer — not a directory lookup.",
  },
  {
    node: "Sort",
    kind: "RANK · KEEP 341",
    icon: ArrowDownWideNarrow,
    rows: "498 in · 341 kept",
    mono: `sort by: {{ $json.recent }} desc\nkeep top 341`,
    note: "Ranked by how fresh the signal is; the rest stay in the run history, unranked.",
  },
];

const faqs = [
  {
    q: "What is n3rf?",
    a: "n3rf is a local-first workflow builder for working with batches of data. Bring a spreadsheet, connect steps for transforming or researching its rows, and inspect what each step produced. Use your own model provider and API key.",
  },
  {
    q: "Is n3rf free?",
    a: "There is no n3rf platform fee. You run it on your machine and pay any model or search provider you choose, according to that provider's current pricing. Local models may avoid per-token API charges, but still use your own hardware.",
  },
  {
    q: "How is n3rf different from a chat and spreadsheet?",
    a: "Instead of moving batches between a chat window and a spreadsheet by hand, n3rf runs a workflow over rows. You can see how many rows enter and leave each step, inspect samples, and rerun after changing the workflow.",
  },
  {
    q: "Is my data safe with n3rf?",
    a: "n3rf is designed to run locally: workflows and run history are stored on your machine, and provider keys are configured in your environment rather than saved in workflow JSON. Data sent to a model or search service is subject to that provider's terms and privacy practices.",
  },
  {
    q: "What models does n3rf support?",
    a: "Use a supported provider such as OpenAI, Groq, Gemini, OpenRouter, Mistral, Hugging Face, Ollama, or Cloudflare. You can also configure a compatible custom endpoint. Provider availability and model requirements vary.",
  },
  {
    q: "Can I test before running the full dataset?",
    a: "Yes. Test a small set of rows first, inspect the output, and review token usage before running the full batch. AI and search steps also let you control concurrency and how errors are handled.",
  },
  {
    q: "What file formats does n3rf support?",
    a: "The workspace accepts CSV, TSV, and Excel (.xlsx) files up to 10 MB. You can also start with pasted spreadsheet data, JSON, text lines, or a built-in example dataset.",
  },
  {
    q: "How much will a run cost?",
    a: "n3rf does not add a platform fee or markup. Model and search charges depend on your providers, models, and prompts. Test a small sample to see token usage, then check your provider's current rates for an estimate.",
  },
  {
    q: "Do I need to create an account?",
    a: "No n3rf account or card is required. To make live model or search requests, configure the credentials required by the providers you choose.",
  },
  {
    q: "What kind of data can I enrich?",
    a: "Any tabular data that fits your workflow. For example, research companies, compare products, categorize reviews, or summarize public information. Results depend on your prompts, source data, and providers, so verify important outputs.",
  },
  {
    q: "Can an AI agent set this up for me?",
    a: "Yes. Paste the repo URL into OpenCode, Claude Code, or Codex and it clones, installs, builds, and runs n3rf for you. See SETUP.md for the exact steps.",
  },
  {
    q: "Is n3rf open source?",
    a: "Yes. n3rf is licensed under AGPL-3.0. It is free to self-host, and a separate commercial license is available for embedding it in proprietary products.",
  },
  {
    q: "Can an agent and I edit the same workflow?",
    a: "Yes. Workflows use versioned saves, so neither you nor the agent silently overwrites the other. The agent asks before saving, and conflicting edits are rejected with a clear message.",
  },
];

export function LandingPage() {
  useEffect(() => {
    const onScroll = () => {
      const hero = document.querySelector<HTMLElement>(".landing-hero-frame");
      if (hero) hero.style.setProperty("--hero-shift", String(Math.min(window.scrollY, 600)));
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id) {
      const el = document.getElementById(id);
      el?.scrollIntoView({ block: "start" });
    }
  }, []);

  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !("IntersectionObserver" in window)
    ) {
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
    // Safety net: never leave content invisible if the observer stalls.
    const fallback = window.setTimeout(() => {
      elements.forEach((element) => element.setAttribute("data-revealed", "true"));
    }, 1500);
    return () => {
      observer.disconnect();
      window.clearTimeout(fallback);
    };
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

  function downloadSample() {
    const content = [
      "n3rf · Illustrative workflow example",
      "",
      "Prepared example data; these figures are illustrative, not customer results.",
      "500 rows in → 498 after filters → 341 kept",
      "",
      ...enrichedCompanies.map(
        (c) => `${c.company},${c.domain},${c.industry},${c.aiCeo},${c.aiNote}`,
      ),
      "",
      "No live model or search calls are made for this prepared example.",
      "AI-generated information can be inaccurate. Verify results before relying on them.",
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
      <SiteNav active="landing" onNavigate={goTo} />

      <section className="landing-hero" id="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-hero-frame">
            <span className="hero-bracket hero-bracket-tl" />
            <span className="hero-bracket hero-bracket-tr" />
            <span className="hero-bracket hero-bracket-bl" />
            <span className="hero-bracket hero-bracket-br" />
            <div className="landing-hero-main">
              <div className="landing-hero-copy">
                <p className="landing-qualifier">AI DATA WORKFLOWS · YOUR MODEL · NO PLATFORM FEE</p>
                <h1>AI workflows for messy rows—<em className="landing-accent-word">with every step in&nbsp;view.</em></h1>
                <p className="landing-subhead">
                  Turn a spreadsheet into a clean, useful dataset without shuttling
                  rows between a chat window and a script. Build a workflow around
                  your data, use your own AI provider, and see what each step did.
                  Self-hosted, AGPL-licensed, and agent-ready: paste the repo URL
                  into OpenCode, Claude Code, or Codex and it sets itself up.
                </p>
                <div className="landing-hero-actions">
                  <a
                    className="ui-button ui-button-md ui-button-primary"
                    href={SELF_HOSTING_URL}
                    onPointerMove={tiltElement}
                    onPointerLeave={resetTilt}
                  >
                    <Upload /> Get started
                  </a>
                  <Button variant="ghost" onClick={() => { window.location.href = "/templates"; }}>Browse templates <ArrowUpRight aria-hidden="true" /></Button>
                  <Button variant="ghost" onClick={() => goTo("landing-how")}>How it works <ArrowDown /></Button>
                  <p className="landing-sample-note">No account needed · CSV, TSV, or .xlsx up to 10 MB. <button type="button" onClick={() => goTo("landing-artifact")}>Preview an example ↓</button></p>
                </div>
                <a
                  className="landing-upload"
                  href={SELF_HOSTING_URL}
                  aria-label="Open the n3rf workspace"
                >
                  <Upload />
                  <span>Self-host n3rf and start with your data</span>
                  <ChevronRight />
                </a>
              </div>
              <HeroWorkflowPreview />
            </div>
            <div className="landing-proof" aria-label="Illustrative prepared example: 500 rows in, 498 after filters, 341 kept">
              <span className="landing-proof-dot" />
              <span><b>500</b> ROWS IN</span><ArrowRight />
              <span><b>498</b> AFTER FILTERS</span><ArrowRight />
              <span><b>341</b> KEPT</span>
              <i>· ILLUSTRATIVE EXAMPLE · NO PLATFORM FEE</i>
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
                ].map((name, index) => (
                  <span key={`${name}-${index}`}>{name} <b>→</b></span>
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
                ].map((name, index) => (
                  <span key={`dup-${name}-${index}`}>{name} <b>→</b></span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="landing-content">
        <section className="landing-section" id="landing-pain" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">01 · The problem</span>
            <h2>When rows disappear into the process, results are hard to trust.</h2>
            <p>Copying, pasting, and rerunning by hand makes it difficult to see what changed—or which step needs fixing.</p>
          </div>
          <section className="landing-models" aria-label="The problem">
            <article><span className="landing-kicker">SPREADSHEET + CHAT</span><p>Move chunks back and forth, then try to match the answers to the original rows.</p><small>MANUAL COPY AND PASTE</small></article>
            <article><span className="landing-kicker">GENERAL AUTOMATION</span><p>Connect triggers and services, then piece together a flow for a one-off batch job.</p><small>ROWS ARE AN AFTERTHOUGHT</small></article>
            <article><span className="landing-kicker">A CUSTOM SCRIPT</span><p>Get the result you need, but rely on code and logs to understand what happened.</p><small>HARD TO HAND OFF</small></article>
          </section>
        </section>

        <section className="landing-section" id="landing-what" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">02 · What you can do</span>
            <h2>Start with your rows. Ask the questions that matter to you.</h2>
            <p>Build a repeatable workflow to clean, organize, and research all kinds of tabular data—not just company lists.</p>
          </div>
          <div className="datasets-grid" aria-label="Datasets n3rf can enrich">
            {useCases.map((u) => (
              <article key={u.tag} className="dataset-card">
                <div className="dataset-card-top">
                  <u.icon aria-hidden="true" />
                  <span className="landing-kicker">{u.tag}</span>
                </div>
                <h3>{u.title}</h3>
                <p>{u.desc}</p>
                <small>{u.cols}</small>
              </article>
            ))}
          </div>
          <div className="built-note">
            <h3>For questions a fixed database field cannot answer</h3>
            <p>
              A directory can only return the fields it has. With n3rf, define the
              question, choose the steps and sources, and run that workflow across
              your rows. Results stay inspectable from the first transformation to
              the final output.
            </p>
            <ul>
              <li>Shape, filter, sort, and combine rows before or after AI steps</li>
              <li>Ask custom questions in plain language and define the output you need</li>
              <li>Use web search and page-reading steps when your workflow needs them</li>
              <li>Inspect row counts, errors, and sample outputs as the workflow runs</li>
            </ul>
            <p><ArrowRight /> Bring a data provider or service into the workflow with the generic HTTP Request step.</p>
          </div>
        </section>

        <section className="landing-section landing-artifact" id="landing-artifact" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">03 · Example workflow · prepared data</span>
            <h2>Follow one row from sheet to answer.</h2>
            <p>The workspace ships with this prepared example. Each step shows the node it used, the exact setting you’d write, and what it did to the rows — the same detail you get in the results panel.</p>
          </div>
          <ol className="flow-steps" aria-label="How the example row moves through the workflow">
            {exampleSteps.map((step, index) => (
              <li className="flow-step" key={step.node}>
                <div className="flow-step-head">
                  <span className="flow-step-index">{String(index + 1).padStart(2, "0")}</span>
                  <step.icon aria-hidden="true" />
                  <span className="flow-step-name">{step.node}</span>
                </div>
                <span className="flow-step-kind">{step.kind}</span>
                <pre className="flow-step-mono">{step.mono}</pre>
                <span className="flow-step-rows">{step.rows}</span>
                <p>{step.note}</p>
              </li>
            ))}
          </ol>
          <p className="flow-foot"><i /> PREPARED EXAMPLE · NO LIVE CALLS · YOUR WORKFLOW, YOUR PROMPTS, YOUR PROVIDER</p>
          <div className="artifact-example">
            <div className="artifact-table-panel">
              <div className="artifact-panel-heading"><span>ENRICHED COMPANY LIST</span><small>PREPARED EXAMPLE · 5 OF 341 ROWS KEPT</small></div>
              <div className="artifact-table-scroll">
                <table className="artifact-table">
                  <thead><tr><th>COMPANY</th><th>DOMAIN</th><th>INDUSTRY</th><th className="ai-col">CEO</th><th className="ai-col">SIGNAL</th></tr></thead>
                  <tbody>
                    {enrichedCompanies.map((c) => (
                      <tr key={c.company}>
                        <th scope="row">{c.company}</th>
                        <td>{c.domain}</td>
                        <td>{c.industry}</td>
                        <td className="ai-col">{c.aiCeo}</td>
                        <td className="ai-col artifact-quote">{c.aiNote}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="enriched-note">
                <span className="ai-legend"><i />AI-GENERATED COLUMNS</span>
                <small>Prepared data, not customer results. AI output can be inaccurate — verify before relying on it.</small>
              </div>
            </div>
            <div className="run-trace-panel">
              <div className="artifact-panel-heading"><span>WHAT HAPPENED TO THE ROWS?</span><small>ILLUSTRATIVE RUN TRACE</small></div>
              <div className="run-trace-steps">
                {pipeline.map(([name, before, after], index) => (
                  <div className={`run-trace-step trace-${name.toLowerCase()}`} key={name}>
                    <span className="run-trace-step-name"><i>{String(index + 1).padStart(2, "0")}</i>{name}</span>
                    <strong>{before}<ArrowRight />{after}</strong>
                    <small>rows in <span>rows out</span></small>
                  </div>
                ))}
              </div>
              <p className="run-trace-micro">Prepared example · no live calls · results vary with your data, workflow, and providers.</p>
            </div>
          </div>
        </section>

        <section className="landing-section landing-how" id="landing-how" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">04 · How it works</span>
            <h2>From spreadsheet to repeatable workflow.</h2>
            <p>Bring your data, define the steps, test a sample, then run the batch. Results show what happened at every step.</p>
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
          <p className="pipeline-note"><ArrowDown /> Inspect row counts, status, duration, sample outputs, and errors in the results panel.</p>
        </section>

        <section className="landing-section" id="landing-pricing" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">05 · Costing</span>
            <h2>No n3rf fee. Your provider, your call.</h2>
            <p>n3rf adds no subscription or usage markup. Model and search services may charge separately; check their current rates and test a sample before a full run.</p>
          </div>
          <div className="pricing-grid" aria-label="Cost breakdown">
            <article><span className="cost-card-label"><CircleDollarSign aria-hidden="true" /><span className="landing-kicker">N3RF</span></span><h3>$0 platform fee</h3><p>Run the workspace on your own machine. No n3rf subscription or usage markup.</p><small>SELF-HOSTED · NO SEATS</small></article>
            <article><span className="cost-card-label"><Brain aria-hidden="true" /><span className="landing-kicker">AI MODEL</span></span><h3>Your provider</h3><p>Connect a model with your own API key. Provider charges depend on your model and usage.</p><small>BRING YOUR OWN KEY</small></article>
            <article><span className="cost-card-label"><Search aria-hidden="true" /><span className="landing-kicker">SEARCH SERVICES</span></span><h3>Your choice</h3><p>Use supported search and page-reading providers. Their pricing, limits, and key requirements vary.</p><small>CHECK PROVIDER TERMS</small></article>
            <article><span className="cost-card-label"><Cpu aria-hidden="true" /><span className="landing-kicker">LOCAL MODEL</span></span><h3>Run locally</h3><p>Connect a local model such as Ollama. You supply and maintain the hardware.</p><small>NO MODEL API BILL</small></article>
            <article><span className="cost-card-label"><Sparkles aria-hidden="true" /><span className="landing-kicker">AGENT-READY</span></span><h3>One-command setup</h3><p>Paste the repo URL into OpenCode, Claude Code, or Codex and it installs and runs n3rf for you.</p><small>AGPL-3.0 · OPEN SOURCE</small></article>
          </div>
          <p className="pipeline-note"><ArrowRight /> A small test can help you understand token use; it cannot guarantee the cost or output of a full run.</p>
        </section>

        <section className="landing-section" id="landing-why" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">06 · Why n3rf</span>
            <h2>AI research, built around your rows.</h2>
            <p>Choose n3rf for a local, inspectable AI workflow over a dataset; choose the alternative that best fits your data sources, integrations, and way of working.</p>
          </div>
          <div className="method-table-wrap">
            <table className="method-table">
              <thead><tr><th>CAPABILITY</th><th>N3RF</th><th>CLAY / CLAYGENT</th><th>ZAPIER / N8N</th><th>CHAT + SHEET</th><th>CUSTOM SCRIPT</th></tr></thead>
              <tbody>{compareRows.map(([capability, n3rf, clay, automation, chat, script]) => (
                <tr key={capability}><th scope="row">{capability}</th><td>{n3rf}</td><td>{clay}</td><td>{automation}</td><td>{chat}</td><td>{script}</td></tr>
              ))}</tbody>
            </table>
          </div>
          <p className="table-foot">High-level comparison of typical product focus, not a feature-by-feature benchmark. Plans, pricing, integrations, and capabilities change; check each provider's current details. n3rf's distinction is a local-first, row-based workflow with visible results at each step.</p>
          <a className="claygent-page-link" href="/alternatives/claygent">
            See n3rf as a Claygent alternative <ArrowUpRight aria-hidden="true" />
          </a>
        </section>

        <section className="landing-section" id="landing-proof" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">07 · Privacy and data</span>
            <h2>Know where your data goes.</h2>
            <p>Your workflow runs locally. Only steps that use an external provider send requests to that provider.</p>
          </div>
          <div className="privacy-flow" aria-label="How data moves through n3rf">
            <article>
              <span className="privacy-step-label"><HardDrive aria-hidden="true" /><span className="landing-kicker">01 · YOUR MACHINE</span></span>
              <h3>Workflow and run history</h3>
              <p>Stored in your local workspace.</p>
            </article>
            <article>
              <span className="privacy-step-label"><KeyRound aria-hidden="true" /><span className="landing-kicker">02 · YOUR PROVIDER</span></span>
              <h3>Only when a step needs it</h3>
              <p>Configured AI and search requests go to the provider you choose.</p>
            </article>
            <article>
              <span className="privacy-step-label"><FileCheck2 aria-hidden="true" /><span className="landing-kicker">03 · YOUR RESULTS</span></span>
              <h3>Back in your workspace</h3>
              <p>Inspect the output and export the rows you need.</p>
            </article>
          </div>
          <div className="privacy-note">
            <strong>Provider calls leave your machine.</strong>
            <span>Review each provider’s data practices. Credentials are configured in your environment, not saved in workflow JSON.</span>
          </div>
        </section>

        <section className="landing-section" id="landing-faq" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">08 · FAQ</span>
            <h2>Frequently asked questions</h2>
            <p>What it does, what it costs, and where your data goes.</p>
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
            <h2>Put your next dataset to work.</h2>
            <p>Open the workspace, start with a spreadsheet or sample data, and build a workflow you can inspect. No n3rf account or platform fee. Live provider calls use your own credentials.</p>
            <small>Want to see the example first? <button type="button" onClick={downloadSample}>Download the illustrative output</button> (txt).</small>
          </div>
          <a className="ui-button ui-button-md ui-button-primary landing-download-button" href={SELF_HOSTING_URL}><Play /> Self-host n3rf <ArrowUpRight /></a>
        </section>

        <footer className="landing-footer">
          <div className="landing-footer-main">
            <a className="landing-footer-brand" href="/" aria-label="n3rf home">n3rf</a>
            <span>Self-hosted AI data workflows for structured rows.</span>
            <nav aria-label="Footer">
              <a href="/templates">Templates</a>
              <a href="/legal">About · Privacy · Terms · Data</a>
              <a href={SELF_HOSTING_URL}>Self-hosting guide <ArrowUpRight aria-hidden="true" /></a>
            </nav>
          </div>
          <p className="landing-footer-note">© 2026 n3rf · AI-generated information may be inaccurate. Verify important results.</p>
        </footer>
      </div>
    </main>
  );
}

function HeroWorkflowPreview() {
  return (
    <figure className="hero-workflow-preview" aria-label="Illustrative company research workflow canvas">
      <div className="hero-workflow-window">
        <div className="hero-workflow-toolbar">
          <div className="hero-workflow-title">
            <Workflow />
            <span>COMPANY RESEARCH</span>
          </div>
          <span className="hero-workflow-state"><i /> PREVIEW</span>
        </div>
        <div className="hero-workflow-canvas">
          <svg className="hero-workflow-connectors" viewBox="0 0 420 200" preserveAspectRatio="none" aria-hidden="true">
            <path d="M168 45H252M328 76V124M252 155H168" />
          </svg>
          <article className="hero-workflow-node hero-workflow-input">
            <span className="hero-workflow-node-icon"><FileCheck2 /></span>
            <span className="hero-workflow-node-kind">INPUT · CSV</span>
            <strong>Company list</strong>
            <small>500 rows</small>
          </article>
          <article className="hero-workflow-node hero-workflow-search">
            <span className="hero-workflow-node-icon"><Search /></span>
            <span className="hero-workflow-node-kind">RESEARCH</span>
            <strong>Find signals</strong>
            <small>Web search</small>
          </article>
          <article className="hero-workflow-node hero-workflow-ai">
            <span className="hero-workflow-node-icon"><Brain /></span>
            <span className="hero-workflow-node-kind">AI STEP</span>
            <strong>Summarize fit</strong>
            <small>Per row</small>
          </article>
          <article className="hero-workflow-node hero-workflow-output">
            <span className="hero-workflow-node-icon"><FileCheck2 /></span>
            <span className="hero-workflow-node-kind">RESULTS</span>
            <strong>Clean output</strong>
            <small>341 rows kept</small>
          </article>
        </div>
        <figcaption className="hero-workflow-caption">
          <span><i /> ROWS THROUGH EVERY STEP</span>
          <span>ILLUSTRATIVE SAMPLE</span>
        </figcaption>
      </div>
    </figure>
  );
}
