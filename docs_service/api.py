import asyncio

import asyncpg
from rapidfuzz import fuzz, process
from sanic import Blueprint, Request, Sanic
from sanic.response import HTTPResponse, json

import config

app = Sanic("ahkdocs_api")

api = Blueprint("api", url_prefix="/api")

from pprint import pprint as pp


def docs_search(names, query, k=8):
    if not query:
        return []

    query = query.strip()

    ratio = process.extract(
        query=query,
        choices=names,
        scorer=fuzz.token_ratio,
        processor=None,
        limit=10,
    )

    # pp(ratio[:4])

    tweak = list()
    query = query.lower()

    for name, score, junk in ratio:
        lower = name.lower()

        # we could do this for more chars? like iteratively
        if query[0] == lower[0]:
            score += 5

        if lower == query:
            score += 40

        if lower.startswith(query):
            score += 20

        if query in lower:
            score += 10

        tweak.append((name, score))

    tweak = list(sorted(tweak, key=lambda v: v[1], reverse=True))
    # pp(tweak[:4])

    l = list(name for name, score in tweak)[:k]

    return l


def entry_to_dict(row):
    return dict(
        id=row.get("id"),
        v=row.get("v"),
        name=row.get("name"),
        page=row.get("page"),
        fragment=row.get("fragment"),
        content=row.get("content"),
        syntax=row.get("syntax"),
        version=row.get("version"),
    )


async def get_entry(
    conn: asyncpg.Connection, docs_id: int, lineage=True, search_match=None
):
    row = await conn.fetchrow("SELECT * FROM docs_entry WHERE id=$1", docs_id)

    o = entry_to_dict(row)

    if lineage:
        parents = []
        children = []

        for parent_id in row.get("parents"):
            if parent_id is None:  # shouldn't happen
                continue
            parents.append(await get_entry(conn, parent_id, lineage=False))

        rows = await conn.fetch(
            "SELECT * FROM docs_entry WHERE parents[array_upper(parents, 1)] = $1",
            docs_id,
        )
        for row in rows:
            children.append(entry_to_dict(row))

        o["parents"] = parents
        o["children"] = children
        o["search_match"] = search_match

    return o


@api.post("/search")
async def search(request: Request):
    data = request.json

    if data is None:
        return HTTPResponse(status=400)

    q = data.get("q", None)
    v = data.get("v", None)

    if q is None or v is None:
        return HTTPResponse(status=400)

    if not isinstance(q, str) or not isinstance(v, int):
        return HTTPResponse(status=400)

    names = app.ctx.names[v]

    res = docs_search(names, q, k=5)
    return json(res)


@api.post("/entry")
async def entry(request: Request):
    data = request.json

    if data is None:
        return HTTPResponse(status=400)

    q = data.get("q", None)
    v = data.get("v", None)

    if q is None or v is None:
        return HTTPResponse(status=400)

    if not isinstance(q, str) or not isinstance(v, int):
        return HTTPResponse(status=400)

    names = app.ctx.names[v]

    res = docs_search(names, q, k=1)[0]
    docs_id = app.ctx.id_map[v][res]

    async with app.ctx.pool.acquire() as conn:
        conn: asyncpg.Connection
        async with conn.transaction():
            return json(await get_entry(conn, docs_id, lineage=True, search_match=res))


app.blueprint(api)


@app.signal("server.init.before")
async def setup(app, loop):
    pool = await asyncpg.create_pool(config.DB_BIND)

    async with pool.acquire() as conn:
        conn: asyncpg.Connection
        async with conn.transaction():
            res = await conn.fetch("SELECT * FROM docs_name")
            id_map = {v: {} for v in (1, 2)}
            names = {v: [] for v in (1, 2)}

            for row in res:
                v = row.get("v")
                docs_id = row.get("docs_id")
                name = row.get("name")
                id_map[v][name] = docs_id
                names[v].append(name)

    if True:
        from pprint import pprint as pp
        while True:
            i = input("Prompt: ")
            res = docs_search(names[1], i)
            pp(res)
    else:
        app.ctx.names = names
        app.ctx.id_map = id_map
        app.ctx.pool = pool


if False:
    app.run("0.0.0.0", 80)
else:
    loop = asyncio.new_event_loop()
    loop.create_task(setup(None, None))
    loop.run_forever()
