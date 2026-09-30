const state = {
  papers: [],
  categories: [],
  categorySetId: null,
  classifications: [],
};

const $ = (selector) => document.querySelector(selector);

// /classify/categories と /categories の categories は
// { "category_id": { name, description }, ... } という辞書形式。
// 画面では配列として扱えるように変換する。
function normalizeCategories(categories) {
  if (Array.isArray(categories)) {
    return categories;
  }

  if (categories && typeof categories === "object") {
    return Object.entries(categories).map(([id, value]) => ({
      id,
      name: value?.name ?? id,
      description: value?.description ?? "",
    }));
  }

  return [];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
    } catch (_) {}
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

function showMessage(message, error = false) {
  const element = $("#message");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.classList.remove("hidden");
}

function clearMessage() {
  $("#message").classList.add("hidden");
}

function renderPapers(latestPaperId = null) {
  const container = $("#papers");
  $("#paper-count").textContent = `${state.papers.length} papers`;

  if (!state.papers.length) {
    container.innerHTML = '<div class="empty">論文がありません。</div>';
    return;
  }

  container.innerHTML = state.papers.map((paper) => `
    <article class="paper ${paper.id === latestPaperId ? "latest" : ""}"
             data-paper-id="${paper.id}">
      <h2 class="paper-title">
        <a href="${escapeHtml(paper.url)}" target="_blank" rel="noopener noreferrer">
          ${escapeHtml(paper.title)}
        </a>
      </h2>
      <div class="paper-meta">
        arXiv: ${escapeHtml(paper.arxiv_id)}
      </div>
      <p class="abstract">${escapeHtml(paper.abstract)}</p>
    </article>
  `).join("");

  if (latestPaperId !== null) {
    const latest = container.querySelector(`[data-paper-id="${latestPaperId}"]`);
    latest?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function renderCategories() {
  const container = $("#category-list");

  if (!state.categories.length) {
    container.innerHTML = '<div class="muted">まだカテゴリがありません。</div>';
    $("#jev-button").disabled = true;
    $("#category-set-id").textContent = "";
    return;
  }

  $("#category-set-id").textContent = `ID: ${state.categorySetId ?? "-"}`;
  $("#jev-button").disabled = state.papers.length === 0 || state.categorySetId === null;

  container.innerHTML = state.categories.map((category) => `
    <div class="category">
      <div class="category-name">${escapeHtml(category.name)}</div>
      <div class="category-description">${escapeHtml(category.description)}</div>
    </div>
  `).join("");
}

function renderClassificationResults() {
  const section = $("#classification-results");
  const container = $("#result-list");

  if (!state.classifications.length) {
    section.classList.add("hidden");
    container.innerHTML = "";
    return;
  }

  section.classList.remove("hidden");

  container.innerHTML = state.classifications.map((result) => {
    const probabilities = result.probabilities &&
      typeof result.probabilities === "object"
      ? Object.entries(result.probabilities)
          .map(([name, value]) => `${escapeHtml(name)}: ${escapeHtml(value)}`)
          .join(" / ")
      : "";

    return `
      <div class="result-item">
        <div class="result-title">${escapeHtml(result.title)}</div>
        <div class="result-meta">
          ${escapeHtml(result.category)}
          · confidence: ${escapeHtml(result.confidence)}
          · model: ${escapeHtml(result.model)}
        </div>
        ${probabilities
          ? `<div class="result-probabilities">${probabilities}</div>`
          : ""}
      </div>
    `;
  }).join("");
}

async function loadPapers() {
  state.papers = await api("/papers");
  renderPapers();
}

async function loadCategories() {
  const rows = await api("/categories");

  if (!rows.length) {
    state.categories = [];
    state.categorySetId = null;
  } else {
    const latest = rows[0];
    state.categorySetId = latest.id;
    state.categories = normalizeCategories(latest.categories);
  }

  renderCategories();
}

$("#paper-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();

  const input = $("#paper-url");
  const button = $("#paper-add-button");
  const url = input.value.trim();

  if (!url) return;

  button.disabled = true;
  button.textContent = "追加中...";

  try {
    const result = await api("/papers/import", {
      method: "POST",
      body: JSON.stringify({ url }),
    });

    input.value = "";

    // /papers/import の戻り値は
    // { id, created, paper }。
    // 一覧の完全な情報は /papers から取得する。
    await loadPapers();
    renderPapers(result.id);

    showMessage(
      result.created
        ? `「${result.paper}」を登録しました。`
        : `「${result.paper}」は既に登録されています。`
    );
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "追加";
  }
});

$("#category-button").addEventListener("click", async (event) => {
  clearMessage();

  if (!state.papers.length) {
    showMessage("先に論文を登録してください。", true);
    return;
  }

  const button = event.currentTarget;
  const prompt = $("#category-prompt").value.trim();

  button.disabled = true;
  button.textContent = "生成中...";

  try {
    const result = await api("/classify/categories", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });

    state.categorySetId = result.category_set_id;
    state.categories = normalizeCategories(result.categories);
    state.classifications = [];

    renderCategories();
    renderClassificationResults();
    showMessage(`カテゴリを ${state.categories.length} 件生成しました。`);
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "カテゴリを生成";
  }
});

$("#jev-button").addEventListener("click", async (event) => {
  clearMessage();

  if (state.categorySetId === null) {
    showMessage("先にカテゴリを生成してください。", true);
    return;
  }

  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "分類中...";

  try {
    const result = await api("/classify/jev", {
      method: "POST",
      body: JSON.stringify({
        category_set_id: state.categorySetId,
      }),
    });

    state.classifications = result.results || [];
    renderClassificationResults();
    showMessage(`${state.classifications.length} 件の論文をJevで分類しました。`);
  } catch (error) {
    showMessage(error.message, true);
    renderClassificationResults();
    renderCategories();
  } finally {
    button.disabled = false;
    button.textContent = "Jevで分類";
  }
});

$("#refresh-button").addEventListener("click", async () => {
  clearMessage();

  try {
    await loadPapers();
    await loadCategories();
    // app.py には分類結果取得APIがないため、
    // refreshではJev分類結果を再取得しない。
    showMessage("更新しました。");
  } catch (error) {
    showMessage(error.message, true);
  }
});

(async function init() {
  try {
    await loadPapers();
    await loadCategories();
  } catch (error) {
    showMessage(error.message, true);
  }
})();
