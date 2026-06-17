# Build Notes for Future AI Agents

This file captures non-obvious lessons learned while restoring the PRISM X Android (Element X fork) build pipeline. Read it before touching `Frontend_Source/`.

## Server-side gotcha: deleting Synapse users at the SQL level

When mass-deleting users via SQL (instead of the admin API), the obvious "delete from every table whose column is named `user_id`" sweep is **incomplete**. Synapse mixes two reference styles:

- **Full Matrix ID** in most tables (`@alice:matrix.fathertkt.uk`) — column usually `user_id`, `user_name`, `creator`.
- **Localpart only** in a handful of tables (`alice`) — `profiles.user_id`, `user_filters.user_id`.

If you `DELETE FROM users WHERE name LIKE '%@user...'` and miss the localpart-keyed tables, the next registration of the same localpart blows up with:

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "profiles_user_id_key"
DETAIL:  Key (user_id)=(alice) already exists.
```

…surfaced to the app as `Hata Internal Server Error`.

**Fix when this happens** (one-shot, idempotent):

```sql
DELETE FROM profiles
 WHERE full_user_id IS NULL
    OR full_user_id NOT IN (SELECT name FROM users);

DELETE FROM user_filters
 WHERE user_id NOT IN (
   SELECT split_part(split_part(name, ':', 1), '@', 2) FROM users
 );
```

Long-term, prefer Synapse's admin API (`POST /_synapse/admin/v1/deactivate/{userId}` with `erase=true`) — it keeps integrity, but requires an admin token. For test environments without an admin user, the orphan-cleanup SQL above is acceptable.

## Project identity

`Frontend_Source/` is **PRISM X** — a fork of Element X (Android, Compose, Appyx + Molecule + Metro DI, prism-rust-sdk). It is **not** the legacy Element Android. Per-screen architecture is mandated by `Frontend_Source/AGENTS.md`:

```
FooNode.kt        Appyx node — wires Presenter to View
FooPresenter.kt   @Composable, produces FooState from FooEvents
FooView.kt        Stateless Composable
FooState.kt       Immutable UI state
FooEvent.kt       Sealed interface of UI actions
FooStateProvider  Sample states for previews
FooPresenterTest  Turbine-based unit tests
```

Strings go in `temporary.xml` (never `localazy.xml` — it is auto-generated and overwritten). Use `Timber` for logging, never `android.util.Log`. UI tokens live in `libraries/compound/`.

## Half-renamed references (Element → PRISM)

The previous maintainer ran a global "Element"→"PRISM" / "element"→"prism" replace too aggressively. This rename was supposed to apply only to **PRISM-owned** types and identifiers, but it also hit:

- **Upstream Appyx public API names** (`BackStackElement`, `NavElement`, `activeElement`, `initialElements`, `LocalSharedElementScope`, `descriptor.element`, `BackStack.elements` property, etc.) — these MUST keep their original names because they're defined in the Appyx library, not in the PRISM codebase.
- **Gradle module references** that were renamed on one side but not the other (e.g., consumers said `prismui` but the directory is still `matrixui`).

If the build complains about an "unresolved reference" that looks like a rename mismatch, check whether it's an Appyx/Compose API name (revert to `Element`) or a PRISM module that simply wasn't renamed on both ends.

### Build-script rename mismatches (fixed for v1.0.0 baseline)

| Symptom | Reality | Fix applied |
| :--- | :--- | :--- |
| `projects.libraries.prismui` unresolved | Directory is `libraries/matrixui/` (not renamed) | Reverted 35 files to `projects.libraries.matrixui` |
| `projects.libraries.prismmedia` unresolved | Directory is `libraries/matrixmedia/` | Reverted to `matrixmedia` |
| Plugin id `io.element.android-compose-library` not found | Convention plugins compile to `io.prism.android-*` (see `plugins/build/classes/kotlin/main/Io_prism_*`) | Renamed across 97 `.kts` files |
| `projects.appicon.element` unresolved | Directory is `appicon/prism/` | Renamed in `tests/uitests/build.gradle.kts` |
| `libs.prism.call.embedded` unresolved | Catalog alias is `element_call_embedded` in `gradle/libs.versions.toml` | Use `libs.element.call.embedded` |
| `libs.prism.emojibase.bindings` unresolved | Catalog alias is `matrix_emojibase_bindings` | Use `libs.matrix.emojibase.bindings` |
| `projects.features.lightning.api` unresolved | No such module — never created | Removed dangling import in `features/home/impl/build.gradle.kts` |
| `com.github.matrix-org:matrix-analytics-events:0.33.2` not resolvable | Settings restricted Jitpack to `prism-org` only; dep is from `matrix-org` | Added `includeModule("com.github.matrix-org", "matrix-analytics-events")` in `settings.gradle.kts` |

### Kotlin source rename mismatches (Appyx / Compose APIs)

These were reverted from `PRISM`/`prism` back to the upstream API names because Appyx and Compose define them outside PRISM's control. **Do not rename these forward again.**

| Bad rename | Correct upstream name | Where it lives |
| :--- | :--- | :--- |
| `BackStackElement` → `BackStackPRISM` | `BackStackElement` | `com.bumble.appyx.navmodel.backstack` |
| `BackStackElements` → `BackStackPRISMs` | `BackStackElements` | `com.bumble.appyx.navmodel.backstack` |
| `NavElement` → `NavPRISM` | `NavElement` | `com.bumble.appyx.core.navigation` |
| `NavElements` → `NavPRISMs` | `NavElements` | `com.bumble.appyx.core.navigation` |
| `activeElement` → `activePRISM` | `activeElement` | `com.bumble.appyx.navmodel.backstack` (extension) |
| `initialElement(s)` → `initialPRISM(s)` | `initialElement` (BackStack ctor) / `initialElements` (BaseNavModel override) | Appyx |
| `BackStack.elements` (StateFlow) → `BackStack.prisms` | `BackStack.elements` | Appyx public property |
| `TransitionDescriptor.element` → `descriptor.prism` | `descriptor.element` | Appyx |
| `LocalSharedElementScope` → `LocalSharedPRISMScope` | `LocalSharedElementScope` | `com.bumble.appyx.core.node` |
| `shareElement` modifier → `sharePRISM` | `shareElement` | Appyx |
| `withSharedElementTransition` → `withSharedPRISMTransition` | `withSharedElementTransition` | local helper but follows Compose terminology |

The bad rename also affected lambda variable names (`prism` instead of `element`, `prisms` instead of `elements`). Those are harmless when consistent within a function, but when an Appyx interface override expects a parameter named `elements`, KAPT and the compiler accept it as a warning ("The corresponding parameter in the supertype is named 'elements'.") rather than an error. Leave such warnings alone unless they break named-argument calls.

### Quick triage rule

Lowercase `prism` followed by `.android` (e.g., `io.prism.android.foo`) is a **PRISM package path** — keep it.
Lowercase `prism`/`prisms` as a standalone identifier in code that interacts with Appyx (`BackStack`, `NavModel`, `Overlay`, `TransitionDescriptor`) is a **bad rename** — revert it.

If you see another mismatch, the algorithm is:
1. `ls Frontend_Source/libraries/` and `Frontend_Source/features/` to see what actually exists.
2. `grep -n "^element_\|^matrix_\|^prism_" Frontend_Source/gradle/libs.versions.toml` to see catalog aliases.
3. Pick the side with the directory / alias and patch the consumer.

## SDK and Gradle locations

- `tools/android/sdk` — Android SDK (build-tools 34.0.0, platforms/android-34). Path is wired via `Frontend_Source/local.properties`.
- `tools/android/gradle_dist` — bundled Gradle 8.5. **Not used by the wrapper**; the wrapper downloads 9.2.1 itself. Kept only as a fallback for offline scenarios.
- JDK 21: `C:\AMDDesignTools\.xinstall\2025.2\tps\win64\jre21.0.5_11`. Set `JAVA_HOME` and prepend `%JAVA_HOME%\bin` to PATH before invoking the wrapper.

The old `Frontend/` directory (jadx-decompiled APK + sdk + gradle_dist) was removed on 2026-05-01 because it caused confusion with `Frontend_Source/` and contained no build-recoverable code.

## Memory tuning (8 GB host)

Element X has 100+ modules. Default Gradle JVM args cause OOM during configuration. Use:

```properties
org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8 -XX:+UseG1GC -XX:MaxMetaspaceSize=1g
kotlin.daemon.jvm.options=-Xmx2048m -XX:+UseG1GC
org.gradle.workers.max=1
```

Do not enable `org.gradle.parallel=true` with workers.max > 1 on this host — KSP + Compose compiler will swap.

If you still get `Java heap space` during a specific task (e.g., `generateDebugLintReportModel`), skip lint with `-x lint -x lintVitalRelease`. Lint reports are not required for APK output.

## Removed legacy

- `tools/build_apk.py` — DELETED on 2026-05-01. It was a re-signer over `Frontend/prism_dbg.apk` (decompiled APK). Every "build" produced a byte-equivalent output, which is why v1.0.0 attempts kept regenerating the v0 binary. Future agents: do not resurrect this approach. Always build from source via `./gradlew.bat :app:assembleDebug`.

## Verification commands

```powershell
# Cheap sanity check — configures the project graph (no compilation):
./gradlew.bat projects --no-configuration-cache

# Full debug APK build:
./gradlew.bat :app:assembleDebug -x lint -x lintVitalRelease
```

If `projects` fails, fix the script-compilation error before attempting `assembleDebug`. Configuration-time errors are 100x cheaper to iterate on.
