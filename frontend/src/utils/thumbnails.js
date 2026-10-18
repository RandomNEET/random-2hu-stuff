export const needsSpecialAttributes = (imageUrl) => {
  if (!imageUrl) return false;
  const lowerUrl = imageUrl.toLowerCase();
  return lowerUrl.includes("hdslb.com");
};

export const handleThumbnailLoad = (event) => {
  event.target.style.opacity = "1";
  const loadingElement = event.target.previousElementSibling;
  if (
    loadingElement &&
    loadingElement.classList.contains("thumbnail-loading")
  ) {
    loadingElement.style.display = "none";
  }
};

export const handleThumbnailError = (event) => {
  event.target.style.display = "none";
  const loadingElement = event.target.previousElementSibling;
  if (
    loadingElement &&
    loadingElement.classList.contains("thumbnail-loading")
  ) {
    loadingElement.innerHTML = '<span class="error-text">封面加载失败</span>';
    loadingElement.style.color = "var(--color-red)";
  }
};
