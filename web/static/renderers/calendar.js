"use strict";
import { parseDateOnly, localDateKey, formatWeekRange, formatWeekCardRange } from "../dates.js?v=35";
export { parseDateOnly, formatWeekRange } from "../dates.js?v=35";
import { layoutDay, timelinePercent } from "./calendar_layout.js?v=35";

import { apiJson, runMossAction } from "../api.js?v=35";
import {
  appendText,
  createElement,
  makeLabeledSection,
  shortExcerpt,
} from "../dom.js?v=35";

const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function parseClockMinutes(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

function formatClockValue(value) {
  const minutes = parseClockMinutes(value);
  if (minutes === null) return null;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(
    minutes % 60,
  ).padStart(2, "0")}`;
}

function formatEventTime(node, includeDay = false) {
  const start = formatClockValue(node.start_time);
  const end = formatClockValue(node.end_time);
  let timeLabel = "No time";
  if (start && end) {
    timeLabel = `${start} – ${end}`;
  } else if (start) {
    timeLabel = `Starts ${start}`;
  } else if (end) {
    timeLabel = `Ends ${end}`;
  }
  if (!includeDay) return timeLabel;
  const dayNumber = Number(node.day);
  const dayLabel = DAY_NAMES[dayNumber - 1] || "Day not set";
  return `${dayLabel} · ${timeLabel}`;
}

export function currentCalendarWeeks(node, today = new Date()) {
  const date = localDateKey(today);
  return (node.child_nodes || []).filter(week => {
    if (week.missing || week.type !== "week") return false;
    const start = parseDateOnly(week.start_date);
    if (!start) return false;
    const end = new Date(start); end.setDate(end.getDate() + 7);
    return date >= localDateKey(start) && date < localDateKey(end);
  });
}

export function createCalendarRenderers({
  bindNodeLink,
  crumbFor,
  displayNode,
  makeHeadingLink,
  nodeSchemas,
  showActionNotice,
}) {
  const eventAttributes = Object.fromEntries(
    (nodeSchemas.event?.attributes || []).map((item) => [item.name, item]),
  );
  function makeEventCard(eventNode, path) {
    const link = createElement("a", "calendar-event");
    bindNodeLink(link, eventNode.id, path);
    const startMinutes = parseClockMinutes(eventNode.start_time);
    const endMinutes = parseClockMinutes(eventNode.end_time);
    if (startMinutes !== null && endMinutes !== null && endMinutes > startMinutes) {
      const durationHeight = Math.max(4.5, Math.min(12, (endMinutes - startMinutes) * 0.047));
      link.style.setProperty("--event-block-height", `${durationHeight}rem`);
    }
    link.append(
      createElement("span", "event-time", formatEventTime(eventNode)),
      createElement(
        "span",
        "event-title",
        eventNode.display_title || eventNode.title || eventNode.id,
      ),
    );
    if (eventNode.description) {
      link.append(
        createElement(
          "span",
          "event-notes-preview",
          shortExcerpt(eventNode.description, 90),
        ),
      );
    }
    return link;
  }

  function makeEventComposer(weekNode, path, startDate) {
    const composer = createElement("section", "event-composer");
    const toolbar = createElement("div", "event-composer-toolbar");
    const headingGroup = createElement("div");
    headingGroup.append(
      createElement("p", "event-composer-kicker", "Week actions"),
      createElement("h2", "event-composer-title", "Add to this week"),
    );
    const toggle = createElement("button", "primary-button", "Add item");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    toolbar.append(headingGroup, toggle);

    const form = createElement("form", "event-form");
    form.hidden = true;
    const grid = createElement("div", "event-form-grid");

    const titleLabel = createElement("label", "event-field event-field-wide");
    titleLabel.append(createElement("span", "event-field-label", "Title"));
    const titleInput = createElement("input");
    titleInput.name = "title";
    titleInput.type = "text";
    titleInput.required = true;
    if (eventAttributes.title?.editor?.max_length) {
      titleInput.maxLength = eventAttributes.title.editor.max_length;
    }
    titleInput.autocomplete = "off";
    titleLabel.append(titleInput);

    const dayLabel = createElement("label", "event-field");
    dayLabel.append(createElement("span", "event-field-label", "Day"));
    const daySelect = createElement("select");
    daySelect.name = "day";
    const todayKey = localDateKey(new Date());
    let defaultDay = 1;
    for (let offset = 0; offset < 7; offset += 1) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + offset);
      const option = createElement(
        "option",
        null,
        `${DAY_NAMES[offset]} · ${localDateKey(date)}`,
      );
      option.value = String(offset + 1);
      if (localDateKey(date) === todayKey) defaultDay = offset + 1;
      daySelect.append(option);
    }
    daySelect.value = String(defaultDay);
    dayLabel.append(daySelect);

    const startLabel = createElement("label", "event-field");
    startLabel.append(createElement("span", "event-field-label", "Starts"));
    const startInput = createElement("input");
    startInput.name = "start_time";
    startInput.type = "text";
    startInput.inputMode = "numeric";
    startInput.pattern = eventAttributes.start_time?.editor?.pattern || "";
    startInput.placeholder = "09:00";
    startInput.title = eventAttributes.start_time?.editor?.title || "";
    startInput.required = true;
    startInput.value = "09:00";
    startLabel.append(startInput);

    const endLabel = createElement("label", "event-field");
    endLabel.append(createElement("span", "event-field-label", "Ends"));
    const endInput = createElement("input");
    endInput.name = "end_time";
    endInput.type = "text";
    endInput.inputMode = "numeric";
    endInput.pattern = eventAttributes.end_time?.editor?.pattern || "";
    endInput.placeholder = "10:00";
    endInput.title = eventAttributes.end_time?.editor?.title || "";
    endInput.required = true;
    endInput.value = "10:00";
    endLabel.append(endInput);
    const timeRow = createElement("div", "event-time-row event-field-wide");
    timeRow.append(startLabel, endLabel);

    const notesLabel = createElement("label", "event-field event-field-wide");
    notesLabel.append(createElement("span", "event-field-label", "Notes (optional)"));
    const notesInput = createElement("textarea");
    notesInput.name = "description";
    notesInput.rows = 4;
    if (eventAttributes.description?.editor?.max_length) {
      notesInput.maxLength = eventAttributes.description.editor.max_length;
    }
    notesLabel.append(notesInput);

    const kindLabel = createElement("label", "event-field");
    kindLabel.append(createElement("span", "event-field-label", "Kind"));
    const kindSelect = createElement("select");
    kindSelect.name = "kind";
    for (const [value, label] of [["timed", "Timed event"], ["untimed", "Day item (no time)"]]) {
      const option = createElement("option", null, label);
      option.value = value;
      kindSelect.append(option);
    }
    kindLabel.append(kindSelect);
    const updateKind = () => {
      const untimed = kindSelect.value === "untimed";
      timeRow.hidden = untimed;
      startInput.disabled = endInput.disabled = untimed;
      startInput.required = endInput.required = !untimed;
    };
    kindSelect.addEventListener("change", updateKind);
    grid.append(titleLabel, dayLabel, kindLabel, timeRow, notesLabel);
    const feedback = createElement("p", "event-form-feedback");
    feedback.setAttribute("role", "alert");
    const actions = createElement("div", "event-form-actions");
    const submit = createElement("button", "primary-button", "Create item");
    submit.type = "submit";
    const cancel = createElement("button", "secondary-button", "Cancel");
    cancel.type = "button";
    actions.append(submit, cancel);
    form.append(grid, feedback, actions);
    composer.append(toolbar, form);

    const closeForm = () => {
      form.hidden = true;
      toggle.hidden = false;
      toggle.setAttribute("aria-expanded", "false");
      feedback.textContent = "";
    };
    const openForm = () => {
      kindSelect.value = "timed";
      updateKind();
      form.hidden = false;
      toggle.hidden = true;
      toggle.setAttribute("aria-expanded", "true");
      titleInput.focus();
    };
    toggle.addEventListener("click", () => openForm());
    cancel.addEventListener("click", closeForm);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      const startMinutes = parseClockMinutes(startInput.value);
      const endMinutes = parseClockMinutes(endInput.value);
      if (kindSelect.value === "timed" && (startMinutes === null || endMinutes === null || endMinutes <= startMinutes)) {
        feedback.textContent = "End time must be later than start time.";
        return;
      }
      submit.disabled = true;
      cancel.disabled = true;
      submit.textContent = "Creating…";
      try {
        const response = await apiJson("/api/events", {
          method: "POST",
          body: {
            week_id: weekNode.id,
            title: titleInput.value,
            description: notesInput.value,
            day: Number(daySelect.value),
            start_time: kindSelect.value === "untimed" ? "" : startInput.value,
            end_time: kindSelect.value === "untimed" ? "" : endInput.value,
          },
        });
        await displayNode(response.week, path, window.scrollY);
        showActionNotice(`Created ${response.event.display_title || response.event.id}.`);
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
        cancel.disabled = false;
        submit.textContent = "Create item";
      }
    });
    return composer;
  }

  function makeWeekNotes(node, direct) {
    const section = createElement("section", "week-notes");
    section.append(createElement("h2", "section-heading", "Notes & goals"));
    const notes = node.attributes?.notes || "";
    if (!direct) {
      if (notes) appendText(section, notes);
      else section.append(createElement("p", "empty-message", "No notes or goals yet."));
      return section;
    }
    const form = createElement("form", "week-notes-form");
    const input = createElement("textarea");
    input.rows = 5;
    input.value = notes;
    input.setAttribute("aria-label", "Week notes and goals");
    const definition = nodeSchemas.week.attributes.find(item => item.name === "notes");
    if (definition?.editor?.max_length) input.maxLength = definition.editor.max_length;
    const fit = () => {
      if (!input.isConnected) return;
      input.style.height = "auto";
      input.style.height = `${input.scrollHeight + input.offsetHeight - input.clientHeight}px`;
    };
    input.addEventListener("input", fit);
    requestAnimationFrame(fit);
    const save = createElement("button", "primary-button compact-button", "Save notes");
    save.type = "submit";
    const feedback = createElement("p", "edit-feedback");
    feedback.setAttribute("role", "status");
    form.append(input, save, feedback);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      save.disabled = true; input.readOnly = true; feedback.textContent = "";
      try {
        await runMossAction("update_node", { node_id: node.id, attributes: { notes: input.value } });
        feedback.textContent = "Notes saved.";
      } catch (error) { feedback.textContent = error.message; }
      finally { save.disabled = false; input.readOnly = false; }
    });
    section.append(form);
    return section;
  }

  function renderWeek(node, path, direct = false) {
    const panel = createElement("section", "week-panel");
    const startDate = parseDateOnly(node.start_date);
    const rangeLabel = node.title || formatWeekRange(startDate);
    if (!direct) {
      const header = createElement("header", "week-header");
      const heading = createElement("h2", "week-title");
      heading.append(makeHeadingLink({ ...node, display_title: rangeLabel }, path));
      header.append(heading, createElement("span", "week-date-range", formatWeekCardRange(startDate)));
      panel.append(header);
    }

    if (!startDate) {
      panel.append(
        createElement("p", "empty-message", "This week does not have a valid Monday start date."),
      );
      return panel;
    }

    const events = (Array.isArray(node.child_nodes) ? node.child_nodes : [])
      .filter((child) => !child.missing && child.type === "event")
      .sort((left, right) => {
        const byDay = Number(left.day || 1) - Number(right.day || 1);
        if (byDay) return byDay;
        const byTime = String(left.start_time || "").localeCompare(
          String(right.start_time || ""),
        );
        return byTime || String(left.display_title || left.id).localeCompare(
          String(right.display_title || right.id),
        );
      });
    const eventsByDay = new Map();
    for (const eventNode of events) {
      const dayNumber = Number(eventNode.day);
      if (!eventsByDay.has(dayNumber)) eventsByDay.set(dayNumber, []);
      eventsByDay.get(dayNumber).push(eventNode);
    }

    const composer = direct ? makeEventComposer(node, path, startDate) : null;
    if (composer) panel.append(composer);

    const scroll = createElement("div", "week-grid-scroll");
    scroll.classList.add("week-time-scroll");
    scroll.setAttribute("aria-label", "Weekly schedule, 00:00 to 24:00. Overnight hours before 06:00 are half-height.");
    const grid = createElement("div", "week-grid week-time-grid");
    const todayKey = localDateKey(new Date());
    const days = [];
    grid.append(createElement("div", "timeline-corner", "Time"));
    for (let offset = 0; offset < 7; offset += 1) {
      const day = new Date(startDate);
      day.setDate(startDate.getDate() + offset);
      const dayKey = localDateKey(day);
      const label = `${DAY_NAMES[offset]} · ${dayKey}`;
      const dayHeader = createElement("header", `day-header timeline-header${dayKey === todayKey ? " is-today" : ""}`);
      const heading = createElement("div", "day-heading");
      heading.append(
        createElement(
          "span",
          "day-name",
          DAY_NAMES[offset].slice(0, 3),
        ),
        createElement("span", "day-date", dayKey),
      );
      const dayLayout = layoutDay(eventsByDay.get(offset + 1) || []);
      const dayItems = createElement("section", "day-items");
      dayItems.setAttribute("aria-label", `${label}: day items`);
      dayItems.append(createElement("p", "day-items-label", `Day items (${dayLayout.untimed.length})`));
      const items = createElement("div", "day-items-list day-events");
      for (const eventNode of dayLayout.untimed) {
        items.append(makeEventCard(eventNode, [...path, crumbFor(eventNode)]));
      }
      if (!dayLayout.untimed.length) items.append(createElement("p", "empty-message", "No day items."));
      dayItems.append(items);
      dayHeader.append(heading, dayItems);
      grid.append(dayHeader);
      days.push({ label, today: dayKey === todayKey, ...dayLayout });
    }
    const hours = createElement("div", "timeline-hours");
    for (let hour = 0; hour <= 24; hour += 1) {
      const label = createElement("span", "timeline-hour", `${String(hour).padStart(2, "0")}:00`);
      label.style.top = `${timelinePercent(hour * 60)}%`;
      hours.append(label);
    }
    grid.append(hours);
    for (const day of days) {
      const lane = createElement("section", `day-timeline${day.today ? " is-today" : ""}`);
      lane.setAttribute("aria-label", day.label);
      for (let hour = 0; hour < 24; hour += 1) {
        const line = createElement("div", "timeline-gridline");
        line.style.top = `${timelinePercent(hour * 60)}%`;
        line.setAttribute("aria-hidden", "true");
        lane.append(line);
      }
      for (const item of day.timed) {
        const card = makeEventCard(item.event, [...path, crumbFor(item.event)]);
        card.classList.add("timeline-event");
        if (item.end - item.start < 45) card.classList.add("is-short");
        card.style.top = `${timelinePercent(item.start)}%`;
        card.style.height = `${timelinePercent(item.end) - timelinePercent(item.start)}%`;
        card.style.left = "0";
        card.style.width = "100%";
        const label = `${day.label}: ${formatEventTime(item.event)} · ${item.event.display_title || item.event.title || item.event.id}`;
        card.title = [label, item.event.description].filter(Boolean).join("\n");
        card.setAttribute("aria-label", label);
        lane.append(card);
      }
      grid.append(lane);
    }
    scroll.append(grid);
    panel.append(scroll, makeWeekNotes(node, direct));
    return panel;
  }

  function makeWeekSummaryCard(weekNode, path) {
    const link = createElement("a", "week-summary-card");
    bindNodeLink(link, weekNode.id, path);
    const startDate = parseDateOnly(weekNode.start_date);
    const eventCount = (Array.isArray(weekNode.child_nodes) ? weekNode.child_nodes : [])
      .filter((child) => !child.missing && child.type === "event").length;
    link.append(
      createElement(
        "span",
        "week-summary-title",
        weekNode.title || formatWeekRange(startDate),
      ),
      createElement("span", "week-date-range", formatWeekCardRange(startDate)),
      createElement(
        "span",
        "week-summary-meta",
        `${eventCount} ${eventCount === 1 ? "event" : "events"}`,
      ),
    );
    return link;
  }

  function makeWeeksStack(weeks, path) {
    const stack = createElement("div", "calendar-weeks");
    for (const weekNode of weeks) {
      stack.append(makeWeekSummaryCard(weekNode, [...path, crumbFor(weekNode)]));
    }
    return stack;
  }

  function renderCalendar(node, path, direct = false) {
    const panel = createElement("section", "calendar-panel");
    if (!direct && node.title) {
      const heading = createElement("h2", "section-heading");
      heading.append(makeHeadingLink(node, path));
      panel.append(heading);
    }
    const weeks = (Array.isArray(node.child_nodes) ? node.child_nodes : [])
      .filter((child) => !child.missing && child.type === "week")
      .sort((left, right) => String(left.start_date || "").localeCompare(String(right.start_date || "")));
    if (!weeks.length) {
      panel.append(createElement("p", "empty-message", "No weeks in this calendar."));
      return panel;
    }
    const activeWeeks = weeks.filter((weekNode) => !weekNode.completed);
    const pastWeeks = weeks.filter((weekNode) => weekNode.completed);
    if (activeWeeks.length) {
      panel.append(makeWeeksStack(direct ? activeWeeks : activeWeeks.slice(0, 4), path));
    } else {
      panel.append(createElement("p", "empty-message", "No active weeks."));
    }
    if (!direct && (activeWeeks.length > 4 || pastWeeks.length)) {
      const more = createElement("a", "todo-preview-more", "Open calendar to view all weeks");
      bindNodeLink(more, node.id, path);
      panel.append(more);
    }
    if (direct && pastWeeks.length) {
      const past = createElement("details", "past-weeks");
      past.append(
        createElement(
          "summary",
          "past-weeks-summary",
          `Past weeks (${pastWeeks.length})`,
        ),
        makeWeeksStack(pastWeeks, path),
      );
      panel.append(past);
    }
    return panel;
  }

  async function renderCurrentWeek(node, path) {
    const panel = createElement("section", "calendar-panel calendar-current-week");
    const heading = createElement("h2", "section-heading");
    heading.append(makeHeadingLink(node, path)); panel.append(heading);
    try {
      // Deeper/repeated previews may omit children. Fetch only when necessary.
      const incomplete = !Array.isArray(node.child_nodes) || node.child_nodes.some(child => child.type === "week" && !Array.isArray(child.child_nodes));
      const calendar = incomplete ? await apiJson(`/api/node/${encodeURIComponent(node.id)}`) : node;
      const weeks = currentCalendarWeeks(calendar);
      if (!weeks.length) panel.append(createElement("p", "empty-message", "No week containing today in this calendar."));
      for (const week of weeks) panel.append(renderWeek(week, [...path, crumbFor(week)]));
    } catch (error) {
      panel.append(createElement("p", "empty-message", `Unable to load the current week: ${error.message}`));
    }
    const more = createElement("a", "todo-preview-more", "Open calendar to view all weeks");
    bindNodeLink(more, node.id, path); panel.append(more);
    return panel;
  }

  function renderEventDetail(node) {
    const panel = createElement("section", "event-detail");
    const when = makeLabeledSection("When", "event-detail-when");
    when.append(createElement("p", "event-detail-time", formatEventTime(node, true)));
    panel.append(when);
    const notes = createElement("div", "event-detail-notes");
    notes.append(createElement("h2", "section-heading", "Notes"));
    if (node.description) {
      appendText(notes, node.description);
    } else {
      notes.append(createElement("p", "empty-message", "No notes."));
    }
    panel.append(notes);
    return panel;
  }

  return { makeEventCard, renderCalendar, renderCurrentWeek, renderEventDetail, renderWeek };
}
