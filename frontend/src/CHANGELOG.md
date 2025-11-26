# Changelog

## 2025-11-06 - UI Enhancement Update

### ✅ Fixed Issues

#### 1. React Ref Forwarding Errors
**Problem:** Function components cannot be given refs when using `asChild` prop with Radix UI components.

**Fixed Components:**
- `/components/chat/Header.tsx` - DropdownMenuTrigger
- `/components/chat/ChatInput.tsx` - DialogTrigger

**Solution:** Replaced Button components with native HTML `<button>` elements when used with `asChild` prop.

**Before:**
```tsx
<DropdownMenuTrigger asChild>
  <Button variant="ghost">...</Button>
</DropdownMenuTrigger>
```

**After:**
```tsx
<DropdownMenuTrigger asChild>
  <button className="...">...</button>
</DropdownMenuTrigger>
```

---

### 🎨 New Features

#### 1. Dark Mode Support
- Complete dark theme implementation
- Theme persistence with LocalStorage
- Smooth transitions between light/dark modes
- System-wide color consistency

**Files:**
- `/hooks/useTheme.ts` - Theme state management
- `/styles/globals.css` - CSS variables for both themes
- All components updated with `dark:` class variants

#### 2. Premium Header Component
**Features:**
- ⏰ Real-time clock (HH:MM:SS + date)
- 👤 User profile dropdown menu
- 🌓 Dark mode toggle
- 🛡️ Role badge (ADMIN/ANALYST/USER)
- 📱 Fully responsive design
- 🚪 Logout functionality

**Location:** `/components/chat/Header.tsx`

#### 3. File Upload System
**Features:**
- Drag & drop support
- Multiple file selection (max 5 files)
- File size validation (10MB limit)
- Preview with delete option
- Supported formats: CSV, XLSX, JSON, TXT

**Files:**
- `/components/chat/FileUpload.tsx`
- `/components/chat/ChatInput.tsx` (updated)

#### 4. Session Title Editing
**Features:**
- Inline editing with Enter/ESC shortcuts
- Visual feedback on hover
- Auto-update timestamp
- Edit/Delete buttons on hover

**Files:**
- `/hooks/useSessions.ts` - Added `renameSession` method
- `/components/chat/SessionSidebar.tsx` - UI implementation

---

### 🌈 Dark Mode Updates

All components updated with dark mode support:

| Component | File | Updates |
|-----------|------|---------|
| Header | `Header.tsx` | Background, text, borders |
| Sidebar | `SessionSidebar.tsx` | Full dark theme |
| Chat Input | `ChatInput.tsx` | Input field, buttons |
| Message List | `MessageList.tsx` | Empty state, suggestions |
| Message Item | `MessageItem.tsx` | Message bubbles, avatars |
| Trace Widget | `TraceWidget.tsx` | Cards, metrics, events |

**Color Scheme:**

Light Mode:
- Background: `#ffffff`
- Text: `oklch(0.145 0 0)`
- Border: `rgba(0, 0, 0, 0.1)`

Dark Mode:
- Background: `oklch(0.145 0 0)`
- Text: `oklch(0.985 0 0)`
- Border: `oklch(0.269 0 0)`

---

### 🔧 Technical Improvements

1. **Zustand Persist** - Theme preference saved to LocalStorage
2. **CSS Variables** - Tailwind v4 with custom color tokens
3. **Responsive Design** - Mobile-first approach
4. **Type Safety** - Full TypeScript coverage
5. **Performance** - Optimized re-renders with proper memoization

---

### 📁 New Files

```
/hooks/useTheme.ts              - Theme state management
/components/chat/Header.tsx     - Premium header component
/components/chat/FileUpload.tsx - File upload component
/guidelines/UI-Enhancements.md  - Feature documentation
/CHANGELOG.md                   - This file
```

---

### 🐛 Bug Fixes

1. ✅ Fixed React ref forwarding warnings
2. ✅ Fixed DropdownMenuTrigger Button ref issue
3. ✅ Fixed DialogTrigger Button ref issue
4. ✅ Added missing dark mode classes across all components
5. ✅ Improved text contrast in dark mode

---

### 🚀 Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| ADMIN | admin@manufacturing.ai | admin123 |
| ANALYST | analyst@manufacturing.ai | analyst123 |
| USER | user@manufacturing.ai | user123 |

---

### 📋 Testing Checklist

- [x] Dark mode toggle works
- [x] Theme persists across page refresh
- [x] File upload with drag & drop
- [x] Session title editing
- [x] Logout functionality
- [x] Real-time clock
- [x] User dropdown menu
- [x] Mobile responsive layout
- [x] No console warnings
- [x] All text readable in both themes

---

### 🔜 Future Enhancements

- [ ] File preview for images/CSV
- [ ] File download capability
- [ ] Session search/filter
- [ ] Keyboard shortcuts
- [ ] User settings page
- [ ] System theme detection
- [ ] Theme animation presets

---

**Version:** 2.0  
**Date:** November 6, 2025  
**Status:** ✅ Stable
