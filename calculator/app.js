(() => {
  const currentEl = document.getElementById('current');
  const historyEl = document.getElementById('history');

  const state = {
    current: '0',
    previous: null,
    op: null,
    justEvaluated: false,
  };

  const MAX_LEN = 14;

  function format(n) {
    if (n === null || n === undefined || n === '') return '0';
    if (typeof n === 'string') {
      // user is typing; preserve trailing dot etc.
      return n;
    }
    if (!isFinite(n)) return 'Error';
    // limit precision but trim trailing zeros
    const abs = Math.abs(n);
    let s;
    if (abs !== 0 && (abs < 1e-6 || abs >= 1e12)) {
      s = n.toExponential(6);
    } else {
      s = Number(n.toPrecision(12)).toString();
    }
    return s;
  }

  function render() {
    currentEl.textContent = format(state.current);
    if (state.previous !== null && state.op) {
      const sym = { '+': '+', '-': '−', '*': '×', '/': '÷' }[state.op] || state.op;
      historyEl.textContent = `${format(state.previous)} ${sym}`;
    } else {
      historyEl.textContent = '';
    }
  }

  function inputDigit(d) {
    if (state.justEvaluated) {
      state.current = d;
      state.justEvaluated = false;
      state.previous = null;
      state.op = null;
      return;
    }
    if (state.current === '0') state.current = d;
    else if (state.current.replace(/[^0-9]/g, '').length < MAX_LEN) state.current += d;
  }

  function inputDot() {
    if (state.justEvaluated) {
      state.current = '0.';
      state.justEvaluated = false;
      state.previous = null;
      state.op = null;
      return;
    }
    if (!state.current.includes('.')) state.current += '.';
  }

  function clearAll() {
    state.current = '0';
    state.previous = null;
    state.op = null;
    state.justEvaluated = false;
  }

  function toggleSign() {
    if (state.current === '0') return;
    state.current = state.current.startsWith('-')
      ? state.current.slice(1)
      : '-' + state.current;
  }

  function percent() {
    const n = parseFloat(state.current);
    if (isNaN(n)) return;
    state.current = String(n / 100);
  }

  function compute(a, b, op) {
    switch (op) {
      case '+': return a + b;
      case '-': return a - b;
      case '*': return a * b;
      case '/': return b === 0 ? Infinity : a / b;
    }
    return b;
  }

  function setOp(op) {
    const cur = parseFloat(state.current);
    if (state.previous !== null && state.op && !state.justEvaluated) {
      const result = compute(state.previous, cur, state.op);
      state.previous = result;
      state.current = format(result);
    } else {
      state.previous = cur;
    }
    state.op = op;
    state.justEvaluated = false;
    // next digit should start a fresh number
    state.current = '0';
    state._awaitingOperand = true;
  }

  function equals() {
    if (state.previous === null || !state.op) return;
    const cur = parseFloat(state.current);
    const result = compute(state.previous, cur, state.op);
    historyEl.textContent = `${format(state.previous)} ${{'+':'+','-':'−','*':'×','/':'÷'}[state.op]} ${format(cur)} =`;
    state.current = format(result);
    state.previous = null;
    state.op = null;
    state.justEvaluated = true;
    currentEl.textContent = state.current;
  }

  document.querySelector('.keys').addEventListener('click', (e) => {
    const btn = e.target.closest('button.key');
    if (!btn) return;
    if (btn.dataset.num !== undefined) {
      // when a fresh number begins after operator
      if (state._awaitingOperand) { state.current = '0'; state._awaitingOperand = false; }
      inputDigit(btn.dataset.num);
    } else if (btn.dataset.op) {
      setOp(btn.dataset.op);
    } else if (btn.dataset.action === 'dot') {
      if (state._awaitingOperand) { state.current = '0'; state._awaitingOperand = false; }
      inputDot();
    } else if (btn.dataset.action === 'clear') {
      clearAll();
    } else if (btn.dataset.action === 'sign') {
      toggleSign();
    } else if (btn.dataset.action === 'percent') {
      percent();
    } else if (btn.dataset.action === 'equals') {
      equals();
    }
    render();
  });

  // keyboard
  window.addEventListener('keydown', (e) => {
    const k = e.key;
    if (/^[0-9]$/.test(k)) {
      if (state._awaitingOperand) { state.current = '0'; state._awaitingOperand = false; }
      inputDigit(k);
    } else if (k === '.') {
      if (state._awaitingOperand) { state.current = '0'; state._awaitingOperand = false; }
      inputDot();
    } else if (['+','-','*','/'].includes(k)) {
      setOp(k);
    } else if (k === 'Enter' || k === '=') {
      e.preventDefault();
      equals();
    } else if (k === 'Escape') {
      clearAll();
    } else if (k === 'Backspace') {
      if (state.justEvaluated) { clearAll(); }
      else if (state.current.length <= 1 || (state.current.length === 2 && state.current.startsWith('-'))) {
        state.current = '0';
      } else {
        state.current = state.current.slice(0, -1);
      }
    } else if (k === '%') {
      percent();
    } else {
      return;
    }
    render();
  });

  render();
})();
