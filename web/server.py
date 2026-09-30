"""Local FastAPI application for MOSS reads and narrowly scoped actions."""

import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.action_catalog import public_action_types
from core.action_runner import ActionRunner
from core.memory import Memory
from web.read_service import (
    MalformedNodeError,
    MaterialNotFoundError,
    NodeNotFoundError,
    ReadService,
    ReadServiceError,
    UnsafeMaterialPathError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
WEB_ACTIONS = {
    "create_child",
    "create_item",
    "link_node",
    "move_child",
    "snapshot",
    "unlink_node",
    "update_node",
    "submit_log_entry",
    "update_log_template",
    "update_log_entry",
    "update_item",
    "update_item_list_fields",
    "trash_node",
}


def create_app(project_root: str | Path | None = None) -> FastAPI:
    resolved_root = Path(project_root or PROJECT_ROOT).resolve()
    service = ReadService(resolved_root)
    actions = ActionRunner(Memory(project_root=resolved_root, initialize=False))
    write_lock = threading.Lock()
    application = FastAPI(
        title="MOSS local web interface",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.read_service = service
    application.state.action_runner = actions
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )

    @application.middleware("http")
    async def action_boundary(request, call_next):
        write_markers = {
            "/api/events": "create-event",
            "/api/actions": "run-action",
        }
        expected_marker = write_markers.get(request.url.path)
        is_allowed_write = request.method == "POST" and expected_marker is not None
        if request.method not in {"GET", "HEAD"} and not is_allowed_write:
            allowed_methods = "POST" if expected_marker else "GET, HEAD"
            return JSONResponse(
                status_code=405,
                content={"detail": "This write operation is not available in MOSS web."},
                headers={"Allow": allowed_methods},
            )
        if is_allowed_write:
            expected_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
            if request.headers.get("origin") != expected_origin:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "MOSS actions require a same-origin MOSS page."},
                )
            if request.headers.get("sec-fetch-site") not in {None, "same-origin"}:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-site event creation is not allowed."},
                )
            if request.headers.get("x-moss-request") != expected_marker:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "The MOSS action header is missing."},
                )
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={"detail": "MOSS actions require JSON."},
                )
            try:
                content_length = int(request.headers.get("content-length", "0"))
            except ValueError:
                content_length = 0
            maximum_length = 20_000 if request.url.path == "/api/events" else 300_000
            if content_length > maximum_length:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "MOSS action request is too large."},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith(("/api/", "/static/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(NodeNotFoundError)
    async def node_not_found(_request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    async def malformed_read(_request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    application.add_exception_handler(MalformedNodeError, malformed_read)
    application.add_exception_handler(UnsafeMaterialPathError, malformed_read)

    @application.exception_handler(MaterialNotFoundError)
    async def material_not_found(_request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.exception_handler(ReadServiceError)
    async def read_failure(_request, error):
        return JSONResponse(status_code=500, content={"detail": str(error)})

    @application.exception_handler(ValueError)
    async def invalid_action(_request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.exception_handler(FileNotFoundError)
    async def missing_action_target(_request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @application.get("/api/health")
    def health():
        return {
            **service.health(),
            "application": "moss",
            "api_version": 14,
            "read_only": False,
            "write_capabilities": [
                "events:create",
                "nodes:update",
                "children:create",
                "items:create",
                "items:update",
                "item-lists:update-fields",
                "children:link",
                "children:move",
                "children:unlink",
                "logs:submit",
                "logs:update-template",
                "logs:update-entry",
                "snapshots:create",
                "nodes:delete",
            ],
        }

    @application.get("/api/node/{node_id}")
    def node(node_id: str):
        with write_lock:
            return service.get_node(node_id)

    @application.get("/api/schema")
    def schema():
        with write_lock:
            return service.get_schema()

    @application.get("/api/action-types")
    def action_types():
        with write_lock:
            return public_action_types(WEB_ACTIONS | {"create_event"})

    @application.get("/api/snapshots")
    def snapshots():
        with write_lock:
            return service.get_snapshots()

    @application.get("/api/tree")
    def tree():
        with write_lock:
            return service.get_tree()

    @application.get("/api/search")
    def search(q: str = Query(default="", max_length=200)):
        with write_lock:
            return service.search(q)

    @application.get("/api/pages")
    def pages():
        with write_lock:
            return service.get_pages()

    @application.get("/api/change-log")
    def change_log():
        return service.get_change_log()

    @application.get("/api/action-log")
    def action_log(limit: int = Query(default=250, ge=1, le=1000)):
        with write_lock:
            return service.get_action_log(limit)

    @application.post("/api/events", status_code=201)
    def create_event(payload: dict[str, Any]):
        with write_lock:
            result = actions.run("create_event", payload=payload)
            return {
                "event": service.get_node(result["node_id"]),
                "week": service.get_node(result["week_id"]),
            }

    @application.post("/api/actions")
    def run_action(payload: dict[str, Any]):
        unknown_fields = sorted(set(payload) - {"action", "payload"})
        if unknown_fields:
            raise ValueError(f"Unknown action request field: {', '.join(unknown_fields)}")
        action_name = payload.get("action")
        action_payload = payload.get("payload", {})
        if action_name not in WEB_ACTIONS:
            raise ValueError("This MOSS action is not available in the web interface.")
        if not isinstance(action_payload, dict):
            raise ValueError("Action payload must be an object.")

        with write_lock:
            result = actions.run(action_name, payload=action_payload)
            if action_name == "snapshot":
                return {
                    "action": action_name,
                    "result": {"name": result["name"]},
                    "node": None,
                }
            if action_name == "trash_node":
                return {
                    "action": action_name,
                    "result": result,
                    "node": None,
                }
            primary_id = result.get("parent_id") or result.get("node_id")
            response = {
                "action": action_name,
                "result": result,
                "node": service.get_node(primary_id) if primary_id else None,
            }
            if action_name in {"create_child", "create_item"}:
                response["created"] = service.get_node(result["node_id"])
            return response

    @application.get("/materials/{material_path:path}", include_in_schema=False)
    def material(material_path: str):
        path = service.resolve_material_request(material_path)
        return FileResponse(
            path,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "Cross-Origin-Resource-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @application.get("/snapshots/{snapshot_name}.zip", include_in_schema=False)
    def snapshot_download(snapshot_name: str):
        path = service.resolve_snapshot_request(snapshot_name)
        return FileResponse(
            path,
            filename=path.name,
            media_type="application/zip",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "Cross-Origin-Resource-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def frontend():
        return FileResponse(
            STATIC_ROOT / "index.html",
            media_type="text/html",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                    "base-uri 'none'; form-action 'self'"
                ),
            },
        )

    application.add_api_route("/", frontend, methods=["GET"], include_in_schema=False)
    application.add_api_route(
        "/node/{node_id}",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/search",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/node-types",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/action-types",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/snapshots",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route("/tree", frontend, methods=["GET"], include_in_schema=False)
    application.add_api_route(
        "/action-log",
        frontend,
        methods=["GET"],
        include_in_schema=False,
    )
    application.add_api_route(
        "/change-log", frontend, methods=["GET"], include_in_schema=False,
    )
    application.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
    return application


app = create_app()
