"use strict";

import { apiJson } from "../api.js?v=24";
import { createElement, humanLabel, makeLabeledSection } from "../dom.js?v=24";


export function createSystemViews({
  bindNodeLink,
  crumbFor,
  elements,
  renderBreadcrumbs,
  safePath,
  setHistory,
  setShellActive,
  showError,
  showLoading,
  viewState,
}) {
  function bindSystemLink(link, view) {
    link.addEventListener("click", (event) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      event.preventDefault();
      navigateSystemView(view);
    });
    return link;
  }

  function makeSearchForm(initialQuery = "") {
    const form = createElement("form", "memory-search");
    form.setAttribute("role", "search");
    const label = createElement("label", "field-label", "Search memory");
    const row = createElement("div", "memory-search-row");
    const input = createElement("input");
    input.type = "search";
    input.name = "q";
    input.autocomplete = "off";
    input.placeholder = "Find a title, node ID, type, or phrase";
    input.value = initialQuery;
    const submit = createElement("button", null, "Search");
    submit.type = "submit";
    row.append(input, submit);
    label.append(row);
    form.append(label);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      performSearch(input.value);
    });
    return form;
  }

  function renderSearchLanding(scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    elements.content.classList.remove("is-wide");
    setShellActive("search");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "search", type: "search", title: "Search" },
      ],
      "Search",
    );

    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "search-header");
    header.append(
      createElement("p", "eyebrow", "Memory search"),
      createElement("h1", "search-title", "Search memory"),
      createElement("p", "search-summary", "Find a title, node ID, type, or phrase."),
    );
    article.append(header, makeSearchForm());
    elements.content.replaceChildren(article);
    document.title = "Search · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  function navigateSearch(options = {}) {
    const nextState = {
      view: "search",
      query: "",
      scrollY: Number(options.scrollY) || 0,
    };
    setHistory(nextState, "/search", Boolean(options.replace));
    renderSearchLanding(nextState.scrollY);
  }

  function renderSearchResults(data, scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    elements.content.classList.remove("is-wide");
    setShellActive("search");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "search", type: "search", title: "Search" },
      ],
      "Search",
    );

    const article = createElement("article", "node-article");
    const header = createElement("header", "search-header");
    header.append(
      createElement("p", "eyebrow", "Memory search"),
      createElement("h1", "search-title", `Results for “${data.query}”`),
    );
    const count = data.results.length;
    header.append(
      createElement(
        "p",
        "search-summary",
        count ? `${count} ${count === 1 ? "result" : "results"}` : "No results",
      ),
    );
    article.append(header, makeSearchForm(data.query));

    const results = createElement("div", "search-results");
    for (const result of data.results) {
      const link = createElement("a", "search-result");
      bindNodeLink(link, result.id, safePath(result.path, result));
      link.append(
        createElement(
          "span",
          "result-type",
          `Node type · ${String(result.type || "node").replaceAll("_", " ")}`,
        ),
        createElement("span", "field-label card-title-label", "Title"),
        createElement("span", "result-title", result.title || result.id),
        createElement("span", "card-id", `ID · ${result.id}`),
      );
      if (result.snippet) {
        link.append(
          createElement("span", "field-label card-description-label", "Matching text"),
          createElement("span", "result-snippet", result.snippet),
        );
      }
      results.append(link);
    }
    if (!results.childElementCount) {
      results.append(
        createElement(
          "div",
          "missing-node",
          "No nodes matched this search. Try a title, node ID, type, or phrase.",
        ),
      );
    }
    article.append(results);
    elements.content.replaceChildren(article);
    document.title = `Search: ${data.query} · MOSS`;
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  async function performSearch(query, options = {}) {
    const cleanQuery = String(query || "").trim();
    if (!cleanQuery) return;
    showLoading("Searching memory…");
    try {
      const data = await apiJson(`/api/search?q=${encodeURIComponent(cleanQuery)}`);
      const nextState = {
        view: "search",
        query: cleanQuery,
        scrollY: Number(options.scrollY) || 0,
      };
      setHistory(
        nextState,
        `/search?q=${encodeURIComponent(cleanQuery)}`,
        Boolean(options.replace),
      );
      renderSearchResults(data, nextState.scrollY);
    } catch (error) {
      renderBreadcrumbs([
        { id: "home", type: "page", title: "Home" },
        { id: "search", type: "search", title: "Search" },
      ]);
      showError(error, "Unable to search memory");
    }
  }

  function makeTocHeader() {
    const header = createElement("div", "toc-table-header");
    header.append(
      createElement("span", "toc-header-spacer", ""),
      createElement("span", null, "Title"),
      createElement("span", null, "ID"),
      createElement("span", null, "Node type"),
    );
    return header;
  }

  function makeTocBranch(item, parentPath = null, depth = 0) {
    const branch = createElement("li", "toc-branch");
    const row = createElement("div", "toc-row");
    row.style.setProperty("--toc-depth", String(depth));
    const children = Array.isArray(item.children) ? item.children : [];
    const path = Array.isArray(parentPath) ? [...parentPath, crumbFor(item)] : null;

    let toggle;
    if (children.length) {
      const expanded = depth === 0;
      toggle = createElement("button", "toc-toggle", expanded ? "−" : "+");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.setAttribute(
        "aria-label",
        `${expanded ? "Collapse" : "Expand"} children of ${item.title || item.id}`,
      );
      row.append(toggle);
    } else {
      row.append(createElement("span", "toc-leaf", "·"));
    }

    const title = createElement("a", "toc-title", item.title || item.id);
    if (item.missing) {
      title.classList.add("is-missing");
      title.removeAttribute("href");
    } else {
      bindNodeLink(title, item.id, path);
    }
    row.append(
      title,
      createElement("span", "toc-id", item.id),
      createElement("span", "toc-type", humanLabel(item.type || "node")),
    );
    if (item.repeated_reference) {
      row.append(createElement("span", "toc-reference", "Repeated reference"));
    }
    branch.append(row);

    if (children.length) {
      const childList = createElement("ul", "toc-children");
      childList.hidden = depth !== 0;
      for (const child of children) {
        childList.append(makeTocBranch(child, path, depth + 1));
      }
      toggle.addEventListener("click", () => {
        const expanded = toggle.getAttribute("aria-expanded") === "true";
        toggle.setAttribute("aria-expanded", String(!expanded));
        toggle.textContent = expanded ? "+" : "−";
        toggle.setAttribute(
          "aria-label",
          `${expanded ? "Expand" : "Collapse"} children of ${item.title || item.id}`,
        );
        childList.hidden = expanded;
      });
      branch.append(childList);
    }
    return branch;
  }

  function renderMemoryMap(data, scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    viewState.tree = data;
    setShellActive("tree");
    elements.content.classList.remove("is-wide");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "tree", type: "system", title: "Memory map" },
      ],
      "Memory map",
    );

    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    header.append(
      createElement("p", "eyebrow", "Structure view"),
      createElement("p", "field-label", "View title"),
      createElement("h1", "search-title", "Memory map"),
      createElement(
        "p",
        "system-view-description",
        "A compact table of contents for the navigable hierarchy beneath Home.",
      ),
    );
    article.append(header);

    const mapSection = makeLabeledSection("Contents", "toc-section");
    const contents = createElement("div", "toc-table");
    contents.append(makeTocHeader());
    const tree = createElement("ul", "toc-tree");
    tree.append(makeTocBranch(data.root, [], 0));
    contents.append(tree);
    mapSection.append(contents);
    article.append(mapSection);

    const orphanedNodes = Array.isArray(data.orphaned_nodes) ? data.orphaned_nodes : [];
    const orphaned = makeLabeledSection(
      `Orphaned nodes (${orphanedNodes.length})`,
      "orphaned-nodes-section",
    );
    orphaned.append(
      createElement(
        "p",
        "orphaned-nodes-description",
        "Nodes outside the hierarchy reachable from Home.",
      ),
    );
    const orphanedTable = createElement("div", "toc-table");
    orphanedTable.append(makeTocHeader());
    const orphanedList = createElement("ul", "toc-tree toc-orphans");
    for (const item of orphanedNodes) orphanedList.append(makeTocBranch(item));
    if (!orphanedList.childElementCount) {
      orphanedList.append(createElement("li", "empty-message", "No orphaned nodes."));
    }
    orphanedTable.append(orphanedList);
    orphaned.append(orphanedTable);
    article.append(orphaned);

    elements.content.replaceChildren(article);
    document.title = "Memory map · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  function renderActionLog(data, scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    setShellActive("action-log");
    elements.content.classList.remove("is-wide");
    renderBreadcrumbs(
      [
        { id: "home", type: "page", title: "Home" },
        { id: "action-log", type: "system", title: "Action log" },
      ],
      "Action log",
    );

    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    const shownCount = Array.isArray(data.entries) ? data.entries.length : 0;
    const totalCount = Number(data.total) || shownCount;
    const summary = shownCount < totalCount
      ? `${shownCount} of ${totalCount} actions · newest first`
      : `${totalCount} actions · newest first`;
    header.append(
      createElement("h1", "search-title", "Action log"),
      createElement("p", "search-summary", summary),
    );
    article.append(header);

    const section = makeLabeledSection("Entries", "action-log-section");
    const entries = createElement("ol", "action-log-list");
    const knownKinds = new Set(["create", "change", "link", "remove", "session"]);
    for (const entry of data.entries || []) {
      const row = createElement("li", "action-log-entry");
      const kind = knownKinds.has(entry.kind) ? entry.kind : "other";
      row.classList.add(`is-${kind}`);
      row.append(createElement("span", "log-kind", humanLabel(entry.verb || kind)));
      if (entry.timestamp) {
        row.append(createElement("time", "log-time", entry.timestamp));
      } else {
        row.append(createElement("span", "log-time", "No timestamp"));
      }
      row.append(
        createElement("span", "log-action", entry.action),
        createElement("span", "log-line", `#${entry.line}`),
      );
      entries.append(row);
    }
    if (!entries.childElementCount) {
      entries.append(createElement("li", "empty-message", "No actions have been recorded."));
    }
    section.append(entries);
    article.append(section);
    elements.content.replaceChildren(article);
    document.title = "Action log · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  function renderChangeLog(data, scrollY = 0) {
    viewState.currentNode = null;
    viewState.currentPath = [];
    setShellActive("change-log");
    elements.content.classList.remove("is-wide");
    renderBreadcrumbs([
      { id: "home", type: "page", title: "Home" },
      { id: "change-log", type: "system", title: "MOSS Change log" },
    ], "MOSS Change log");
    const article = createElement("article", "node-article system-view");
    const header = createElement("header", "system-view-header");
    header.append(
      createElement("h1", "search-title", "MOSS Change log"),
      createElement("p", "search-summary", data.current_version
        ? `Current version: ${data.current_version} · newest first`
        : "No releases have been recorded."),
      createElement("p", "search-summary", "Code releases are recorded here. Commands and memory changes are recorded in Action log."),
    );
    article.append(header);
    for (const entry of data.entries || []) {
      const section = makeLabeledSection(entry.version, "change-log-release");
      section.append(createElement("time", "log-time", entry.date));
      const changes = createElement("ul");
      for (const change of entry.changes) {
        changes.append(createElement("li", null, change));
      }
      section.append(changes);
      article.append(section);
    }
    elements.content.replaceChildren(article);
    document.title = "MOSS Change log · MOSS";
    requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
  }

  async function navigateSystemView(view, options = {}) {
    showLoading(view === "tree" ? "Mapping memory…" : `Reading ${humanLabel(view)}…`);
    try {
      const data = await apiJson(`/api/${view}`);
      const nextState = { view, scrollY: Number(options.scrollY) || 0 };
      setHistory(nextState, `/${view}`, Boolean(options.replace));
      if (view === "tree") {
        renderMemoryMap(data, nextState.scrollY);
      } else if (view === "change-log") {
        renderChangeLog(data, nextState.scrollY);
      } else {
        renderActionLog(data, nextState.scrollY);
      }
    } catch (error) {
      renderBreadcrumbs([
        { id: "home", type: "page", title: "Home" },
        { id: view, type: "system", title: humanLabel(view) },
      ]);
      showError(error, `Unable to open ${humanLabel(view)}`);
    }
  }

  return { bindSystemLink, navigateSearch, navigateSystemView, performSearch };
}
