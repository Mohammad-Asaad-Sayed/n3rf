import * as Collapsible from "@radix-ui/react-collapsible";
import {
  ArrowRight,
  ArrowUpRight,
  Activity,
  AlertTriangle,
  AtSign,
  Braces,
  Clock3,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Copy,
  Database,
  Download,
  FileText,
  FileJson2,
  GripVertical,
  House,
  Layers3,
  LoaderCircle,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Play,
  Redo2,
  Undo2,
  Save,
  Search,
  Settings2,
  Eye,
  Trash2,
  Upload,
  Workflow,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import {
  type ChangeEvent,
  type CSSProperties,
  type DragEvent as ReactDragEvent,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  Fragment,
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Button } from "./components/ui/button";
import { Input, Select, Textarea } from "./components/ui/fields";
import { NodeLibrary } from "./components/editor/NodeLibrary";
import { DataGrid, type GridCellSelection } from "./components/grid/DataGrid";
import { CellDetails } from "./components/grid/CellDetails";
import { Tooltip, TooltipProvider } from "./components/ui/tooltip";
import {
  apiFetch,
  bareFieldName,
  buildCondition,
  CODE_PRESETS,
  CONDITION_OPERATORS,
  defaultParams,
  detectSmartColumns,
  ENV_SUGGESTIONS,
  fallbackCatalog,
  fallbackExpressionFields,
  FIELD_NAME_KEYS,
  formatValue,
  groupIcons,
  groupTokens,
  humanizeFieldLabel,
  humanizeOption,
  isVisible,
  MODEL_SUGGESTIONS,
  normalizeHeaders,
  parseCondition,
  partitionParams,
  plainHint,
  plainParamLabel,
  previewWithRow,
  PROVIDER_PRESETS,
  readPaneWidths,
  SCHEMA_PRESETS,
  schemaPresetLabel,
  summaryLabel,
  summaryParams,
  templatesFor,
  type NodeSpec,
  type PaneWidths,
  type ParamSpec,
  type RunNode,
  type RunResult,
  type SavedWorkflow,
  type SimulatedRow,
  type WorkflowEdge,
  type WorkflowNode,
} from "./lib/workflow";

type ModelProfile = {
  id: string;
  name: string;
  base_url: string;
  model: string;
  api_key_env: string;
  updated_at: string;
};

export function App() {
  const [url, setUrl] = useState(() => ({ pathname: window.location.pathname, hash: window.location.hash }));

  useEffect(() => {
    const updateUrl = () => setUrl({ pathname: window.location.pathname, hash: window.location.hash });
    window.addEventListener("popstate", updateUrl);
    window.addEventListener("hashchange", updateUrl);
    return () => {
      window.removeEventListener("popstate", updateUrl);
      window.removeEventListener("hashchange", updateUrl);
    };
  }, []);

  const { pathname, hash } = url;

  useEffect(() => {
    document.title = pathname === "/app/models"
      ? "Model settings | n3rf"
      : pathname === "/app/workflows"
        ? "Saved workflows | n3rf"
        : "n3rf — self-hosted workflow editor";
  }, [pathname]);

  // Legacy hash URLs (#/home, #/editor, #/models, #/landing...) -> clean paths.
  useEffect(() => {
    if (pathname !== "/") return;
    if (hash === "#/home" || hash === "#/landingpage") {
      window.history.replaceState(null, "", "/app");
      setUrl({ pathname: "/app", hash: "" });
    } else if (hash.startsWith("#/editor")) {
      const rest = hash.slice("#/editor".length);
      const target = rest ? `/app/editor?workflow=${encodeURIComponent(rest.slice(1))}` : "/app/editor";
      window.history.replaceState(null, "", target);
      setUrl({ pathname: "/app/editor", hash: "" });
    } else if (hash === "#/models") {
      window.history.replaceState(null, "", "/app/models");
      setUrl({ pathname: "/app/models", hash: "" });
    }
  }, [pathname, hash]);

  const openEditor = (id?: string) => {
    window.location.href = id
      ? `/app/editor?workflow=${encodeURIComponent(id)}`
      : "/app/editor";
  };
  const openModels = () => { window.location.href = "/app/models"; };

  // Bricks-style /app: upload gate first, canvas in place after upload (no editor route hop).
  // /app/editor* stays as a direct-canvas alias for bookmarks.
  if (pathname.startsWith("/app/editor")) {
    return <WorkflowEditor key={pathname + hash + window.location.search} />;
  }
  if (pathname === "/" || pathname === "/app" || pathname === "/app/") {
    return <AppPage />;
  }
  if (pathname === "/app/models") return <ModelSettingsPage />;
  if (pathname === "/app/workflows") {
    return (
      <HomePage
        onCreate={() => openEditor()}
        onOpen={(id) => openEditor(id)}
        onModels={() => openModels()}
      />
    );
  }
  return <AppPage />;
}

function HomePage({
  onCreate,
  onOpen,
  onModels,
}: {
  onCreate: () => void;
  onOpen: (id: string) => void;
  onModels: () => void;
}) {
  const [workflows, setWorkflows] = useState<Array<{
    id: string;
    name: string;
    nodes?: WorkflowNode[];
    updated_at?: string;
  }>>([]);
  const [nodeCount, setNodeCount] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deletingWorkflow, setDeletingWorkflow] = useState<string | null>(null);
  const [workflowToDelete, setWorkflowToDelete] = useState<{ id: string; name: string } | null>(
    null,
  );
  const deleteDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = deleteDialogRef.current;
    if (!dialog) return;
    if (workflowToDelete && !dialog.open) {
      dialog.showModal();
    } else if (!workflowToDelete && dialog.open) {
      dialog.close();
    }
  }, [workflowToDelete]);

  useEffect(() => {
    let active = true;
    async function loadHome() {
      try {
        const [workflowResponse, catalogResponse] = await Promise.all([
          apiFetch("/workflows"),
          apiFetch("/nodes"),
        ]);
        if (!workflowResponse.ok || !catalogResponse.ok) {
          throw new Error("The workflow library could not be loaded from the backend.");
        }
        const [loadedWorkflows, catalog] = await Promise.all([
          workflowResponse.json(),
          catalogResponse.json(),
        ]);
        if (!active) return;
        setWorkflows(loadedWorkflows);
        setNodeCount(catalog.length);
        setError("");
      } catch (loadError) {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "The home page could not be loaded.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadHome();
    return () => { active = false; };
  }, []);

  const query = search.trim().toLocaleLowerCase();
  const visibleWorkflows = workflows.filter((workflow) =>
    workflow.name.toLocaleLowerCase().includes(query),
  );
  const totalNodes = workflows.reduce((total, workflow) => total + (workflow.nodes?.length ?? 0), 0);

  async function deleteWorkflow() {
    if (!workflowToDelete) return;
    const workflow = workflowToDelete;
    setDeletingWorkflow(workflow.id);
    setDeleteError("");
    try {
      const response = await apiFetch(`/workflows/${encodeURIComponent(workflow.id)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("Workflow could not be deleted. Please try again.");
      }
      setWorkflows((current) => current.filter((item) => item.id !== workflow.id));
      setWorkflowToDelete(null);
    } catch (deleteFailure) {
      setDeleteError(
        deleteFailure instanceof Error ? deleteFailure.message : "Workflow could not be deleted.",
      );
    } finally {
      setDeletingWorkflow(null);
    }
  }

  return (
    <main className="home-shell">
      <header className="home-topbar">
        <a className="home-brand" href="/app" aria-label="n3rf home">
          <span className="home-brand-mark"><Workflow /></span>
          <span><strong>n3rf</strong><small>workflow systems</small></span>
        </a>
        <div className="home-status"><span />LOCAL WORKSPACE</div>
        <Button variant="ghost" onClick={onModels}><Settings2 /> Models</Button>
        <a
          className="ui-button ui-button-md ui-button-ghost"
          href="https://github.com/Mohammad-Asaad-Sayed/n3rf/blob/main/docs/self-hosting.md"
          target="_blank"
          rel="noreferrer"
        >
          <FileText /> Self-hosting guide
        </a>
        <Button variant="primary" onClick={onCreate}><Plus /> New workflow</Button>
      </header>

      <div className="home-content">
        <section className="home-hero">
          <div className="hero-copy">
            <span className="home-eyebrow"><span /> YOUR WORKSPACE</span>
            <h1>Make the messy<br /><em>make sense.</em></h1>
            <p>Build clear, visual workflows that turn unstructured input into useful data.</p>
            <div className="hero-actions">
              <Button variant="primary" onClick={onCreate}><Plus /> Create a workflow</Button>
              <span className="hero-hint">Your data stays on this machine.</span>
            </div>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="art-orbit orbit-one" />
            <div className="art-orbit orbit-two" />
            <div className="art-node art-input"><FileJson2 /></div>
            <div className="art-node art-transform"><Layers3 /></div>
            <div className="art-node art-output"><Braces /></div>
            <div className="art-link link-one" /><div className="art-link link-two" />
            <span className="art-signal signal-one" /><span className="art-signal signal-two" />
            <div className="art-caption">INPUT <ArrowRight /> TRANSFORM <ArrowRight /> OUTPUT</div>
          </div>
          <div className="hero-index">N° 01 <span>LOCAL-FIRST BUILDER</span></div>
        </section>

        <section className="home-overview" aria-label="Workspace overview">
          <div className="overview-label"><span className="home-eyebrow">AT A GLANCE</span><span className="overview-line" /></div>
          <div className="overview-stat"><strong>{loading ? "—" : String(workflows.length).padStart(2, "0")}</strong><span>SAVED WORKFLOWS</span></div>
          <div className="overview-stat"><strong>{loading ? "—" : String(totalNodes).padStart(2, "0")}</strong><span>NODES IN YOUR FLOWS</span></div>
          <div className="overview-stat"><strong>{loading || nodeCount === null ? "—" : String(nodeCount).padStart(2, "0")}</strong><span>AVAILABLE NODES</span></div>
          <div className="overview-storage"><Database /><span>SQLite<br /><small>LOCAL STORAGE</small></span></div>
        </section>

        <section className="home-library">
          <div className="library-heading">
            <div><span className="home-eyebrow">YOUR PROJECTS</span><h2>Workflows <span>{String(workflows.length).padStart(2, "0")}</span></h2></div>
            <label className="workflow-search"><Search /><input aria-label="Search workflows" placeholder="Search workflows" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          </div>

          {error ? (
            <div className="home-message" role="alert"><strong>Workspace unavailable</strong><span>{error}</span><small>Start FastAPI to browse and save workflows.</small></div>
          ) : loading ? (
            <div className="home-message"><span>Loading your workspace…</span></div>
          ) : visibleWorkflows.length ? (
            <div className="workflow-library">
              {deleteError && <p className="workflow-delete-error" role="alert">{deleteError}</p>}
              <div className="workflow-grid">
                {visibleWorkflows.map((workflow, index) => (
                  <article className="workflow-tile" key={workflow.id}>
                    <button className="workflow-tile-open-button" onClick={() => onOpen(workflow.id)}>
                      <span className="workflow-tile-top"><span className="workflow-tile-icon"><Workflow /></span><span className="workflow-tile-number">WF / {String(index + 1).padStart(2, "0")}</span><ArrowUpRight className="workflow-tile-open" /></span>
                      <strong className="workflow-tile-name">{workflow.name || "Untitled workflow"}</strong>
                      <span className="workflow-tile-meta"><span><Layers3 />{workflow.nodes?.length ?? 0} {(workflow.nodes?.length ?? 0) === 1 ? "node" : "nodes"}</span><span><Clock3 />{workflow.updated_at ? new Date(`${workflow.updated_at}${workflow.updated_at.endsWith("Z") ? "" : "Z"}`).toLocaleDateString() : "Recently"}</span></span>
                    </button>
                    <button
                      className="workflow-delete-button"
                      type="button"
                      aria-label={`Delete ${workflow.name || "Untitled workflow"}`}
                      title="Delete workflow"
                      disabled={deletingWorkflow !== null}
                      onClick={() => {
                        setDeleteError("");
                        setWorkflowToDelete({
                          id: workflow.id,
                          name: workflow.name || "Untitled workflow",
                        });
                      }}
                    >
                      <Trash2 />
                    </button>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="home-empty">
              <div className="empty-mark"><Workflow /></div>
              <div><span className="home-eyebrow">{query ? "NO MATCHES" : "A CLEAN CANVAS"}</span><h3>{query ? "Nothing found" : "Your first workflow starts here."}</h3><p>{query ? "Try another name or clear your search." : "Connect a source, shape your data, and see every row move through the pipeline."}</p></div>
              {!query && <Button onClick={onCreate}><Plus /> Build your first workflow</Button>}
            </div>
          )}
        </section>

        <footer className="home-footer"><span>n3rf <b>·</b> A LOCAL-FIRST WORKFLOW BUILDER</span><span>BUILT FOR ROWS, NOT NOISE</span></footer>
      </div>
      <dialog
        ref={deleteDialogRef}
        className="delete-confirmation"
        aria-labelledby="delete-confirmation-title"
        aria-describedby="delete-confirmation-description"
        onCancel={() => setWorkflowToDelete(null)}
        onClick={(event) => {
          if (event.target === event.currentTarget && deletingWorkflow === null) {
            setWorkflowToDelete(null);
          }
        }}
      >
        <div className="delete-confirmation-mark"><Trash2 /></div>
        <span className="home-eyebrow">DELETE WORKFLOW</span>
        <h2 id="delete-confirmation-title">Are you sure?</h2>
        <p id="delete-confirmation-description">
          Delete <strong>{workflowToDelete?.name}</strong>? This cannot be undone.
        </p>
        {deleteError && <p className="workflow-delete-error" role="alert">{deleteError}</p>}
        <div className="delete-confirmation-actions">
          <Button
            type="button"
            variant="ghost"
            disabled={deletingWorkflow !== null}
            onClick={() => setWorkflowToDelete(null)}
            autoFocus
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="ui-button-danger"
            disabled={deletingWorkflow !== null}
            onClick={() => void deleteWorkflow()}
          >
            {deletingWorkflow !== null ? "Deleting…" : "Delete workflow"}
          </Button>
        </div>
      </dialog>
    </main>
  );
}

function ModelSettingsPage() {
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [name, setName] = useState("OpenAI");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o-mini");
  const [apiKeyEnv, setApiKeyEnv] = useState("OPENAI_API_KEY");
  // Ephemeral BYOK: pasting a key here tests the connection with that key
  // for one request only. It is never sent to the save endpoint.
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiFetch("/models")
      .then(async (response) => {
        if (!response.ok) throw new Error("Saved model profiles could not be loaded.");
        return response.json() as Promise<ModelProfile[]>;
      })
      .then((loaded) => { if (active) setProfiles(loaded); })
      .catch((loadError: unknown) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Could not load profiles.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function chooseProfile(id: string) {
    setProfileId(id);
    setApiKey("");
    const profile = profiles.find((item) => item.id === id);
    if (!profile) {
      setName("OpenAI");
      setBaseUrl("https://api.openai.com/v1");
      setModel("gpt-4o-mini");
      setApiKeyEnv("OPENAI_API_KEY");
      return;
    }
    setName(profile.name);
    setBaseUrl(profile.base_url);
    setModel(profile.model);
    setApiKeyEnv(profile.api_key_env);
    setMessage("");
    setError("");
  }

  function requestBody(includeEphemeralKey = false) {
    return {
      ...(profileId ? { id: profileId } : {}),
      name,
      base_url: baseUrl,
      model,
      api_key_env: apiKeyEnv,
      ...(includeEphemeralKey && apiKey ? { api_key: apiKey } : {}),
    };
  }

  async function testProfile() {
    setTesting(true);
    setMessage("");
    setError("");
    try {
      const response = await apiFetch("/models/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody(true)),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Connection test failed.");
      const listed = payload.models.length ? ` ${payload.models.slice(0, 5).join(", ")}` : "";
      setMessage(`${payload.message}${payload.model_available ? "" : " Selected model was not listed."}${listed}`);
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Connection test failed.");
    } finally {
      setTesting(false);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const response = await apiFetch("/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody()),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Profile could not be saved.");
      setProfileId(payload.id);
      setProfiles((current) => [...current.filter((item) => item.id !== payload.id), payload]);
      setMessage("Model profile saved. API secrets remain in your environment.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Profile could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteProfile() {
    if (!profileId) return;
    try {
      const response = await apiFetch(`/models/${profileId}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Model profile could not be deleted.");
      setProfiles((current) => current.filter((item) => item.id !== profileId));
      chooseProfile("");
      setMessage("Model profile deleted.");
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Model profile could not be deleted.");
    }
  }

  return (
    <main className="home-shell settings-shell">
      <header className="home-topbar">
        <a className="home-brand" href="/app" aria-label="Back to workspace"><span className="home-brand-mark"><Workflow /></span><span><strong>n3rf</strong><small>model settings</small></span></a>
        <div className="home-status"><span />LOCAL WORKSPACE</div>
        <Button variant="ghost" onClick={() => { window.location.href = "/app"; }}><ArrowRight /> Back to workspace</Button>
      </header>
      <div className="settings-content">
        <div className="settings-intro">
          <span className="home-eyebrow"><span /> PROVIDER CONNECTIONS</span>
          <h1>Models, on <em>your terms.</em></h1>
          <p>Connect an OpenAI-compatible provider. Use an environment variable for the API key — or paste a key to test it once — n3rf never stores the secret.</p>
        </div>
        <div className="settings-layout">
          <aside className="profile-list">
            <div className="profile-list-heading"><span className="home-eyebrow">SAVED PROFILES</span><Button size="sm" onClick={() => chooseProfile("")}><Plus /> New</Button></div>
            {loading ? <p>Loading profiles…</p> : profiles.length ? profiles.map((profile) => (
              <button className={`profile-list-item ${profile.id === profileId ? "active" : ""}`} key={profile.id} onClick={() => chooseProfile(profile.id)}>
                <span className="profile-provider-mark"><Database /></span><span><strong>{profile.name}</strong><small>{profile.model}</small></span><ArrowUpRight />
              </button>
            )) : <p className="profile-empty">No saved providers yet.</p>}
          </aside>
          <form className="profile-form" onSubmit={(event) => void saveProfile(event)}>
            <div className="profile-form-heading"><span className="profile-form-icon"><Settings2 /></span><div><span className="home-eyebrow">OPENAI-COMPATIBLE</span><h2>{profileId ? "Edit provider" : "Configure a provider"}</h2></div></div>
            <div className="profile-fields">
              <label className="form-field"><span className="field-label">Profile name</span><Input required maxLength={80} value={name} onChange={(event) => setName(event.target.value)} placeholder="My local model" /></label>
              <label className="form-field"><span className="field-label">API base URL</span><Input required type="url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="http://localhost:11434/v1" /></label>
              <label className="form-field"><span className="field-label">Chat model</span><Input required value={model} onChange={(event) => setModel(event.target.value)} placeholder="model-name" /></label>
              <label className="form-field"><span className="field-label">API key environment variable <span>NEVER STORED</span></span><Input value={apiKeyEnv} onChange={(event) => setApiKeyEnv(event.target.value)} placeholder="OPENAI_API_KEY (blank for local providers)" /><small className="field-hint">Set this variable in the shell that starts FastAPI. Leave blank for providers that do not require a key. Or paste a key below to test once.</small></label>
              <label className="form-field"><span className="field-label">API key (paste to test — never saved) <span>RUN ONLY</span></span><Input type="password" autoComplete="off" spellCheck={false} value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Paste a key to test the connection once" /><small className="field-hint">Used for the connection test only. Never saved in SQLite or localStorage.</small></label>
            </div>
            {message && <p className="profile-feedback success" role="status">{message}</p>}
            {error && <p className="profile-feedback error" role="alert">{error}</p>}
            <div className="profile-actions">
              {profileId && <Button type="button" variant="ghost" onClick={() => void deleteProfile()}>Delete</Button>}
              <Button type="button" onClick={() => void testProfile()} disabled={testing}>{testing ? "Testing…" : "Test connection"}</Button>
              <Button type="submit" variant="primary" disabled={saving}>{saving ? "Saving…" : "Save profile"}</Button>
            </div>
            <div className="profile-security"><span className="security-mark">✓</span><span><strong>Secret-safe by design</strong><small>Only the environment variable name is saved in SQLite. Connection tests call the provider’s models endpoint and do not send a prompt. Pasted test keys are sent once and never saved.</small></span></div>
          </form>
        </div>
      </div>
    </main>
  );
}

function AppPage() {
  const [started, setStarted] = useState(false);
  const [localCsv, setLocalCsv] = useState<{ name: string; text: string } | null>(null);
  const [preview, setPreview] = useState<{ name: string; text: string; columns: string[]; totalRows: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  async function importFile(file: File | undefined) {
    setError("");
    if (!file) return;
    const name = file.name.toLocaleLowerCase();
    const isCsv = name.endsWith(".csv") || name.endsWith(".tsv") || file.type === "text/csv";
    const isXlsx = name.endsWith(".xlsx");
    if (!isCsv && !isXlsx) {
      setError("Choose a CSV or Excel (.xlsx) file to start.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("This local import is limited to 10 MB. Split the file and try again.");
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
        if (!csvText || !csvText.trim()) {
          setError("That spreadsheet has no rows to read. Export the full sheet and try again.");
          return;
        }
        setLocalCsv({ name: file.name.replace(/\.xlsx$/i, ""), text: csvText });
        setPreview({
          name: file.name.replace(/\.xlsx$/i, ""),
          text: csvText,
          columns: (payload.columns as string[]) ?? [],
          totalRows: (payload.totalRows as number) ?? 0,
        });
        setStarted(true);
      } catch (error) {
        setError(error instanceof Error ? error.message : "The spreadsheet could not be read.");
      }
      return;
    }
    try {
      const text = await file.text();
      if (!text.trim()) {
        setError("That file has no rows to read. Export the full CSV — not just a preview.");
        return;
      }
      setLocalCsv({ name: file.name.replace(/\.(csv|tsv)$/i, ""), text });
      const firstLine = text.slice(0, 4000).split(/\r?\n/, 1)[0] ?? "";
      const columns = normalizeHeaders(firstLine.split(name.endsWith(".tsv") ? "\t" : ",").map((c) => c.trim()).filter(Boolean));
      setPreview({ name: file.name.replace(/\.(csv|tsv)$/i, ""), text, columns, totalRows: Math.max(0, text.trim().split(/\r?\n/).length - 1) });
      setStarted(true);
    } catch {
      setError("The file could not be read. Check it and try again.");
    }
  }

  function startWithSample() {
    const text = "company,website\nAcme,https://acme.com\nNorthstar,https://northstar.example\nBluebird,https://bluebird.example";
    setLocalCsv({ name: "sample-companies", text });
    setPreview({ name: "sample-companies", text, columns: ["company", "website"], totalRows: 3 });
    setStarted(true);
  }

  if (started) {
    const csvImport = localCsv ?? (preview ? { name: preview.name, text: preview.text } : null);
    return <WorkflowEditor csvImport={csvImport} onCsvImportConsumed={() => setLocalCsv(null)} />;
  }

  return (
    <main className="home-shell">
      <header className="home-topbar">
        <a className="home-brand" href="/" aria-label="n3rf home">
          <span className="home-brand-mark"><Workflow /></span>
          <span><strong>n3rf</strong><small>workflow systems</small></span>
        </a>
        <div className="home-status"><span />LOCAL WORKSPACE</div>
        <Button variant="ghost" onClick={() => { window.location.href = "/app/workflows"; }}><Workflow /> Workflows</Button>
        <Button variant="ghost" onClick={() => { window.location.href = "/app/models"; }}><Settings2 /> Models</Button>
      </header>
      <div className="app-gate">
        <p className="home-eyebrow"><span /> {"// DATA ENRICHMENT — NO CLOUD REQUIRED"}</p>
        <h1>Enrich data on<br />your own <em>machine.</em></h1>
        <p className="app-gate-sub">
          Upload a CSV, Excel (.xlsx), spreadsheet paste, or text list and build a workflow for it.
          Headers become columns instantly.
        </p>
        <button
          type="button"
          className={`app-dropzone${dragging ? " is-dragging" : ""}`}
          onClick={() => fileInput.current?.click()}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            void importFile(event.dataTransfer.files[0]);
          }}
        >
          <span className="app-dropzone-icon"><Upload /></span>
          <strong>{dragging ? "Drop it. Build the grid." : "Drop your CSV"}</strong>
          <small>{dragging ? "Release to load your data" : ".csv · .tsv · .xlsx — headers become columns"}</small>
          <span className="app-dropzone-cta"><Upload /> Browse files</span>
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".csv,.tsv,.xlsx,text/csv"
          aria-label="Choose a CSV file"
          className="sr-only"
          onChange={(event) => {
            void importFile(event.currentTarget.files?.[0]);
            event.currentTarget.value = "";
          }}
        />
        {error && <p className="profile-feedback error" role="alert">{error}</p>}
        <div className="app-gate-alt">
          <button type="button" className="model-settings-link" onClick={startWithSample}>
            No file handy? Try 3-row sample data
          </button>
          <span aria-hidden="true">·</span>
          <button type="button" className="model-settings-link" onClick={() => setStarted(true)}>
            Start with a blank canvas
          </button>
        </div>
        <div className="app-gate-steps">
          <div><span>01</span><strong>Upload CSV</strong><p>Drag in your list. Headers become columns instantly.</p></div>
          <div><span>02</span><strong>Program columns</strong><p>Nodes enrich each column — click a column to configure it.</p></div>
          <div><span>03</span><strong>Execute &amp; export</strong><p>Watch cells fill in real time. Export when the grid is solid.</p></div>
        </div>
      </div>
    </main>
  );
}

// Ephemeral BYOK: a pasted api_key is per-request only. It lives in React
// state (sent with /run) but must never reach localStorage or the save API.
function stripEphemeralKeys(nodes: WorkflowNode[]): WorkflowNode[] {
  return nodes.map((node) => {
    if (!node.params || !("api_key" in node.params)) return node;
    const { api_key: _stripped, ...rest } = node.params as Record<string, unknown>;
    return { ...node, params: rest };
  });
}

function sampleRowsFromNode(node: WorkflowNode): Record<string, unknown>[] {
  if (node.type === "manual_json" && Array.isArray(node.params.data)) {
    return node.params.data.filter((r): r is Record<string, unknown> => r && typeof r === "object");
  }
  if (node.type === "csv_file") {
    let text = typeof node.params.text === "string" ? node.params.text : "";
    if (!text && typeof node.params.file === "string" && node.params.file) {
      try { text = atob(node.params.file); } catch { /* ignore */ }
    }
    const firstLine = text.split("\n")[0] || "";
    const headers = firstLine.split(",").map((h) => h.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
    if (headers.length) {
      return [Object.fromEntries(headers.map((h) => [h, ""]))];
    }
  }
  if (node.type === "field_builder" && Array.isArray(node.params.fields)) {
    const obj: Record<string, unknown> = {};
    for (const f of node.params.fields as { name?: string; value?: unknown }[]) {
      if (f.name) obj[f.name] = f.value ?? "";
    }
    return [obj];
  }
  if (node.type === "set_fields" && Array.isArray(node.params.fields)) {
    const obj: Record<string, unknown> = {};
    for (const f of node.params.fields as { name?: string; value?: unknown }[]) {
      if (f.name) obj[f.name] = f.value ?? "";
    }
    return [obj];
  }
  if (node.type === "text_lines") {
    return [{ value: "" }];
  }
  if (node.type === "example_dataset") {
    const ds = node.params.dataset;
    if (ds === "people") return [{ name: "", title: "", email: "" }];
    if (ds === "products") return [{ product: "", category: "", price: 0 }];
    return [{ company: "", website: "", notes: "" }];
  }
  if (node.type === "file_upload" && typeof node.params.content === "string" && node.params.content) {
    try {
      const decoded = atob(node.params.content);
      const trimmed = decoded.trim();
      if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
        const parsed = JSON.parse(trimmed);
        return Array.isArray(parsed) ? parsed : [parsed];
      }
      const firstLine = decoded.split("\n")[0] || "";
      const headers = firstLine.split(",").map((h) => h.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
      if (headers.length) {
        return [Object.fromEntries(headers.map((h) => [h, ""]))];
      }
    } catch {
      // ignore
    }
  }
  return [];
}

function WorkflowEditor({
  csvImport = null,
  onCsvImportConsumed,
}: {
  csvImport?: { name: string; text: string } | null;
  onCsvImportConsumed?: () => void;
}) {
  const workflowPath = window.location.pathname.startsWith("/app/editor/")
    ? window.location.pathname.slice("/app/editor/".length)
    : "";
  const workflowQuery = new URLSearchParams(window.location.search).get("workflow") ?? "";
  const workflowHash = window.location.hash.startsWith("#/editor/")
    ? window.location.hash.slice("#/editor/".length)
    : "";
  const rawWorkflowId = workflowPath || workflowQuery || workflowHash;
  const initialWorkflowId = rawWorkflowId ? decodeURIComponent(rawWorkflowId) : null;
  const [catalog, setCatalog] = useState<NodeSpec[]>([]);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [connectionDrag, setConnectionDrag] = useState<{
    sourceId: string;
    x: number;
    y: number;
    targetId: string | null;
    targetInput: number;
  } | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [runningNodeId, setRunningNodeId] = useState<string | null>(null);
  const [resultTab, setResultTab] = useState<"output" | "steps" | "diagnostics">("output");
  const [outputNotice, setOutputNotice] = useState("");
  const [apiConnected, setApiConnected] = useState(true);
  const [workflowName, setWorkflowName] = useState("Untitled workflow");
  const [workflows, setWorkflows] = useState<SavedWorkflow[]>([]);
  const [modelProfiles, setModelProfiles] = useState<ModelProfile[]>([]);
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [search, setSearch] = useState("");
  const [widths, setWidths] = useState<PaneWidths>(readPaneWidths);
  const [paletteOpen, setPaletteOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [resultsOpen, setResultsOpen] = useState(true);
  const [zoom, setZoom] = useState(0.85);
  const [pan, setPan] = useState({ x: 80, y: 60 });
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<"node" | "cell" | "column">("node");
  const [selectedCell, setSelectedCell] = useState<GridCellSelection | null>(null);
  const [selectedColumn, setSelectedColumn] = useState("");
  const [gridNodeId, setGridNodeId] = useState<string | null>(null);
  const [columnDraftType, setColumnDraftType] = useState("set_fields");
  const [columnDraftParams, setColumnDraftParams] = useState<Record<string, unknown>>({});
  const [scopeColumn, setScopeColumn] = useState<string | null>(null);
  const scopeDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = scopeDialogRef.current;
    if (!dialog) return;
    if (scopeColumn && !dialog.open) {
      dialog.showModal();
    } else if (!scopeColumn && dialog.open) {
      dialog.close();
    }
  }, [scopeColumn]);

  const [gridFirstN, setGridFirstN] = useState<number | null>(null);
  const [gridEmptyColumn, setGridEmptyColumn] = useState<string | null>(null);
  // Canvas undo/redo: nodes+edges only (structural). Param text edits keep
  // native input undo — we never re-render the inspector on keystroke.
  const [past, setPast] = useState<Array<{ nodes: WorkflowNode[]; edges: WorkflowEdge[] }>>([]);
  const [future, setFuture] = useState<Array<{ nodes: WorkflowNode[]; edges: WorkflowEdge[] }>>([]);
  const snapshot = (ns: WorkflowNode[], es: WorkflowEdge[]) =>
    ({ nodes: structuredClone(ns), edges: structuredClone(es) }) as {
      nodes: WorkflowNode[];
      edges: WorkflowEdge[];
    };
  const pushHistory = () => {
    setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
    setFuture([]);
  };
  const undo = () => {
    setPast((current) => {
      if (!current.length) return current;
      const prev = current[current.length - 1];
      setFuture((f) => [...f, snapshot(nodes, edges)]);
      setNodes(structuredClone(prev.nodes));
      setEdges(structuredClone(prev.edges));
      setSelectedId(null);
      setResult(null);
      return current.slice(0, -1);
    });
  };
  const redo = () => {
    setFuture((current) => {
      if (!current.length) return current;
      const next = current[current.length - 1];
      setPast((p) => [...p, snapshot(nodes, edges)]);
      setNodes(structuredClone(next.nodes));
      setEdges(structuredClone(next.edges));
      setSelectedId(null);
      setResult(null);
      return current.slice(0, -1);
    });
  };
  const canvasRef = useRef<HTMLDivElement>(null);

  const specById = useMemo(() => new Map(catalog.map((spec) => [spec.id, spec])), [catalog]);
  const selected = nodes.find((node) => node.id === selectedId) ?? null;
  const selectedSpec = selected ? specById.get(selected.type) ?? null : null;
  const selectedRunNode = result?.nodes.find((item) => item.id === selected?.id);

  // Column pickers + drag/drop chips come from upstream rows, never blank:
  // after a run use real fields from ancestors, before that use examples.
  const expressionFields = useMemo(() => {
    const samples: unknown[][] = [];
    if (selectedId) {
      const seen = new Set<string>();
      const pending = [selectedId];
      while (pending.length) {
        const target = pending.pop();
        if (!target || seen.has(target)) continue;
        seen.add(target);
        if (result) {
          const runNode = result.nodes.find((item) => item.id === target);
          if (runNode?.sample?.length) samples.push(runNode.sample);
          for (const group of runNode?.input_samples ?? []) {
            if (group.length) samples.push(group);
          }
        }
        const graphNode = nodes.find((item) => item.id === target);
        if (graphNode) {
          const staticSamples = sampleRowsFromNode(graphNode);
          if (staticSamples.length) samples.push(staticSamples);
        }
        for (const edge of edges) {
          if (edge.target === target) pending.push(edge.source);
        }
      }
      if (!samples.length && result?.output?.length) samples.push(result.output);
    }
    if (!samples.length) {
      for (const node of nodes) {
        const s = sampleRowsFromNode(node);
        if (s.length) samples.push(s);
      }
    }
    const discovered = expressionFieldsFromSamples(samples);
    const merged = [...discovered, ...fallbackExpressionFields().filter((field) => !discovered.some((f) => f.label === field.label))];
    const smart = new Set(detectSmartColumns(merged.map((field) => field.label)));
    return [...merged].sort((a, b) => Number(smart.has(b.label)) - Number(smart.has(a.label)));
  }, [result, selectedId, edges, nodes]);

  const expressionPreviewRow = useMemo<Record<string, unknown> | null>(() => {
    const firstInput = selectedRunNode?.input_samples?.flat().find(
      (row): row is Record<string, unknown> =>
        row !== null && typeof row === "object" && !Array.isArray(row),
    );
    if (firstInput) return firstInput;
    const firstOutput = result?.output.find(
      (row): row is Record<string, unknown> =>
        row !== null && typeof row === "object" && !Array.isArray(row),
    );
    return firstOutput ?? null;
  }, [selectedRunNode, result]);

  const programmedByColumn = useMemo(() => {
    const map: Record<string, { nodeId: string; nodeName: string }> = {};
    if (!result) return map;
    // Columns produced by a node = keys in its sample that were not in its inputs.
    for (const item of result.nodes) {
      const inputs = (item.input_samples ?? []).flat();
      const inputKeys = new Set(
        inputs.flatMap((row) =>
          row && typeof row === "object" && !Array.isArray(row)
            ? Object.keys(row as Record<string, unknown>)
            : [],
        ),
      );
      for (const row of item.sample ?? []) {
        if (row && typeof row === "object" && !Array.isArray(row)) {
          for (const key of Object.keys(row as Record<string, unknown>)) {
            if (!inputKeys.has(key) && !map[key]) {
              map[key] = { nodeId: item.id, nodeName: item.name || item.id };
            }
          }
        }
      }
    }
    return map;
  }, [result]);

  const programmed: Record<string, string> = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(programmedByColumn).map(([col, info]) => [col, info.nodeName]),
      ),
    [programmedByColumn],
  );

  const gridRows: unknown[] = useMemo(() => {
    if (!result) return [];
    if (!gridNodeId) return result.output;
    const found = result.nodes.find((item) => item.id === gridNodeId);
    return found?.sample ?? [];
  }, [result, gridNodeId]);

  const gridPartial = gridNodeId != null;

  const gridFilteredRows: unknown[] = useMemo(() => {
    let rows = gridRows;
    if (gridEmptyColumn) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rows = rows.filter((row) => {
        const rec = (row as Record<string, unknown>) ?? {};
        return rec[gridEmptyColumn] == null || rec[gridEmptyColumn] === "";
      });
    }
    if (gridFirstN != null) rows = rows.slice(0, gridFirstN);
    return rows;
  }, [gridRows, gridEmptyColumn, gridFirstN]);

  const executingColumn =
    runningNodeId && programmedByColumn
      ? Object.entries(programmedByColumn).find(([, info]) => info.nodeId === runningNodeId)?.[0] ?? null
      : null;

  const selectedProducingNode = selectedColumn
    ? programmedByColumn[selectedColumn]
    : undefined;

  const columnDraftSpec = specById.get(columnDraftType) ?? null;

  function openColumnEditor(column: string) {
    setSelectedColumn(column);
    setInspectorTab("column");
    setInspectorOpen(true);
    const spec = columnDraftSpec;
    if (spec && !Object.keys(columnDraftParams).length) {
      setColumnDraftParams(defaultParams(spec));
    }
  }

  function createColumnNode() {
    const spec = columnDraftSpec;
    if (!spec) return;
    const id = `${spec.id}_${crypto.randomUUID().slice(0, 8)}`;
    // When the user typed a column name for a set_fields node, seed the field
    // name so the new column is created; the value stays user-editable.
    let params: Record<string, unknown> = defaultParams(spec) as Record<string, unknown>;
    if (spec.id === "set_fields" && selectedColumn) {
      params = {
        ...params,
        fields: [{ name: selectedColumn, value: "" }],
      };
    }
    // Include any draft params the user already tuned in the column panel.
    if (Object.keys(columnDraftParams).length) {
      params = { ...params, ...columnDraftParams };
    }
    const sourceId = selectedId ?? nodes[nodes.length - 1]?.id ?? null;
    const baseX = sourceId
      ? (nodes.find((node) => node.id === sourceId)?.position.x ?? 180) + 280
      : 180;
    const baseY = sourceId
      ? (nodes.find((node) => node.id === sourceId)?.position.y ?? 150)
      : 150;
    pushHistory();
    setNodes((current) => [
      ...current,
      { id, type: spec.id, params, position: { x: baseX, y: baseY } },
    ]);
    if (sourceId) {
      setEdges((current) => [
        ...current.filter((edge) => !(edge.source === sourceId && edge.target === id)),
        { source: sourceId, target: id, target_input: 0 },
      ]);
    }
    setSelectedId(id);
    setInspectorTab("node");
    setInspectorOpen(true);
    setErrorMessage("");
  }

  function runColumn(column: string) {
    const info = programmedByColumn[column];
    if (info?.nodeId) {
      void runNode(info.nodeId);
    } else {
      openColumnEditor(column);
    }
  }

  const patchNode = useCallback((id: string, update: (node: WorkflowNode) => WorkflowNode) => {
    setNodes((current) => current.map((node) => (node.id === id ? update(node) : node)));
  }, []);

  const selectNode = useCallback((id: string) => {
    setSelectedId(id);
    setInspectorOpen(true);
  }, []);

  const addNode = useCallback(
    (type: string) => {
      const spec = specById.get(type);
      if (!spec) return;
      const id = `${type}_${crypto.randomUUID().slice(0, 8)}`;
      const x = Math.max(180, ...nodes.map((node) => node.position.x + 300));
      const y = nodes[0]?.position.y ?? 150;
      setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
      setFuture([]);
      setNodes((current) => [...current, { id, type, params: defaultParams(spec), position: { x, y } }]);
      setSelectedId(id);
      setInspectorOpen(true);
      setErrorMessage("");
    },
    [nodes, edges, specById],
  );

  const addEdge = useCallback(
    (source: string, target: string, input = 0) => {
      if (source === target) return;
      if (
        edges.some(
          (edge) =>
            edge.source === source &&
            edge.target === target &&
            Number(edge.target_input ?? 0) === input,
        )
      ) {
        return;
      }
      setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
      setFuture([]);
      setEdges((current) => [...current, { source, target, target_input: input }]);
    },
    [nodes, edges],
  );

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [catalogResponse, workflowResponse, modelResponse] = await Promise.all([
          apiFetch("/nodes"),
          apiFetch("/workflows"),
          apiFetch("/models"),
        ]);
        if (!catalogResponse.ok) throw new Error("Node catalog could not be loaded.");
        if (!workflowResponse.ok || !modelResponse.ok) {
          throw new Error("Workspace settings could not be loaded.");
        }
        const loadedCatalog = (await catalogResponse.json()) as NodeSpec[];
        if (!active) return;
        setCatalog(loadedCatalog);
        setApiConnected(true);
        if (!workflowResponse.ok) throw new Error("Saved workflows could not be loaded.");
        const [loadedWorkflows, loadedProfiles] = await Promise.all([
          workflowResponse.json(),
          modelResponse.json(),
        ]);
        setWorkflows(loadedWorkflows);
        setModelProfiles(loadedProfiles);
        if (initialWorkflowId) {
          const savedResponse = await apiFetch(`/workflows/${initialWorkflowId}`);
          const saved = await savedResponse.json();
          if (!savedResponse.ok) throw new Error(saved.detail || "Workflow could not be loaded.");
          if (!active) return;
          setWorkflowId(saved.id);
          setWorkflowName(saved.name);
          setNodes(saved.nodes);
          setEdges(saved.edges);
          setSelectedId(saved.nodes[0]?.id ?? null);
        }
      } catch {
        if (!active) return;
        setCatalog(fallbackCatalog);
        setApiConnected(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!catalog.length || nodes.length || initialWorkflowId) return;
    if (csvImport) {
      const spec = catalog.find((item) => item.id === "csv_file");
      if (!spec) {
        setErrorMessage("CSV import is unavailable because the CSV node is missing.");
        return;
      }
      const id = `csv_file_${crypto.randomUUID().slice(0, 8)}`;
      setWorkflowName(`Review CSV — ${csvImport.name}`);
      setNodes([
        {
          id,
          type: spec.id,
          params: { ...defaultParams(spec), text: csvImport.text },
          position: { x: 180, y: 160 },
        },
      ]);
      setSelectedId(id);
      onCsvImportConsumed?.();
      return;
    }
    // Draft backup (Bricks-style auto-save): restore unsaved canvas if present.
    // Primary store stays SQLite — this is only crash/reload recovery, no secrets
    // (workflow params hold env-var names, never the keys themselves).
    try {
      const raw = localStorage.getItem("n3rf-draft");
      if (raw) {
        const draft = JSON.parse(raw) as { name?: string; nodes?: WorkflowNode[]; edges?: WorkflowEdge[] };
        if (Array.isArray(draft.nodes) && draft.nodes.length) {
          setNodes(draft.nodes);
          setEdges(Array.isArray(draft.edges) ? draft.edges : []);
          setWorkflowName(draft.name || "Untitled workflow");
          setSelectedId(draft.nodes[0]?.id ?? null);
          return;
        }
      }
    } catch {
      /* ignore corrupt draft */
    }
    const spec = catalog.find((item) => item.id === "example_dataset") ?? catalog[0];
    if (!spec) return;
    const id = `${spec.id}_${crypto.randomUUID().slice(0, 8)}`;
    setNodes([
      {
        id,
        type: spec.id,
        params: defaultParams(spec),
        position: { x: 180, y: 160 },
      },
    ]);
    setSelectedId((current) => current ?? id);
  }, [catalog, nodes.length, initialWorkflowId, csvImport, onCsvImportConsumed]);

  useEffect(() => {
    if (!nodes.length) return;
    try {
      // Draft is crash recovery only — strip ephemeral pasted keys so a
      // secret never lands in localStorage.
      localStorage.setItem(
        "n3rf-draft",
        JSON.stringify({ name: workflowName, nodes: stripEphemeralKeys(nodes), edges, updatedAt: Date.now() }),
      );
    } catch {
      /* storage full — draft is best-effort only */
    }
  }, [nodes, edges, workflowName]);

  useEffect(() => {
    localStorage.setItem("n3rf-pane-widths", JSON.stringify(widths));
  }, [widths]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement;
      const inField = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        void runWorkflow();
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z" && !event.shiftKey) {
        if (inField) return; // let native text undo work in fields
        event.preventDefault();
        undo();
      } else if (
        ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z" && event.shiftKey) ||
        ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "y")
      ) {
        if (inField) return;
        event.preventDefault();
        redo();
      } else if (event.key === "Escape") {
        setConnectionDrag(null);
      } else if (
        ["Delete", "Backspace"].includes(event.key) &&
        selectedId &&
        !inField
      ) {
        setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
        setFuture([]);
        setNodes((current) => current.filter((node) => node.id !== selectedId));
        setEdges((current) =>
          current.filter((edge) => edge.source !== selectedId && edge.target !== selectedId),
        );
        setSelectedId(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  function centerCanvas() {
    if (window.innerWidth <= 560 && nodes.length) {
      setPan({ x: 12 - nodes[0].position.x * zoom, y: 20 - nodes[0].position.y * zoom });
    } else {
      setPan({ x: 80, y: 60 });
    }
  }

  function validateNode(node: WorkflowNode) {
    const spec = specById.get(node.type);
    if (!spec) return "Node type is missing from the catalog.";
    for (const param of spec.params) {
      if (!isVisible(param, node.params)) continue;
      const value = node.params[param.key];
      if (param.required && (value === "" || value === null || value === undefined)) {
        return `${param.label} is required.`;
      }
      if (param.type === "json" && typeof value === "string") {
        try {
          JSON.parse(value);
        } catch {
          return `${param.label} must contain valid JSON.`;
        }
      }
    }
    return "";
  }

  async function runWorkflow(testRows?: number) {
    if (runningNodeId) return;
    const invalidNode = nodes.find((node) => validateNode(node));
    if (invalidNode) {
      selectNode(invalidNode.id);
      setErrorMessage(validateNode(invalidNode));
      return;
    }
    setErrorMessage("");
    setOutputNotice("");
    setResultTab("output");
    setResultsOpen(true);
    setRunningNodeId("workflow");
    try {
      const response = await apiFetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(testRows ? { nodes, edges, test_rows: testRows } : { nodes, edges }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Run failed.");
      setResult(payload);
      setApiConnected(true);
      if (testRows) {
        setOutputNotice(`Test run: ${payload.output.length} of ${payload.nodes.reduce((max: number, n: RunNode) => Math.max(max, n.rows_in), 0)} rows — full run next.`);
      }
    } catch (error) {
      if (error instanceof TypeError) {
        setApiConnected(false);
        setResult(simulateRun(nodes, edges, specById));
      } else {
        setErrorMessage(error instanceof Error ? error.message : "Run failed.");
      }
    } finally {
      setRunningNodeId(null);
    }
  }

  async function runNode(nodeId: string) {
    if (runningNodeId) return;
    const included = new Set([nodeId]);
    const pending = [nodeId];
    while (pending.length) {
      const target = pending.pop();
      if (!target) continue;
      for (const edge of edges) {
        if (edge.target === target && !included.has(edge.source)) {
          included.add(edge.source);
          pending.push(edge.source);
        }
      }
    }
    const runNodes = nodes.filter((node) => included.has(node.id));
    const runEdges = edges.filter((edge) => included.has(edge.source) && included.has(edge.target));
    const invalidNode = runNodes.find((node) => validateNode(node));
    if (invalidNode) {
      selectNode(invalidNode.id);
      setErrorMessage(validateNode(invalidNode));
      return;
    }

    setRunningNodeId(nodeId);
    setSelectedId(nodeId);
    setResultsOpen(true);
    setResultTab("output");
    setOutputNotice("");
    setErrorMessage("");
    try {
      const response = await apiFetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nodes, edges, target_node_id: nodeId }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Node run failed.");
      setResult(payload);
      setApiConnected(true);
    } catch (error) {
      if (error instanceof TypeError) {
        setApiConnected(false);
        setResult(simulateRun(runNodes, runEdges, specById));
      } else {
        setErrorMessage(error instanceof Error ? error.message : "Node run failed.");
      }
    } finally {
      setRunningNodeId(null);
    }
  }

  async function saveWorkflow() {
    try {
      // Defense in depth: never send a pasted key to the save endpoint either —
      // the backend strips it too, but it should not travel for storage at all.
      const response = await apiFetch(workflowId ? `/workflows/${workflowId}` : "/workflows", {
        method: workflowId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: workflowName, nodes: stripEphemeralKeys(nodes), edges }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Save failed.");
      setWorkflowId(payload.id);
      setWorkflows((current) => [
        { id: payload.id, name: payload.name },
        ...current.filter((workflow) => workflow.id !== payload.id),
      ]);
      setErrorMessage(`Saved ${payload.name}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Save failed.");
    }
  }

  async function loadWorkflow(id: string) {
    if (!id) return;
    try {
      const response = await apiFetch(`/workflows/${id}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Workflow could not be loaded.");
      setWorkflowId(payload.id);
      setWorkflowName(payload.name);
      setNodes(payload.nodes);
      setEdges(payload.edges);
      setSelectedId(null);
      setResult(null);
      setOutputNotice("");
      setResultTab("output");
      setErrorMessage("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Workflow could not be loaded.");
    }
  }

  function resizePane(
    event: ReactPointerEvent<HTMLDivElement>,
    key: keyof PaneWidths,
    direction: 1 | -1,
  ) {
    event.preventDefault();
    const start = key === "results" ? event.clientY : event.clientX;
    const initialWidth = widths[key];
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);
    function move(next: PointerEvent) {
      const current = key === "results" ? next.clientY : next.clientX;
      const delta = (current - start) * direction;
      const min = key === "palette" ? 190 : key === "inspector" ? 280 : 140;
      const max = key === "palette" ? 360 : key === "inspector" ? 480 : 420;
      setWidths((current) => ({ ...current, [key]: Math.max(min, Math.min(max, initialWidth + delta)) }));
    }
    function up() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
    window.addEventListener("pointercancel", up, { once: true });
  }

  function beginNodeDrag(event: ReactPointerEvent<HTMLDivElement>, node: WorkflowNode) {
    if ((event.target as HTMLElement).closest("button")) return;
    event.preventDefault();
    setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
    setFuture([]);
    setDraggedNode(node.id);
    const start = { x: event.clientX, y: event.clientY, nx: node.position.x, ny: node.position.y };
    function move(next: PointerEvent) {
      patchNode(node.id, (current) => ({
        ...current,
        position: {
          x: start.nx + (next.clientX - start.x) / zoom,
          y: start.ny + (next.clientY - start.y) / zoom,
        },
      }));
    }
    function up() {
      setDraggedNode(null);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
  }

  function beginConnect(event: ReactPointerEvent<HTMLButtonElement>, sourceId: string) {
    event.stopPropagation();
    event.preventDefault();

    function update(next: PointerEvent) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const input = document
        .elementFromPoint(next.clientX, next.clientY)
        ?.closest<HTMLButtonElement>("[data-input]");
      const targetId = input?.dataset.input ?? null;
      const point = input?.getBoundingClientRect();
      const x = point
        ? (point.left + point.width / 2 - rect.left - pan.x) / zoom
        : (next.clientX - rect.left - pan.x) / zoom;
      const y = point
        ? (point.top + point.height / 2 - rect.top - pan.y) / zoom
        : (next.clientY - rect.top - pan.y) / zoom;
      setConnectionDrag({
        sourceId,
        x,
        y,
        targetId: targetId && targetId !== sourceId ? targetId : null,
        targetInput: Number(input?.dataset.inputIndex ?? 0),
      });
    }

    function finish(next: PointerEvent) {
      update(next);
      const input = document
        .elementFromPoint(next.clientX, next.clientY)
        ?.closest<HTMLButtonElement>("[data-input]");
      const targetId = input?.dataset.input;
      if (targetId && targetId !== sourceId) {
        addEdge(sourceId, targetId, Number(input.dataset.inputIndex ?? 0));
      }
      setConnectionDrag(null);
      window.removeEventListener("pointermove", update);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", cancel);
    }
    function cancel() {
      setConnectionDrag(null);
      window.removeEventListener("pointermove", update);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", cancel);
    }

    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setConnectionDrag({
        sourceId,
        x: (event.clientX - rect.left - pan.x) / zoom,
        y: (event.clientY - rect.top - pan.y) / zoom,
        targetId: null,
        targetInput: 0,
      });
    }
    window.addEventListener("pointermove", update);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", cancel);
  }

  function beginPan(event: ReactPointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest(".node-card,.canvas-toolbar,.canvas-hud")) return;
    const start = { x: event.clientX, y: event.clientY, px: pan.x, py: pan.y };
    function move(next: PointerEvent) {
      setPan({ x: start.px + next.clientX - start.x, y: start.py + next.clientY - start.y });
    }
    function up() {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
  }

  function updateParam(key: string, value: unknown) {
    if (!selectedId) return;
    patchNode(selectedId, (node) => {
      // Bricks-style: picking a provider fills in model + key name.
      if (key === "provider" && typeof value === "string" && PROVIDER_PRESETS[value]) {
        const preset = PROVIDER_PRESETS[value];
        return {
          ...node,
          params: {
            ...node.params,
            provider: value,
            model: preset.model,
            api_key_env: preset.api_key_env,
            ...(value === "custom" || value === "ollama" ? { base_url: preset.base_url } : {}),
          },
        };
      }
      return { ...node, params: { ...node.params, [key]: value } };
    });
  }

  function applyModelProfile(profileId: string) {
    if (!selectedId) return;
    const profile = modelProfiles.find((item) => item.id === profileId);
    if (!profile) return;
    patchNode(selectedId, (node) => ({
      ...node,
      params: {
        ...node.params,
        provider: "custom",
        base_url: profile.base_url,
        model: profile.model,
        api_key_env: profile.api_key_env,
      },
    }));
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>, paramKey: string) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await apiFetch("/upload", { method: "POST", body: form });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Upload failed.");
      if (selectedId) {
        let decodedText = "";
        try {
          decodedText = atob(payload.content);
        } catch {
          // not base64
        }
        const fname = (payload.filename || "").toLowerCase();
        const autoEncoding = fname.endsWith(".csv") || fname.endsWith(".tsv") ? "csv" : fname.endsWith(".json") ? "json" : undefined;
        patchNode(selectedId, (node) => ({
          ...node,
          params: {
            ...node.params,
            [paramKey]: payload.content,
            ...(node.params.filename !== undefined ? { filename: payload.filename } : {}),
            ...(autoEncoding && node.params.encoding !== undefined ? { encoding: autoEncoding } : {}),
            ...(node.params.text !== undefined && decodedText ? { text: decodedText } : {}),
          },
        }));
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  const shellStyle = {
    "--palette-width": paletteOpen ? `${widths.palette}px` : "0px",
    "--palette-grip": paletteOpen ? "5px" : "0px",
    "--inspector-width": inspectorOpen ? `${widths.inspector}px` : "0px",
    "--inspector-grip": inspectorOpen ? "5px" : "0px",
    "--results-height": resultsOpen ? `${widths.results}px` : "34px",
    "--results-grip": resultsOpen ? "5px" : "0px",
    "--pan-x": `${pan.x}px`,
    "--pan-y": `${pan.y}px`,
    "--zoom": zoom,
  } as CSSProperties;

  const resultSummary = result
    ? `${result.run_id} · ${result.ms} ms · ${result.nodes.length} nodes · ${result.metrics?.llm_calls ?? 0} LLM calls · ${result.metrics?.tokens_in ?? 0}/${result.metrics?.tokens_out ?? 0} tokens${result.simulated ? " · simulated" : ""}`
    : "Run the workflow to see per-node results.";

  return (
    <TooltipProvider>
      <main className={`app-shell ${!apiConnected ? "is-simulated" : ""}`} style={shellStyle}>
        <header className="topbar">
          <a className="brand-lockup editor-home-link" href="/app" aria-label="Back to workspace">
            <div className="brand-emblem"><Workflow aria-hidden="true" /></div>
            <div><div className="brand-name">n3rf</div><div className="brand-caption">workflow systems</div></div>
          </a>
          <a className="editor-home-button" href="/app" aria-label="Go to app home page" title="Go to app home page">
            <House aria-hidden="true" />
            <span>Home</span>
          </a>
          <div className="topbar-rule" />
          <label className="workflow-field">
            <span className="eyebrow">Current workflow</span>
            <input aria-label="Workflow name" value={workflowName} onChange={(event) => setWorkflowName(event.target.value)} />
          </label>
          <select
            aria-label="Load saved workflow"
            className="saved-workflows"
            value={workflowId ?? ""}
            onChange={(event) => void loadWorkflow(event.target.value)}
          >
            <option value="">Saved workflows</option>
            {workflows.map((workflow) => <option key={workflow.id} value={workflow.id}>{workflow.name}</option>)}
          </select>
          <div className={`connection-state ${apiConnected ? "" : "offline"}`}>
            <span />{apiConnected ? "CONNECTED" : "SIMULATED"}
          </div>
          <div className="topbar-actions">
            <Tooltip label="Undo (Ctrl+Z)"><Button variant="icon" size="icon" aria-label="Undo" title="Undo (Ctrl+Z)" onClick={undo} disabled={!past.length}><Undo2 /></Button></Tooltip>
            <Tooltip label="Redo (Ctrl+Shift+Z)"><Button variant="icon" size="icon" aria-label="Redo" title="Redo (Ctrl+Shift+Z)" onClick={redo} disabled={!future.length}><Redo2 /></Button></Tooltip>
            <Button onClick={() => void saveWorkflow()} disabled={!apiConnected}><Save /> Save</Button>
            <Button
              size="sm"
              onClick={() => void runWorkflow(5)}
              disabled={runningNodeId !== null}
              title="Run the first 5 rows only to check cost and quality"
            >
              <Play /> Test 5 rows
            </Button>
            <Button
              variant="primary"
              onClick={() => void runWorkflow()}
              disabled={runningNodeId !== null}
            >
              {runningNodeId === "workflow" ? <LoaderCircle className="spin" /> : <Play />}
              {runningNodeId === "workflow" ? "Running…" : "Run"}
            </Button>
          </div>
        </header>

        {!apiConnected && (
          <div className="simulation-banner" role="status">
            Backend unavailable — simulated results are for exploration only.
          </div>
        )}

        <Collapsible.Root
          asChild
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          className="palette-pane"
          data-collapsed={!paletteOpen}
        >
          <aside className="palette-pane">
            <div className="pane-heading">
              <Collapsible.Trigger asChild>
                <Button variant="icon" size="icon" aria-label="Collapse node library"><PanelLeftClose /></Button>
              </Collapsible.Trigger>
              <div><span className="eyebrow">Workflow toolkit</span><h2>Node library</h2></div>
              <span className="catalog-count">{String(catalog.length).padStart(2, "0")}</span>
            </div>
            <Collapsible.Content forceMount className="palette-content">
              <NodeLibrary
                catalog={catalog}
                search={search}
                onSearch={setSearch}
                onAdd={addNode}
              />
            </Collapsible.Content>
          </aside>
        </Collapsible.Root>

        <div
          className={`pane-grip palette-grip ${paletteOpen ? "" : "grip-hidden"}`}
          role="separator"
          aria-label="Resize node library"
          aria-orientation="vertical"
          onPointerDown={(event) => resizePane(event, "palette", 1)}
        ><GripVertical /></div>

        <section className="workspace">
          <div
            ref={canvasRef}
            className={`canvas${runningNodeId !== null ? " is-running" : ""}`}
            aria-label="Workflow canvas"
            onPointerDown={beginPan}
            onWheel={(event) => {
              if (event.ctrlKey || event.metaKey) {
                event.preventDefault();
                setZoom((current) => Math.max(0.45, Math.min(1.5, current + (event.deltaY < 0 ? 0.05 : -0.05))));
              }
            }}
          >
            <div className="canvas-hud">
              {!paletteOpen && (
                <Tooltip label="Open node library">
                  <Button variant="icon" size="icon" aria-label="Open node library" onClick={() => setPaletteOpen(true)}>
                    <PanelLeftOpen />
                  </Button>
                </Tooltip>
              )}
              <span className="hud-diamond" /><span>Workflow canvas</span><small>{connectionDrag ? "DROP ON AN INPUT PORT" : `${nodes.length} NODES · ${edges.length} LINKS`}</small>
            </div>
            <div className="canvas-toolbar">
              <Tooltip label="Zoom out"><Button variant="icon" size="icon" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(0.45, value - 0.1))}><ZoomOut /></Button></Tooltip>
              <span className="zoom-value">{Math.round(zoom * 100)}%</span>
              <Tooltip label="Zoom in"><Button variant="icon" size="icon" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(1.5, value + 0.1))}><ZoomIn /></Button></Tooltip>
              <Button size="sm" onClick={centerCanvas}>Fit</Button>
              <span className="toolbar-divider" />
              <Tooltip label={resultsOpen ? "Collapse run results" : "Open run results"}>
                <Button variant="icon" size="icon" aria-label={resultsOpen ? "Collapse run results" : "Open run results"} onClick={() => setResultsOpen((open) => !open)}>
                  {resultsOpen ? <ChevronDown /> : <ChevronUp />}
                </Button>
              </Tooltip>
              {!inspectorOpen && <Tooltip label="Open inspector"><Button variant="icon" size="icon" aria-label="Open inspector" onClick={() => setInspectorOpen(true)}><PanelRightOpen /></Button></Tooltip>}
            </div>
            <div className="world">
              <svg className="edge-layer" width="4000" height="3000" aria-label="Workflow connections">
                {edges.map((edge, index) => {
                  const from = nodes.find((node) => node.id === edge.source);
                  const to = nodes.find((node) => node.id === edge.target);
                  if (!from || !to) return null;
                  const x1 = from.position.x + 240;
                  const y1 = from.position.y + 56;
                  const x2 = to.position.x;
                  const y2 = to.position.y + 56 + (Number(edge.target_input || 0) * 34);
                  const middle = (x1 + x2) / 2;
                  const path = x2 >= x1
                    ? `M ${x1} ${y1} C ${middle} ${y1}, ${middle} ${y2}, ${x2} ${y2}`
                    : `M ${x1} ${y1} L ${x1 + 32} ${y1} L ${x1 + 32} ${y2 - 24} L ${x2 - 32} ${y2 - 24} L ${x2 - 32} ${y2} L ${x2} ${y2}`;
                  return <path key={`${edge.source}-${edge.target}-${index}`} className="workflow-edge" d={path} onClick={() => { setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]); setFuture([]); setEdges((current) => current.filter((_, edgeIndex) => edgeIndex !== index)); }} />;
                })}
                {connectionDrag && (() => {
                  const source = nodes.find((node) => node.id === connectionDrag.sourceId);
                  if (!source) return null;
                  const x1 = source.position.x + 240;
                  const y1 = source.position.y + 56;
                  const middle = (x1 + connectionDrag.x) / 2;
                  return (
                    <path
                      className={`workflow-edge-preview ${connectionDrag.targetId ? "valid" : ""}`}
                      d={`M ${x1} ${y1} C ${middle} ${y1}, ${middle} ${connectionDrag.y}, ${connectionDrag.x} ${connectionDrag.y}`}
                    />
                  );
                })()}
              </svg>
              {nodes.map((node) => {
                const spec = specById.get(node.type);
                if (!spec) return null;
                const Icon = groupIcons[spec.group] ?? Braces;
                const nodeResult = result?.nodes.find((item) => item.id === node.id);
                return (
                  <article
                    key={node.id}
                    className={`node-card ${selectedId === node.id ? "selected" : ""} ${draggedNode === node.id ? "dragging" : ""} ${nodeResult?.status === "error" ? "failed" : ""}`}
                    style={{ left: node.position.x, top: node.position.y, "--node-color": groupTokens[spec.group] } as CSSProperties}
                    onClick={(event) => {
                      if ((event.target as HTMLElement).closest("[data-output],[data-input]")) return;
                      selectNode(node.id);
                    }}
                  >
                    {Array.from({ length: spec.inputs || 1 }, (_, port) => (
                      <Fragment key={port}>
                        <button
                          className={`node-port input-port ${edges.some((edge) => edge.target === node.id && Number(edge.target_input || 0) === port) ? "connected" : ""} ${connectionDrag?.targetId === node.id && connectionDrag.targetInput === port ? "drop-target" : ""}`}
                          data-input={node.id}
                          data-input-index={port}
                          style={spec.inputs && spec.inputs > 1 ? { top: `${35 + port * 30}%` } : undefined}
                          aria-label={`Input port ${port + 1}`}
                        />
                        {spec.inputs && spec.inputs > 1 && (
                          <span className="input-label" style={{ top: `calc(${35 + port * 30}% + 7px)` }}>{port === 0 ? "A" : "B"}</span>
                        )}
                      </Fragment>
                    ))}
                    <div className="node-accent" />
                    <div className="node-titlebar" onPointerDown={(event) => beginNodeDrag(event, node)}>
                      <span className="node-title">
                        <span className="node-icon"><Icon /></span>
                        <span className="node-title-copy"><small>{spec.group}</small>{spec.name}</span>
                      </span>
                      <span className="node-id">{node.id.slice(-4)}</span>
                      <button
                        type="button"
                        className="node-run-button"
                        aria-label={`Run ${spec.name} and upstream nodes`}
                        title={`Run ${spec.name} and upstream nodes`}
                        disabled={runningNodeId !== null}
                        onPointerDown={(event) => event.stopPropagation()}
                        onClick={(event) => {
                          event.stopPropagation();
                          void runNode(node.id);
                        }}
                      >
                        {runningNodeId === node.id
                          ? <LoaderCircle className="spin" />
                          : <Play />}
                      </button>
                    </div>
                    <div className="node-summary">
                      {spec.params.length ? summaryParams(spec.params).map((param) => (
                        <span className="node-param" key={param.key}>
                          <small>{plainParamLabel(param)}</small>
                          <strong>{summaryLabel(param, node.params[param.key])}</strong>
                        </span>
                      )) : <span className="node-param"><small>Configuration</small><strong>No parameters</strong></span>}
                    </div>
                    {nodeResult && (
                      <div className="node-run-meta">
                        <span>{nodeResult.rows_in} <ChevronRight /> {nodeResult.rows_out} rows</span>
                        <small>{nodeResult.ms} ms</small>
                      </div>
                    )}
                    {nodeResult?.error && <div className="node-error">{nodeResult.error}</div>}
                    <button
                      className={`node-port output-port ${edges.some((edge) => edge.source === node.id) ? "connected" : ""}`}
                      data-output={node.id}
                      aria-label="Drag output connector to an input port"
                      onPointerDown={(event) => beginConnect(event, node.id)}
                    />
                  </article>
                );
              })}
            </div>
          </div>

          <div
            className={`pane-grip results-grip ${resultsOpen ? "" : "grip-hidden"}`}
            role="separator"
            aria-label="Resize run results"
            aria-orientation="horizontal"
            onPointerDown={(event) => resizePane(event, "results", -1)}
          ><GripVertical /></div>

          <Collapsible.Root open={resultsOpen} onOpenChange={setResultsOpen} className={`results-pane ${resultsOpen ? "" : "collapsed"}`}>
            <div className="results-heading">
              <Collapsible.Trigger asChild>
                <Button variant="ghost" className="results-title"><Activity /> Run results {resultsOpen ? <ChevronDown /> : <ChevronUp />}</Button>
              </Collapsible.Trigger>
              <span className="result-count">{result ? `${result.nodes.length} steps` : "READY"}</span>
              <span className={`run-summary ${errorMessage ? "has-error" : ""}`} role="status">{errorMessage || resultSummary}</span>
            </div>
            <Collapsible.Content forceMount className="results-content">
              {result ? (
                <div className="results-body">
                  <div className="results-toolbar">
                    <div className="results-tabs" role="tablist" aria-label="Run result views">
                      <button
                        type="button"
                        role="tab"
                        aria-selected={resultTab === "output"}
                        className={`results-tab ${resultTab === "output" ? "active" : ""}`}
                        onClick={() => setResultTab("output")}
                      >
                        Output rows <span>{result.output.length}</span>
                      </button>
                      <button
                        type="button"
                        role="tab"
                        aria-selected={resultTab === "steps"}
                        className={`results-tab ${resultTab === "steps" ? "active" : ""}`}
                        onClick={() => setResultTab("steps")}
                      >
                        Node steps <span>{result.nodes.length}</span>
                      </button>
                      <button
                        type="button"
                        role="tab"
                        aria-selected={resultTab === "diagnostics"}
                        className={`results-tab ${resultTab === "diagnostics" ? "active" : ""}`}
                        onClick={() => setResultTab("diagnostics")}
                      >
                        Diagnostics <span>{result.nodes.reduce((count, item) => count + (item.status === "error" ? 1 : 0) + (item.logs?.filter((entry) => entry.startsWith("Row ")).length ?? 0), 0)}</span>
                      </button>
                    </div>
                    {resultTab === "output" && (
                          <div className="results-actions">
                            <div className="grid-node-select">
                              <label className="field-label" htmlFor="grid-node">GRID</label>
                              <select
                                id="grid-node"
                                aria-label="Choose grid rows"
                                value={gridNodeId ?? ""}
                                onChange={(event) => {
                                  setGridNodeId(event.target.value || null);
                                  setGridFirstN(null);
                                  setGridEmptyColumn(null);
                                }}
                              >
                                <option value="">Final output</option>
                                {result.nodes.map((item) => (
                                  <option key={item.id} value={item.id}>
                                    {item.name || item.id} ({item.rows_out} rows)
                                  </option>
                                ))}
                              </select>
                            </div>
                            {gridFirstN != null && (
                              <button type="button" className="model-settings-link" onClick={() => setGridFirstN(null)}>
                                Show all rows
                              </button>
                            )}
                            {gridEmptyColumn && (
                              <button type="button" className="model-settings-link" onClick={() => setGridEmptyColumn(null)}>
                                Clear empty-cell filter
                              </button>
                            )}
                            <Button
                              size="sm"
                              onClick={() => void copyOutputRows(gridRows).then(
                                () => setOutputNotice("Rows copied to clipboard."),
                                () => setOutputNotice("Could not access the clipboard. Check browser permissions."),
                              )}
                            >
                              <Copy /> Copy rows
                            </Button>
                            <Button size="sm" onClick={() => exportOutputRows(gridRows)}>
                              <Download /> Export CSV
                            </Button>
                          </div>
                    )}
                  </div>
                  {outputNotice && resultTab === "output" && (
                    <span className="output-notice" role="status">{outputNotice}</span>
                  )}
                  {resultTab === "output" ? (
                    <DataGrid
                      rows={gridFilteredRows}
                      label={gridNodeId ? `${result.nodes.find((item) => item.id === gridNodeId)?.name || gridNodeId} — output` : "Final output"}
                      partial={gridPartial}
                      programmed={programmed}
                      executingColumn={executingColumn}
                      executingCell={null}
                      selectedCell={selectedCell}
                      onCellSelect={(cell) => {
                        setSelectedCell(cell);
                        setInspectorTab("cell");
                        setInspectorOpen(true);
                      }}
                      onCellRun={(_rowIndex, column) => setScopeColumn(column)}
                      onColumnEdit={openColumnEditor}
                      onColumnRun={(column) => setScopeColumn(column)}
                      onAddColumn={() => {
                        setSelectedColumn("");
                        setInspectorTab("column");
                        setInspectorOpen(true);
                      }}
                    />
                  ) : resultTab === "steps" ? (
                    <div className="results-scroll">
                      <table className="results-table">
                        <thead><tr><th>Node</th><th>Status</th><th>Time</th><th>Rows</th></tr></thead>
                        <tbody>
                          {result.nodes.map((item, index) => (
                            <ResultRows
                              key={`${item.id}-${index}`}
                              item={item}
                              index={index}
                              onNode={() => selectNode(item.id)}
                              onViewGrid={() => {
                                setGridNodeId(item.id);
                                setResultTab("output");
                                setGridFirstN(null);
                                setGridEmptyColumn(null);
                              }}
                            />
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <RunDiagnostics result={result} onNode={selectNode} />
                  )}
                </div>
              ) : (
                <div className="empty-results"><FileJson2 /><strong>No run data yet</strong><span>Execute your workflow to inspect rows and node performance.</span></div>
              )}
            </Collapsible.Content>
          </Collapsible.Root>
        </section>

        <div
          className={`pane-grip inspector-grip ${inspectorOpen ? "" : "grip-hidden"}`}
          role="separator"
          aria-label="Resize inspector"
          aria-orientation="vertical"
          onPointerDown={(event) => resizePane(event, "inspector", -1)}
        ><GripVertical /></div>

        <Collapsible.Root
          asChild
          open={inspectorOpen}
          onOpenChange={setInspectorOpen}
          className="inspector-pane"
          data-collapsed={!inspectorOpen}
        >
          <aside className="inspector-pane">
            <div className="inspector-heading">
              <Collapsible.Trigger asChild><Button variant="icon" size="icon" aria-label="Collapse inspector"><PanelRightClose /></Button></Collapsible.Trigger>
              <div><span className="eyebrow">Configuration</span><h2>Inspector</h2></div>
            </div>
            <Collapsible.Content forceMount className="inspector-content">
              <div className="inspector-tabs" role="tablist" aria-label="Inspector views">
                <button
                  type="button"
                  role="tab"
                  aria-selected={inspectorTab === "node"}
                  className={`inspector-tab ${inspectorTab === "node" ? "active" : ""}`}
                  onClick={() => setInspectorTab("node")}
                >
                  Node
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={inspectorTab === "column"}
                  className={`inspector-tab ${inspectorTab === "column" ? "active" : ""}`}
                  onClick={() => setInspectorTab("column")}
                >
                  Column{selectedColumn ? ` · ${selectedColumn}` : ""}
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={inspectorTab === "cell"}
                  className={`inspector-tab ${inspectorTab === "cell" ? "active" : ""}`}
                  onClick={() => setInspectorTab("cell")}
                >
                  Cell{selectedCell ? ` · R${selectedCell.rowIndex + 1}` : ""}
                </button>
              </div>

              {inspectorTab === "cell" &&
                (selectedCell ? (
                  <CellDetails
                    cell={{
                      ...selectedCell,
                      producingNode: programmedByColumn[selectedCell.column]?.nodeName,
                      producingNodeId: programmedByColumn[selectedCell.column]?.nodeId,
                    }}
                    onClose={() => {
                      setSelectedCell(null);
                      setInspectorTab("node");
                    }}
                    onEditColumn={openColumnEditor}
                    onRunColumn={runColumn}
                  />
                ) : (
                  <div className="empty-inspector">
                    <Eye /><strong>No cell selected</strong>
                    <span>Click any grid cell to inspect its value, type and lineage.</span>
                  </div>
                ))}

              {inspectorTab === "column" && (
                <div className="column-panel">
                  <div>
                    <span className="eyebrow">Program a column — creates a node</span>
                    <p className="column-panel-note">
                      Columns in n3rf are nodes. Choosing a node type here creates a real graph
                      node (forms still come from <code>GET /nodes</code>) wired after the
                      selected node.
                    </p>
                  </div>
                  <div className="form-field">
                    <label className="field-label" htmlFor="column-name">
                      Column name
                    </label>
                    <Input
                      id="column-name"
                      placeholder="new_column"
                      value={selectedColumn}
                      onChange={(event) => setSelectedColumn(event.target.value)}
                    />
                    <p className="field-hint">
                      {selectedProducingNode
                        ? `Currently produced by: ${selectedProducingNode.nodeName}. Editing here creates a new node.`
                        : "This column is input data — adding a node will create it."}
                    </p>
                  </div>
                  <div className="form-field">
                    <label className="field-label" htmlFor="column-node-type">
                      Node type
                    </label>
                    <Select
                      id="column-node-type"
                      value={columnDraftType}
                      onChange={(event) => {
                        const nextType = event.target.value;
                        setColumnDraftType(nextType);
                        const nextSpec = specById.get(nextType);
                        if (nextSpec) setColumnDraftParams(defaultParams(nextSpec));
                      }}
                    >
                      {catalog
                        .filter((spec) => spec.group !== "input")
                        .map((spec) => (
                          <option key={spec.id} value={spec.id}>
                            {spec.group} · {spec.name}
                          </option>
                        ))}
                    </Select>
                  </div>
                  {columnDraftSpec && (
                    <div className="inspector-fields">
                      {(() => {
                        const visible = columnDraftSpec.params.filter((param) => isVisible(param, columnDraftParams));
                        const { core, advanced } = partitionParams(visible);
                        return (
                          <>
                            {core.map((param) => (
                              <ParamControl
                                key={param.key}
                                param={param}
                                value={columnDraftParams[param.key]}
                                expressionFields={expressionFields} previewRow={expressionPreviewRow}
                                onChange={(value) =>
                                  setColumnDraftParams((current) => ({ ...current, [param.key]: value }))
                                }
                                onUpload={(event) => void uploadFile(event, param.key)}
                              />
                            ))}
                            {advanced.length > 0 && (
                              <details className="advanced-params">
                                <summary>Advanced · {advanced.length} {advanced.length === 1 ? "option" : "options"}</summary>
                                <div className="inspector-fields advanced-fields">
                                  {advanced.map((param) => (
                                    <ParamControl
                                      key={param.key}
                                      param={param}
                                      value={columnDraftParams[param.key]}
                                      expressionFields={expressionFields} previewRow={expressionPreviewRow}
                                      onChange={(value) =>
                                        setColumnDraftParams((current) => ({ ...current, [param.key]: value }))
                                      }
                                      onUpload={(event) => void uploadFile(event, param.key)}
                                    />
                                  ))}
                                </div>
                              </details>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  )}
                  <div className="cell-details-actions">
                    <Button size="sm" variant="primary" onClick={createColumnNode} disabled={!columnDraftSpec}>
                      <Plus /> Create column node
                    </Button>
                    {selectedProducingNode && (
                      <Button size="sm" onClick={() => void runNode(selectedProducingNode.nodeId)}>
                        <Play /> Run producing node
                      </Button>
                    )}
                  </div>
                  <p className="column-panel-note">
                    Cell execution is batch, not per-row: Run executes the owning node for the
                    whole batch. Use filters above the grid to slice the view.
                  </p>
                </div>
              )}

              {inspectorTab === "node" &&
                (selected && selectedSpec ? (
                <>
                  <div
                    className="inspector-node-card"
                    style={{ "--node-color": groupTokens[selectedSpec.group] } as CSSProperties}
                  >
                    <div className="inspector-node-heading">
                      <span className="inspector-node-glyph" style={{ "--node-color": groupTokens[selectedSpec.group] } as CSSProperties}>
                        {(() => { const Icon = groupIcons[selectedSpec.group] ?? Braces; return <Icon />; })()}
                      </span>
                      <div><span className="eyebrow">{selectedSpec.group} node</span><h3>{selectedSpec.name}</h3></div>
                      <Button variant="icon" size="icon" aria-label="Delete selected node" onClick={() => {
                        setPast((current) => [...current.slice(-99), snapshot(nodes, edges)]);
                        setFuture([]);
                        setNodes((current) => current.filter((node) => node.id !== selected.id));
                        setEdges((current) => current.filter((edge) => edge.source !== selected.id && edge.target !== selected.id));
                        setSelectedId(null);
                      }}><Trash2 /></Button>
                    </div>
                    <span className="inspector-node-id">NODE ID <code>{selected.id}</code></span>
                  </div>
                  {selectedSpec.group === "ai" && (
                    <div className="model-profile-picker">
                      <label className="field-label" htmlFor="model-profile">MODEL PROFILE</label>
                      <Select
                        id="model-profile"
                        value={modelProfiles.find((profile) =>
                          selected.params.provider === "custom" &&
                          profile.base_url === selected.params.base_url &&
                          profile.model === selected.params.model &&
                          profile.api_key_env === selected.params.api_key_env
                        )?.id ?? ""}
                        onChange={(event) => applyModelProfile(event.target.value)}
                      >
                        <option value="">Node-specific settings</option>
                        {modelProfiles.map((profile) => (
                          <option value={profile.id} key={profile.id}>{profile.name} · {profile.model}</option>
                        ))}
                      </Select>
                      <button type="button" className="model-settings-link" onClick={() => { window.location.href = "/app/models"; }}>
                        {modelProfiles.length ? "Manage model profiles" : "Configure a model provider"} <ArrowUpRight />
                      </button>
                    </div>
                  )}
                  <p className="inspector-description">{selectedSpec.description}</p>
                  {result?.nodes.find((item) => item.id === selected.id)?.input_samples?.map((rows, inputIndex) => {
                    const sourceId = edges.find(
                      (edge) => edge.target === selected.id && Number(edge.target_input ?? 0) === inputIndex,
                    )?.source;
                    const source = nodes.find((node) => node.id === sourceId);
                    const sourceName = source
                      ? specById.get(source.type)?.name ?? source.type
                      : "Workflow input";
                    return (
                      <section className="inspector-input-preview" key={`${selected.id}-input-${inputIndex}`}>
                        <div>
                          <span className="eyebrow">INPUT {inputIndex + 1} · {sourceName}</span>
                          <small>{rows.length} sample {rows.length === 1 ? "row" : "rows"}</small>
                        </div>
                        {rows.length
                          ? <pre>{JSON.stringify(rows, null, 2)}</pre>
                          : <p>No incoming rows at this input.</p>}
                      </section>
                    );
                  })}
                  <div className="inspector-section-heading">
                    <span>Parameters</span><small>{String(selectedSpec.params.length).padStart(2, "0")}</small>
                  </div>
                  <div className="inspector-fields">
                    {(() => {
                      const visible = selectedSpec.params.filter((param) => isVisible(param, selected.params));
                      const { core, advanced } = partitionParams(visible);
                      return (
                        <>
                          {core.map((param) => (
                            <ParamControl key={param.key} param={param} value={selected.params[param.key]} expressionFields={expressionFields} previewRow={expressionPreviewRow} onChange={(value) => updateParam(param.key, value)} onUpload={(event) => void uploadFile(event, param.key)} />
                          ))}
                          {advanced.length > 0 && (
                            <details className="advanced-params">
                              <summary>Advanced · {advanced.length} {advanced.length === 1 ? "option" : "options"}</summary>
                              <div className="inspector-fields advanced-fields">
                                {advanced.map((param) => (
                                  <ParamControl key={param.key} param={param} value={selected.params[param.key]} expressionFields={expressionFields} previewRow={expressionPreviewRow} onChange={(value) => updateParam(param.key, value)} onUpload={(event) => void uploadFile(event, param.key)} />
                                ))}
                              </div>
                            </details>
                          )}
                        </>
                      );
                    })()}
                  </div>
                </>
              ) : (
                <div className="empty-inspector"><Workflow /><strong>Select a node</strong><span>Choose a node on the canvas to configure its parameters.</span></div>
              ))}
            </Collapsible.Content>
          </aside>
        </Collapsible.Root>

        <dialog
          ref={scopeDialogRef}
          className="scope-dialog"
          aria-label={`Run column ${scopeColumn ?? ""}`}
          onCancel={() => setScopeColumn(null)}
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setScopeColumn(null);
            }
          }}
        >
          <span className="eyebrow">Run column — batch, not per-row</span>
          <h2>{scopeColumn ? `Run “${scopeColumn}”` : "Run column"}</h2>
          <p className="column-panel-note">
            n3rf runs a whole batch at a time. Run executes the owning node for all rows.
            The other two options only slice the grid view.
          </p>
          <div className="scope-modes">
            <button
              type="button"
              className="scope-mode"
              onClick={() => {
                if (scopeColumn) runColumn(scopeColumn);
                setScopeColumn(null);
              }}
            >
              <Play /> Run whole column
              <small>Upstream + node that creates this column</small>
            </button>
            <button
              type="button"
              className="scope-mode"
              onClick={() => {
                setGridFirstN(100);
                setGridEmptyColumn(null);
                setScopeColumn(null);
              }}
            >
              <Eye /> First 100 rows — view only
              <small>Slices the grid; does not re-run</small>
            </button>
            <button
              type="button"
              className="scope-mode"
              onClick={() => {
                if (scopeColumn) {
                  setGridEmptyColumn(scopeColumn);
                  setGridFirstN(null);
                }
                setScopeColumn(null);
              }}
            >
              <Eye /> Empty cells only — view only
              <small>Shows rows where this column is empty</small>
            </button>
          </div>
          <div className="profile-actions">
            <Button type="button" variant="ghost" onClick={() => setScopeColumn(null)}>
              Cancel
            </Button>
          </div>
        </dialog>

      </main>
    </TooltipProvider>
  );
}

type ExpressionField = { label: string; expression: string };

function expressionFieldsFromSamples(samples: unknown[][]): ExpressionField[] {
  const fields = new Map<string, ExpressionField>();
  function collect(value: Record<string, unknown>, path: string[] = []) {
    for (const [key, child] of Object.entries(value)) {
      const nextPath = [...path, key];
      const barePath = nextPath.reduce(
        (source, part) =>
          /^[A-Za-z_$][\w$]*$/.test(part)
            ? source === ""
              ? part
              : `${source}.${part}`
            : `${source}[${JSON.stringify(part)}]`,
        "",
      );
      // Headers with spaces/punctuation can't be bare names — keep $json there.
      const expressionPath = /^[A-Za-z_$][\w$]*$/.test(nextPath[0]) ? barePath : `$json${barePath}`;
      const expression = `{{${expressionPath}}}`;
      fields.set(expression, { label: nextPath.join("."), expression });
      if (
        child !== null &&
        typeof child === "object" &&
        !Array.isArray(child) &&
        nextPath.length < 4
      ) {
        collect(child as Record<string, unknown>, nextPath);
      }
    }
  }
  for (const sample of samples) {
    for (const row of sample) {
      if (row !== null && typeof row === "object" && !Array.isArray(row)) {
        collect(row as Record<string, unknown>);
      }
    }
  }
  return [...fields.values()];
}

function ExpressionInput({
  id,
  ariaLabel,
  value,
  onChange,
  fields,
  multiline = false,
  paramKey = "",
  previewRow = null,
}: {
  id: string;
  ariaLabel?: string;
  value: string;
  onChange: (value: unknown) => void;
  fields: ExpressionField[];
  multiline?: boolean;
  paramKey?: string;
  previewRow?: Record<string, unknown> | null;
}) {
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const [trigger, setTrigger] = useState<{ start: number; end: number; query: string } | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isDropping, setIsDropping] = useState(false);
  const [templateChoice, setTemplateChoice] = useState("");
  const listId = `${id}-expression-options`;
  const options = trigger
    ? fields.filter((field) => field.label.toLowerCase().includes(trigger.query.toLowerCase()))
    : [];
  const templates = templatesFor(paramKey);
  const preview = value ? previewWithRow(value, previewRow) : "";

  function insertAt(start: number, end: number, field: ExpressionField) {
    const nextValue = `${value.slice(0, start)}${field.expression}${value.slice(end)}`;
    const cursor = start + field.expression.length;
    onChange(nextValue);
    setTrigger(null);
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      inputRef.current?.setSelectionRange(cursor, cursor);
    });
  }

  function insertField(field: ExpressionField) {
    if (!trigger) {
      const input = inputRef.current;
      const at = input?.selectionStart ?? value.length;
      insertAt(at, at, field);
      return;
    }
    insertAt(trigger.start, trigger.end, field);
  }

  function update(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const text = event.currentTarget.value;
    const cursor = event.currentTarget.selectionStart ?? text.length;
    onChange(text);
    const match = /(^|[\s"'`(\[{])@([\w.-]*)$/.exec(text.slice(0, cursor));
    if (match) {
      setTrigger({
        start: cursor - match[0].length + match[1].length,
        end: cursor,
        query: match[2],
      });
      setActiveIndex(0);
    } else {
      setTrigger(null);
    }
  }

  function openPicker() {
    const input = inputRef.current;
    const start = input?.selectionStart ?? value.length;
    const end = input?.selectionEnd ?? start;
    setTrigger({ start, end, query: "" });
    setActiveIndex(0);
    input?.focus();
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
    if (!trigger) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setTrigger(null);
    } else if (event.key === "ArrowDown" && options.length) {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % options.length);
    } else if (event.key === "ArrowUp" && options.length) {
      event.preventDefault();
      setActiveIndex((current) => (current - 1 + options.length) % options.length);
    } else if (event.key === "Enter" && options[activeIndex]) {
      event.preventDefault();
      insertField(options[activeIndex]);
    }
  }

  function onDrop(event: ReactDragEvent<HTMLInputElement | HTMLTextAreaElement>) {
    event.preventDefault();
    setIsDropping(false);
    const expression = event.dataTransfer.getData("text/plain");
    if (!expression) return;
    const input = inputRef.current;
    const at = input?.selectionStart ?? value.length;
    const end = input?.selectionEnd ?? at;
    const nextValue = `${value.slice(0, at)}${expression}${value.slice(end)}`;
    const cursor = at + expression.length;
    onChange(nextValue);
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      inputRef.current?.setSelectionRange(cursor, cursor);
    });
  }

  const inputProps = {
    id,
    "aria-label": ariaLabel,
    className: "form-control expression-input-control",
    value,
    role: "combobox" as const,
    "aria-autocomplete": "list" as const,
    "aria-expanded": trigger !== null,
    "aria-controls": listId,
    onChange: update,
    onKeyDown: handleKeyDown,
    onBlur: () => setTrigger(null),
    onDragOver: (event: ReactDragEvent) => {
      event.preventDefault();
      setIsDropping(true);
    },
    onDragLeave: () => setIsDropping(false),
    onDrop,
  };

  return (
    <div className={`expression-input-wrap${isDropping ? " is-drop-target" : ""}`}>
      {templates.length > 0 && (
        <label className="field-chip-label" htmlFor={`${id}-template`}>
          <span>Start from a template</span>
          <Select
            id={`${id}-template`}
            value={templateChoice}
            onChange={(event) => {
              setTemplateChoice("");
              const index = Number(event.target.value);
              const template = templates[index];
              const firstField = fields[0];
              if (!template || !firstField) return;
              onChange(template.make(firstField.expression));
            }}
          >
            <option value="">Choose a template…</option>
            {templates.map((template, index) => (
              <option key={template.label} value={index}>
                {template.label}
              </option>
            ))}
          </Select>
        </label>
      )}
      {multiline ? (
        <Textarea {...inputProps} ref={(element) => { inputRef.current = element; }} />
      ) : (
        <Input {...inputProps} ref={(element) => { inputRef.current = element; }} type="text" />
      )}
      <button
        type="button"
        className="expression-picker-trigger"
        aria-label="Insert incoming field"
        title="Insert incoming field"
        onMouseDown={(event) => event.preventDefault()}
        onClick={openPicker}
      >
        <AtSign />
      </button>
      <div className="field-chip-strip" aria-label="Your columns — click or drag into the box">
        <span className="field-chip-title">Your columns — click or drag into the box</span>
        <div className="field-chip-list">
          {fields.map((field) => (
            <button
              type="button"
              key={field.expression}
              className="field-chip"
              draggable
              title={`${humanizeFieldLabel(field.label)} — click to insert, or drag into the box`}
              onDragStart={(event) => {
                event.dataTransfer.setData("text/plain", field.expression);
                event.dataTransfer.effectAllowed = "copy";
              }}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => insertField(field)}
            >
              {humanizeFieldLabel(field.label)}
            </button>
          ))}
        </div>
      </div>
      {preview && (
        <p className="expression-preview">
          <strong>Will use:</strong> {preview}
        </p>
      )}
      {trigger && (
        <div className="expression-picker" id={listId} role="listbox" aria-label="Incoming fields">
          {options.length ? options.map((field, index) => (
            <button
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              className={`expression-picker-option ${index === activeIndex ? "active" : ""}`}
              key={field.expression}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => insertField(field)}
            >
              <span>{humanizeFieldLabel(field.label)}</span>
            </button>
          )) : (
            <p className="expression-picker-empty">No matching columns.</p>
          )}
        </div>
      )}
    </div>
  );
}

function FieldNameControl({
  id,
  value,
  fields,
  onChange,
}: {
  id: string;
  value: string;
  fields: ExpressionField[];
  onChange: (value: unknown) => void;
}) {
  const names = [...new Set(fields.map((field) => bareFieldName(field.label)))];
  const known = value.trim() === "" || names.includes(value.trim());
  const [custom, setCustom] = useState(!known && value.trim() !== "");
  return (
    <div>
      <Select
        id={id}
        value={custom ? "__custom__" : value.trim() || names[0] || ""}
        onChange={(event) => {
          if (event.target.value === "__custom__") {
            setCustom(true);
            return;
          }
          setCustom(false);
          onChange(event.target.value);
        }}
      >
        {names.map((name) => (
          <option key={name} value={name}>
            {humanizeFieldLabel(name)}
          </option>
        ))}
        <option value="__custom__">Other — type a name</option>
      </Select>
      {custom && (
        <Input
          type="text"
          placeholder="Column name"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Custom column name"
        />
      )}
    </div>
  );
}

function MultiFieldControl({
  value,
  fields,
  onChange,
}: {
  value: string;
  fields: ExpressionField[];
  onChange: (value: unknown) => void;
}) {
  const names = [...new Set(fields.map((field) => bareFieldName(field.label)))];
  const selected = new Set(
    value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  );
  function toggle(name: string) {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    onChange([...next].join(", "));
  }
  return (
    <div className="field-chip-list">
      {names.map((name) => (
        <button
          key={name}
          type="button"
          className={`field-chip${selected.has(name) ? " selected" : ""}`}
          aria-pressed={selected.has(name)}
          onClick={() => toggle(name)}
        >
          {humanizeFieldLabel(name)}
        </button>
      ))}
    </div>
  );
}

function ConditionControl({
  id,
  value,
  fields,
  onChange,
}: {
  id: string;
  value: string;
  fields: ExpressionField[];
  onChange: (value: unknown) => void;
}) {
  const parsed = parseCondition(value);
  const [advanced, setAdvanced] = useState(false);
  const field = parsed?.field ?? bareFieldName(fields[0]?.label ?? "company");
  const operator = parsed?.operator ?? "==";
  const textValue = parsed?.value ?? "";
  if (advanced || !parsed) {
    return (
      <div>
        <ExpressionInput
          id={id}
          value={value}
          onChange={onChange}
          fields={fields}
          paramKey="condition"
        />
        <button type="button" className="model-settings-link" onClick={() => setAdvanced(false)}>
          Use simple picks instead
        </button>
      </div>
    );
  }
  const names = [...new Set(fields.map((item) => bareFieldName(item.label)))];
  return (
    <fieldset className="condition-builder">
      <legend className="condition-builder-title">Keep rows where</legend>
      <div className="condition-row">
        <Select
          aria-label="Column"
          value={names.includes(field) ? field : names[0] ?? field}
          onChange={(event) => onChange(buildCondition(event.target.value, operator, textValue))}
        >
          {names.map((name) => (
            <option key={name} value={name}>
              {humanizeFieldLabel(name)}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Operator"
          value={operator}
          onChange={(event) => onChange(buildCondition(field, event.target.value, textValue))}
        >
          {CONDITION_OPERATORS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
      </div>
      <Input
        type="text"
        placeholder='Value, e.g. software, 42, true'
        aria-label="Value to match"
        value={textValue}
        onChange={(event) => onChange(buildCondition(field, operator, event.target.value))}
      />
      <button type="button" className="model-settings-link" onClick={() => setAdvanced(true)}>
        Type it myself (advanced)
      </button>
    </fieldset>
  );
}

function JsonControl({
  paramKey,
  value,
  onChange,
}: {
  paramKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const [showRaw, setShowRaw] = useState(false);
  const [rawError, setRawError] = useState("");
  let parsed: unknown = value;
  if (typeof value === "string") {
    try {
      parsed = value === "" ? {} : JSON.parse(value);
    } catch {
      parsed = value;
    }
  }
  if (showRaw) {
    const rawText =
      typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2);
    return (
      <div>
        <Textarea
          className="code-control"
          value={rawText}
          onChange={(event) => {
            const text = event.target.value;
            setRawError("");
            try {
              onChange(text === "" ? {} : JSON.parse(text));
            } catch {
              onChange(text);
              setRawError("That is not valid JSON — the friendly editor will be safer.");
            }
          }}
          aria-label="JSON (advanced)"
        />
        {rawError && <p className="field-error">{rawError}</p>}
        <button type="button" className="model-settings-link" onClick={() => setShowRaw(false)}>
          Hide JSON — use picks instead
        </button>
      </div>
    );
  }
  if (Array.isArray(parsed)) {
    const rows = parsed as Record<string, unknown>[];
    const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
    return (
      <div>
        <div className="json-table">
          {rows.map((row, index) => (
            <div className="json-row" key={index}>
              {columns.map((column) => (
                <label className="json-cell" key={column}>
                  <span>{humanizeFieldLabel(column)}</span>
                  <Input
                    value={String(row[column] ?? "")}
                    aria-label={column}
                    onChange={(event) => {
                      const next = rows.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, [column]: event.target.value } : item,
                      );
                      onChange(next);
                    }}
                  />
                </label>
              ))}
              <button
                type="button"
                className="model-settings-link"
                aria-label="Remove row"
                onClick={() => onChange(rows.filter((_, itemIndex) => itemIndex !== index))}
              >
                Remove
              </button>
            </div>
          ))}
          {rows.length === 0 && <p className="field-hint">No rows yet — add one below.</p>}
        </div>
        <div className="json-actions">
          <button
            type="button"
            className="model-settings-link"
            onClick={() => {
              const nextRow = Object.fromEntries(columns.map((column) => [column, ""]));
              onChange([...rows, nextRow]);
            }}
          >
            + Add a row
          </button>
          <button type="button" className="model-settings-link" onClick={() => setShowRaw(true)}>
            Edit as JSON (advanced)
          </button>
        </div>
      </div>
    );
  }
  if (paramKey === "schema") {
    const current = schemaPresetLabel(parsed);
    return (
      <div>
        <Select
          aria-label="What the model returns"
          value={current}
          onChange={(event) => {
            const preset = SCHEMA_PRESETS.find((item) => item.label === event.target.value);
            if (preset) onChange(preset.value);
            else setShowRaw(true);
          }}
        >
          {SCHEMA_PRESETS.map((preset) => (
            <option key={preset.label} value={preset.label}>
              {preset.label}
            </option>
          ))}
          <option value="custom">Custom (edit JSON directly)</option>
        </Select>
        <button type="button" className="model-settings-link" onClick={() => setShowRaw(true)}>
          Edit as JSON (advanced)
        </button>
      </div>
    );
  }
  const entries = parsed && typeof parsed === "object"
    ? Object.entries(parsed as Record<string, unknown>)
    : [];
  return (
    <div>
      {entries.map(([key, entryValue], index) => (
        <div className="json-pair" key={`${key}-${index}`}>
          <Input
            placeholder="Name"
            aria-label="Name"
            value={key}
            onChange={(event) => {
              const next = entries.map(([k, v], itemIndex) =>
                itemIndex === index ? [event.target.value, v] as const : ([k, v] as const),
              );
              onChange(Object.fromEntries(next));
            }}
          />
          <Input
            placeholder="Value"
            aria-label="Value"
            value={typeof entryValue === "string" ? entryValue : JSON.stringify(entryValue)}
            onChange={(event) => {
              const next = entries.map(([k, v], itemIndex) =>
                itemIndex === index ? [k, event.target.value] as const : ([k, v] as const),
              );
              onChange(Object.fromEntries(next));
            }}
          />
          <button
            type="button"
            className="model-settings-link"
            onClick={() => onChange(Object.fromEntries(entries.filter((_, i) => i !== index)))}
          >
            Remove
          </button>
        </div>
      ))}
      {entries.length === 0 && <p className="field-hint">Nothing set yet — this is optional.</p>}
      <div className="json-actions">
        <button
          type="button"
          className="model-settings-link"
          onClick={() =>
            onChange(Object.fromEntries([...entries, [`new_${entries.length + 1}`, ""]]))
          }
        >
          + Add a pair
        </button>
        <button type="button" className="model-settings-link" onClick={() => setShowRaw(true)}>
          Edit as JSON (advanced)
        </button>
      </div>
    </div>
  );
}

function ParamControl({
  param,
  value,
  expressionFields,
  previewRow = null,
  onChange,
  onUpload,
}: {
  param: ParamSpec;
  value: unknown;
  expressionFields: ExpressionField[];
  previewRow?: Record<string, unknown> | null;
  onChange: (value: unknown) => void;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const [error, setError] = useState("");
  const [presetChoice, setPresetChoice] = useState("");
  const inputId = `param-${param.key}`;

  function updateText(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const text = event.target.value;
    if (param.type === "number") {
      onChange(text === "" ? "" : Number(text));
    } else {
      onChange(text);
    }
    setError("");
  }

  const stringValue = typeof value === "string" ? value : formatValue(value);

  let control;
  if (param.key === "condition" && param.expression) {
    control = (
      <ConditionControl id={inputId} value={stringValue} fields={expressionFields} onChange={onChange} />
    );
  } else if (param.key === "fields" && param.type === "string") {
    control = <MultiFieldControl value={stringValue} fields={expressionFields} onChange={onChange} />;
  } else if (FIELD_NAME_KEYS.has(param.key) && param.type === "string") {
    control = (
      <FieldNameControl id={inputId} value={stringValue} fields={expressionFields} onChange={onChange} />
    );
  } else if (param.expression && (param.type === "string" || param.type === "textarea")) {
    control = (
      <ExpressionInput
        id={inputId}
        value={stringValue}
        onChange={onChange}
        fields={expressionFields}
        multiline={param.type === "textarea"}
        paramKey={param.key}
        previewRow={previewRow}
      />
    );
  } else if (param.type === "boolean") {
    control = (
      <label className="toggle-control">
        <input id={inputId} type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} />
        <span />
        <small>{value ? "On" : "Off"}</small>
      </label>
    );
  } else if (param.type === "select") {
    control = (
      <Select id={inputId} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
        {(param.options || []).map((option) => (
          <option value={option} key={option}>
            {humanizeOption(option)}
          </option>
        ))}
      </Select>
    );
  } else if (param.type === "rows") {
    control = (
      <RowsControl
        param={param}
        value={Array.isArray(value) ? (value as Record<string, unknown>[]) : []}
        expressionFields={expressionFields}
        previewRow={previewRow}
        onChange={onChange}
      />
    );
  } else if (param.type === "file") {
    control = <Input id={inputId} className="file-control" type="file" onChange={onUpload} />;
  } else if (param.type === "json") {
    control = <JsonControl paramKey={param.key} value={value} onChange={onChange} />;
  } else if (param.type === "code") {
    control = (
      <div>
        <Select
          aria-label="Start from a template"
          value={presetChoice}
          onChange={(event) => {
            const preset = CODE_PRESETS.find((item) => item.label === event.target.value);
            setPresetChoice("");
            if (preset) onChange(preset.value);
          }}
        >
          <option value="">Start from a template…</option>
          {CODE_PRESETS.map((preset) => (
            <option key={preset.label} value={preset.label}>
              {preset.label}
            </option>
          ))}
        </Select>
        <Textarea
          id={inputId}
          className="code-control"
          value={stringValue}
          onChange={updateText}
          aria-label="Your custom step (Python)"
        />
      </div>
    );
  } else if (param.type === "number") {
    const numeric = typeof value === "number" ? value : Number(value) || 0;
    control = (
      <div className="number-control">
        <button type="button" aria-label="Decrease" onClick={() => onChange(numeric - 1)}>−</button>
        <Input
          id={inputId}
          type="number"
          value={stringValue}
          onChange={updateText}
        />
        <button type="button" aria-label="Increase" onClick={() => onChange(numeric + 1)}>+</button>
      </div>
    );
  } else if (param.type === "textarea") {
    const example = typeof param.default === "string" ? param.default : "";
    control = (
      <div>
        <Textarea id={inputId} value={stringValue} onChange={updateText} />
        {example && example !== stringValue && (
          <button type="button" className="model-settings-link" onClick={() => onChange(example)}>
            Restore the example
          </button>
        )}
      </div>
    );
  } else if (param.key === "model" || param.key === "embedding_model") {
    control = (
      <div>
        <Input id={inputId} type="text" list="model-suggestions" value={stringValue} onChange={updateText} />
        <datalist id="model-suggestions">
          {MODEL_SUGGESTIONS.map((model) => (
            <option key={model} value={model} />
          ))}
        </datalist>
      </div>
    );
  } else if (param.key === "api_key" || param.type === "password") {
    control = (
      <div>
        <Input id={inputId} type="password" autoComplete="off" spellCheck={false} value={stringValue} onChange={updateText} placeholder="Paste a key for this run only" />
        <p className="field-hint">Never saved or logged. Leave blank to use the env var above.</p>
      </div>
    );
  } else if (param.key === "api_key_env") {
    control = (
      <div>
        <Input id={inputId} type="text" list="env-suggestions" value={stringValue} onChange={updateText} />
        <datalist id="env-suggestions">
          {ENV_SUGGESTIONS.map((name) => (
            <option key={name} value={name} />
          ))}
        </datalist>
        <p className="field-hint">Just the name — the secret itself is never typed here. Or paste a key below for this run only.</p>
      </div>
    );
  } else {
    control = (
      <Input id={inputId} type="text" value={stringValue} onChange={updateText} />
    );
  }

  const hint = param.hint ? plainHint(param.hint) : undefined;
  return (
    <div className="form-field">
      <label className="field-label" htmlFor={param.type === "rows" || param.type === "json" ? undefined : inputId}>
        {plainParamLabel(param)}
        {param.required ? " *" : ""}
        {param.unit ? <span>{param.unit}</span> : null}
      </label>
      {control}
      {hint && <p className="field-hint">{hint}</p>}
      {param.expression && !param.hint && (
        <p className="field-hint">Pick a column below, or drag one into the box.</p>
      )}
      <span className="field-error">{error}</span>
    </div>
  );
}

function RowsControl({
  param,
  value,
  expressionFields,
  previewRow = null,
  onChange,
}: {
  param: ParamSpec;
  value: Record<string, unknown>[];
  expressionFields: ExpressionField[];
  previewRow?: Record<string, unknown> | null;
  onChange: (value: unknown) => void;
}) {
  const columns = param.columns ?? [];
  function updateCell(rowIndex: number, key: string, nextValue: unknown) {
    onChange(value.map((row, index) => (index === rowIndex ? { ...row, [key]: nextValue } : row)));
  }
  return (
    <div className="rows-control">
      {value.map((row, index) => (
        <div className="row-editor" key={index} style={{ "--row-columns": columns.length } as CSSProperties}>
          {columns.map((column) => {
            const cellId = `param-${param.key}-${index}-${column.key}`;
            const editor = column.type === "select" ? (
              <Select
                key={column.key}
                id={cellId}
                value={String(row[column.key] ?? "")}
                aria-label={column.label}
                onChange={(event) => updateCell(index, column.key, event.target.value)}
              >
                {(column.options ?? []).map((option) => (
                  <option key={option} value={option}>
                    {humanizeOption(option)}
                  </option>
                ))}
              </Select>
            ) : column.type === "boolean" ? (
              <input
                key={column.key}
                type="checkbox"
                id={cellId}
                aria-label={column.label}
                checked={Boolean(row[column.key])}
                onChange={(event) => updateCell(index, column.key, event.target.checked)}
              />
            ) : column.expression ? (
              <ExpressionInput
                id={cellId}
                ariaLabel={column.label}
                key={column.key}
                value={formatValue(row[column.key])}
                onChange={(nextValue) => updateCell(index, column.key, nextValue)}
                fields={expressionFields}
                paramKey={column.key}
                previewRow={previewRow}
              />
            ) : column.key === "from" || column.key === "field" ? (
              <FieldNameControl
                key={column.key}
                id={cellId}
                value={formatValue(row[column.key])}
                fields={expressionFields}
                onChange={(nextValue) => updateCell(index, column.key, nextValue)}
              />
            ) : (
              <Input
                key={column.key}
                id={cellId}
                type={column.type === "number" ? "number" : "text"}
                placeholder={column.label}
                aria-label={column.label}
                value={formatValue(row[column.key])}
                onChange={(event) =>
                  updateCell(index, column.key, column.type === "number" ? Number(event.target.value) : event.target.value)
                }
              />
            );
            return (
              <div className="row-cell" key={column.key}>
                <span>{column.label}</span>
                {editor}
              </div>
            );
          })}
          <Button variant="icon" size="icon" aria-label="Remove row" onClick={() => onChange(value.filter((_, rowIndex) => rowIndex !== index))}>
            <X />
          </Button>
        </div>
      ))}
      <Button
        size="sm"
        onClick={() =>
          onChange([
            ...value,
            Object.fromEntries(columns.map((column) => [column.key, column.default ?? (column.type === "boolean" ? false : "")])),
          ])
        }
      >
        <Plus /> Add row
      </Button>
    </div>
  );
}

function outputRecords(rows: unknown[]): Record<string, unknown>[] {
  return rows.map((row) =>
    row !== null && typeof row === "object" && !Array.isArray(row)
      ? row as Record<string, unknown>
      : { value: row },
  );
}

function outputCellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function spreadsheetSafeText(value: unknown): string {
  const text = outputCellText(value);
  return typeof value === "string" && /^[\t\r ]*[=+\-@]/.test(text) ? `'${text}` : text;
}

function csvCell(value: unknown): string {
  return `"${spreadsheetSafeText(value).replaceAll('"', '""')}"`;
}

function exportOutputRows(rows: unknown[]) {
  const records = outputRecords(rows);
  const columns = [...new Set(records.flatMap((row) => Object.keys(row)))];
  const lines = [
    columns.map(csvCell).join(","),
    ...records.map((row) => columns.map((column) => csvCell(row[column])).join(",")),
  ];
  const url = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "n3rf-output.csv";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function copyOutputRows(rows: unknown[]) {
  const records = outputRecords(rows);
  const columns = [...new Set(records.flatMap((row) => Object.keys(row)))];
  const text = [
    columns.map(spreadsheetSafeText).join("\t"),
    ...records.map((row) => columns.map((column) => spreadsheetSafeText(row[column])).join("\t")),
  ].join("\n");
  await navigator.clipboard.writeText(text);
}

function RunDiagnostics({
  result,
  onNode,
}: {
  result: RunResult;
  onNode: (id: string) => void;
}) {
  const failures = result.nodes.filter((item) => item.status === "error");
  const rowIssues = result.nodes.flatMap((item) =>
    (item.logs ?? [])
      .filter((entry) => entry.startsWith("Row "))
      .map((message) => ({ item, message })),
  );
  const loggedNodes = result.nodes.filter((item) => item.logs?.length);
  return (
    <div className="results-scroll diagnostics-scroll">
      <div className="diagnostic-metrics" aria-label="Run metrics">
        <div><span>Duration</span><strong>{result.ms} ms</strong></div>
        <div><span>Nodes executed</span><strong>{result.nodes.length}</strong></div>
        <div><span>LLM calls</span><strong>{result.metrics?.llm_calls ?? 0}</strong></div>
        <div><span>Tokens in / out</span><strong>{result.metrics?.tokens_in ?? 0} / {result.metrics?.tokens_out ?? 0}</strong></div>
        <div className={failures.length ? "has-failure" : ""}><span>Failed nodes</span><strong>{failures.length}</strong></div>
      </div>
      {failures.length ? (
        <section className="diagnostic-section" aria-label="Node failures">
          <h3><AlertTriangle /> Failures <span>{failures.length}</span></h3>
          {failures.map((item) => (
            <article className="diagnostic-failure" key={item.id}>
              <button type="button" className="diagnostic-node-link" onClick={() => onNode(item.id)}>
                {item.name || item.id}
              </button>
              <span className="diagnostic-node-id">{item.id}</span>
              <p>{item.error || "Node failed without an error message."}</p>
              <div className="diagnostic-failure-meta">
                <span>{item.ms} ms</span>
                <span>{item.rows_in} rows in</span>
                <span>{item.rows_out} rows out</span>
              </div>
            </article>
          ))}
        </section>
      ) : rowIssues.length ? (
        <p className="diagnostic-log-empty">
          {rowIssues.length} row {rowIssues.length === 1 ? "issue" : "issues"} recorded below.
        </p>
      ) : (
        <div className="diagnostic-ok"><span className="status-indicator" /> No node failures in this run.</div>
      )}
      <section className="diagnostic-section" aria-label="Run logs">
        <h3><FileText /> Logs <span>{loggedNodes.reduce((count, item) => count + (item.logs?.length ?? 0), 0)}</span></h3>
        {loggedNodes.length ? loggedNodes.map((item) => (
          <div className="diagnostic-log-group" key={item.id}>
            <strong>{item.name || item.id}</strong>
            {item.logs?.map((entry, index) => <code key={`${item.id}-${index}`}>{entry}</code>)}
          </div>
        )) : (
          <p className="diagnostic-log-empty">
            {failures.length
              ? "No additional runtime logs were captured. See the failure details above."
              : "No logs were emitted by this run."}
          </p>
        )}
      </section>
    </div>
  );
}

function ResultRows({ item, index, onNode, onViewGrid }: { item: RunNode; index: number; onNode: () => void; onViewGrid?: () => void }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr className="result-row" data-result-index={index} onClick={() => { setExpanded((open) => !open); onNode(); }}>
        <td><span className="result-name">{item.name || item.id}</span></td>
        <td><span className={`status-pill ${item.status === "error" ? "error" : "success"}`}><span className="status-indicator" />{item.status}</span></td>
        <td className="numeric-cell">{item.ms} ms</td>
        <td className="numeric-cell"><span className="row-count">{item.rows_in}</span><ChevronRight /><span className="row-count output">{item.rows_out}</span></td>
      </tr>
      {expanded && (
        <tr className="sample-row">
          <td colSpan={4}>
            <div className="sample-viewer">
              <div className="sample-viewer-heading"><Braces /><span>{item.error ? "Node error" : "Output sample"}</span><small>{item.error ? "ERROR" : `${item.sample?.length ?? 0} ROWS`}</small></div>
              <pre>{item.error || JSON.stringify(item.sample ?? [], null, 2)}</pre>
              {onViewGrid && (
                <div className="cell-details-actions" style={{ padding: "var(--space-3)" }}>
                  <Button
                    size="sm"
                    onClick={(event) => {
                      event.stopPropagation();
                      onViewGrid();
                    }}
                  >
                    <Eye /> View as grid
                  </Button>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function simulateRun(nodes: WorkflowNode[], edges: WorkflowEdge[], specs: Map<string, NodeSpec>): RunResult {
  const outputByNode: Record<string, SimulatedRow[]> = {};
  const results: RunNode[] = [];
  for (const node of nodes) {
    const spec = specs.get(node.type);
    if (!spec) continue;
    const parents = edges.filter((edge) => edge.target === node.id).map((edge) => outputByNode[edge.source] ?? []);
    let rows: SimulatedRow[] = parents[0] ?? [];
    const params = node.params;
    if (node.type === "manual_json") {
      const raw = params.data;
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      rows = Array.isArray(parsed) ? parsed.map((json) => ({ json: json && typeof json === "object" && !Array.isArray(json) ? json as Record<string, unknown> : { value: json } })) : [];
    } else if (node.type === "field_builder") {
      const fields = Array.isArray(params.fields)
        ? params.fields as { name?: string; type?: string; value?: unknown }[]
        : [];
      const json: Record<string, unknown> = {};
      for (const field of fields) {
        if (!field.name) continue;
        if (field.type === "number") {
          const number = Number(field.value);
          json[field.name] = Number.isFinite(number) ? number : null;
        } else if (field.type === "boolean") {
          json[field.name] = ["true", "1", "yes"].includes(String(field.value).toLowerCase());
        } else {
          json[field.name] = field.value ?? "";
        }
      }
      rows = [{ json }];
    } else if (node.type === "example_dataset") {
      rows = Array.from({ length: Math.min(Number(params.rows) || 0, 500) }, (_, index) => ({
        json: { company: ["Acme", "Northstar", "Bluebird"][index % 3], industry: ["software", "retail", "health"][index % 3] },
      }));
    } else if (node.type === "text_lines") {
      rows = String(params.text || "").split(params.delimiter === "comma" ? "," : params.delimiter === "tab" ? "\t" : "\n").filter(Boolean).map((value) => ({ json: { value: value.trim() } }));
    } else if (node.type === "limit") {
      rows = rows.slice(Number(params.offset) || 0, (Number(params.offset) || 0) + (Number(params.max) || 0));
    } else if (node.type === "sort") {
      rows = [...rows].sort((left, right) => String(left.json[ String(params.field) ] ?? "").localeCompare(String(right.json[String(params.field)] ?? "")));
      if (params.direction === "desc") rows.reverse();
    } else if (node.type === "set_fields") {
      const fields = Array.isArray(params.fields) ? params.fields as { name: string; value: unknown }[] : [];
      rows = rows.map((row) => {
        const json = { ...row.json };
        for (const field of fields) {
          if (field.name) json[field.name] = renderSimulatedValue(field.value, json);
        }
        return { ...row, json };
      });
    } else if (node.type === "filter") {
      const match = String(params.condition || "").match(/(?:\$json\.)?([A-Za-z_][\w-]*)/);
      rows = match ? rows.filter((row) => Boolean(row.json[match[1]])) : [];
    }
    outputByNode[node.id] = rows;
    results.push({
      id: node.id,
      name: spec.name,
      status: "success",
      rows_in: parents.reduce((total, list) => total + list.length, 0),
      rows_out: rows.length,
      ms: 0,
      input_samples: parents.map((list) => list.slice(0, 5).map((row) => row.json)),
      sample: rows.slice(0, 5).map((row) => row.json),
    });
  }
  return {
    run_id: "simulated",
    status: "success",
    ms: 0,
    nodes: results,
    output: outputByNode[nodes.at(-1)?.id ?? ""] ?? [],
    simulated: true,
    metrics: { llm_calls: 0, tokens_in: 0, tokens_out: 0 },
  };
}

function renderSimulatedValue(value: unknown, row: Record<string, unknown>): unknown {
  if (typeof value !== "string") return value;
  const expression = /\{\{\s*(?:\$json\.([A-Za-z_]\w*)|\$json\["([^"]+)"\]|([A-Za-z_]\w*))\s*\}\}/g;
  const exact = value.match(/^\{\{\s*(?:\$json\.([A-Za-z_]\w*)|\$json\["([^"]+)"\]|([A-Za-z_]\w*))\s*\}\}$/);
  const exactKey = exact?.[1] ?? exact?.[2] ?? exact?.[3];
  if (exact && exactKey !== undefined) return row[exactKey] ?? "";
  return value.replace(expression, (_match, dotKey: string | undefined, bracketKey: string | undefined, bareKey: string | undefined) =>
    String(row[dotKey ?? bracketKey ?? bareKey ?? ""] ?? ""),
  );
}
