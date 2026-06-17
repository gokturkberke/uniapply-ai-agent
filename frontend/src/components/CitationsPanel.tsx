import type { Citation } from "../api/types";

export function CitationsPanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return null;
  }
  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Sources
      </h3>
      <ul className="mt-2 space-y-1">
        {citations.map((citation, index) => (
          <li key={`${citation.source_id}-${index}`} className="text-sm">
            <span className="font-mono text-xs text-slate-900">
              {citation.source_id}
            </span>
            {citation.heading_path.length > 0 ? (
              <span className="text-slate-500">
                {" "}
                &rsaquo; {citation.heading_path.join(" › ")}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
