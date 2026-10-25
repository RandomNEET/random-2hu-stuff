export function useSortControl(
  props,
  emit,
  { fieldProp = "sortBy", defaultOrder = () => "asc" } = {},
) {
  return (field) => {
    const sortOrder =
      props[fieldProp] === field
        ? props.sortOrder === "asc"
          ? "desc"
          : "asc"
        : defaultOrder(field);
    emit(`update:${fieldProp}`, field);
    emit("update:sortOrder", sortOrder);
    emit("sort-change", { [fieldProp]: field, sortOrder });
  };
}
