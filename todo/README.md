# Todo List

A zero-dependency static todo list web app.

## Features

- Add, edit (double-click), complete, and delete tasks
- Filter by **All / Active / Completed**
- "Clear completed" bulk action
- Persists to `localStorage` across reloads
- Keyboard friendly: `Enter` to add or save edits, `Esc` to cancel an edit
- Responsive layout, no build step, no dependencies

## Run

From the repo root:

```bash
python -m http.server -d todo 8000
```

Then open <http://localhost:8000>.

## Files

- `index.html` — markup
- `styles.css` — styling
- `app.js` — state, rendering, and persistence
