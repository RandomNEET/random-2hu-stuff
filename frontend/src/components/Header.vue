<template>
  <v-app-bar
    app
    elevation="4"
    class="app-header"
    height="70"
  >
    <v-container class="d-flex align-center">
      <!-- Site title -->
      <div class="site-title" @click="$router.push('/')" style="cursor: pointer">
        <h1 class="title-text">random 2hu stuff</h1>
      </div>

      <v-spacer></v-spacer>

      <!-- Desktop search bar with dropdown -->
      <div class="search-container" ref="searchContainer">
        <div class="search-wrapper">
          <v-text-field
            v-model="searchForm.query"
            placeholder="搜索作者或视频..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            hide-details
            class="search-field desktop-search"
            @focus="handleSearchFocus"
            @click="handleSearchClick"
            @input="handleSearchInput"
            @keyup.enter="performSearch"
          />
          
          <!-- Search Panel Dropdown -->
          <div v-if="showSearchPanel" class="search-panel" @click.stop>
            <!-- Search Type Selection -->
            <div class="search-type-section">
              <v-btn-toggle
                v-model="searchForm.type"
                color="primary"
                mandatory
                class="search-type-toggle"
              >
                <v-btn value="videos" class="search-type-btn">
                  <v-icon size="small" class="mr-1">mdi-video</v-icon>
                  视频
                </v-btn>
                <v-btn value="authors" class="search-type-btn">
                  <v-icon size="small" class="mr-1">mdi-account</v-icon>
                  作者
                </v-btn>
              </v-btn-toggle>
            </div>

            <!-- Video Filters -->
            <div v-if="searchForm.type === 'videos'" class="filters-section">
              <!-- Author Filter -->
              <div class="filter-row">
                <label class="filter-label">作者</label>
                <v-combobox
                  v-model="searchForm.filters.authorInput"
                  :items="authorOptions"
                  item-title="name"
                  item-value="name"
                  placeholder="输入或选择作者"
                  variant="outlined"
                  density="compact"
                  hide-details
                  clearable
                  auto-select-first
                  :menu-props="{ closeOnContentClick: true, maxHeight: 200 }"
                  class="filter-input"
                  @update:model-value="handleAuthorSelection"
                  @blur="handleAuthorBlur"
                />
              </div>

              <!-- Translation Status Filter -->
              <div class="filter-row">
                <label class="filter-label">翻译状态</label>
                <v-select
                  v-model="searchForm.filters.translationStatus"
                  :items="translationOptions"
                  placeholder="选择翻译状态"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="filter-input"
                />
              </div>

              <!-- Date Range Filter -->
              <div class="filter-row">
                <label class="filter-label">时间范围</label>
                <div class="date-range-container">
                  <v-text-field
                    v-model="searchForm.filters.dateFrom"
                    type="date"
                    placeholder="开始日期"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="date-input"
                  />
                  <span class="date-separator">至</span>
                  <v-text-field
                    v-model="searchForm.filters.dateTo"
                    type="date"
                    placeholder="结束日期"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="date-input"
                  />
                </div>
              </div>
            </div>

            <!-- Search Limit -->
            <div class="limit-section">
              <div class="limit-header">
                <span class="limit-label">搜索数量</span>
                <span class="limit-value">{{ searchForm.limit }}</span>
              </div>
              <v-slider
                v-model="searchForm.limit"
                :min="10"
                :max="searchForm.type === 'videos' ? 500 : 200"
                :step="10"
                color="#89b4fa"
                track-color="#45475a"
                thumb-color="#89b4fa"
                hide-details
              />
            </div>

            <!-- Action Buttons -->
            <div class="search-actions">
              <v-btn
                size="small"
                variant="outlined"
                color="surface-variant"
                @click="resetForm"
                class="action-btn reset-btn"
              >
                重置
              </v-btn>
              <v-btn
                size="small"
                color="primary"
                variant="flat"
                @click="performSearch"
                :disabled="!searchForm.query.trim()"
                class="action-btn search-btn"
              >
                搜索
              </v-btn>
            </div>
          </div>
        </div>
      </div>

      <v-spacer></v-spacer>

      <!-- Navigation menu -->
      <div class="nav-menu">
        <!-- Mobile search toggle button -->
        <v-btn
          icon
          class="mobile-search-btn"
          @click="showMobileSearch = !showMobileSearch"
        >
          <v-icon>mdi-magnify</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/')"
        >
          <v-icon>mdi-home</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/announcement')"
        >
          <v-icon>mdi-bullhorn</v-icon>
        </v-btn>
        
        <v-btn
          icon
          class="nav-button"
          @click="$router.push('/about')"
        >
          <v-icon>mdi-information</v-icon>
        </v-btn>
      </div>
    </v-container>

    <!-- Mobile search popup overlay -->
    <div v-if="showMobileSearch" class="mobile-search-overlay" @click="showMobileSearch = false">
      <div class="mobile-search-popup" @click.stop>
        <!-- Close button -->
        <v-btn
          icon
          class="mobile-close-btn"
          @click="showMobileSearch = false"
        >
          <v-icon>mdi-close</v-icon>
        </v-btn>
        
        <!-- Mobile search title -->
        <h3 class="mobile-search-title">搜索</h3>
        
        <!-- Search input -->
        <v-text-field
          v-model="searchForm.query"
          placeholder="搜索作者或视频..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          hide-details
          class="mobile-search-input"
          @keyup.enter="handleMobileSearch"
          autofocus
        />
        
        <!-- Search type selection -->
        <div class="mobile-search-types">
          <v-btn
            :variant="searchForm.type === 'videos' ? 'flat' : 'outlined'"
            :color="searchForm.type === 'videos' ? 'primary' : 'default'"
            class="mobile-type-btn"
            @click="searchForm.type = 'videos'"
          >
            <v-icon left>mdi-video</v-icon>
            视频
          </v-btn>
          <v-btn
            :variant="searchForm.type === 'authors' ? 'flat' : 'outlined'"
            :color="searchForm.type === 'authors' ? 'primary' : 'default'"
            class="mobile-type-btn"
            @click="searchForm.type = 'authors'"
          >
            <v-icon left>mdi-account</v-icon>
            作者
          </v-btn>
        </div>
        
        <!-- Filters (only show for video search) -->
        <div v-if="searchForm.type === 'videos'" class="mobile-filters">
          <h4 class="mobile-filter-title">筛选条件</h4>
          
          <!-- Author filter -->
          <div class="mobile-filter-item">
            <label class="mobile-filter-label">作者</label>
            <v-combobox
              v-model="searchForm.filters.authorInput"
              :items="authorOptions"
              item-title="name"
              item-value="name"
              placeholder="输入或选择作者"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              auto-select-first
              :menu-props="{ closeOnContentClick: true, maxHeight: 200 }"
              class="mobile-filter-input"
              @update:model-value="handleMobileAuthorSelection"
              @blur="handleMobileAuthorBlur"
            />
          </div>

          <!-- Translation Status Filter -->
          <div class="mobile-filter-item">
            <label class="mobile-filter-label">翻译状态</label>
            <v-select
              v-model="searchForm.filters.translationStatus"
              :items="translationOptions"
              item-title="title"
              item-value="value"
              variant="outlined"
              density="compact"
              hide-details
              class="mobile-filter-input"
              @update:model-value="handleFilterChange"
            />
          </div>

          <!-- Date Range Filter -->
          <div class="mobile-filter-item">
            <label class="mobile-filter-label">时间范围</label>
            <div class="mobile-date-range">
              <v-text-field
                v-model="searchForm.filters.dateFrom"
                type="date"
                variant="outlined"
                density="compact"
                hide-details
                class="mobile-date-input"
              />
              <span class="mobile-date-separator">至</span>
              <v-text-field
                v-model="searchForm.filters.dateTo"
                type="date"
                variant="outlined"
                density="compact"
                hide-details
                class="mobile-date-input"
              />
            </div>
          </div>
        </div>

        <!-- Search Limit (show for both video and author search) -->
        <div class="mobile-filter-item">
          <label class="mobile-filter-label">搜索数量</label>
          <div class="mobile-limit-container">
            <v-slider
              v-model="searchForm.limit"
              :min="10"
              :max="searchForm.type === 'videos' ? 500 : 200"
              :step="10"
              variant="outlined"
              density="compact"
              hide-details
              class="mobile-limit-slider"
            />
            <span class="mobile-limit-value">{{ searchForm.limit }}</span>
          </div>
        </div>
        
        <!-- Action buttons -->
        <div class="mobile-actions">
          <v-btn
            variant="outlined"
            class="mobile-reset-btn"
            @click="resetMobileSearch"
          >
            重置
          </v-btn>
          <v-btn
            variant="flat"
            color="primary"
            class="mobile-search-btn"
            @click="handleMobileSearch"
          >
            搜索
          </v-btn>
        </div>
      </div>
    </div>
  </v-app-bar>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { API_URLS } from '@/config/api.js';

const router = useRouter();
const searchQuery = ref('');
const showMobileSearch = ref(false);
const showSearchPanel = ref(false);
const searchContainer = ref(null);

// Search form data
const searchForm = ref({
  query: '',
  type: 'videos', // 'videos' or 'authors'
  limit: 100,
  filters: {
    authorInput: '',
    translationStatus: 'all',
    dateFrom: '',
    dateTo: ''
  }
});

// Author options for filter (loaded from API)
const authorOptions = ref([]);

// Translation status options
const translationOptions = [
  { title: '全部', value: 'all' },
  { title: '中文内嵌', value: '1' },
  { title: 'CC字幕', value: '2' },
  { title: '弹幕翻译', value: '3' },
  { title: '无需翻译', value: '4' },
  { title: '暂无翻译', value: '5' }
];

// Load authors for filter dropdown
const loadAuthors = async () => {
  try {
    const response = await fetch(API_URLS.AUTHORS);
    const authors = await response.json();
    authorOptions.value = authors.map(author => ({
      id: author.id,
      name: author.yt_name || author.nico_name || author.twitter_name || 'Unknown'
    }));
  } catch (error) {
    console.error('Failed to load authors:', error);
  }
};

// Watch for search type changes to adjust limit
watch(() => searchForm.value.type, (newType) => {
  if (newType === 'authors' && searchForm.value.limit > 200) {
    searchForm.value.limit = 200;
  }
});

// Watch for route changes to handle panel state
watch(() => router.currentRoute.value, () => {
  // Close search panel when route changes (e.g., after search)
  if (showSearchPanel.value) {
    // Use nextTick to ensure the navigation completes first
    nextTick(() => {
      showSearchPanel.value = false;
    });
  }
});

// Close search panel when clicking outside
const handleClickOutside = (event) => {
  if (searchContainer.value && !searchContainer.value.contains(event.target)) {
    // Check if clicked element is part of a dropdown menu or overlay
    const isDropdownClick = event.target.closest('.v-overlay, .v-menu, .v-select__content, .v-combobox__content, .v-list, .v-list-item, .v-overlay__content, [role="listbox"], [role="option"]');
    // Also check if the target has any Japanese/Chinese characters (additional safety)
    const hasAsianText = event.target.textContent && /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]/.test(event.target.textContent);
    const isComboboxItem = event.target.closest('.v-combobox') !== null;
    
    if (!isDropdownClick && !(hasAsianText && isComboboxItem)) {
      showSearchPanel.value = false;
    }
  }
};

// Reset search form to defaults
const resetForm = () => {
  searchForm.value.type = 'videos';
  searchForm.value.limit = 100;
  searchForm.value.filters = {
    authorInput: '',
    translationStatus: 'all',
    dateFrom: '',
    dateTo: ''
  };
};

// Find author ID by name for searching
const findAuthorIdByName = (authorName) => {
  if (!authorName) return null;
  // 精确匹配作者名称
  const author = authorOptions.value.find(a => a.name === authorName);
  if (author) {
    return author.id;
  }
  // 如果没有精确匹配，尝试模糊匹配
  const fuzzyAuthor = authorOptions.value.find(a => {
    const name = a.name.toLowerCase();
    const input = authorName.toLowerCase();
    return name.includes(input) || input.includes(name);
  });
  return fuzzyAuthor ? fuzzyAuthor.id : null;
};

// Perform search with filters
const performSearch = () => {
  if (!searchForm.value.query.trim()) return;
  
  const query = {
    q: searchForm.value.query.trim(),
    type: searchForm.value.type,
    limit: searchForm.value.limit
  };

  // Add video-specific filters
  if (searchForm.value.type === 'videos') {
    // Handle author input - convert author name to ID
    if (searchForm.value.filters.authorInput) {
      const authorId = findAuthorIdByName(searchForm.value.filters.authorInput);
      if (authorId) {
        query.author = authorId;
        console.log('Found author ID:', authorId, 'for name:', searchForm.value.filters.authorInput);
      } else {
        console.warn('Author not found:', searchForm.value.filters.authorInput);
        // 如果找不到作者ID，不添加作者筛选条件
      }
    }
    if (searchForm.value.filters.translationStatus !== 'all') {
      query.translationStatus = searchForm.value.filters.translationStatus;
    }
    if (searchForm.value.filters.dateFrom) {
      query.dateFrom = searchForm.value.filters.dateFrom;
    }
    if (searchForm.value.filters.dateTo) {
      query.dateTo = searchForm.value.filters.dateTo;
    }
  }

  console.log('Final search query:', query); // 调试信息

  // Navigate to search page with query parameters
  router.push({
    path: '/search',
    query
  });

  // Close panel
  showSearchPanel.value = false;
};

const handleMobileSearch = () => {
  if (!searchForm.value.query.trim()) return;
  
  const query = {
    q: searchForm.value.query.trim(),
    type: searchForm.value.type,
    limit: searchForm.value.limit
  };

  // Add video-specific filters
  if (searchForm.value.type === 'videos') {
    // Handle author input - convert author name to ID
    if (searchForm.value.filters.authorInput) {
      const authorId = findAuthorIdByName(searchForm.value.filters.authorInput);
      if (authorId) {
        query.author = authorId;
      }
    }
    if (searchForm.value.filters.translationStatus !== 'all') {
      query.translationStatus = searchForm.value.filters.translationStatus;
    }
    if (searchForm.value.filters.dateFrom) {
      query.dateFrom = searchForm.value.filters.dateFrom;
    }
    if (searchForm.value.filters.dateTo) {
      query.dateTo = searchForm.value.filters.dateTo;
    }
  }

  // Navigate to search page
  router.push({
    path: '/search',
    query
  });

  // Close mobile search
  showMobileSearch.value = false;
};

const resetMobileSearch = () => {
  searchForm.value = {
    query: '',
    type: 'videos',
    limit: 100,
    filters: {
      authorInput: '',
      translationStatus: 'all',
      dateFrom: '',
      dateTo: ''
    }
  };
};

// Handle search input focus event
const handleSearchFocus = () => {
  showSearchPanel.value = true;
};

// Handle search input click event
const handleSearchClick = () => {
  showSearchPanel.value = true;
};

// Handle search input change event
const handleSearchInput = () => {
  showSearchPanel.value = true;
};

// Handle author selection for desktop
const handleAuthorSelection = (value) => {
  console.log('Desktop author selection changed:', value);
  searchForm.value.filters.authorInput = value;
  // If value is selected from dropdown (not manually typed), it should take immediate effect
  if (value && typeof value === 'string' && authorOptions.value.some(author => author.name === value)) {
    // Value was selected from dropdown, close menu and make it active immediately
    nextTick(() => {
      // Force close any open menus
      const combobox = searchContainer.value?.querySelector('.v-combobox');
      if (combobox) {
        const input = combobox.querySelector('input');
        if (input) {
          input.blur();
        }
      }
    });
  }
};

// Handle desktop author blur event
const handleAuthorBlur = (event) => {
  const value = event.target.value;
  console.log('Desktop author blur event:', value);
  searchForm.value.filters.authorInput = value;
};

// Handle author selection for mobile
const handleMobileAuthorSelection = (value) => {
  console.log('Mobile author selection changed:', value);
  searchForm.value.filters.authorInput = value;
  // If value is selected from dropdown, close menu immediately
  if (value && typeof value === 'string' && authorOptions.value.some(author => author.name === value)) {
    nextTick(() => {
      // Force close any open menus
      const mobilePopup = document.querySelector('.mobile-search-popup');
      if (mobilePopup) {
        const combobox = mobilePopup.querySelector('.v-combobox');
        if (combobox) {
          const input = combobox.querySelector('input');
          if (input) {
            input.blur();
          }
        }
      }
    });
  }
};

// Handle mobile author blur event
const handleMobileAuthorBlur = (event) => {
  const value = event.target.value;
  console.log('Mobile author blur event:', value);
  searchForm.value.filters.authorInput = value;
};

// Setup click outside listener
watch(showSearchPanel, (newValue) => {
  if (newValue) {
    nextTick(() => {
      // Calculate panel position based on search input
      const searchInput = searchContainer.value?.querySelector('.v-field');
      if (searchInput) {
        const rect = searchInput.getBoundingClientRect();
        const panel = searchContainer.value?.querySelector('.search-panel');
        if (panel) {
          panel.style.top = `${rect.bottom + 8}px`;
          panel.style.left = `${rect.left}px`;
          panel.style.width = `${Math.max(400, rect.width)}px`;
        }
      }
      document.addEventListener('click', handleClickOutside);
    });
  } else {
    document.removeEventListener('click', handleClickOutside);
  }
});

// Load data on component mount
onMounted(() => {
  loadAuthors();
});

// Cleanup on unmount
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* Header with Catppuccin Mocha theme */
.app-header {
  background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%) !important; /* Catppuccin Mocha gradient */
  border-bottom: 2px solid #45475a; /* Catppuccin Mocha Surface1 */
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.app-header * {
  font-family: 'JetBrains Mono', 'JetBrainsMono Nerd Font', monospace !important;
}

.site-title {
  transition: transform 0.2s ease;
  flex-shrink: 0; /* Prevent title from being compressed */
}

.site-title:hover {
  transform: scale(1.05);
}

.title-text {
  color: #f9e2af; /* Catppuccin Mocha Yellow */
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.search-container {
  max-width: 400px;
  width: 100%;
  position: relative;
  overflow: visible;
  z-index: 1000;
  margin: 0 auto;
}

.mobile-search-container {
  display: none; /* Hidden by default for mobile search */
  width: 100px;
  margin-right: 8px;
}

.mobile-search-btn {
  display: none !important; /* Ensure hidden on desktop; override Vuetify */
  color: #cdd6f4 !important;
  transition: all 0.2s ease;
  border: 1px solid #585b70 !important; /* Add border for normal state */
  border-radius: 50% !important; /* Keep shape perfectly circular when shown */
}

.mobile-search-btn:hover {
  background-color: rgba(137, 180, 250, 0.1) !important;
  color: #89b4fa !important;
  border-color: #89b4fa !important; /* Change border color on hover */
}

.desktop-search {
  display: block; /* Show desktop search by default */
}

.mobile-search {
  display: none; /* Hide mobile search by default */
}

.search-field :deep(.v-field) {
  background-color: #45475a !important; /* Catppuccin Mocha Surface1 */
  border-radius: 12px;
}

.search-field :deep(.v-field__input) {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
}

.search-field :deep(.v-field__outline) {
  border-color: #585b70 !important; /* Catppuccin Mocha Surface2 */
}

.search-field :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important; /* Catppuccin Mocha Blue */
}

.search-field :deep(.v-field__prepend-inner .v-icon) {
  color: #a6adc8 !important; /* Catppuccin Mocha Subtext0 */
}

.search-field :deep(::placeholder) {
  color: #6c7086 !important; /* Catppuccin Mocha Overlay0 */
}

.nav-menu {
  display: flex;
  gap: 8px;
  flex-shrink: 0; /* Prevent compression on small screens */
  align-items: center; /* Ensure buttons are vertically centered */
}

.nav-button {
  color: #cdd6f4 !important; /* Catppuccin Mocha Text */
  transition: all 0.2s ease;
  border: 1px solid #585b70 !important; /* Add border for normal state */
}

.nav-button:hover {
  background-color: rgba(137, 180, 250, 0.1) !important; /* Catppuccin Mocha Blue with opacity */
  color: #89b4fa !important; /* Catppuccin Mocha Blue */
  border-color: #89b4fa !important; /* Change border color on hover */
}

/* Mobile search popup overlay styles */
.mobile-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
}

.mobile-search-popup {
  background: #1e1e2e;
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 400px;
  max-height: 90vh;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  border: 1px solid #45475a;
  position: relative;
  overflow-y: auto;
  margin-top: 60px;
}

.mobile-close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  color: #cdd6f4 !important;
  z-index: 10;
}

.mobile-close-btn:hover {
  background-color: rgba(243, 139, 168, 0.1) !important;
  color: #f38ba8 !important;
}

.mobile-search-title {
  color: #cdd6f4;
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 20px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
}

.mobile-search-input {
  margin-bottom: 20px;
}

.mobile-search-types {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.mobile-type-btn {
  flex: 1;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
}

.mobile-filters {
  margin-bottom: 24px;
}

.mobile-filter-title {
  color: #cdd6f4;
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 16px;
  font-family: 'JetBrains Mono', monospace;
}

.mobile-filter-item {
  margin-bottom: 16px;
}

.mobile-filter-label {
  display: block;
  color: #a6adc8;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 8px;
  font-family: 'JetBrains Mono', monospace;
}

.mobile-filter-input {
  width: 100%;
}

.mobile-date-range {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-date-input {
  flex: 1;
}

.mobile-date-separator {
  color: #a6adc8;
  font-size: 0.9rem;
  font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
}

.mobile-limit-container {
  display: flex;
  align-items: center;
  gap: 16px;
}

.mobile-limit-slider {
  flex: 1;
}

.mobile-limit-value {
  color: #89b4fa;
  font-size: 0.9rem;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  min-width: 40px;
  text-align: center;
  background: rgba(137, 180, 250, 0.1);
  border-radius: 8px;
  padding: 4px 8px;
  border: 1px solid rgba(137, 180, 250, 0.2);
}

.mobile-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  align-items: center;
}

.mobile-reset-btn,
.mobile-search-btn {
  flex: 1;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 500;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive design */
@media (max-width: 960px) {
  .title-text {
    font-size: 1.2rem;
  }
  
  .search-container {
    display: none; /* Hide desktop search bar */
  }
  
  .desktop-search {
    display: none !important; /* Hide desktop search */
  }
  
  .mobile-search-btn {
    display: flex !important; /* Show mobile search button */
    width: 40px !important; /* Ensure square dimensions */
    height: 40px !important;
    min-width: 40px !important;
    border-radius: 50% !important; /* Guarantee circle across tablet widths */
  }
}

@media (max-width: 600px) {
  .app-header :deep(.v-container) {
    padding: 0 12px !important; /* Appropriate padding for mobile */
  }
  
  .title-text {
    font-size: 1rem;
  }
  
  .nav-menu {
    gap: 4px; /* Reduce button spacing */
  }
  
  .nav-button {
    width: 40px !important; /* Set fixed width */
    height: 40px !important; /* Set fixed height to maintain circular shape */
    min-width: 40px !important; /* Minimum width */
  }
  
  .mobile-search-btn {
    width: 40px !important; /* Set fixed width */
    height: 40px !important; /* Set fixed height to maintain circular shape */
    min-width: 40px !important;
  }
  
  .mobile-search-popup {
    width: 95%;
    padding: 16px;
  }
}

/* Search Panel Styles */
.search-wrapper {
  position: relative;
  width: 100%;
  z-index: 1001;
}

.search-panel {
  position: fixed;
  background: #1e1e2e;
  border: 1px solid #45475a;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 9999;
  padding: 16px;
  max-height: 80vh;
  overflow-y: auto;
  width: 400px;
  max-width: calc(100vw - 40px);
}



.filters-section {
  background: #313244;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid #45475a;
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-label {
  color: #a6adc8 !important;
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 4px;
}

.filter-input :deep(.v-field) {
  background-color: #45475a !important;
  border-radius: 6px;
}

.filter-input :deep(.v-field__input) {
  color: #cdd6f4 !important;
  font-size: 0.9rem;
}

.filter-input :deep(.v-field__outline) {
  border-color: #585b70 !important;
}

.filter-input :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important;
}

.date-range-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-input {
  flex: 1;
}

.date-input :deep(.v-field) {
  background-color: #45475a !important;
  border-radius: 6px;
}

.date-input :deep(.v-field__input) {
  color: #cdd6f4 !important;
  font-size: 0.9rem;
}

.date-separator {
  color: #a6adc8;
  font-size: 0.8rem;
  white-space: nowrap;
}

.limit-section {
  background: #313244;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #45475a;
  margin-bottom: 16px;
}



.search-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #45475a;
}

.action-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
}

/* Responsive adjustments for search panel */
@media (max-width: 600px) {
  .search-panel {
    left: 20px !important;
    width: calc(100vw - 40px) !important;
    border-radius: 8px;
    padding: 12px;
  }
  
  .filters-section,
  .limit-section {
    padding: 10px;
  }
  
  .date-range-container {
    flex-direction: column;
    align-items: stretch;
  }
  
  .date-separator {
    text-align: center;
    padding: 4px 0;
  }
}

/* Search Dialog Styles */
.search-dialog :deep(.v-overlay__content) {
  margin: 24px;
}

.search-card {
  background: #1e1e2e !important;
  border: 1px solid #45475a;
  border-radius: 16px;
  overflow: hidden;
}

.search-title {
  background: #313244 !important;
  color: #f9e2af !important;
  padding: 20px !important;
  font-weight: 600;
  border-bottom: 1px solid #45475a;
}

.search-content {
  padding: 24px !important;
}

.search-input :deep(.v-field) {
  background-color: #45475a !important;
  border-radius: 12px;
}

.search-input :deep(.v-field__input) {
  color: #cdd6f4 !important;
}

.search-input :deep(.v-field__outline) {
  border-color: #585b70 !important;
}

.search-input :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important;
}

.search-type-section {
  margin-bottom: 20px;
}

.section-title {
  color: #cdd6f4 !important;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 12px;
}

.search-type-toggle {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.search-type-btn {
  flex: 1;
  height: 40px;
  color: #a6adc8 !important;
  background-color: #45475a !important;
  border: none !important;
  border-radius: 0 !important;
  font-weight: 500 !important;
  font-size: 0.9rem !important;
  transition: all 0.2s ease !important;
}

.search-type-btn:hover {
  background-color: #585b70 !important;
  color: #cdd6f4 !important;
}

.search-type-btn.v-btn--selected {
  background-color: #89b4fa !important;
  color: #1e1e2e !important;
  font-weight: 600 !important;
}

.search-type-btn:first-child {
  border-top-left-radius: 8px !important;
  border-bottom-left-radius: 8px !important;
}

.search-type-btn:last-child {
  border-top-right-radius: 8px !important;
  border-bottom-right-radius: 8px !important;
}

.filters-section {
  background: #313244;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  border: 1px solid #45475a;
}

.filter-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  color: #a6adc8 !important;
  font-size: 0.9rem;
  font-weight: 500;
}

.filter-select :deep(.v-field) {
  background-color: #45475a !important;
  border-radius: 8px;
}

.filter-select :deep(.v-field__input) {
  color: #cdd6f4 !important;
}

.filter-select :deep(.v-field__outline) {
  border-color: #585b70 !important;
}

.filter-select :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important;
}

.date-range-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-input {
  flex: 1;
}

.date-input :deep(.v-field) {
  background-color: #45475a !important;
  border-radius: 8px;
  min-height: 40px !important;
}

.date-input :deep(.v-field__input) {
  color: #cdd6f4 !important;
  padding-left: 12px !important;
  padding-right: 40px !important; /* 为日期图标留出空间 */
}

.date-input :deep(.v-field__outline) {
  border-color: #585b70 !important;
}

.date-input :deep(.v-field--focused .v-field__outline) {
  border-color: #89b4fa !important;
}

.date-separator {
  color: #a6adc8;
  font-size: 0.9rem;
  white-space: nowrap;
}

.limit-section {
  background: #313244;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #45475a;
}

.limit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.limit-label {
  color: #cdd6f4;
  font-size: 0.9rem;
  font-weight: 500;
}

.limit-value {
  color: #89b4fa;
  font-weight: 600;
  font-size: 1rem;
  background: #45475a;
  padding: 4px 12px;
  border-radius: 16px;
  min-width: 50px;
  text-align: center;
}



.search-actions {
  background: transparent !important;
  padding: 16px 24px !important;
  border-top: 1px solid #45475a;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.action-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  min-width: 80px;
}

.reset-btn {
  background-color: transparent !important;
  border-color: #585b70 !important;
  color: #a6adc8 !important;
}

.reset-btn:hover {
  background-color: #45475a !important;
  border-color: #6c7086 !important;
}

.search-btn {
  background-color: #89b4fa !important;
  color: #1e1e2e !important;
  box-shadow: 0 2px 8px rgba(137, 180, 250, 0.3) !important;
}

.search-btn:hover {
  background-color: #74c7ec !important;
  box-shadow: 0 4px 12px rgba(137, 180, 250, 0.4) !important;
}

/* Responsive adjustments for search dialog */
@media (max-width: 600px) {
  .search-dialog :deep(.v-overlay__content) {
    margin: 12px;
  }
  
  .search-content {
    padding: 16px !important;
  }
  
  .filters-section,
  .limit-section {
    padding: 16px;
  }
  
  .date-range-container {
    flex-direction: column;
    align-items: stretch;
  }
  
  .date-separator {
    text-align: center;
    padding: 8px 0;
  }
}
</style>
