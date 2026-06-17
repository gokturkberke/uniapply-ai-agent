import { useState } from "react";

import { AppShell } from "./components/AppShell";
import { AskPanel } from "./components/AskPanel";
import { ChecklistPanel } from "./components/ChecklistPanel";
import { DetectMissingPanel } from "./components/DetectMissingPanel";
import { DraftEmailPanel } from "./components/DraftEmailPanel";
import { Tabs, type TabId } from "./components/Tabs";
import { findProgramme, programmeKey } from "./config/programmes";

function EmptyState() {
  return (
    <div className="mt-6 rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="text-sm font-medium text-slate-700">
        Select a programme to begin
      </p>
      <p className="mt-1 text-sm text-slate-500">
        Every answer is scoped to a single university and programme so facts are
        never blended across institutions.
      </p>
    </div>
  );
}

export default function App() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("ask");

  const programme = selectedKey ? (findProgramme(selectedKey) ?? null) : null;

  return (
    <AppShell selectedKey={selectedKey} onSelectProgramme={setSelectedKey}>
      <Tabs active={activeTab} onChange={setActiveTab} disabled={!programme} />
      {!programme ? (
        <EmptyState />
      ) : (
        <div className="mt-4" key={programmeKey(programme)}>
          {activeTab === "ask" ? <AskPanel programme={programme} /> : null}
          {activeTab === "checklist" ? (
            <ChecklistPanel programme={programme} />
          ) : null}
          {activeTab === "missing" ? (
            <DetectMissingPanel programme={programme} />
          ) : null}
          {activeTab === "email" ? (
            <DraftEmailPanel programme={programme} />
          ) : null}
        </div>
      )}
    </AppShell>
  );
}
