const gatewayGrid = document.querySelector("#gatewayGrid");
const gatewaySummary = document.querySelector("#gatewaySummary");
const connectionBadge = document.querySelector("#connectionBadge");
const selectedGatewayLabel = document.querySelector("#selectedGatewayLabel");
const globalControlHint = document.querySelector("#globalControlHint");
const lampPanelHint = document.querySelector("#lampPanelHint");
const lampGrid = document.querySelector("#lampGrid");
const messageBanner = document.querySelector("#messageBanner");
const globalControlForm = document.querySelector("#globalControlForm");
const turnAllOffButton = document.querySelector("#turnAllOffButton");
const refreshStatusButton = document.querySelector("#refreshStatusButton");
const autoRefreshButton = document.querySelector("#autoRefreshButton");
const manualRefreshButton = document.querySelector("#manualRefreshButton");
const refreshModeHint = document.querySelector("#refreshModeHint");
const gatewayCardTemplate = document.querySelector("#gatewayCardTemplate");
const lampCardTemplate = document.querySelector("#lampCardTemplate");
const globalIntensity = document.querySelector("#globalIntensity");
const globalIntensityValue = document.querySelector("#globalIntensityValue");

const AUTO_REFRESH_INTERVAL_MS = 5000;

let autoRefreshEnabled = true;
let autoRefreshTimer = null;
let selectedGatewayId = null;

function formatDateTime(value) {
    if (!value) {
        return "N/A";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

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

function emptyState(text) {
    const wrapper = document.createElement("div");
    wrapper.className = "empty-state";
    wrapper.textContent = text;
    return wrapper;
}

function setControlsEnabled(enabled) {
    const formControls = globalControlForm.querySelectorAll("input, button");
    formControls.forEach((element) => {
        element.disabled = !enabled;
    });
    turnAllOffButton.disabled = !enabled;
}

function renderGatewayList(gateways) {
    gatewayGrid.replaceChildren();

    if (!gateways.length) {
        gatewayGrid.append(emptyState("暂未发现网关，等待局域网广播。"));
        return;
    }

    gateways.forEach((gateway) => {
        const fragment = gatewayCardTemplate.content.cloneNode(true);
        const card = fragment.querySelector(".gateway-card");
        const title = fragment.querySelector(".gateway-title");
        const host = fragment.querySelector(".gateway-host");
        const dot = fragment.querySelector(".gateway-dot");

        title.textContent = `网关 ${gateway.gateway_id} · ${gateway.lamp_count} 灯`;
        host.textContent = gateway.gateway_host || "未知地址";
        dot.classList.toggle("is-offline", !gateway.connected);
        card.classList.toggle("is-active", gateway.gateway_id === selectedGatewayId);

        card.addEventListener("click", async () => {
            if (selectedGatewayId === gateway.gateway_id) {
                return;
            }
            selectedGatewayId = gateway.gateway_id;
            await refreshDashboard(false);
        });

        gatewayGrid.append(fragment);
    });
}

function renderCurrentGateway(currentGateway) {
    if (!currentGateway) {
        selectedGatewayLabel.textContent = "尚未选中网关";
        globalControlHint.textContent = "请先从上方网关列表中选择一个网关。";
        lampPanelHint.textContent = "请先从上方网关列表中选择一个网关。";
        connectionBadge.textContent = "未选择";
        connectionBadge.className = "badge offline";
        gatewaySummary.replaceChildren(
            summaryItem("网关地址", "未选择"),
            summaryItem("网关 ID", "未选择"),
            summaryItem("灯泡数量", "N/A"),
            summaryItem("全灯关闭", "N/A"),
            summaryItem("最近发现", "N/A"),
            summaryItem("最近通信", "N/A"),
        );
        setControlsEnabled(false);
        return;
    }

    selectedGatewayLabel.textContent = `当前网关 ${currentGateway.gateway_id} · ${currentGateway.gateway_host}`;
    globalControlHint.textContent = `对网关 ${currentGateway.gateway_id} 下的全部灯泡统一设置颜色和亮度。`;
    lampPanelHint.textContent = `按网关 ${currentGateway.gateway_id} 下的灯泡单独查看和控制。`;
    connectionBadge.textContent = currentGateway.connected ? "已连接" : "离线";
    connectionBadge.className = `badge ${currentGateway.connected ? "online" : "offline"}`;
    gatewaySummary.replaceChildren(
        summaryItem("网关地址", currentGateway.gateway_host || "未发现"),
        summaryItem("网关 ID", currentGateway.gateway_id ?? "未发现"),
        summaryItem("灯泡数量", currentGateway.lamp_count),
        summaryItem("全灯关闭", currentGateway.all_off ? "是" : "否"),
        summaryItem("最近发现", formatDateTime(currentGateway.last_seen)),
        summaryItem("最近通信", formatDateTime(currentGateway.last_communication)),
    );
    setControlsEnabled(true);
}

function renderLamps(currentGateway) {
    lampGrid.replaceChildren();

    if (!currentGateway) {
        lampGrid.append(emptyState("请选择一个网关后再查看灯泡。"));
        return;
    }

    if (!currentGateway.lamps.length) {
        lampGrid.append(
            emptyState(currentGateway.connected ? "该网关下未读到灯泡，请尝试刷新。" : "当前网关不可用。"),
        );
        return;
    }

    currentGateway.lamps.forEach((lamp) => {
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
            await callApi(`/api/gateways/${selectedGatewayId}/lamps/on`, {
                device_id: Number.parseInt(deviceIdInput.value, 10),
                intensity: Number.parseInt(intensityInput.value, 10),
                red: color.red,
                green: color.green,
                blue: color.blue,
            });
        });

        offButton.addEventListener("click", async () => {
            await callApi(`/api/gateways/${selectedGatewayId}/lamps/off`, {
                device_id: Number.parseInt(deviceIdInput.value, 10),
            });
        });

        card.dataset.deviceId = String(lamp.device_id);
        lampGrid.append(fragment);
    });
}

function renderDashboard(status) {
    selectedGatewayId = status.selected_gateway_id ?? null;
    renderGatewayList(status.gateways);
    renderCurrentGateway(status.current_gateway);
    renderLamps(status.current_gateway);
}

async function fetchDashboard(refresh = false) {
    const query = new URLSearchParams();
    query.set("refresh", String(refresh));
    if (selectedGatewayId !== null) {
        query.set("gateway_id", String(selectedGatewayId));
    }

    const response = await fetch(`/api/status?${query.toString()}`);
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
    renderDashboard(payload.status);
}

function applyRefreshModeUi() {
    autoRefreshButton.classList.toggle("is-active", autoRefreshEnabled);
    manualRefreshButton.classList.toggle("is-active", !autoRefreshEnabled);
    refreshModeHint.textContent = autoRefreshEnabled
        ? "当前为自动刷新，每 5 秒更新一次。"
        : "当前为手动刷新，仅在点击按钮时更新。";
}

async function refreshDashboard(refresh = false) {
    clearMessage();
    try {
        const status = await fetchDashboard(refresh);
        renderDashboard(status);
    } catch (error) {
        showMessage(error.message, "error");
    }
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        window.clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

function startAutoRefresh() {
    stopAutoRefresh();
    if (!autoRefreshEnabled) {
        return;
    }
    autoRefreshTimer = window.setInterval(async () => {
        try {
            const status = await fetchDashboard(false);
            renderDashboard(status);
        } catch (error) {
            showMessage(error.message, "error");
        }
    }, AUTO_REFRESH_INTERVAL_MS);
}

function setRefreshMode(enabled) {
    autoRefreshEnabled = enabled;
    applyRefreshModeUi();
    startAutoRefresh();
}

globalIntensity.addEventListener("input", () => updateRangeOutput(globalIntensity, globalIntensityValue));

globalControlForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (selectedGatewayId === null) {
        showMessage("请先选择一个网关。", "error");
        return;
    }
    const color = hexToRgb(document.querySelector("#globalColor").value);
    await callApi(`/api/gateways/${selectedGatewayId}/lamps/on`, {
        intensity: Number.parseInt(globalIntensity.value, 10),
        red: color.red,
        green: color.green,
        blue: color.blue,
    });
});

turnAllOffButton.addEventListener("click", async () => {
    if (selectedGatewayId === null) {
        showMessage("请先选择一个网关。", "error");
        return;
    }
    await callApi(`/api/gateways/${selectedGatewayId}/lamps/off`, {});
});

refreshStatusButton.addEventListener("click", async () => {
    await refreshDashboard(true);
});

autoRefreshButton.addEventListener("click", () => {
    setRefreshMode(true);
});

manualRefreshButton.addEventListener("click", () => {
    setRefreshMode(false);
});

async function boot() {
    updateRangeOutput(globalIntensity, globalIntensityValue);
    applyRefreshModeUi();
    setControlsEnabled(false);
    await refreshDashboard(false);
    startAutoRefresh();
}

boot();
