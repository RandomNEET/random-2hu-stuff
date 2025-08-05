<template>
  <div class="announcement-page">
    <div class="container">
      <!-- Page header with announcement title and icon -->
      <div class="page-header">
        <v-icon size="48" class="header-icon">mdi-bullhorn</v-icon>
        <h1 class="page-title">公告</h1>
      </div>

      <!-- Latest updates section with timeline layout -->
      <div class="announcement-section">
        <div class="section-header">
          <v-icon class="section-icon">mdi-update</v-icon>
          <h2 class="section-title">最新更新</h2>
        </div>

        <div class="update-timeline">

          <div class="update-item">
            <div class="update-date">2025.08.05</div>
            <div class="update-content">
              <h3>第二次更新</h3>
              <ul>
                <li>功能：支持封面显示</li>
                <li>内容：新收录24位作者，494个视频，287个熟肉，感谢组员的整理与校对</li>
              </ul>
            </div>
          </div>

          <div class="update-item">
            <div class="update-date">2025.08.03</div>
            <div class="update-content">
              <h3>第一次更新</h3>
              <ul>
                <li>功能：视频列表支持按照翻译状态排序，为部分视频添加备注</li>
                <li>内容：新增20位作者，363个视频，感谢群友的整理</li>
              </ul>
            </div>
          </div>

          <div class="update-item">
            <div class="update-date">2025.08.01</div>
            <div class="update-content">
              <h3>🎉 网站正式部署</h3>
              <ul>
                <li>random 2hu stuff 豪华重置版成功部署，可喜可贺</li>
                <li>支持作者浏览、视频查看、搜索功能</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";

const showBackToTop = ref(false);

// Listen to scroll events to control back-to-top button visibility
// Button appears when user scrolls down more than 300px
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300;
};

// Smooth scroll to top functionality
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

// Set up scroll listener when component is mounted
onMounted(() => {
  window.addEventListener("scroll", handleScroll);
});

// Clean up scroll listener when component is unmounted to prevent memory leaks
onUnmounted(() => {
  window.removeEventListener("scroll", handleScroll);
});
</script>

<style scoped>
/* Main announcement page container with Catppuccin gradient background */
.announcement-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1e1e2e 0%, #181825 100%); /* Catppuccin Mocha base colors */
  color: #cdd6f4; /* Catppuccin text color */
  padding: 32px 0;
}

/* Responsive container with max width and centered layout */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Page header styling - centered title section */
.page-header {
  text-align: center;
  margin-bottom: 48px;
  padding: 32px 0;
}

/* Header icon with yellow accent color */
.header-icon {
  color: #f9e2af; /* Catppuccin yellow */
  margin-bottom: 16px;
}

/* Main page title with gradient text shadow effect */
.page-title {
  font-size: 3rem;
  font-weight: bold;
  color: #f9e2af; /* Catppuccin yellow */
  margin-bottom: 8px;
  text-shadow: 0 2px 8px rgba(249, 226, 175, 0.3); /* Subtle glow effect */
}

/* Subtitle text with muted color */
.page-subtitle {
  font-size: 1.2rem;
  color: #a6adc8; /* Catppuccin subtext0 */
  margin: 0;
}

/* Announcement content section with glassmorphism effect */
.announcement-section {
  background: rgba(49, 50, 68, 0.4); /* Semi-transparent surface */
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid rgba(203, 166, 247, 0.2); /* Subtle mauve border */
  backdrop-filter: blur(10px); /* Glassmorphism blur effect */
}

/* Section header with icon and title */
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(203, 166, 247, 0.3); /* Mauve accent line */
}

/* Section icon styling with mauve color */
.section-icon {
  color: #cba6f7; /* Catppuccin mauve */
  font-size: 28px;
}

/* Section title with mauve accent color */
.section-title {
  color: #cba6f7; /* Catppuccin mauve */
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
}

/* Update timeline container - vertical layout for chronological display */
.update-timeline {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Individual update item with card-like appearance and blue left border */
.update-item {
  display: flex;
  gap: 24px;
  padding: 20px;
  background: rgba(30, 30, 46, 0.6); /* Semi-transparent dark background */
  border-radius: 12px;
  border-left: 4px solid #89b4fa; /* Catppuccin blue accent border */
  transition: all 0.3s ease; /* Smooth hover transitions */
}

/* Hover effect for update items - subtle animation */
.update-item:hover {
  background: rgba(30, 30, 46, 0.8); /* Darker background on hover */
  transform: translateX(4px); /* Slight slide animation */
}

/* Date display with blue accent color */
.update-date {
  color: #89b4fa; /* Catppuccin blue */
  font-weight: bold;
  font-size: 0.9rem;
  min-width: 80px; /* Fixed width for consistent alignment */
  padding-top: 4px;
}

/* Update content section with yellow heading */
.update-content h3 {
  color: #f9e2af; /* Catppuccin yellow for emphasis */
  margin-bottom: 8px;
  font-size: 1.1rem;
}

/* Update list styling with proper indentation */
.update-content ul {
  margin: 0;
  padding-left: 20px;
  color: #cdd6f4; /* Standard text color */
}

/* List items with improved readability */
.update-content li {
  margin-bottom: 4px;
  line-height: 1.5; /* Better line spacing for readability */
}

/* Responsive design for tablet and mobile devices */
@media (max-width: 768px) {
  /* Reduced padding for smaller screens */
  .container {
    padding: 0 16px;
  }

  /* Smaller title font size for mobile */
  .page-title {
    font-size: 2rem;
  }

  /* Reduced padding in announcement sections */
  .announcement-section {
    padding: 20px;
  }

  /* Stack update items vertically on mobile */
  .update-item {
    flex-direction: column;
    gap: 12px;
  }

  /* Remove fixed width for date on mobile */
  .update-date {
    min-width: auto;
  }
}

/* Mobile-first responsive design for very small screens */
@media (max-width: 480px) {
  /* Further reduced spacing for small mobile devices */
  .announcement-page {
    padding: 16px 0;
  }

  /* Even smaller title for tiny screens */
  .page-title {
    font-size: 1.5rem;
  }

  /* Smaller subtitle text */
  .page-subtitle {
    font-size: 1rem;
  }

  /* Reduced section title size */
  .section-title {
    font-size: 1.4rem;
  }

  /* Minimal padding and margins for small screens */
  .announcement-section {
    padding: 16px;
    margin-bottom: 20px;
  }
}
</style>
