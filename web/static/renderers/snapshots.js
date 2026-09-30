"use strict";

import { runMossAction, apiJson } from "../api.js?v=24";
import { createElement } from "../dom.js?v=24";


function padNumber(value) {
  return String(value).padStart(2, "0");
}

function defaultSnapshotName() {
  const now = new Date();
  return [
    "moss",
    now.getFullYear(),
    padNumber(now.getMonth() + 1),
    padNumber(now.getDate()),
    `${padNumber(now.getHours())}${padNumber(now.getMinutes())}${padNumber(now.getSeconds())}`,
  ].join("_");
}

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function snapshotRecord(snapshot) {
  const record = createElement("article", "snapshot-record");
  const heading = createElement("div", "snapshot-record-heading");
  const identity = createElement("div");
  identity.append(
    createElement("h2", "snapshot-name", snapshot.name),
    createElement(
      "p",
      "snapshot-created",
      snapshot.created || snapshot.modified || "Creation time unavailable",
    ),
  );
  heading.append(identity);

  if (snapshot.status === "ready" && snapshot.download_url) {
    const download = createElement("a", "secondary-button compact-button", "Download ZIP");
    download.href = snapshot.download_url;
    download.download = `${snapshot.name}.zip`;
    heading.append(download);
  } else {
    heading.append(createElement("span", "snapshot-unreadable", "Unreadable archive"));
  }

  const facts = createElement("p", "snapshot-facts");
  facts.append(
    document.createTextNode(`${formatBytes(snapshot.size_bytes)} · `),
    document.createTextNode(`${Number(snapshot.node_count) || 0} nodes · `),
    document.createTextNode(`${Number(snapshot.file_count) || 0} files · `),
    document.createTextNode(snapshot.moss_version || "MOSS version unavailable"),
  );
  record.append(heading, facts);
  return record;
}

export function createSnapshotView({
  elements,
  renderBreadcrumbs,
  setHistory,
  setShellActive,
  showError,
  showLoading,
  viewState,
}) {
  function renderSnapshots(data, scrollY = 0, message = "") {
    viewState.currentNode = null;
    viewState.currentPath = [];
    elements.content.classList.remove("is-wide");
    setShellActive("snapshots");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "snapshots", type: "system", title: "Snapshots" },
      ],
      "Snapshots",
    );

    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    header.append(
      createElement("p", "eyebrow", "Memory archives"),
      createElement("h1", "search-title", "Snapshots"),
      createElement(
        "p",
        "system-view-description",
        "Snapshots are non-overwriting ZIP archives of memory and the recorded MOSS version. They do not include application source code.",
      ),
    );
    article.append(header);

    const createSection = createElement("section", "snapshot-create-section");
    createSection.append(createElement("h2", "schema-section-title", "Take a snapshot"));
    const form = createElement("form", "snapshot-form");
    const input = createElement("input");
    input.type = "text";
    input.name = "name";
    input.required = true;
    input.maxLength = 80;
    input.pattern = "[a-z0-9_]+";
    input.title = "Use lowercase letters, numbers, and underscores.";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.value = defaultSnapshotName();
    input.setAttribute("aria-label", "Snapshot name");
    const submit = createElement("button", "primary-button compact-button", "Take snapshot");
    submit.type = "submit";
    const feedback = createElement("p", "edit-feedback snapshot-feedback", message);
    feedback.setAttribute("role", "status");
    form.append(input, submit, feedback);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      submit.disabled = true;
      try {
        const response = await runMossAction("snapshot", { name: input.value.trim() });
        await navigateSnapshots({
          replace: true,
          message: `Created ${response.result.name}.`,
        });
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
      }
    });
    createSection.append(form);
    article.append(createSection);

    const snapshots = Array.isArray(data.snapshots) ? data.snapshots : [];
    const list = createElement("section", "snapshot-list");
    list.append(createElement("h2", "schema-section-title", `Saved snapshots (${snapshots.length})`));
    const records = createElement("div", "snapshot-records");
    for (const snapshot of snapshots) records.append(snapshotRecord(snapshot));
    if (!records.childElementCount) {
      records.append(createElement("p", "empty-message", "No snapshots have been saved yet."));
    }
    list.append(records);
    article.append(list);

    elements.content.replaceChildren(article);
    document.title = "Snapshots · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  async function navigateSnapshots(options = {}) {
    showLoading("Reading snapshots…");
    try {
      const data = await apiJson("/api/snapshots");
      const nextState = { view: "snapshots", scrollY: Number(options.scrollY) || 0 };
      setHistory(nextState, "/snapshots", Boolean(options.replace));
      renderSnapshots(data, nextState.scrollY, options.message || "");
    } catch (error) {
      renderBreadcrumbs([
        { id: "home", type: "page", title: "Home" },
        { id: "snapshots", type: "system", title: "Snapshots" },
      ]);
      showError(error, "Unable to open Snapshots");
    }
  }

  return { navigateSnapshots };
}
