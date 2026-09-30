"use strict";

import { apiJson, loadSchema } from "./api.js?v=24";
import {
  appendLabeledText,
  appendText,
  createElement,
  displayValue,
  humanLabel,
  makeLabeledSection,
  shortExcerpt,
  textDisplayTitle,
} from "./dom.js?v=24";
import { createEditors } from "./editors.js?v=24";
import { createCalendarRenderers, formatWeekRange, parseDateOnly } from "./renderers/calendar.js?v=24";
import { createContentRenderers } from "./renderers/content.js?v=24";
import { createMaterialRenderers } from "./renderers/materials.js?v=24";
import { createItemRenderers } from "./renderers/items.js?v=24";
import { createLogRenderers } from "./renderers/logs.js?v=24";
import { createSchemaView } from "./renderers/schema.js?v=24";
import { createSnapshotView } from "./renderers/snapshots.js?v=24";
import { createSystemViews } from "./renderers/system.js?v=24";
import { createTodoRenderers } from "./renderers/todos.js?v=24";


const elements = {
  brandHome: document.querySelector("#brand-home"),
  breadcrumbs: document.querySelector("#breadcrumbs"),
  content: document.querySelector("#content"),
  navHome: document.querySelector("#nav-home"),
  navActionTypes: document.querySelector("#nav-action-types"),
  navNodeTypes: document.querySelector("#nav-node-types"),
  navSearch: document.querySelector("#nav-search"),
  navSnapshots: document.querySelector("#nav-snapshots"),
  navTree: document.querySelector("#nav-tree"),
  navActionLog: document.querySelector("#nav-action-log"),
  navChangeLog: document.querySelector("#nav-change-log"),
};

const viewState = {
  currentNode: null,
  currentPath: [],
  tree: null,
};

let makeNodeEditor;
let makeEventCard;
let makeTodoComposer;
let navigateSystemView;
let navigateActionTypes;
let navigateNodeTypes;
let navigateSearch;
let navigateSnapshots;
let performSearch;
let renderCalendar;
let renderEventDetail;
let renderFallback;
let renderImage;
let renderInternalLink;
let renderItem;
let renderItemList;
let renderLog;
let renderLogEntry;
let renderLink;
let renderNote;
let renderRandomizer;
let renderTodoItem;
let renderTodoList;
let renderWeek;


function crumbFor(node) {
  return {
    id: node.id,
    type: node.type,
    title: node.display_title || node.title || node.id,
  };
}

function safePath(path, finalNode) {
  const clean = Array.isArray(path)
    ? path.filter((item) => item && typeof item.id === "string").map((item) => ({
        id: item.id,
        type: item.type || "node",
        title: item.title || item.display_title || item.id,
      }))
    : [];
  if (!clean.length && finalNode) {
    clean.push({ id: "home", type: "page", title: "Home" });
  }
  if (finalNode && clean.at(-1)?.id !== finalNode.id) {
    clean.push(crumbFor(finalNode));
  }
  return clean;
}

function nodeUrl(nodeId) {
  return `/node/${encodeURIComponent(nodeId)}`;
}

function bindNodeLink(link, nodeId, path) {
  link.href = nodeUrl(nodeId);
  link.addEventListener("click", (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey
    ) return;
    event.preventDefault();
    navigateNode(nodeId, path);
  });
  return link;
}

function saveCurrentScroll() {
  if (!history.state) return;
  history.replaceState(
    { ...history.state, scrollY: window.scrollY },
    "",
    window.location.href,
  );
}

function setHistory(nextState, url, replace) {
  if (!replace) saveCurrentScroll();
  if (replace) history.replaceState(nextState, "", url);
  else history.pushState(nextState, "", url);
}

function showLoading(message = "Opening memory…") {
  const card = createElement("div", "loading-card");
  card.append(createElement("span", "loading-leaf"), document.createTextNode(message));
  card.firstElementChild.setAttribute("aria-hidden", "true");
  elements.content.replaceChildren(card);
}

function showError(error, heading = "Unable to open this node") {
  const card = createElement("div", "error-card");
  card.append(
    createElement("h1", null, heading),
    createElement("p", null, error instanceof Error ? error.message : String(error)),
  );
  elements.content.replaceChildren(card);
  document.title = "MOSS · Read error";
}

function renderBreadcrumbs(path, currentLabel) {
  const fragment = document.createDocumentFragment();
  if (!path.length && currentLabel) path = [{ id: "home", title: "Home", type: "page" }];
  path.forEach((item, index) => {
    if (index) fragment.append(createElement("span", "breadcrumb-separator", "/"));
    if (index === path.length - 1) {
      fragment.append(createElement("span", "breadcrumb-current", currentLabel || item.title || item.id));
      return;
    }
    const link = createElement("a", "breadcrumb-link", item.title || item.id);
    bindNodeLink(link, item.id, path.slice(0, index + 1));
    fragment.append(link);
  });
  elements.breadcrumbs.replaceChildren(fragment);
}

function setShellActive(view) {
  for (const [name, link] of [
    ["home", elements.navHome],
    ["action-types", elements.navActionTypes],
    ["node-types", elements.navNodeTypes],
    ["search", elements.navSearch],
    ["snapshots", elements.navSnapshots],
    ["tree", elements.navTree],
    ["action-log", elements.navActionLog],
    ["change-log", elements.navChangeLog],
  ]) {
    if (name === view) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}

function appendMetadataItem(list, label, value) {
  const item = createElement("div", "attribute-item");
  item.append(
    createElement("dt", "attribute-name", label),
    createElement("dd", "attribute-value", displayValue(value)),
  );
  list.append(item);
}

function appendReferenceMetadata(list, label, nodeIds) {
  const item = createElement("div", "attribute-item attribute-item-wide");
  item.append(createElement("dt", "attribute-name", label));
  const value = createElement("dd", "attribute-value attribute-links");
  for (const nodeId of nodeIds || []) {
    const link = createElement("a", null, nodeId);
    bindNodeLink(link, nodeId, null);
    value.append(link);
  }
  if (!value.childElementCount) value.textContent = "—";
  item.append(value);
  list.append(item);
}

function makeNodeMetadata(node) {
  const section = createElement("details", "node-metadata");
  const summary = createElement("summary", "node-metadata-summary");
  const list = createElement("dl", "attribute-grid");
  appendMetadataItem(list, "Node type", humanLabel(node.type || "node"));
  appendMetadataItem(list, "ID", node.id);
  appendMetadataItem(list, "Description visible", node.description_visible);
  appendMetadataItem(list, "Child count", (node.children || []).length);
  appendReferenceMetadata(list, "Parent references", node.parents);
  appendReferenceMetadata(list, "Child references", node.children);
  const shown = new Set(["description_visible"]);
  for (const [name, value] of Object.entries(node.attributes || {})) {
    if (!shown.has(name)) appendMetadataItem(list, humanLabel(name), value);
  }
  if (node.type === "todo_item") {
    appendMetadataItem(list, "Checked", node.checked);
    appendMetadataItem(list, "Date completed", node.date_completed);
  }
  if (node.type === "week") appendMetadataItem(list, "Completed", node.completed);
  if (node.type === "randomizer") appendMetadataItem(list, "Selection count", node.count);
  if (node.type === "image") {
    appendMetadataItem(list, "Material source", node.source);
    appendMetadataItem(list, "Material status", humanLabel(node.material_status));
  }
  if (node.type === "log_entry") {
    appendMetadataItem(list, "Log", node.log_id);
    appendMetadataItem(list, "Entry date", node.entry_date);
    appendMetadataItem(list, "Submitted", node.submitted_at);
  }
  summary.append(
    createElement("span", "field-label", "Node attributes"),
    createElement("span", "node-metadata-count", `${list.childElementCount} fields`),
  );
  section.append(summary, list);
  return section;
}

function appendNodeHeader(article, node, options = {}) {
  const header = createElement("header", "node-header");
  header.append(createElement("p", "eyebrow", options.eyebrow || "Node record"));
  if (options.showTitle !== false) {
    header.append(createElement("p", "field-label", "Title"));
    header.append(createElement("h1", "node-title", node.display_title || node.title || node.id));
  }
  if (options.showDescription !== false && node.description_visible && node.description) {
    const description = makeLabeledSection("Description", "node-description-block");
    description.append(createElement("p", "node-description", node.description));
    header.append(description);
  }
  if (options.showMetadata !== false) header.append(makeNodeMetadata(node));
  article.append(header);
}

function makeCard(node, path) {
  const link = createElement("a", "node-card");
  bindNodeLink(link, node.id, path);
  link.append(createElement("span", "card-title", node.display_title || node.title || node.id));
  if (node.description_visible && node.description) {
    link.append(createElement("span", "card-description", node.description));
  } else if (node.type === "note" && node.content) {
    link.append(createElement("span", "card-description", shortExcerpt(node.content, 150)));
  }
  link.append(createElement("span", "card-id", `ID · ${node.id}`));
  return link;
}

function makeLinkedNodeSection(node, path) {
  const section = createElement("section", "linked-node-section");
  const heading = createElement("h2", "section-heading");
  heading.append(makeHeadingLink(node, path));
  section.append(heading);
  if (node.description_visible && node.description) {
    section.append(createElement("p", "linked-node-description", node.description));
  } else if (node.type === "note" && node.content) {
    section.append(createElement("p", "linked-node-description", shortExcerpt(node.content, 240)));
  }
  return section;
}

function beginsPageSection(node) {
  if (["text", "image"].includes(node.type)) return false;
  if (node.type === "week") return true;
  return Boolean(node.title);
}

function showActionNotice(message, isError = false) {
  const notice = createElement("p", `action-notice${isError ? " is-error" : ""}`, message);
  const header = elements.content.querySelector(".node-header");
  if (header) header.after(notice);
  else elements.content.prepend(notice);
}

async function refreshCurrentNode(message) {
  const currentId = viewState.currentNode?.id;
  if (!currentId) return;
  const node = await apiJson(`/api/node/${encodeURIComponent(currentId)}`);
  await displayNode(node, viewState.currentPath, window.scrollY);
  if (message) showActionNotice(message);
}

async function deleteCurrentNode(node) {
  const parentPath = viewState.currentPath.slice(0, -1);
  const parent = parentPath.at(-1) || { id: "home", type: "page", title: "Home" };
  await navigateNode(parent.id, parentPath.length ? parentPath : null, { replace: true });
  showActionNotice(`Deleted ${node.display_title || node.title || node.id}.`);
}

function makeHeadingLink(node, path) {
  const link = createElement("a", null, node.display_title || node.title || node.id);
  bindNodeLink(link, node.id, path);
  return link;
}

async function renderEmbedded(node, path) {
  if (node.missing) return createElement("div", "missing-node", `Missing child node: ${node.id}`);
  switch (node.type) {
    case "page":
      return makeLinkedNodeSection(node, path);
    case "note": return renderNote(node, path);
    case "item_list": return renderItemList(node, path);
    case "item": return renderItem(node, path);
    case "text": {
      const block = createElement("section", "inline-block");
      const link = makeHeadingLink({ ...node, display_title: textDisplayTitle(node) }, path);
      link.className = "flow-text-link";
      link.replaceChildren();
      link.title = `Open ${textDisplayTitle(node)} text node`;
      appendText(link, node.content, node);
      block.append(link);
      return block;
    }
    case "todo_list": return renderTodoList(node, path);
    case "todo_item": {
      const panel = createElement("section", "todo-panel");
      const list = createElement("ul", "todo-list");
      list.append(renderTodoItem(node, path));
      panel.append(list);
      return panel;
    }
    case "image": return renderImage(node, path);
    case "randomizer": return renderRandomizer(node, path);
    case "calendar": return renderCalendar(node, path);
    case "link": return renderLink(node, path);
    case "internal_link": return renderInternalLink(node, path);
    case "log": return renderLog(node, path);
    case "log_entry": return renderLogEntry(node, path);
    case "week": return renderWeek(node, path);
    case "event": return makeEventCard(node, path);
    default: return renderFallback(node, path);
  }
}

async function renderPage(article, node, path) {
  appendNodeHeader(article, node, {
    eyebrow: node.id === "home" ? "Home node" : "Page node",
    showMetadata: node.id !== "home",
  });
  if (node.id === "home") article.append(makeNodeMetadata(node));
  const children = Array.isArray(node.child_nodes) ? node.child_nodes : [];
  const childSection = createElement("section", "page-body");
  if (!children.length) {
    childSection.append(createElement("p", "empty-message", "This page has no children."));
    article.append(childSection);
    return;
  }
  const stack = createElement("div", "children-stack");
  for (const child of children) {
    const childPath = [...path, crumbFor(child)];
    const rendered = await renderEmbedded(child, childPath);
    rendered.classList.add("page-child");
    if (beginsPageSection(child)) rendered.classList.add("starts-section");
    stack.append(rendered);
  }
  childSection.append(stack);
  article.append(childSection);
}

async function renderDirectNode(article, node, path) {
  switch (node.type) {
    case "page": await renderPage(article, node, path); return;
    case "text":
      appendNodeHeader(article, { ...node, display_title: textDisplayTitle(node) }, {
        eyebrow: "Text node", showDescription: false,
      });
      appendLabeledText(article, "Content", node.content, node);
      return;
    case "note":
      appendNodeHeader(article, node, { eyebrow: "Note node", showDescription: false });
      appendLabeledText(article, "Content", node.content, node);
      return;
    case "item_list":
      appendNodeHeader(article, node, { eyebrow: "Item list node", showDescription: false });
      article.append(renderItemList(node, path, true));
      return;
    case "item":
      appendNodeHeader(article, node, { eyebrow: "Item node", showDescription: false });
      article.append(renderItem(node));
      return;
    case "todo_list":
      appendNodeHeader(article, node, { eyebrow: "Todo list node", showDescription: false });
      article.append(await renderTodoList(node, path, true));
      return;
    case "todo_item": {
      appendNodeHeader(article, node, { eyebrow: "Todo item node", showDescription: false });
      const panel = createElement("section", "todo-panel");
      const list = createElement("ul", "todo-list");
      list.append(renderTodoItem(node, path));
      panel.append(list, makeTodoComposer(node, {
        label: "New child todo",
        placeholder: "Add a child todo…",
        buttonLabel: "Add child todo",
        successMessage: "Child todo added.",
      }));
      article.append(panel);
      return;
    }
    case "image":
      appendNodeHeader(article, node, { eyebrow: "Image node", showDescription: false });
      article.append(renderImage(node, path, true)); return;
    case "randomizer":
      appendNodeHeader(article, node, { eyebrow: "Randomizer node", showDescription: false });
      article.append(renderRandomizer(node, path, true)); return;
    case "calendar":
      appendNodeHeader(article, node, { eyebrow: "Calendar node", showDescription: false });
      article.append(renderCalendar(node, path, true)); return;
    case "week": {
      const weekTitle = node.title || formatWeekRange(parseDateOnly(node.start_date));
      appendNodeHeader(article, { ...node, display_title: weekTitle }, {
        eyebrow: "Week node", showDescription: false,
      });
      article.append(renderWeek(node, path, true)); return;
    }
    case "event":
      appendNodeHeader(article, node, { eyebrow: "Event node", showDescription: false });
      article.append(renderEventDetail(node)); return;
    case "link":
      appendNodeHeader(article, node, { eyebrow: "Link node", showDescription: false });
      article.append(renderLink(node, path, true)); return;
    case "internal_link":
      appendNodeHeader(article, node, { eyebrow: "Internal link node", showDescription: false });
      article.append(renderInternalLink(node, path, true)); return;
    case "log":
      appendNodeHeader(article, node, { eyebrow: "Log node" });
      article.append(renderLog(node, path, true)); return;
    case "log_entry":
      appendNodeHeader(article, node, { eyebrow: "Log entry", showDescription: false });
      article.append(renderLogEntry(node, path, true)); return;
    default:
      appendNodeHeader(article, node, { eyebrow: "MOSS node", showDescription: false });
      article.append(renderFallback(node, path, true));
  }
}

async function displayNode(node, path, scrollY = 0) {
  const cleanPath = safePath(path, node);
  const displayTitle = node.type === "text"
    ? textDisplayTitle(node)
    : node.display_title || node.title || node.id;
  viewState.currentNode = node;
  viewState.currentPath = cleanPath;
  elements.content.classList.remove("is-wide");
  setShellActive(node.id === "home" ? "home" : "node");
  renderBreadcrumbs(cleanPath, displayTitle);
  const article = createElement("article", "node-article");
  await renderDirectNode(article, node, cleanPath);
  const editor = makeNodeEditor(node);
  const header = article.querySelector(".node-header");
  if (editor && header) header.after(editor);
  elements.content.replaceChildren(article);
  document.title = `${displayTitle} · MOSS`;
  requestAnimationFrame(() => window.scrollTo(0, Number(scrollY) || 0));
}

async function navigateNode(nodeId, pathHint, options = {}) {
  showLoading();
  try {
    const node = await apiJson(`/api/node/${encodeURIComponent(nodeId)}`);
    const path = safePath(pathHint || node.path, node);
    const nextState = {
      view: "node", nodeId: node.id, path, scrollY: Number(options.scrollY) || 0,
    };
    setHistory(nextState, nodeUrl(node.id), Boolean(options.replace));
    await displayNode(node, path, nextState.scrollY);
  } catch (error) {
    renderBreadcrumbs([
      { id: "home", type: "page", title: "Home" },
      { id: nodeId, type: "node", title: nodeId },
    ]);
    showError(error);
  }
}

function stateFromLocation() {
  if (window.location.pathname === "/tree") return { view: "tree", scrollY: 0 };
  if (window.location.pathname === "/action-log") return { view: "action-log", scrollY: 0 };
  if (window.location.pathname === "/change-log") return { view: "change-log", scrollY: 0 };
  if (window.location.pathname === "/action-types") return { view: "action-types", scrollY: 0 };
  if (window.location.pathname === "/node-types") return { view: "node-types", scrollY: 0 };
  if (window.location.pathname === "/snapshots") return { view: "snapshots", scrollY: 0 };
  if (window.location.pathname === "/search") {
    return {
      view: "search",
      query: new URLSearchParams(window.location.search).get("q") || "",
      scrollY: 0,
    };
  }
  const match = window.location.pathname.match(/^\/node\/([^/]+)$/);
  if (match) return { view: "node", nodeId: decodeURIComponent(match[1]), path: null, scrollY: 0 };
  return { view: "node", nodeId: "home", path: null, scrollY: 0 };
}

function bindShellEvents(bindSystemLink) {
  for (const homeLink of [elements.brandHome, elements.navHome]) {
    bindNodeLink(homeLink, "home", null);
  }
  bindSystemLink(elements.navTree, "tree");
  bindSystemLink(elements.navActionLog, "action-log");
  bindSystemLink(elements.navChangeLog, "change-log");
  elements.navActionTypes.addEventListener("click", (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey
    ) return;
    event.preventDefault();
    navigateActionTypes();
  });
  elements.navNodeTypes.addEventListener("click", (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey
    ) return;
    event.preventDefault();
    navigateNodeTypes();
  });
  elements.navSearch.addEventListener("click", (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey
    ) return;
    event.preventDefault();
    navigateSearch();
  });
  elements.navSnapshots.addEventListener("click", (event) => {
    if (
      event.defaultPrevented || event.button !== 0 || event.metaKey ||
      event.ctrlKey || event.shiftKey || event.altKey
    ) return;
    event.preventDefault();
    navigateSnapshots();
  });
  window.addEventListener("popstate", async (event) => {
    const state = event.state || stateFromLocation();
    if (state.view === "search") {
      if (state.query) {
        await performSearch(state.query, { replace: true, scrollY: state.scrollY });
      } else {
        navigateSearch({ replace: true, scrollY: state.scrollY });
      }
      return;
    }
    if (["tree", "action-log", "change-log"].includes(state.view)) {
      await navigateSystemView(state.view, { replace: true, scrollY: state.scrollY }); return;
    }
    if (state.view === "node-types") {
      navigateNodeTypes({ replace: true, scrollY: state.scrollY }); return;
    }
    if (state.view === "action-types") {
      await navigateActionTypes({ replace: true, scrollY: state.scrollY }); return;
    }
    if (state.view === "snapshots") {
      await navigateSnapshots({ replace: true, scrollY: state.scrollY }); return;
    }
    await navigateNode(state.nodeId || "home", state.path, {
      replace: true, scrollY: state.scrollY,
    });
  });
}

function initializeModules(nodeSchemas) {
  ({ makeNodeEditor } = createEditors({
    deleteCurrentNode, nodeSchemas, refreshCurrentNode, showActionNotice,
  }));
  ({ makeTodoComposer, renderTodoItem, renderTodoList } = createTodoRenderers({
    bindNodeLink, crumbFor, makeHeadingLink, nodeSchemas, refreshCurrentNode, showActionNotice,
  }));
  ({ makeEventCard, renderCalendar, renderEventDetail, renderWeek } = createCalendarRenderers({
    bindNodeLink, crumbFor, displayNode, makeHeadingLink, nodeSchemas, showActionNotice,
  }));
  ({ renderImage } = createMaterialRenderers({ makeHeadingLink }));
  ({ renderItem, renderItemList } = createItemRenderers({
    bindNodeLink, makeHeadingLink, refreshCurrentNode,
  }));
  ({ renderLog, renderLogEntry } = createLogRenderers({
    bindNodeLink, crumbFor, makeHeadingLink, refreshCurrentNode,
  }));
  ({
    renderFallback, renderInternalLink, renderLink, renderNote, renderRandomizer,
  } = createContentRenderers({
    bindNodeLink, makeHeadingLink, nodeSchemas, refreshCurrentNode,
  }));
  const systemViews = createSystemViews({
    bindNodeLink, crumbFor, elements, renderBreadcrumbs, safePath,
    setHistory, setShellActive, showError, showLoading, viewState,
  });
  ({ navigateActionTypes, navigateNodeTypes } = createSchemaView({
    elements, nodeSchemas, renderBreadcrumbs, setHistory, setShellActive,
    showError, showLoading, viewState,
  }));
  ({ navigateSnapshots } = createSnapshotView({
    elements, renderBreadcrumbs, setHistory, setShellActive,
    showError, showLoading, viewState,
  }));
  ({ navigateSearch, navigateSystemView, performSearch } = systemViews);
  bindShellEvents(systemViews.bindSystemLink);
}

async function start() {
  try {
    initializeModules(await loadSchema());
  } catch (error) {
    renderBreadcrumbs([{ id: "home", type: "page", title: "Home" }]);
    showError(error, "Restart MOSS web");
    return;
  }
  const route = stateFromLocation();
  const stored = history.state;
  if (route.view === "node-types") {
    navigateNodeTypes({
      replace: true,
      scrollY: stored?.view === "node-types" ? stored.scrollY : 0,
    });
    return;
  }
  if (route.view === "action-types") {
    await navigateActionTypes({
      replace: true,
      scrollY: stored?.view === "action-types" ? stored.scrollY : 0,
    });
    return;
  }
  if (route.view === "snapshots") {
    await navigateSnapshots({
      replace: true,
      scrollY: stored?.view === "snapshots" ? stored.scrollY : 0,
    });
    return;
  }
  if (["tree", "action-log", "change-log"].includes(route.view)) {
    await navigateSystemView(route.view, {
      replace: true, scrollY: stored?.view === route.view ? stored.scrollY : 0,
    });
    return;
  }
  if (route.view === "search") {
    if (!route.query) {
      navigateSearch({
        replace: true,
        scrollY: stored?.view === "search" ? stored.scrollY : 0,
      });
      return;
    }
    await performSearch(route.query, {
      replace: true, scrollY: stored?.view === "search" ? stored.scrollY : 0,
    });
    return;
  }
  await navigateNode(
    route.nodeId,
    stored?.view === "node" && stored.nodeId === route.nodeId ? stored.path : null,
    {
      replace: true,
      scrollY: stored?.view === "node" && stored.nodeId === route.nodeId ? stored.scrollY : 0,
    },
  );
}

start();
