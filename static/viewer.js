import RFB from "/novnc/core/rfb.js";

const $ = (sel) => document.querySelector(sel);
const user = new URLSearchParams(location.search).get("user");
let rfb = null;

$("#who").textContent = user || "?";
document.title = `Kiosk viewer — ${user}`;

function setStatus(text, ok) {
  const el = $("#status");
  el.textContent = text;
  el.className = ok ? "ok" : "bad";
}

function connect() {
  $("#btn-reconnect").classList.add("hidden");
  setStatus("connecting…", true);
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  rfb = new RFB($("#screen"), `${scheme}://${location.host}/ws/vnc/${encodeURIComponent(user)}`);
  rfb.scaleViewport = true;
  rfb.viewOnly = $("#viewonly").checked;

  rfb.addEventListener("connect", () => setStatus("connected — you control this screen", true));
  rfb.addEventListener("disconnect", (e) => {
    setStatus(e.detail.clean ? "disconnected" : "connection lost (not logged in, or session ended)", false);
    $("#btn-reconnect").classList.remove("hidden");
  });
}

$("#viewonly").addEventListener("change", (e) => {
  if (rfb) rfb.viewOnly = e.target.checked;
});
$("#btn-reconnect").addEventListener("click", connect);

function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = isError ? "error-toast" : "ok-toast";
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = "hidden"; }, 4000);
}

async function action(act) {
  const res = await fetch(`/api/sessions/${encodeURIComponent(user)}/${act}`, { method: "POST" });
  if (res.ok) {
    toast(`${act.replace("-", " ")} ✓`);
  } else {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) { /* ignore */ }
    toast(msg, true);
  }
}

$("#btn-refresh").addEventListener("click", () => action("refresh"));
$("#btn-reset").addEventListener("click", () => action("restart-browser"));

if (user) {
  connect();
} else {
  setStatus("no user given — open a session from the dashboard", false);
}
