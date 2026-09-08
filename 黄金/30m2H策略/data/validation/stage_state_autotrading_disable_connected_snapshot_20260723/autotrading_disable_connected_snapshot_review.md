# AutoTrading Disable Connected-Session Snapshot

Generated: 2026-07-23T19:45:12

## Decision

- Status: `connected_session_autotrading_disabled_confirmed`
- Terminal connected: `True`
- Terminal trade_allowed: `False`
- Emergency stop flag exists: `True`
- Runner stop flag exists: `True`
- Orders placed: `false`
- Runner executed: `false`
- Ready to live trade: `false`

## Summary

This is a read-only connected-session snapshot. It verifies the terminal-side trading permission and stop flags without placing orders or invoking the Python runner.
