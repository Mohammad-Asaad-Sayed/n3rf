import { useEffect } from "react";
import { ArrowUpRight, Sparkles, Users, Wrench, MessageSquare, ShieldCheck, Star, Bug, ClipboardList, Share2, MapPin, Coffee, Video, KeyRound, HeartHandshake, Check } from "lucide-react";
import "./styles/landing.css";
import { SiteNav } from "./SiteNav";

const ethos = [
  "A lot of GTM work is done by a team of one. You shouldn't have to figure it out alone.",
  "Bring real problems. Leave with useful answers — or a better question.",
  "Show the system, not the pitch: prompts, automations, costs, and decisions.",
  "Give more than you take. Credit where ideas came from.",
];

const who = [
  {
    icon: Wrench,
    title: "People building GTM tools",
    desc: "You write nodes, integrations, scrapers, or workflows in the GTM space. Bring the half-finished thing — that's often the most interesting one.",
  },
  {
    icon: Sparkles,
    title: "People bending OSS tools",
    desc: "You took n8n, PostHog, OpenBot, n3rf, or something else and used it in a way nobody expected. We want to see it.",
  },
  {
    icon: Users,
    title: "Operators running the stack",
    desc: "RevOps, growth, and marketing folks using these tools every day. You know what breaks, what's expensive, and what actually ships.",
  },
  {
    icon: MessageSquare,
    title: "People on the receiving end",
    desc: "If GTM pipelines reach you, your perspective matters. Good feedback from the audience side is rare and valuable.",
  },
];

const topics = [
  "Workflows and prompts that held up — and the ones that fell apart, and why.",
  "Cost, concurrency, row counts, and tracing where the output went wrong.",
  "Choosing a model or provider: what you used, what it cost, and what you'd change.",
  "New uses for open-source GTM tools — n8n, PostHog, OpenBot, n3rf, or anything with an API.",
  "Pune meetups, office hours, and chances to build alongside other people.",
];

const rituals = [
  { n: "01", title: "Build and share", desc: "Bring a workflow, a dataset, or a question. Build for a focused block, then show what you made and what you learned. Something that works, or something that broke in a useful way." },
  { n: "02", title: "Show your work", desc: "Walk through the real thing: the prompt, the node chain, the cost per row, and where it failed. The messy truth is the useful part." },
  { n: "03", title: "Themed build sessions", desc: "Everyone works in one shared area — lead enrichment, row debugging, search + AI pipelines, cost tuning — so people can compare approaches and help each other." },
  { n: "04", title: "Guided walkthroughs", desc: "One person shows how they built something (n8n flow, n3rf pipeline, PostHog setup), then others try the same ideas on their own problem." },
  { n: "05", title: "Peer circles", desc: "A small group, 8–12 people. Share wins, challenges, and a case to work through together. No pitches, no slides." },
  { n: "06", title: "Online and async", desc: "For people who can't make it in person. Share progress, ask questions, and get feedback in chat between sessions." },
];

const rules = [
  "Give more than you take.",
  "Be kind. Critique ideas, not people.",
  "No cold pitching, recruitment spam, or unsolicited DMs for leads.",
  "No ads or disguised promotion. Share what you learned, not what you're selling.",
  "Keep career talk in its own thread so the main space stays useful.",
  "Protect people's privacy. Don't scrape, export, or message the member list.",
  "Share work generously, and credit the people and projects behind it.",
  "Skip politics and religion. We're here to build and learn.",
  "Follow the project's Code of Conduct (in the repo).",
];

const REPO_URL = "https://github.com/Mohammad-Asaad-Sayed/n3rf";
const ISSUES_URL = "https://github.com/Mohammad-Asaad-Sayed/n3rf/issues";

const support = [
  {
    icon: Star,
    title: "Star the repo",
    desc: "A star is thirty seconds, costs nothing, and is how other operators find this before spending hours rebuilding it themselves.",
    href: REPO_URL,
    link: "Star on GitHub",
  },
  {
    icon: Bug,
    title: "File a good bug",
    desc: "Hit an error, a slow run, or a confusing screen? An issue with steps to reproduce, what you expected, and what happened is a real contribution.",
    href: ISSUES_URL,
    link: "Open an issue",
  },
  {
    icon: ClipboardList,
    title: "Bring a template",
    desc: "Workflow templates and examples are the fastest way to take someone from repo to first run. Bring yours via issues or a pull request.",
    href: ISSUES_URL,
    link: "Share via issues",
  },
  {
    icon: Share2,
    title: "Tell one operator",
    desc: "Word of mouth is how niche tools survive. Show one RevOps or founder friend what n3rf does — one conversation beats a hundred impressions.",
    href: REPO_URL,
    link: "Send them the repo",
  },
];

const SPONSOR_ISSUE_URL =
  "https://github.com/Mohammad-Asaad-Sayed/n3rf/issues/new?title=Sponsorship&body=What+would+you+like+to+sponsor%20%28venue%2C+food%2C+equipment%2C+community%29%3F";

const sponsorshipCovers = [
  { icon: MapPin, strong: "Venue or host", rest: "Offer a space in Pune for build sessions, walkthroughs, and meetups." },
  { icon: Coffee, strong: "Tea, food & essentials", rest: "Five people or fifty — goodwill compounds fast." },
  { icon: Video, strong: "Equipment & streaming", rest: "Cameras, mics, and capture so remotes can follow along." },
  { icon: KeyRound, strong: "API credits & model access", rest: "Provider tokens for build sessions — sponsored pool or member keys, nobody's key is shared." },
  { icon: HeartHandshake, strong: "Community sponsor", rest: "Recurring support that keeps the room open as the group grows." },
];

const sponsorshipGets = [
  "Your name or logo in the room and on this page — plainly credited, always.",
  "A short, clearly-labeled walkthrough slot at a session — a demo, never a pitch.",
  "First access to session materials, if you want them.",
];

const faqs = [
  { q: "When does it open?", a: "Soon. This page will be updated when the group is ready to join." },
  { q: "Is it only for n3rf users?", a: "No. Any open-source GTM tool belongs here — n3rf, n8n, PostHog, OpenBot, or something you built yourself." },
  { q: "Do I need to be technical?", a: "No. If you run GTM workflows, depend on them, or are affected by them, you have something useful to contribute." },
  { q: "Is it only for people in Pune?", a: "The focus is Pune — local meetups and a local group — but online and async participation will be part of it too." },
  { q: "Can I share my workflow?", a: "Please do. Share the prompt, the steps, the cost, and what broke. Redact anything sensitive before you post it." },
  { q: "What will meetups look like?", a: "Small and practical. Bring a laptop and a question. Expect 15–20 people at first, working sessions over talks, and time to show what you made." },
  { q: "Is there a sponsorship program?", a: "Yes — sponsorship is the community's support system. See section 05 for how to partner (venue, food, equipment, or recurring support). There's no published price list yet; we work out terms with each sponsor directly. The non-financial ways to help are listed there too." },
  { q: "Is there a code of conduct?", a: "Yes. The full rules and participation guide will live in COMMUNITY.md in the repo." },
];

export function CommunityPage() {
  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
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
    return () => observer.disconnect();
  }, []);

  return (
    <main className="landing-shell templates-shell community-shell">
      <SiteNav active="community" />

      <header className="community-hero">
        <div className="community-hero-frame">
          <span className="templates-bracket templates-bracket-tl" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-tr" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-bl" aria-hidden="true" />
          <span className="templates-bracket templates-bracket-br" aria-hidden="true" />
          <p className="landing-kicker templates-kicker">COMMUNITY · PUNE · COMING SOON</p>
          <h1>Experimenting with GTM-Tech on the open stack, <em>together.</em></h1>
          <p className="templates-hero-sub">
            Make open-source GTM tools do useful things. For folks testing tools, workflows, and dev marketing ideas on the open stack. A Pune space for builders, operators, and the people their work reaches — n3rf, n8n, PostHog, OpenBot, and whatever comes next. No pitches, no posturing.
          </p>
          <div className="community-coming-soon-badge" aria-label="Status">
            <span className="community-pulse" /> COMING SOON
          </div>
        </div>
        <div className="community-ethos" aria-label="Community ethos">
          {ethos.map((line, i) => (
            <p key={i} className="community-ethos-line"><span>{String(i + 1).padStart(2, "0")}</span>{line}</p>
          ))}
        </div>
      </header>

      <div className="landing-content">
        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">01 · WHO IT'S FOR</span>
            <h2>Different roles, one room.</h2>
            <p>You don't need the same job title to have the same problem. This group is for anyone working with open-source GTM tools — or living with the results.</p>
          </div>
          <div className="community-who-grid">
            {who.map((w) => (
              <article key={w.title} className="community-card">
                <div className="community-card-head"><w.icon aria-hidden="true" /><span>{w.title.toUpperCase()}</span></div>
                <p>{w.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">02 · WHAT WE TALK ABOUT</span>
            <h2>Real problems. Useful answers.</h2>
            <p>The conversations worth having are the ones you can act on — what worked, what didn't, and what it cost.</p>
          </div>
          <ul className="community-topics">
            {topics.map((t) => <li key={t}>{t}</li>)}
          </ul>
        </section>

        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">03 · HOW WE MEET</span>
            <h2>Six ways to spend a session.</h2>
            <p>Most sessions are open build time. Bring a laptop and something you want to try. You leave with something that works, or something that broke in a useful way.</p>
          </div>
          <div className="community-rituals">
            {rituals.map((r) => (
              <article key={r.n} className="community-ritual">
                <span className="community-ritual-n">{r.n}</span>
                <h3>{r.title}</h3>
                <p>{r.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">04 · HOUSE RULES</span>
            <h2>A few, kept short.</h2>
            <p>Enough structure to keep the space useful. Nothing more.</p>
          </div>
          <div className="community-rules">
            <div className="community-rules-head"><ShieldCheck aria-hidden="true" /><span>GIVE MORE THAN YOU TAKE</span></div>
            <ol>
              {rules.map((r, i) => <li key={i}>{r}</li>)}
            </ol>
          </div>
        </section>

        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">05 · SPONSORSHIP</span>
            <h2>Sponsor the open stack.</h2>
            <p>n3rf is AGPL-licensed and free, and the community will be free to join. It isn't free to run: venues, tea, streaming, and equipment cost real money, and the group is in growth mode. We want more helping hands — including yours.</p>
          </div>
          <div className="sponsorship-grid">
            <div className="sponsorship-panel">
              <p className="sponsorship-label">WHAT SPONSORSHIP CAN LOOK LIKE</p>
              <div className="sponsorship-lanes">
                {sponsorshipCovers.map((item) => (
                  <div className="sponsorship-lane" key={item.strong}>
                    <item.icon aria-hidden="true" />
                    <div><strong>{item.strong}</strong><p>{item.rest}</p></div>
                  </div>
                ))}
              </div>
              <p className="sponsorship-label">WHAT SPONSORS GET</p>
              <ul className="sponsorship-gets">
                {sponsorshipGets.map((item) => (
                  <li key={item}><Check aria-hidden="true" />{item}</li>
                ))}
              </ul>
            </div>
            <aside className="sponsorship-cta">
              <span className="landing-kicker">PARTNER WITH US</span>
              <h3>Let's talk.</h3>
              <p>No form, no invoice, no price list yet — the community launches first. Tell us what you'd like to sponsor and we'll work out the terms together, honestly.</p>
              <a className="ui-button ui-button-md ui-button-primary" href={SPONSOR_ISSUE_URL} target="_blank" rel="noreferrer">Sponsor via GitHub <ArrowUpRight aria-hidden="true" /></a>
              <p className="sponsorship-note">We reply through GitHub. No commitment until we've both agreed — and no publicity you didn't approve.</p>
            </aside>
          </div>
          <div className="sponsorship-help">
            <span className="sponsorship-label">CAN'T SPONSOR? STILL HELP</span>
            <div className="community-who-grid">
              {support.map((s) => (
                <article key={s.title} className="community-card">
                  <div className="community-card-head"><s.icon aria-hidden="true" /><span>{s.title.toUpperCase()}</span></div>
                  <p>{s.desc}</p>
                  <a className="community-support-link" href={s.href} target="_blank" rel="noreferrer">{s.link} <ArrowUpRight aria-hidden="true" /></a>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section community-section" data-reveal>
          <div className="landing-section-heading">
            <span className="landing-kicker">06 · FAQ</span>
            <h2>A few things you might want to know.</h2>
          </div>
          <div className="faq-list">
            {faqs.map((f) => (
              <details key={f.q} className="faq-item">
                <summary>{f.q}<ArrowUpRight aria-hidden="true" /></summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="community-join" data-reveal>
          <div>
            <span className="landing-kicker">07 · JOIN</span>
            <h2>We're getting it ready.</h2>
            <p>This community is coming soon. When it opens, this page is where you'll find the way in. Until then, keep building — and bring what you learn when the doors open.</p>
          </div>
          <span className="ui-button ui-button-md ui-button-primary community-join-btn" aria-disabled="true">
            COMING SOON
          </span>
        </section>

        <footer className="landing-footer">
          <div className="landing-footer-main">
            <a className="landing-footer-brand" href="/" aria-label="n3rf home">n3rf</a>
            <span>Open-source GTM community · Pune · Coming soon</span>
            <nav aria-label="Footer">
              <a href="/">Landing</a>
              <a href="/templates">Templates</a>
              <a href="/community">Community</a>
              <a href="/legal">About · Privacy · Terms · Data</a>
            </nav>
          </div>
          <p className="landing-footer-note">© 2026 n3rf · Built for people who learn by making things.</p>
        </footer>
      </div>
    </main>
  );
}
