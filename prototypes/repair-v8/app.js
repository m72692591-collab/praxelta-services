(() => {
  'use strict';
  const views = [...document.querySelectorAll('[data-view]')];
  const tabs = [...document.querySelectorAll('[data-tab]')];
  const device = document.querySelector('.device');
  const content = document.getElementById('app-content');
  const live = document.getElementById('live-region');
  const statePanel = document.getElementById('state-panel');
  const stateSelect = document.getElementById('demo-state');
  const statePreview = document.getElementById('state-preview');
  const systemStates = Object.freeze({
    loading: ['Проверяем состояние', 'Дождитесь ответа backend. Критичные данные не скрываются анимацией.'],
    empty: ['Пока ничего нет', 'Создайте первую заявку или вернитесь позже.'],
    error: ['Не удалось получить данные', 'Повторите безопасную проверку. Деньги и статусы не изменены.'],
    blocked: ['Действие заблокировано', 'Причина указана рядом. Обход блокировки недоступен.'],
    offline: ['Нет соединения', 'Доступно только ранее открытое демо. Платёжные действия выключены.'],
    stale: ['Данные устарели', 'Обновите backend-состояние перед решением.'],
    partial: ['Подтверждена только часть', 'Неподтверждённые суммы не считаются оплаченными.'],
    refund: ['Возврат обрабатывается', 'Показываем каждую сторнируемую денежную ногу отдельно.'],
    dispute: ['Спор открыт', 'История сметы сохранена; связанная выплата приостановлена.'],
  });
  const formatKopecks = (value) => `${new Intl.NumberFormat('ru-RU').format(Math.trunc(value / 100))} ₽`;
  document.querySelectorAll('[data-kopecks-min]').forEach((node) => { node.textContent = `${formatKopecks(Number(node.dataset.kopecksMin))}–${formatKopecks(Number(node.dataset.kopecksMax))}`; });
  function go(name) {
    if (!views.some((view) => view.dataset.view === name)) return;
    views.forEach((view) => { const active = view.dataset.view === name; view.classList.toggle('active', active); view.toggleAttribute('inert', !active); view.setAttribute('aria-hidden', String(!active)); });
    tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
    device.dataset.screen = name; history.replaceState(null, '', `#${name}`); content.scrollTop = 0; content.focus({ preventScroll: true });
    live.textContent = `Открыт экран: ${views.find((view) => view.dataset.view === name).querySelector('h2').textContent}`;
  }
  function showState(name) { const state = systemStates[name]; statePreview.dataset.state = name; statePreview.innerHTML = `<strong>${state[0]}</strong><p>${state[1]}</p>`; }
  document.addEventListener('click', (event) => {
    const navigation = event.target.closest('[data-go],[data-tab]'); if (navigation) go(navigation.dataset.go || navigation.dataset.tab);
    if (event.target.closest('[data-open-state-panel]')) { showState(stateSelect.value); statePanel.showModal(); }
    if (event.target.closest('[data-demo-decision]')) live.textContent = 'Демо-решение отмечено локально. Данные не сохранены.';
    if (event.target.closest('[data-show-dispute]')) { stateSelect.value = 'dispute'; showState('dispute'); statePanel.showModal(); }
  });
  stateSelect.addEventListener('change', () => showState(stateSelect.value));
  window.addEventListener('offline', () => { stateSelect.value = 'offline'; showState('offline'); });
  const initial = location.hash.slice(1); go(views.some((view) => view.dataset.view === initial) ? initial : 'home');
})();
