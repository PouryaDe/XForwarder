/**
 * XForwarder - Reactive State Store
 */

export const state = {
    currentRules: [],
    lastRuntime: {},
    lastTrafficData: null,
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
