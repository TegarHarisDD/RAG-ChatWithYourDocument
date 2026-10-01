import type { Message } from "./api";
import { formatLocator } from "./locator";

function sourceLine(citation: Message["citations"][number]): string {
  const locator = formatLocator(citation.locator);
  return `[${citation.index}] ${citation.filename}${locator ? ` (${locator})` : ""}`;
}

export function conversationToMarkdown(title: string, messages: Message[]): string {
  const lines: string[] = [`# ${title}`, ""];

  for (const message of messages) {
    if (message.role === "user") {
      lines.push(`## Question`, "", message.content, "");
    } else {
      lines.push(`## Answer`, "", message.content, "");
      if (message.citations.length) {
        lines.push("Sources:", "");
        for (const citation of message.citations) {
          lines.push(`- ${sourceLine(citation)}`);
        }
        lines.push("");
      }
    }
  }

  return lines.join("\n").trimEnd() + "\n";
}

export function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "conversation";
}

export function downloadTextFile(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
