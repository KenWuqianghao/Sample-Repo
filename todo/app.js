(() => {
  "use strict";

  const STORAGE_KEY = "todo-app:v1";

  /** @type {{id: string, text: string, done: boolean}[]} */
  let todos = load();
  let filter = "all";

  const form = document.getElementById("new-todo-form");
  const input = document.getElementById("new-todo-input");
  const list = document.getElementById("todo-list");
  const summary = document.getElementById("summary");
  const filterBtns = document.querySelectorAll(".filters__btn");
  const clearBtn = document.getElementById("clear-completed");

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  }

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function addTodo(text) {
    const trimmed = text.trim();
    if (!trimmed) return;
    todos.unshift({ id: uid(), text: trimmed, done: false });
    save();
    render();
  }

  function toggle(id) {
    const t = todos.find((x) => x.id === id);
    if (!t) return;
    t.done = !t.done;
    save();
    render();
  }

  function remove(id) {
    todos = todos.filter((x) => x.id !== id);
    save();
    render();
  }

  function update(id, text) {
    const trimmed = text.trim();
    const t = todos.find((x) => x.id === id);
    if (!t) return;
    if (!trimmed) {
      remove(id);
      return;
    }
    t.text = trimmed;
    save();
    render();
  }

  function clearCompleted() {
    todos = todos.filter((t) => !t.done);
    save();
    render();
  }

  function visibleTodos() {
    if (filter === "active") return todos.filter((t) => !t.done);
    if (filter === "completed") return todos.filter((t) => t.done);
    return todos;
  }

  function render() {
    list.innerHTML = "";
    const items = visibleTodos();

    if (items.length === 0) {
      const li = document.createElement("li");
      li.className = "todo-list__empty";
      li.textContent =
        filter === "all"
          ? "Nothing here yet. Add your first task!"
          : `No ${filter} tasks.`;
      list.appendChild(li);
    } else {
      for (const t of items) list.appendChild(renderItem(t));
    }

    const remaining = todos.filter((t) => !t.done).length;
    const total = todos.length;
    summary.textContent =
      total === 0
        ? "No tasks yet"
        : `${remaining} of ${total} remaining`;
  }

  function renderItem(t) {
    const li = document.createElement("li");
    li.className = "todo-item" + (t.done ? " is-done" : "");
    li.dataset.id = t.id;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "todo-item__checkbox";
    checkbox.checked = t.done;
    checkbox.addEventListener("change", () => toggle(t.id));

    const span = document.createElement("span");
    span.className = "todo-item__text";
    span.textContent = t.text;
    span.title = "Double-click to edit";
    span.addEventListener("dblclick", () => startEdit(li, t));

    const del = document.createElement("button");
    del.className = "todo-item__delete";
    del.type = "button";
    del.setAttribute("aria-label", "Delete task");
    del.textContent = "✕";
    del.addEventListener("click", () => remove(t.id));

    li.append(checkbox, span, del);
    return li;
  }

  function startEdit(li, t) {
    const span = li.querySelector(".todo-item__text");
    const editor = document.createElement("input");
    editor.type = "text";
    editor.className = "todo-item__edit";
    editor.value = t.text;
    li.replaceChild(editor, span);
    editor.focus();
    editor.setSelectionRange(editor.value.length, editor.value.length);

    let committed = false;
    const commit = () => {
      if (committed) return;
      committed = true;
      update(t.id, editor.value);
    };

    editor.addEventListener("blur", commit);
    editor.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        editor.blur();
      } else if (e.key === "Escape") {
        committed = true;
        render();
      }
    });
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    addTodo(input.value);
    input.value = "";
    input.focus();
  });

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filter = btn.dataset.filter;
      filterBtns.forEach((b) => b.classList.toggle("is-active", b === btn));
      render();
    });
  });

  clearBtn.addEventListener("click", clearCompleted);

  render();
})();
