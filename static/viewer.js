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

async function connect() {
  $("#btn-reconnect").classList.add("hidden");
  setStatus("connecting…", true);

  // diagnose before dialing so failures get a precise message
  let sessions;
  try {
    const res = await fetch("/api/sessions");
    if (res.status === 401) {
      setStatus("not signed in — sign in on the dashboard, then reload this page", false);
      $("#btn-reconnect").classList.remove("hidden");
      return;
    }
    sessions = await res.json();
  } catch (e) {
    setStatus("admin service unreachable", false);
    $("#btn-reconnect").classList.remove("hidden");
    return;
  }
  if (!sessions.some((s) => s.user === user)) {
    setStatus(`${user} has no active RDP session`, false);
    $("#btn-reconnect").classList.remove("hidden");
    return;
  }

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  rfb = new RFB($("#screen"), `${scheme}://${location.host}/ws/vnc/${encodeURIComponent(user)}`);
  rfb.scaleViewport = true;
  rfb.viewOnly = $("#viewonly").checked;
  // touch devices have no hover pointer: show a dot at the remote cursor
  // position so taps have visible feedback
  rfb.showDotCursor = $("#touchmode").checked;

  rfb.addEventListener("connect", () => setStatus("connected — you control this screen", true));
  rfb.addEventListener("disconnect", (e) => {
    setStatus(e.detail.clean
      ? "disconnected"
      : "connection lost — session may have ended (server log: journalctl -u kiosk-admin)", false);
    $("#btn-reconnect").classList.remove("hidden");
  });
}

$("#viewonly").addEventListener("change", (e) => {
  if (rfb) rfb.viewOnly = e.target.checked;
});
$("#btn-reconnect").addEventListener("click", connect);

/* touch-screen mode for the person mirroring: bigger toolbar targets and a
   dot cursor. Remembered per browser; defaults to on for touch devices. */
const touchBox = $("#touchmode");
const storedTouch = localStorage.getItem("kiosk-viewer-touch");
touchBox.checked = storedTouch === null ? ("ontouchstart" in window) : storedTouch === "1";

function applyTouch() {
  document.body.classList.toggle("touch", touchBox.checked);
  if (rfb) rfb.showDotCursor = touchBox.checked;
}
touchBox.addEventListener("change", () => {
  localStorage.setItem("kiosk-viewer-touch", touchBox.checked ? "1" : "0");
  applyTouch();
});
applyTouch();

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

// viewers can watch & control the screen but get no admin buttons
fetch("/api/me").then((r) => r.ok ? r.json() : null).then(async (who) => {
  if (!who) return;
  if (who.role !== "admin") {
    $("#btn-refresh").classList.add("hidden");
    $("#btn-reset").classList.add("hidden");
    return;
  }
  // admins also get a toggle for the USER's touch mode (kiosk-side)
  try {
    const users = await fetch("/api/users").then((r) => r.json());
    const u = users.find((x) => x.username === user);
    if (!u) return;
    const box = $("#usertouch");
    box.checked = u.touch;
    $("#usertouch-label").classList.remove("hidden");
    box.addEventListener("change", async () => {
      box.disabled = true;
      try {
        const res = await fetch(`/api/users/${encodeURIComponent(user)}/touch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ touch: box.checked }),
        });
        if (!res.ok) {
          let msg = res.statusText;
          try { msg = (await res.json()).detail || msg; } catch (e) { /* ignore */ }
          throw new Error(msg);
        }
        toast(`touch screen ${box.checked ? "enabled" : "disabled"} for ${user} — press "Reset browser" to apply now`);
      } catch (err) {
        toast(err.message, true);
        box.checked = !box.checked;
      } finally {
        box.disabled = false;
      }
    });
  } catch (e) { /* ignore */ }
}).catch(() => {});

if (user) {
  connect();
} else {
  setStatus("no user given — open a session from the dashboard", false);
}
