import {
  ArrowDown,
  ArrowUp,
  Copy,
  Eye,
  Play,
  Plus,
  Search,
  Settings2,
  Trash2,
  LoaderCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "../ui/button";

export type GridCellSelection = {
  rowIndex: number;
  column: string;
  value: string;
  row: Record<string, unknown>;
};

function recordsOf(rows: unknown[]): Record<string, unknown>[] {
  return rows.map((row) =>
    row !== null && typeof row === "object" && !Array.isArray(row)
      ? (row as Record<string, unknown>)
      : { value: row },
  );
}

function cellText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export function DataGrid({
  rows,
  label,
  partial,
  programmed,
  executingColumn,
  executingCell,
  selectedCell,
  onCellSelect,
  onCellRun,
  onColumnEdit,
  onColumnRun,
  onAddColumn,
}: {
  rows: unknown[];
  label: string;
  partial?: boolean;
  programmed: Record<string, string>;
  executingColumn?: string | null;
  executingCell?: string | null;
  selectedCell: GridCellSelection | null;
  onCellSelect: (cell: GridCellSelection) => void;
  onCellRun: (rowIndex: number, column: string) => void;
  onColumnEdit: (column: string) => void;
  onColumnRun: (column: string) => void;
  onAddColumn: () => void;
}) {
  const records = useMemo(() => recordsOf(rows), [rows]);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [search, setSearch] = useState("");
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState("");

  const columns = useMemo(
    () => [...new Set(records.flatMap((row) => Object.keys(row)))],
    [records],
  );
  const visibleColumns = columns.filter((column) => !hidden.has(column));

  const filtered = useMemo(() => {
    let indexed = records.map((row, index) => ({ row, index }));
    const query = search.trim().toLocaleLowerCase();
    if (query) {
      indexed = indexed.filter(({ row }) =>
        visibleColumns.some((column) =>
          cellText(row[column]).toLocaleLowerCase().includes(query),
        ),
      );
    }
    if (sortColumn) {
      indexed = [...indexed].sort((a, b) => {
        const cmp = cellText(a.row[sortColumn]).localeCompare(cellText(b.row[sortColumn]));
        return sortDir === "asc" ? cmp : -cmp;
      });
    }
    return indexed;
  }, [records, search, visibleColumns, sortColumn, sortDir]);

  function toggleSort(column: string) {
    if (sortColumn !== column) {
      setSortColumn(column);
      setSortDir("asc");
    } else {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"));
    }
  }

  function hideColumn(column: string) {
    setHidden((current) => {
      const next = new Set(current);
      next.add(column);
      return next;
    });
  }

  function copyCell(rowIndex: number, column: string) {
    const text = cellText(records[rowIndex]?.[column]);
    void navigator.clipboard.writeText(text).then(
      () => setCopied(`${rowIndex}-${column}`),
      () => setCopied(""),
    );
    window.setTimeout(() => setCopied(""), 1200);
  }

  if (!records.length) {
    return (
      <div className="empty-results output-empty">
        <Eye />
        <strong>No rows in this grid</strong>
        <span>Run the workflow to fill this grid.</span>
      </div>
    );
  }

  return (
    <div className="data-grid-wrap">
      <div className="data-grid-toolbar">
        <span className="data-grid-title">{label}</span>
        {partial && <span className="grid-badge warn">SAMPLE — RUN FULL WORKFLOW FOR ALL ROWS</span>}
        {executingColumn && (
          <span className="data-grid-progress">
            <LoaderCircle className="spin" /> Enriching {executingColumn}…
          </span>
        )}
        <label className="data-grid-search">
          <Search />
          <input
            aria-label="Filter rows"
            placeholder="Filter rows"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <span className="data-grid-count">
          {filtered.length}/{records.length} rows · {visibleColumns.length} cols
          {Object.keys(programmed).length ? ` · ${Object.keys(programmed).length} programmed` : ""}
        </span>
        <Button size="sm" onClick={onAddColumn}>
          <Plus /> Add column
        </Button>
      </div>
      {hidden.size > 0 && (
        <div className="data-grid-hiddenbar">
          <span>Hidden: {[...hidden].join(", ")}</span>
          <button type="button" onClick={() => setHidden(new Set())}>Show all</button>
        </div>
      )}
      <div className="results-scroll data-grid-scroll">
        <table className="results-table output-table data-grid-table">
          <thead>
            <tr>
              <th className="output-index-heading">#</th>
              {visibleColumns.map((column) => {
                const sorted = sortColumn === column;
                const executing = executingColumn === column;
                return (
                  <th key={column} className="data-grid-th">
                    <span className="data-grid-th-inner">
                      <button
                        type="button"
                        className="data-grid-sort"
                        onClick={() => toggleSort(column)}
                        aria-label={`Sort by ${column}`}
                      >
                        <span className="data-grid-th-name">{column}</span>
                        {sorted &&
                          (sortDir === "asc" ? (
                            <ArrowUp className="grid-sort-icon" />
                          ) : (
                            <ArrowDown className="grid-sort-icon" />
                          ))}
                      </button>
                      {programmed[column] && <span className="grid-badge">f(x)</span>}
                      <span className="data-grid-th-actions">
                        <button
                          type="button"
                          className="grid-icon-btn"
                          aria-label={`Edit column ${column}`}
                          title="Program this column (creates a node)"
                          onClick={() => onColumnEdit(column)}
                        >
                          <Settings2 />
                        </button>
                        <button
                          type="button"
                          className="grid-icon-btn"
                          aria-label={`Run column ${column}`}
                          title="Run the node that produces this column"
                          disabled={!programmed[column] || executingColumn != null}
                          onClick={() => onColumnRun(column)}
                        >
                          {executing ? <LoaderCircle className="spin" /> : <Play />}
                        </button>
                        <button
                          type="button"
                          className="grid-icon-btn"
                          aria-label={`Hide column ${column}`}
                          title="Hide column (view only)"
                          onClick={() => hideColumn(column)}
                        >
                          <Trash2 />
                        </button>
                      </span>
                    </span>
                    {executing && <span className="grid-progress-line" />}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 500).map(({ row, index }) => (
              <tr key={index} className="data-grid-row">
                <td className="output-index">{index + 1}</td>
                {visibleColumns.map((column) => {
                  const value = row[column];
                  const text = cellText(value);
                  const cellKey = `${index}-${column}`;
                  const isSelected =
                    selectedCell?.rowIndex === index && selectedCell?.column === column;
                  const isExecutingCell = executingCell === cellKey;
                  const empty = value === null || value === undefined || value === "";
                  return (
                    <td
                      key={column}
                      className={`data-grid-cell group/cell ${isSelected ? "selected-cell" : ""}`}
                      title={text}
                      onClick={() => {
                        const rec = records[index];
                        if (rec) onCellSelect({ rowIndex: index, column, value: text, row: rec });
                      }}
                    >
                      <span className="data-grid-cell-inner">
                        {isExecutingCell ? (
                          <span className="grid-running">
                            <LoaderCircle className="spin" /> running…
                          </span>
                        ) : empty ? (
                          <span className="output-null">—</span>
                        ) : (
                          text
                        )}
                        <span className="data-grid-cell-actions">
                          {programmed[column] && !isExecutingCell && (
                            <button
                              type="button"
                              className="grid-icon-btn"
                              aria-label={`Run ${column} for row ${index + 1}`}
                              title="Run this column (batch — full upstream node)"
                              onClick={(event) => {
                                event.stopPropagation();
                                onCellRun(index, column);
                              }}
                            >
                              <Play />
                            </button>
                          )}
                          <button
                            type="button"
                            className="grid-icon-btn"
                            aria-label={`Copy ${column} row ${index + 1}`}
                            title={copied === cellKey ? "Copied" : "Copy cell"}
                            onClick={(event) => {
                              event.stopPropagation();
                              copyCell(index, column);
                            }}
                          >
                            {copied === cellKey ? <Eye /> : <Copy />}
                          </button>
                        </span>
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 500 && (
          <p className="data-grid-showing">
            Showing first 500 of {filtered.length} rows — filter or narrow the workflow to see more.
          </p>
        )}
      </div>
      <div className="data-grid-footer">
        {records.length} rows · {columns.length} columns · {Object.keys(programmed).length} programmed
        {partial ? " · sample only" : ""}
      </div>
    </div>
  );
}
