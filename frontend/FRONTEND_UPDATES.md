# Frontend - Timetable OCR System

## ✨ Recent Updates & Features

### 🆕 New Features

#### 1. **Toast Notification System**
- Real-time notifications (success, error, warning, info)
- Auto-dismiss after 3-4 seconds
- Positioned at top-right corner
- Smooth animations with slide-in effect

#### 2. **Dark Mode Support**
- Toggle button in top navigation
- Theme persists in localStorage
- Automatic CSS variable updates
- Smooth transitions between themes

#### 3. **Google Calendar Integration**
- One-click sync to Google Calendar
- OAuth 2.0 integration
- Events created with correct dates within semester range
- Success notification with event count

#### 4. **Calendar View with Date Range**
- Select custom semester start/end dates
- View all class occurrences within date range
- Timeline display of events by date
- Shows venue and class type information

#### 5. **ICS File Export**
- Download timetable as iCalendar file
- Compatible with all calendar applications
- Includes all events within selected date range

#### 6. **Enhanced Venue Support**
- Display venue information on class cards
- Include venue in reminder notifications
- Show venue in Google Calendar events

#### 7. **Improved Settings Page**
- Configure semester dates (used by all views)
- Adjust reminder notification time (5/15/30/60 min)
- Toggle email notifications
- Export settings as JSON file
- Dark mode toggle with persistence

### 🔧 Backend API Alignment

The frontend now supports all new backend endpoints:

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /upload-schedule` | Upload timetable image | ✅ Working |
| `GET /timetable/{id}` | Get timetable structure | ✅ Working |
| `GET /timetable/{id}/calendar-view` | Get events with dates | ✅ Implemented |
| `GET /timetable/{id}/add-to-google-calendar` | Google Calendar sync | ✅ Implemented |
| `GET /auth/google/callback` | Google OAuth callback | ✅ Handled |
| `GET /timetable/{id}/calendar.ics` | Download ICS file | ✅ Implemented |
| `POST /reminder` | Create reminder (with venue) | ✅ Updated |
| `GET /timetable/{id}/calendar-view` | Calendar with dates | ✅ Implemented |

### 📦 New Files & Components

```
frontend/
├── src/
│   ├── utils/
│   │   ├── notificationContext.jsx    (Toast system)
│   │   ├── hooks.js                   (useToast, useTheme)
│   │   └── dependencies.js            (unchanged)
│   ├── pages/
│   │   ├── dashboard/
│   │   │   ├── AcademicCalendar.jsx   (Rewritten: Date range + timeline)
│   │   │   ├── MyClasses.jsx          (Updated: Venue support)
│   │   │   ├── Settings.jsx           (Enhanced: More options)
│   │   │   ├── Profile.jsx            (Updated: Toast notifications)
│   │   │   └── ImageUpload.jsx        (Updated: Toast + progress bar)
│   │   ├── AuthPage.jsx               (unchanged)
│   │   ├── RoleSelect.jsx             (unchanged)
│   │   └── Dashboard.jsx              (unchanged)
│   ├── components/
│   │   ├── TopNav.jsx                 (Added: Dark mode toggle)
│   │   └── Sidebar.jsx                (unchanged)
│   ├── App.jsx                        (Added: Google callback handler)
│   ├── main.jsx                       (Added: Theme initialization)
│   ├── index.css                      (Enhanced: Dark mode, animations)
│   └── api.js                         (unchanged)
```

### 🎨 UI/UX Improvements

1. **Notification System**
   - Top-right toast notifications
   - Color-coded by type (green=success, red=error, yellow=warning, blue=info)
   - Auto-dismisses or manual close button

2. **Calendar View**
   - Timeline format showing events by date
   - Compact event cards with type badges
   - Type badges (THEORY/LAB) with distinct colors
   - Date range selector with calendar inputs

3. **Dark Mode**
   - Affects all colors, backgrounds, borders
   - Smooth transitions when toggling
   - Respects user preference across sessions
   - CSS custom properties for dynamic theming

4. **Enhanced Forms**
   - Progress bars for uploads
   - Better field labels and hints
   - Inline input fields with consistent styling
   - Improved error/success messages

### 🔐 API Configuration

**Base URL**: Currently set to `''` (relative paths)

For development:
```javascript
// frontend/src/api.js - line 1
const BASE = 'http://localhost:8000'  // for local development
```

For production:
```javascript
const BASE = 'https://your-api-domain.com'  // for production
```

### 📱 Key User Flows

#### Upload & View Timetable
1. Go to "Upload Timetable" → Choose image or JSON
2. System extracts and stores timetable
3. Timetable ID saved to localStorage
4. View in "My Classes" → Select day to see schedule

#### Sync to Google Calendar
1. Set semester dates in Settings
2. Go to "Academic Calendar"
3. Click "Google Calendar" button
4. Authorize with Google account
5. Events synced automatically
6. Success notification shows event count

#### Download Timetable
1. Load timetable in "Academic Calendar"
2. Set date range
3. Click "Download ICS"
4. Import into any calendar app

#### Create Reminder
1. Go to "My Classes"
2. Load your timetable
3. Click bell icon on a class
4. Confirm reminder details
5. Receive email 15 minutes before class

### 🚀 Development Setup

```bash
cd frontend
npm install
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Build for production
npm run preview      # Preview production build
```

### ⚙️ Environment Variables Required (Backend)

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback
FRONTEND_URL=http://localhost:3000
```

### 📋 Testing Checklist

- [ ] Toast notifications appear when actions complete
- [ ] Dark mode toggle works and persists
- [ ] Semester dates save and persist across sessions
- [ ] Calendar view loads events with correct dates
- [ ] Google Calendar sync redirects and shows success
- [ ] ICS file downloads and opens in calendar app
- [ ] Venue displays on class cards and in reminders
- [ ] Profile, Settings, and My Classes pages load correctly
- [ ] All forms validate input properly
- [ ] Loading spinners show during async operations

### 🐛 Known Limitations

1. Google Calendar sync requires GOOGLE_REDIRECT_URI to be configured
2. ICS file generation depends on backend implementation
3. Email reminders require backend SMTP configuration
4. Venue field is optional and may be empty

### 📝 Notes

- All dates use ISO 8601 format (YYYY-MM-DD)
- Theme preference stored in localStorage as 'theme'
- Semester dates stored as 'semester_start' and 'semester_end'
- Timetable ID stored as 'timetable_id'
- Token and refresh_token stored for authentication
