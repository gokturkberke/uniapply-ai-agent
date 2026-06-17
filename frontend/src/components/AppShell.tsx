import type { ReactNode } from "react";

import { HealthDot } from "./HealthDot";
import { ProgrammeSelector } from "./ProgrammeSelector";

export function AppShell({
  selectedKey,
  onSelectProgramme,
  children,
}: {
  selectedKey: string | null;
  onSelectProgramme: (key: string | null) => void;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-base font-semibold leading-tight">
              UniApply Assistant
            </h1>
            <p className="text-xs text-slate-500">
              Grounded answers from official programme documents
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <HealthDot />
            <ProgrammeSelector value={selectedKey} onChange={onSelectProgramme} />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-6">{children}</main>
    </div>
  );
}
