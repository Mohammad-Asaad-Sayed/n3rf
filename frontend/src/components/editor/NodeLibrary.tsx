import { Braces, Plus, Search } from "lucide-react";
import type { CSSProperties } from "react";
import { groupIcons, groupOrder, groupTokens, type NodeSpec } from "../../lib/workflow";

export function NodeLibrary({
  catalog,
  search,
  onSearch,
  onAdd,
}: {
  catalog: NodeSpec[];
  search: string;
  onSearch: (search: string) => void;
  onAdd: (type: string) => void;
}) {
  const query = search.trim().toLocaleLowerCase();

  return (
    <>
      <label className="node-search">
        <Search />
        <input
          aria-label="Search nodes"
          placeholder="Find a node…"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
      <div className="node-groups">
        {groupOrder.map((group) => {
          const members = catalog.filter(
            (spec) =>
              spec.group === group &&
              (!query || `${spec.name} ${spec.description}`.toLocaleLowerCase().includes(query)),
          );
          if (!members.length) return null;
          const Icon = groupIcons[group as keyof typeof groupIcons] ?? Braces;
          return (
            <section className="node-group" key={group}>
              <h3><Icon />{group}<span /></h3>
              {members.map((spec) => {
                const NodeIcon = groupIcons[spec.group as keyof typeof groupIcons] ?? Braces;
                return (
                  <button
                    className="catalog-node"
                    key={spec.id}
                    title={spec.description}
                    style={{ "--node-color": groupTokens[spec.group] } as CSSProperties}
                    onClick={() => onAdd(spec.id)}
                  >
                    <span className="catalog-glyph"><NodeIcon /></span>
                    <span className="catalog-node-copy">
                      <span className="catalog-node-name">{spec.name}</span>
                      <span className="catalog-node-description">{spec.description}</span>
                    </span>
                    <Plus className="catalog-add" />
                  </button>
                );
              })}
            </section>
          );
        })}
      </div>
    </>
  );
}
