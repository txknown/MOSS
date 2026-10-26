"use strict";

export function clockMinutes(value) {
  const match = String(value || "").match(/^(\d{2}):(\d{2})$/);
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}

// 00:00–06:00 uses half the height per minute; the remaining hours are uniform.
export function timelinePercent(minutes) {
  const scaled = Math.min(minutes, 360) / 2 + Math.max(0, minutes - 360);
  return scaled / 1260 * 100;
}

// Preserve every timed event; overlapping cards occupy the same day column.
export function layoutDay(events) {
  const timed = [];
  const untimed = [];
  for (const event of events) {
    const start = clockMinutes(event.start_time);
    const end = clockMinutes(event.end_time);
    if (start === null || end === null || end <= start) untimed.push(event);
    else timed.push({ event, start, end });
  }
  timed.sort((a, b) => a.start - b.start || b.end - a.end || String(a.event.id).localeCompare(String(b.event.id)));
  return { timed, untimed };
}
