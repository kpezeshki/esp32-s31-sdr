# Freerouting v2.1.0 security / privacy audit (static)

Date: 2026-11-10. Method: static only. The jar was never executed. It was unzipped into a scratch dir, and its class constant-pool strings were cross-checked against the upstream source at tag v2.1.0 (shallow git clone). No javap is available, because the bundled JRE has no JDK tools. Task: agentq T18.

## Verdict

**Not malicious.** The jar is byte-identical to the official GitHub release asset, and the bundled JRE is byte-identical to the official Eclipse Temurin build. There is no exec, no dynamic or remote class loading, no credential or file harvesting, and no upload of board data in the CLI path that we use.

Privacy concerns, both minor:
1. The **update check is unconditional**. There is no setting or flag for it in v2.1.0, so every run does one GET to api.github.com.
2. **Analytics are opt-out.** They default ON and go to api.freerouting.app. Our flag does disable them. However, one earlier run (`--help`, 2026-11-10 14:10:27) lacked the flag, so analytics were enabled for that run. It likely sent an `identify` event, and possibly an "Application Started" event, carrying: a random UUID, an empty email, the args "--help", the OS/kernel version string, the Java version, the locale, the CPU count and the max heap. No file names, board data, hostname or username were sent.

## 1. Integrity

| Item | Result |
|---|---|
| `/home/kaveh/tools/freerouting/freerouting.jar` | 66,978,394 B, sha256 `2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def` |
| Upstream `freerouting-2.1.0.jar` (GitHub release v2.1.0, published 2025-04-12) | Same size. Downloaded the copy and ran `cmp`: **IDENTICAL**. GitHub publishes no digest for this release, so the comparison was done by direct download. |
| Manifest | Main-Class `app.freerouting.Freerouting`, Built-By andra, Build-Revision 1c1edc12..., built with Temurin 21.0.5 |
| `/home/kaveh/tools/freerouting/jre.tar.gz` | sha256 `a535a1df...51dd` **matches** the official Temurin `OpenJDK21U-jre_x64_linux_hotspot_21.0.13_9.tar.gz.sha256.txt` |
| Extracted `jdk-21.0.13+9-jre/` | Has 320 entries, the same count as the tarball. `bin/java`, `lib/modules` and `lib/server/libjvm.so` hashes match the tarball. No files are newer than the tarball. |

Contents of the jar:
- 31,556 classes, of which 752 are in `app/freerouting/**`.
- Every third-party package corresponds to the build.gradle dependencies (log4j 2.24.3, gson, jersey/hk2, jetty 12, jakarta, slf4j) or to their transitive dependencies. The transitive set is google-cloud-bigquery, gax, grpc (netty-shaded), conscrypt, arrow, protobuf, opencensus/opentelemetry, guava, jackson and apache httpclient.
- Native libraries in `META-INF/native` (conscrypt, netty-tcnative, epoll) belong to grpc/conscrypt. They load only if the BigQuery or grpc code path runs, which the CLI path never does.
- Harmless upstream leftover: empty `app/freerouting/.vs/` folders (a Visual Studio index).
- Nothing in the jar is foreign to the project.

## 2. Network

All URL strings in `app/**/*.class`:
- api.freerouting.app/v1/analytics/{identify,track}
- api.github.com/repos/freerouting/freerouting/releases/latest
- api.segment.io/v1/{identify,track}
- www.googleapis.com/auth/bigquery
- localhost:37864 and 0.0.0.0:37864
- github.com docs and sponsors links, and www.freerouting.app

The compiled strings match the v2.1.0 source.

| Endpoint | Class | When | Data sent |
|---|---|---|---|
| `https://api.github.com/repos/freerouting/freerouting/releases/latest` | `management/VersionChecker` (java.net.http.HttpClient GET), started from `Freerouting.main` | **Every run, unconditionally.** There is no setting. | Plain GET with UA `Java-http-client/21.0.13`. It reveals the source IP and the Java version, and nothing else. The response is only compared to "v2.1.0" and logged ("New version available"). Nothing is downloaded or executed. |
| `https://api.freerouting.app/v1/analytics/identify` and `/track` | `management/analytics/FreeroutingAnalyticsClient` (HttpURLConnection POST JSON), wrapped by `FRAnalytics` | Only when analytics are enabled, which is the default | Basic-auth header with `logger_key`. The key is transient and random per run, so it is not a secret. Fields per event are listed below. |
| `https://api.segment.io/v1/*` | `SegmentClient` | **Dead code.** The constructor call is commented out in `FRAnalytics.setAccessKey`. | The hard-coded Segment write key is unused. |
| BigQuery (googleapis) | `BigQueryClient` | Only from `api/v1/AnalyticsControllerV1`, which is the server side of freerouting.app. It needs `bigquery_service_account_key`, which is null by default. | Not reachable in our use. |
| `Desktop.browse(github.com/sponsors/...)` | `gui/WindowUserSettings` | Only on a GUI click | Not reachable headless. |

Analytics payload, when enabled:
- Every event includes the persistent random UUID `profile.id`, `profile.email` (empty by default), the current time and the GUI window location.
- **identify**: the UUID and email.
- **Application Started**: version, full command-line args (this would include file paths), OS name/arch/kernel version, Java version/vendor, system and GUI locale, CPU cores, max heap MB, `-host` arg value (default "N/A", not the hostname), screen width/height/DPI.
- **File Loaded**: BoardStatistics JSON, which is counts of layers, components, nets, pads, traces and vias plus the board host CAD.
- **Board Loaded**: host CAD/version and layer, component and net counts.
- **Auto-router / Optimizer Started/Finished**: the whole GlobalSettings JSON, meaning profile id/email and router settings. Filenames are transient and excluded.
- **Application Closed**: runtimes and job counters.
- **Exception Thrown**: the stack trace.
- **API Endpoint Called**: the request and response.
- Board geometry and the DSN file itself are **never** sent.

Does `--usage_and_diagnostic_data.disable_analytics=true` work? **Yes.**
- `GlobalSettings.applyCommandLineArguments` runs before the gate. It maps `--a.b=c` to `ReflectionUtil.setFieldValue` by `@SerializedName`.
- `Freerouting.main` computes `allowAnalytics = !disableAnalytics && (uuid-prefix % 1 == 0) && profile.allow_telemetry`, then calls `FRAnalytics.setEnabled(false)`.
- `FreeroutingAnalyticsClient.sendPayloadAsync` returns early when the client is not enabled, so identify and all track calls become no-ops.
- Evidence in `/tmp/freerouting/freerouting.log`: every flagged run logs "DEBUG Analytics are disabled". Of 18 runs, only the `--help` run lacked the flag.
- Other equivalent switches:
  - `--profile.allow_telemetry=false` (a second, independent gate)
  - env `FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS=true`
  - `"disable_analytics": true` in freerouting.json. The file on disk currently says **false**, because the CLI flag is in-memory only and is never saved.

Update check: there is **no switch** in v2.1.0. To block it, block the network (see below).

API server:
- It is `api_server.enabled=false` by default, so **nothing listens by default**.
- If enabled, the default endpoint is `https://0.0.0.0:37864`. HTTPS is not implemented and "falls back to HTTP", so it would be an unauthenticated plain-HTTP Jetty/Jersey server on all interfaces.
- Our freerouting.json has `enabled: false`.

## 3. Filesystem (outside -de/-do)

The user-data dir defaults to `${java.io.tmpdir}/freerouting`, which is `/tmp/freerouting` here. It can be overridden with `--user_data_path=DIR` or env `FREEROUTING__USER_DATA_PATH`. Nothing goes into `~` (`~/.freerouting` does not exist).

| Path | Contents now |
|---|---|
| `/tmp/freerouting/freerouting.json` (1.7 KB, 2026-11-10 14:10) | Settings. `profile.id` is a random UUID (redacted here), `email` is "", `allow_telemetry` true, `disable_analytics` false, `api_server.enabled` false, `gui.enabled` true, router defaults, statistics start time, version 2.1.0. It is rewritten when the version differs. |
| `/tmp/freerouting/freerouting.log` | **960 MB, 329k lines**, appended by every run. log4j File appender at DEBUG, `bufferSize=1`. Most of it is "Autorouter Failed to route connection ..." debug lines. It also holds command lines with relative board paths. Mode 664, readable by other local users. |
| `/tmp/freerouting/snapshots/` | Empty. It would hold intermediate `snapshot-<crc>.frb` files. |

Notes on logging flags:
- `-ll LEVEL` changes only the **console** appender in v2.1.0 (`FRLogger.changeFileLogLevel` replaces the "Console" ref). The file log stays at DEBUG.
- `-dl` disables FRLogger entirely, console included.
- The per-board `hw/board_*/freerouting*.log` files are our own redirect of stdout.
- In GUI and save paths, `.rules`, `.frb` and `.scr` files can be written next to the output file. The CLI path writes only the -do file.

## 4. Code execution and dangerous APIs (app/freerouting/**)

- **Runtime.exec / ProcessBuilder:** none.
- **System.load / loadLibrary:** none in app code. Only the bundled grpc and conscrypt libraries load native code, and only on their own paths.
- **URLClassLoader / defineClass / Class.forName / javax.script:** none.
- **Reflection:** `management/ReflectionUtil` sets settings fields named by CLI/env keys (`setAccessible`). It is limited to the GlobalSettings object tree and is not a loader.
- **Java deserialization (ObjectInputStream):**
  - `RoutingBoard.deepCopy` deserializes only bytes it serialized itself, so it is safe.
  - `BasicBoard.deserialize` is an in-memory copy.
  - `gui/BoardFrame` loads `.frb` "Freerouting binary" files with readObject. This is a deserialization risk **only if you open untrusted .frb files**. It is not used for `-de *.dsn`.
- **Inbound network:** Jetty only if `api_server.enabled=true`.
- **Bundled dependencies:** log4j-core 2.24.3, which postdates Log4Shell. The log4j2.xml has no lookups of user input.

## 5. Recommendations

1. Run it network-isolated. Both mechanisms were tested on this machine, and both leave only `lo` in the namespace:
   - `unshare -rn` (unprivileged user plus network namespace), or
   - `systemd-run --user -p PrivateNetwork=yes -p PrivateUsers=yes`.

   Avoid relying on `-p IPAddressDeny=any`: in `--user` units, systemd 255 cannot attach the BPF firewall unprivileged, so it is not enforced. With the network blocked, the version check just prints a stack trace to stderr, and routing is unaffected.
2. Keep `--usage_and_diagnostic_data.disable_analytics=true` and add `--profile.allow_telemetry=false`. That is belt and braces, and also covers runs like `--help`.
3. Pin settings with `--user_data_path=<project dir>/.freerouting` so nothing lands in world-readable `/tmp`. Pre-seed its freerouting.json with:
   - `"disable_analytics": true`
   - `"allow_telemetry": false`
   - `"api_server": {"enabled": false}`
   - `"gui": {"enabled": false}`
4. Delete or rotate the 960 MB `/tmp/freerouting/freerouting.log`. Use `-dl` if the stdout progress output is not needed. `-ll` does not reduce the file log.
5. Defence in depth when namespaces are unavailable: `-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9`. Both HttpClient and HttpURLConnection honour it, so outbound HTTPS fails fast.
6. Don't open `.frb` files from untrusted sources.

Recommended invocation:

```
systemd-run --user --unit=freerouting-a --wait --collect \
  -p MemoryMax=4G -p MemorySwapMax=0 -p PrivateNetwork=yes -p PrivateUsers=yes \
  -p WorkingDirectory=/home/kaveh/claude_out_remote/esp32_sdr/hw \
  /home/kaveh/tools/freerouting/jdk-21.0.13+9-jre/bin/java -Xmx3g \
    -Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9 \
    -jar /home/kaveh/tools/freerouting/freerouting.jar \
    --user_data_path=/home/kaveh/claude_out_remote/esp32_sdr/hw/.freerouting \
    --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true \
    --profile.allow_telemetry=false --api_server.enabled=false \
    -de board_a/board.dsn -do board_a/board.ses -mp 100
```

If you don't need systemd, use `unshare -rn java ...` with the same java args.

## Evidence locations

- Scratch extraction: `/tmp/claude-1000/-home-kaveh-claude/73262aa8-2faf-4273-a4fa-c18966225833/scratchpad/fr_audit/x/`
- Upstream source: `.../fr_audit/src/`, key files:
  - `src/main/java/app/freerouting/Freerouting.java`
  - `management/VersionChecker.java`
  - `management/analytics/*.java`
  - `settings/{GlobalSettings,UsageAndDiagnosticDataSettings,UserProfileSettings,ApiServerSettings}.java`
  - `src/main/resources/log4j2.xml`
- Upstream jar copy: `.../fr_audit/upstream/freerouting-2.1.0.jar`
