import { useEffect } from "react";
import {
  ArrowDown,
  ArrowRight,
  CheckCircle2,
  Plus,
  Send,
} from "lucide-react";
import "./styles/landing.css";
import "./styles/answers.css";
import { SELF_HOSTING_URL } from "./links";
import { SiteNav } from "./SiteNav";

const chips = [
  "Launches & messaging",
  "Competitive & win/loss",
  "Pricing & packaging",
  "Objection handling",
  "Enablement & onboarding",
  "Internal positioning",
];

const faq = [
  {
    q: "What is the answer desk?",
    a: "Slack-native, cited answers to the GTM and PMM questions your team keeps re-asking. It answers from your own playbook, asks one sharp question when the match is weak, or routes to the owner with full context. The loop is being exercised on real GTM questions inside n3rf today.",
  },
  {
    q: "Is it available today?",
    a: "Partially, and we won't pretend otherwise. The two packs it is built on — Slack (Send Message / Add Reaction / Fetch Thread) and Supabase (Select / Upsert / RPC) — ship in the open-source n3rf build. The answering loop itself is in early build.",
  },
  {
    q: "Where does it run, and what leaves my network?",
    a: "Inside your n3rf — on your machine, on your models, against your playbook and your decisions log. Nothing is hosted by us; data leaves only if you route it through a model or search provider you chose.",
  },
  {
    q: "What does it cost?",
    a: "n3rf is AGPL-3.0 and free to self-host — no platform fee, no credits wall. You pay only the model and search providers you wire up; their free tiers usually cover a first pilot.",
  },
  {
    q: "How do I try it or get involved?",
    a: "Self-host n3rf with the Slack pack (the self-hosting guide walks through it), run your first play against a test channel, and open an issue with the GTM questions you keep getting asked — that is how the playbook grows.",
  },
];

export function AnswerDeskPage() {
  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !("IntersectionObserver" in window)
    ) {
      elements.forEach((el) => el.setAttribute("data-revealed", "true"));
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
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
    );
    elements.forEach((el) => observer.observe(el));
    const fallback = window.setTimeout(() => {
      elements.forEach((el) => el.setAttribute("data-revealed", "true"));
    }, 1500);
    return () => {
      observer.disconnect();
      window.clearTimeout(fallback);
    };
  }, []);

  return (
    <main className="landing-shell answers-shell">
      <SiteNav active="magi" />

      <header className="answers-hero">
        <div className="answers-hero-frame">
          <span className="answers-bracket answers-bracket-tl" aria-hidden="true" />
          <span className="answers-bracket answers-bracket-tr" aria-hidden="true" />
          <span className="answers-bracket answers-bracket-bl" aria-hidden="true" />
          <span className="answers-bracket answers-bracket-br" aria-hidden="true" />

          <div className="answers-hero-copy">
            <p className="landing-kicker">EARLY BUILD · N3RF · FOR GTM &amp; PMM</p>
            <h1>The answer desk for <em>GTM &amp; PMM.</em></h1>
            <p className="answers-subhead">
              Slack-native answers from the playbook you already have — the source
              cited, one sharp question when it's unsure, a clean handoff when it
              isn't. On your machine, on your models.
            </p>
            <div className="answers-actions">
              <a className="ui-button ui-button-md ui-button-primary" href="#method">
                See how it decides <ArrowDown aria-hidden="true" />
              </a>
              <a className="ui-button ui-button-md" href={SELF_HOSTING_URL}>
                Self-host n3rf
              </a>
            </div>
            <p className="answers-status">
              <span className="answers-status-dot" aria-hidden="true" />
              <span><b>In early build.</b> The Slack and Supabase packs ship in the
              open-source build today; the answering loop is exercised on real GTM
              questions. Nothing here is a mock screenshot.</span>
            </p>
          </div>

          <figure className="answers-fig" aria-label="A question enters the desk and leaves down one of three exits: answer with a cited source, ask one scoped question, or route to the owner.">
            <div className="answers-fig-frame">
              <div className="answers-fig-head">
                <span>n3rf · decision flow</span>
                <span className="answers-fig-live"><i aria-hidden="true" />live</span>
              </div>
              <svg viewBox="0 0 420 300" width="100%" role="presentation" aria-hidden="true">
                <defs>
                  <pattern id="answers-dots" width="16" height="16" patternUnits="userSpaceOnUse">
                    <circle cx="1" cy="1" r="1" fill="var(--line-strong)" />
                  </pattern>
                </defs>
                <rect x="0" y="0" width="420" height="300" fill="url(#answers-dots)" opacity="0.35" />
                <path stroke="var(--line-strong)" strokeWidth="1.5" fill="none" d="M30 150 H150" />
                <rect x="18" y="126" width="112" height="48" fill="var(--surface-void)" stroke="var(--line-strong)" />
                <text x="74" y="146" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="11" fill="var(--text-primary)" letterSpacing="0.08em">QUESTION</text>
                <text x="74" y="162" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="8.5" fill="var(--text-meta)">"what's our line on…"</text>
                <path stroke="var(--line-strong)" strokeWidth="1.5" strokeDasharray="4 5" fill="none" d="M150 150 H210" />
                <rect x="210" y="120" width="72" height="60" fill="var(--surface-raised)" stroke="var(--line-strong)" />
                <path stroke="var(--accent)" strokeWidth="3.5" strokeLinecap="square" fill="none" d="M228 158V134l14 18 14-18v24" />
                <path stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="4 5" fill="none" d="M282 132 H342 V64 H372" />
                <path stroke="var(--info)" strokeWidth="1.5" strokeDasharray="4 5" fill="none" d="M282 150 H372" />
                <path stroke="var(--alert)" strokeWidth="1.5" strokeDasharray="4 5" fill="none" d="M282 168 H342 V236 H372" />
                <text x="366" y="60" textAnchor="end" fontFamily="var(--font-mono)" fontSize="8" fill="var(--text-meta)" letterSpacing="0.08em">ANSWER</text>
                <text x="366" y="142" textAnchor="end" fontFamily="var(--font-mono)" fontSize="8" fill="var(--text-meta)" letterSpacing="0.08em">ASK</text>
                <text x="366" y="232" textAnchor="end" fontFamily="var(--font-mono)" fontSize="8" fill="var(--text-meta)" letterSpacing="0.08em">ROUTE</text>
                <rect x="372" y="36" width="34" height="56" fill="var(--surface-void)" stroke="var(--accent)" />
                <text x="389" y="68" textAnchor="middle" fontFamily="var(--font-display)" fontWeight="700" fontSize="14" fill="var(--accent)">A</text>
                <rect x="372" y="122" width="34" height="56" fill="var(--surface-void)" stroke="var(--info)" />
                <text x="389" y="154" textAnchor="middle" fontFamily="var(--font-display)" fontWeight="700" fontSize="14" fill="var(--info)">S</text>
                <rect x="372" y="208" width="34" height="56" fill="var(--surface-void)" stroke="var(--alert)" />
                <text x="389" y="240" textAnchor="middle" fontFamily="var(--font-display)" fontWeight="700" fontSize="14" fill="var(--alert)">R</text>
              </svg>
              <figcaption className="answers-fig-cap">One question in · three exits · a reason attached</figcaption>
            </div>
          </figure>
        </div>
      </header>

      <section id="method" className="landing-section" aria-label="How the answer desk decides" data-reveal>
        <div className="landing-content">
          <div className="landing-section-heading">
            <p className="landing-kicker">HOW IT DECIDES</p>
            <h2>Three exits. <em>Never</em> a guess.</h2>
            <p>Every question the desk hears ends in exactly one of three places — and it always tells you which, and why.</p>
          </div>
          <div className="answers-paths">
            <article className="answers-path">
              <div className="answers-path-ix" aria-hidden="true">A</div>
              <h3>Answer</h3>
              <p>Confident match on your playbook. Posts inline, cites the source section, and asks for a thumbs-up or thumbs-down to keep the playbook honest.</p>
              <p className="answers-path-foot">When the playbook knows — say it.</p>
            </article>
            <article className="answers-path answers-path--info">
              <div className="answers-path-ix" aria-hidden="true">S</div>
              <h3>Ask</h3>
              <p>Weak or tied match. One scoped question — the exact fact that would decide it — then it re-checks the playbook instead of improvising around the gap.</p>
              <p className="answers-path-foot">When one fact is missing, ask for one fact.</p>
            </article>
            <article className="answers-path answers-path--alert">
              <div className="answers-path-ix" aria-hidden="true">R</div>
              <h3>Route</h3>
              <p>No match — or above its pay grade. Sends the thread, the summary, and what it already tried to the person who owns the answer, then steps back.</p>
              <p className="answers-path-foot">When it doesn't know, it hands off cleanly.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="landing-section" aria-label="Where the knowledge comes from" data-reveal>
        <div className="landing-content">
          <div className="answers-split">
            <div className="landing-section-heading answers-split-heading">
              <p className="landing-kicker">THE KNOWLEDGE LAYER</p>
              <h2>Distilled, <em>not written.</em></h2>
              <p>Hand-authored wikis go stale. The desk compresses the GTM work that actually happened — so the answer you get is the one that held up last time.</p>
            </div>
            <div>
              <ul className="answers-facts">
                <li><em aria-hidden="true">01</em><div><b>Compressed from real work</b><span>Not interviews about what people think they do — launches shipped, objections handled, wins distilled.</span></div></li>
                <li><em aria-hidden="true">02</em><div><b>Cited on every answer</b><span>Every response carries its source section, so you can check the ground it stands on.</span></div></li>
                <li><em aria-hidden="true">03</em><div><b>Gaps surface themselves</b><span>Questions the desk can't answer cluster — and the loudest clusters are your next playbook sections.</span></div></li>
              </ul>
              <p className="answers-chips-label">What the playbook covers</p>
              <ul className="answers-chips" aria-label="Playbook domains">
                {chips.map((chip) => <li key={chip}>{chip}</li>)}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="answers-band" aria-label="Why GTM and product marketing" data-reveal>
        <div className="answers-band-inner">
          <div className="answers-band-grid">
            <div className="answers-band-copy">
              <p className="answers-band-label">FOR GTM &amp; PMM</p>
              <h2 className="answers-band-title">Built for the people<br />who get asked.</h2>
              <p className="answers-band-lead">One cited answer instead of three drifting versions — and when the desk can't find it, it says so.</p>
            </div>
            <div className="answers-band-stat" role="img" aria-label="Zero guesses — every answer is cited, scoped, or routed to the owner">
              <b aria-hidden="true">0</b>
              <span>guesses, ever —<br />every answer cited,<br />asked, or routed</span>
            </div>
          </div>
          <div className="answers-band-row">
            <article className="answers-gtm">
              <em>01 · Message</em>
              <h3>Positioning that survives contact</h3>
              <p>Answers land in your approved words, from the latest messaging — not a model's paraphrase of what positioning presumably might be.</p>
            </article>
            <article className="answers-gtm">
              <em>02 · Consistency</em>
              <h3>One answer, everywhere</h3>
              <p>Sales, CS, the founder's DMs — everyone hears the same cited answer instead of three drifting versions of it.</p>
            </article>
            <article className="answers-gtm">
              <em>03 · Signal</em>
              <h3>The gaps write themselves</h3>
              <p>A question the desk can't answer isn't a failure. It's a ranked to-do list of what the playbook still needs.</p>
            </article>
          </div>
          <p className="answers-band-foot"><em>THE POINT</em>“What keeps getting asked is what hasn't been written down yet.”</p>
        </div>
      </section>

      <section id="faq" className="landing-section answers-faq" aria-label="Frequently asked questions" data-reveal>
        <div className="landing-content">
          <div className="landing-section-heading">
            <p className="landing-kicker">FAQ</p>
            <h2>Asked first,<br />answered once.</h2>
          </div>
          {faq.map((item, index) => (
            <details key={item.q} open={index === 0}>
              <summary><em>{String(index + 1).padStart(2, "0")}</em><span className="answers-faq-q">{item.q}</span><Plus className="answers-faq-icon" size={16} aria-hidden="true" /></summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-section" aria-label="Self-host" data-reveal>
        <div className="landing-content">
          <div className="landing-section-heading">
            <p className="landing-kicker">GET YOURS RUNNING</p>
            <h2>Same shelf. <em>Your models.</em></h2>
            <p>The answer desk is part of the n3rf family — self-host it with the Slack and Supabase packs, wire your own keys, and point it at a test channel.</p>
          </div>
          <div className="answers-actions answers-cta-actions">
            <a className="ui-button ui-button-md ui-button-primary" href={SELF_HOSTING_URL}>
              <CheckCircle2 aria-hidden="true" /> Self-host n3rf <ArrowRight aria-hidden="true" />
            </a>
            <a className="ui-button ui-button-md" href="https://github.com/Mohammad-Asaad-Sayed/n3rf/issues">
              Open an issue with your questions
            </a>
          </div>
          <p className="answers-cta-note">
            <Send size={12} aria-hidden="true" /> Early build · AGPL-3.0 · no platform fee
          </p>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-content">
        <div className="landing-footer-main">
          <a className="landing-footer-brand" href="/" aria-label="n3rf home">n3rf</a>
          <span>Self-hosted AI data workflows for structured rows.</span>
          <nav aria-label="Footer">
            <a href="/magi">Answer desk</a>
            <a href="/templates">Templates</a>
            <a href="/community">Community</a>
            <a href="/legal">About · Privacy · Terms · Data</a>
          </nav>
        </div>
        <p className="landing-footer-note">© 2026 n3rf · AI-generated information may be inaccurate. Verify important results.</p>
        </div>
      </footer>
    </main>
  );
}

export default AnswerDeskPage;
