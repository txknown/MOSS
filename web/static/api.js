"use strict";

export const REQUIRED_API_VERSION = 14;

export async function apiJson(url, options = {}) {
  const method = options.method || "GET";
  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
  };
  const request = { method, headers, cache: "no-store" };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-MOSS-Request"] = options.requestMarker || "create-event";
    request.body = JSON.stringify(options.body);
  }
  const response = await fetch(url, request);
  if (!response.ok) {
    let message = `Unable to read MOSS (${response.status}).`;
    try {
      const body = await response.json();
      if (body && body.detail) {
        message = body.detail;
      }
    } catch (_error) {
      // The friendly status message above is sufficient for non-JSON errors.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function loadSchema() {
  const health = await apiJson("/api/health");
  if (
    health.application !== "moss" ||
    Number(health.api_version || 0) < REQUIRED_API_VERSION
  ) {
    throw new Error(
      "The MOSS web server is out of date. Stop the running server with Ctrl+C, then run python start_web.py again.",
    );
  }
  const schema = await apiJson("/api/schema");
  if (!schema || schema.schema_version !== 1 || !schema.node_types) {
    throw new Error(
      "The MOSS web server returned an incompatible node schema. Restart python start_web.py and try again.",
    );
  }
  return schema.node_types;
}

export function runMossAction(action, payload) {
  return apiJson("/api/actions", {
    method: "POST",
    requestMarker: "run-action",
    body: { action, payload },
  });
}
