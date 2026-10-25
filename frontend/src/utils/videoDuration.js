export const formatVideoDuration = (duration) => {
  if (duration === null || duration === undefined || duration === "") {
    return "";
  }
  const value = Number(duration);
  if (!Number.isFinite(value) || value < 0) return "";

  const totalSeconds = Math.round(value);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${totalMinutes}:${String(seconds).padStart(2, "0")}`;
};
