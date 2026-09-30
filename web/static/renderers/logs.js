"use strict";

import { runMossAction } from "../api.js?v=24";
import { createElement } from "../dom.js?v=24";


function choiceIndex(prompt, value) {
  return (prompt.options || []).findIndex(
    (option) => typeof option === typeof value && option === value,
  );
}

function localToday() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function makeAnswerFields(prompts, currentAnswers = {}, useToday = false) {
  const grid = createElement("div", "log-answer-grid");
  const controls = new Map();
  for (const prompt of prompts) {
    const field = createElement("label", "edit-field log-answer-field");
    field.append(createElement("span", "edit-field-label", prompt.label));
    let control;
    const current = Object.hasOwn(currentAnswers, prompt.id)
      ? currentAnswers[prompt.id]
      : "";
    if (prompt.type === "choice") {
      control = createElement("select");
      if (!prompt.required) {
        const blank = createElement("option", null, "—");
        blank.value = "";
        control.append(blank);
      }
      for (const [index, optionValue] of (prompt.options || []).entries()) {
        const option = createElement("option", null, String(optionValue));
        option.value = String(index);
        option.selected = choiceIndex(prompt, current) === index;
        control.append(option);
      }
    } else if (prompt.type === "date") {
      control = createElement("input");
      control.type = "date";
      control.value = current || (useToday ? localToday() : "");
    } else {
      control = createElement("textarea");
      control.rows = 4;
      control.value = current || "";
      field.classList.add("is-wide");
    }
    control.required = Boolean(prompt.required);
    control.name = prompt.id;
    controls.set(prompt.id, control);
    field.append(control);
    grid.append(field);
  }
  return {
    element: grid,
    answers() {
      const values = {};
      for (const prompt of prompts) {
        const control = controls.get(prompt.id);
        if (prompt.type === "choice") {
          values[prompt.id] = control.value === ""
            ? ""
            : prompt.options[Number(control.value)];
        } else {
          values[prompt.id] = control.value;
        }
      }
      return values;
    },
  };
}

function appendAnswerList(container, prompts, answers) {
  const list = createElement("dl", "log-answer-list");
  for (const prompt of prompts) {
    const item = createElement("div", "log-answer-item");
    const value = answers?.[prompt.id];
    item.append(
      createElement("dt", "log-answer-label", prompt.label),
      createElement("dd", "log-answer-value", value === "" || value == null ? "—" : String(value)),
    );
    list.append(item);
  }
  container.append(list);
}

function parseChoiceOptions(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean).map((part) => (
    /^-?\d+$/.test(part) ? Number(part) : part
  ));
}

function makeTemplateEditor(node, refreshCurrentNode) {
  const details = createElement("details", "log-template-editor");
  details.append(createElement("summary", "log-template-summary", "Edit prompts"));
  const form = createElement("form", "log-template-form");
  const intro = createElement(
    "p",
    "log-editor-note",
    "Changes apply to future entries. Previous entries keep the prompts they used.",
  );
  const rows = createElement("div", "log-prompt-rows");
  const prompts = Array.isArray(node.prompts)
    ? node.prompts.map((prompt) => ({ ...prompt, options: [...(prompt.options || [])] }))
    : [];

  function renderRows() {
    rows.replaceChildren();
    prompts.forEach((prompt, index) => {
      const row = createElement("fieldset", "log-prompt-row");
      const legend = createElement("legend", null, `Prompt ${index + 1}`);
      const grid = createElement("div", "log-prompt-grid");

      const idField = createElement("label", "edit-field");
      idField.append(createElement("span", "edit-field-label", "Stable ID"));
      const idInput = createElement("input");
      idInput.value = prompt.id;
      idInput.pattern = "[a-z][a-z0-9_]{0,63}";
      idInput.required = true;
      idInput.addEventListener("input", () => { prompt.id = idInput.value; });
      idField.append(idInput);

      const labelField = createElement("label", "edit-field");
      labelField.append(createElement("span", "edit-field-label", "Label"));
      const labelInput = createElement("input");
      labelInput.value = prompt.label;
      labelInput.required = true;
      labelInput.maxLength = 120;
      labelInput.addEventListener("input", () => { prompt.label = labelInput.value; });
      labelField.append(labelInput);

      const typeField = createElement("label", "edit-field");
      typeField.append(createElement("span", "edit-field-label", "Answer type"));
      const typeSelect = createElement("select");
      for (const [value, label] of [["text", "Free text"], ["date", "Date"], ["choice", "Restricted choices"]]) {
        const option = createElement("option", null, label);
        option.value = value;
        option.selected = prompt.type === value;
        typeSelect.append(option);
      }
      typeField.append(typeSelect);

      const optionsField = createElement("label", "edit-field");
      optionsField.append(createElement("span", "edit-field-label", "Choices (comma separated)"));
      const optionsInput = createElement("input");
      optionsInput.value = (prompt.options || []).join(", ");
      optionsInput.addEventListener("input", () => {
        prompt.options = parseChoiceOptions(optionsInput.value);
      });
      optionsField.append(optionsInput);

      const requiredField = createElement("label", "edit-field is-checkbox");
      const requiredInput = createElement("input");
      requiredInput.type = "checkbox";
      requiredInput.checked = Boolean(prompt.required);
      requiredInput.addEventListener("change", () => { prompt.required = requiredInput.checked; });
      requiredField.append(requiredInput, createElement("span", "edit-field-label", "Required"));

      const controls = createElement("div", "log-prompt-controls");
      for (const [label, delta] of [["↑", -1], ["↓", 1]]) {
        const button = createElement("button", "quiet-button", label);
        button.type = "button";
        button.disabled = index + delta < 0 || index + delta >= prompts.length;
        button.setAttribute("aria-label", `Move prompt ${delta < 0 ? "up" : "down"}`);
        button.addEventListener("click", () => {
          const [moved] = prompts.splice(index, 1);
          prompts.splice(index + delta, 0, moved);
          renderRows();
        });
        controls.append(button);
      }
      const remove = createElement("button", "quiet-button is-danger", "Remove");
      remove.type = "button";
      remove.disabled = prompts.length === 1;
      remove.addEventListener("click", () => {
        prompts.splice(index, 1);
        renderRows();
      });
      controls.append(remove);

      const updateType = () => {
        prompt.type = typeSelect.value;
        optionsField.hidden = prompt.type !== "choice";
        if (prompt.type === "choice" && !prompt.options?.length) {
          prompt.options = [0, 1, 3];
          optionsInput.value = "0, 1, 3";
        }
      };
      typeSelect.addEventListener("change", updateType);
      updateType();
      grid.append(idField, labelField, typeField, optionsField, requiredField);
      row.append(legend, grid, controls);
      rows.append(row);
    });
  }
  renderRows();

  const add = createElement("button", "secondary-button compact-button", "Add prompt");
  add.type = "button";
  add.addEventListener("click", () => {
    let number = prompts.length + 1;
    let id = `prompt_${number}`;
    while (prompts.some((prompt) => prompt.id === id)) id = `prompt_${++number}`;
    prompts.push({ id, label: "New prompt", type: "text", required: false });
    renderRows();
  });
  const feedback = createElement("p", "edit-feedback");
  feedback.setAttribute("role", "status");
  const save = createElement("button", "primary-button compact-button", "Save prompt template");
  save.type = "submit";
  form.append(intro, rows, add, feedback, save);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    save.disabled = true;
    try {
      const response = await runMossAction("update_log_template", {
        node_id: node.id,
        prompts,
      });
      if (!response.result?.changed) {
        feedback.textContent = "No prompt changes to save.";
        save.disabled = false;
        return;
      }
      await refreshCurrentNode("Prompt template updated. Previous entries were preserved.");
    } catch (error) {
      feedback.textContent = error instanceof Error ? error.message : String(error);
      save.disabled = false;
    }
  });
  details.append(form);
  return details;
}

export function createLogRenderers({ bindNodeLink, crumbFor, makeHeadingLink, refreshCurrentNode }) {
  function renderLogEntry(node, path, direct = false) {
    const section = createElement("section", "log-entry-panel");
    const prompts = Array.isArray(node.prompts) ? node.prompts : [];
    appendAnswerList(section, prompts, node.answers || {});
    if (direct && prompts.length) {
      const editor = createElement("details", "log-entry-editor");
      editor.append(createElement("summary", null, "Correct this entry"));
      const form = createElement("form", "log-entry-edit-form");
      const answerFields = makeAnswerFields(prompts, node.answers || {});
      const feedback = createElement("p", "edit-feedback");
      feedback.setAttribute("role", "status");
      const save = createElement("button", "primary-button compact-button", "Save correction");
      save.type = "submit";
      form.append(answerFields.element, feedback, save);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        feedback.textContent = "";
        save.disabled = true;
        try {
          const response = await runMossAction("update_log_entry", {
            node_id: node.id,
            answers: answerFields.answers(),
          });
          if (!response.result?.changed) {
            feedback.textContent = "No corrections to save.";
            save.disabled = false;
            return;
          }
          await refreshCurrentNode("Log entry corrected.");
        } catch (error) {
          feedback.textContent = error instanceof Error ? error.message : String(error);
          save.disabled = false;
        }
      });
      editor.append(form);
      section.append(editor);
    }
    return section;
  }

  function makeHistory(node, path) {
    const entries = (node.child_nodes || []).filter((child) => child.type === "log_entry");
    entries.sort((left, right) => {
      const leftKey = `${left.entry_date || ""}|${left.submitted_at || ""}`;
      const rightKey = `${right.entry_date || ""}|${right.submitted_at || ""}`;
      return rightKey.localeCompare(leftKey);
    });
    const history = createElement("details", "log-history");
    history.append(createElement(
      "summary",
      "log-history-summary",
      `Previous entries (${entries.length})`,
    ));
    const list = createElement("div", "log-history-list");
    if (!entries.length) {
      list.append(createElement("p", "empty-message", "No entries yet."));
    }
    for (const entry of entries) {
      const item = createElement("details", "log-history-item");
      const summary = createElement("summary", "log-history-item-summary");
      const link = createElement("a", null, entry.entry_date || entry.display_title || entry.id);
      bindNodeLink(link, entry.id, [...path, crumbFor(entry)]);
      summary.append(link);
      item.append(summary);
      appendAnswerList(item, entry.prompts || [], entry.answers || {});
      list.append(item);
    }
    history.append(list);
    return history;
  }

  function renderLog(node, path, direct = false) {
    const panel = createElement("section", "log-panel");
    if (!direct) {
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      const entryCount = Array.isArray(node.children) ? node.children.length : 0;
      panel.append(heading);
      if (node.description) {
        panel.append(createElement("p", "linked-node-description", node.description));
      }
      panel.append(
        createElement("p", "log-summary", `${entryCount} saved ${entryCount === 1 ? "entry" : "entries"}.`),
      );
      const open = makeHeadingLink(node, path);
      open.className = "secondary-button compact-button log-open-link";
      open.textContent = "Open log";
      panel.append(open);
      return panel;
    }

    const prompts = Array.isArray(node.prompts) ? node.prompts : [];
    if (prompts.length) {
      const start = createElement("button", "secondary-button compact-button", "Close instance");
      start.type = "button";
      const form = createElement("form", "log-instance-form");
      form.hidden = false;
      const answerFields = makeAnswerFields(prompts, {}, true);
      const feedback = createElement("p", "edit-feedback");
      feedback.setAttribute("role", "status");
      const submit = createElement("button", "primary-button compact-button", "Save entry");
      submit.type = "submit";
      form.append(createElement("h2", "section-heading", "New entry"), answerFields.element, feedback, submit);
      start.addEventListener("click", () => {
        form.hidden = !form.hidden;
        start.textContent = form.hidden ? "Start instance" : "Close instance";
        if (!form.hidden) form.querySelector("input, select, textarea")?.focus();
      });
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        feedback.textContent = "";
        submit.disabled = true;
        try {
          await runMossAction("submit_log_entry", {
            log_id: node.id,
            answers: answerFields.answers(),
          });
          await refreshCurrentNode("Log entry saved.");
        } catch (error) {
          feedback.textContent = error instanceof Error ? error.message : String(error);
          submit.disabled = false;
        }
      });
      panel.append(start, form);
    } else {
      panel.append(createElement("p", "empty-message", "Add prompts before starting this log."));
    }
    panel.append(makeHistory(node, path), makeTemplateEditor(node, refreshCurrentNode));
    return panel;
  }

  return { renderLog, renderLogEntry };
}
