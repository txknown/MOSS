import assert from "node:assert/strict";
import { createTodoRenderers } from "../web/static/renderers/todos.js";
import { createCalendarRenderers } from "../web/static/renderers/calendar.js";

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.value = "";
    this.attributes = {};
    this.listeners = {};
    this.style = { setProperty() {} };
    this.classList = { add() {} };
  }
  append(...children) { this.children.push(...children); }
  get childElementCount() { return this.children.length; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(name, listener) { this.listeners[name] = listener; }
  focus() {}
}
globalThis.document = { createElement: tag => new Element(tag) };
globalThis.window = { scrollY: 0 };
globalThis.requestAnimationFrame = () => {};
const descendants = node => [node, ...node.children.flatMap(descendants)];
const find = (node, predicate) => descendants(node).find(predicate);
const named = (node, name) => find(node, n => n.name === name);
const submit = node => node.listeners.submit({ preventDefault() {} });
const bindNodeLink = (link, id) => { link.href = `/node/${id}`; return link; };
const shared = {
  bindNodeLink,
  crumbFor: node => ({ id: node.id }),
  makeHeadingLink: node => bindNodeLink(new Element("a"), node.id),
  nodeSchemas: { week: { attributes: [] }, todo_item: { content: { max_length: 250000 } } },
  showActionNotice() {},
};
let requests = [];
let failure = false;
globalThis.fetch = async (url, request) => {
  requests.push({ url, ...request, body: JSON.parse(request.body) });
  return {
    ok: !failure,
    status: failure ? 422 : 200,
    json: async () => failure ? { detail: "Please try again." } : { week: {}, event: { id: "created" } },
  };
};

let refreshed = 0;
const { renderTodoList } = createTodoRenderers({ ...shared, refreshCurrentNode: async () => { refreshed++; } });
const todos = {
  id: "tasks", title: "Tasks", child_nodes: [
    { id: "done", type: "todo_item", checked: true, content: "Completed" },
    ...Array.from({ length: 6 }, (_, i) => ({ id: `task_${i}`, type: "todo_item", content: `Task ${i}` })),
  ],
};
const preview = await renderTodoList(todos, []);
assert.equal(descendants(preview).filter(n => n.className === "todo-row").length, 4);
assert.ok(find(preview, n => n.textContent === "View 2 more open items"));
assert.equal(descendants(preview).filter(n => n.className === "todo-composer").length, 1);
const form = find(preview, n => n.tag === "form");
const input = named(form, "content");
input.value = "  New task <literal>  ";
await submit(form);
assert.deepEqual(requests.at(-1).body, {
  action: "create_child",
  payload: { parent_id: "tasks", type: "todo_item", id: null, content: "New task <literal>", attributes: {} },
});
assert.equal(refreshed, 1);
failure = true;
await submit(form);
assert.equal(input.value, "  New task <literal>  ");
assert.equal(find(form, n => n.type === "submit").disabled, false);
assert.ok(find(form, n => n.textContent === "Please try again."));
failure = false;
const full = await renderTodoList(todos, [], true);
assert.equal(descendants(full).filter(n => n.className === "todo-row").length, 6);
assert.ok(find(full, n => n.textContent === "Show completed (1)"));
const empty = await renderTodoList({ ...todos, child_nodes: [] }, []);
assert.ok(find(empty, n => n.className === "todo-composer"));
assert.ok(find(empty, n => n.textContent === "No open todo items."));

const { renderWeek } = createCalendarRenderers({ ...shared, displayNode: async () => {} });
const week = { id: "week", start_date: "2026-10-12", child_nodes: [], attributes: {} };
const panel = renderWeek(week, [], true);
assert.equal(descendants(panel).filter(n => n.textContent === "Add item").length, 1);
assert.equal(descendants(panel).filter(n => n.textContent === "Add day item").length, 0);
const toggle = find(panel, n => n.textContent === "Add item");
const eventForm = find(panel, n => n.className === "event-form");
const kind = named(eventForm, "kind");
toggle.listeners.click();
assert.equal(kind.value, "timed");
assert.equal(eventForm.hidden, false);
const timeRow = find(eventForm, n => n.className === "event-time-row event-field-wide");
assert.deepEqual(timeRow.children.map(n => n.children[1].name), ["start_time", "end_time"]);
assert.equal(timeRow.hidden, false);
named(eventForm, "title").value = "Timed item";
await submit(eventForm);
assert.equal(requests.at(-1).body.start_time, "09:00");
assert.equal(requests.at(-1).body.end_time, "10:00");
kind.value = "untimed";
kind.listeners.change();
assert.equal(timeRow.hidden, true);
assert.equal(named(eventForm, "start_time").disabled, true);
assert.equal(named(eventForm, "end_time").required, false);
await submit(eventForm);
assert.equal(requests.at(-1).body.start_time, "");
assert.equal(requests.at(-1).body.end_time, "");
find(eventForm, n => n.textContent === "Cancel").listeners.click();
toggle.listeners.click();
assert.equal(kind.value, "timed");
assert.equal(named(eventForm, "start_time").disabled, false);
const previous = requests.length;
named(eventForm, "end_time").value = "08:00";
await submit(eventForm);
assert.equal(requests.length, previous);
assert.ok(find(eventForm, n => n.textContent === "End time must be later than start time."));
const embeddedWeek = renderWeek(week, [], false);
assert.equal(descendants(embeddedWeek).filter(n => n.className === "event-composer").length, 0);
