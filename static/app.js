const SOURCE_HINTS = {
  maxroll: "Maxroll 官方攻略團隊 D4 BD 指南，依最新更新排序取前 10（v1 live）",
  mobalytics: "Mobalytics Diablo 4 熱門 BD（TRENDING），取前 10（v1 live）",
  d2core: "暗黑核 d2core.com／api 需 ACCESS_TOKEN；無 token 時此來源為空，見 IMPL",
};

const state = {
  data: null,
  buildsSource: "maxroll",
  hotLang: "zh", newLang: "zh", tweetsLang: "zh",
  activeTab: "builds",
};
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function fmtViews(n) {
  if (typeof n !== "number") return "";
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, "") + " 萬觀看";
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "K 觀看";
  return n + " 觀看";
}

const EXT_ICON = '<svg class="ext-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14L21 3"/></svg>';

function buildCard(b) {
  const tags = (b.tags || []).slice(0, 4)
    .map((t) => `<span class="tag">${esc(t)}</span>`).join("");
  const sub = [
    b.author ? `👤 ${esc(b.author)}` : "",
    b.updated ? `🕒 ${esc(b.updated)}` : "",
    b.patch ? `⭐ ${esc(b.patch)}` : "",
  ].filter(Boolean).join("");
  return `<article class="build-card">
    <span class="rank-badge">${b.rank}</span>
    <div class="build-main">
      <h4><a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">${esc(b.title)}</a></h4>
      ${sub ? `<div class="thread-sub">${sub}</div>` : ""}
      ${tags ? `<div class="card-foot">${tags}</div>` : ""}
    </div>
  </article>`;
}

function videoCard(v, rank) {
  const vid = esc(v.video_id);
  return `<article class="video-card">
    <a class="thumb-link" href="${esc(v.url)}" target="_blank" rel="noopener noreferrer">
      <img class="thumb" src="https://i.ytimg.com/vi/${vid}/mqdefault.jpg" alt="" loading="lazy" referrerpolicy="no-referrer">
      <span class="play-badge"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.14v14l11-7-11-7z"/></svg></span>
      ${rank != null ? `<span class="rank-badge corner">${rank}</span>` : ""}
    </a>
    <div class="video-info">
      <h4><a href="${esc(v.url)}" target="_blank" rel="noopener noreferrer">${esc(v.title)}</a></h4>
      <div class="video-meta">
        <span class="lang-flag">${v.lang === "zh" ? "中文" : v.lang === "ja" ? "日文" : "EN"}</span>
        <span>${esc(v.channel)}</span>
        ${v.views != null ? `<span>👁 ${fmtViews(v.views)}</span>` : ""}
        ${v.date ? `<span>📅 ${esc(v.date)}</span>` : ""}
      </div>
    </div>
  </article>`;
}

document.addEventListener("error", (e) => {
  const img = e.target;
  if (img.tagName === "IMG" && img.classList.contains("thumb")) img.style.visibility = "hidden";
}, true);

function renderBuilds() {
  const src = state.buildsSource;
  $("#buildHint").textContent = SOURCE_HINTS[src] || "";
  const list = state.data[`builds_${src}`] || [];
  if (!list.length) {
    $("#buildList").innerHTML = '<p class="empty-msg">此來源尚無資料（暗黑核需 token；其他來源等待下次每日掃描）。</p>';
    return;
  }
  $("#buildList").innerHTML = list.map(buildCard).join("");
}

function renderVideos() {
  const hot = state.data[`videos_hot_${state.hotLang}`] || [];
  const fresh = state.data[`videos_new_${state.newLang}`] || [];
  $("#hotGrid").innerHTML = hot.length ? hot.map((v, i) => videoCard(v, i + 1)).join("") : '<p class="empty-msg">尚無資料。</p>';
  $("#newGrid").innerHTML = fresh.length ? fresh.map((v) => videoCard(v)).join("") : '<p class="empty-msg">尚無資料。</p>';
}

function renderBahamut() {
  const items = state.data.bahamut || [];
  $("#bahaList").innerHTML = items.length ? items.map((b, i) => `
    <div class="thread-item">
      <span class="thread-num">${i + 1}</span>
      <div class="thread-body">
        <h4><a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">${esc(b.title)}</a></h4>
        <div class="thread-sub"><span>👤 ${esc(b.author) || "匿名"}</span><span>🕒 ${esc(b.time)}</span></div>
      </div>
      ${b.replies ? `<span class="reply-badge">回應 ${esc(b.replies)}</span>` : ""}
    </div>`).join("") : '<p class="empty-msg">尚無資料。</p>';
}

function renderTweets() {
  const items = state.data[`tweets_${state.tweetsLang}`] || [];
  $("#tweetList").innerHTML = items.length ? items.map((tw) => `
    <article class="tweet-item">
      <div class="tweet-head">
        <a class="tweet-author" href="https://x.com/${esc(tw.author)}" target="_blank" rel="noopener noreferrer">${esc(tw.author_name || tw.author)}</a>
        <span class="tweet-handle">@${esc(tw.author)}</span>
        ${tw.date ? `<span>📅 ${esc(tw.date)}</span>` : ""}
        ${typeof tw.likes === "number" ? `<span>❤️ ${tw.likes.toLocaleString()}</span>` : ""}
        <a class="ext-link" href="${esc(tw.url)}" target="_blank" rel="noopener noreferrer" aria-label="在 X 開啟">${EXT_ICON}</a>
      </div>
      <p class="tweet-text"><a href="${esc(tw.url)}" target="_blank" rel="noopener noreferrer">${esc(tw.text)}</a></p>
    </article>`).join("") : '<p class="empty-msg">尚無資料。</p>';
}

const STORY_SPOILER = {
  main: "本章回小說體長稿含主線關鍵劇情。未通關或不欲知曉劇情者請勿閱讀。繼續瀏覽即視為接受劇透。原創敘事改寫，非官方劇本。",
};

let storyState = { data: null, volumeId: "main" };

function renderStoryVolume(volumeId) {
  const body = $("#storyBody");
  const toc = $("#storyToc");
  const meta = $("#storyMeta");
  const bar = $("#storyVolumeBar");
  const blurb = $("#storyVolumeBlurb");
  const spoilerText = $("#storySpoilerText");
  if (!body || !storyState.data) return;

  const story = storyState.data;
  const volumes = Array.isArray(story.volumes) && story.volumes.length
    ? story.volumes
    : [{
        id: "main",
        title: "本篇",
        short_title: "本篇",
        blurb: "",
        chapters: story.chapters || [],
        chapter_count: (story.chapters || []).length,
      }];

  const vol = volumes.find((v) => v.id === volumeId) || volumes[0];
  storyState.volumeId = vol.id;
  const chapters = vol.chapters || [];

  if (bar) {
    bar.innerHTML = volumes.map((v) =>
      `<button type="button" class="story-volume-btn${v.id === vol.id ? " active" : ""}" data-volume="${esc(v.id)}" role="tab" aria-selected="${v.id === vol.id ? "true" : "false"}">${esc(v.short_title || v.title)}</button>`
    ).join("");
  }
  if (blurb) {
    if (vol.blurb) {
      blurb.hidden = false;
      blurb.textContent = vol.blurb;
    } else {
      blurb.hidden = true;
      blurb.textContent = "";
    }
  }
  if (spoilerText) {
    spoilerText.textContent = STORY_SPOILER[vol.id] || STORY_SPOILER.main;
  }

  if (!chapters.length) {
    toc.innerHTML = "";
    body.innerHTML = '<p class="empty-msg">劇情小說尚無章節。</p>';
    if (meta) meta.textContent = "尚未建置";
    return;
  }

  const totalCh = volumes.reduce((n, v) => n + (v.chapter_count || (v.chapters || []).length), 0);
  if (meta) {
    meta.textContent = volumes.length > 1
      ? `${vol.short_title || vol.title}｜${chapters.length} 章（全站 ${totalCh} 章）`
      : `${story.chapter_count || chapters.length} 章`;
  }

  toc.innerHTML = `<h3 class="story-toc-title">章回目錄</h3><ol class="story-toc-list">${
    chapters.map((c) => `<li><a href="#${esc(c.id)}">${esc(c.title)}</a></li>`).join("")
  }</ol>`;
  body.innerHTML = chapters.map((c) =>
    `<section class="story-chapter" id="${esc(c.id)}">
      <div class="story-chapter-inner">${c.html}</div>
      <a class="story-back-toc" href="#storyToc">↑ 回目錄</a>
    </section>`
  ).join("");
}

async function loadStory() {
  const body = $("#storyBody");
  const toc = $("#storyToc");
  const meta = $("#storyMeta");
  if (!body) return;
  try {
    const res = await fetch("data/story.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    storyState.data = await res.json();
    renderStoryVolume(storyState.volumeId || "main");
  } catch (err) {
    if (toc) toc.innerHTML = "";
    body.innerHTML = '<p class="empty-msg">劇情小說載入失敗，請重新整理頁面後再試。</p>';
    if (meta) meta.textContent = "載入失敗";
    console.warn("story load failed", err);
  }
}

function renderMeta() {
  const meta = state.data.meta || {};
  const map = {
    builds: ["builds_maxroll", "builds_mobalytics", "builds_d2core"],
    videos_hot: ["videos_hot_zh", "videos_hot_en", "videos_hot_ja"],
    videos_new: ["videos_new_zh", "videos_new_en", "videos_new_ja"],
    bahamut: ["bahamut"],
    tweets: ["tweets_zh", "tweets_en", "tweets_ja"],
  };
  $$("[data-meta]").forEach((el) => {
    const times = (map[el.dataset.meta] || []).map((k) => meta[k]).filter(Boolean);
    el.textContent = times.length ? `最後更新：${times.sort().reverse()[0]}` : "尚未更新";
  });
  if (meta._last_run) $("#lastRun").textContent = `上次完整掃描：${meta._last_run}`;
}

function localSearch(raw) {
  const q = raw.trim().toLowerCase();
  if (!q) return null;
  const words = q.split(/\s+/);
  const m = (item, keys) => {
    const hay = keys.map((k) => Array.isArray(item[k]) ? item[k].join(" ") : String(item[k] || "")).join(" ").toLowerCase();
    return words.every((w) => hay.includes(w));
  };
  const builds = [...(state.data.builds_d2core || []), ...(state.data.builds_mobalytics || []), ...(state.data.builds_maxroll || [])]
    .filter((b) => m(b, ["title", "author", "source", "classes", "tags", "patch"])).slice(0, 30);
  const hot = [...(state.data.videos_hot_zh || []), ...(state.data.videos_hot_en || []), ...(state.data.videos_hot_ja || [])]
    .filter((v) => m(v, ["title", "channel", "lang"])).slice(0, 20);
  const fresh = [...(state.data.videos_new_zh || []), ...(state.data.videos_new_en || []), ...(state.data.videos_new_ja || [])]
    .filter((v) => m(v, ["title", "channel", "lang"])).slice(0, 20);
  const baha = (state.data.bahamut || [])
    .filter((b) => m(b, ["title", "snippet", "author", "source"])).slice(0, 20);
  const tweets = [...(state.data.tweets_zh || []), ...(state.data.tweets_en || []), ...(state.data.tweets_ja || [])]
    .filter((t) => m(t, ["text", "author", "author_name"]))
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || ""))).slice(0, 20);
  return { builds, hot, new: fresh, bahamut: baha, tweets, total: builds.length + hot.length + fresh.length + baha.length + tweets.length };
}

async function doSearch(q) {
  q = q.trim();
  if (!q) return;
  const r = localSearch(q);
  $("#searchTitle").textContent = `「${q}」搜尋結果：共 ${r.total} 筆`;
  let html = "";
  if (r.builds.length) html += `<h3 class="group-title">Build（${r.builds.length}）</h3><div class="build-list">${r.builds.map(buildCard).join("")}</div>`;
  if (r.hot.length) html += `<h3 class="group-title">熱門影片（${r.hot.length}）</h3><div class="video-grid">${r.hot.map((v) => videoCard(v)).join("")}</div>`;
  if (r.new.length) html += `<h3 class="group-title">最新影片（${r.new.length}）</h3><div class="video-grid">${r.new.map((v) => videoCard(v)).join("")}</div>`;
  if (r.bahamut.length) html += `<h3 class="group-title">巴哈討論（${r.bahamut.length}）</h3><div class="thread-list">${r.bahamut.map((b) => `
    <div class="thread-item"><div class="thread-body">
      <h4><a href="${esc(b.url)}" target="_blank" rel="noopener noreferrer">${esc(b.title)}</a></h4>
      <div class="thread-sub"><span>👤 ${esc(b.author) || "匿名"}</span><span>🕒 ${esc(b.time)}</span></div>
    </div></div>`).join("")}</div>`;
  if (r.tweets.length) html += `<h3 class="group-title">X 推文（${r.tweets.length}）</h3><div class="tweet-list">${r.tweets.map((tw) => `
    <article class="tweet-item">
      <div class="tweet-head">
        <a class="tweet-author" href="https://x.com/${esc(tw.author)}" target="_blank" rel="noopener noreferrer">${esc(tw.author_name || tw.author)}</a>
        <span class="tweet-handle">@${esc(tw.author)}</span>
        ${tw.date ? `<span>📅 ${esc(tw.date)}</span>` : ""}
        ${typeof tw.likes === "number" ? `<span>❤️ ${tw.likes.toLocaleString()}</span>` : ""}
        <a class="ext-link" href="${esc(tw.url)}" target="_blank" rel="noopener noreferrer" aria-label="在 X 開啟">${EXT_ICON}</a>
      </div>
      <p class="tweet-text"><a href="${esc(tw.url)}" target="_blank" rel="noopener noreferrer">${esc(tw.text)}</a></p>
    </article>`).join("")}</div>`;
  $("#searchResults").innerHTML = html || `<p class="no-result">找不到符合「${esc(q)}」的內容。</p>`;
  switchView("search");
}

function switchView(name) {
  if (name !== "search") state.activeTab = name;
  $$(".view").forEach((el) => el.classList.add("hidden"));
  const view = $(`#view-${name}`);
  if (view) view.classList.remove("hidden");
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
}
window.switchView = switchView;

document.addEventListener("DOMContentLoaded", async () => {
  state.data = await (await fetch("data/site.json")).json();
  renderBuilds(); renderVideos(); renderBahamut(); renderTweets(); renderMeta();
  await loadStory();

  $$(".tab").forEach((t) => t.addEventListener("click", () => switchView(t.dataset.tab)));

  document.addEventListener("click", (e) => {
    const volBtn = e.target.closest(".story-volume-btn");
    if (volBtn) {
      renderStoryVolume(volBtn.dataset.volume);
      const tocEl = $("#storyToc");
      if (tocEl) tocEl.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const pill = e.target.closest(".pill");
    if (!pill) return;
    pill.closest(".pill-group").querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    if (pill.dataset.source) {
      state.buildsSource = pill.dataset.source;
      renderBuilds();
    } else {
      state[`${pill.closest(".pill-group").dataset.langFor}Lang`] = pill.dataset.lang;
      renderVideos(); renderTweets();
    }
  });

  $("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); doSearch($("#searchInput").value); });
  $("#clearSearch").addEventListener("click", () => { $("#searchInput").value = ""; switchView(state.activeTab); });

  switchView(state.activeTab);
});
