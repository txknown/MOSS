"use strict";

import { runMossAction } from "../api.js?v=24";
import {
  applyTextPresentation,
  appendText,
  createElement,
} from "../dom.js?v=24";


const NOTE_PREVIEW_LENGTH = 420;

function notePreview(value) {
  const normalized = String(value || "").replace(/\r\n?/g, "\n").trim();
  if (normalized.length <= NOTE_PREVIEW_LENGTH) return normalized;
  const candidate = normalized.slice(0, NOTE_PREVIEW_LENGTH);
  const breakAt = Math.max(candidate.lastIndexOf("\n"), candidate.lastIndexOf(" "));
  return `${candidate.slice(0, breakAt > NOTE_PREVIEW_LENGTH * 0.7 ? breakAt : undefined).trimEnd()}…`;
}


export function createContentRenderers({ bindNodeLink, makeHeadingLink, nodeSchemas, refreshCurrentNode }) {
  function renderNote(node, path) {
    const panel = createElement("section", "embedded-note");
    const headingRow = createElement("div", "embedded-note-heading");
    const edit = createElement("button", "embedded-note-edit", "\u270e");
    edit.type = "button";
    edit.title = "Edit note";
    edit.setAttribute("aria-label", `Edit ${node.display_title || node.title || "note"}`);
    edit.setAttribute("aria-expanded", "false");
    const heading = createElement("h2", "section-heading");
    heading.append(makeHeadingLink(node, path));
    headingRow.append(heading, edit);
    panel.append(headingRow);

    const fullContent = String(node.content || "");
    const previewContent = notePreview(fullContent);
    const preview = createElement("div", "embedded-note-preview");
    appendText(preview, previewContent, node);
    panel.append(preview);

    const isTruncated = previewContent !== fullContent.replace(/\r\n?/g, "\n").trim();
    const toolbar = createElement("div", "embedded-note-toolbar");
    if (isTruncated) {
      const open = makeHeadingLink(node, path);
      open.className = "embedded-note-open";
      open.textContent = "Open full note";
      toolbar.append(open);
    }

    const form = createElement("form", "embedded-note-form");
    form.hidden = true;
    const field = createElement("label", "edit-field");
    field.append(createElement("span", "edit-field-label", "Note text"));
    const textarea = createElement("textarea");
    textarea.rows = nodeSchemas.note?.content?.rows || 7;
    textarea.value = fullContent;
    const maximum = nodeSchemas.note?.content?.max_length;
    if (maximum) textarea.maxLength = maximum;
    field.append(textarea);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const actions = createElement("div", "embedded-note-actions");
    const save = createElement("button", "primary-button compact-button", "Save note");
    save.type = "submit";
    const cancel = createElement("button", "secondary-button compact-button", "Cancel");
    cancel.type = "button";
    actions.append(save, cancel);
    form.append(field, feedback, actions);

    const closeEditor = () => {
      form.hidden = true;
      preview.hidden = false;
      edit.hidden = false;
      edit.setAttribute("aria-expanded", "false");
      if (isTruncated) toolbar.hidden = false;
    };
    edit.addEventListener("click", () => {
      preview.hidden = true;
      edit.hidden = true;
      edit.setAttribute("aria-expanded", "true");
      if (isTruncated) toolbar.hidden = true;
      form.hidden = false;
      textarea.focus();
    });
    cancel.addEventListener("click", () => {
      textarea.value = fullContent;
      closeEditor();
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      save.disabled = true;
      try {
        const response = await runMossAction("update_node", {
          node_id: node.id,
          attributes: {},
          content: textarea.value,
        });
        if (!response.result?.changed?.length) {
          feedback.textContent = "No changes to save.";
          save.disabled = false;
          return;
        }
        await refreshCurrentNode(`Updated ${node.display_title || node.title || "note"}.`);
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        save.disabled = false;
      }
    });
    if (isTruncated) panel.append(toolbar);
    panel.append(form);
    return panel;
  }

  function renderLink(node, path, direct = false) {
    const panel = createElement("section", "link-panel");
    const destination = node.url;
    if (direct && destination) {
      const external = createElement(
        "a",
        "named-link named-link-direct",
        destination,
      );
      external.href = destination;
      external.target = "_blank";
      external.rel = "noopener noreferrer";
      external.append(createElement("span", "named-link-arrow", "↗"));
      panel.append(external);
    } else if (direct) {
      panel.append(createElement("p", "empty-message", "This link has no safe HTTP or HTTPS destination."));
    } else {
      const headingRow = createElement("div", "embedded-node-heading");
      if (destination) {
        const external = createElement(
          "a",
          "named-link",
          node.display_title || node.title || node.id,
        );
        external.href = destination;
        external.target = "_blank";
        external.rel = "noopener noreferrer";
        external.append(createElement("span", "named-link-arrow", "↗"));
        headingRow.append(external);
      } else {
        headingRow.append(
          createElement("span", "named-link", node.display_title || node.title || node.id),
        );
      }
      const editLink = makeHeadingLink(node, path);
      editLink.className = "parent-edit-icon";
      editLink.textContent = "\u270e";
      editLink.title = "Edit link";
      editLink.setAttribute("aria-label", `Edit ${node.display_title || node.title || "link"}`);
      headingRow.append(editLink);
      panel.append(headingRow);
      if (!destination) {
        panel.append(createElement("p", "empty-message", "This link has no safe HTTP or HTTPS destination."));
      }
    }
    return panel;
  }

  function renderInternalLink(node, path, direct = false) {
    const panel = createElement("section", "link-panel internal-link-panel");
    const target = node.internal_target;
    const label = node.display_title || node.title || target?.title || node.target_id || node.id;
    if (target) {
      const link = createElement("a", direct ? "named-link named-link-direct" : "named-link", label);
      bindNodeLink(link, target.id, null);
      link.append(createElement("span", "named-link-arrow", "→"));
      if (direct) {
        panel.append(link, createElement("p", "internal-link-target", `${target.type} · ID · ${target.id}`));
      } else {
        const headingRow = createElement("div", "embedded-node-heading");
        const editLink = makeHeadingLink(node, path);
        editLink.className = "parent-edit-icon";
        editLink.textContent = "\u270e";
        editLink.title = "Edit internal link";
        editLink.setAttribute("aria-label", `Edit ${label}`);
        headingRow.append(link, editLink);
        panel.append(headingRow);
      }
    } else {
      panel.append(
        createElement("p", "empty-message", `Missing internal target: ${node.target_id || "not set"}.`),
      );
    }
    return panel;
  }

  function renderRandomizer(node, path, direct = false) {
    const panel = createElement("section", "randomizer-panel");
    if (!direct && node.title && node.attributes?.title_visible === true) {
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      panel.append(heading);
    }

    const selections = Array.isArray(node.random_selection)
      ? node.random_selection
      : [];
    if (node.attributes?.display_mode === "text") {
      const text = createElement("div", "random-text node-text");
      applyTextPresentation(text, node);
      for (const phrase of selections) {
        text.append(createElement("p", null, phrase));
      }
      if (!text.childElementCount) {
        text.append(createElement("p", "empty-message", "No phrases."));
      }
      panel.append(text);
    } else {
      const list = createElement("ul", "random-list");
      applyTextPresentation(list, node);
      for (const phrase of selections) {
        list.append(createElement("li", "random-item", phrase));
      }
      if (!list.childElementCount) {
        list.append(createElement("li", "empty-message", "No phrases."));
      }
      panel.append(list);
    }
    return panel;
  }

  function renderFallback(node, path, direct = false) {
    const panel = createElement("section", "fallback-panel");
    panel.append(
      createElement(
        "p",
        "fallback-type",
        `Node type: ${String(node.type || "unknown").replaceAll("_", " ")}`,
      ),
    );
    if (!direct && node.title) {
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      panel.append(heading);
    }
    if (node.content) {
      appendText(panel, node.content);
    } else {
      panel.append(createElement("p", "empty-message", "No readable content."));
    }
    return panel;
  }

  return {
    renderFallback,
    renderInternalLink,
    renderLink,
    renderNote,
    renderRandomizer,
  };
}
