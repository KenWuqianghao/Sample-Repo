# Calculator

A tiny static calculator web app — no build step, no dependencies.

## Run

Just open `index.html` in a browser, or serve the folder:

```
python -m http.server -d calculator 8000
# then visit http://localhost:8000
```

## Features

- Add, subtract, multiply, divide
- Sign toggle (±), percent (%), all-clear (AC)
- Chained operations (e.g. `2 + 3 × 4 =` evaluates left-to-right)
- Full keyboard support: digits, `.`, `+`, `-`, `*`, `/`, `Enter`/`=`, `Backspace`, `Esc`, `%`
- Responsive dark UI, works on mobile
