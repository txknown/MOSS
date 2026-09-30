import re


def search_nodes(memory, query):
    query = str(query or "").strip()
    if not query:
        raise ValueError("Use: search <query>")

    needle = query.casefold()
    results = []
    for meta in memory.list_nodes():
        content = memory.read_content(meta["id"])
        description = meta.get("description", "")
        searchable = (
            meta["id"],
            meta.get("type", ""),
            meta.get("title", ""),
            description,
            content,
        )
        if not any(needle in str(value).casefold() for value in searchable):
            continue

        snippet = None
        if needle in str(description).casefold():
            snippet = _matching_snippet(description, query)
        elif needle in content.casefold():
            snippet = _matching_snippet(content, query)
        results.append(
            {
                "id": meta["id"],
                "type": meta.get("type", "(unknown)"),
                "title": meta.get("title") or meta["id"],
                "snippet": snippet,
            }
        )

    return sorted(results, key=lambda item: (item["title"].casefold(), item["id"]))


def format_search_results(query, results):
    lines = [f"Search: {str(query).strip()}", ""]
    if not results:
        lines.append("No results")
        return "\n".join(lines)

    for index, result in enumerate(results):
        if index:
            lines.append("")
        lines.append(f"{result['title']} [{result['type']}]")
        lines.append(f"ID: {result['id']}")
        if result.get("snippet"):
            lines.append(f'"...{result["snippet"]}..."')
    return "\n".join(lines)


def _matching_snippet(text, query, radius=45):
    compact = re.sub(r"\s+", " ", str(text)).strip()
    index = compact.casefold().find(str(query).casefold())
    if index < 0:
        return compact[: radius * 2].strip()
    start = max(0, index - radius)
    end = min(len(compact), index + len(str(query)) + radius)
    return compact[start:end].strip()
