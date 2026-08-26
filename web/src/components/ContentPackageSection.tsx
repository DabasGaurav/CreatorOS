"use client";

import { useState } from "react";
import type { ContentPackage } from "@/lib/types";

const FIELDS: { key: keyof ContentPackage; label: string }[] = [
  { key: "hook", label: "Hook" },
  { key: "script", label: "Script" },
  { key: "storyboard", label: "Storyboard" },
  { key: "caption", label: "Caption" },
  { key: "cta", label: "CTA" },
];

export default function ContentPackageSection({ content }: { content: ContentPackage }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-md border border-surface-raised bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-left font-body text-sm font-medium text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber"
      >
        Content package
        <span className="font-utility text-ink-muted" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && (
        <div className="space-y-4 border-t border-surface-raised px-4 py-4">
          {FIELDS.map(({ key, label }) => (
            <div key={key}>
              <h3 className="mb-1 font-utility text-xs uppercase tracking-wide text-ink-muted">
                {label}
              </h3>
              <p className="whitespace-pre-wrap font-body text-sm leading-relaxed text-ink">
                {content[key]}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
