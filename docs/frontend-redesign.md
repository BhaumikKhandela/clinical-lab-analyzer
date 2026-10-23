# Editorial Health frontend redesign

Implemented on `codex/frontend-ui-revamp`. Evaluation Studio's component and CSS,
backend APIs, medical rules, and model integration are unchanged.

## Audit and implementation

The app uses React 19 and Vite 8, with plain CSS and no component-library dependency.
Its authenticated views cover lab analysis, patient creation, report/image filing,
patient report/image libraries, email sharing, and administrator accounts. Analysis
returns existing severity buckets, values, intervals, explanations, sources and
next steps; report chat uses the existing checkpoint-backed WebSocket.

- Replaced the photo/grid/gradient shell with a warm ivory workspace, light
  navigation rail, restrained sage accents, editorial serif headings and a
  scoped design-token layer. Existing system fonts provide offline fallbacks;
  no external font requests or new runtime dependencies are introduced.
- Rebuilt sign-in, navigation and analysis input hierarchy. Existing views remain
  mounted when switching sections so drafts and completed analyses survive.
- PDF upload now has native selection and drag/drop, visible selection state,
  PDF/10-MB validation consistent with the existing analyzer, and honest loading
  copy. Manual entry is a separate input mode with visible mobile labels.
- Results show real document metadata where available, backend-derived counts,
  critical attention guidance, functional severity filters, expandable explanations,
  next steps and source records, and an optional reference-range visualization.
  No frontend diagnoses, scores, demographic claims or demo patient data are added.
- Report and image library actions, patient/account forms, existing image analysis
  and email actions retain their API handlers and receive shared form/list styles.
  The overview links to the real library rather than fabricating recent reports
  across patients (there is no aggregate reports endpoint in this frontend).
- Report chat remains contextual and collapsible. It has quieter typography,
  readable messages, suggested questions, pending/connection states, and explicit
  reconnect. Closed panels are inert so keyboard users cannot tab into them.
- Main-app CSS is scoped to `.app`; Evaluation Studio remains a separate surface.
  The main app explicitly uses a light color scheme regardless of system theme.

## Validation

From the repository root:

```sh
npm run build --prefix frontend
npm run lint --prefix frontend
npm run test:ui --prefix frontend
```

The static integration checks render the real components with isolated test state:
access gating, authenticated navigation, hidden mounted views, preservation of
source facts/actions, chat availability, and unchanged Evaluation Studio files.
They never create real sessions, call backends, or inject demo data into the app.

Browser inspection covers the actual sign-in page, desktop and 390px mobile
layouts, report details with explicitly labeled synthetic fixtures, light appearance,
and absence of horizontal page overflow. Temporary fixture pages are removed after
inspection. The actual sign-in screen is left open for the user.

The browser had no signed-in session, so a live authenticated upload, saved-report
round trip, WebSocket conversation and email were not exercised. They require
an existing account and running services. No paid model calls or emails were made.

Lint retains the pre-existing Fast Refresh warning about `severityKey` being
exported from `SeverityBadge.jsx`; there are no build errors or new lint warnings.
