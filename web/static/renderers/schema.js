"use strict";

import { apiJson } from "../api.js?v=24";
import { createElement, displayValue, humanLabel } from "../dom.js?v=24";


function schemaValue(value) {
  if (value === "") return "Empty text";
  return displayValue(value);
}

function appendFact(list, label, value) {
  const fact = createElement("div", "schema-fact");
  fact.append(
    createElement("dt", "schema-fact-name", label),
    createElement("dd", "schema-fact-value", value),
  );
  list.append(fact);
}

function editorDescription(attribute) {
  const editor = attribute.editor;
  if (!editor) return attribute.system_managed ? "System managed" : "Read only";
  const parts = [editor.label || humanLabel(attribute.name), humanLabel(editor.input_type)];
  if (editor.required) parts.push("required");
  if (editor.max_length) parts.push(`up to ${editor.max_length} characters`);
  return parts.join(" · ");
}

function appendOptions(container, editor) {
  const values = editor?.choices?.length ? editor.choices : editor?.suggestions;
  if (!values?.length) return;
  const options = createElement("p", "schema-attribute-options");
  options.append(createElement("span", null, editor.choices?.length ? "Choices: " : "Suggestions: "));
  options.append(
    document.createTextNode(
      values.map((item) => `${item.label} (${schemaValue(item.value)})`).join(", "),
    ),
  );
  container.append(options);
}

function makeAttributeRow(attribute) {
  const row = createElement("li", "schema-attribute-row");
  const identity = createElement("div", "schema-attribute-identity");
  identity.append(
    createElement("code", "schema-attribute-name", attribute.name),
    createElement("span", "schema-attribute-type", humanLabel(attribute.type)),
  );
  const details = createElement("div", "schema-attribute-details");
  details.append(createElement("p", null, editorDescription(attribute)));
  if (Object.hasOwn(attribute, "default")) {
    details.append(
      createElement("p", "schema-attribute-default", `Default · ${schemaValue(attribute.default)}`),
    );
  }
  appendOptions(details, attribute.editor);
  row.append(identity, details);
  return row;
}

function makeTypeRecord(nodeType, schema) {
  const record = createElement("details", "node-type-record");
  const summary = createElement("summary", "node-type-summary");
  const attributes = Array.isArray(schema.attributes) ? schema.attributes : [];
  const identity = createElement("span", "node-type-identity");
  identity.append(createElement("span", "node-type-name", humanLabel(nodeType)));
  if (schema.description) {
    identity.append(createElement("span", "node-type-description", schema.description));
  }
  summary.append(
    identity,
    createElement(
      "span",
      "node-type-count",
      `${attributes.length} ${attributes.length === 1 ? "attribute" : "attributes"}`,
    ),
  );

  const body = createElement("div", "node-type-body");
  const facts = createElement("dl", "schema-facts");
  const content = schema.content?.editable
    ? `${schema.content.label || "Content"} · free-form text · up to ${schema.content.max_length} characters`
    : "None";
  appendFact(facts, "Editable content", content);
  appendFact(
    facts,
    "Allowed children",
    schema.allowed_child_types?.length
      ? schema.allowed_child_types.map(humanLabel).join(", ")
      : "None",
  );
  appendFact(
    facts,
    "Create menu",
    schema.child_creation_types?.length
      ? schema.child_creation_types.map(humanLabel).join(", ")
      : "None",
  );
  body.append(facts);

  const attributeSection = createElement("section", "schema-attributes");
  attributeSection.append(createElement("h2", "schema-section-title", "Attributes"));
  if (attributes.length) {
    const list = createElement("ul", "schema-attribute-list");
    for (const attribute of attributes) list.append(makeAttributeRow(attribute));
    attributeSection.append(list);
  } else {
    attributeSection.append(createElement("p", "empty-message", "No attributes."));
  }
  body.append(attributeSection);
  record.append(summary, body);
  return record;
}

function makeActionTypeRecord(action) {
  const record = createElement("details", "node-type-record");
  const summary = createElement("summary", "node-type-summary");
  summary.append(
    createElement("span", "node-type-name", humanLabel(action.name)),
    createElement(
      "span",
      "node-type-count",
      action.browser_available ? "Browser action" : "Core action",
    ),
  );

  const body = createElement("div", "node-type-body");
  const facts = createElement("dl", "schema-facts");
  appendFact(facts, "Registered name", action.name);
  appendFact(
    facts,
    "Web boundary",
    action.browser_available ? "Explicitly allowlisted" : "Not exposed to the browser",
  );
  body.append(
    facts,
    createElement("p", "action-type-description", action.summary || "No description."),
  );
  record.append(summary, body);
  return record;
}

export function createSchemaView({
  elements,
  nodeSchemas,
  renderBreadcrumbs,
  setHistory,
  setShellActive,
  showError,
  showLoading,
  viewState,
}) {
  function renderNodeTypes(scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    elements.content.classList.remove("is-wide");
    setShellActive("node-types");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "node-types", type: "system", title: "Node types" },
      ],
      "Node types",
    );

    const entries = Object.entries(nodeSchemas);
    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    header.append(
      createElement("p", "eyebrow", "Structure reference"),
      createElement("h1", "search-title", "Node types"),
      createElement(
        "p",
        "system-view-description",
        `${entries.length} canonical node types. Open a type to inspect its content, attributes, defaults, and child rules.`,
      ),
    );
    const directory = createElement("section", "node-type-directory");
    for (const [nodeType, schema] of entries) {
      directory.append(makeTypeRecord(nodeType, schema));
    }
    article.append(header, directory);
    elements.content.replaceChildren(article);
    document.title = "Node types · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  function navigateNodeTypes(options = {}) {
    const nextState = {
      view: "node-types",
      scrollY: Number(options.scrollY) || 0,
    };
    setHistory(nextState, "/node-types", Boolean(options.replace));
    renderNodeTypes(nextState.scrollY);
  }

  function renderActionTypes(data, scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    elements.content.classList.remove("is-wide");
    setShellActive("action-types");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "action-types", type: "system", title: "Action types" },
      ],
      "Action types",
    );

    const entries = Array.isArray(data.action_types) ? data.action_types : [];
    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    header.append(
      createElement("p", "eyebrow", "Behavior reference"),
      createElement("h1", "search-title", "Action types"),
      createElement(
        "p",
        "system-view-description",
        `${entries.length} registered actions. Open an action to inspect its purpose and whether the web interface may invoke it.`,
      ),
    );
    const directory = createElement("section", "node-type-directory");
    for (const action of entries) directory.append(makeActionTypeRecord(action));
    article.append(header, directory);
    elements.content.replaceChildren(article);
    document.title = "Action types · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  async function navigateActionTypes(options = {}) {
    showLoading("Reading action types…");
    try {
      const data = await apiJson("/api/action-types");
      const nextState = {
        view: "action-types",
        scrollY: Number(options.scrollY) || 0,
      };
      setHistory(nextState, "/action-types", Boolean(options.replace));
      renderActionTypes(data, nextState.scrollY);
    } catch (error) {
      renderBreadcrumbs([
        { id: "home", type: "page", title: "Home" },
        { id: "action-types", type: "system", title: "Action types" },
      ]);
      showError(error, "Unable to open Action types");
    }
  }

  return { navigateActionTypes, navigateNodeTypes };
}
