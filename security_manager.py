import time
import json
import asyncio
from typing import Any, Dict

from config import Config

class SecurityManager:
    """Define security policies and manage tool calls with rate limiting and user approval."""

    def __init__(self):
        # Define security policies for different tools
        self.tool_policies = Config.TOOL_POLICIES

        # Rate limiting state
        self.tool_call_counts: Dict[str, Dict[str, Any]] = {}

    def need_approval(self, tool_name: str) -> bool:
        """Check if a tool call requires approval.

        Args:
            tool_name: The name of the tool being called.
            args: Arguments passed to the tool.

        Returns:
            True if the tool call is allowed, False otherwise.
        """
        # Get policy for this tool (default is to require approval)
        policy = self.tool_policies.get(tool_name, Config.DEFAULT_TOOL_POLICY)
        
        if policy['requires_approval']:
            return True
        
        return False

    async def check_tool_call(self, tool_name: str, args: Any) -> bool:
        """Check if a tool call should be allowed.

        Args:
            tool_name: The name of the tool being called.
            args: Arguments passed to the tool.

        Returns:
            True if the tool call is allowed, False otherwise.
        """
        # Get policy for this tool (default is to require approval)
        policy = self.tool_policies.get(tool_name, Config.DEFAULT_TOOL_POLICY)

        # Check rate limits
        if not self._check_rate_limit(tool_name, policy['max_calls_per_minute']):
            print(f"Rate limit exceeded for tool {tool_name}")
            return False

        # If approval required, ask user
        if policy['requires_approval']:
            return await self._get_user_approval(tool_name, args)

        # No approval needed and rate limit not exceeded
        return True

    def _check_rate_limit(self, tool_name: str, max_calls_per_minute: int) -> bool:
        """Check if the tool call exceeds the rate limit.

        Args:
            tool_name: The name of the tool being called.
            max_calls_per_minute: Maximum allowed calls per minute.

        Returns:
            True if the call is within the rate limit, False otherwise.
        """
        now = time.time() * 1000  # Current time in milliseconds

        # Initialize count if not exists
        if tool_name not in self.tool_call_counts:
            self.tool_call_counts[tool_name] = {'count': 0, 'timestamp': now}

        record = self.tool_call_counts[tool_name]

        # Reset counter if more than a minute has passed
        if now - record['timestamp'] > 60000:
            record['count'] = 0
            record['timestamp'] = now

        # Increment counter
        record['count'] += 1

        # Check if limit exceeded
        return record['count'] <= max_calls_per_minute

    async def _get_user_approval(self, tool_name: str, args: Any) -> bool:
        """Ask the user for approval to execute the tool.

        Args:
            tool_name: The name of the tool being called.
            args: Arguments passed to the tool.

        Returns:
            True if the user approves, False otherwise.
        """
        print(f'Tool "{tool_name}" requires approval.')
        print('Arguments:', json.dumps(args, indent=2))
        print('Type "y" to approve, anything else to deny:')

        # Wait for user input
        return await self._get_user_input()

    async def _get_user_input(self) -> bool:
        """Get user input asynchronously."""
        return await self._read_input()

    async def _read_input(self) -> bool:
        """Read input from the user."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_read_input)

    def _sync_read_input(self) -> bool:
        """Synchronously read input from the user."""
        input_data = input().strip().lower()
        return input_data == 'y' or input_data == 'yes'
