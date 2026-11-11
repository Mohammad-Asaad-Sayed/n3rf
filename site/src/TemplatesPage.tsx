import {
  ArrowUpRight,
  Building2,
  GraduationCap,
  Rocket,
  ShoppingBag,
  Sparkles,
  Upload,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import "./styles/landing.css";
import { SiteNav } from "./SiteNav";
import { SELF_HOSTING_URL } from "./links";

type Playbook = {
  id: string;
  tag: string;
  icon: LucideIcon;
  title: string;
  intro: string;
  columns: string[];
  prompt: string;
  chain: string[];
  chainNotes: [string, string][];
  cost: string;
  costNote: string;
  goodToKnow: string[];
};

const playbooks: Playbook[] = [
  {
    id: "company-research",
    tag: "COMPANIES",
    icon: Building2,
    title: "Enrich a company list with AI",
    intro:
      "Turn a column of company names into the fields you actually need: leadership, funding, headcount, positioning — researched live on the web, one row at a time, with every step inspectable on the grid.",
    columns: ["company", "website", "ceo", "funding_total", "headcount", "positioning"],
    prompt: `Research the company "{{company}}" using the web search results provided.
Return ONLY a JSON object with these keys:
  - ceo: string — current CEO's full name (or "unknown")
  - funding_total: string — total funding raised, e.g. "$120M Series B" (or "unknown")
  - headcount: string — approximate headcount with source confidence, e.g. "approx. 250, likely smaller"
  - positioning: string — one sentence on what the company sells and to whom
Return "unknown" for anything the sources do not support. No commentary, no markdown fences.`,
    chain: ["CSV File", "Tavily Search", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Input: company,website — headers become columns"],
      ["Tavily Search", "Query: {{company}} funding leadership · basic depth"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 400"],
      ["Export CSV", "Or copy rows / filter by verified fields first"],
    ],
    cost: "≈ 1 Tavily credit per row + model tokens (~500 in / ~150 out per row)",
    costNote: "With Gemini 3 Flash that is well under $1 per 1,000 rows. With Claude Sonnet 5 ≈ $12 per 1,000. Check your provider's current rates — these figures drift.",
    goodToKnow: [
      "Tavily basic search returns the page content you need for most rows; switch to advanced only if accuracy matters more than bill size.",
      "Funding numbers go stale fast — the prompt asks for source-honest 'unknown' rather than confident wrong answers. That is on purpose.",
      "A 500-company run ≈ 500 Tavily searches. Tavily's free tier covers roughly that; SerpApi's covers 250/month. Budget accordingly.",
      "Use Filter before Ask AI to skip rows with missing websites (saves search + model calls).",
    ],
  },
  {
    id: "lead-enrichment",
    tag: "LEADS",
    icon: UserRound,
    title: "Enrich a lead list without a subscription",
    intro:
      "Export the raw prospects from Apollo, lemlist or LinkedIn Sales Navigator. n3rf reads a column, runs one live search per row, and fills in current title, seniority band and a one-line company summary — no per-lead credit SaaS required.",
    columns: ["first_name", "last_name", "current_title", "seniority", "company", "company_summary"],
    prompt: `Research the person "{{first_name}} {{last_name}}" at "{{company}}" using the web results provided.
Return ONLY a JSON object:
  - current_title: string — their current role (or "unknown")
  - seniority: string — one of: junior, mid, senior, director, executive, or "unknown"
  - company_summary: string — one sentence on what the company sells and to whom
Return "unknown" for anything you cannot verify.`,
    chain: ["CSV File", "Tavily Search", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Input headers: first_name, last_name, company — headers become columns"],
      ["Tavily Search", "Query: {{first_name}} {{last_name}} {{company}} · basic depth"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 400"],
      ["Export CSV", "Straight into your sequencer, or filter first with Filter node"],
    ],
    cost: "≈ 1 Tavily credit per row + model tokens (~450 in / ~120 out per row)",
    costNote: "Enriching 200 leads ≈ 200 searches + model calls. A few dollars at most on cheap models.",
    goodToKnow: [
      "Put a Filter node before Ask AI: drop rows where company or last_name is empty — empty queries burn search and model credits for zero result.",
      "Ask the model to return 'unknown' for unverifiable fields. A confident-but-wrong title is worse than an honest gap.",
      "LinkedIn blocks scraping — expect Tavily to return public profiles partially. The prompt tolerates that by design.",
      "Re-import the output into your sequencer; the merge pattern (CSV → Tavily → Ask AI → Export CSV) round-trips cleanly.",
    ],
  },
  {
    id: "competitor-matrix",
    tag: "COMPETITORS",
    icon: ShoppingBag,
    title: "Build a competitor matrix from a list of names",
    intro:
      "Give it a column of competitor names and get structured differentiators back: pricing model, entry price, the segment each serves, and their own headline positioning. Useful for win/loss analysis, displacement campaigns, or sizing up a new market.",
    columns: ["competitor", "website", "starting_price", "pricing_model", "target_segment", "differentiator"],
    prompt: `Research the company "{{competitor}}" using the web results and page extracts provided.
Return ONLY a JSON object:
  - starting_price: string — their cheapest paid plan, in their displayed currency, e.g. "$29/mo" (or "unknown" / "free")
  - pricing_model: string — one of: free, freemium, subscription, usage-based, enterprise-quote, unknown
  - target_segment: string — one sentence on who their customers are
  - differentiator: string — one sentence on what they claim to do better than alternatives
Return "unknown" for anything you cannot verify with the supplied sources.`,
    chain: ["CSV File", "Tavily Search", "Jina Reader", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Input headers: competitor, website — headers become columns"],
      ["Tavily Search", "Query: {{competitor}} pricing · max_results 3"],
      ["Jina Reader", "Optional: fetch their pricing page for verbatim prices, no key required"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 500"],
      ["Export CSV", "Review and sort by differentiator; paste into your analysis doc"],
    ],
    cost: "≈ 1 Tavily credit + 1 page fetch + model tokens (~800 in / ~200 out per row)",
    costNote: "The Jina Reader leg is free (no key, no credit). The heavy cost is Tavily search + model output, ~$1–2 per 100 competitors on cheap models.",
    goodToKnow: [
      "Pricing pages rot fast. The prompt asks for 'unknown' rather than a stale guess — run this quarterly.",
      "Use Jina Reader selectively (only for rows where the search output lacked a concrete number) — it avoids fetching 50 pages at Google-cached content's terms.",
      "If your competitors are mostly SaaS, filter out the ones that never publish pricing (enterprise-quote only).",
      "Sort by 'pricing_model' in the grid to group them: freemium vs usage-based vs enterprise makes the positioning obvious.",
    ],
  },
  {
    id: "university-data",
    tag: "UNIVERSITIES",
    icon: GraduationCap,
    title: "Compare universities or schools",
    intro:
      "Rankings, acceptance rates, tuition and programme fit — evaluated across hundreds of institutions in a single pass. Use this for recruiting, college counselling, or relocation analysis. Public widely-available data makes this a well-behaved search workload.",
    columns: ["university", "website", "world_ranking", "acceptance_rate", "tuition_usd", "strongest_programme"],
    prompt: `Research the university "{{university}}" using the web search results provided.
Return ONLY a JSON object:
  - world_ranking: string — its current Times or QS ranking, e.g. "≈ #42 QS" (or "unknown")
  - acceptance_rate: string — admission acceptance rate, e.g. "28%" (or "unknown")
  - tuition_usd: string — annual undergraduate tuition in USD, e.g. "$42,000" or "public in-state $18,500" (or "unknown")
  - strongest_programme: string — the field this university is most known for, one phrase
Return "unknown" for anything you cannot verify.`,
    chain: ["CSV File", "Exa Search", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Input headers: university, website — headers become columns"],
      ["Exa Search", "Query: {{university}} admission tuition · type auto"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 400"],
      ["Export CSV", "The university table you would build by hand across 5 tabs"],
    ],
    cost: "≈ 1 Exa search per row + model tokens (~400 in / ~150 out per row)",
    costNote: "Exa's auto search includes page selection; free tier is 1,000 searches/month at the time of writing for the standard self-serve plan. 500 universities ≈ half that.",
    goodToKnow: [
      "Use Exa's 'auto' type — it relevance-ranks results better than a fixed depth for factual lookup queries.",
      "Private universities quote tuition very differently from public ones — the prompt asks for the in-state figure explicitly.",
      "QS and THE publish their rankings in plain text — include 'QS' or 'Times' in your query if you want consistently sourced numbers.",
      "For a repeatable pipeline, re-run quarterly — rankings and tuition change each academic cycle.",
    ],
  },
  {
    id: "hiring-signals",
    tag: "HIRING",
    icon: Rocket,
    title: "Track hiring signals across companies",
    intro:
      "Open roles, the functions being hired, and the careers page URL — practical signals of where a company is allocating resources. Useful for outbound, recruiting outreach timing, or simply briefing before a call.",
    columns: ["company", "careers_url", "open_roles", "top_hiring_function", "signal_summary"],
    prompt: `Research the company "{{company}}" and its public careers page.
Return ONLY a JSON object:
  - careers_url: string — the canonical URL of the public careers/jobs page (or "unknown")
  - open_roles: string — approximate number of open roles right now, e.g. "approx. 22" (or "unknown")
  - top_hiring_function: string — the function with the most open roles, e.g. "engineering", "sales", "product"
  - signal_summary: string — one sentence on what their hiring pattern implies, e.g. "scaling engineering; GTM team static; treating machine learning as core"
Return "unknown" for anything you cannot verify.`,
    chain: ["CSV File", "Tavily Search", "Jina Reader", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Input headers: company, website — headers become columns"],
      ["Tavily Search", "Query: {{company}} careers jobs open roles · basic depth"],
      ["Jina Reader", "Fetch the careers page verbatim for signed role counts"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 500"],
      ["Export CSV", "Rank by top_hiring_function; review before any outreach"],
    ],
    cost: "≈ 1 Tavily credit + 1 page fetch + model tokens (~700 in / ~180 out per row)",
    costNote: "TheJina leg is free. The expensive part is usually your model's output; budget around $5–10 per 100 companies on cheap models.",
    goodToKnow: [
      "Jina Reader is free and needs no key — it fetches careers pages verbatim. Use it when the search results look vague or stale.",
      "Large companies (300+ roles) will blow the context. If you care about scale companies, swap Ask AI to filter only your target functions with a Filter node before it.",
      "Roles come and go; treat signal_summary as directional, not as a quantitative headcount.",
      "Careers pages are public — using them for personal outreach is generally fine, but respect each company's terms of service and do not scrape authenticated ATS portals.",
    ],
  },
  {
    id: "any-csv-any-question",
    tag: "ANYTHING",
    icon: Sparkles,
    title: "Any CSV, any question the web can answer",
    intro:
      "The generic template. If the answer exists on the public web and you can ask it in a sentence, this workflow produces it — repeatably, with every step on the grid. Use it for awards, patents, events, code, benchmarks, pricing, qualifiers.",
    columns: ["row_label", "answer", "source_url", "confidence"],
    prompt: `You are enriching rows from a CSV using web search.
The row contains this column: "{{row_label}}" (and any other fields you want to see).
Task: answer this question about the row: {{question}}
Return ONLY a JSON object:
  - answer: string — your best answer to the question
  - source_url: string — the URL you relied on
  - confidence: string — one of: low, medium, high
Return "unknown" and "low" confidence when sources are thin.`,
    chain: ["CSV File", "Tavily Search", "Jina Reader", "Ask AI", "Export CSV"],
    chainNotes: [
      ["CSV File", "Any CSV; store the question as a column named 'question', or hard-code it in the prompt"],
      ["Tavily Search", "Query: {{row_label}} {{question}} · max_results 3"],
      ["Jina Reader", "Optional: fetch one page per row verbatim"],
      ["Ask AI", "Provider: your choice · prompt above · max_tokens 500"],
      ["Export CSV", "Every row carries answer, source and confidence"],
    ],
    cost: "Per-row search + model cost, same order of magnitude as company-research (~1 search/row)",
    costNote: "The cost story here is your imagination, not your provider. Start with 5 rows using TEST 5 ROWS before committing the full batch.",
    goodToKnow: [
      "Hard-code the question in the prompt for a consistent output across all rows, or keep it parameterized per row for mixed-question datasets.",
      "Return 'source_url' always — it is the difference between research and confident unverified claims.",
      "Confidence: expose low/medium/high rather than a number — models calibrate words better than decimals.",
      "Anything that smells like structured verifier data (funding, prices, rankings) pays off here. Anything that needs authenticated access does not.",
    ],
  },
];

export function TemplatesPage() {
  return (
    <main className="landing-shell templates-shell">
      <SiteNav active="templates" />

      <header className="templates-hero">
        <div className="templates-hero-frame">
          <span className="templates-bracket templates-bracket-tl" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-tr" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-bl" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-br" aria-hidden="true" />
          <p className="landing-kicker templates-kicker">TEMPLATES · 06 · RUN-READY</p>
          <h1>Six playbooks. <em>Batched rows out.</em></h1>
          <p className="templates-hero-sub">
            Not demos. Full node chains with working prompts, the columns you get back,
            the honest cost per 1,000 rows, and every sharp edge that will bite you.
          </p>
          <div className="templates-proof" aria-label="What every template includes">
            <span><i />PROMPT</span><span><i />CHAIN</span><span><i />COLS</span><span><i />COST</span><span><i />GOTCHAS</span>
          </div>
        </div>
      </header>

      <nav className="templates-rail" aria-label="Jump to a playbook">
        {playbooks.map((playbook, index) => (
          <a key={playbook.id} className="templates-rail-item" href={`#${playbook.id}`}>
            <span className="templates-rail-index">{String(index + 1).padStart(2, "0")}</span>
            <playbook.icon aria-hidden="true" />
            <span>{playbook.tag}</span>
          </a>
        ))}
      </nav>

      <section className="templates-list" aria-label="Playbooks">
        {playbooks.map((playbook, index) => (
          <details key={playbook.id} id={playbook.id} className="template-item">
            <summary className="template-summary">
              <span className="template-index">{String(index + 1).padStart(2, "0")}</span>
              <span className="template-icon-ring"><playbook.icon aria-hidden="true" /></span>
              <span className="template-summary-text">
                <span className="landing-kicker templates-kicker">{playbook.tag}</span>
                <strong>{playbook.title}</strong>
              </span>
              <span className="template-summary-cols" aria-label="Columns produced">
                {playbook.columns.slice(0, 4).map((column) => (
                  <em key={column}>{column}</em>
                ))}
              </span>
              <span className="template-expand">EXPAND</span>
            </summary>

            <div className="template-body">
              <p className="template-intro">{playbook.intro}</p>

              <div className="template-section">
                <span className="templates-section-kicker"><i />THE PROMPT</span>
                <pre>{playbook.prompt}</pre>
              </div>

              <div className="template-section">
                <span className="templates-section-kicker"><i />NODE CHAIN</span>
                <ol className="template-chain-list">
                  {playbook.chainNotes.map(([name, note]) => (
                    <li key={name}><strong>{name}</strong><em>{note}</em></li>
                  ))}
                </ol>
              </div>

              <div className="template-section-grid">
                <div className="template-section">
                  <span className="templates-section-kicker"><i />COLS</span>
                  <ul className="template-cols-list">
                    {playbook.columns.map((column) => (
                      <li key={column}><code>{column}</code></li>
                    ))}
                  </ul>
                </div>
                <div className="template-section">
                  <span className="templates-section-kicker"><i />COST</span>
                  <p className="template-cost-line">{playbook.cost}</p>
                  <small className="template-cost-note">{playbook.costNote}</small>
                </div>
              </div>

              <div className="template-section">
                <span className="templates-section-kicker"><i />GOOD TO KNOW</span>
                <ul className="template-goodtoknow-list">
                  {playbook.goodToKnow.map((note, noteIndex) => (
                    <li key={noteIndex}>{note}</li>
                  ))}
                </ul>
              </div>

              <div className="template-footer-actions">
                <a className="template-cta" href={SELF_HOSTING_URL}>
                  <Upload aria-hidden="true" /> SELF-HOST N3RF &amp; RUN THIS PLAYBOOK <ArrowUpRight aria-hidden="true" />
                </a>
                <span className="template-tag">PROVEN PATTERN · {playbook.tag}</span>
              </div>
            </div>
          </details>
        ))}
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-main">
          <a className="landing-footer-brand" href="/" aria-label="n3rf home">n3rf</a>
          <span>Six playbooks. One machine. No platform fee.</span>
          <nav aria-label="Footer">
            <a href="/">Landing</a>
            <a href="/legal">About · Privacy · Terms · Data</a>
            <a href={SELF_HOSTING_URL}>Self-hosting guide <ArrowUpRight aria-hidden="true" /></a>
          </nav>
        </div>
        <p className="landing-footer-note">© 2026 n3rf · AI-generated output can be wrong. Verify before you ship.</p>
      </footer>
    </main>
  );
}
