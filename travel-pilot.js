"use strict";

(() => {
  const CONTACT_EMAIL = "animatactus087@gmail.com";
  const REQUEST_CODE = "PRAXELTA_TRAVEL_PILOT_V1";
  const byId = (id) => document.getElementById(id);

  const localIsoDate = (offsetDays) => {
    const value = new Date();
    value.setHours(12, 0, 0, 0);
    value.setDate(value.getDate() + offsetDays);
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const normalizeText = (value, maxLength) =>
    String(value || "")
      .replace(/[\u0000-\u001f\u007f]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, maxLength);

  const appendText = (parent, tag, text, className = "") => {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  };

  const values = () => ({
    departure: normalizeText(byId("pilot-departure").value, 80),
    type: normalizeText(byId("pilot-type").value, 80),
    start: byId("pilot-start").value,
    end: byId("pilot-end").value,
    flexibility: Number(byId("pilot-flexibility").value),
    budget: Number(byId("pilot-budget").value),
    adults: Number(byId("pilot-adults").value),
    children: Number(byId("pilot-children").value),
    documents: normalizeText(byId("pilot-documents").value, 100),
    priority: normalizeText(byId("pilot-priority").value, 100),
    note: normalizeText(byId("pilot-note").value, 300)
  });

  const validate = (data) => {
    if (!data.departure) return "Укажите город отправления.";
    if (!data.start || !data.end) return "Укажите начало и окончание периода.";
    if (data.end < data.start) return "Окончание периода должно быть не раньше начала.";
    if (!Number.isInteger(data.flexibility) || data.flexibility < 0 || data.flexibility > 14) {
      return "Допустимый сдвиг — от 0 до 14 дней.";
    }
    if (!Number.isFinite(data.budget) || data.budget < 10000 || data.budget > 20000000) {
      return "Укажите общий бюджет от 10 000 до 20 000 000 ₽.";
    }
    if (!Number.isInteger(data.adults) || data.adults < 1 || data.adults > 10) {
      return "Количество взрослых — от 1 до 10.";
    }
    if (!Number.isInteger(data.children) || data.children < 0 || data.children > 10) {
      return "Количество детей — от 0 до 10.";
    }
    return "";
  };

  const formatMoney = (value) => `${value.toLocaleString("ru-RU")} ₽`;

  const buildBody = (data) => [
    `Код запроса: ${REQUEST_CODE}`,
    "",
    "Хочу принять участие в закрытом пилоте информационного подбора поездки.",
    "",
    `Город отправления: ${data.departure}`,
    `Период: ${data.start} — ${data.end}`,
    `Допустимый сдвиг: ${data.flexibility} дн.`,
    `Состав: взрослых ${data.adults}, детей ${data.children}`,
    `Максимальный общий бюджет: ${formatMoney(data.budget)}`,
    `Документы: ${data.documents}`,
    `Вид отдыха: ${data.type}`,
    `Главный приоритет: ${data.priority}`,
    `Дополнительное пожелание: ${data.note || "нет"}`,
    "",
    "Я понимаю, что это запрос на информационный подбор, а не бронирование. Окончательную цену, состав услуги, договор и возврат определяет продавец.",
    "",
    "Не отправляю паспортные, банковские, медицинские данные, адрес или сканы документов."
  ].join("\n");

  const render = (body) => {
    const preview = byId("travel-pilot-preview");
    preview.replaceChildren();
    appendText(preview, "h3", "Письмо сформировано");
    appendText(
      preview,
      "p",
      "Проверьте текст. При нажатии откроется ваше почтовое приложение; до самостоятельной отправки данные никуда не уйдут.",
      "travel-pilot-note"
    );
    appendText(preview, "pre", body);

    const link = document.createElement("a");
    link.className = "button primary travel-pilot-mail";
    link.textContent = "Открыть письмо";
    link.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("Закрытый пилот подбора поездки")}&body=${encodeURIComponent(body)}`;
    preview.appendChild(link);
    appendText(
      preview,
      "small",
      `Получатель: ${CONTACT_EMAIL}. Вы можете изменить или закрыть письмо без отправки.`,
      "travel-pilot-note"
    );
    preview.focus();
  };

  let currentBody = "";

  const create = () => {
    const error = byId("travel-pilot-error");
    error.textContent = "";
    const data = values();
    const problem = validate(data);
    if (problem) {
      error.textContent = problem;
      currentBody = "";
      byId("travel-pilot-copy").disabled = true;
      return;
    }
    currentBody = buildBody(data);
    byId("travel-pilot-copy").disabled = false;
    render(currentBody);
  };

  const copy = async () => {
    const error = byId("travel-pilot-error");
    error.textContent = "";
    if (!currentBody) {
      error.textContent = "Сначала создайте письмо.";
      return;
    }
    try {
      await navigator.clipboard.writeText(currentBody);
      error.textContent = "Текст скопирован.";
    } catch {
      error.textContent = "Браузер не дал доступ к буферу. Выделите текст в блоке справа вручную.";
    }
  };

  const start = byId("pilot-start");
  const end = byId("pilot-end");
  if (start && !start.value) start.value = localIsoDate(30);
  if (end && !end.value) end.value = localIsoDate(40);

  const createButton = byId("travel-pilot-create");
  const copyButton = byId("travel-pilot-copy");
  if (createButton) createButton.addEventListener("click", create);
  if (copyButton) copyButton.addEventListener("click", copy);
})();
