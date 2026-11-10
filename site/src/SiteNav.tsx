import { ArrowUpRight, Upload, Workflow } from "lucide-react";
import "./styles/landing.css";
import { SELF_HOSTING_URL } from "./links";

type SiteNavProps = {
  /** Which page is active — "landing" | "templates" | "community" */
  active?: "landing" | "templates" | "community";
  /** In-page scroll handler. Defaults to full navigation to "/#id". */
  onNavigate?: (id: string) => void;
};

export function SiteNav({ active = "landing", onNavigate }: SiteNavProps) {
  const go = (id: string) => () => {
    if (onNavigate) {
      onNavigate(id);
      return;
    }
    window.location.href = `/#${id}`;
  };

  return (
    <header className="site-nav" data-active={active}>
      <a className="site-nav-brand" href="/" aria-label="n3rf — home">
        <span className="site-nav-mark" aria-hidden="true"><Workflow /></span>
        <span className="site-nav-wordmark">N<span className="site-nav-wordmark-rest">3RF</span></span>
        <span className="site-nav-status"><i />READY · LOCAL</span>
      </a>
      <nav className="site-nav-links" aria-label="Marketing site">
        <button type="button" onClick={go("landing-what")}>Examples</button>
        <a href="/templates" aria-current={active === "templates" ? "page" : undefined}>Templates</a>
        <a href="/community" aria-current={active === "community" ? "page" : undefined}>Community</a>
        <button type="button" onClick={go("landing-how")}>How it works</button>
        <button type="button" onClick={go("landing-pricing")}>Costing</button>
        <button type="button" onClick={go("landing-faq")}>FAQ</button>
      </nav>
      <a className="site-nav-cta" href={SELF_HOSTING_URL}>
        <Upload /> Self-host <ArrowUpRight />
      </a>
    </header>
  );
}
