# HQE Fyers Token Hot Reload V1

Each current-day live-data cycle reloads the latest FYERS access token from disk before invoking the fetcher.

Priority:

1. `secrets/fyers_access_token.txt`
2. `%LOCALAPPDATA%/HunterQuantEngine/FyersAuth/FYERS_ACCESS_TOKEN.txt`
3. inherited environment variable fallback

This prevents a long-running paper-watch process from repeatedly using a stale token after the operator refreshes the token file.

Manual browser authentication is still required whenever FYERS rejects or expires the token. No broker execution or real orders are enabled.
