(() => {
  const display = document.getElementById('display');

  const state = {
    current: '0',
    previous: null,
    op: null,
    justEvaluated: false,
  };

  const format = (n) => {
    if (n === 'Error') return n;
    const num = Number(n);
    if (!isFinite(num)) return 'Error';
    // Trim long floats while keeping precision-ish
    const str = Math.abs(num) < 1e-9 && num !== 0 ? num.toExponential(6) : String(num);
    if (str.length > 12 && !str.includes('e')) return num.toPrecision(10).replace(/\.?0+$/, '');
    return str;
  };

  const render = () => { display.textContent = state.current; };

  const compute = (a, b, op) => {
    a = Number(a); b = Number(b);
    switch (op) {
      case '+': return a + b;
      case '-': return a - b;
      case '*': return a * b;
      case '/': return b === 0 ? 'Error' : a / b;
    }
    return b;
  };

  const inputDigit = (d) => {
    if (state.justEvaluated) { state.current = '0'; state.justEvaluated = false; }
    state.current = state.current === '0' ? d : state.current + d;
  };

  const inputDot = () => {
    if (state.justEvaluated) { state.current = '0'; state.justEvaluated = false; }
    if (!state.current.includes('.')) state.current += '.';
  };

  const setOp = (op) => {
    if (state.op && state.previous !== null && !state.justEvaluated) {
      const r = compute(state.previous, state.current, state.op);
      state.previous = format(r);
      state.current = format(r);
    } else {
      state.previous = state.current;
    }
    state.op = op;
    state.justEvaluated = false;
    state.current = '0';
    // show running value
    display.textContent = state.previous;
    return;
  };

  const equals = () => {
    if (state.op === null || state.previous === null) return;
    const r = compute(state.previous, state.current, state.op);
    state.current = format(r);
    state.previous = null;
    state.op = null;
    state.justEvaluated = true;
  };

  const clearAll = () => {
    state.current = '0'; state.previous = null; state.op = null; state.justEvaluated = false;
  };

  const sign = () => {
    if (state.current === '0' || state.current === 'Error') return;
    state.current = state.current.startsWith('-')
      ? state.current.slice(1)
      : '-' + state.current;
  };

  const percent = () => {
    state.current = format(Number(state.current) / 100);
  };

  document.querySelectorAll('.key').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      if (action === 'digit') inputDigit(btn.dataset.digit);
      else if (action === 'dot') inputDot();
      else if (action === 'op') { setOp(btn.dataset.op); return; }
      else if (action === 'equals') equals();
      else if (action === 'clear') clearAll();
      else if (action === 'sign') sign();
      else if (action === 'percent') percent();
      render();
    });
  });

  document.addEventListener('keydown', (e) => {
    const k = e.key;
    if (/[0-9]/.test(k)) { inputDigit(k); render(); }
    else if (k === '.') { inputDot(); render(); }
    else if (['+','-','*','/'].includes(k)) { setOp(k); }
    else if (k === 'Enter' || k === '=') { e.preventDefault(); equals(); render(); }
    else if (k === 'Escape') { clearAll(); render(); }
    else if (k === 'Backspace') {
      state.current = state.current.length <= 1 || (state.current.length === 2 && state.current.startsWith('-'))
        ? '0' : state.current.slice(0, -1);
      render();
    }
  });

  render();
})();
