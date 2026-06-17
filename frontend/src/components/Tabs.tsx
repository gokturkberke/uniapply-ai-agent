export type TabId = "ask" | "checklist" | "missing" | "email";

export const TABS: ReadonlyArray<{ id: TabId; label: string }> = [
  { id: "ask", label: "Ask" },
  { id: "checklist", label: "Checklist" },
  { id: "missing", label: "Missing Documents" },
  { id: "email", label: "Draft Email" },
];

export function Tabs({
  active,
  onChange,
  disabled,
}: {
  active: TabId;
  onChange: (tab: TabId) => void;
  disabled: boolean;
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 border-b border-slate-200">
      {TABS.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => onChange(tab.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:text-slate-300 ${
              isActive
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
