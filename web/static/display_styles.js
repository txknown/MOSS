"use strict";
import { runMossAction } from "./api.js?v=35";
import { createElement } from "./dom.js?v=35";

// Renderers are explicit code supplied by the app, never executable settings.
export function createDisplayStyles({ uiViews, renderers, refreshCurrentNode }) {
  function selected(node, context) {
    const id = uiViews.getNodeStyles()[node.id]?.[context] || "default";
    return uiViews.getDisplayCatalog()[node.type]?.[context]?.some(style => style.id === id) ? id : "default";
  }
  function render(node, path, context) {
    const id = selected(node, context);
    const renderer = renderers[`${node.type}:${context}:${id}`];
    return id !== "default" && renderer ? renderer(node, path) : null;
  }
  function makeEditor(node) {
    const section = createElement("section", "node-display-editor");
    section.append(createElement("h3", "section-heading", "Display styles"));
    const form = createElement("form", "node-display-form");
    const controls = {};
    for (const [context, caption] of [["parent", "On a parent page"], ["open", "When opened"]]) {
      const field = createElement("label", "edit-field");
      const select = createElement("select"); select.name = context;
      const styles = uiViews.getDisplayCatalog()[node.type]?.[context] || [{id:"default",name:"Default"}];
      for (const style of styles) {
        const option = createElement("option", null, style.name); option.value = style.id;
        select.append(option);
      }
      select.value = selected(node, context); controls[context] = select;
      field.append(createElement("span", "edit-field-label", caption), select); form.append(field);
    }
    const save = createElement("button", "primary-button compact-button", "Save display styles"); save.type = "submit";
    const feedback = createElement("p", "edit-feedback"); feedback.setAttribute("role", "status");
    form.append(createElement("p", "muted", "Presentation only. These choices leave this node’s content and children unchanged."), save, feedback);
    form.addEventListener("submit", async event => {
      event.preventDefault(); save.disabled = true; feedback.textContent = "Saving…";
      try {
        const response = await runMossAction("update_node_display", {node_id: node.id, parent: controls.parent.value, open: controls.open.value});
        uiViews.setNodeStyles(node.id, response.result.styles);
        await refreshCurrentNode("Display styles saved.");
      } catch (error) { feedback.textContent = error.message; }
      finally { save.disabled = false; }
    });
    section.append(form); return section;
  }
  return { render, makeEditor, selected };
}
