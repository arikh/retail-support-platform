# Loop breaker: stop the graph if a run exceeds this many steps.
MAX_STEPS = 10

# Inner loop breaker: max steps inside one worker's tool loop.
WORKER_RECURSION_LIMIT = 12

# How many times a worker may run its agent before giving up.
WORKER_ATTEMPTS = 2

SUPPORT_TOOL_SOURCES = ("in_process", "mcp")
DEFAULT_SUPPORT_TOOL_SOURCE = "in_process"