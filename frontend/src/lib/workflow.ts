import { Code2, Database, Layers3, Sparkles, type LucideIcon } from "lucide-react";

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

export const groupOrder = ["input", "transform", "ai", "code"];
export const groupTokens: Record<string, string> = {
  input: "var(--info)",
  transform: "var(--purple-light)",
  ai: "var(--alert)",
  code: "var(--warn)",
};
export const groupIcons: Record<string, LucideIcon> = {
  input: Database,
  transform: Layers3,
  ai: Sparkles,
  code: Code2,
};

export const fallbackCatalog: NodeSpec[] = [
  {
    id: "manual_json",
    name: "Manual JSON",
    group: "input",
    description: "Enter a JSON array of rows.",
    params: [{ key: "data", label: "Rows", type: "json", default: [] }],
  },
  {
    id: "csv_file",
    name: "CSV File",
    group: "input",
    description: "Parse CSV text into rows.",
    params: [
    { key: "text", label: "CSV content", type: "textarea", default: "" },
    { key: "delimiter", label: "Delimiter", type: "string", default: "," },
    { key: "header", label: "First row is header", type: "boolean", default: true },
    ],
  },
  {
    id: "field_builder",
    name: "Field Builder",
    group: "input",
    description: "Build one row from declared fields.",
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
    description: "Load a small sample dataset.",
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
    description: "Keep rows matching a condition.",
    params: [
      {
        key: "condition",
        label: "Condition",
        type: "string",
        default: "{{ $json.active }}",
        required: true,
        expression: true,
      },
      { key: "keep_empty", label: "Keep on error", type: "boolean", default: false },
    ],
  },
  {
    id: "set_fields",
    name: "Set Fields",
    group: "transform",
    description: "Set fields on every incoming row.",
    params: [{
      key: "fields",
      label: "Fields",
      type: "rows",
      default: [],
      hint: "Type @ to insert a field from each incoming row.",
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
    description: "Sort rows by a field.",
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
    description: "Keep a range of rows.",
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
