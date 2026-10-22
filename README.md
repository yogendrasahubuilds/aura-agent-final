# Here are your Instructions

## Turning authentication on/off

Set `AUTH_ENABLED` in `backend/.env` and `REACT_APP_AUTH_ENABLED` in `frontend/.env` to the same value. Use `true` (the default if missing) for signup, login, and JWT-protected accounts. Set both to `false` to open AURA directly as Guest; if MongoDB is unavailable in this mode, AURA uses temporary in-memory storage that is cleared when the backend restarts. Restart the backend and frontend after changing these variables.
