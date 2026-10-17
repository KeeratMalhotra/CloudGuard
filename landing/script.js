/* CloudGuard landing page: small, dependency-free interactions */
(() => {
  "use strict";

  document.documentElement.classList.remove("no-js");

  // localStorage can throw in some private-browsing modes, so wrap it
  const store = {
    get: (k) => { try { return window.localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { window.localStorage.setItem(k, v); } catch { /* ignore */ } },
  };

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Toast + clipboard ---------- */
  const toast = $("#toast");
  let toastTimer;
  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-on"), 1600);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback for browsers/contexts without the async clipboard API
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    showToast("Copied to clipboard");
  }

  // Copy buttons inside code blocks copy whatever is currently shown,
  // including the project ID the visitor typed in.
  $$(".copy").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.copyTarget
        ? document.getElementById(btn.dataset.copyTarget)
        : btn.closest(".code").querySelector("pre");
      copyText(target.innerText.trim());
      btn.textContent = "Copied";
      btn.classList.add("is-done");
      setTimeout(() => {
        btn.textContent = "Copy";
        btn.classList.remove("is-done");
      }, 1400);
    });
  });

  $$("[data-copy]").forEach((el) => el.addEventListener("click", () => copyText(el.dataset.copy)));

  /* ---------- Nav border on scroll ---------- */
  const nav = $(".nav");
  const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* ---------- Scroll reveal ---------- */
  const reveals = $$(".reveal");
  if ("IntersectionObserver" in window && !reduceMotion) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach((el, i) => {
      // small stagger for siblings that appear together
      el.style.transitionDelay = `${(i % 4) * 60}ms`;
      io.observe(el);
    });
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }

  /* ---------- Card spotlight follows the cursor ---------- */
  $$(".card").forEach((card) => {
    card.addEventListener("pointermove", (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${e.clientX - r.left}px`);
      card.style.setProperty("--my", `${e.clientY - r.top}px`);
    });
  });

  /* ---------- Hero stage: subtle parallax tilt ---------- */
  const stage = $("#stage");
  if (stage && finePointer && !reduceMotion) {
    let raf = null;
    window.addEventListener("pointermove", (e) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        const x = e.clientX / window.innerWidth - 0.5;
        const y = e.clientY / window.innerHeight - 0.5;
        stage.style.setProperty("--rx", `${(x * 5).toFixed(2)}deg`);
        stage.style.setProperty("--ry", `${(-y * 4).toFixed(2)}deg`);
        raf = null;
      });
    });
  }

  /* ---------- Hero terminal + live score ----------
     Each finding line deducts its severity weight, so the score card
     visibly drops from 100 to 23, the same maths scorecard.py does. */
  const WEIGHTS = { CRITICAL: 20, HIGH: 10, MEDIUM: 5, LOW: 2 };
  const LINES = [
    { html: '<span class="p">(venv) PS C:\\CloudGuard&gt;</span> python scorecard.py', delay: 500 },
    { html: '<span class="d">============================================</span>', delay: 120 },
    { html: '<span class="h">  CLOUDGUARD SECURITY SCORECARD - my-gcp-project</span>', delay: 120 },
    { html: '<span class="d">============================================</span>', delay: 260 },
    { html: '<span class="s-critical">--- CRITICAL ---</span>', delay: 180 },
    { html: '  [Storage Buckets] my-public-bucket', sev: "CRITICAL" },
    { html: '<span class="s-high">--- HIGH ---</span>', delay: 180 },
    { html: '  [IAM] 1234567890-compute@developer.gserviceaccount.com', sev: "HIGH" },
    { html: '  [Firewall] cloudguard-test-risky   tcp:22', sev: "HIGH" },
    { html: '  [Firewall] default-allow-rdp       tcp:3389', sev: "HIGH" },
    { html: '  [Firewall] default-allow-ssh       tcp:22', sev: "HIGH" },
    { html: '<span class="s-medium">--- MEDIUM ---</span>', delay: 180 },
    { html: '  [IAM] user:owner-one@example.com   roles/owner', sev: "MEDIUM" },
    { html: '  [IAM] user:owner-two@example.com   roles/owner', sev: "MEDIUM" },
    { html: '  [Audit Logging] no custom log sinks', sev: "MEDIUM" },
    { html: '<span class="s-low">--- LOW ---</span>', delay: 180 },
    { html: '  [Audit Logging] retention is only 30 days', sev: "LOW" },
    { html: '<span class="d">============================================</span>', delay: 200 },
    { html: 'SCORE: <span class="score">23/100</span>   (Critical Risk)   · 9 findings', delay: 300 },
  ];

  const term = $("#term");
  const scoreNum = $("#scoreNum");
  const ringBar = $("#ringBar");
  const gradeLabel = $("#gradeLabel");
  const CIRC = 2 * Math.PI * 50;
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  let score = 100;

  function gradeFor(s) {
    if (s >= 90) return ["Excellent", "var(--low)"];
    if (s >= 70) return ["Good", "var(--medium)"];
    if (s >= 50) return ["Needs improvement", "var(--high)"];
    return ["Critical risk", "var(--critical)"];
  }

  function renderScore() {
    scoreNum.textContent = score;
    ringBar.style.strokeDashoffset = String(CIRC * (1 - score / 100));
    const [label, color] = gradeFor(score);
    gradeLabel.textContent = label;
    gradeLabel.style.color = color;
    ringBar.style.stroke = score < 50 ? "var(--accent)" : color;
    Object.keys(counts).forEach((k) => ($("#c-" + k).textContent = counts[k]));
  }

  function animateScoreTo(target) {
    const start = score;
    const t0 = performance.now();
    const dur = 420;
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      score = Math.round(start + (target - start) * (1 - Math.pow(1 - p, 3)));
      renderScore();
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function applyFinding(sev) {
    counts[sev] += 1;
    animateScoreTo(Math.max(0, score - WEIGHTS[sev]));
  }

  const cursor = () => '<span class="cursor"></span>';

  function renderInstant() {
    term.innerHTML = LINES.map((l) => `<span class="ln">${l.html}</span>`).join("") + cursor();
    term.scrollTop = term.scrollHeight;
    LINES.forEach((l) => l.sev && (counts[l.sev] += 1));
    score = 100 - LINES.reduce((acc, l) => acc + (l.sev ? WEIGHTS[l.sev] : 0), 0);
    renderScore();
  }

  function typeFirstLine(line, done) {
    // "Type" the command character by character, then print the rest as output
    const tmp = document.createElement("div");
    tmp.innerHTML = line.html;
    const prompt = tmp.querySelector(".p").outerHTML + " ";
    const cmd = "python scorecard.py";
    let i = 0;
    const step = () => {
      term.innerHTML = `<span class="ln">${prompt}${cmd.slice(0, i)}${cursor()}</span>`;
      if (i++ < cmd.length) setTimeout(step, 45 + Math.random() * 40);
      else setTimeout(done, 450);
    };
    step();
  }

  function play() {
    let html = "";
    typeFirstLine(LINES[0], () => {
      html = `<span class="ln">${LINES[0].html}</span>`;
      let idx = 1;
      const next = () => {
        if (idx >= LINES.length) {
          term.innerHTML = html + cursor();
          term.scrollTop = term.scrollHeight;
          return;
        }
        const line = LINES[idx++];
        html += `<span class="ln">${line.html}</span>`;
        term.innerHTML = html + cursor();
        term.scrollTop = term.scrollHeight; // keep the newest line in view, like a real terminal
        if (line.sev) applyFinding(line.sev);
        setTimeout(next, line.delay ?? 340);
      };
      next();
    });
  }

  if (term) {
    renderScore();
    if (reduceMotion) {
      renderInstant();
    } else {
      // Start once the hero is actually on screen
      const startObs = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          startObs.disconnect();
          setTimeout(play, 400);
        }
      }, { threshold: 0.25 });
      startObs.observe(term);
    }
  }

  /* ---------- Install: live project ID ---------- */
  const pidInput = $("#pidInput");
  const pids = $$(".pid");
  const PLACEHOLDER = "YOUR_PROJECT_ID";
  const saved = store.get("cg-project-id");
  if (saved) pidInput.value = saved;

  function applyPid() {
    // Keep it to characters that are valid in GCP project IDs
    const clean = pidInput.value.trim().toLowerCase().replace(/[^a-z0-9-]/g, "");
    if (clean !== pidInput.value) pidInput.value = clean;
    pids.forEach((el) => (el.textContent = clean || PLACEHOLDER));
    store.set("cg-project-id", clean);
  }
  pidInput.addEventListener("input", applyPid);
  applyPid();

  /* ---------- Install: OS toggle ---------- */
  const segBtns = $$(".seg__btn");
  function setOS(os) {
    segBtns.forEach((b) => {
      const on = b.dataset.os === os;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", String(on));
    });
    $$("[data-os-block]").forEach((el) => (el.hidden = el.dataset.osBlock !== os));
    store.set("cg-os", os);
  }
  segBtns.forEach((b) => b.addEventListener("click", () => setOS(b.dataset.os)));
  const guessOS = /Win/i.test(navigator.platform || navigator.userAgent) ? "win" : "unix";
  setOS(store.get("cg-os") || guessOS);

  /* ---------- Tabs (Fork / Clone / ZIP) ---------- */
  $$("[data-tabs]").forEach((tabs) => {
    const btns = $$(".tabs__btn", tabs);
    const panels = $$(".tabs__panel", tabs);
    btns.forEach((btn) =>
      btn.addEventListener("click", () => {
        btns.forEach((b) => {
          const on = b === btn;
          b.classList.toggle("is-active", on);
          b.setAttribute("aria-selected", String(on));
        });
        panels.forEach((p) => p.classList.toggle("is-active", p.dataset.panel === btn.dataset.tab));
      })
    );
  });
})();
