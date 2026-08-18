"use strict";

(() => {
  const offers = [
    {
      title: "Синтетический пример: семейный отдых у моря",
      destination: "Анталья",
      departure: "Саратов",
      start: "2026-09-11",
      end: "2026-09-19",
      price: 174000,
      type: "море",
      family: true,
      meals: true,
      direct: true,
      quiet: false,
      rating: 4.5
    },
    {
      title: "Синтетический пример: апарт-отель в Сочи",
      destination: "Сочи",
      departure: "Саратов",
      start: "2026-09-10",
      end: "2026-09-18",
      price: 136000,
      type: "море",
      family: true,
      meals: true,
      direct: false,
      quiet: true,
      rating: 4.3
    },
    {
      title: "Синтетический пример: выходные в Санкт-Петербурге",
      destination: "Санкт-Петербург",
      departure: "Саратов",
      start: "2026-09-12",
      end: "2026-09-17",
      price: 92000,
      type: "город",
      family: true,
      meals: true,
      direct: true,
      quiet: false,
      rating: 4.6
    },
    {
      title: "Синтетический пример: санаторий в Кисловодске",
      destination: "Кисловодск",
      departure: "Саратов",
      start: "2026-09-09",
      end: "2026-09-20",
      price: 151000,
      type: "санаторий",
      family: true,
      meals: true,
      direct: false,
      quiet: true,
      rating: 4.4
    },
    {
      title: "Синтетический пример: поездка в Дагестан",
      destination: "Дагестан",
      departure: "Москва",
      start: "2026-09-11",
      end: "2026-09-18",
      price: 119000,
      type: "природа",
      family: true,
      meals: true,
      direct: true,
      quiet: false,
      rating: 4.7
    },
    {
      title: "Синтетический пример: Калининград и область",
      destination: "Калининград",
      departure: "Саратов",
      start: "2026-09-14",
      end: "2026-09-20",
      price: 108000,
      type: "экскурсии",
      family: true,
      meals: true,
      direct: false,
      quiet: true,
      rating: 4.5
    }
  ];

  const byId = (id) => document.getElementById(id);

  const dateDistance = (queryStart, queryEnd, offerStart, offerEnd) => {
    const day = 86400000;
    const qStart = new Date(`${queryStart}T00:00:00Z`).getTime();
    const qEnd = new Date(`${queryEnd}T00:00:00Z`).getTime();
    const oStart = new Date(`${offerStart}T00:00:00Z`).getTime();
    const oEnd = new Date(`${offerEnd}T00:00:00Z`).getTime();
    if (oEnd < qStart) return Math.round((qStart - oEnd) / day);
    if (oStart > qEnd) return Math.round((oStart - qEnd) / day);
    return 0;
  };

  const scoreOffer = (offer, query) => {
    let score = 0;
    const reasons = [];
    const ratio = offer.price / Math.max(query.budget, 1);

    if (ratio <= 1) {
      score += 45 - 15 * ratio;
      reasons.push("укладывается в бюджет");
    } else if (ratio <= 1.1) {
      score += 3;
      reasons.push("немного выше бюджета");
    } else {
      score -= Math.min(60, (ratio - 1) * 100);
    }

    if (offer.departure === query.departure) {
      score += 15;
      reasons.push("нужный город отправления");
    } else {
      score -= 8;
    }

    const distance = dateDistance(query.start, query.end, offer.start, offer.end);
    if (distance === 0) {
      score += 12;
      reasons.push("подходит по датам");
    } else if (distance <= query.flexibility) {
      score += 7;
      reasons.push("попадает в допустимый сдвиг");
    } else {
      score -= Math.min(20, distance);
    }

    if (query.children > 0 && offer.family) {
      score += 8;
      reasons.push("подходит для поездки с детьми");
    }
    if (offer.type === query.type) {
      score += 7;
      reasons.push("совпадает тип отдыха");
    }
    if (query.priority === "питание" && offer.meals) {
      score += 5;
      reasons.push("питание указано");
    }
    if (query.priority === "прямой маршрут" && offer.direct) {
      score += 7;
      reasons.push("прямой маршрут");
    }
    if (query.priority === "тишина" && offer.quiet) {
      score += 5;
      reasons.push("тихий формат");
    }
    if (query.priority === "рейтинг") {
      score += Math.max(0, offer.rating - 3) * 3;
      reasons.push(`рейтинг ${offer.rating.toFixed(1)}`);
    }

    return { offer, score, reasons: reasons.slice(0, 5) };
  };

  const appendText = (parent, tag, text, className = "") => {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  };

  const render = (ranked) => {
    const results = byId("travel-demo-results");
    results.replaceChildren();
    appendText(results, "h3", "Демонстрационный подбор готов");
    appendText(
      results,
      "p",
      "Это синтетические примеры для проверки логики интерфейса. Они не являются предложениями, рекламой или бронированием.",
      "travel-demo-warning"
    );

    ranked.forEach((item, index) => {
      const card = document.createElement("article");
      card.className = "travel-demo-result";
      appendText(card, "span", `Вариант ${index + 1}`, "travel-demo-kicker");
      appendText(card, "h3", item.offer.title);
      appendText(
        card,
        "p",
        `${item.offer.departure} → ${item.offer.destination}, ${item.offer.start} — ${item.offer.end}.`
      );
      appendText(card, "strong", `${item.offer.price.toLocaleString("ru-RU")} ₽`);
      appendText(card, "p", `Почему: ${item.reasons.join("; ") || "соответствует части параметров"}.`);
      appendText(card, "small", "Ссылка закрыта production-gate. Данные никуда не отправлялись.");
      results.appendChild(card);
    });
    results.focus();
  };

  const run = () => {
    const query = {
      departure: byId("travel-departure").value,
      start: byId("travel-start").value,
      end: byId("travel-end").value,
      flexibility: Number(byId("travel-flexibility").value),
      adults: Number(byId("travel-adults").value),
      children: Number(byId("travel-children").value),
      budget: Number(byId("travel-budget").value),
      documents: byId("travel-documents").value,
      type: byId("travel-type").value,
      priority: byId("travel-priority").value
    };

    const error = byId("travel-demo-error");
    error.textContent = "";
    if (!query.start || !query.end || query.end < query.start) {
      error.textContent = "Проверьте даты: окончание должно быть не раньше начала.";
      return;
    }
    if (!Number.isFinite(query.budget) || query.budget < 10000) {
      error.textContent = "Укажите общий бюджет не менее 10 000 ₽.";
      return;
    }
    if (query.adults < 1 || query.children < 0) {
      error.textContent = "Проверьте количество путешественников.";
      return;
    }

    const ranked = offers
      .map((offer) => scoreOffer(offer, query))
      .sort((left, right) => right.score - left.score || left.offer.price - right.offer.price)
      .slice(0, 3);
    render(ranked);
  };

  const button = byId("travel-demo-run");
  if (button) button.addEventListener("click", run);
})();
