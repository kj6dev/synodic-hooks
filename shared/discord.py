#!/usr/bin/env python3
"""
Discord notification utilities for Claude Code hooks

Provides simple Discord webhook integration for session lifecycle events.
Follows self-healing philosophy: errors never block hook execution.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


def get_webhook_url() -> Optional[str]:
    """
    Get Discord webhook URL from environment or .env file

    Checks DISCORD_WEBHOOK_URL environment variable first,
    then falls back to .env file in synodic-hooks root.

    Returns:
        Webhook URL if configured, None otherwise
    """
    # Check environment variable first
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if url:
        return url

    # Fall back to .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() == "DISCORD_WEBHOOK_URL":
                            return value.strip()
        except Exception:
            pass

    return None


def send_notification(
    message: str,
    project: str,
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send notification to Discord via webhook

    Args:
        message: Emoji/icon for the notification (e.g., "🛑", "🔔")
        project: Project/directory name
        webhook_url: Discord webhook URL (auto-detected if None)

    Returns:
        True if sent successfully, False otherwise

    Note:
        Errors are printed to stderr but don't raise exceptions.
        This maintains self-healing philosophy - never block hooks.
    """
    # Get webhook URL if not provided
    if webhook_url is None:
        webhook_url = get_webhook_url()

    # No webhook configured - exit silently
    if not webhook_url:
        return False

    try:
        # Build simple Discord payload: "🛑 `repo-name`"
        payload = {
            "content": f"{message} `{project}`"
        }

        # Convert to JSON and encode
        data = json.dumps(payload).encode('utf-8')

        # Create and send request
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Claude-Code-Hooks/1.0'
            }
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            # Discord webhooks return 204 on success
            return response.status == 204

    except urllib.error.HTTPError as e:
        print(f"⚠️  Discord webhook HTTP error: {e.code} {e.reason}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"⚠️  Discord webhook URL error: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"⚠️  Discord notification failed: {e}", file=sys.stderr)
        return False
