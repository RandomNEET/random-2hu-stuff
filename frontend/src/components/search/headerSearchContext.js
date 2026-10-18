import { inject, provide } from "vue";

const headerSearchKey = Symbol("header-search");

// AppHeader owns one form and its lifecycle; desktop and mobile are views of that state.
export const provideHeaderSearch = state => provide(headerSearchKey, state);

export function useHeaderSearchContext() {
  const state = inject(headerSearchKey);
  if (!state) throw new Error("AppHeader search components must be rendered inside AppHeader");
  return state;
}
