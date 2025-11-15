(function(){
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    tg.expand();
    tg.enableClosingConfirmation();
    tg.MainButton.setParams({ text: 'Играть', is_visible: false });
  }

  const $ = (id) => document.getElementById(id);

  const userLine = $('user-line');
  const initData = tg ? tg.initData : '';
  const initDataUnsafe = tg ? tg.initDataUnsafe : {};

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

  function onPlay() {
    if (tg) tg.HapticFeedback.impactOccurred('heavy');
    alert('Игра будет добавлена позже.');
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
  $('btn-deposit').addEventListener('click', onDeposit);
  $('btn-withdraw').addEventListener('click', onWithdraw);
  $('btn-invite').addEventListener('click', onInvite);
  $('btn-top').addEventListener('click', onTop);

  loadProfile();
})();
