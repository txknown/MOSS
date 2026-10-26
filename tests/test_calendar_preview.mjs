import assert from 'node:assert/strict';
import { createCalendarRenderers } from '../web/static/renderers/calendar.js';
class Element {
  constructor(tag) { this.tag=tag; this.children=[]; this.textContent=''; }
  append(...children) { this.children.push(...children); }
}
globalThis.document={createElement:tag=>new Element(tag)};
const bindNodeLink=(link,id)=>{link.href=`/node/${id}`;return link;};
const {renderCalendar}=createCalendarRenderers({bindNodeLink,crumbFor:n=>({id:n.id}),makeHeadingLink:n=>bindNodeLink(new Element('a'),n.id),nodeSchemas:{}});
const descendants=n=>[n,...n.children.flatMap(descendants)];
const weeks=Array.from({length:6},(_,i)=>({id:`week_${i}`,type:'week',start_date:`2026-11-${String(2+i*7).padStart(2,'0')}`,child_nodes:[]}));
// Deliberately shuffled input; the preview must retain chronological order.
weeks[4].start_date='2026-11-30';weeks[5].start_date='2026-12-07';
const past={id:'past',type:'week',start_date:'2026-10-26',completed:true};
const calendar={id:'calendar',title:'Calendar',child_nodes:[weeks[4],past,weeks[1],weeks[5],weeks[0],weeks[3],weeks[2]]};
let nodes=descendants(renderCalendar(calendar,[]));
assert.deepEqual(nodes.filter(n=>n.className==='week-summary-card').map(n=>n.href),weeks.slice(0,4).map(n=>`/node/${n.id}`));
assert.equal(nodes.some(n=>n.tag==='details'),false);
assert.ok(nodes.some(n=>n.textContent==='Open calendar to view all weeks'&&n.href==='/node/calendar'));
nodes=descendants(renderCalendar(calendar,[],true));
assert.equal(nodes.filter(n=>n.className==='week-summary-card').length,7);
assert.equal(nodes.filter(n=>n.tag==='details').length,1);
nodes=descendants(renderCalendar({...calendar,child_nodes:[past]},[]));
assert.equal(nodes.filter(n=>n.className==='week-summary-card').length,0);
assert.ok(nodes.some(n=>n.href==='/node/calendar'));
nodes=descendants(renderCalendar({...calendar,child_nodes:weeks.slice(0,2)},[]));
assert.equal(nodes.filter(n=>n.className==='week-summary-card').length,2);
assert.equal(nodes.some(n=>n.textContent==='Open calendar to view all weeks'),false);
