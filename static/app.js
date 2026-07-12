"use strict";

const $ = (sel) => document.querySelector(sel);

let sessionsTimer = null;
let usersTimer = null;

/* ---------- API helper ---------- */

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (res.status === 401) {
    showLogin();
    throw new Error("not authenticated");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) { /* ignore */ }
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res;
}

function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = isError ? "error-toast" : "ok-toast";
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = "hidden"; }, 4000);
}

/* ---------- auth ---------- */

function showLogin() {
  stopPolling();
  $("#login-overlay").classList.remove("hidden");
  $("#login-password").focus();
}

function hideLogin() {
  $("#login-overlay").classList.add("hidden");
  startPolling();
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#login-error").textContent = "";
  try {
    await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ password: $("#login-password").value }),
    });
    $("#login-password").value = "";
    hideLogin();
  } catch (err) {
    $("#login-error").textContent = err.message;
  }
});

$("#btn-logout").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); } catch (e) { /* ignore */ }
  showLogin();
});

/* ---------- sessions ---------- */

function fmtUptime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function sessionCard(s) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <a class="shot" href="/viewer.html?user=${encodeURIComponent(s.user)}" target="_blank" title="Open live view">
      <img alt="screen of ${s.user}" loading="lazy">
      <span class="shot-hint">click to view &amp; control</span>
    </a>
    <div class="meta">
      <strong>${s.user}</strong>
      <span class="muted">display :${s.display} &middot; up ${fmtUptime(s.uptime)}</span>
      <span class="dot ${s.browser_running ? "ok" : "bad"}"
            title="${s.browser_running ? "browser running" : "browser NOT running"}"></span>
    </div>
    <div class="actions">
      <button data-act="refresh" title="Send Ctrl+Shift+R to the browser">Refresh</button>
      <button data-act="restart-browser" title="Kill &amp; relaunch the browser with a clean profile">Reset</button>
      <button data-act="logout" class="danger" title="Terminate this RDP session">Logout</button>
    </div>`;
  card.querySelector("img").src =
    `/api/sessions/${encodeURIComponent(s.user)}/screenshot?t=${Date.now()}`;
  card.querySelectorAll("button[data-act]").forEach((btn) => {
    btn.addEventListener("click", () => sessionAction(s.user, btn.dataset.act, btn));
  });
  return card;
}

async function sessionAction(user, act, btn) {
  if (act === "logout" && !confirm(`Log out ${user}'s RDP session?`)) return;
  btn.disabled = true;
  try {
    await api(`/api/sessions/${encodeURIComponent(user)}/${act}`, { method: "POST" });
    toast(`${act.replace("-", " ")}: ${user} ✓`);
    if (act === "logout") loadSessions();
  } catch (err) {
    toast(`${user}: ${err.message}`, true);
  } finally {
    btn.disabled = false;
  }
}

async function loadSessions() {
  const list = await api("/api/sessions");
  const grid = $("#sessions");
  grid.replaceChildren(...list.map(sessionCard));
  $("#session-count").textContent = list.length ? `(${list.length})` : "";
  $("#no-sessions").classList.toggle("hidden", list.length > 0);
}

/* ---------- users ---------- */

async function loadUsers() {
  const users = await api("/api/users");
  const tbody = $("#users-table tbody");
  tbody.replaceChildren(...users.map((u) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${u.username}</td>
      <td><span class="badge ${u.online ? "on" : "off"}">${u.online ? "online" : "offline"}</span></td>
      <td class="right">
        <button data-act="passwd">Set password</button>
        <button data-act="delete" class="danger">Delete</button>
      </td>`;
    tr.querySelector('[data-act="passwd"]')
      .addEventListener("click", () => openModal("passwd", u.username));
    tr.querySelector('[data-act="delete"]')
      .addEventListener("click", () => deleteUser(u.username));
    return tr;
  }));
}

async function deleteUser(username) {
  if (!confirm(`Delete user ${username} and their home directory? This cannot be undone.`)) return;
  try {
    await api(`/api/users/${encodeURIComponent(username)}`, { method: "DELETE" });
    toast(`deleted ${username}`);
    loadUsers();
    loadSessions();
  } catch (err) {
    toast(err.message, true);
  }
}

/* ---------- add-user / set-password modal ---------- */

let modalMode = "add";

function openModal(mode, username = "") {
  modalMode = mode;
  $("#modal-title").textContent = mode === "add" ? "Add user" : `Set password for ${username}`;
  $("#modal-username").value = username;
  $("#modal-username").classList.toggle("hidden", mode !== "add");
  $("#modal-password").value = "";
  $("#modal-error").textContent = "";
  $("#modal-overlay").classList.remove("hidden");
  (mode === "add" ? $("#modal-username") : $("#modal-password")).focus();
}

$("#btn-adduser").addEventListener("click", () => openModal("add"));
$("#modal-cancel").addEventListener("click", () => $("#modal-overlay").classList.add("hidden"));

$("#modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = $("#modal-username").value.trim();
  const password = $("#modal-password").value;
  try {
    if (modalMode === "add") {
      await api("/api/users", { method: "POST", body: JSON.stringify({ username, password }) });
      toast(`user ${username} created — they can now log in over RDP`);
    } else {
      await api(`/api/users/${encodeURIComponent(username)}/password`, {
        method: "POST", body: JSON.stringify({ password }),
      });
      toast(`password updated for ${username}`);
    }
    $("#modal-overlay").classList.add("hidden");
    loadUsers();
  } catch (err) {
    $("#modal-error").textContent = err.message;
  }
});

/* ---------- polling ---------- */

function startPolling() {
  loadSessions().catch(() => {});
  loadUsers().catch(() => {});
  sessionsTimer = setInterval(() => loadSessions().catch(() => {}), 7000);
  usersTimer = setInterval(() => loadUsers().catch(() => {}), 20000);
}

function stopPolling() {
  clearInterval(sessionsTimer);
  clearInterval(usersTimer);
}

/* ---------- boot ---------- */

(async () => {
  try {
    const v = await fetch("/api/version").then((r) => r.json());
    $("#version").textContent = "v" + v.version;
  } catch (e) { /* ignore */ }
  try {
    await api("/api/sessions"); // auth probe
    hideLogin();
  } catch (e) {
    showLogin();
  }
})();
