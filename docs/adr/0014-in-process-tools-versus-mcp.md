# ADR-0014: In-Process Tools versus MCP — One Implementation, Two Registrations

## Status
Accepted

## Context

The platform's workers call their tools as plain in-process functions (7 tools: 4 support,
3 analysis). The Model Context Protocol (MCP) is the standard way for an outside host — another
team's agent, a desktop assistant, an IDE — to call tools it cannot import as code. We
needed to decide whether the platform's own agent should move to MCP, and how to offer the
pricing lookups to outside hosts without a second copy of the SQL.

Two facts in the code shaped the decision. First, the support tools were wrapped by
LangChain's @tool, so an MCP server that imported them would depend on LangChain. Second,
every query ran through db.py as the retail user, which is a Postgres superuser; read-only
was set by the code on each connection, not enforced by the database. A separate MCP
process would not have passed through that code path at all.

## Decision

The agent keeps its in-process tools. The MCP server exposes the same lookups to outside
hosts. Both register the same functions, so there is one implementation.

The four support lookups live as plain async functions in pricing_lookups.py, which imports
neither LangChain nor MCP. support_tools.py registers them with LangChain. mcp_server.py
registers the same four with MCPServer (mcp 2.3.0), each marked with a read-only
annotation. The function name is the tool name and the docstring is the description in both
registrations.

The MCP server connects to Postgres as its own role, retail_mcp_ro
(sql/005_mcp_readonly_role.sql): SELECT on the four pricing tables only, and a 5-second
statement timeout. It cannot read pii_vault, thread_metadata or the checkpoints schema.
The server chooses this role in its lifespan through db.use_database_url(); if
MCP_DATABASE_URL is missing the server fails at start instead of falling back to the
superuser.

The server exposes narrow domain tools only. It will never expose a general SQL tool.

The rule we follow: in-process tools inside one application; MCP at the boundary between
applications or teams.

Alternatives considered and rejected:

- The agent calls its own tools through MCP. Rejected: it adds a process that can be down
  or slow, and more to deploy and monitor, while the agent and the tools share one
  codebase, one language and one release.
- A separate MCP server with its own copy of the SQL. Rejected: two implementations drift
  apart.
- The MCP server imports the LangChain tools. Rejected: the server would depend on
  LangChain and would run its queries as the application's database user.

## Consequences

One function and one docstring serve both the agent and MCP. A change to a docstring
changes the prompt text for both; that is intended, but it means a docstring edit is a
prompt change.

Read-only is enforced by the database for the MCP path. The read-only annotation is a hint
that a client may ignore; the role is the control. Tool arguments are validated against the
schema generated from the type hints before the function runs, and a bad call returns as a
tool error the model can read.

What has been shown by a run: the four tools over stdio in the MCP Inspector (that session
used protocol revision 2025-11-25); five automated tests through an in-memory client on
revision 2026-07-28, including that queries run as retail_mcp_ro; and our own client
scripts over stdio and over Streamable HTTP on localhost, both on 2026-07-28. The client,
not the server or the transport, decides which revision is used.

What is not built: the agent is not an MCP host and does not call any MCP server. The HTTP
server has no sign-in and no TLS and listens on 127.0.0.1 only; it is not deployed. There
is no automated test for the stdio or HTTP transports — those are manual scripts.

Known gaps accepted for now:

- The agent's own path still connects as the retail superuser, with read-only set per
  connection in db.py. Follow-up: a non-superuser role for the application.
- db.use_database_url() is one setting per process. That fits one process with one
  database identity; a process that needed two identities would have to pass a connection
  in instead.
- Tool descriptions carry the leading newline and indentation of the docstrings. It is
  small, but descriptions are sent to the model on every request.
- The three analysis tools are not on the MCP server. The MCP tool list is a second list
  to keep in step when tools are added.

## Trigger

This ADR is revisited when any of these happens:

- A second application or team needs these tools. Then the server is deployed over
  Streamable HTTP with authorization in front of it.
- The agent needs tools owned by someone else. Then the agent becomes an MCP host, tool
  output from those servers is untrusted text that must never reach a routing decision,
  and approvals live in the host.
- The tool count on one server grows large enough to hurt cost or tool selection.

## References
- ADR-0006 — PII vault (the MCP role cannot read it)
- ADR-0012 — worker design (the in-process tool path)
- sql/005_mcp_readonly_role.sql
- src/retail_support/pricing_lookups.py, support_tools.py, mcp_server.py, db.py
- tests/test_mcp_server.py
- tests/test_db.py::test_use_database_url_switches_the_database_user
- scripts/try_mcp_http.py, scripts/try_mcp_stdio.py
- MCP specification 2026-07-28 — architecture (one client per server; the host enforces
  the boundary)
- Build plan — Piece 1
