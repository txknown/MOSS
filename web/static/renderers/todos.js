"use strict";

import { apiJson, runMossAction } from "../api.js?v=24";
import { createElement } from "../dom.js?v=24";


export function createTodoRenderers({
  bindNodeLink,
  crumbFor,
  makeHeadingLink,
  nodeSchemas,
  refreshCurrentNode,
  showActionNotice,
}) {
  function renderTodoItem(item, path) {
    const row = createElement("li", `todo-row${item.checked ? " is-checked" : ""}`);
    const main = createElement("div", "todo-row-main");
    const mark = createElement("button", "todo-mark todo-toggle", item.checked ? "[x]" : "[ ]");
    mark.type = "button";
    mark.setAttribute("aria-pressed", String(Boolean(item.checked)));
    mark.setAttribute("aria-label", `${item.checked ? "Reopen" : "Complete"} ${item.content || item.id}`);
    mark.addEventListener("click", async () => {
      mark.disabled = true;
      try {
        await runMossAction("update_node", {
          node_id: item.id,
          attributes: { checked: !item.checked },
        });
        await refreshCurrentNode(item.checked ? "Todo reopened." : "Todo completed.");
      } catch (error) {
        mark.disabled = false;
        showActionNotice(error instanceof Error ? error.message : String(error), true);
      }
    });

    const content = createElement("div", "todo-content");
    const link = createElement(
      "a",
      "todo-link",
      item.content || item.display_title || item.id,
    );
    bindNodeLink(link, item.id, path);
    link.setAttribute(
      "aria-label",
      `${item.checked ? "Completed" : "Open"}: ${item.content || item.display_title || item.id}`,
    );
    content.append(link);
    content.append(createElement("span", "todo-node-id", `ID · ${item.id}`));
    if (item.checked && item.date_completed) {
      content.append(
        createElement("span", "completion-date", `Completed ${item.date_completed}`),
      );
    }
    main.append(mark, content);
    row.append(main);

    const children = Array.isArray(item.child_nodes) ? item.child_nodes : [];
    if (children.length) {
      const childList = createElement("ul", "todo-list todo-children");
      for (const child of children) {
        if (child.missing) {
          childList.append(
            createElement("li", "missing-node", `Missing child todo: ${child.id}`),
          );
        } else if (child.type === "todo_item") {
          childList.append(renderTodoItem(child, [...path, crumbFor(child)]));
        }
      }
      row.append(childList);
    }
    return row;
  }

  function makeTodoComposer(parentNode, options = {}) {
    const form = createElement("form", "todo-composer");
    const input = createElement("input");
    input.type = "text";
    input.name = "content";
    input.required = true;
    if (nodeSchemas.todo_item?.content?.max_length) {
      input.maxLength = nodeSchemas.todo_item.content.max_length;
    }
    input.autocomplete = "off";
    input.placeholder = options.placeholder || "Add a todo…";
    input.setAttribute("aria-label", options.label || "New todo");
    const submit = createElement(
      "button",
      "primary-button compact-button",
      options.buttonLabel || "Add todo",
    );
    submit.type = "submit";
    const feedback = createElement("p", "edit-feedback todo-composer-feedback");
    feedback.setAttribute("role", "status");
    form.append(input, submit, feedback);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const content = input.value.trim();
      if (!content) return;
      feedback.textContent = "";
      submit.disabled = true;
      try {
        await runMossAction("create_child", {
          parent_id: parentNode.id,
          type: "todo_item",
          id: null,
          content,
          attributes: {},
        });
        await refreshCurrentNode(options.successMessage || "Todo added.");
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
      }
    });
    return form;
  }

  function makeNodeLinkText(node, path) {
    const link = createElement(
      "a",
      "todo-link",
      node.display_title || node.title || node.id,
    );
    return bindNodeLink(link, node.id, path);
  }

  async function renderTodoList(node, path, direct = false) {
    const panel = createElement("section", "todo-panel");
    if (!direct && node.title) {
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      panel.append(heading);
    }
    if (direct) {
      panel.append(makeTodoComposer(node));
    }

    let items = Array.isArray(node.child_nodes) ? node.child_nodes : null;
    if (items === null) {
      try {
        const fullNode = await apiJson(`/api/node/${encodeURIComponent(node.id)}`);
        items = fullNode.child_nodes || [];
      } catch (error) {
        panel.append(createElement("p", "empty-message", error.message));
        return panel;
      }
    }

    const openItems = items.filter((item) => !item.checked);
    const completedItems = items.filter((item) => item.checked);
    const list = createElement("ul", "todo-list");
    const visibleItems = direct ? openItems : openItems.slice(0, 2);
    for (const item of visibleItems) {
      if (item.missing) {
        list.append(
          createElement("li", "missing-node", `Missing todo item: ${item.id}`),
        );
        continue;
      }
      if (item.type === "todo_item") {
        list.append(renderTodoItem(item, [...path, crumbFor(item)]));
      } else {
        const row = createElement("li", "todo-row");
        const main = createElement("div", "todo-row-main");
        main.append(
          createElement("span", "todo-mark", "—"),
          makeNodeLinkText(item, [...path, crumbFor(item)]),
        );
        row.append(main);
        list.append(row);
      }
    }
    if (!list.childElementCount) {
      list.append(createElement("li", "empty-message", "No open todo items."));
    }
    panel.append(list);
    if (direct && completedItems.length) {
      const completed = createElement("details", "completed-todos");
      completed.append(
        createElement(
          "summary",
          "completed-todos-summary",
          `Show completed (${completedItems.length})`,
        ),
      );
      const completedList = createElement("ul", "todo-list completed-todo-list");
      for (const item of completedItems) {
        if (item.missing) {
          completedList.append(
            createElement("li", "missing-node", `Missing todo item: ${item.id}`),
          );
        } else if (item.type === "todo_item") {
          completedList.append(renderTodoItem(item, [...path, crumbFor(item)]));
        }
      }
      completed.append(completedList);
      panel.append(completed);
    }
    if (!direct) {
      const remaining = openItems.length - visibleItems.length;
      const linkLabel = remaining > 0
        ? `View ${remaining} more open ${remaining === 1 ? "item" : "items"}`
        : completedItems.length
          ? `View completed items (${completedItems.length})`
          : "Open todo list";
      const more = createElement("a", "todo-preview-more", linkLabel);
      bindNodeLink(more, node.id, path);
      panel.append(more);
    }
    return panel;
  }

  return { makeTodoComposer, renderTodoItem, renderTodoList };
}
