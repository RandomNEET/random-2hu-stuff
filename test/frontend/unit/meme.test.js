import { createRenderer, h, nextTick } from "vue";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useMemeWidget } from "../../../frontend/src/composables/useMemeWidget.js";

const renderer = createRenderer({
  createElement: () => ({}),
  insert: () => {},
  remove: () => {},
  setElementText: () => {},
  patchProp: () => {},
  parentNode: () => null,
  nextSibling: () => null,
});
let apps;
let storage;
let events;
beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(Math, "random").mockReturnValue(0.4);
  apps = [];
  storage = new Map();
  events = new EventTarget();
  vi.stubGlobal("localStorage", {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
  });
  vi.stubGlobal("document", {
    hidden: false,
    addEventListener: (...args) => events.addEventListener(...args),
    removeEventListener: (...args) => events.removeEventListener(...args),
  });
});
afterEach(() => {
  apps.forEach((app) => app.unmount());
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
function mount(images = ["a.gif", "b.gif", "c.gif"]) {
  let state;
  const app = renderer.createApp({
    setup() {
      state = useMemeWidget(images);
      return () => h("div");
    },
  });
  app.mount({});
  apps.push(app);
  return state;
}

it("rotates without consecutive repeats and stops on close and unmount", async () => {
  const state = mount();
  for (let i = 0; i < 10; i++) {
    const previous = state.current.value;
    vi.advanceTimersByTime(30000);
    expect(state.current.value).not.toBe(previous);
  }
  state.visible.value = false;
  await nextTick();
  expect(vi.getTimerCount()).toBe(0);
  state.visible.value = true;
  await nextTick();
  expect(vi.getTimerCount()).toBe(1);
  apps.pop().unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it("persists both switches and tolerates corrupt or blocked storage", async () => {
  const state = mount();
  state.visible.value = false;
  state.autoRotate.value = false;
  await nextTick();
  const restored = mount();
  expect(restored.visible.value).toBe(false);
  expect(restored.autoRotate.value).toBe(false);
  storage.set("memeWidget-settings", "invalid");
  expect(mount().visible.value).toBe(true);
  vi.stubGlobal("localStorage", {
    getItem() {
      throw Error("blocked");
    },
    setItem() {
      throw Error("blocked");
    },
  });
  const blocked = mount();
  blocked.autoRotate.value = false;
  await nextTick();
  expect(blocked.autoRotate.value).toBe(false);
});

it("chooses another image on every reopen while preserving the rotation preference", async () => {
  const state = mount();
  state.autoRotate.value = false;
  await nextTick();
  for (let i = 0; i < 5; i++) {
    const previous = state.current.value;
    state.visible.value = false;
    await nextTick();
    expect(state.current.value).toBe(previous);
    state.visible.value = true;
    await nextTick();
    expect(state.current.value).not.toBe(previous);
    expect(state.autoRotate.value).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  }
});

it("pauses while hidden and starts a fresh interval on return", async () => {
  const state = mount();
  document.hidden = true;
  events.dispatchEvent(new Event("visibilitychange"));
  await nextTick();
  expect(vi.getTimerCount()).toBe(0);
  const previous = state.current.value;
  document.hidden = false;
  events.dispatchEvent(new Event("visibilitychange"));
  await nextTick();
  vi.advanceTimersByTime(29999);
  expect(state.current.value).toBe(previous);
  vi.advanceTimersByTime(1);
  expect(state.current.value).not.toBe(previous);
});

it("handles empty, single and failed images without useless timers", async () => {
  expect(mount([]).current.value).toBe(null);
  expect(mount(["single.gif"]).current.value).toBe("single.gif");
  expect(vi.getTimerCount()).toBe(0);
  const state = mount(["a.gif", "b.gif"]);
  const failed = state.current.value;
  state.imageFailed();
  await nextTick();
  expect(state.current.value).not.toBe(failed);
  expect(vi.getTimerCount()).toBe(0);
  state.imageFailed();
  expect(state.current.value).toBe(null);
});

it("allows manual randomization with rotation off and resets the interval", async () => {
  const state = mount();
  state.autoRotate.value = false;
  await nextTick();
  const first = state.current.value;
  state.randomize();
  expect(state.current.value).not.toBe(first);
  expect(vi.getTimerCount()).toBe(0);
  state.autoRotate.value = true;
  await nextTick();
  vi.advanceTimersByTime(20000);
  state.randomize();
  const current = state.current.value;
  vi.advanceTimersByTime(29999);
  expect(state.current.value).toBe(current);
  vi.advanceTimersByTime(1);
  expect(state.current.value).not.toBe(current);
});

it("draws a new 10–60 second delay after each rotation", () => {
  Math.random.mockReturnValue(0);
  const state = mount();
  const first = state.current.value;
  vi.advanceTimersByTime(9999);
  expect(state.current.value).toBe(first);
  Math.random.mockReturnValue(0.999999);
  vi.advanceTimersByTime(1);
  const second = state.current.value;
  expect(second).not.toBe(first);
  vi.advanceTimersByTime(59999);
  expect(state.current.value).toBe(second);
  Math.random.mockReturnValue(0);
  vi.advanceTimersByTime(1);
  const third = state.current.value;
  expect(third).not.toBe(second);
  vi.advanceTimersByTime(9999);
  expect(state.current.value).toBe(third);
  vi.advanceTimersByTime(1);
  expect(state.current.value).not.toBe(third);
  expect(vi.getTimerCount()).toBe(1);
});
