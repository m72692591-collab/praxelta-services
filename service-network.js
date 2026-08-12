"use strict";

(() => {
  const form = document.querySelector("#service-request-form");
  if (!form) return;
  const warning = document.querySelector("#emergency-warning");
  const status = document.querySelector("#form-status");
  const preview = document.querySelector("#request-preview");
  const previewText = document.querySelector("#request-preview-text");
  const clearButton = document.querySelector("#clear-preview");
  const emergencyTerms = ["запах газа", "пахнет газом", "хлопок", "пожар", "открытое пламя", "сигнализатор", "отравление", "задыха"];

  function hasEmergency(value) {
    const normalized = value.toLocaleLowerCase("ru");
    return emergencyTerms.some((term) => normalized.includes(term));
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    status.textContent = "";
    preview.hidden = true;
    const data = new FormData(form);
    const problem = String(data.get("problem") || "");
    if (hasEmergency(problem)) {
      warning.hidden = false;
      warning.focus();
      status.textContent = "Заявка не сформирована: сработала проверка аварийных признаков.";
      return;
    }
    warning.hidden = true;
    if (!form.checkValidity()) {
      form.reportValidity();
      status.textContent = "Проверьте обязательные поля и оба согласия.";
      return;
    }
    const shareLabels = {
      one: "одному мастеру",
      sequential: "последовательно одному мастеру",
      three: "не более трём мастерам",
      choice: "никому до выбора клиента",
    };
    const safePreview = [
      `Город: ${data.get("city")}`,
      `Район: ${data.get("district")}`,
      `Категория: ${data.get("category")}`,
      `Оборудование: ${data.get("equipment") || "не указано"}`,
      `Проблема: ${problem}`,
      `Срочность: ${data.get("urgency")}`,
      `Передача: ${shareLabels[String(data.get("share_mode"))]}`,
      "Контакт: указан, но скрыт в предпросмотре",
      "Статус: НЕ ОТПРАВЛЕНО",
    ];
    previewText.textContent = safePreview.join("\n");
    preview.hidden = false;
    status.textContent = "Готов локальный предпросмотр. Сеть не использовалась, данные не сохранены.";
    preview.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  clearButton?.addEventListener("click", () => {
    form.reset();
    previewText.textContent = "";
    preview.hidden = true;
    warning.hidden = true;
    status.textContent = "Экран очищен.";
    form.querySelector("input, select, textarea")?.focus();
  });
})();
