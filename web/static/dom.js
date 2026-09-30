"use strict";

export function createElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined && text !== null) {
    node.textContent = String(text);
  }
  return node;
}

export function humanLabel(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

export function makeLabeledSection(label, className = "record-section") {
  const section = createElement("section", className);
  section.append(createElement("p", "field-label", label));
  return section;
}

const TEXT_SIZE_PRESETS = {
  small: "15px",
  medium: "18px",
  large: "24px",
};

const TEXT_FONT_PRESETS = {
  serif: "var(--font-serif)",
  sans: "var(--font-sans)",
  "sans-serif": "var(--font-sans)",
  monospace: "ui-monospace, SFMono-Regular, Menlo, monospace",
};

export function applyTextPresentation(block, node) {
  if (!node || !["text", "note", "randomizer"].includes(node.type)) {
    return;
  }

  block.classList.add("presented-text");
  const rawSize = String(node.attributes?.size || "").trim();
  let size = TEXT_SIZE_PRESETS[rawSize.toLowerCase()] || rawSize;
  if (/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(size)) {
    size = `${size}px`;
  }
  if (size && CSS.supports("font-size", size)) {
    block.style.fontSize = size;
  }

  const rawFont = String(node.attributes?.font || "").trim();
  const font = TEXT_FONT_PRESETS[rawFont.toLowerCase()] || rawFont;
  if (font && CSS.supports("font-family", font)) {
    block.style.fontFamily = font;
  }

  const align = node.attributes?.align;
  if (["left", "center", "right"].includes(align)) {
    block.classList.add(`text-align-${align}`);
  }

  const color = node.attributes?.color;
  if (
    typeof color === "string" &&
    color.trim() &&
    CSS.supports("color", color.trim())
  ) {
    block.style.color = color.trim();
  }
}

export function appendText(container, content, node = null) {
  const block = createElement("div", "node-text");
  applyTextPresentation(block, node);
  const normalized = String(content || "").replace(/\r\n?/g, "\n");
  const paragraphs = normalized.split(/\n[ \t]*\n/);
  let added = false;
  for (const paragraph of paragraphs) {
    if (!paragraph && paragraphs.length === 1) {
      continue;
    }
    block.append(createElement("p", null, paragraph));
    added = true;
  }
  if (!added) {
    block.append(createElement("p", "empty-message", "No content."));
  }
  container.append(block);
}

export function appendLabeledText(container, label, content, node = null) {
  const section = makeLabeledSection(label);
  appendText(section, content, node);
  container.append(section);
}

export function textDisplayTitle(node) {
  return node.title || humanLabel(node.display_title || node.id);
}

export function shortExcerpt(text, maximum) {
  const compact = String(text || "").replace(/\s+/g, " ").trim();
  if (compact.length <= maximum) {
    return compact;
  }
  return `${compact.slice(0, maximum).trimEnd()}…`;
}
