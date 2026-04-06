# Testing Instructions for Live Session Sync

## Overview
The system has been enhanced with comprehensive logging and improved matching logic to ensure that when a faculty member starts a live session, the student dashboard immediately reflects the status change and the join button turns green.

## Key Changes Made

### 1. **Student Dashboard (student-dashboard.html)**
   - Enhanced `loadCourses()` function with detailed logging
   - Improved `syncActiveSessions()` with robust ID matching (case-insensitive, string conversion)
   - Added comprehensive console logging with emoji indicators (📚📡🔍✅❌🔄🎨)
   - Added debug helpers: `window.debugShow()` and `window.debugSync()`
   - Ensures courses are loaded before sync attempt

### 2. **Session Page (session.html)**
   - Enhanced `registerLiveSession()` with verification logging
   - Shows what's being saved to localStorage
   - Added `window.debugSession()` debug helper

### 3. **Key Features**
   - Case-insensitive ID matching
   - Type conversion (string comparison)
   - Polling every 1 second for instant visual feedback
   - Comprehensive console logs at every step
   - Fallback to STATIC_COURSES if no enrollments

## Step-by-Step Testing

### Prerequisites
1. Open the seed-database.html page and click "Seed" to populate test data
2. Student and faculty accounts should be created with test classrooms and enrollments

### Test Scenario

**STEP 1: Student Login**
1. Open browser developer console (F12)
2. Go to login.html
3. Select "I am a Student"
4. Login with: `ananya.k@student.nitw.ac.in` / `student123`
5. Student dashboard should load
6. Open Console and run: `debugShow()`
7. **Expected Output**: Should show:
   - Student email: `ananya.k@student.nitw.ac.in`
   - courses array with 3-4 courses (enrolled classrooms)
   - Each course should have `id` (like 'cls_seed_001'), `classroomId`, and `status: 'ended'`
   - localStorage amigo_live_sessions: should be empty `[]`

**STEP 2: Faculty Starts Session (in another tab/window)**
1. Open a NEW tab/window (important!)
2. Go to login.html
3. Select "I am a Faculty"
4. Login with: `prof.menon@nitw.ac.in` / `faculty123`
5. Click "Start" on the first course (e.g., "Software Engineering")
6. Session.html should load
7. Open Console and run: `debugSession()`
8. **Expected Output**: Should show:
   - localStorage amigo_live_sessions: array with one session object
   - Session should have classId like 'cls_seed_001' (as string)

**STEP 3: Monitor Student Dashboard (back to first tab)**
1. Go back to the student dashboard tab
2. Keep an eye on the Developer Console
3. Watch for console logs with emoji indicators:
   - 🎓 `loadCourses` messages
   - 📡 `Live sessions from localStorage` messages
   - 🔍 `Checking course` messages
   - ✅ `MATCH FOUND!` or ❌ `No match` messages
   - 🔄 `Status changed` messages
   - 🎨 `renderTable` messages

4. **Expected Console Output Flow**:
   ```
   📡 Live sessions from localStorage: [{classId: 'cls_seed_001', ...}]
   🎓 Current courses array: [{name: 'Software Engineering', id: 'cls_seed_001', ...}]
   🔍 Checking course "Software Engineering" | id="cls_seed_001" (cls_seed_001)
   🆚 vs session classId="cls_seed_001" (cls_seed_001)
   ✅ MATCH FOUND!
   🔄 Status changed for "Software Engineering": ended → live
   🎨 renderTable called | filter: all | courses count: 3
   ```

5. **Expected UI Changes**:
   - The course row should show a green "JOIN" button (was previously red/disabled)
   - A toast notification should appear: "🟢 Software Engineering is LIVE — Join now!"
   - Course status in the table should be updated

### Debugging Helpers

**Available console commands:**

1. **`debugShow()`** (on student dashboard)
   - Shows current student email
   - Shows courses array with IDs and statuses
   - Shows what's in localStorage live sessions

2. **`debugSync()`** (on student dashboard)
   - Manually triggers sync function
   - Useful to see console logs without waiting

3. **`debugSession()`** (on session.html)
   - Shows what's in localStorage live sessions from faculty perspective

### Common Issues & Troubleshooting

**Issue: "⚠️  Using STATIC_COURSES (no enrollment)"**
- **Cause**: Student is not enrolled in any real classrooms
- **Solution**: Check if seed database was run. Make sure student email in STUDENTS array matches the email being logged in with

**Issue: "❌ No match" appearing repeatedly**
- **Cause**: Course IDs don't match session classIDs
- **Check**:
  1. Run `debugShow()` on student dashboard
  2. Run `debugSession()` on faculty session.html
  3. Compare the IDs - they should be identical
  4. Check formatting - should be like 'cls_seed_001' (lowercase string)

**Issue: No console logs appearing at all**
- **Cause**: syncActiveSessions might not be running
- **Solution**: Open console and manually run `debugSync()` to trigger it

**Issue: Course status changes but button doesn't turn green**
- **Cause**: CSS issue or renderTable not being called
- **Check**: Look for "🎨 renderTable called" in console
- **Solution**: Check that `btn-join-live` CSS class is being applied

**Issue: Status changes but then reverts back to 'ended'**
- **Cause**: Faculty session ended or localStorage was cleared
- **Solution**: Check localStorage amigo_live_sessions - should still have the session entry

### Advanced Debugging

If issues persist, try these additional checks:

1. **Verify localStorage is being shared**:
   - In faculty session.html console: `localStorage.getItem('amigo_live_sessions')`
   - In student dashboard console: `localStorage.getItem('amigo_live_sessions')`
   - Should show the SAME data

2. **Check if tabs are in same browser context**:
   - If using private/incognito windows, localStorage is NOT shared
   - Use regular browser tabs instead

3. **Verify classroom enrollment data**:
   ```javascript
   // In student dashboard console:
   const classrooms = JSON.parse(localStorage.getItem('amigo_classrooms') || '[]');
   const studentEmail = localStorage.getItem('amigo_email');
   const enrolled = classrooms.filter(cls => 
     cls.students && cls.students.some(s => s.email === studentEmail)
   );
   console.log('Enrolled classrooms:', enrolled);
   ```

4. **Check exact ID format**:
   ```javascript
   // Should show something like:
   // [{id: 'cls_seed_001', name: 'Software Engineering', students: [...], ...}]
   ```

## Expected Results

After completing all steps:
1. ✅ Student dashboard loads with enrolled courses showing "ended" status
2. ✅ Faculty starts session in another window
3. ✅ Within 1 second, student dashboard detects live session
4. ✅ Course status changes from "ended" to "live"
5. ✅ Join button turns GREEN with play icon (▶)
6. ✅ Toast notification shows "🟢 [Course Name] is LIVE — Join now!"
7. ✅ All console logs show successful matching and status update

## Notes

- The polling interval is set to 1000ms (1 second) for instant visual feedback
- Console logs are comprehensive - every step is logged with emoji indicators for easy tracking
- Case-insensitive and type-safe string comparisons ensure matching works regardless of formatting
- If student hasn't enrolled in any classrooms, the system falls back to demo STATIC_COURSES (but ID matching might not work in this case)

## Support

If the issue persists after testing:
1. Check browser console for error messages (red `console.error` statements)
2. Ensure seed database has been run with classrooms and student enrollments
3. Verify faculty is logging in with correct email/password
4. Make sure both tabs/windows are in the same browser (not private/incognito)
5. Clear localStorage and reseed if corruption is suspected: localStorage.clear()
