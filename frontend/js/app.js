"use strict";
/* ============ Yordamchi funksiyalar ============ */
const API = "/api";
const S = {
  token: sessionStorage.getItem("token"),
  user: JSON.parse(sessionStorage.getItem("user") || "null"),
  charts: [],
  modalChart: null,
};
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const LEVELS = { LOW: "Past", MEDIUM: "O'rtacha", HIGH: "Yuqori", CRITICAL: "Kritik" };
const GTYPES = { CURRENT: "Joriy", MIDTERM: "Oraliq", FINAL: "Yakuniy" };
const ASTAT = { PRESENT: "Keldi", ABSENT: "Kelmadi", LATE: "Kechikdi", EXCUSED: "Sababli" };
const pill = (l) => `<span class="pill ${l || "NONE"}">${l ? LEVELS[l] : "Ma'lumot yo'q"}</span>`;
const fmt = (n) => (n == null ? "—" : Number(n).toFixed(1));
const fdate = (s) => (s ? String(s).slice(0, 10) : "—");
const opts = (items, valKey, labelFn, selected) =>
  items.map((i) => `<option value="${esc(i[valKey])}" ${String(i[valKey]) === String(selected) ? "selected" : ""}>${esc(labelFn(i))}</option>`).join("");

function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (err ? " err" : "");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 3800);
}

async function api(path, { method = "GET", body, form, raw = false } = {}) {
  const headers = {};
  if (S.token) headers.Authorization = "Bearer " + S.token;
  let payload;
  if (form) payload = new URLSearchParams(form);
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401 && S.token) { logout(); throw new Error("Seans tugadi, qayta kiring"); }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join("; ") : msg;
    } catch (e) { /* JSON emas */ }
    throw new Error(msg);
  }
  return raw ? res : res.json();
}

function formObj(form) {
  const o = {};
  new FormData(form).forEach((v, k) => { o[k] = v === "" ? null : v; });
  return o;
}
const toInt = (v) => (v == null || v === "" ? null : parseInt(v, 10));

function openModal(title, html) {
  $("#modal-title").innerHTML = title;
  $("#modal-body").innerHTML = html;
  const m = $("#modal");
  if (!m.open) m.showModal();
  return $("#modal-body");
}
function closeModal() {
  if (S.modalChart) { S.modalChart.destroy(); S.modalChart = null; }
  const m = $("#modal");
  if (m.open) m.close();
}

function makeChart(id, config) {
  if (typeof Chart === "undefined") return null; // CDN mavjud bo'lmasa
  const c = new Chart($("#" + id), config);
  S.charts.push(c);
  return c;
}
const destroyCharts = () => { S.charts.forEach((c) => c.destroy()); S.charts = []; };

/* ============ Autentifikatsiya ============ */
function logout() {
  sessionStorage.clear();
  S.token = null; S.user = null;
  showLogin();
}
function showLogin() {
  $("#app").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
}
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#login-error").textContent = "";
  try {
    const data = await api("/auth/login", { method: "POST", form: formObj(e.target) });
    S.token = data.access_token; S.user = data.user;
    sessionStorage.setItem("token", S.token);
    sessionStorage.setItem("user", JSON.stringify(S.user));
    e.target.reset();
    startApp();
  } catch (err) { $("#login-error").textContent = err.message; }
});
$("#logout").addEventListener("click", logout);
$("#modal-close").addEventListener("click", closeModal);
$("#modal").addEventListener("close", () => { if (S.modalChart) { S.modalChart.destroy(); S.modalChart = null; } });
$("#menu-btn").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));

/* ============ Sahifalar ro'yxati va router ============ */
const PAGES = {
  studentHome: { title: "🎓 Mening kabinetim", roles: ["STUDENT"], render: pageStudentHome },
  dashboard: { title: "📊 Dashboard", roles: ["ADMIN", "TEACHER"], render: pageDashboard },
  students: { title: "👩‍🎓 Talabalar", roles: ["ADMIN", "TEACHER"], render: pageStudents },
  academic: { title: "📚 Guruhlar va fanlar", roles: ["ADMIN", "TEACHER"], render: pageAcademic },
  grades: { title: "📝 Baholar", roles: ["ADMIN", "TEACHER"], render: pageGrades },
  attendance: { title: "🗓 Davomat", roles: ["ADMIN", "TEACHER"], render: pageAttendance },
  risk: { title: "⚠️ Xavf guruhi", roles: ["ADMIN", "TEACHER"], render: pageRisk },
  notifications: { title: "🔔 Xabarnomalar", roles: ["ADMIN", "TEACHER"], render: pageNotifications },
  users: { title: "👤 Foydalanuvchilar", roles: ["ADMIN"], render: pageUsers },
};

function startApp() {
  $("#login-view").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#user-box").innerHTML = `<b>${esc(S.user.full_name)}</b><br><span class="muted">${S.user.role === "ADMIN" ? "Administrator" : "O'qituvchi"}</span>`;
  $("#nav").innerHTML = Object.entries(PAGES)
    .filter(([, p]) => p.roles.includes(S.user.role))
    .map(([k, p]) => `<a href="#/${k}" data-page="${k}">${p.title}</a>`).join("");
  if (!location.hash) { location.hash = S.user.role === "STUDENT" ? "#/studentHome" : "#/dashboard"; return; } // hashchange route() ni chaqiradi
  route();
}

async function route() {
  if (!S.token) return showLogin();
  const key = (location.hash.replace("#/", "") || "dashboard");
  const defaultKey = S.user.role === "STUDENT" ? "studentHome" : "dashboard";
  const page = PAGES[key] && PAGES[key].roles.includes(S.user.role) ? PAGES[key] : PAGES[defaultKey];
  const pageKey = Object.keys(PAGES).find((k) => PAGES[k] === page);
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === pageKey));
  document.querySelector(".sidebar").classList.remove("open");
  $("#page-title").textContent = page.title;
  destroyCharts();
  const v = $("#view");
  v.onclick = null;
  v.innerHTML = '<p class="muted">Yuklanmoqda…</p>';
  try { await page.render(v); } catch (err) { v.innerHTML = `<div class="card error">Xatolik: ${esc(err.message)}</div>`; }
  refreshBell();
}
window.addEventListener("hashchange", route);

async function refreshBell() {
  try {
    const { count } = await api("/notifications/unread-count");
    const b = $("#bell-count");
    b.textContent = count;
    b.classList.toggle("hidden", !count);
  } catch (e) { /* e'tiborsiz */ }
}

/* ============ Dashboard ============ */
async function pageDashboard(v) {
  const d = await api("/dashboard/summary");
  const t = d.totals;
  const kpi = (l, val, warn) => `<div class="card kpi ${warn && val > 0 ? "warn" : ""}"><div class="v">${val}</div><div class="l">${l}</div></div>`;
  v.innerHTML = `
    <div class="grid kpis">
      ${kpi("Talabalar", t.students)}${kpi("Guruhlar", t.groups)}${kpi("Fanlar", t.subjects)}
      ${kpi("O'rtacha ball", t.avg_score == null ? "—" : fmt(t.avg_score) + "%")}
      ${kpi("O'rtacha davomat", t.avg_attendance == null ? "—" : fmt(t.avg_attendance) + "%")}
      ${kpi("Xavf guruhida", t.at_risk, true)}
    </div>
    <div class="grid cols-2">
      <div class="card"><h3>Risk darajalari taqsimoti</h3><div class="chart-box"><canvas id="c-dist"></canvas></div></div>
      <div class="card"><h3>Guruhlar: o'rtacha ball va davomat (%)</h3><div class="chart-box"><canvas id="c-groups"></canvas></div></div>
      <div class="card"><h3>O'rtacha risk dinamikasi (oylar)</h3><div class="chart-box"><canvas id="c-trend"></canvas></div></div>
      <div class="card"><h3>Eng yuqori xavfdagi talabalar</h3><div class="table-wrap"><table>
        <tr><th>Talaba</th><th>Guruh</th><th>Ball</th><th>Daraja</th></tr>
        ${d.top_risk.map((r) => `<tr><td><a href="#/students">${esc(r.full_name)}</a></td><td>${esc(r.group_name)}</td><td>${fmt(r.risk_score)}</td><td>${pill(r.risk_level)}</td></tr>`).join("") || '<tr><td colspan="4" class="muted">Ma\'lumot yo\'q</td></tr>'}
      </table></div></div>
    </div>`;
  const dist = d.distribution;
  makeChart("c-dist", {
    type: "doughnut",
    data: { labels: ["Past", "O'rtacha", "Yuqori", "Kritik", "Ma'lumot yo'q"],
      datasets: [{ data: [dist.LOW, dist.MEDIUM, dist.HIGH, dist.CRITICAL, dist.NO_DATA], backgroundColor: ["#16a34a", "#d97706", "#ea580c", "#dc2626", "#9ca3af"] }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
  });
  makeChart("c-groups", {
    type: "bar",
    data: { labels: d.groups.map((g) => g.group),
      datasets: [{ label: "O'rtacha ball", data: d.groups.map((g) => g.avg_score), backgroundColor: "#4f46e5" },
                 { label: "Davomat", data: d.groups.map((g) => g.avg_attendance), backgroundColor: "#06b6d4" }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } },
  });
  makeChart("c-trend", {
    type: "line",
    data: { labels: d.risk_trend.map((r) => r.month),
      datasets: [{ label: "O'rtacha risk bali", data: d.risk_trend.map((r) => r.avg_risk), borderColor: "#dc2626", backgroundColor: "rgba(220,38,38,.15)", fill: true, tension: .3 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } },
  });
}

/* ============ Talabalar ============ */
async function pageStudents(v) {
  const groups = await api("/groups");
  const isAdmin = S.user.role === "ADMIN";
  v.innerHTML = `
    <div class="card"><div class="toolbar">
      <label>Qidirish<input id="f-q" placeholder="Ism yoki talaba kodi"></label>
      <label>Guruh<select id="f-group"><option value="">Barchasi</option>${opts(groups, "id", (g) => g.name)}</select></label>
      <label>Risk<select id="f-risk"><option value="">Barchasi</option>${Object.entries(LEVELS).map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></label>
      ${isAdmin ? '<button class="btn primary" id="add-student">+ Yangi talaba</button>' : ""}
    </div></div>
    <div class="card table-wrap" id="st-table"></div>`;
  let list = [];
  async function load() {
    const p = new URLSearchParams();
    if ($("#f-q").value.trim()) p.set("q", $("#f-q").value.trim());
    if ($("#f-group").value) p.set("group_id", $("#f-group").value);
    if ($("#f-risk").value) p.set("risk_level", $("#f-risk").value);
    list = await api("/students?" + p.toString());
    $("#st-table").innerHTML = `<table><tr><th>Kod</th><th>F.I.Sh.</th><th>Guruh</th><th>Ball</th><th>Davomat</th><th>Xavf</th><th></th></tr>
      ${list.map((s) => `<tr><td>${esc(s.student_code)}</td><td>${esc(s.full_name)}</td><td>${esc(s.group_name)}</td>
        <td>${fmt(s.avg_score)}</td><td>${fmt(s.attendance_rate)}</td><td>${pill(s.risk_level)}</td>
        <td class="actions"><button class="btn small" data-view="${s.id}">Ko'rish</button>
        ${isAdmin ? `<button class="btn small" data-edit="${s.id}">Tahrir</button><button class="btn small danger" data-del="${s.id}">O'chirish</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="7" class="muted">Talaba topilmadi</td></tr>'}</table>`;
  }
  let timer;
  $("#f-q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(load, 300); });
  $("#f-group").addEventListener("change", load);
  $("#f-risk").addEventListener("change", load);

  function studentForm(s = {}) {
    const body = openModal(s.id ? "Talabani tahrirlash" : "Yangi talaba", `
      <form class="form-grid">
        <label>Talaba kodi<input name="student_code" required minlength="3" value="${esc(s.student_code)}"></label>
        <label>F.I.Sh.<input name="full_name" required minlength="3" value="${esc(s.full_name)}"></label>
        <label>Email<input name="email" type="email" value="${esc(s.email)}"></label>
        ${s.id ? "" : '<label>Talaba logini<input name="username" required minlength="3"></label><label>Parol<input name="password" type="password" required minlength="8"></label>'}
        <label>Telefon<input name="phone" value="${esc(s.phone)}"></label>
        <label>Tug'ilgan sana<input name="birth_date" type="date" value="${esc(fdate(s.birth_date) === "—" ? "" : fdate(s.birth_date))}"></label>
        <label>Guruh<select name="group_id" required>${opts(groups, "id", (g) => g.name, s.group_id)}</select></label>
        <label>Holati<select name="status">${[["ACTIVE", "Faol"], ["LEAVE", "Akademik ta'til"], ["EXPELLED", "Chetlatilgan"]].map(([k, l]) => `<option value="${k}" ${s.status === k ? "selected" : ""}>${l}</option>`).join("")}</select></label>
        <button class="btn primary" type="submit">Saqlash</button>
      </form>`);
    $("form", body).addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = formObj(e.target);
      data.group_id = toInt(data.group_id);
      try {
        await api(s.id ? `/students/${s.id}` : "/students", { method: s.id ? "PUT" : "POST", body: data });
        closeModal(); toast(s.id ? "Ma'lumotlar saqlandi" : "Talaba va login-paroli yaratildi"); load();
      } catch (err) { toast(err.message, true); }
    });
  }
  if (isAdmin) $("#add-student").addEventListener("click", () => studentForm());

  v.onclick = async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    try {
      if (b.dataset.view) showStudent(b.dataset.view);
      else if (b.dataset.edit) studentForm(list.find((x) => String(x.id) === b.dataset.edit));
      else if (b.dataset.del && confirm("Talaba va uning barcha baho/davomat yozuvlari o'chiriladi. Davom etasizmi?")) {
        await api(`/students/${b.dataset.del}`, { method: "DELETE" }); toast("O'chirildi"); load();
      }
    } catch (err) { toast(err.message, true); }
  };
  await load();
}

async function showStudent(id) {
  const s = await api(`/students/${id}`);
  const body = openModal(esc(s.full_name) + " " + pill(s.risk_level), `
    <p class="muted">${esc(s.student_code)} · ${esc(s.group_name)} · Xavf bali: <b>${fmt(s.risk_score)}</b> · O'rtacha ball: <b>${fmt(s.avg_score)}%</b> · Davomat: <b>${fmt(s.attendance_rate)}%</b></p>
    <h4>Fanlar bo'yicha</h4>
    <div class="table-wrap"><table><tr><th>Fan</th><th>Ball %</th><th>Davomat %</th><th>Baholar</th></tr>
    ${s.subjects.map((x) => `<tr><td>${esc(x.name)}</td><td>${fmt(x.avg_score)}</td><td>${fmt(x.attendance_rate)}</td><td>${x.grades_count}</td></tr>`).join("") || '<tr><td colspan="4" class="muted">Fanga yozilmagan</td></tr>'}</table></div>
    <h4>Baholar dinamikasi (%)</h4>
    <div class="chart-box" style="height:220px"><canvas id="sc"></canvas></div>
    <h4>Risk tarixi</h4>
    <div class="table-wrap"><table><tr><th>Sana</th><th>Xavf bali</th><th>Daraja</th></tr>
    ${s.risk_history.slice().reverse().slice(0, 8).map((h) => `<tr><td>${fdate(h.calculated_at)}</td><td>${fmt(h.risk_score)}</td><td>${pill(h.risk_level)}</td></tr>`).join("") || '<tr><td colspan="3" class="muted">Hali hisoblanmagan</td></tr>'}</table></div>`);
  if (typeof Chart !== "undefined" && s.grades.length) {
    S.modalChart = new Chart($("#sc", body), {
      type: "line",
      data: { labels: s.grades.map((g) => fdate(g.graded_at)), datasets: [{ label: "Baho %", data: s.grades.map((g) => g.percent), borderColor: "#4f46e5", tension: .25 }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } } },
    });
  }
}

/* ============ Guruhlar va fanlar ============ */
async function pageAcademic(v) {
  const isAdmin = S.user.role === "ADMIN";
  const [groups, subjects, teachers] = await Promise.all([api("/groups"), api("/subjects"), api("/teachers")]);
  v.innerHTML = `
    <div class="grid cols-2">
      <div class="card"><h3>Guruhlar</h3><div class="table-wrap"><table>
        <tr><th>Nomi</th><th>Kurs</th><th>Yo'nalish</th><th>Kurator</th><th>Talabalar</th>${isAdmin ? "<th></th>" : ""}</tr>
        ${groups.map((g) => `<tr><td>${esc(g.name)}</td><td>${g.course_year}</td><td>${esc(g.specialty)}</td><td>${esc(g.curator_name || "—")}</td><td>${g.student_count}</td>
          ${isAdmin ? `<td><button class="btn small danger" data-delgroup="${g.id}">O'chirish</button></td>` : ""}</tr>`).join("")}</table></div>
        ${isAdmin ? `<hr><form id="group-form" class="form-grid">
          <label>Nomi<input name="name" required></label><label>Kurs<input name="course_year" type="number" min="1" max="6" value="1" required></label>
          <label>Yo'nalish<input name="specialty" required></label>
          <label>Kurator<select name="curator_id"><option value="">—</option>${opts(teachers, "id", (t) => t.full_name)}</select></label>
          <button class="btn primary">+ Guruh qo'shish</button></form>` : ""}</div>
      <div class="card"><h3>${isAdmin ? "Fanlar" : "Mening fanlarim"}</h3><div class="table-wrap"><table>
        <tr><th>Kod</th><th>Nomi</th><th>Kredit</th><th>O'qituvchi</th>${isAdmin ? "<th></th>" : ""}</tr>
        ${subjects.map((s) => `<tr><td>${esc(s.code)}</td><td>${esc(s.name)}</td><td>${s.credits}</td><td>${esc(s.teacher_name || "—")}</td>
          ${isAdmin ? `<td><button class="btn small danger" data-delsubject="${s.id}">O'chirish</button></td>` : ""}</tr>`).join("")}</table></div>
        ${isAdmin ? `<hr><form id="subject-form" class="form-grid">
          <label>Kod<input name="code" required></label><label>Nomi<input name="name" required></label>
          <label>Kredit<input name="credits" type="number" min="1" value="3"></label>
          <label>O'qituvchi<select name="teacher_id"><option value="">—</option>${opts(teachers, "id", (t) => t.full_name)}</select></label>
          <button class="btn primary">+ Fan qo'shish</button></form>` : ""}</div>
    </div>
    ${isAdmin ? `<div class="card"><h3>Guruhni fanga yozish (enrollment)</h3><form id="enroll-form" class="form-grid">
      <label>Guruh<select name="group_id">${opts(groups, "id", (g) => g.name)}</select></label>
      <label>Fan<select name="subject_id">${opts(subjects, "id", (s) => s.code + " — " + s.name)}</select></label>
      <button class="btn primary">Guruh talabalarini yozish</button></form></div>` : ""}`;
  const submit = (sel, fn) => { const f = $(sel); if (f) f.addEventListener("submit", async (e) => { e.preventDefault(); try { await fn(formObj(e.target)); } catch (err) { toast(err.message, true); } }); };
  submit("#group-form", async (d) => { d.course_year = toInt(d.course_year); d.curator_id = toInt(d.curator_id); await api("/groups", { method: "POST", body: d }); toast("Guruh qo'shildi"); route(); });
  submit("#subject-form", async (d) => { d.credits = toInt(d.credits) || 3; d.teacher_id = toInt(d.teacher_id); await api("/subjects", { method: "POST", body: d }); toast("Fan qo'shildi"); route(); });
  submit("#enroll-form", async (d) => { const r = await api("/enrollments/group", { method: "POST", body: { group_id: toInt(d.group_id), subject_id: toInt(d.subject_id) } }); toast(`Yozildi: ${r.added}, o'tkazib yuborildi: ${r.skipped}`); });
  v.onclick = async (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    try {
      if (b.dataset.delgroup && confirm("Guruhni o'chirasizmi?")) { await api(`/groups/${b.dataset.delgroup}`, { method: "DELETE" }); route(); }
      if (b.dataset.delsubject && confirm("Fan va uning baholarini o'chirasizmi?")) { await api(`/subjects/${b.dataset.delsubject}`, { method: "DELETE" }); route(); }
    } catch (err) { toast(err.message, true); }
  };
}

/* ============ Baholar ============ */
async function pageGrades(v) {
  const subjects = await api("/subjects");
  if (!subjects.length) { v.innerHTML = '<div class="card muted">Sizga biriktirilgan fan yo\'q.</div>'; return; }
  v.innerHTML = `
    <div class="card"><h3>Baho kiritish</h3><div class="form-grid">
      <label>Fan<select id="g-subject">${opts(subjects, "id", (s) => s.code + " — " + s.name)}</select></label></div>
      <form id="grade-form" class="form-grid" style="margin-top:12px">
        <label>Talaba<select name="enrollment_id" id="g-student"></select></label>
        <label>Turi<select name="grade_type">${Object.entries(GTYPES).map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></label>
        <label>Ball<input name="score" type="number" step="0.1" min="0" required></label>
        <label>Maksimal ball<input name="max_score" type="number" step="0.1" min="1" value="100" required></label>
        <label>Sana<input name="graded_at" type="date" value="${new Date().toISOString().slice(0, 10)}"></label>
        <label>Izoh<input name="comment" maxlength="255"></label>
        <button class="btn primary">Saqlash</button></form></div>
    <div class="card"><h3>So'nggi baholar</h3><div class="table-wrap" id="g-list"></div></div>`;
  async function loadSubject() {
    const sid = $("#g-subject").value;
    const enr = await api(`/subjects/${sid}/enrollments`);
    $("#g-student").innerHTML = opts(enr, "enrollment_id", (e) => `${e.full_name} (${e.group_name})`);
    const rows = await api(`/grades?subject_id=${sid}`);
    $("#g-list").innerHTML = `<table><tr><th>Sana</th><th>Talaba</th><th>Turi</th><th>Ball</th><th></th></tr>
      ${rows.map((r) => `<tr><td>${fdate(r.graded_at)}</td><td>${esc(r.full_name)}</td><td>${GTYPES[r.grade_type]}</td><td>${r.score} / ${r.max_score}</td>
        <td><button class="btn small danger" data-delgrade="${r.id}">O'chirish</button></td></tr>`).join("") || '<tr><td colspan="5" class="muted">Hali baho yo\'q</td></tr>'}</table>`;
  }
  $("#g-subject").addEventListener("change", () => loadSubject().catch((e) => toast(e.message, true)));
  $("#grade-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = formObj(e.target);
    d.enrollment_id = toInt(d.enrollment_id); d.score = parseFloat(d.score); d.max_score = parseFloat(d.max_score);
    if (!d.graded_at) delete d.graded_at;
    try {
      const r = await api("/grades", { method: "POST", body: d });
      toast(`Saqlandi. Talaba xavf darajasi: ${LEVELS[r.risk_level]} (${fmt(r.risk_score)})`);
      e.target.score.value = "";
      loadSubject();
    } catch (err) { toast(err.message, true); }
  });
  v.onclick = async (e) => {
    const b = e.target.closest("button[data-delgrade]");
    if (b && confirm("Bahoni o'chirasizmi?")) {
      try { await api(`/grades/${b.dataset.delgrade}`, { method: "DELETE" }); toast("O'chirildi"); loadSubject(); } catch (err) { toast(err.message, true); }
    }
  };
  await loadSubject();
}

/* ============ Davomat ============ */
async function pageAttendance(v) {
  const subjects = await api("/subjects");
  if (!subjects.length) { v.innerHTML = '<div class="card muted">Sizga biriktirilgan fan yo\'q.</div>'; return; }
  v.innerHTML = `
    <div class="card"><div class="toolbar">
      <label>Fan<select id="a-subject">${opts(subjects, "id", (s) => s.code + " — " + s.name)}</select></label>
      <label>Dars sanasi<input id="a-date" type="date" value="${new Date().toISOString().slice(0, 10)}"></label>
      <button class="btn" id="a-load">Yuklash</button>
      <button class="btn" id="a-all">Hammasi keldi</button>
      <button class="btn primary" id="a-save">Saqlash</button>
    </div></div>
    <div class="card table-wrap" id="a-list"></div>`;
  async function load() {
    const sid = $("#a-subject").value, date = $("#a-date").value;
    if (!date) return toast("Sanani tanlang", true);
    const [enr, saved] = await Promise.all([api(`/subjects/${sid}/enrollments`), api(`/attendance?subject_id=${sid}&lesson_date=${date}`)]);
    const map = Object.fromEntries(saved.map((r) => [r.enrollment_id, r.status]));
    $("#a-list").innerHTML = `<table><tr><th>#</th><th>Talaba</th><th>Guruh</th><th>Holat</th></tr>
      ${enr.map((e, i) => `<tr><td>${i + 1}</td><td>${esc(e.full_name)}</td><td>${esc(e.group_name)}</td>
        <td><select data-enr="${e.enrollment_id}">${Object.entries(ASTAT).map(([k, l]) => `<option value="${k}" ${(map[e.enrollment_id] || "PRESENT") === k ? "selected" : ""}>${l}</option>`).join("")}</select></td></tr>`).join("") || '<tr><td colspan="4" class="muted">Fanga talaba yozilmagan</td></tr>'}</table>`;
  }
  $("#a-load").addEventListener("click", () => load().catch((e) => toast(e.message, true)));
  $("#a-subject").addEventListener("change", () => load().catch((e) => toast(e.message, true)));
  $("#a-all").addEventListener("click", () => document.querySelectorAll("#a-list select").forEach((s) => (s.value = "PRESENT")));
  $("#a-save").addEventListener("click", async () => {
    const records = [...document.querySelectorAll("#a-list select")].map((s) => ({ enrollment_id: toInt(s.dataset.enr), status: s.value }));
    if (!records.length) return toast("Saqlash uchun talaba yo'q", true);
    try {
      const r = await api("/attendance/bulk", { method: "POST", body: { subject_id: toInt($("#a-subject").value), lesson_date: $("#a-date").value, records } });
      toast(`Davomat saqlandi (${r.saved} ta), risk qayta hisoblandi`);
    } catch (err) { toast(err.message, true); }
  });
  await load();
}

/* ============ Xavf guruhi ============ */
async function pageRisk(v) {
  const isAdmin = S.user.role === "ADMIN";
  v.innerHTML = `
    <div class="card"><div class="toolbar">
      <label>Daraja<select id="r-level"><option value="">Yuqori + Kritik</option><option value="CRITICAL">Faqat Kritik</option><option value="HIGH">Faqat Yuqori</option><option value="MEDIUM">O'rtacha</option></select></label>
      ${isAdmin ? '<button class="btn primary" id="r-recalc">Barchasini qayta hisoblash</button>' : ""}
      <button class="btn" id="r-csv">CSV yuklab olish</button>
    </div></div>
    <div class="card table-wrap" id="r-list"></div>`;
  async function load() {
    const lvl = $("#r-level").value;
    const rows = await api("/risk/at-risk" + (lvl ? `?level=${lvl}` : ""));
    $("#r-list").innerHTML = `<table><tr><th>Kod</th><th>Talaba</th><th>Guruh</th><th>Ball %</th><th>Davomat %</th><th>Xavf bali</th><th>Daraja</th></tr>
      ${rows.map((r) => `<tr><td>${esc(r.student_code)}</td><td>${esc(r.full_name)}</td><td>${esc(r.group_name)}</td><td>${fmt(r.avg_score)}</td><td>${fmt(r.attendance_rate)}</td><td><b>${fmt(r.risk_score)}</b></td><td>${pill(r.risk_level)}</td></tr>`).join("") || '<tr><td colspan="7" class="muted">Bu darajada talaba yo\'q 🎉</td></tr>'}</table>`;
  }
  $("#r-level").addEventListener("change", () => load().catch((e) => toast(e.message, true)));
  if (isAdmin) $("#r-recalc").addEventListener("click", async () => {
    try { const r = await api("/risk/recalculate", { method: "POST" }); toast(`Qayta hisoblandi: ${r.students} ta talaba`); load(); } catch (err) { toast(err.message, true); }
  });
  $("#r-csv").addEventListener("click", async () => {
    try {
      const lvl = $("#r-level").value;
      const res = await api("/risk/export.csv" + (lvl ? `?level=${lvl}` : ""), { raw: true });
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: "xavf_guruhi.csv" });
      a.click(); URL.revokeObjectURL(url);
    } catch (err) { toast(err.message, true); }
  });
  await load();
}

/* ============ Xabarnomalar ============ */
async function pageNotifications(v) {
  const rows = await api("/notifications");
  v.innerHTML = `<div class="toolbar"><button class="btn primary" id="n-all">Hammasini o'qilgan deb belgilash</button></div>
    <div class="grid">${rows.map((n) => `<div class="notif ${n.is_read ? "read" : ""}"><div class="t">${esc(n.title)}</div>
      <div>${esc(n.message)}</div><div class="d">${fdate(n.created_at)} ${n.is_read ? "" : `· <a href="#" data-read="${n.id}">o'qildi</a>`}</div></div>`).join("") || '<div class="card muted">Xabarnomalar yo\'q</div>'}</div>`;
  $("#n-all").addEventListener("click", async () => { await api("/notifications/read-all", { method: "POST" }); route(); });
  v.onclick = async (e) => {
    const a = e.target.closest("a[data-read]");
    if (a) { e.preventDefault(); await api(`/notifications/${a.dataset.read}/read`, { method: "POST" }); route(); }
  };
}

/* ============ Foydalanuvchilar (ADMIN) ============ */
async function pageUsers(v) {
  const users = await api("/users");
  v.innerHTML = `
    <div class="card"><h3>Yangi foydalanuvchi</h3><form id="user-form" class="form-grid">
      <label>Login<input name="username" required minlength="3"></label><label>F.I.Sh.<input name="full_name" required minlength="3"></label>
      <label>Email<input name="email" type="email" required></label><label>Parol (kamida 8 belgi)<input name="password" type="password" minlength="8" required></label>
      <label>Rol<select name="role"><option value="TEACHER">O'qituvchi</option><option value="ADMIN">Administrator</option></select></label>
      <label>Kafedra<input name="department"></label><button class="btn primary">Qo'shish</button></form></div>
    <div class="card table-wrap"><table><tr><th>ID</th><th>Login</th><th>F.I.Sh.</th><th>Email</th><th>Rol</th><th>Holati</th><th></th></tr>
    ${users.map((u) => `<tr><td>${u.id}</td><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td><td>${esc(u.email)}</td><td>${u.role}</td><td>${u.is_active ? "Faol" : "Faolsiz"}</td>
      <td>${u.is_active && u.id !== S.user.id ? `<button class="btn small danger" data-deact="${u.id}">Faolsizlantirish</button>` : ""}</td></tr>`).join("")}</table></div>`;
  $("#user-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await api("/users", { method: "POST", body: formObj(e.target) }); toast("Foydalanuvchi qo'shildi"); route(); } catch (err) { toast(err.message, true); }
  });
  v.onclick = async (e) => {
    const b = e.target.closest("button[data-deact]");
    if (b && confirm("Foydalanuvchi tizimga kira olmaydi. Davom etasizmi?")) {
      try { await api(`/users/${b.dataset.deact}`, { method: "DELETE" }); route(); } catch (err) { toast(err.message, true); }
    }
  };
}


/* Talaba shaxsiy kabineti */
async function pageStudentHome(v) {
  const s = await api(`/students/${S.user.student_id}`);
  const riskText = LEVELS[s.risk_level] || "Hali hisoblanmagan";
  const statusText = { PRESENT: "Keldi", ABSENT: "Kelmadi", LATE: "Kechikdi", EXCUSED: "Sababli" };
  const kpi = (label, value) => `<div class="card kpi"><div class="v">${value}</div><div class="l">${label}</div></div>`;
  v.innerHTML = `
    <div class="card"><h3>${esc(s.full_name)}</h3><p class="muted">Talaba kodi: ${esc(s.student_code)} · Guruh: ${esc(s.group_name)}</p><p>Risk darajasi: <b>${esc(riskText)}</b></p></div>
    <div class="grid kpis">${kpi("O'zlashtirish", s.avg_score == null ? "—" : fmt(s.avg_score) + "%")}${kpi("Davomat", s.attendance_rate == null ? "—" : fmt(s.attendance_rate) + "%")}${kpi("Xavf bali", s.risk_score == null ? "—" : fmt(s.risk_score))}</div>
    <div class="card"><h3>Fanlarim</h3><div class="table-wrap"><table><tr><th>Fan</th><th>O'rtacha ball</th><th>Davomat</th></tr>
    ${s.subjects.map(x => `<tr><td>${esc(x.name)}</td><td>${fmt(x.avg_score)}%</td><td>${fmt(x.attendance_rate)}%</td></tr>`).join("") || '<tr><td colspan="3">Fanlar biriktirilmagan</td></tr>'}</table></div></div>
    <div class="card"><h3>Baholarim va o'qituvchi izohlari</h3><div class="table-wrap"><table><tr><th>Sana</th><th>Fan</th><th>Turi</th><th>Ball</th><th>Izoh</th></tr>
    ${s.grades.slice().reverse().map(g => `<tr><td>${fdate(g.graded_at)}</td><td>${esc(g.subject)}</td><td>${GTYPES[g.grade_type] || g.grade_type}</td><td>${fmt(g.percent)}%</td><td>${esc(g.comment || "—")}</td></tr>`).join("") || '<tr><td colspan="5">Baholar hali kiritilmagan</td></tr>'}</table></div></div>
    <div class="card"><h3>Davomat tarixim</h3><div class="table-wrap"><table><tr><th>Sana</th><th>Fan</th><th>Holat</th><th>Izoh</th></tr>
    ${s.attendance_list.map(a => `<tr><td>${fdate(a.lesson_date)}</td><td>${esc(a.subject)}</td><td>${statusText[a.status] || a.status}</td><td>${esc(a.note || "—")}</td></tr>`).join("") || '<tr><td colspan="4">Davomat hali kiritilmagan</td></tr>'}</table></div></div>`;
}

/* ============ Ishga tushirish ============ */
if (S.token && S.user) startApp(); else showLogin();
