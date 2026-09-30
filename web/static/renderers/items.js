"use strict";

import { runMossAction } from "../api.js?v=24";
import { createElement, displayValue } from "../dom.js?v=24";


const EMBEDDED_ITEM_LIMIT = 8;

function appendValueFields(container, fields, values = {}) {
  for (const field of fields || []) {
    const label = createElement("label", "edit-field");
    label.append(createElement("span", "edit-field-label", field.label));
    const input = createElement("input");
    input.type = "text";
    input.name = field.id;
    input.value = values[field.id] ?? "";
    label.append(input);
    container.append(label);
  }
}

function readValues(container, fields) {
  return Object.fromEntries(
    (fields || []).map((field) => [field.id, container.elements[field.id]?.value ?? ""]),
  );
}

function parseFields(value) {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [rawId, ...labelParts] = line.split("|");
      const id = rawId.trim();
      const label = labelParts.join("|").trim();
      if (!label) throw new Error(`Field ${id || "(blank)"} needs a label after |.`);
      return { id, label };
    });
}

function fieldsText(fields) {
  return (fields || []).map((field) => `${field.id} | ${field.label}`).join("\n");
}

export function createItemRenderers({ bindNodeLink, makeHeadingLink, refreshCurrentNode }) {
  function makeItemRow(item, path, fields) {
    const row = createElement("li", "item-list-row");
    const title = createElement("a", "item-list-title", item.display_title || item.title || item.id);
    bindNodeLink(title, item.id, path);
    row.append(title);
    if (fields.length) {
      const values = createElement("dl", "item-list-values");
      for (const field of fields) {
        const pair = createElement("div", "item-list-value");
        pair.append(
          createElement("dt", null, field.label),
          createElement("dd", null, displayValue(item.values?.[field.id])),
        );
        values.append(pair);
      }
      row.append(values);
    }
    return row;
  }

  function makeItemComposer(node) {
    const form = createElement("form", "compact-action-form item-composer");
    form.append(createElement("h3", "edit-subtitle", "Add item"));
    const grid = createElement("div", "compact-form-grid");
    const titleField = createElement("label", "edit-field");
    titleField.append(createElement("span", "edit-field-label", "Title"));
    const title = createElement("input");
    title.type = "text";
    title.name = "title";
    title.required = true;
    title.maxLength = 160;
    title.placeholder = "New item";
    titleField.append(title);
    grid.append(titleField);
    appendValueFields(grid, node.fields);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const submit = createElement("button", "primary-button compact-button", "Add item");
    submit.type = "submit";
    form.append(grid, feedback, submit);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      submit.disabled = true;
      try {
        await runMossAction("create_item", {
          parent_id: node.id,
          title: title.value,
          values: readValues(form, node.fields),
        });
        await refreshCurrentNode("Item added.");
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
      }
    });
    return form;
  }

  function makeFieldsEditor(node) {
    const details = createElement("details", "item-fields-editor");
    details.append(createElement("summary", null, "Define item fields"));
    const form = createElement("form", "compact-action-form");
    const explanation = createElement(
      "p",
      "item-fields-help",
      "Use one field per line: field_id | Display label. Every item shares these fields. Removing a field removes its saved values.",
    );
    const field = createElement("label", "edit-field");
    field.append(createElement("span", "edit-field-label", "Shared fields"));
    const textarea = createElement("textarea");
    textarea.name = "fields";
    textarea.rows = Math.max(4, (node.fields || []).length + 1);
    textarea.placeholder = "rating | Rating / 10\ncolor | Color";
    textarea.value = fieldsText(node.fields);
    field.append(textarea);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const save = createElement("button", "secondary-button compact-button", "Save field structure");
    save.type = "submit";
    form.append(explanation, field, feedback, save);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      save.disabled = true;
      try {
        const fields = parseFields(textarea.value);
        const response = await runMossAction("update_item_list_fields", {
          node_id: node.id,
          fields,
        });
        if (!response.result?.changed) {
          feedback.textContent = "No field changes to save.";
          save.disabled = false;
          return;
        }
        await refreshCurrentNode("Item fields updated.");
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        save.disabled = false;
      }
    });
    details.append(form);
    return details;
  }

  function renderItemList(node, path, direct = false) {
    const panel = createElement("section", "item-list-panel");
    if (!direct) {
      const headingRow = createElement("div", "embedded-node-heading");
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      const editLink = makeHeadingLink(node, path);
      editLink.className = "parent-edit-icon";
      editLink.textContent = "\u270e";
      editLink.title = "Edit item list";
      editLink.setAttribute("aria-label", `Edit ${node.display_title || node.title || "item list"}`);
      headingRow.append(heading, editLink);
      panel.append(headingRow);
    }

    const allItems = Array.isArray(node.child_nodes) ? node.child_nodes : [];
    const visibleItems = direct ? allItems : allItems.slice(0, EMBEDDED_ITEM_LIMIT);
    const list = createElement("ul", "item-list");
    for (const item of visibleItems) {
      list.append(makeItemRow(item, [...path, {
        id: item.id,
        type: item.type,
        title: item.display_title || item.title || item.id,
      }], node.fields || []));
    }
    if (visibleItems.length) panel.append(list);
    else panel.append(createElement("p", "empty-message", "This item list has no items."));

    if (!direct && allItems.length > visibleItems.length) {
      const open = makeHeadingLink(node, path);
      open.className = "item-list-more";
      open.textContent = `Open all ${allItems.length} items`;
      panel.append(open);
    }
    if (direct) panel.append(makeItemComposer(node), makeFieldsEditor(node));
    return panel;
  }

  function renderItem(node) {
    const panel = createElement("section", "item-detail");
    if (node.fields?.length) {
      const values = createElement("dl", "item-detail-values");
      for (const field of node.fields) {
        const pair = createElement("div", "item-detail-value");
        pair.append(
          createElement("dt", null, field.label),
          createElement("dd", null, displayValue(node.values?.[field.id])),
        );
        values.append(pair);
      }
      panel.append(values);
    } else {
      panel.append(createElement("p", "empty-message", "This list uses title-only items."));
    }

    const form = createElement("form", "compact-action-form item-values-editor");
    form.append(createElement("h2", "edit-section-title", "Edit item"));
    const grid = createElement("div", "compact-form-grid");
    const titleField = createElement("label", "edit-field");
    titleField.append(createElement("span", "edit-field-label", "Title"));
    const title = createElement("input");
    title.type = "text";
    title.name = "title";
    title.required = true;
    title.maxLength = 160;
    title.value = node.title || "";
    titleField.append(title);
    grid.append(titleField);
    appendValueFields(grid, node.fields, node.values);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const save = createElement("button", "primary-button compact-button", "Save item");
    save.type = "submit";
    form.append(grid, feedback, save);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      save.disabled = true;
      try {
        const response = await runMossAction("update_item", {
          node_id: node.id,
          title: title.value,
          values: readValues(form, node.fields),
        });
        if (!response.result?.changed) {
          feedback.textContent = "No item changes to save.";
          save.disabled = false;
          return;
        }
        await refreshCurrentNode("Item updated.");
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        save.disabled = false;
      }
    });
    panel.append(form);
    return panel;
  }

  return { renderItem, renderItemList };
}
