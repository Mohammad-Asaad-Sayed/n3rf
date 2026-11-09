import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Database,
  Eye,
  KeyRound,
  Rows3,
  Workflow,
} from "lucide-react";
import { SELF_HOSTING_URL } from "./links";
import "./styles/landing.css";

const comparison = [
  ["Research each row", "Ask AI and web-search nodes can run over rows in a workflow.", "Claygent is designed for AI-assisted research within Clay."],
  ["Shape the workflow", "Arrange search, AI, and data transformations as visible steps.", "Use Clay's tables, enrichment features, and connected data sources."],
  ["Inspect a run", "See row counts, status, errors, and sample outputs by node.", "Review results in Clay; available details depend on its current product and plan."],
  ["Provider costs", "No n3rf platform fee. Model and search providers may charge separately.", "Clay plans and credit usage depend on current pricing and features."],
  ["Contact data and CRM", "Bring an external service through a configured HTTP Request node.", "Clay may be a better fit when you rely on its data-provider integrations or CRM workflows."],
];

const steps = [
  {
    icon: Rows3,
    title: "Start with your table",
    description: "Export the rows you want to research as CSV and load them into n3rf.",
  },
  {
    icon: Workflow,
    title: "Build the research steps",
    description: "Use web search and Ask AI nodes to look up and answer your question for each row.",
  },
  {
    icon: Eye,
    title: "Test and inspect",
    description: "Run a small sample, review the output and row counts, then decide whether to run the full batch.",
  },
];

export function ClaygentAlternativePage() {
  return (
    <main className="landing-shell claygent-page">
      <header className="landing-nav claygent-nav">
        <a className="claygent-brand" href="/" aria-label="n3rf home">n3rf</a>
        <a className="claygent-back" href="/"><ArrowLeft aria-hidden="true" /> Back to n3rf</a>
        <a className="ui-button ui-button-md ui-button-primary" href={SELF_HOSTING_URL}>
          Self-host n3rf <ArrowUpRight aria-hidden="true" />
        </a>
      </header>

      <div className="landing-content">
        <section className="claygent-hero">
          <span className="landing-kicker">AI RESEARCH FOR ROWS</span>
          <h1>A Claygent alternative for research workflows you can inspect.</h1>
          <p>
            If your Claygent task is to research a question for every row, n3rf lets
            you build that job as a local workflow—with your own model and search
            providers, and row counts visible at every step.
          </p>
          <div className="claygent-hero-actions">
            <a className="ui-button ui-button-md ui-button-primary" href={SELF_HOSTING_URL}>
              Build a research workflow <ArrowUpRight aria-hidden="true" />
            </a>
            <span><KeyRound aria-hidden="true" /> No n3rf account or platform fee</span>
          </div>
          <p className="claygent-disclaimer">
            This is a focused alternative for row-by-row research, not a drop-in
            replacement for all of Clay. Product features and pricing can change.
          </p>
        </section>

        <section className="claygent-section">
          <div className="landing-section-heading">
            <span className="landing-kicker">THE DIFFERENCE</span>
            <h2>Similar research job. Different workflow and trade-offs.</h2>
            <p>
              Claygent is part of Clay’s broader platform. n3rf focuses on running
              AI and web research steps over your own rows and making each step’s
              results inspectable.
            </p>
          </div>
          <div className="method-table-wrap">
            <table className="method-table claygent-comparison">
              <thead>
                <tr><th>CAPABILITY</th><th>N3RF</th><th>CLAY / CLAYGENT</th></tr>
              </thead>
              <tbody>
                {comparison.map(([capability, n3rf, clay]) => (
                  <tr key={capability}>
                    <th scope="row">{capability}</th>
                    <td>{n3rf}</td>
                    <td>{clay}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="table-foot">
            High-level product comparison, not a feature benchmark. Check Clay’s
            current documentation and pricing for details.
          </p>
        </section>

        <section className="claygent-section">
          <div className="landing-section-heading">
            <span className="landing-kicker">A SIMPLE START</span>
            <h2>Bring a Claygent-style research task into n3rf.</h2>
            <p>Start with the question you need answered and the rows you already have.</p>
          </div>
          <div className="claygent-steps">
            {steps.map(({ icon: Icon, title, description }, index) => (
              <article key={title}>
                <span className="claygent-step-top">
                  <Icon aria-hidden="true" />
                  <span className="landing-kicker">0{index + 1}</span>
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
                {index < steps.length - 1 && <ArrowRight className="claygent-step-arrow" aria-hidden="true" />}
              </article>
            ))}
          </div>
        </section>

        <section className="claygent-boundary">
          <Database aria-hidden="true" />
          <div>
            <span className="landing-kicker">WHEN TO KEEP CLAY</span>
            <h2>Need Clay’s data-provider integrations or CRM workflows?</h2>
            <p>
              Keep using Clay for those jobs. n3rf can complement that setup when
              you want a custom, inspectable AI research workflow over a dataset.
            </p>
          </div>
          <a className="ui-button ui-button-md ui-button-primary" href={SELF_HOSTING_URL}>
            Self-host n3rf <ArrowUpRight aria-hidden="true" />
          </a>
        </section>

        <footer className="claygent-footer">
          <a href="/"><ArrowLeft aria-hidden="true" /> Back to n3rf home</a>
          <span>n3rf is not affiliated with Clay. <a href="/legal">About · Privacy · Terms · Data</a></span>
        </footer>
      </div>
    </main>
  );
}
