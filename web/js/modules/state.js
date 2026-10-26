/**
 * XForwarder - Reactive State Store
 */

export let currentRules = [];
export let lastRuntime = {};
export let lastTrafficData = null;
export let lastLatestLoss = {};

export function setCurrentRules(rules) {
    currentRules = Array.isArray(rules) ? rules : [];
    state.currentRules = currentRules;
}

export function setLastRuntime(runtime) {
    lastRuntime = runtime && typeof runtime === "object" ? runtime : {};
    state.lastRuntime = lastRuntime;
}

export function setLastTrafficData(traffic) {
    lastTrafficData = traffic;
    state.lastTrafficData = traffic;
}

export function setLastLatestLoss(loss) {
    lastLatestLoss = loss && typeof loss === "object" ? loss : {};
    state.lastLatestLoss = lastLatestLoss;
}

export const state = {
    get currentRules() { return currentRules; },
    set currentRules(val) { currentRules = val; },
    get lastRuntime() { return lastRuntime; },
    set lastRuntime(val) { lastRuntime = val; },
    get lastTrafficData() { return lastTrafficData; },
    set lastTrafficData(val) { lastTrafficData = val; },
    get lastLatestLoss() { return lastLatestLoss; },
    set lastLatestLoss(val) { lastLatestLoss = val; },
    currentTrafficEntity: "all:all",
    currentTrafficPeriod: "24h",
    pollTimer: null,
    searchQuery: "",
    activeFilter: "all",
    currentViewMode: localStorage.getItem("xfwd_rules_view") || "cards",
    currentSort: localStorage.getItem("xfwd_rules_sort") || "port_asc",
    previousPortVal: "",
    confirmResolve: null,
    pendingOverrides: new Set(),
    listeners: new Set(),

    subscribe(fn) {
        this.listeners.add(fn);
        return () => this.listeners.delete(fn);
    },

    notify(event, payload) {
        this.listeners.forEach(fn => {
            try { fn(event, payload); } catch (e) { console.error(e); }
        });
    }
};
