import type { ReactNode } from "react";
import type { Citation } from "../api";

type Ctx = {
  byIndex: Map<number, Citation>;
  onCitation: (citation: Citation) => void;
};

// A deliberately small, safe markdown subset rendered as React elements (never
// HTML strings), so model output can never inject markup. Anything not matched
// falls through as plain text.
function renderInline(text: string, ctx: Ctx, keyBase: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const re =
    /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|~~[^~]+~~|\[[^\]]+\]\([^)]+\)|\[\d+\])/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = re.exec(text))) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[0];
    const key = `${keyBase}-${i++}`;

    if (token.startsWith("`")) {
      nodes.push(
        <code key={key} className="bg-panel2 px-1 py-0.5 font-mono text-[0.85em] text-ink">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(
        <strong key={key} className="font-semibold">
          {renderInline(token.slice(2, -2), ctx, key)}
        </strong>
      );
    } else if (token.startsWith("~~")) {
      nodes.push(
        <del key={key} className="text-muted">
          {renderInline(token.slice(2, -2), ctx, key)}
        </del>
      );
    } else if (token.startsWith("*") || token.startsWith("_")) {
      nodes.push(
        <em key={key} className="italic">
          {renderInline(token.slice(1, -1), ctx, key)}
        </em>
      );
    } else if (token.startsWith("[")) {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const cite = /^\[(\d+)\]$/.exec(token);
      if (link && /^(https?:|mailto:)/i.test(link[2].trim())) {
        nodes.push(
          <a
            key={key}
            href={link[2].trim()}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
          >
            {renderInline(link[1], ctx, key)}
          </a>
        );
      } else if (cite) {
        const citation = ctx.byIndex.get(Number(cite[1]));
        if (citation) {
          nodes.push(
            <button
              key={key}
              className="citation"
              title={`Source: ${citation.filename}`}
              aria-label={`View source ${citation.index}: ${citation.filename}`}
              onClick={() => ctx.onCitation(citation)}
            >
              {token}
            </button>
          );
        } else {
          nodes.push(token);
        }
      } else {
        nodes.push(token);
      }
    }

    last = match.index + token.length;
  }

  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  return nodes;
}

function renderLines(
  lines: string[],
  ctx: Ctx,
  keyBase: string,
  trailing?: ReactNode
): ReactNode[] {
  const nodes: ReactNode[] = [];
  lines.forEach((line, idx) => {
    if (idx > 0) nodes.push(<br key={`${keyBase}-br-${idx}`} />);
    nodes.push(...renderInline(line, ctx, `${keyBase}-${idx}`));
  });
  if (trailing) nodes.push(trailing);
  return nodes;
}

function renderBlocks(content: string, ctx: Ctx, trailing?: ReactNode): ReactNode[] {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];
  const isBlank = (line: string) => /^\s*$/.test(line);
  const isRule = (line: string) => /^\s*([-*_])(\s*\1){2,}\s*$/.test(line);
  const isList = (line: string) => /^\s*([-*+]|\d+\.)\s+/.test(line);
  let i = 0;
  let key = 0;
  let trailingPlaced = false;

  while (i < lines.length) {
    const line = lines[i];

    if (/^\s*```/.test(line)) {
      i++;
      const code: string[] = [];
      while (i < lines.length && !/^\s*```/.test(lines[i])) {
        code.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      const base = `pre-${key++}`;
      blocks.push(
        <pre
          key={base}
          className="mt-3 overflow-x-auto border border-line bg-panel2 p-3 font-mono text-xs leading-relaxed first:mt-0"
        >
          <code>{code.join("\n")}</code>
        </pre>
      );
      continue;
    }

    if (isBlank(line)) {
      i++;
      continue;
    }

    if (isRule(line)) {
      blocks.push(<hr key={`hr-${key++}`} className="my-4 border-t border-line" />);
      i++;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const base = `head-${key++}`;
      blocks.push(
        <p
          key={base}
          className="mt-5 font-display text-base font-medium leading-snug first:mt-0"
        >
          {renderInline(heading[2], ctx, base)}
        </p>
      );
      i++;
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        quote.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      const base = `quote-${key++}`;
      blocks.push(
        <blockquote
          key={base}
          className="mt-3 border-l-2 border-accent/40 pl-4 italic text-ink/85 first:mt-0"
        >
          {renderLines(quote, ctx, base)}
        </blockquote>
      );
      continue;
    }

    if (isList(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items: string[] = [];
      while (i < lines.length && isList(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
        i++;
      }
      const base = `list-${key++}`;
      blocks.push(
        <ul
          key={base}
          className={`mt-3 space-y-1 pl-5 marker:text-faint first:mt-0 ${
            ordered ? "list-decimal" : "list-disc"
          }`}
        >
          {items.map((item, idx) => (
            <li key={`${base}-${idx}`}>{renderInline(item, ctx, `${base}-${idx}`)}</li>
          ))}
        </ul>
      );
      continue;
    }

    const buf: string[] = [line];
    i++;
    while (
      i < lines.length &&
      !isBlank(lines[i]) &&
      !isRule(lines[i]) &&
      !isList(lines[i]) &&
      !/^\s*(```|#{1,6}\s|>)/.test(lines[i])
    ) {
      buf.push(lines[i]);
      i++;
    }
    const isLast = lines.slice(i).every(isBlank);
    const trailingHere = trailing && isLast ? trailing : undefined;
    if (trailingHere) trailingPlaced = true;
    blocks.push(
      <p key={`p-${key++}`} className="mt-3 first:mt-0">
        {renderLines(buf, ctx, `p-${key}`, trailingHere)}
      </p>
    );
  }

  if (trailing && !trailingPlaced) {
    blocks.push(
      <p key="trailing" className="mt-3 first:mt-0">
        {trailing}
      </p>
    );
  }

  return blocks;
}

export default function MessageContent({
  content,
  citations,
  onCitation,
  trailing,
}: {
  content: string;
  citations: Citation[];
  onCitation: (citation: Citation) => void;
  trailing?: ReactNode;
}) {
  const ctx: Ctx = {
    byIndex: new Map(citations.map((citation) => [citation.index, citation])),
    onCitation,
  };

  return (
    <div className="break-words font-reading text-[1.0625rem] leading-[1.75] text-ink/95">
      {renderBlocks(content, ctx, trailing)}
    </div>
  );
}
