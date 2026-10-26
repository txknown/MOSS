import assert from 'node:assert/strict';
import { currentCalendarWeeks, createCalendarRenderers } from '../web/static/renderers/calendar.js';
import { createDisplayStyles } from '../web/static/display_styles.js';
class Element {
  constructor(tag) { this.tag=tag; this.children=[]; this.textContent=''; this.attributes={}; this.style={setProperty(){}}; this.classList={add(){}}; }
  append(...children) { this.children.push(...children); }
  setAttribute(key,value) { this.attributes[key]=value; }
}
globalThis.document={createElement:tag=>new Element(tag)};
const week = {id:'week',type:'week',start_date:'2026-10-19',completed:true,child_nodes:[]};
const cal = {id:'cal',type:'calendar',title:'Calendar',child_nodes:[week]};
assert.equal(currentCalendarWeeks(cal,new Date(2026,9,18,23,59)).length,0);
assert.equal(currentCalendarWeeks(cal,new Date(2026,9,19,0,0)).length,1);
assert.equal(currentCalendarWeeks(cal,new Date(2026,9,25,23,59)).length,1);
assert.equal(currentCalendarWeeks(cal,new Date(2026,9,26,0,0)).length,0);
assert.equal(currentCalendarWeeks({...cal,child_nodes:[{...week,start_date:'bad'}]},new Date()).length,0);
// Local calendar comparisons also span year changes and daylight-saving weeks.
for (const [start,today] of [['2026-12-28',new Date(2027,0,3,23)],['2026-10-26',new Date(2026,10,1,23)]]) {
  assert.equal(currentCalendarWeeks({...cal,child_nodes:[{...week,start_date:start}]},today).length,1);
}
const bindNodeLink=(link,id)=>{link.href=`/node/${id}`;return link;};
const makeHeadingLink=n=>bindNodeLink(new Element('a'),n.id);
const {renderCurrentWeek}=createCalendarRenderers({bindNodeLink,makeHeadingLink,crumbFor:n=>({id:n.id}),nodeSchemas:{}});
const descendants=n=>[n,...n.children.flatMap(descendants)];
const today=new Date(); const monday=new Date(today); monday.setDate(today.getDate()-((today.getDay()+6)%7));
const key=`${monday.getFullYear()}-${String(monday.getMonth()+1).padStart(2,'0')}-${String(monday.getDate()).padStart(2,'0')}`;
const event={id:'event',type:'event',day:1,start_time:'09:00',end_time:'10:00',title:'Test event'};
const dayItem={id:'day_item',type:'event',day:2,start_time:'',end_time:'',title:'Untimed'};
let panel=await renderCurrentWeek({...cal,child_nodes:[{...week,start_date:key,child_nodes:[event,dayItem]}]},[]);
let nodes=descendants(panel);
assert.ok(nodes.some(n=>n.href==='/node/event'));
assert.ok(nodes.some(n=>n.href==='/node/day_item'));
assert.ok(nodes.some(n=>n.href==='/node/cal'));
assert.ok(nodes.some(n=>n.href==='/node/week'));
assert.equal(nodes.some(n=>n.tag==='form'),false);
panel=await renderCurrentWeek({...cal,child_nodes:[]},[]);
assert.ok(descendants(panel).some(n=>n.textContent==='No week containing today in this calendar.'));
let selected={parent:'current-week',open:'default'}, called=0;
const styles=createDisplayStyles({uiViews:{getNodeStyles:()=>({cal:selected}),getDisplayCatalog:()=>({calendar:{parent:[{id:'default'},{id:'current-week'}],open:[{id:'default'}]}})},renderers:{'calendar:parent:current-week':()=>{called++;return panel;}}});
assert.equal(styles.render(cal,[],'parent'),panel);
assert.equal(styles.render(cal,[],'open'),null);
selected={parent:'removed',open:'default'};
assert.equal(styles.render(cal,[],'parent'),null);
assert.equal(called,1);
