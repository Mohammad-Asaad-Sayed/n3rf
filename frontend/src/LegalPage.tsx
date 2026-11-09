import { ArrowLeft, ArrowUpRight, Database, ExternalLink, ShieldCheck } from "lucide-react";
import "./styles/landing.css";

const dataTypes = [
  ["Spreadsheet input", "CSV/TSV files are read in the browser. Excel (.xlsx) files are sent to your n3rf backend for parsing. File contents are not intentionally saved as a separate server-side file."],
  ["Browser draft", "The editor stores an auto-recovery workflow draft in browser local storage. It can include row data placed in workflow parameters. Canvas pane widths are also stored locally."],
  ["Saved workflows", "When you save a workflow, its nodes, parameters, and edges are stored in the instance database on the machine running n3rf."],
  ["Saved run history", "Runs of saved workflows are stored with their results in the instance database. Unsaved workflow runs are not added to run history."],
  ["Provider credentials", "Saved provider profiles contain configuration and an environment-variable name, not the secret itself. A key pasted for a single request is sent to your local backend and the selected provider, and is not intentionally persisted by n3rf."],
  ["External requests", "AI, web search, page-reading, and HTTP Request nodes send the configured prompt or row data to the external service you selected. The service's terms and privacy practices apply."],
  ["Hosting and logs", "The person or organization operating the instance controls server access, backups, logs, and retention. Hosting providers may separately process connection metadata under their own terms."],
];

export function LegalPage() {
  return (
    <main className="landing-shell legal-page">
      <header className="landing-nav legal-nav">
        <a className="legal-brand" href="/">n3rf</a>
        <nav aria-label="Legal and information sections">
          <a href="#about">About</a>
          <a href="#privacy">Privacy</a>
          <a href="#terms">Terms</a>
          <a href="#data">Data</a>
        </nav>
        <a className="legal-home-link" href="/">Back to n3rf <ArrowUpRight aria-hidden="true" /></a>
      </header>

      <div className="landing-content">
        <header className="legal-hero">
          <span className="landing-kicker">PROJECT INFORMATION</span>
          <h1>About, privacy, terms, and data.</h1>
          <p>How n3rf works, what it stores, and what to consider when you run it.</p>
        </header>

        <aside className="legal-draft-notice">
          <ShieldCheck aria-hidden="true" />
          <p>
            <strong>Deployment-specific notice.</strong> n3rf is self-hostable software.
            These notes describe the current project code, not every deployment. Operators
            should review these terms for their organization, location, and hosting setup.
            This page is not legal advice.
          </p>
        </aside>

        <section className="legal-section" id="about">
          <span className="landing-kicker">01 · ABOUT</span>
          <h2>AI workflows for batches of rows.</h2>
          <p>
            n3rf is a local-first workflow builder for turning tabular input into structured
            output. Connect steps for transforming rows, calling AI models, searching the web,
            and making authorized HTTP requests. The editor shows run status and row counts
            by step so you can inspect what happened.
          </p>
          <p>
            n3rf is software, not an AI model or data provider. You configure the providers
            and endpoints used by your workflows. There is no n3rf platform fee; third-party
            services and the machine used to run n3rf may have their own costs.
          </p>
          <p>
            n3rf is not affiliated with or endorsed by Clay. Product names belong to their
            respective owners. View the project source on{" "}
            <a href="https://github.com/Mohammad-Asaad-Sayed/n3rf" target="_blank" rel="noreferrer">
              GitHub <ExternalLink aria-hidden="true" />
            </a>.
          </p>
        </section>

        <section className="legal-section" id="privacy">
          <span className="landing-kicker">02 · PRIVACY</span>
          <h2>Privacy depends on where you run n3rf.</h2>
          <p>
            In a self-hosted setup, workflow data is handled by the browser and the n3rf
            backend you operate. The project does not provide a central n3rf account service.
            If someone else hosts your instance, that operator controls access to the host
            and its stored data.
          </p>
          <h3>Information handled by the software</h3>
          <ul>
            <li>Browser local storage holds an auto-recovery workflow draft, which can include row data, and editor pane preferences.</li>
            <li>The local database stores saved workflows, model profile configuration, and results for runs of saved workflows.</li>
            <li>Provider secrets are read from the backend environment. Profiles store the variable name, not its secret value.</li>
            <li>A key pasted for a one-time request is sent to the local backend and selected provider; n3rf does not intentionally save it.</li>
            <li>The application code does not include an analytics SDK. Your chosen hosting environment may still keep its own logs.</li>
          </ul>
          <h3>Third-party services</h3>
          <p>
            When a workflow uses an AI, search, page-reading, or HTTP Request node, configured
            data is sent to that service. Review the service’s privacy terms and retention
            settings before sending personal, confidential, or regulated information.
          </p>
          <h3>Retention and requests</h3>
          <p>
            The instance operator controls database backups and retention. Workflow deletion
            does not necessarily remove saved run history. Browser drafts can be removed from
            browser storage; saved data can be removed by the operator by managing the local
            database and backups. For a hosted instance, contact its operator about privacy
            requests.
          </p>
        </section>

        <section className="legal-section" id="terms">
          <span className="landing-kicker">03 · TERMS</span>
          <h2>Use the software responsibly.</h2>
          <p>
            These are general use terms for the n3rf project and need review by the operator
            before being used as binding terms for a hosted service.
          </p>
          <h3>Your data and instructions</h3>
          <p>
            You are responsible for having the rights and permissions needed to process,
            upload, or send your data to the providers configured in your workflow. Use
            authorized endpoints and follow applicable laws and third-party service terms.
          </p>
          <h3>AI and external services</h3>
          <p>
            AI-generated and web-researched output can be inaccurate, incomplete, outdated,
            or misleading. Review and verify output before relying on it, especially for
            consequential decisions. You are responsible for provider selection, credentials,
            usage, and any associated charges.
          </p>
          <h3>Local execution and security</h3>
          <p>
            n3rf is designed for a trusted, single-operator deployment. Do not expose an
            instance to untrusted users or networks: the Code node is not a security boundary
            for multi-tenant use. Protect the host, database, backups, and provider credentials.
          </p>
          <h3>Availability and liability</h3>
          <p>
            The software is provided as-is and as-available, without a promise of uninterrupted
            operation, error-free results, or suitability for a particular purpose. Any
            warranty exclusions or liability limits apply only to the extent permitted by
            applicable law. A project maintainer should add operator identity, contact details,
            and governing-law terms before relying on this section as a legal agreement.
          </p>
        </section>

        <section className="legal-section" id="data">
          <span className="landing-kicker">04 · DATA</span>
          <h2>Where information goes.</h2>
          <p>
            n3rf is local-first, but local does not mean data never leaves the machine. Files
            and row data may be sent to your own backend or to the external services you
            configure. This table summarizes the default application behavior.
          </p>
          <div className="legal-data-wrap">
            <table className="legal-data-table">
              <thead><tr><th>DATA</th><th>LOCATION / USE</th></tr></thead>
              <tbody>
                {dataTypes.map(([kind, detail]) => (
                  <tr key={kind}><th scope="row">{kind}</th><td>{detail}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="legal-data-callout">
            <Database aria-hidden="true" />
            <p>
              <strong>Before using sensitive data:</strong> secure the machine and local
              database, check browser storage on shared devices, and confirm the policies of
              every model, search, or HTTP service in your workflow.
            </p>
          </div>
        </section>

        <footer className="legal-footer">
          <a href="/"><ArrowLeft aria-hidden="true" /> Back to n3rf</a>
          <span>Content updated: November 10, 2026 · Ask your deployment operator about local policies.</span>
        </footer>
      </div>
    </main>
  );
}
