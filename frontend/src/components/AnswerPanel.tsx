function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = Math.round(Math.max(0, Math.min(1, confidence)) * 100);
  return (
    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
      Confidence {percent}%
    </span>
  );
}

export function AnswerPanel({
  answer,
  confidence,
}: {
  answer: string;
  confidence: number;
}) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Answer
        </h3>
        <ConfidenceBadge confidence={confidence} />
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
        {answer}
      </p>
    </section>
  );
}
