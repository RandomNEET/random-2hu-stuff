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
          <h2 class="section-title">最近更新</h2>
        </div>

        <div class="update-timeline">
          <div
            v-for="update in announcements"
            :key="update.date"
            class="update-item"
          >
            <div class="update-date">{{ update.date }}</div>
            <div class="update-content">
              <h3 v-if="update.heading">
                <template v-for="(part, index) in update.heading" :key="index">
                  <br v-if="part.break" />
                  <template v-else>{{ part.text }}</template>
                </template>
              </h3>
              <ul>
                <li v-for="(item, index) in update.items" :key="index">
                  <template v-for="(part, partIndex) in item" :key="partIndex">
                    <a
                      v-if="part.href"
                      :href="part.href"
                      target="_blank"
                      rel="noopener noreferrer"
                      >{{ part.text }}</a
                    >
                    <template v-else>{{ part.text }}</template>
                  </template>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { announcements } from "@/data/announcements.js";
</script>

<style scoped>
/* Main announcement page container with Catppuccin gradient background */
.announcement-page {
  min-height: 100vh;
  background: linear-gradient(
    135deg,
    var(--color-base) 0%,
    var(--color-crust) 100%
  ); /* Catppuccin Mocha base colors */
  color: var(--color-text); /* Catppuccin text color */
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

/* AppHeader icon with yellow accent color */
.header-icon {
  color: var(--color-yellow); /* Catppuccin yellow */
  margin-bottom: 16px;
}

/* Main page title with gradient text shadow effect */
.page-title {
  font-size: 3rem;
  font-weight: bold;
  color: var(--color-yellow); /* Catppuccin yellow */
  margin-bottom: 8px;
  text-shadow: 0 2px 8px var(--color-yellow-30); /* Subtle glow effect */
}

/* Subtitle text with muted color */
.page-subtitle {
  font-size: 1.2rem;
  color: var(--color-text-muted); /* Catppuccin subtext0 */
  margin: 0;
}

/* Announcement content section with glassmorphism effect */
.announcement-section {
  background: var(--color-surface-0-40); /* Semi-transparent surface */
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid var(--color-mauve-20); /* Subtle mauve border */
  backdrop-filter: blur(10px); /* Glassmorphism blur effect */
}

/* Section header with icon and title */
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--color-mauve-30); /* Mauve accent line */
}

/* Section icon styling with mauve color */
.section-icon {
  color: var(--color-mauve); /* Catppuccin mauve */
  font-size: 28px;
}

/* Section title with mauve accent color */
.section-title {
  color: var(--color-mauve); /* Catppuccin mauve */
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
  background: var(--color-base-60); /* Semi-transparent dark background */
  border-radius: 12px;
  border-left: 4px solid var(--color-blue); /* Catppuccin blue accent border */
  transition: all 0.3s ease; /* Smooth hover transitions */
}

/* Hover effect for update items - subtle animation */
.update-item:hover {
  background: var(--color-base-80); /* Darker background on hover */
  transform: translateX(4px); /* Slight slide animation */
}

/* Date display with blue accent color */
.update-date {
  color: var(--color-blue); /* Catppuccin blue */
  font-weight: bold;
  font-size: 0.9rem;
  min-width: 80px; /* Fixed width for consistent alignment */
  padding-top: 4px;
}

/* Update content section with yellow heading */
.update-content h3 {
  color: var(--color-yellow); /* Catppuccin yellow for emphasis */
  margin-bottom: 8px;
  font-size: 1.1rem;
}

/* Update list styling with proper indentation */
.update-content ul {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text); /* Standard text color */
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
