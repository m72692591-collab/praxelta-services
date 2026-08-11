(() => {
  const dialog = document.querySelector("#order-dialog");
  const subjectField = document.querySelector("#order-subject");
  const bodyField = document.querySelector("#order-body");
  const copyButton = document.querySelector("#copy-order");
  const status = document.querySelector("#dialog-status");
  const openGmail = document.querySelector("#open-gmail");
  const openMailApp = document.querySelector("#open-mail-app");
  const closeButton = document.querySelector(".dialog-close");
  const orderLinks = document.querySelectorAll(
    'a[href^="mailto:"][href*="body="]'
  );
  const allowedSources = new Set([
    "telegram_partner",
    "max_partner",
    "email_partner",
    "telegram_marketplace",
    "max_marketplace",
    "email_marketplace"
  ]);
  const requestedSource = new URLSearchParams(window.location.search).get("ref");
  const sourceCode = allowedSources.has(requestedSource) ? requestedSource : "";
  let returnFocus = null;

  let recipient = "";

  const gmailUrl = (to, subject, body) => {
    const params = new URLSearchParams({
      view: "cm",
      fs: "1",
      to,
      su: subject,
      body
    });
    return `https://mail.google.com/mail/?${params.toString()}`;
  };

  const updateDestinations = () => {
    const subject = subjectField.value;
    const body = bodyField.value;
    openGmail.href = gmailUrl(recipient, subject, body);
    openMailApp.href = `mailto:${recipient}?${new URLSearchParams({
      subject,
      body
    }).toString()}`;
  };

  const showOrder = (link) => {
    const mailto = new URL(link.href);
    recipient = mailto.pathname;
    const subject = mailto.searchParams.get("subject") || "Запрос ПРОКСЕЛЬТА";
    const baseBody = mailto.searchParams.get("body") || "";
    const body = sourceCode ? `${baseBody}\nИсточник: ${sourceCode}` : baseBody;

    returnFocus = link;
    subjectField.value = subject;
    bodyField.value = body;
    updateDestinations();
    status.textContent = "";
    dialog.showModal();
    bodyField.focus();
  };

  const copyOrder = async () => {
    const text = `Кому: ${recipient}\nТема: ${subjectField.value}\n\n${bodyField.value}`;
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = "Заполненный запрос скопирован. Его можно вставить в любую почту.";
    } catch {
      bodyField.focus();
      bodyField.select();
      const copied = document.execCommand("copy");
      status.textContent = copied
        ? "Текст запроса скопирован. Тему и адрес можно взять выше."
        : "Выделите текст запроса и скопируйте его вручную.";
    }
  };

  orderLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showOrder(link);
    });
  });

  copyButton.addEventListener("click", copyOrder);
  bodyField.addEventListener("input", updateDestinations);
  closeButton.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    if (returnFocus) returnFocus.focus();
  });
})();
