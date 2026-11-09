import { Copy, Eye, Play, X } from "lucide-react";
import { Button } from "../ui/button";

export type CellDetailsData = {
  rowIndex: number;
  column: string;
  value: string;
  row: Record<string, unknown>;
  producingNode?: string;
  producingNodeId?: string;
};

function cellType(value: string): string {
  if (!value) return "Empty";
  if (/^-?\d+(\.\d+)?$/.test(value.trim())) return "Number";
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "Email-like";
  if (/^https?:\/\/.+\..+/.test(value)) return "URL-like";
  if (/^(true|false)$/i.test(value)) return "Boolean";
  if (value.trimStart().startsWith("{") || value.trimStart().startsWith("[")) return "JSON-like";
  return "Text";
}

export function CellDetails({
  cell,
  onClose,
  onEditColumn,
  onRunColumn,
}: {
  cell: CellDetailsData;
  onClose: () => void;
  onEditColumn: (column: string) => void;
  onRunColumn: (column: string) => void;
}) {
  return (
    <div className="cell-details">
      <div className="cell-details-heading">
        <span className="eyebrow">Cell · Row {cell.rowIndex + 1} · {cell.column}</span>
        <Button variant="icon" size="icon" aria-label="Close cell details" onClick={onClose}>
          <X />
        </Button>
      </div>
      <div className="cell-details-grid">
        <div><span className="field-label">Row</span><strong>{cell.rowIndex + 1}</strong></div>
        <div><span className="field-label">Column</span><strong>{cell.column}</strong></div>
      </div>
      <div className="cell-details-block">
        <span className="field-label">Content</span>
        <div className="cell-details-value">
          {cell.value ? cell.value : <span className="output-null">— empty —</span>}
        </div>
      </div>
      <div className="cell-details-grid">
        <div><span className="field-label">Length</span><strong>{cell.value.length} chars</strong></div>
        <div><span className="field-label">Type</span><strong>{cellType(cell.value)}</strong></div>
      </div>
      <div className="cell-details-block">
        <span className="field-label">Produced by</span>
        <p className="cell-details-note">
          {cell.producingNode
            ? `${cell.producingNode} (column added by this node)`
            : "Present in the workflow input — no node produces this column."}
        </p>
      </div>
      <div className="cell-details-block">
        <span className="field-label">Full row</span>
        <pre>{JSON.stringify(cell.row, null, 2)}</pre>
      </div>
      <div className="cell-details-actions">
        <Button
          size="sm"
          onClick={() => {
            void navigator.clipboard.writeText(cell.value);
          }}
        >
          <Copy /> Copy
        </Button>
        {cell.producingNodeId && (
          <>
            <Button size="sm" onClick={() => onEditColumn(cell.column)}>
              <Eye /> Edit column
            </Button>
            <Button size="sm" variant="primary" onClick={() => onRunColumn(cell.column)}>
              <Play /> Run column
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
