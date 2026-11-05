"use strict";

let state = null;
let currentPlan = null;
let lastExecution = null;

const el = id => document.getElementById(id);

const titles = {
  search: "Find the file. Understand why.",
  files: "Authorized document collection.",
  warranty: "Warranty & Asset Ledger (Feature 1)",
  tax: "Tax Dossier Stager (Feature 6)",
  quarantine: "Zero-Trust Quarantine & Privacy (Feature 2)",
  tags: "SafeTagging Metadata (Feature 3)",
  ocr: "Native OCR Inspector (Feature 7)",
  duplicates: "Duplicate review & content equality.",
  actions: "SafeAction Planner & ProofChain (Feature 4 & 5)",
  adversarial: "Adversarial Invariant Sandbox (Feature 5)",
  history: "ProofChain Audit Receipts & Ledger"
};

function node(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined && text !== null) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
}

function error(message) {
  const errEl = el("error");
  errEl.textContent = message || "";
  errEl.hidden = !message;
}

async function api(path, body) {
  const options = body ? {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-VaultMind-CSRF": state ? state.csrf : ""
    },
    body: JSON.stringify(body)
  } : {};
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Request failed");
  return data;
}

function action(label, fn, cls = "") {
  const b = node("button", label, cls);
  b.type = "button";
  b.addEventListener("click", () => Promise.resolve().then(fn).catch(e => error(e.message)));
  return b;
}

function item(title, text) {
  const d = node("article", undefined, "item");
  d.append(node("h3", title), node("p", text));
  return d;
}

function setProofChainStep(step) {
  const steps = ["proposal", "validation", "approval", "execution", "receipt"];
  steps.forEach(s => {
    const elStep = el("step-" + s);
    if (elStep) elStep.classList.remove("active", "completed");
  });
  if (step === "proposal") el("step-proposal")?.classList.add("active");
  if (step === "validation") { el("step-proposal")?.classList.add("completed"); el("step-validation")?.classList.add("active"); }
  if (step === "approval") { el("step-proposal")?.classList.add("completed"); el("step-validation")?.classList.add("completed"); el("step-approval")?.classList.add("active"); }
  if (step === "execution") { el("step-proposal")?.classList.add("completed"); el("step-validation")?.classList.add("completed"); el("step-approval")?.classList.add("completed"); el("step-execution")?.classList.add("active"); }
  if (step === "receipt") { steps.forEach(s => el("step-" + s)?.classList.add("completed")); }
}

async function preview(path) {
  const data = await api("/api/preview?path=" + encodeURIComponent(path));
  el("preview-title").textContent = path;
  el("preview-text").textContent = data.text;
  el("preview").showModal();
}

async function search() {
  error("");
  const query = el("query").value;
  const data = await api("/api/search?q=" + encodeURIComponent(query));
  const container = el("results");
  container.replaceChildren();
  if (!data.results.length) {
    container.append(node("p", "No matching evidence. Try a term in the source (e.g. 'warranty', 'monitor', 'w2'). This lexical baseline cannot infer synonyms.", "muted"));
    return;
  }
  for (const r of data.results) {
    const d = item(r.path.split("/").pop(), r.excerpt);
    d.append(node("p", r.path, "path"), action("Preview source", () => preview(r.path)));
    container.append(d);
  }
}

function displayPlan(plan) {
  currentPlan = plan;
  setProofChainStep("approval");
  const box = node("div", undefined, "plan-card");
  box.append(
    node("span", `PROOFCHAIN PROPOSAL · PLAN ${plan.version} (${plan.plan_type.toUpperCase()})`, "tag"),
    node("h2", `Plan v${plan.version}: ${plan.actions.length} action(s) proposed`)
  );

  const table = node("table", undefined, "plan-table");
  const thead = node("tr");
  thead.append(node("th", "Action"), node("th", "Source"), node("th", "Target"), node("th", "Rationale"), node("th", "Confidence"));
  table.append(thead);

  plan.actions.forEach((a, idx) => {
    const tr = node("tr");
    tr.append(
      node("td", `#${idx}`),
      node("td", a.source, "path"),
      node("td", a.destination, "path"),
      node("td", a.rationale),
      node("td", a.confidence, `badge badge-${a.confidence === "high" ? "success" : "warning"}`)
    );
    table.append(tr);
  });
  box.append(table);

  const approvalGroup = node("div", undefined, "approval-group");
  const label = node("label", `Enter 'APPROVE ${plan.version}' to authorize:`);
  label.htmlFor = "approval-input";
  const input = node("input");
  input.id = "approval-input";
  input.value = `APPROVE ${plan.version}`;
  input.autocomplete = "off";

  const btnApprove = action("Approve & Execute via ProofChain", async () => {
    setProofChainStep("execution");
    const result = await api("/api/execute", {
      fingerprint: plan.fingerprint,
      confirmation: input.value.trim(),
      selected: plan.actions.map((_, i) => i)
    });
    lastExecution = plan.fingerprint;
    setProofChainStep("receipt");

    const receiptBox = node("div", undefined, "receipt-summary");
    receiptBox.append(
      node("h3", "Execution Completed & Verified"),
      node("p", `Cryptographic Proof Receipt: ${result.receipt}`, "path"),
      node("p", `Authorized: ${result.authorized.length} | Changed: ${result.actually_changed.length} | Unchanged: ${result.unchanged.length}`)
    );

    if (plan.plan_type === "move" || plan.plan_type === "quarantine" || plan.plan_type === "tax_stage") {
      receiptBox.append(action("Generate Verified Inverse Plan", async () => {
        const inv = await api("/api/inverse", { fingerprint: lastExecution });
        displayPlan(inv);
        await refresh();
      }, "btn-secondary"));
    }

    box.replaceChildren(receiptBox);
    await refresh();
  }, "primary");

  approvalGroup.append(label, input, btnApprove);
  box.append(approvalGroup);

  el("plan").replaceChildren(box);
  // Switch to actions view if not already there
  switchView("actions");
}

async function loadWarrantyLedger() {
  const data = await api("/api/warranty-ledger");
  const summaryEl = el("warranty-summary");
  summaryEl.replaceChildren();

  const m1 = node("div", undefined, "stat");
  m1.append(node("b", String(data.total_assets)), node("span", "Indexed Assets"));
  const m2 = node("div", undefined, "stat");
  m2.append(node("b", String(data.total_assets - data.assets_with_missing_serials)), node("span", "Verified Serials"));
  const m3 = node("div", undefined, "stat");
  m3.append(node("b", String(data.assets_with_missing_serials)), node("span", "Missing Serial Alerts"));
  summaryEl.append(m1, m2, m3);

  const container = el("warranty-cards");
  container.replaceChildren();

  data.assets.forEach(asset => {
    const card = node("div", undefined, "card asset-card");
    const header = node("div", undefined, "card-header");
    header.append(
      node("h3", asset.product_name),
      node("span", asset.serial_status === "verified" ? "Serial Verified" : "Serial Missing", `badge badge-${asset.serial_status === "verified" ? "success" : "danger"}`)
    );

    const body = node("div", undefined, "card-body");
    body.append(
      node("p", `Manufacturer: ${asset.manufacturer}`),
      node("p", `Serial Number: ${asset.serial_number || "Not stated in documents (flagged)"}`),
      node("p", `Purchase Date: ${asset.purchase_date || "Unknown"} | Warranty: ${asset.warranty_period || "Unknown"}`),
      node("p", `Warranty Expiration: ${asset.expiration_date || "Unknown"}`)
    );

    if (asset.uncertainty_flags && asset.uncertainty_flags.length) {
      const u = node("div", undefined, "uncertainty-tag");
      u.append(node("small", `Uncertainty: ${asset.uncertainty_flags.join(", ")}`));
      body.append(u);
    }

    const citationsDiv = node("div", undefined, "citations-box");
    asset.citations.forEach(c => {
      citationsDiv.append(action(`Source: ${c.source}`, () => preview(c.source), "btn-link"));
    });
    body.append(citationsDiv);

    card.append(header, body);
    container.append(card);
  });
}

async function loadTaxDossier() {
  const data = await api("/api/tax-dossier");
  const container = el("tax-manifest-container");
  container.replaceChildren();

  const manifest = data.manifest;
  const mDiv = node("div", undefined, "manifest-summary");
  mDiv.append(
    node("p", `Total Financial Documents Staged: ${manifest.total_staged}`),
    node("p", `Exact Duplicates Detected & Skipped: ${manifest.duplicates_flagged.length}`)
  );

  const table = node("table", undefined, "plan-table");
  const thead = node("tr");
  thead.append(node("th", "Source"), node("th", "Tax Year"), node("th", "Quarter"), node("th", "Category"), node("th", "Staged Destination"));
  table.append(thead);

  manifest.records.forEach(r => {
    const tr = node("tr");
    tr.append(
      node("td", r.source, "path"),
      node("td", r.tax_year),
      node("td", r.quarter),
      node("td", r.category, "badge badge-info"),
      node("td", r.staged_destination, "path")
    );
    table.append(tr);
  });

  if (manifest.duplicates_flagged.length) {
    const dupeBox = node("div", undefined, "dupe-flag-box");
    dupeBox.append(node("h4", "Exact Duplicate Tax Files (Skipped from Move):"));
    manifest.duplicates_flagged.forEach(d => {
      dupeBox.append(node("p", `${d.duplicate_path} == duplicate of == ${d.primary_path}`, "path"));
    });
    container.append(dupeBox);
  }

  container.append(mDiv, table);
}

async function loadQuarantine() {
  const data = await api("/api/quarantine");
  const container = el("quarantine-list");
  container.replaceChildren();

  if (!data.sensitive_files.length) {
    container.append(node("p", "No sensitive documents detected in current corpus.", "muted"));
    return;
  }

  data.sensitive_files.forEach(f => {
    const item = node("article", undefined, "item");
    item.append(
      node("h3", f.path),
      node("p", `Detected Privacy Categories: ${f.privacy_hints.join(", ")}`, "badge badge-danger"),
      node("p", `Masked Preview: ${f.masked_preview}`),
      action("Masked preview", () => preview(f.path))
    );
    container.append(item);
  });
}

async function loadSafeTagging() {
  const data = await api("/api/tags");
  const container = el("tags-active-list");
  container.replaceChildren();

  const fileSelect = el("tag-file");
  fileSelect.replaceChildren();
  state.virtual_paths.forEach(p => {
    const opt = node("option", p);
    opt.value = p;
    fileSelect.append(opt);
  });

  const filesWithTags = Object.entries(data.file_tags);
  if (!filesWithTags.length) {
    container.append(node("p", "No custom tags assigned yet. Use the form above to add tags without moving files.", "muted"));
    return;
  }

  filesWithTags.forEach(([filePath, tags]) => {
    const row = node("div", undefined, "tag-row");
    row.append(node("span", filePath, "path"));
    const tagWrap = node("span", undefined, "tags-wrapper");
    tags.forEach(t => {
      const chip = node("span", t.name, "tag-chip");
      chip.style.backgroundColor = t.colour || "#3b82f6";
      chip.style.color = "#fff";
      tagWrap.append(chip);
    });
    row.append(tagWrap);
    container.append(row);
  });
}

async function inspectOcr() {
  const selectedPath = el("ocr-file-select").value;
  const data = await api("/api/ocr?path=" + encodeURIComponent(selectedPath));
  const container = el("ocr-results-container");
  container.replaceChildren();

  const card = node("div", undefined, "card ocr-card");
  const header = node("div", undefined, "card-header");
  header.append(
    node("h3", `OCR Inspection: ${selectedPath}`),
    node("span", `Confidence: ${Math.round(data.confidence * 100)}% · ${data.status}`, `badge badge-${data.confidence > 0.85 ? "success" : "warning"}`)
  );

  const body = node("div", undefined, "card-body");
  body.append(
    node("p", `Native Capability: ${data.engine} (photo-agent)`),
    node("p", `Extraction Provenance: Timestamp ${data.timestamp}`)
  );

  if (Object.keys(data.extracted_fields).length) {
    const fieldsBox = node("div", undefined, "fields-box");
    fieldsBox.append(node("h4", "Extracted Structured Fields:"));
    for (const [k, v] of Object.entries(data.extracted_fields)) {
      fieldsBox.append(node("p", `${k}: ${v}`));
    }
    body.append(fieldsBox);
  }

  if (data.uncertainty_flags && data.uncertainty_flags.length) {
    const uBox = node("div", undefined, "uncertainty-tag");
    uBox.append(node("b", "Uncertainty Flags: "), node("span", data.uncertainty_flags.join(", ")));
    body.append(uBox);
  }

  body.append(node("h4", "Transcribed OCR Text:"), node("pre", data.raw_text));
  card.append(header, body);
  container.append(card);
}

async function runAdversarialSuite() {
  const res = await api("/api/adversarial-check", {});
  const container = el("adversarial-results");
  container.replaceChildren();

  const box = node("div", undefined, "card");
  box.append(
    node("h3", `Adversarial Test Suite: ${Math.round(res.rejection_rate * 100)}% Rejection Rate`),
    node("p", `Tested Vectors: ${res.vectors_tested} | Rejected Vectors: ${res.vectors_rejected} (Fail-Closed)`),
    node("p", res.status, "badge badge-success")
  );
  container.append(box);
}

function switchView(viewName) {
  document.querySelectorAll(".view").forEach(v => v.hidden = v.id !== viewName);
  document.querySelectorAll("nav button").forEach(n => n.classList.toggle("active", n.dataset.view === viewName));
  el("title").textContent = titles[viewName] || "VaultMind AI";
  error("");

  if (viewName === "warranty") loadWarrantyLedger().catch(e => error(e.message));
  if (viewName === "tax") loadTaxDossier().catch(e => error(e.message));
  if (viewName === "quarantine") loadQuarantine().catch(e => error(e.message));
  if (viewName === "tags") loadSafeTagging().catch(e => error(e.message));
  if (viewName === "ocr") inspectOcr().catch(e => error(e.message));
}

async function refresh() {
  state = await api("/api/state");
  const logical = state.duplicates.reduce((a, g) => a + g.logical_redundant_bytes, 0);

  el("stats").replaceChildren();
  for (const [value, label] of [
    [state.files.length, "authorized text fixtures"],
    [state.duplicates.length, "verified duplicate groups"],
    [logical.toLocaleString() + " B", "logical redundant content"]
  ]) {
    const s = node("div", undefined, "stat");
    s.append(node("b", String(value)), node("span", label));
    el("stats").append(s);
  }

  el("file-list").replaceChildren();
  for (const f of state.files) {
    const d = item(f.path, f.size + " bytes");
    d.append(action("Preview", () => preview(f.path)));
    el("file-list").append(d);
  }

  el("duplicate-list").replaceChildren();
  for (const g of state.duplicates) {
    const d = item(g.paths[0].split("/").pop(), g.paths.join("\n"));
    d.append(node("span", g.logical_redundant_bytes + " logical redundant bytes", "tag"), node("p", "SHA-256 " + g.sha256, "path"));
    el("duplicate-list").append(d);
  }

  const selected = el("source").value;
  el("source").replaceChildren();
  for (const path of state.virtual_paths) {
    const o = node("option", path);
    o.value = path;
    el("source").append(o);
  }
  if (state.virtual_paths.includes(selected)) el("source").value = selected;

  el("history-list").replaceChildren();
  if (!state.history.length) {
    el("history-list").append(node("p", "No simulated actions in this session.", "muted"));
  }
  for (const entry of [...state.history].reverse()) {
    const title = `${entry.event.toUpperCase()} · Plan v${entry.version} (${entry.plan_type || "move"})`;
    el("history-list").append(item(title, JSON.stringify(entry, null, 2)));
  }
}

// Event Listeners
document.querySelectorAll("nav button").forEach(b => {
  b.addEventListener("click", () => switchView(b.dataset.view));
});

el("search-form").addEventListener("submit", e => {
  e.preventDefault();
  search().catch(e => error(e.message));
});

document.querySelectorAll("[data-query]").forEach(b => {
  b.addEventListener("click", () => {
    el("query").value = b.dataset.query;
    search().catch(e => error(e.message));
  });
});

el("plan-form").addEventListener("submit", e => {
  e.preventDefault();
  error("");
  api("/api/plan", { source: el("source").value, destination: el("destination").value })
    .then(displayPlan)
    .then(refresh)
    .catch(e => error(e.message));
});

el("btn-stage-tax")?.addEventListener("click", () => {
  api("/api/tax/plan", {})
    .then(res => displayPlan(res.plan))
    .catch(e => error(e.message));
});

el("btn-propose-quarantine")?.addEventListener("click", () => {
  api("/api/quarantine", {})
    .then(res => displayPlan(res.plan))
    .catch(e => error(e.message));
});

el("tag-form")?.addEventListener("submit", e => {
  e.preventDefault();
  const filePath = el("tag-file").value;
  const tagName = el("tag-name").value;
  const tagColor = el("tag-color").value;
  api("/api/tags/plan", {
    operations: [{ path: filePath, tag_name: tagName, colour: tagColor, operation: "tag_add" }]
  })
    .then(displayPlan)
    .catch(e => error(e.message));
});

el("btn-run-ocr")?.addEventListener("click", () => {
  inspectOcr().catch(e => error(e.message));
});

el("btn-run-adversarial")?.addEventListener("click", () => {
  runAdversarialSuite().catch(e => error(e.message));
});

// Initialization
refresh().then(search).catch(e => error(e.message));
