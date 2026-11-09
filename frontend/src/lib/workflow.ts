import { Code2, Database, Layers3, Search, Sparkles, type LucideIcon } from "lucide-react";

/**
 * Micro-SaaS split hosting (Bricks-style): the static frontend may sit on a
 * CDN while the API runs elsewhere. Same-origin by default (`""`), override
 * with VITE_API_URL only (e.g. https://api.n3rf.example). Keys never travel
 * in URLs or localStorage — the backend reads them from its own environment.
 */
const viteEnv =
  (import.meta as unknown as { env?: Record<string, string> }).env ?? {};
export const API_BASE = (viteEnv.VITE_API_URL ?? "").replace(/\/$/, "");

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, init);
}

export type ParamColumn = {
  key: string;
  label: string;
  type?: string;
  options?: string[];
  default?: unknown;
  expression?: boolean;
};

export type ParamSpec = {
  key: string;
  type: string;
  label: string;
  default?: unknown;
  options?: string[];
  required?: boolean;
  unit?: string;
  hint?: string;
  expression?: boolean;
  columns?: ParamColumn[];
  show_if?: { param: string; in: unknown[] };
};

export type NodeSpec = {
  id: string;
  name: string;
  group: string;
  description: string;
  inputs?: number;
  params: ParamSpec[];
};

export type WorkflowNode = {
  id: string;
  type: string;
  params: Record<string, unknown>;
  position: { x: number; y: number };
};

export type WorkflowEdge = { source: string; target: string; target_input?: number };
export type SimulatedRow = { json: Record<string, unknown>; meta?: Record<string, unknown> };
export type RunNode = {
  id: string;
  name: string;
  status: string;
  rows_in: number;
  rows_out: number;
  ms: number;
  input_samples?: unknown[][];
  sample?: unknown[];
  error?: string;
  logs?: string[];
};
export type RunResult = {
  run_id: string;
  status: string;
  ms: number;
  nodes: RunNode[];
  output: unknown[];
  simulated?: boolean;
  metrics?: { llm_calls?: number; tokens_in?: number; tokens_out?: number };
};
export type SavedWorkflow = { id: string; name: string };
export type PaneWidths = { palette: number; inspector: number; results: number };

export const groupOrder = ["input", "transform", "search", "ai", "code"];
export const groupTokens: Record<string, string> = {
  input: "var(--info)",
  transform: "var(--purple-light)",
  search: "var(--accent-dim)",
  ai: "var(--alert)",
  code: "var(--warn)",
};
export const groupIcons: Record<string, LucideIcon> = {
  input: Database,
  transform: Layers3,
  search: Search,
  ai: Sparkles,
  code: Code2,
};

export const fallbackCatalog: NodeSpec[] = [
  {
    id: "manual_json",
    name: "Manual JSON",
    group: "input",
    description: "Start from a JSON list you type. One list item becomes one row.",
    params: [{ key: "data", label: "Rows", type: "json", default: [{ company: "Acme", website: "https://acme.com" }], required: true, hint: 'JSON array. Example: [{"company": "Acme"}]' }],
  },
  {
    id: "csv_file",
    name: "CSV File",
    group: "input",
    description: "Start from CSV. The header row becomes field names.",
    params: [
    { key: "text", label: "CSV content", type: "textarea", default: "company,website\nAcme,https://acme.com", hint: "Paste CSV. First row becomes field names." },
    { key: "delimiter", label: "Delimiter", type: "string", default: "," },
    { key: "header", label: "First row is header", type: "boolean", default: true },
    ],
  },
  {
    id: "field_builder",
    name: "Field Builder",
    group: "input",
    description: "Build one row from fields you name.",
    params: [{
      key: "fields",
      label: "Fields",
      type: "rows",
      default: [],
      columns: [
        { key: "name", label: "Name", type: "string" },
        { key: "type", label: "Type", type: "select", options: ["string", "number", "boolean"] },
        { key: "value", label: "Value", type: "string" },
      ],
    }],
  },
  {
    id: "example_dataset",
    name: "Example Dataset",
    group: "input",
    description: "Start from a sample list so you can try the builder.",
    params: [
      {
        key: "dataset",
        label: "Dataset",
        type: "select",
        options: ["companies", "people", "products"],
        default: "companies",
      },
      { key: "rows", label: "Row count", type: "number", default: 3 },
    ],
  },
  {
    id: "filter",
    name: "Filter",
    group: "transform",
    description: "Keep only rows that match a condition. Drops the rest.",
    params: [
      {
        key: "condition",
        label: "Condition",
        type: "string",
        default: "active == true",
        required: true,
        expression: true,
        hint: 'Example: "score >= 5". @ picks a field.',
      },
      { key: "keep_empty", label: "Keep on error", type: "boolean", default: false },
    ],
  },
  {
    id: "set_fields",
    name: "Set Fields",
    group: "transform",
    description: "Add or overwrite fields on every row. Use @ to copy another field.",
    params: [{
      key: "fields",
      label: "Fields",
      type: "rows",
      default: [{ name: "label", value: "{{company}} review" }],
      hint: "@ picks a field. Example value: {{company}} review",
      columns: [
        { key: "name", label: "Name", type: "string" },
        { key: "value", label: "Value", type: "string", expression: true },
      ],
    }],
  },
  {
    id: "sort",
    name: "Sort",
    group: "transform",
    description: "Order rows by a field, smallest first or largest first.",
    params: [
      { key: "field", label: "Field", type: "string", default: "company", required: true },
      {
        key: "direction",
        label: "Direction",
        type: "select",
        options: ["asc", "desc"],
        default: "asc",
      },
    ],
  },
  {
    id: "limit",
    name: "Limit",
    group: "transform",
    description: "Keep the first N rows, or skip N then keep M.",
    params: [
      { key: "max", label: "Maximum rows", type: "number", default: 100 },
      { key: "offset", label: "Offset", type: "number", default: 0 },
    ],
  },
];

export function readPaneWidths(): PaneWidths {
  try {
    const stored = JSON.parse(localStorage.getItem("n3rf-pane-widths") || "{}");
    return {
      palette: Math.max(190, Math.min(360, Number(stored.palette) || 252)),
      inspector: Math.max(280, Math.min(480, Number(stored.inspector) || 352)),
      results: Math.max(140, Math.min(420, Number(stored.results) || 212)),
    };
  } catch {
    return { palette: 252, inspector: 352, results: 212 };
  }
}

export function defaultParams(spec: NodeSpec) {
  return Object.fromEntries(
    spec.params.map((param) => [
      param.key,
      structuredClone(param.default ?? (param.type === "rows" ? [] : "")),
    ]),
  );
}

export function formatValue(value: unknown) {
  if (typeof value === "string") return value;
  if (value === undefined || value === null) return "";
  return JSON.stringify(value);
}

export function isVisible(param: ParamSpec, values: Record<string, unknown>) {
  return !param.show_if || param.show_if.in.includes(values[param.show_if.param]);
}

/** Params worth previewing on the canvas card: required/expression first, stable order. */
export function summaryParams(params: ParamSpec[], limit = 2): ParamSpec[] {
  const rank = (param: ParamSpec) =>
    (param.required ? 0 : 2) + (param.expression ? 0 : 1);
  return [...params].sort((a, b) => rank(a) - rank(b)).slice(0, limit);
}

/** Tuning knobs that rarely change — collapsed under Advanced in the inspector. */
export const advancedParamKeys = new Set([
  "api_key",
  "base_url",
  "api_key_env",
  "concurrency",
  "max_output_rows",
  "on_error",
  "max_results",
  "num_results",
  "search_depth",
  "extract_depth",
  "include_answer",
  "include_text",
  "timeout",
  "type",
  "format",
  "keep_empty",
  "numeric",
]);

export function partitionParams(params: ParamSpec[]): { core: ParamSpec[]; advanced: ParamSpec[] } {
  const core: ParamSpec[] = [];
  const advanced: ParamSpec[] = [];
  for (const param of params) {
    if (param.required || !advancedParamKeys.has(param.key)) core.push(param);
    else advanced.push(param);
  }
  return { core, advanced };
}

/* ------------------------------------------------------------------ */
/* Non-techie helpers — generic only, keyed by Param.type / Param.key.  */
/* No per-node forms: every helper below works for any node whose       */
/* params use the same type or key.                                       */
/* ------------------------------------------------------------------ */

/** String params whose value is a plain column name (not text). Dropdown, not typing. */
export const FIELD_NAME_KEYS = new Set([
  "field",
  "group_by",
  "key",
  "score_field",
  "from",
]);

/** Shown before any run exists, so column pickers and chips are never blank. */
export const FALLBACK_FIELD_NAMES = [
  "company",
  "website",
  "name",
  "title",
  "industry",
  "score",
  "price",
  "text",
  "value",
];

/**
 * Altclay smart columns: put identifying columns first (company/domain/name…)
 * so dropdowns and chips lead with what a non-techie actually wants.
 */
const SMART_PATTERNS = [
  /^(company|organization|org|business|brand)(\s|_|-|$)/i,
  /^(domain|website|url|site|web)(\s|_|-|$)/i,
  /^(name|full\s*name|person\s*name)$/i,
  /^(email|e-mail)/i,
  /^(linkedin|twitter|x|github)/i,
  /^(ticker|symbol|stock)/i,
  /^(university|school|college|institution)/i,
  /^(country|city|state|location|address)$/i,
  /^(product|app|service|tool)/i,
];

export function detectSmartColumns(columns: string[]): string[] {
  const matches = columns.filter((col) =>
    SMART_PATTERNS.some((pattern) => pattern.test(col.trim())),
  );
  return matches.length ? matches : columns.length ? [columns[0]] : [];
}

/** Altclay output derivation: "Find the CEO name, funding raised" → columns. */
export function detectOutputColumns(description: string): { key: string; label: string }[] {
  if (!description.trim()) return [];
  const cleaned = description
    .replace(/find\s+(out\s+)?(the\s+)?/gi, "")
    .replace(/get\s+(me\s+)?(the\s+)?/gi, "")
    .replace(/look\s+up\s+(the\s+)?/gi, "")
    .replace(/research\s+(the\s+)?/gi, "")
    .replace(/for\s+each\s+\w+/gi, "")
    .replace(/of\s+each\s+\w+/gi, "")
    .replace(/for\s+every\s+\w+/gi, "")
    .replace(/per\s+\w+/gi, "")
    .trim();
  const parts = cleaned
    .split(/,\s*|\s+and\s+/i)
    .map((part) => part.replace(/^(the|their|its|a|an)\s+/i, "").trim())
    .filter((part) => part.length > 1 && part.length < 60 && !part.includes("."));
  if (!parts.length) return [];
  return parts
    .map((label) => ({
      key: label.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, ""),
      label,
    }))
    .filter((column) => column.key.length > 0);
}

export function fallbackExpressionFields(): { label: string; expression: string }[] {
  return FALLBACK_FIELD_NAMES.map((name) => ({
    label: name,
    expression: `{{${name}}}`,
  }));
}

/** "website_url" -> "Website url" — readable column names without syntax. */
export function humanizeFieldLabel(label: string): string {
  const words = label.replace(/[_\-]+/g, " ").trim();
  if (!words) return label;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const OPTION_HINTS: Record<string, string> = {
  per_input: "One result per input row",
  expand_arrays: "Split lists into separate rows",
  error_item: "Show an error marker on that row",
  skip: "Skip the failing row",
  fail: "Stop the whole run",
  asc: "Smallest first",
  desc: "Largest first",
  line: "One value per line",
  comma: "Comma separated",
  tab: "Tab separated",
  append: "Stack both lists together",
  merge_by_key: "Join rows that share a column",
  inner: "Only rows in both lists",
  left_only: "Only rows in the first list",
  right_only: "Only rows in the second list",
  first: "Keep the first repeat",
  last: "Keep the last repeat",
  basic: "Fast, light search",
  advanced: "Deep, slow search",
  fast: "Fast extraction",
  auto: "Automatic",
  markdown: "Clean text format",
  html: "Raw web page",
  text: "Plain text",
  csv: "Spreadsheet rows",
  json: "Structured data",
  count: "Count rows",
  sum: "Add numbers",
  avg: "Average",
  min: "Smallest value",
  max: "Largest value",
  GET: "Read from a web address",
  POST: "Send to a web address",
  PUT: "Update on a web address",
  PATCH: "Patch a web address",
  DELETE: "Remove on a web address",
  string: "Text value",
  number: "Numeric value",
  boolean: "True or false",
  companies: "Sample companies list",
  people: "Sample people list",
  products: "Sample products list",
  openai: "OpenAI API",
  groq: "Groq — fast Llama",
  gemini: "Google Gemini — free tier",
  openrouter: "OpenRouter — free models",
  mistral: "Mistral",
  huggingface: "Hugging Face",
  ollama: "Ollama — local, no key, $0",
  cloudflare: "Cloudflare Workers AI",
  custom: "Custom OpenAI-compatible",
};

export function humanizeOption(option: string): string {
  const hint = OPTION_HINTS[option];
  const base = option.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return hint ? `${base} — ${hint}` : base;
}

/** Plain-language labels for plumbing params a non-techie cannot parse. */
const PLAIN_LABELS: Record<string, string> = {
  api_key: "API key (paste — run only)",
  api_key_env: "Key name (no secret here)",
  base_url: "Model website address",
  account_id: "Account ID",
  embedding_model: "Embedding model",
  concurrency: "Rows at once",
  max_output_rows: "Max rows out",
  on_error: "If a row fails",
  max_results: "Results per row",
  num_results: "Results per row",
  keep_empty: "On error, keep the row",
  numeric: "Compare as numbers",
  include_answer: "Include answer text",
  include_text: "Include full text",
  search_depth: "Search depth",
  extract_depth: "Read depth",
  timeout: "Time limit",
  schema: "What the model returns",
  code: "Your custom step",
  data: "Your rows",
};

export function plainParamLabel(param: ParamSpec): string {
  return PLAIN_LABELS[param.key] ?? param.label;
}

/**
 * Bricks-style provider presets. Mirrors the backend PROVIDERS table so
 * picking a provider in the inspector fills in model + key name (generic,
 * keyed by the `provider` param — no per-node form).
 */
export const PROVIDER_PRESETS: Record<string, { model: string; api_key_env: string; base_url: string }> = {
  openai: { model: "gpt-4o-mini", api_key_env: "OPENAI_API_KEY", base_url: "https://api.openai.com/v1" },
  groq: { model: "gpt-oss-120b", api_key_env: "GROQ_API_KEY", base_url: "https://api.groq.com/openai/v1" },
  gemini: { model: "gemini-2.5-flash", api_key_env: "GEMINI_API_KEY", base_url: "https://generativelanguage.googleapis.com/v1beta/openai/" },
  openrouter: { model: "meta-llama/llama-3.3-70b-instruct:free", api_key_env: "OPENROUTER_API_KEY", base_url: "https://openrouter.ai/api/v1" },
  mistral: { model: "mistral-small-latest", api_key_env: "MISTRAL_API_KEY", base_url: "https://api.mistral.ai/v1" },
  huggingface: { model: "mistralai/Mistral-7B-Instruct-v0.3", api_key_env: "HUGGINGFACE_API_KEY", base_url: "https://router.huggingface.co/v1" },
  ollama: { model: "llama3.1:8b", api_key_env: "", base_url: "http://localhost:11434/v1" },
  cloudflare: { model: "@cf/meta/llama-3.3-70b-instruct", api_key_env: "CLOUDFLARE_API_TOKEN", base_url: "" },
  custom: { model: "gpt-4o-mini", api_key_env: "OPENAI_API_KEY", base_url: "https://api.openai.com/v1" },
};

const FIELD_TOKEN =
  /\{\{\s*(\$json(?:\.[\w$]+|\[[^\]]+\])*|[A-Za-z_][\w$]*(?:[ \t\-][\w$]+)*(?:\.[\w$]+(?:[ \t\-][\w$]+)*|\[[^\]]+\])*)\s*\}\}|\$json(?:\.[\w$]+|\[[^\]]+\])*/g;

export type ExpressionToken =
  | { kind: "text"; text: string }
  | { kind: "field"; label: string; expression: string };

function labelFromPath(path: string): string {
  return path
    .replace(/^\$json\.?/, "")
    .replace(/\[["']([^"']+)["']\]/g, ".$1")
    .replace(/^\./, "");
}

export function parseExpressionTokens(text: string): ExpressionToken[] {
  const tokens: ExpressionToken[] = [];
  let last = 0;
  for (const match of text.matchAll(FIELD_TOKEN)) {
    const start = match.index ?? 0;
    if (start > last) tokens.push({ kind: "text", text: text.slice(last, start) });
    const expression = match[0];
    const path = match[1] ?? match[0];
    tokens.push({ kind: "field", label: labelFromPath(path), expression });
    last = start + expression.length;
  }
  if (last < text.length) tokens.push({ kind: "text", text: text.slice(last) });
  return tokens;
}

/** True when the whole value is one column pick like {{website}}. */
export function isSingleFieldExpression(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  const tokens = parseExpressionTokens(trimmed);
  return tokens.length === 1 && tokens[0].kind === "field";
}

export function fieldNameFromExpression(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (isSingleFieldExpression(trimmed)) {
    const tokens = parseExpressionTokens(trimmed);
    if (tokens[0].kind === "field") return tokens[0].label;
    return null;
  }
  return null;
}

export function bareFieldName(label: string): string {
  return label.split(".")[0];
}

/** "Company Name" -> "company_name". Mirrors the backend normalization. */
export function toSnakeCase(name: string): string {
  const cleaned = name
    .trim()
    .replace(/[^0-9a-zA-Z_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  if (cleaned && /^[0-9]/.test(cleaned)) return `field_${cleaned}`;
  return cleaned;
}

export function normalizeHeaders(headers: string[]): string[] {
  const seen = new Set<string>();
  return headers.map((raw, index) => {
    const base = toSnakeCase(raw) || `column_${index + 1}`;
    let candidate = base;
    let suffix = 2;
    while (seen.has(candidate)) {
      candidate = `${base}_${suffix}`;
      suffix += 1;
    }
    seen.add(candidate);
    return candidate;
  });
}

function lookupPath(row: Record<string, unknown>, label: string): unknown {
  let current: unknown = row;
  for (const part of label.split(".")) {
    const wanted = toSnakeCase(part);
    if (current && typeof current === "object" && !Array.isArray(current)) {
      const record = current as Record<string, unknown>;
      if (part in record) {
        current = record[part];
        continue;
      }
      const match = Object.keys(record).find((key) => toSnakeCase(key) === wanted);
      if (match === undefined) return undefined;
      current = record[match];
    } else {
      return undefined;
    }
  }
  return current;
}

function renderValue(value: unknown): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** "Will say: Acme funding" — substitute a real sample row so syntax is never read. */
export function previewWithRow(text: string, row: Record<string, unknown> | null): string {
  if (!row) {
    return parseExpressionTokens(text)
      .map((token) => (token.kind === "field" ? `(${humanizeFieldLabel(token.label)})` : token.text))
      .join("");
  }
  return parseExpressionTokens(text)
    .map((token) =>
      token.kind === "field" ? renderValue(lookupPath(row, token.label)) : token.text,
    )
    .join("");
}

/** Render hint syntax ({{x}}) as plain column names. */
export function plainHint(hint: string): string {
  return previewWithRow(hint, null);
}

export type ExpressionTemplate = { label: string; make: (fieldExpr: string) => string };
/** Starting points a non-techie can pick — stored values stay valid backend syntax. */
export const EXPRESSION_TEMPLATES: Record<string, ExpressionTemplate[]> = {
  query: [
    { label: "Search for [column] + funding", make: (f) => `${f} funding` },
    { label: "Latest news about [column]", make: (f) => `${f} latest news` },
    { label: "Search only for [column]", make: (f) => `${f}` },
  ],
  url: [
    { label: "Open the [column] website", make: (f) => `${f}` },
    { label: "Open the page link in [column]", make: (f) => `${f}` },
  ],
  prompt: [
    {
      label: "Summarize [column] in one line",
      make: (f) => `Summarize ${f} in one line. Return JSON like {"summary": "..."}.`,
    },
    {
      label: "Extract key facts about [column]",
      make: (f) => `Extract the key facts about ${f}. Return JSON like {"facts": "..."}.`,
    },
    {
      label: "Describe [column] briefly",
      make: (f) => `Describe ${f} in two short sentences. Return JSON like {"summary": "..."}.`,
    },
  ],
  criterion: [
    { label: "Simply: [column]", make: (f) => `${f}` },
    { label: "Keep rows where [column] mentions software", make: (f) => `Keep rows where ${f} mentions software.` },
    { label: "Keep rows where [column] is a company", make: (f) => `Keep rows where ${f} is a company.` },
  ],
};

export function templatesFor(key: string): ExpressionTemplate[] {
  return EXPRESSION_TEMPLATES[key] ?? [];
}

export const CONDITION_OPERATORS = [
  { value: "==", label: "is" },
  { value: "!=", label: "is not" },
  { value: ">", label: "is greater than" },
  { value: "<", label: "is less than" },
  { value: ">=", label: "is at least" },
  { value: "<=", label: "is at most" },
] as const;

const CONDITION_RE =
  /^(?:\$json\.|json\.|)([\w$]+)\s*(==|!=|>=|<=|>|<)\s*([\s\S]+)$/;

export function parseCondition(text: string): { field: string; operator: string; value: string } | null {
  const match = text.trim().match(CONDITION_RE);
  if (!match) return null;
  const rawValue = match[3].trim();
  const unquoted =
    (rawValue.startsWith('"') && rawValue.endsWith('"')) ||
    (rawValue.startsWith("'") && rawValue.endsWith("'"))
      ? rawValue.slice(1, -1)
      : rawValue;
  return { field: match[1], operator: match[2], value: unquoted };
}

export function buildCondition(field: string, operator: string, value: string): string {
  const trimmed = value.trim();
  const numeric = /^-?\d+(\.\d+)?$/.test(trimmed);
  const literal =
    numeric || ["true", "false", "null"].includes(trimmed.toLowerCase())
      ? trimmed
      : `"${trimmed.replace(/"/g, '\\"')}"`;
  return `${field} ${operator} ${literal}`;
}

/** Suggestions that fill model / key inputs without the user memorizing names. */
export const MODEL_SUGGESTIONS = [
  "gpt-4o-mini",
  "gpt-4o",
  "gemini-2.5-flash",
  "gpt-oss-120b",
  "meta-llama/llama-3.3-70b-instruct:free",
  "mistral-small-latest",
  "mistralai/Mistral-7B-Instruct-v0.3",
  "llama3.1:8b",
  "@cf/meta/llama-3.3-70b-instruct",
];

export const ENV_SUGGESTIONS = [
  "OPENAI_API_KEY",
  "GROQ_API_KEY",
  "GEMINI_API_KEY",
  "OPENROUTER_API_KEY",
  "MISTRAL_API_KEY",
  "HUGGINGFACE_API_KEY",
  "TAVILY_API_KEY",
  "EXA_API_KEY",
  "CLOUDFLARE_API_TOKEN",
];

export const SCHEMA_PRESETS: { label: string; value: Record<string, unknown> }[] = [
  { label: "Let the model choose (recommended)", value: {} },
  {
    label: "One summary text",
    value: {
      type: "object",
      properties: { summary: { type: "string" } },
      required: ["summary"],
    },
  },
  {
    label: "Company + website",
    value: {
      type: "object",
      properties: { company: { type: "string" }, website: { type: "string" } },
      required: ["company"],
    },
  },
  {
    label: "Contact info",
    value: {
      type: "object",
      properties: { email: { type: "string" }, phone: { type: "string" } },
    },
  },
];

/** Small, safe starting points for the Code node — applied as plain templates. */
export const CODE_PRESETS: { label: string; value: string }[] = [
  { label: "Keep rows as they are", value: "return items" },
  {
    label: "Make the company name uppercase",
    value:
      'return [{"json": {**row["json"], "company": str(row["json"].get("company", "")).upper()}, "meta": row["meta"]} for row in items]',
  },
  {
    label: "Add a row number",
    value:
      'return [{"json": {**row["json"], "row_number": index + 1}, "meta": row["meta"]} for index, row in enumerate(items)]',
  },
];

export function schemaPresetLabel(value: unknown): string {
  const found = SCHEMA_PRESETS.find(
    (preset) => JSON.stringify(preset.value) === JSON.stringify(value),
  );
  return found ? found.label : "Custom (edit JSON directly)";
}

/** Canvas-card summary that never shows raw JSON to a non-techie. */
export function summaryLabel(param: ParamSpec, value: unknown): string {
  // Never echo a pasted secret on the canvas — show that one is set, nothing more.
  if (param.key === "api_key" || param.type === "password") {
    return value ? "Set (run only)" : "—";
  }
  if (param.type === "json") {
    if (Array.isArray(value)) return `${value.length} ${value.length === 1 ? "row" : "rows"}`;
    if (value && typeof value === "object") {
      if (Object.keys(value as Record<string, unknown>).length === 0) return "Default";
      return "(custom)";
    }
    return value === "" || value === null ? "—" : "(custom)";
  }
  if (param.type === "rows") {
    const rows = Array.isArray(value) ? value : [];
    return rows.length ? `${rows.length} ${rows.length === 1 ? "row" : "rows"}` : "—";
  }
  if (param.type === "boolean") return value ? "On" : "Off";
  if (param.type === "select" && typeof value === "string") {
    const hint = OPTION_HINTS[value];
    return hint ? hint.split(" — ")[0] : value.replace(/_/g, " ");
  }
  if (param.type === "code") return value === "return items" ? "Keep rows" : "(custom)";
  if (param.expression && typeof value === "string") {
    const preview = previewWithRow(value, null).trim();
    if (preview.length > 34) return `${preview.slice(0, 34)}…`;
    return preview || "—";
  }
  return formatValue(value).slice(0, 34) || "—";
}
