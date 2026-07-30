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
    'a[href^="mailto:m72692591@gmail.com"][href*="body="]'
  );
  let returnFocus = null;

  const gmailUrl = (subject, body) => {
    const params = new URLSearchParams({
      view: "cm",
      fs: "1",
      to: "m72692591@gmail.com",
      su: subject,
      body
    });
    return `https://mail.google.com/mail/?${params.toString()}`;
  };

  const showOrder = (link) => {
    const mailto = new URL(link.href);
    const subject = mailto.searchParams.get("subject") || "Заказ ПОТОК";
    const body = mailto.searchParams.get("body") || "";

    returnFocus = link;
    subjectField.value = subject;
    bodyField.value = body;
    openGmail.href = gmailUrl(subject, body);
    openMailApp.href = link.href;
    status.textContent = "";
    dialog.showModal();
    copyButton.focus();
  };

  const copyOrder = async () => {
    const text = `Кому: m72692591@gmail.com\nТема: ${subjectField.value}\n\n${bodyField.value}`;
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = "Запрос скопирован. Вставьте его в удобную почту и заполните пустые строки.";
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
  closeButton.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    if (returnFocus) returnFocus.focus();
  });
})();

