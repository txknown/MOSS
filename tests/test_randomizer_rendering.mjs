import assert from "node:assert/strict";
import { createContentRenderers } from "../web/static/renderers/content.js";

// Minimal DOM surface used by the renderer; no browser dependency required.
class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.classList = { add() {} };
    this.style = {};
  }
  append(...children) { this.children.push(...children); }
  get childElementCount() { return this.children.length; }
}
globalThis.document = { createElement: (tag) => new Element(tag) };
const { renderRandomizer } = createContentRenderers({
  makeHeadingLink(node) {
    const link = new Element("a");
    link.textContent = node.title;
    return link;
  },
});
function text(node) {
  return [node.textContent, ...node.children.map(text)].join(" ");
}
for (const display_mode of ["list", "text"]) {
  for (const title_visible of [undefined, false, true]) {
    const node = {
      type: "randomizer", title: "Example title", random_selection: ["Example phrase."],
      attributes: { display_mode, title_visible },
    };
    const embedded = renderRandomizer(node, []);
    assert.equal(embedded.children.some((child) => child.tag === "h2"), title_visible === true);
    assert.ok(text(embedded).includes("Example phrase."));
    // The direct view supplies its own node header, never a duplicate heading.
    const direct = renderRandomizer(node, [], true);
    assert.equal(direct.children.some((child) => child.tag === "h2"), false);
    assert.ok(text(direct).includes("Example phrase."));
  }
}
