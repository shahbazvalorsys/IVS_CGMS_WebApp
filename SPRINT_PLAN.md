# Phase 1 sprint plan (from FSD Section 8)

| Sprint | Content | Status |
|---|---|---|
| 1 | Foundations: project, database, login, client (tenant) model, Arabic/English and right-to-left, audit log, tenant isolation tests, default roles and permissions | **Done** (44 tests) |
| 2 | Platform console: clients, subscriptions, seats, invitations; users and roles screens | Next |
| 3 | Configuration: lists, contract types, custom fields, holidays; two industry packs | |
| 4 | Parties and contacts; documents and file storage | |
| 5 | Contracts and lines; status lifecycle; duplicate checks | |
| 6 | Guarantees, extensions; cheques | |
| 7 | Alert engine: rules, daily job, alert centre, email; default rules | |
| 8 | Dashboard and reports R-01 to R-05; import; hardening; pilot release | |

Rule for every sprint: new client tables extend `TenantModel`; new features come with tests for
validation rules, permissions, audit entries and tenant isolation; every screen works in English and Arabic.
