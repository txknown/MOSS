"use strict";
import { runMossAction } from "../api.js?v=35";
import { appendText, createElement } from "../dom.js?v=35";
import { formatTimestamp } from "../dates.js?v=35";

export function createScratchpadRenderers({ makeHeadingLink, nodeSchemas }) {
  function renderText(node, path, parentId = null, onRemove = null, timestamp = false) {
    const block = createElement("section", parentId ? "inline-block scratchpad-jot" : "inline-block");
    let content = node.content || "";
    const preview = createElement("div");
    const renderPreview = () => {
      preview.replaceChildren();
      const link = makeHeadingLink(node, path);
      link.className = "flow-text-link";
      link.replaceChildren();
      link.title = "Open text node";
      appendText(link, content, node);
      preview.append(link);
    };
    renderPreview();
    if (!parentId) { block.append(preview); return block; }
    if (timestamp && node.attributes?.created) block.append(createElement("time", "jot-time", formatTimestamp(node.attributes.created)));
    const toolbar = createElement("div", "jot-controls jot-text-controls");
    const edit = createElement("button", "embedded-note-edit", "✎");
    edit.type = "button";
    edit.title = "Edit text";
    edit.setAttribute("aria-label", `Edit text ${node.id}`);
    const remove = createElement("button", "embedded-note-edit", "\u{1F5D1}\uFE0E");
    remove.type = "button";
    remove.title = "Remove text";
    remove.setAttribute("aria-label", `Remove text ${node.id}`);
    toolbar.append(edit);
    if (parentId) toolbar.append(remove);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const form = createElement("form", "jot-editor");
    form.hidden = true;
    const input = createElement("textarea");
    input.rows = 8;
    input.maxLength = nodeSchemas.text.content.max_length;
    input.setAttribute("aria-label", "Edit jot text");
    const save = createElement("button", "primary-button compact-button", "Save text");
    save.type = "submit";
    const cancel = createElement("button", "quiet-button", "Cancel");
    cancel.type = "button";
    form.append(input, save, cancel);
    const fitEditor = () => {
      if (form.hidden || !input.isConnected) return;
      input.style.height = "auto";
      const border = input.offsetHeight - input.clientHeight;
      input.style.height = `${input.scrollHeight + border}px`;
    };
    input.addEventListener("input", fitEditor);
    let previousWidth = 0;
    const resize = new ResizeObserver(entries => {
      const width = entries[0].contentRect.width;
      if (width && width !== previousWidth) { previousWidth = width; fitEditor(); }
    });
    resize.observe(input);
    const close = () => {
      form.hidden = true; preview.hidden = false; toolbar.hidden = false;
      block.classList.remove("is-editing");
    };
    edit.addEventListener("click", () => {
      input.value = content;
      form.hidden = false; preview.hidden = true; toolbar.hidden = true;
      block.classList.add("is-editing");
      fitEditor();
      input.focus({ preventScroll: true });
    });
    cancel.addEventListener("click", close);
    form.addEventListener("submit", async event => {
      event.preventDefault(); save.disabled = true; cancel.disabled = true; feedback.textContent = "";
      try {
        const response = await runMossAction("update_node", { node_id: node.id, attributes: {}, content: input.value });
        content = response.node.content;
        renderPreview(); close(); feedback.textContent = "Text saved.";
      } catch (error) { feedback.textContent = error.message; }
      finally { save.disabled = false; cancel.disabled = false; }
    });
    remove.addEventListener("click", async () => {
      if (!window.confirm(`Are you sure you want to permanently delete this jot?\n\n${content.slice(0, 160)}${content.length > 160 ? "…" : ""}`)) return;
      remove.disabled = true;
      try {
        await runMossAction("remove_text", { parent_id: parentId, node_id: node.id, confirm_id: node.id });
        resize.disconnect();
        block.remove();
        if (onRemove) onRemove();
      } catch (error) { feedback.textContent = error.message; remove.disabled = false; }
    });
    block.append(preview, toolbar, form, feedback);
    return block;
  }

  function renderScratchpad(node, path, direct = false) {
    const panel = createElement("section", "scratchpad-panel");
    if (!direct) {
      const title = createElement("h2", "section-heading scratchpad-title");
      title.append(makeHeadingLink(node, path));
      panel.append(title);
    }
    const form = createElement("form", "scratchpad-composer");
    const input = createElement("textarea");
    input.rows = 4;
    input.required = true;
    input.maxLength = nodeSchemas.text.content.max_length;
    input.placeholder = "Jot something…";
    input.setAttribute("aria-label", `Jot in ${node.title || node.id}`);
    const controls = createElement("div", "jot-controls");
    const submit = createElement("button", "primary-button compact-button", "Jot");
    submit.type = "submit";
    controls.append(submit);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    form.append(input, controls, feedback);
    panel.append(form);
    const history = createElement("div", "scratchpad-history");
    const empty = createElement("p", "empty-message", "No jots yet.");
    const updateEmpty = () => { if (!history.querySelector(".scratchpad-jot")) history.append(empty); };
    const jotPath = jot => [...path, { id: jot.id, type: "text", title: jot.id }];
    if (direct) {
      panel.append(createElement("h2", "section-heading", "Previous jots"), history);
      for (const jot of [...(node.child_nodes || [])].reverse()) {
        if (jot.type === "text" && !jot.missing) history.append(renderText(jot, jotPath(jot), node.id, updateEmpty, true));
      }
      updateEmpty();
    }
    form.addEventListener("submit", async event => {
      event.preventDefault(); submit.disabled = true; input.readOnly = true; feedback.textContent = "";
      try {
        const response = await runMossAction("jot", { parent_id: node.id, content: input.value });
        input.value = "";
        feedback.textContent = "Jot saved.";
        if (direct) {
          empty.remove();
          history.prepend(renderText(response.created, jotPath(response.created), node.id, updateEmpty, true));
        }
      } catch (error) { feedback.textContent = error.message; }
      finally { submit.disabled = false; input.readOnly = false; input.focus(); }
    });
    return panel;
  }
  return { renderScratchpad, renderText };
}
