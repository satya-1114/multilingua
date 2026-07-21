# Folder structure

```
├── backend/                       # FastAPI service (documented separately)
├── docs/                          # Architecture, backend contracts, guides
├── public/                        # Static assets served as-is
├── src/
│   ├── api/                       # HTTP client + envelope contracts
│   │   ├── client/http-client.ts  # fetch wrapper: auth, retry, dedupe, timeouts
│   │   └── contracts.ts           # ApiResponse / ApiListResponse
│   ├── components/
│   │   ├── ui/                    # shadcn primitives (do not modify by hand)
│   │   ├── common/                # cross-feature building blocks
│   │   ├── forms/                 # form widgets and wizards
│   │   └── layouts/               # AppLayout, SidebarNav, TopBar, AuthLayout
│   ├── constants/
│   │   ├── rbac.ts                # Roles + PERMISSIONS + ROLE_PERMISSIONS
│   │   ├── india.ts               # States, districts, languages, channels
│   │   └── …                      # Feature-scoped constants
│   ├── contexts/                  # AuthContext + friends
│   ├── hooks/                     # usePermissions, useDebouncedValue, useMobile
│   ├── lib/
│   │   ├── route-access.ts        # URL-prefix → allowed roles
│   │   ├── utils.ts               # cn(), formatters
│   │   └── mock/                  # Local fixtures used when VITE_MOCK_MODE=true
│   ├── routes/                    # File-based routing (TanStack Router)
│   │   ├── __root.tsx             # html/body shell, error/404 boundaries
│   │   ├── index.tsx              # Public landing
│   │   ├── login.tsx / register.tsx
│   │   ├── _authenticated.tsx     # Protected route gate
│   │   ├── _authenticated/…       # Signed-in features (campaigns, disasters, …)
│   │   └── public.*.tsx           # Public campaign / alert pages (no auth)
│   ├── services/                  # Feature services (apiService-backed)
│   ├── styles.css                 # Tailwind v4 + design tokens
│   └── types/                     # Cross-service TypeScript contracts
├── package.json
└── vite.config.ts
```

## Where to add new code

| Adding …                          | Put it here                                      |
| ---------------------------------- | ------------------------------------------------ |
| A new signed-in page               | `src/routes/_authenticated/<feature>.<page>.tsx` |
| A new public page                  | `src/routes/public.<feature>.tsx`                |
| A new REST call                    | Extend the module service, never inline `fetch`  |
| A new reusable widget              | `src/components/common/<name>.tsx`               |
| A new permission                   | `src/constants/rbac.ts` (+ role assignment)      |
| A new route-level RBAC rule        | `src/lib/route-access.ts`                        |
| A new environment variable         | `.env.example` + `src/services/environment.service.ts` |
