"use strict";

import { runMossAction } from "./api.js?v=24";
import { createElement, humanLabel } from "./dom.js?v=24";


function nodeFieldValue(node, field) {
  if (Object.hasOwn(node, field)) {
    return node[field];
  }
  return node.attributes?.[field] ?? "";
}

function appendSelectOptions(select, choices, currentValue) {
  for (const choice of choices || []) {
    const option = createElement("option", null, choice.label);
    option.value = choice.value;
    option.selected = String(currentValue ?? "") === String(choice.value);
    select.append(option);
  }
}

function applyEditorProperties(control, editor) {
  if (editor.placeholder) control.placeholder = editor.placeholder;
  if (editor.max_length) control.maxLength = editor.max_length;
  if (editor.rows) control.rows = editor.rows;
  if (editor.required) control.required = true;
  if (editor.min !== undefined) control.min = String(editor.min);
  if (editor.step !== undefined) control.step = String(editor.step);
  if (editor.pattern) control.pattern = editor.pattern;
  if (editor.title) control.title = editor.title;
}

function makeAttributeEditorField(node, attribute, initialValue) {
  const editor = attribute.editor;
  const currentValue = initialValue !== undefined
    ? initialValue
    : nodeFieldValue(node, attribute.name);
  const label = createElement("label", "edit-field");
  const caption = createElement(
    "span",
    "edit-field-label",
    editor.label || humanLabel(attribute.name),
  );
  let control;

  if (editor.input_type === "textarea") {
    control = createElement("textarea");
    control.value = currentValue ?? "";
  } else if (editor.input_type === "checkbox") {
    label.classList.add("is-checkbox");
    control = createElement("input");
    control.type = "checkbox";
    control.checked = Boolean(currentValue);
  } else if (editor.input_type === "select") {
    control = createElement("select");
    appendSelectOptions(control, editor.choices, currentValue);
  } else {
    control = createElement("input");
    control.type = editor.input_type || "text";
    control.value = currentValue ?? "";
    if (attribute.type === "clock_time_or_blank") {
      control.inputMode = "numeric";
    }
  }
  applyEditorProperties(control, editor);

  control.name = attribute.name;
  control.dataset.attribute = attribute.name;
  control.dataset.valueType = attribute.type;
  control.dataset.requiredAttribute = attribute.required ? "true" : "false";
  if (editor.suggestions?.length) {
    const suggestions = createElement("datalist");
    suggestions.id = `${attribute.name}-options-${node.id}`;
    for (const suggestion of editor.suggestions) {
      const option = createElement("option");
      option.value = suggestion.value;
      option.label = suggestion.label;
      suggestions.append(option);
    }
    control.setAttribute("list", suggestions.id);
    label.append(caption, control, suggestions);
  } else if (label.classList.contains("is-checkbox")) {
    label.append(control, caption);
  } else {
    label.append(caption, control);
  }
  return label;
}

function readAttributeEditor(form) {
  const attributes = {};
  for (const control of form.querySelectorAll("[data-attribute]")) {
    let value = control.value;
    if (control.type === "checkbox") value = control.checked;
    if (["positive_integer", "day_number"].includes(control.dataset.valueType)) {
      value = Number(value);
    }
    attributes[control.name] = value;
  }
  return attributes;
}

function readCreateAttributes(container) {
  const attributes = readAttributeEditor(container);
  for (const control of container.querySelectorAll("[data-attribute]")) {
    if (control.type !== "checkbox" && control.value === "" && !control.required) {
      delete attributes[control.name];
    }
  }
  return attributes;
}

export function createEditors({ deleteCurrentNode, nodeSchemas, refreshCurrentNode, showActionNotice }) {
  function makeCreateChildForm(node) {
    const allowedTypes = nodeSchemas[node.type]?.child_creation_types || [];
    if (!allowedTypes.length) return null;

    const form = createElement("form", "compact-action-form create-child-form");
    form.append(createElement("h3", "edit-subtitle", "Create child"));
    const fields = createElement("div", "compact-form-grid");

    const typeField = createElement("label", "edit-field");
    typeField.append(createElement("span", "edit-field-label", "Type"));
    const typeSelect = createElement("select");
    typeSelect.name = "type";
    appendSelectOptions(
      typeSelect,
      allowedTypes.map((type) => ({ value: type, label: humanLabel(type) })),
      allowedTypes[0],
    );
    typeField.append(typeSelect);

    const idField = createElement("label", "edit-field");
    idField.append(createElement("span", "edit-field-label", "ID (optional)"));
    const idInput = createElement("input");
    idInput.type = "text";
    idInput.name = "id";
    idInput.pattern = "[A-Za-z0-9][A-Za-z0-9_-]*";
    idInput.placeholder = "Generated automatically";
    idField.append(idInput);

    const dynamicFields = createElement("div", "compact-dynamic-fields");

    const contentField = createElement("label", "edit-field edit-field-wide");
    const contentCaption = createElement("span", "edit-field-label", "Content");
    contentField.append(contentCaption);
    const contentInput = createElement("textarea");
    contentInput.name = "content";
    contentField.append(contentInput);

    const updateVisibleFields = () => {
      const childSchema = nodeSchemas[typeSelect.value] || {};
      const attributes = childSchema.attributes || [];
      dynamicFields.replaceChildren();
      const prospectiveNode = { id: `new-${typeSelect.value}`, type: typeSelect.value };
      for (const attribute of attributes.filter((item) => item.editable)) {
        dynamicFields.append(
          makeAttributeEditorField(prospectiveNode, attribute, attribute.default),
        );
      }
      const content = childSchema.content;
      contentField.hidden = !content?.editable;
      contentCaption.textContent = content?.label || "Content";
      contentInput.rows = content?.rows || 4;
      if (content?.max_length) contentInput.maxLength = content.max_length;
      contentInput.placeholder = content?.placeholder || "";
    };
    typeSelect.addEventListener("change", updateVisibleFields);
    updateVisibleFields();

    fields.append(typeField, idField, dynamicFields, contentField);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const submit = createElement("button", "primary-button compact-button", "Create");
    submit.type = "submit";
    form.append(fields, feedback, submit);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      submit.disabled = true;
      const type = typeSelect.value;
      const attributes = readCreateAttributes(dynamicFields);
      try {
        const response = await runMossAction("create_child", {
          parent_id: node.id,
          type,
          id: idInput.value.trim() || null,
          content: contentField.hidden ? "" : contentInput.value,
          attributes,
        });
        const created = response.created?.display_title || response.created?.id || "child";
        await refreshCurrentNode(`Created ${created}.`);
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
      }
    });
    return form;
  }

  function makeRelationshipEditor(node) {
    const schema = nodeSchemas[node.type];
    if (!schema?.manages_children || schema.relationship_editable === false) return null;
    const section = createElement("section", "relationship-editor");
    section.append(createElement("h2", "edit-section-title", "Children"));

    const createForm = makeCreateChildForm(node);
    if (createForm) section.append(createForm);

    const linkForm = createElement("form", "compact-action-form link-child-form");
    linkForm.append(createElement("h3", "edit-subtitle", "Link existing node"));
    const linkRow = createElement("div", "inline-action-row");
    const linkInput = createElement("input");
    linkInput.type = "text";
    linkInput.name = "child_id";
    linkInput.required = true;
    linkInput.pattern = "[A-Za-z0-9][A-Za-z0-9_-]*";
    linkInput.placeholder = "Node ID";
    linkInput.setAttribute("aria-label", "Node ID to link");
    const linkButton = createElement("button", "secondary-button compact-button", "Link");
    linkButton.type = "submit";
    linkRow.append(linkInput, linkButton);
    const linkFeedback = createElement("p", "edit-feedback");
    linkFeedback.setAttribute("role", "status");
    linkForm.append(linkRow, linkFeedback);
    linkForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      linkFeedback.textContent = "";
      linkButton.disabled = true;
      try {
        await runMossAction("link_node", {
          parent_id: node.id,
          child_id: linkInput.value,
        });
        await refreshCurrentNode(`Linked ${linkInput.value}.`);
      } catch (error) {
        linkFeedback.textContent = error instanceof Error ? error.message : String(error);
        linkButton.disabled = false;
      }
    });
    section.append(linkForm);

    const children = Array.isArray(node.child_nodes) ? node.child_nodes : [];
    if (children.length) {
      const list = createElement("ul", "child-action-list");
      children.forEach((child, index) => {
        const row = createElement("li", "child-action-row");
        const identity = createElement("div", "child-action-identity");
        identity.append(
          createElement("strong", null, child.display_title || child.title || child.id),
          createElement("span", null, `${child.type || "node"} · ID · ${child.id}`),
        );
        const controls = createElement("div", "child-action-controls");
        for (const [label, key, value, disabled, accessibleLabel] of [
          ["Top", "position", "top", index === 0, "to top"],
          ["↑", "direction", "up", index === 0, "up"],
          ["↓", "direction", "down", index === children.length - 1, "down"],
          ["Bottom", "position", "bottom", index === children.length - 1, "to bottom"],
        ]) {
          const button = createElement("button", "quiet-button", label);
          button.type = "button";
          button.disabled = disabled;
          button.setAttribute("aria-label", `Move ${child.id} ${accessibleLabel}`);
          button.title = `Move ${accessibleLabel}`;
          button.addEventListener("click", async () => {
            button.disabled = true;
            try {
              await runMossAction("move_child", {
                parent_id: node.id,
                child_id: child.id,
                [key]: value,
              });
              await refreshCurrentNode(`Moved ${child.display_title || child.id} ${accessibleLabel}.`);
            } catch (error) {
              button.disabled = false;
              showActionNotice(error instanceof Error ? error.message : String(error), true);
            }
          });
          controls.append(button);
        }
        const unlink = createElement("button", "quiet-button is-danger", "Unlink");
        unlink.type = "button";
        unlink.addEventListener("click", async () => {
          unlink.disabled = true;
          try {
            await runMossAction("unlink_node", {
              parent_id: node.id,
              child_id: child.id,
            });
            await refreshCurrentNode(`Unlinked ${child.display_title || child.id}.`);
          } catch (error) {
            unlink.disabled = false;
            showActionNotice(error instanceof Error ? error.message : String(error), true);
          }
        });
        controls.append(unlink);
        row.append(identity, controls);
        list.append(row);
      });
      section.append(list);
    }
    return section;
  }

  function makeDeleteNodeSection(node) {
    if (node.id === "home") return null;
    const section = createElement("section", "delete-node-section");
    section.append(
      createElement("h2", "edit-section-title", "Delete node"),
      createElement(
        "p",
        "delete-node-explanation",
        "Permanently deletes this node and removes every link to it. Child nodes are kept.",
      ),
    );
    const reveal = createElement("button", "danger-button compact-button", "Delete this node…");
    reveal.type = "button";
    const form = createElement("form", "delete-node-form");
    form.hidden = true;
    const field = createElement("label", "edit-field");
    field.append(createElement("span", "edit-field-label", `Type ${node.id} to confirm`));
    const confirmation = createElement("input");
    confirmation.type = "text";
    confirmation.autocomplete = "off";
    confirmation.spellcheck = false;
    field.append(confirmation);
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    const remove = createElement("button", "danger-button compact-button", "Delete permanently");
    remove.type = "submit";
    remove.disabled = true;
    confirmation.addEventListener("input", () => {
      remove.disabled = confirmation.value !== node.id;
    });
    reveal.addEventListener("click", () => {
      form.hidden = !form.hidden;
      reveal.textContent = form.hidden ? "Delete this node…" : "Cancel deletion";
      if (!form.hidden) confirmation.focus();
    });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (confirmation.value !== node.id) return;
      feedback.textContent = "";
      remove.disabled = true;
      try {
        await runMossAction("trash_node", { node_id: node.id });
        await deleteCurrentNode(node);
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        remove.disabled = false;
      }
    });
    form.append(field, feedback, remove);
    section.append(reveal, form);
    return section;
  }

  function makeNodeEditor(node) {
    const schema = nodeSchemas[node.type];
    if (!schema) return null;
    const fields = (schema.attributes || []).filter(
      (item) => item.editable && !(node.type === "item" && item.name === "title"),
    );
    const contentSchema = schema.content?.editable ? schema.content : null;
    const relationshipEditor = makeRelationshipEditor(node);
    const deleteNodeSection = makeDeleteNodeSection(node);
    if (!fields.length && !contentSchema && !relationshipEditor && !deleteNodeSection) return null;

    const details = createElement("details", "node-editor");
    const summary = createElement("summary", "node-editor-summary", "Edit");
    const body = createElement("div", "node-editor-body");

    if (fields.length || contentSchema) {
      const form = createElement("form", "node-edit-form");
      const grid = createElement("div", "edit-form-grid");
      for (const field of fields) grid.append(makeAttributeEditorField(node, field));
      if (contentSchema) {
        const contentField = createElement("label", "edit-field edit-field-wide");
        contentField.append(
          createElement("span", "edit-field-label", contentSchema.label || "Content"),
        );
        const textarea = createElement("textarea");
        textarea.name = "content";
        textarea.rows = contentSchema.rows || 7;
        textarea.placeholder = contentSchema.placeholder || "";
        if (contentSchema.max_length) textarea.maxLength = contentSchema.max_length;
        textarea.value = node.content || "";
        contentField.append(textarea);
        grid.append(contentField);
      }
      const feedback = createElement("p", "edit-feedback");
      feedback.setAttribute("role", "status");
      const save = createElement("button", "primary-button compact-button", "Save changes");
      save.type = "submit";
      form.append(grid, feedback, save);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        feedback.textContent = "";
        save.disabled = true;
        const payload = {
          node_id: node.id,
          attributes: readAttributeEditor(form),
        };
        if (contentSchema) payload.content = form.elements.content.value;
        try {
          const response = await runMossAction("update_node", payload);
          if (!response.result?.changed?.length) {
            feedback.textContent = "No changes to save.";
            save.disabled = false;
            return;
          }
          await refreshCurrentNode("Changes saved.");
        } catch (error) {
          feedback.textContent = error instanceof Error ? error.message : String(error);
          save.disabled = false;
        }
      });
      body.append(form);
    }

    if (relationshipEditor) body.append(relationshipEditor);
    if (deleteNodeSection) body.append(deleteNodeSection);
    details.append(summary, body);
    return details;
  }

  return { makeNodeEditor };
}
