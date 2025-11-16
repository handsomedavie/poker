(function(){
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.expand();
    tg.enableClosingConfirmation();
    tg.MainButton.setParams({ text: 'Играть', is_visible: false });
  }

  const $ = (id) => document.getElementById(id);

  const userLine = $('user-line');
  const screenIntro = $('screen-intro');
  const screenGame = $('screen-game');
  const btnHome = $('btn-home');
  const btnPlayGame = $('btn-play-game');
  const boardRow = $('board-row');
  const playerRow = $('player-row');
  const handLabel = $('hand-label');
  const statsLine = $('stats-line');
  const statsDetails = $('stats-details');
  const initData = tg ? tg.initData : '';
  const initDataUnsafe = tg ? tg.initDataUnsafe : {};

  const stats = {
    total: 0,
    byHand: {},
  };
  const handOrder = [
    'Стрит‑флеш',
    'Каре',
    'Фул‑хаус',
    'Флеш',
    'Стрит',
    'Сет',
    'Две пары',
    'Пара',
    'Старшая карта',
  ];

  async function loadProfile() {
    try {
      const resp = await fetch('/api/me', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData })
      });
      if (!resp.ok) throw new Error('auth failed');
      const data = await resp.json();
      userLine.textContent = `Вы вошли как ${data.display_name} • Баланс: ${data.balance}`;
    } catch (e) {
      userLine.textContent = 'Не удалось загрузить профиль';
    }
  }

  function renderHand(data) {
    boardRow.innerHTML = '';
    playerRow.innerHTML = '';
    const board = data.board || [];
    const cards = data.player_cards || [];
    const hand = data.hand_name || 'Комбинация';

    function makeCardEl(code) {
      const el = document.createElement('div');
      el.className = 'card-chip';
      if (!code) return el;
      const rank = code[0] || '';
      const suit = code[1] || '';
      const rankEl = document.createElement('div');
      rankEl.className = 'card-rank';
      rankEl.textContent = rank;
      const suitEl = document.createElement('div');
      suitEl.className = 'card-suit';
      let suitSymbol = suit;
      if (suit === 'h') suitSymbol = '♥';
      else if (suit === 'd') suitSymbol = '♦';
      else if (suit === 'c') suitSymbol = '♣';
      else if (suit === 's') suitSymbol = '♠';
      suitEl.textContent = suitSymbol;
      if (suit === 'h' || suit === 'd') {
        rankEl.classList.add('card-red');
        suitEl.classList.add('card-red');
      }
      el.appendChild(rankEl);
      el.appendChild(suitEl);
      return el;
    }

    board.forEach((c) => {
      boardRow.appendChild(makeCardEl(c));
    });
    cards.forEach((c) => {
      playerRow.appendChild(makeCardEl(c));
    });
    // Подсветка выигрышных рук (пара и выше)
    const isStrong = hand !== 'Старшая карта';
    if (isStrong) {
      boardRow.querySelectorAll('.card-chip').forEach((el) => el.classList.add('card-win'));
      playerRow.querySelectorAll('.card-chip').forEach((el) => el.classList.add('card-win'));
    }
    handLabel.textContent = hand;

    // обновляем статистику
    stats.total += 1;
    stats.byHand[hand] = (stats.byHand[hand] || 0) + 1;

    if (statsLine) {
      statsLine.textContent = `Раздач сыграно: ${stats.total}`;
    }
    if (statsDetails) {
      const lines = [];
      handOrder.forEach((name) => {
        const n = stats.byHand[name] || 0;
        if (n > 0) {
          const pct = ((n / stats.total) * 100).toFixed(1);
          lines.push(`${name}: ${n} (${pct}%)`);
        }
      });
      statsDetails.textContent = lines.join(' • ');
    }
  }

  async function onPlay() {
    if (tg) tg.HapticFeedback.impactOccurred('heavy');
    // первый переход: плавно показываем экран игры
    if (screenIntro && screenGame && !screenGame.classList.contains('screen--active')) {
      screenIntro.classList.remove('screen--active');
      screenIntro.classList.add('screen--hidden');
      screenGame.classList.remove('screen--hidden');
      screenGame.classList.add('screen--active');
    }
    try {
      const resp = await fetch('/api/holdem/start', { method: 'POST' });
      if (!resp.ok) throw new Error('bad status');
      const data = await resp.json();
      renderHand(data);
    } catch (e) {
      if (handLabel) handLabel.textContent = 'Ошибка раздачи руки';
    }
  }
  function onDeposit() {
    alert('Пополнение: будет реализовано позже.');
  }
  function onWithdraw() {
    alert('Вывод: будет реализовано позже.');
  }
  async function onTop() {
    try {
      const resp = await fetch('/api/top');
      const data = await resp.json();
      const lines = data.top.map((t, i) => `${i+1}. ${t[0]}: ${t[1]}`).join('\n');
      alert('Топ игроков:\n' + (lines || 'Нет данных'));
    } catch (e) { alert('Ошибка загрузки топа'); }
  }
  function onInvite() {
    if (tg && initDataUnsafe && initDataUnsafe.user) {
      const text = 'Залетай играть в покер!';
      const url = tg.initDataUnsafe?.start_param ? `https://t.me/${tg.platform}?start=${tg.initDataUnsafe.start_param}` : '';
      tg.shareURL ? tg.shareURL(url || 'https://t.me') : alert(text);
    } else {
      alert('Поделитесь ботом с друзьями!');
    }
  }

  $('btn-play').addEventListener('click', onPlay);
  if (btnPlayGame) {
    btnPlayGame.addEventListener('click', onPlay);
  }
  $('btn-deposit').addEventListener('click', onDeposit);
  $('btn-withdraw').addEventListener('click', onWithdraw);
  $('btn-invite').addEventListener('click', onInvite);
  $('btn-top').addEventListener('click', onTop);
  if (btnHome) {
    btnHome.addEventListener('click', () => {
      if (screenIntro && screenGame) {
        screenGame.classList.remove('screen--active');
        screenGame.classList.add('screen--hidden');
        screenIntro.classList.remove('screen--hidden');
        screenIntro.classList.add('screen--active');
      }
    });
  }

  loadProfile();
})();
