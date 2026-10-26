"use strict";
import { apiJson, runMossAction } from "./api.js?v=35";
import { createElement, humanLabel } from "./dom.js?v=35";

export function createUIViews({ elements, setHistory, setShellActive, renderBreadcrumbs, viewState }) {
  let settings, schemes, navigationCatalog, displayCatalog, nodeStyles;
  function apply() {
    const scheme = schemes.find(item => item.id === settings.scheme);
    for (const [key, value] of Object.entries(scheme.colors)) document.documentElement.style.setProperty(`--${key}`, value);
    document.documentElement.dataset.colorMode = scheme.mode;
    document.documentElement.style.colorScheme = scheme.mode;
    const nav = document.querySelector(".system-nav");
    nav.replaceChildren();
    for (const item of [...settings.navigation, {label: "MOSS UI", target: "system:ui"}]) {
      const link = createElement("a", null, item.label);
      if (item.target === "home" || item.target.startsWith("node:")) {
        const nodeId = item.target === "home" ? settings.home_node_id : item.target.slice(5);
        link.href = `/node/${encodeURIComponent(nodeId)}`;
        link.dataset.nodeId = nodeId;
      } else {
        const destination = navigationCatalog.find(entry => entry.target === item.target);
        if (!destination) continue;
        link.href = destination.url;
        link.dataset.view = item.target.slice(7);
      }
      nav.append(link);
    }
    setShellActive(viewState.activeView || "node");
  }
  async function load() {
    const response = await apiJson("/api/ui-settings");
    settings = response.settings; schemes = response.schemes;
    navigationCatalog = response.navigation_catalog;
    displayCatalog = response.display_styles; nodeStyles = response.node_styles;
    apply();
  }
  function begin(view, title, url, replace) {
    viewState.currentNode = null; viewState.currentPath = [];
    setShellActive(view);
    elements.content.classList.remove("is-wide");
    renderBreadcrumbs([{ title }]);
    setHistory({ view, scrollY: 0 }, url, replace);
    document.title = `${title} · MOSS`;
    elements.content.replaceChildren();
    window.scrollTo(0, 0);
  }
  function choices(form, legendText, name, items, value) {
    const group = createElement("fieldset", "ui-options");
    group.append(createElement("legend", null, legendText));
    for (const item of items) {
      const label = createElement("label", "ui-choice");
      const input = createElement("input");
      input.type = "radio"; input.name = name; input.value = item.id;
      input.checked = value === item.id;
      label.append(input, createElement("span", null, item.name)); group.append(label);
    }
    form.append(group);
  }
  function field(title, control) {
    const label = createElement("label", "edit-field");
    label.append(createElement("span", "edit-field-label", title), control);
    return label;
  }
  function navigationEditor() {
    const section = createElement("section", "ui-navigation-editor");
    section.append(createElement("h2", "section-heading", "Top-bar links"),
      createElement("p", "muted", "Choose built-in views or link to a node by its ID. These links also appear in the top-down view. MOSS UI stays available at the end."));
    const rows = settings.navigation.map(item => ({...item}));
    const list = createElement("div", "ui-navigation-list");
    function render() {
      list.replaceChildren();
      rows.forEach((item, index) => {
        const row = createElement("div", "ui-navigation-row");
        const label = createElement("input"); label.type = "text"; label.value = item.label;
        label.required = true; label.maxLength = 80;
        label.addEventListener("input", () => { item.label = label.value; });
        const target = createElement("select");
        for (const option of [{target:"node",label:"Node"}, ...navigationCatalog.filter(entry => entry.target !== "system:ui")]) {
          const element = createElement("option", null, option.label); element.value = option.target; target.append(element);
        }
        target.value = item.target.startsWith("node:") ? "node" : item.target;
        const id = createElement("input"); id.type = "text"; id.placeholder = "Node ID";
        id.value = item.target.startsWith("node:") ? item.target.slice(5) : "";
        const idField = field(`Node ID ${index + 1}`, id);
        function updateTarget() {
          idField.hidden = target.value !== "node"; id.required = target.value === "node";
          id.disabled = target.value !== "node";
          item.target = target.value === "node" ? `node:${id.value}` : target.value;
        }
        target.addEventListener("change", updateTarget); id.addEventListener("input", updateTarget); updateTarget();
        row.append(field(`Label ${index + 1}`, label), field(`Destination ${index + 1}`, target), idField);
        const controls = createElement("div", "ui-link-controls");
        for (const [caption, position] of [["Top",0],["↑",index-1],["↓",index+1],["Bottom",rows.length-1]]) {
          const button = createElement("button", "secondary-button compact-button", caption); button.type = "button";
          button.setAttribute("aria-label", `${caption === "↑" ? "Up" : caption === "↓" ? "Down" : caption}: link ${index + 1}`);
          button.disabled = position < 0 || position >= rows.length || position === index;
          button.addEventListener("click", () => { rows.splice(index,1); rows.splice(position,0,item); render(); });
          controls.append(button);
        }
        const remove = createElement("button", "secondary-button compact-button", "Remove link"); remove.type = "button";
        remove.addEventListener("click", () => { rows.splice(index,1); render(); }); controls.append(remove);
        row.append(controls); list.append(row);
      });
    }
    render();
    const add = createElement("button", "secondary-button", "Add link"); add.type = "button";
    add.addEventListener("click", () => { if (rows.length < 30) { rows.push({label:"",target:"node:"}); render(); list.lastElementChild.querySelector("input").focus(); } });
    section.append(list, add);
    return { section, values: () => rows.map(item => ({...item})) };
  }
  function styleOverview() {
    const section = createElement("section", "ui-style-overview");
    section.append(createElement("h2", "section-heading", "Node display styles"),
      createElement("p", "muted", "Choose a style in a node’s Edit panel. Ask your AI2 agent to add a reusable display style. Parent-page and opened-node displays are separate choices."));
    for (const [type, contexts] of Object.entries(displayCatalog)) {
      const details = createElement("details", "ui-style-catalog");
      details.append(createElement("summary", null, `${humanLabel(type)} node display styles`));
      for (const [context, title] of [["parent","On a parent page"],["open","When opened"]]) {
        details.append(createElement("h3", "field-label", title));
        const list = createElement("ul");
        for (const style of contexts[context]) list.append(createElement("li", null, `${style.name} — ${style.description}`));
        details.append(list);
      }
      section.append(details);
    }
    return section;
  }
  function showSettings(replace = false) {
    begin("ui", "MOSS UI", "/ui", replace);
    const article = createElement("article", "ui-settings");
    article.append(createElement("h1", "node-title", "MOSS UI"), createElement("p", "muted", "Choose workspace appearance, navigation, and startup behavior."));
    const form = createElement("form", "ui-settings-form");
    choices(form, "Saved color schemes", "scheme", schemes, settings.scheme);
    choices(form, "Home style", "home_style", [{id:"node",name:"Node"},{id:"top-down",name:"Show top-down"}], settings.home_style);
    const home = createElement("input"); home.type = "text"; home.required = true; home.name = "home_node_id"; home.value = settings.home_node_id;
    form.append(field("Home node ID", home), createElement("p", "muted", "Home opens this node. Click the MOSS title anytime to return to the top-down view."));
    const navigation = navigationEditor(); form.append(navigation.section);
    const save = createElement("button", "primary-button", "Save UI settings"); save.type = "submit";
    const feedback = createElement("p", "edit-feedback"); feedback.setAttribute("role", "status");
    form.append(save, feedback);
    form.addEventListener("submit", async event => {
      event.preventDefault(); save.disabled = true; feedback.textContent = "Saving…";
      const data = new FormData(form);
      try {
        const response = await runMossAction("update_ui_settings", {...Object.fromEntries(data), navigation: navigation.values()});
        settings = response.result.settings; apply(); feedback.textContent = "UI settings saved.";
      } catch (error) { feedback.textContent = error.message; }
      finally { save.disabled = false; }
    });
    article.append(form, styleOverview()); elements.content.append(article);
  }
  function showTopDown(replace = false) {
    begin("top-down", "MOSS", "/top-down", replace);
    const hub = createElement("nav", "moss-orbit"); hub.setAttribute("aria-label", "MOSS top-down navigation");
    hub.append(createElement("h1", "orbit-center", "MOSS"));
    const links = [...document.querySelectorAll(".system-nav a")];
    if (links.length > 12) hub.classList.add("orbit-grid");
    links.forEach((source, index) => {
      const angle = -Math.PI / 2 + index * 2 * Math.PI / links.length;
      const link = createElement("a", "orbit-link", source.textContent); link.href = source.href;
      link.style.left = `${50 + 39 * Math.cos(angle)}%`; link.style.top = `${50 + 39 * Math.sin(angle)}%`;
      hub.append(link);
    });
    elements.content.append(hub);
  }
  return { load, showSettings, showTopDown, getSettings: () => settings,
    getDisplayCatalog: () => displayCatalog, getNodeStyles: () => nodeStyles,
    setNodeStyles: (id, styles) => { nodeStyles[id] = styles; } };
}
