from collections import defaultdict
import asyncio

# Store user-specific state like intent sessions, panic status, etc.
user_context = defaultdict(dict)

# Optional: lock if concurrent writes become an issue
state_lock = asyncio.Lock()


