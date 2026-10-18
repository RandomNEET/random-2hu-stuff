import { ref, onMounted, onBeforeUnmount } from "vue";

// One mounted check per repost card; retain JSONP, timeout and teardown behavior.
export function useBilibiliAvailability(props) {
  const isRepostDead = ref(false);
  let biliScript = null;
  let biliCallbackName = null;
  let biliTimeout = null;

  const cleanupBiliCheck = () => {
    if (biliTimeout != null) {
      clearTimeout(biliTimeout);
      biliTimeout = null;
    }
    if (biliCallbackName) {
      delete window[biliCallbackName];
      biliCallbackName = null;
    }
    if (biliScript && biliScript.parentNode) {
      biliScript.parentNode.removeChild(biliScript);
      biliScript = null;
    }
  };

  const checkBilibiliUrl = (url) => {
    const bvMatch = url.match(/BV[a-zA-Z0-9]+/);
    if (!bvMatch) return;

    const bvid = bvMatch[0];
    biliCallbackName = `_biliCheck_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    window[biliCallbackName] = (data) => {
      cleanupBiliCheck();
      if (data.code !== 0) {
        isRepostDead.value = true;
      }
    };

    biliScript = document.createElement("script");
    biliScript.src = `https://api.bilibili.com/x/web-interface/view?bvid=${bvid}&jsonp=jsonp&callback=${biliCallbackName}`;
    biliScript.onerror = () => {
      cleanupBiliCheck();
    };
    document.head.appendChild(biliScript);

    biliTimeout = setTimeout(() => {
      cleanupBiliCheck();
    }, 5000);
  };

  onMounted(() => {
    if (props.columnType !== "repost") return;
    if (!props.video.url || !props.video.url.includes("bilibili.com")) return;
    checkBilibiliUrl(props.video.url);
  });

  onBeforeUnmount(() => {
    cleanupBiliCheck();
  });

  return { isRepostDead };
}
