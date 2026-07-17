const state = {
  running: false,
  streaming: false,
  references: [],
  pending: [],
  lastEvent: "Detenido",
  threshold: null,
  imageCountSignature: "",
  imageRefreshInProgress: false
};

const systemStatus = document.querySelector("#systemStatus");
const cameraFrame = document.querySelector("#cameraFrame");
const videoStream = document.querySelector("#videoStream");
const cameraLabel = document.querySelector("#cameraLabel");
const toggleCamera = document.querySelector("#toggleCamera");
const reloadRefs = document.querySelector("#reloadRefs");
const referenceCount = document.querySelector("#referenceCount");
const pendingCount = document.querySelector("#pendingCount");
const thresholdValue = document.querySelector("#thresholdValue");
const referencesList = document.querySelector("#referencesList");
const pendingList = document.querySelector("#pendingList");

function splitFileName(fileName) {
  const lastDot = fileName.lastIndexOf(".");

  if (lastDot <= 0) {
    return { base: fileName, extension: "" };
  }

  return {
    base: fileName.slice(0, lastDot),
    extension: fileName.slice(lastDot)
  };
}

function imageCountSignatureFromLists(references, pending) {
  return `${references.length}:${pending.length}`;
}

function imageCountSignatureFromStatus(status) {
  return `${status.references_files ?? 0}:${status.pending_files ?? 0}`;
}

function isEditingImageName() {
  return document.activeElement?.classList.contains("name-input");
}

function setStreamSource(running) {
  const target = running ? "/video_feed" : "/placeholder";

  if (videoStream.dataset.source !== target) {
    videoStream.dataset.source = target;
    videoStream.src = `${target}?t=${Date.now()}`;
  }
}

async function api(path, data = null) {
  const options = data
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      }
    : undefined;

  const response = await fetch(path, options);

  if (!response.ok) {
    throw new Error(`Error API: ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";

  if (!contentType.includes("application/json")) {
    throw new Error("La pagina no esta conectada al servidor Python de Witcam.");
  }

  return response.json();
}

function createImageRow(item, type) {
  const row = document.createElement("li");
  const selector = document.createElement("input");
  const preview = document.createElement("img");
  const info = document.createElement("div");
  const nameGroup = document.createElement("div");
  const nameInput = document.createElement("input");
  const extension = document.createElement("span");
  const tag = document.createElement("span");
  const actions = document.createElement("div");
  const rename = document.createElement("button");
  const move = document.createElement("button");

  row.className = "image-row";
  selector.type = "checkbox";
  selector.className = "image-selector";
  preview.src = item.url;
  preview.alt = item.name;
  preview.loading = "lazy";
  info.className = "image-info";
  nameGroup.className = "name-group";
  nameInput.className = "name-input";
  const fileParts = splitFileName(item.name);
  nameInput.value = fileParts.base;
  nameInput.title = item.name;
  extension.className = "file-extension";
  extension.textContent = fileParts.extension || ".jpg";
  tag.textContent = type === "pending" ? "pendiente" : "oficial";
  tag.className = `tag ${type === "pending" ? "pending" : ""}`;
  actions.className = "row-actions";
  rename.textContent = "Renombrar";
  move.textContent = type === "pending" ? "A referencia" : "A pendiente";

  rename.addEventListener("click", () => renameImage(item.name, nameInput.value, type));

  if (type === "pending") {
    const reject = document.createElement("button");
    move.addEventListener("click", () => approvePending(item.name));
    reject.addEventListener("click", () => rejectPending(item.name));
    reject.textContent = "Eliminar";
    reject.className = "danger";
    actions.append(rename, move, reject);
  } else {
    move.addEventListener("click", () => unapproveReference(item.name));
    actions.append(rename, move);
  }

  nameGroup.append(nameInput, extension);
  info.append(nameGroup, tag);
  row.append(selector, preview, info, actions);

  return row;
}

function renderList(element, items, type) {
  element.innerHTML = "";

  if (items.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-row";
    empty.textContent = type === "pending"
      ? "Sin capturas pendientes"
      : "Sin referencias cargadas";
    element.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    element.appendChild(createImageRow(item, type));
  });
}

function renderStatus() {
  systemStatus.textContent = state.running ? "Activo" : "Detenido";
  systemStatus.classList.toggle("active", state.running);
  cameraFrame.classList.toggle("running", state.running);
  setStreamSource(state.streaming);
  toggleCamera.textContent = state.running ? "Detener" : "Iniciar";
  cameraLabel.textContent = state.lastEvent;
  thresholdValue.textContent = state.threshold === null
    ? "--"
    : state.threshold.toFixed(2);
}

function renderImages() {
  referenceCount.textContent = state.references.length;
  pendingCount.textContent = state.pending.length;

  renderList(referencesList, state.references, "reference");
  renderList(pendingList, state.pending, "pending");
}

function render() {
  renderStatus();
  renderImages();
}

async function loadImages() {
  if (state.imageRefreshInProgress) {
    return;
  }

  state.imageRefreshInProgress = true;

  try {
    const data = await api("/api/list");
    state.references = data.references;
    state.pending = data.pending;
    state.imageCountSignature = imageCountSignatureFromLists(state.references, state.pending);
    renderImages();
  } finally {
    state.imageRefreshInProgress = false;
  }
}

async function loadStatus() {
  try {
    const status = await api("/api/status");
    const statusImageSignature = imageCountSignatureFromStatus(status);
    state.running = status.running;
    state.streaming = status.streaming;
    state.lastEvent = status.last_error || status.last_event || "Detenido";
    state.threshold = Number(status.similarity_threshold);
    renderStatus();

    if (
      state.imageCountSignature
      && statusImageSignature !== state.imageCountSignature
      && !isEditingImageName()
    ) {
      await loadImages();
    }
  } catch (error) {
    state.running = false;
    state.streaming = false;
    state.lastEvent = "Abre la app con python app.py";
    renderStatus();
    console.error(error);
  }
}

async function loadAll() {
  await loadStatus();
  await loadImages();
}

async function waitForStreamReady() {
  const maxAttempts = 30;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    await loadStatus();

    if (state.streaming || !state.running) {
      return;
    }
  }
}

async function approvePending(fileName) {
  await api("/api/approve", { file: fileName });
  await loadAll();
}

async function unapproveReference(fileName) {
  await api("/api/unapprove", { file: fileName });
  await loadAll();
}

async function renameImage(fileName, newName, type) {
  const safeBaseName = splitFileName(newName.trim()).base;

  await api("/api/rename", {
    file: fileName,
    newName: safeBaseName,
    type
  });
  await loadAll();
}

async function rejectPending(fileName) {
  await api("/api/reject", { file: fileName });
  await loadAll();
}

toggleCamera.addEventListener("click", async () => {
  try {
    if (state.running) {
      state.running = false;
      state.streaming = false;
      state.lastEvent = "Deteniendo webcam...";
      renderStatus();
      await api("/api/stop", {});
    } else {
      state.running = true;
      state.streaming = false;
      state.lastEvent = "Iniciando webcam...";
      renderStatus();
      await api("/api/start", {});
      await waitForStreamReady();
    }

    await loadStatus();
  } catch (error) {
    state.lastEvent = "No se pudo cambiar el estado de la webcam";
    renderStatus();
    console.error(error);
  }
});

reloadRefs.addEventListener("click", loadImages);

loadAll();
setInterval(loadStatus, 2500);
