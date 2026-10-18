import { createRenderer, h } from 'vue';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useBilibiliAvailability } from '../../../frontend/src/composables/useBilibiliAvailability.js';

const renderer = createRenderer({
  createElement: type => ({type, children: []}),
  insert: (node, parent) => parent.children.push(node),
  remove: () => {},
  setElementText: () => {},
  patchProp: () => {},
  parentNode: () => null,
  nextSibling: () => null,
});
let scripts;
let mounted;
beforeEach(() => {
  vi.useFakeTimers();
  scripts = [];
  mounted = [];
  const head = {
    appendChild(script) { script.parentNode = head; scripts.push(script); },
    removeChild(script) { scripts.splice(scripts.indexOf(script), 1); script.parentNode = null; },
  };
  vi.stubGlobal('window', {});
  vi.stubGlobal('document', {head, createElement: () => ({})});
});
afterEach(() => {
  mounted.forEach(app => app.unmount());
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
function mount(columnType = 'repost', url = 'https://bilibili.com/video/BV123') {
  let state;
  const app = renderer.createApp({
    setup() {
      state = useBilibiliAvailability({columnType, video: {url}});
      return () => h('div');
    },
  });
  app.mount({children: []});
  mounted.push(app);
  return {app, state};
}
function callback() {
  return new URL(scripts[0].src).searchParams.get('callback');
}

it('checks once on mount and cleans the callback, script and timer on unmount', () => {
  const {app, state} = mount();
  const name = callback();
  expect(scripts).toHaveLength(1);
  expect(state.isRepostDead.value).toBe(false);
  app.unmount();
  mounted = [];
  expect(scripts).toHaveLength(0);
  expect(window[name]).toBeUndefined();
  expect(vi.getTimerCount()).toBe(0);
});

it('marks failed API responses dead and removes the JSONP resources', () => {
  const {state} = mount();
  const name = callback();
  window[name]({code: -404});
  expect(state.isRepostDead.value).toBe(true);
  expect(scripts).toHaveLength(0);
  expect(window[name]).toBeUndefined();
  expect(vi.getTimerCount()).toBe(0);
});

it('does not mark network failures or timeouts as dead', () => {
  const first = mount();
  scripts[0].onerror();
  expect(first.state.isRepostDead.value).toBe(false);
  const second = mount();
  const name = callback();
  vi.advanceTimersByTime(5000);
  expect(second.state.isRepostDead.value).toBe(false);
  expect(scripts).toHaveLength(0);
  expect(window[name]).toBeUndefined();
});

it('skips original cards, non-Bilibili links and missing BV identifiers', () => {
  mount('original');
  mount('repost', 'https://youtube.com/watch?v=1');
  mount('repost', 'https://bilibili.com/video/av123');
  mount('repost', '');
  expect(scripts).toHaveLength(0);
  expect(vi.getTimerCount()).toBe(0);
});
