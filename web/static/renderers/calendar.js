"use strict";

import { apiJson } from "../api.js?v=24";
import {
  appendText,
  createElement,
  makeLabeledSection,
  shortExcerpt,
} from "../dom.js?v=24";

const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export function parseDateOnly(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (
    date.getFullYear() !== Number(match[1]) ||
    date.getMonth() !== Number(match[2]) - 1 ||
    date.getDate() !== Number(match[3])
  ) {
    return null;
  }
  return date;
}

function parseClockMinutes(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return null;
  return hours * 60 + minutes;
}

function localDateKey(date) {
  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatWeekRange(startDate) {
  if (!startDate) return "Week";
  const endDate = new Date(startDate);
  endDate.setDate(endDate.getDate() + 6);
  const start = startDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const end = endDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return `${start} – ${end}`;
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
  let timeLabel = "Time not set";
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
      createElement("h2", "event-composer-title", "Add an event"),
    );
    const toggle = createElement("button", "primary-button", "Add event");
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
        date.toLocaleDateString(undefined, {
          weekday: "long",
          month: "short",
          day: "numeric",
        }),
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

    const notesLabel = createElement("label", "event-field event-field-wide");
    notesLabel.append(createElement("span", "event-field-label", "Notes (optional)"));
    const notesInput = createElement("textarea");
    notesInput.name = "description";
    notesInput.rows = 4;
    if (eventAttributes.description?.editor?.max_length) {
      notesInput.maxLength = eventAttributes.description.editor.max_length;
    }
    notesLabel.append(notesInput);

    grid.append(titleLabel, dayLabel, startLabel, endLabel, notesLabel);
    const feedback = createElement("p", "event-form-feedback");
    feedback.setAttribute("role", "alert");
    const actions = createElement("div", "event-form-actions");
    const submit = createElement("button", "primary-button", "Create event");
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
    toggle.addEventListener("click", () => {
      form.hidden = false;
      toggle.hidden = true;
      toggle.setAttribute("aria-expanded", "true");
      titleInput.focus();
    });
    cancel.addEventListener("click", closeForm);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.textContent = "";
      const startMinutes = parseClockMinutes(startInput.value);
      const endMinutes = parseClockMinutes(endInput.value);
      if (startMinutes === null || endMinutes === null || endMinutes <= startMinutes) {
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
            start_time: startInput.value,
            end_time: endInput.value,
          },
        });
        await displayNode(response.week, path, window.scrollY);
        showActionNotice(`Created ${response.event.display_title || response.event.id}.`);
      } catch (error) {
        feedback.textContent = error instanceof Error ? error.message : String(error);
        submit.disabled = false;
        cancel.disabled = false;
        submit.textContent = "Create event";
      }
    });
    return composer;
  }

  function renderWeek(node, path, direct = false) {
    const panel = createElement("section", "week-panel");
    const startDate = parseDateOnly(node.start_date);
    const rangeLabel = node.title || formatWeekRange(startDate);
    if (!direct) {
      const header = createElement("header", "week-header");
      const heading = createElement("h2", "week-title");
      heading.append(makeHeadingLink({ ...node, display_title: rangeLabel }, path));
      header.append(heading);
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

    if (direct) panel.append(makeEventComposer(node, path, startDate));

    const scroll = createElement("div", "week-grid-scroll");
    const grid = createElement("div", "week-grid");
    const todayKey = localDateKey(new Date());
    for (let offset = 0; offset < 7; offset += 1) {
      const day = new Date(startDate);
      day.setDate(startDate.getDate() + offset);
      const dayKey = localDateKey(day);
      const column = createElement(
        "section",
        `week-day${dayKey === todayKey ? " is-today" : ""}`,
      );
      column.setAttribute(
        "aria-label",
        day.toLocaleDateString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
        }),
      );
      const dayHeader = createElement("header", "day-header");
      dayHeader.append(
        createElement(
          "span",
          "day-name",
          day.toLocaleDateString(undefined, { weekday: "short" }),
        ),
        createElement("span", "day-number", day.getDate()),
      );
      const dayEvents = createElement("div", "day-events");
      for (const eventNode of eventsByDay.get(offset + 1) || []) {
        dayEvents.append(makeEventCard(eventNode, [...path, crumbFor(eventNode)]));
      }
      if (!dayEvents.childElementCount) {
        dayEvents.append(createElement("span", "day-empty", "No events"));
      }
      column.append(dayHeader, dayEvents);
      grid.append(column);
    }
    scroll.append(grid);
    panel.append(scroll);
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
      panel.append(makeWeeksStack(activeWeeks, path));
    } else {
      panel.append(createElement("p", "empty-message", "No active weeks."));
    }
    if (pastWeeks.length) {
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

  return { makeEventCard, renderCalendar, renderEventDetail, renderWeek };
}
