# Calculator Web App

A small zero-dependency calculator in plain HTML/CSS/JS.

## Run
Just open `calculator/index.html` in a browser, or serve the folder:

```bash
python -m http.server -d calculator 8000
# then visit http://localhost:8000
```

## Features
- Basic ops: `+`, `−`, `×`, `÷`
- Sign toggle (±), percent (%), clear (AC)
- Keyboard support: digits, `.`, `+ - * /`, `Enter`/`=`, `Esc`, `Backspace`
- Divide-by-zero shows `Error`
