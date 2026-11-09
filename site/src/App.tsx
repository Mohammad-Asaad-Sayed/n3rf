import { useEffect } from "react";
import { ClaygentAlternativePage } from "./ClaygentAlternativePage";
import { LandingPage } from "./LandingPage";
import { LegalPage } from "./LegalPage";
import "./styles/site.css";

export function App() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";

  useEffect(() => {
    if (path === "/legal") {
      document.title = "About, privacy, terms, and data | n3rf";
    } else if (path === "/alternatives/claygent") {
      document.title = "Claygent alternative for row-by-row AI research | n3rf";
    } else {
      document.title = "AI data workflows for messy rows | n3rf";
    }
  }, [path]);

  if (path === "/legal") return <LegalPage />;
  if (path === "/alternatives/claygent") return <ClaygentAlternativePage />;
  return <LandingPage />;
}
