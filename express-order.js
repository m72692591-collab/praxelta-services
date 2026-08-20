(() => {
  "use strict";

  const form = document.querySelector("#express-order-form");
  const preview = document.querySelector("#express-order-preview");
  const previewText = document.querySelector("#express-order-preview-text");
  const status = document.querySelector("#express-order-status");
  const copyButton = document.querySelector("#copy-express-order");
  const clearButton = document.querySelector("#clear-express-order");
  const gmailLink = document.querySelector("#open-express-gmail");
  const mailLink = document.querySelector("#open-express-mail");
  const recipient = "m72692591@gmail.com";
  let preparedText = "";

  const normalize = (value) => value.replace(/\r\n?/g, "\n").trim();

  const randomHex = (bytes = 4) => {
    const values = new Uint8Array(bytes);
    window.crypto.getRandomValues(values);
    return Array.from(values, (value) => value.toString(16).padStart(2, "0")).join("");
  };

  const dateStamp = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}${month}${day}`;
  };

  const requestId = () => `PRX-EX-${dateStamp()}-${randomHex(4).toUpperCase()}`;

  const gmailUrl = (subject, body) => {
    const params = new URLSearchParams({
      view: "cm",
      fs: "1",
      to: recipient,
      su: subject,
      body
    });
    return `https://mail.google.com/mail/?${params.toString()}`;
  };

  const buildPayload = (data, id) => {
    const subject = `ПРАКСЕЛЬТА — запрос Экспресс — ${id}`;
    const lines = [
      `Идентификатор запроса: ${id}`,
      "Продукт: Управляемое продвижение и учёт обращений",
      "Оффер: Экспресс — 7 900 ₽ — 7 дней",
      "",
      `Имя / организация: ${normalize(data.get("customer_name") || "")}`,
      `Регион: ${normalize(data.get("region") || "")}`,
      `Сфера: ${normalize(data.get("business_type") || "")}`,
      `Основной канал: ${normalize(data.get("primary_channel") || "")}`,
      "",
      "Проблема:",
      normalize(data.get("problem") || ""),
      "",
      "Ссылки для разбора:",
      normalize(data.get("links") || "Не указаны"),
      "",
      "Проверяемый результат через 7 дней:",
      normalize(data.get("expected_result") || ""),
      "",
      "Ограничения:",
      normalize(data.get("restrictions") || "Не указаны"),
      "",
      "Доступные данные:",
      normalize(data.get("available_data") || "Не указаны"),
      "",
      "Подтверждения:",
      "- гарантии лидов, продаж, дохода и позиции отсутствуют;",
      "- пароли, банковские данные и клиентская база не передаются;",
      "- договор возникает только после отдельного письменного заказа;",
      "- ответ разрешён только по этой задаче, без рекламной рассылки."
    ];
    return { subject, body: lines.join("\n") };
  };

  const clearPreparedState = () => {
    preparedText = "";
    preview.hidden = true;
    previewText.textContent = "";
    gmailLink.href = "#";
    mailLink.href = "#";
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearPreparedState();
    status.textContent = "";

    if (!form.reportValidity()) {
      status.textContent = "Проверьте обязательные поля и подтверждения.";
      return;
    }

    const payload = buildPayload(new FormData(form), requestId());
    preparedText = `Кому: ${recipient}\nТема: ${payload.subject}\n\n${payload.body}`;
    previewText.textContent = preparedText;
    gmailLink.href = gmailUrl(payload.subject, payload.body);
    mailLink.href = `mailto:${recipient}?${new URLSearchParams({
      subject: payload.subject,
      body: payload.body
    }).toString()}`;
    preview.hidden = false;
    status.textContent = "Письмо подготовлено локально. Оно ещё не отправлено.";
    preview.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  copyButton.addEventListener("click", async () => {
    if (!preparedText) {
      status.textContent = "Сначала сформируйте письмо.";
      return;
    }
    try {
      await navigator.clipboard.writeText(preparedText);
      status.textContent = "Запрос скопирован.";
    } catch {
      previewText.focus();
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(previewText);
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = "Текст выделен. Скопируйте его сочетанием клавиш.";
    }
  });

  clearButton.addEventListener("click", () => {
    form.reset();
    clearPreparedState();
    status.textContent = "Поля и локальный предпросмотр очищены.";
    form.querySelector("input, select, textarea")?.focus();
  });
})();
