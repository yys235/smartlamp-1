const gatewaySummary = document.querySelector("#gatewaySummary");
const connectionBadge = document.querySelector("#connectionBadge");
const lampGrid = document.querySelector("#lampGrid");
const messageBanner = document.querySelector("#messageBanner");
const globalControlForm = document.querySelector("#globalControlForm");
const turnAllOffButton = document.querySelector("#turnAllOffButton");
const refreshStatusButton = document.querySelector("#refreshStatusButton");
const lampCardTemplate = document.querySelector("#lampCardTemplate");
const globalIntensity = document.querySelector("#globalIntensity");
const globalIntensityValue = document.querySelector("#globalIntensityValue");

function updateRangeOutput(input, output) {
    output.textContent = input.value;
}

function showMessage(text, type = "info") {
    messageBanner.hidden = false;
    messageBanner.textContent = text;
    messageBanner.className = `message ${type}`;
}

function clearMessage() {
    messageBanner.hidden = true;
    messageBanner.textContent = "";
    messageBanner.className = "message";
}

function hexToRgb(hex) {
    const normalized = hex.replace("#", "");
    return {
        red: Number.parseInt(normalized.slice(0, 2), 16),
        green: Number.parseInt(normalized.slice(2, 4), 16),
        blue: Number.parseInt(normalized.slice(4, 6), 16),
    };
}

function summaryItem(label, value) {
    const wrapper = document.createElement("div");
    wrapper.className = "summary-item";

    const title = document.createElement("div");
    title.className = "summary-label";
    title.textContent = label;

    const content = document.createElement("div");
    content.className = "summary-value";
    content.textContent = value ?? "N/A";

    wrapper.append(title, content);
    return wrapper;
}

function renderSummary(status) {
    gatewaySummary.replaceChildren(
        summaryItem("网关地址", status.gateway_host || "未发现"),
        summaryItem("网关 ID", status.gateway_id ?? "未发现"),
        summaryItem("灯泡数量", status.lamp_count),
        summaryItem("全灯关闭", status.all_off ? "是" : "否"),
        summaryItem("最近发现", status.last_seen || "N/A"),
        summaryItem("最近通信", status.last_communication || "N/A"),
    );

    connectionBadge.textContent = status.connected ? "已连接" : "未连接";
    connectionBadge.className = `badge ${status.connected ? "online" : "offline"}`;
}

function renderLamps(status) {
    lampGrid.replaceChildren();

    if (!status.lamps.length) {
        const emptyState = document.createElement("div");
        emptyState.className = "summary-item";
        emptyState.textContent = status.connected ? "未读到灯泡，请尝试刷新。" : "等待网关广播。";
        lampGrid.append(emptyState);
        return;
    }

    status.lamps.forEach((lamp) => {
        const fragment = lampCardTemplate.content.cloneNode(true);
        const card = fragment.querySelector(".lamp-card");
        const title = fragment.querySelector(".lamp-title");
        const meta = fragment.querySelector(".lamp-meta");
        const badge = fragment.querySelector(".lamp-badge");
        const preview = fragment.querySelector(".lamp-color-preview");
        const rgb = fragment.querySelector(".lamp-rgb");
        const intensity = fragment.querySelector(".lamp-intensity");
        const form = fragment.querySelector(".lamp-form");
        const deviceIdInput = fragment.querySelector(".lamp-device-id");
        const colorInput = fragment.querySelector(".lamp-color-input");
        const intensityInput = fragment.querySelector(".lamp-intensity-input");
        const intensityOutput = fragment.querySelector(".lamp-intensity-output");
        const offButton = fragment.querySelector(".lamp-off-button");

        title.textContent = `灯泡 ${lamp.device_id}`;
        meta.textContent = lamp.is_on ? "当前处于开启状态" : "当前处于关闭状态";
        badge.textContent = lamp.is_on ? "已开启" : "已关闭";
        badge.className = `lamp-badge ${lamp.is_on ? "on" : "off"}`;
        preview.style.background = lamp.color_hex;
        rgb.textContent = `${lamp.red}, ${lamp.green}, ${lamp.blue}`;
        intensity.textContent = String(lamp.intensity);

        deviceIdInput.value = String(lamp.device_id);
        colorInput.value = lamp.color_hex;
        intensityInput.value = String(lamp.intensity);
        updateRangeOutput(intensityInput, intensityOutput);

        intensityInput.addEventListener("input", () => updateRangeOutput(intensityInput, intensityOutput));

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const color = hexToRgb(colorInput.value);
            await callApi("/api/lamps/on", {
                device_id: Number.parseInt(deviceIdInput.value, 10),
                intensity: Number.parseInt(intensityInput.value, 10),
                red: color.red,
                green: color.green,
                blue: color.blue,
            });
        });

        offButton.addEventListener("click", async () => {
            await callApi("/api/lamps/off", {
                device_id: Number.parseInt(deviceIdInput.value, 10),
            });
        });

        card.dataset.deviceId = String(lamp.device_id);
        lampGrid.append(fragment);
    });
}

async function fetchStatus(refresh = false) {
    const response = await fetch(`/api/status?refresh=${refresh}`);
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || "状态读取失败");
    }
    return payload.status;
}

async function callApi(url, body) {
    clearMessage();
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
        showMessage(payload.detail || "请求失败", "error");
        return;
    }
    showMessage(payload.message, "info");
    render(payload.status);
}

function render(status) {
    renderSummary(status);
    renderLamps(status);
}

globalIntensity.addEventListener("input", () => updateRangeOutput(globalIntensity, globalIntensityValue));

globalControlForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const color = hexToRgb(document.querySelector("#globalColor").value);
    await callApi("/api/lamps/on", {
        intensity: Number.parseInt(globalIntensity.value, 10),
        red: color.red,
        green: color.green,
        blue: color.blue,
    });
});

turnAllOffButton.addEventListener("click", async () => {
    await callApi("/api/lamps/off", {});
});

refreshStatusButton.addEventListener("click", async () => {
    clearMessage();
    try {
        const status = await fetchStatus(true);
        render(status);
    } catch (error) {
        showMessage(error.message, "error");
    }
});

async function boot() {
    updateRangeOutput(globalIntensity, globalIntensityValue);
    try {
        const status = await fetchStatus(false);
        render(status);
    } catch (error) {
        showMessage(error.message, "error");
    }
}

boot();
setInterval(async () => {
    try {
        const status = await fetchStatus(false);
        render(status);
    } catch (error) {
        showMessage(error.message, "error");
    }
}, 15000);
