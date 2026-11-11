# CHANGELOG

<!-- version list -->

## v0.40.0 (2026-11-11)

### Bug Fixes

- **code-intelligence**: Check a Node server's version without native addons
  ([`c5ca236`](https://github.com/bkuberek/coding-study/commit/c5ca23685b843acc841bbd9e4d81a68d01097e12))

- **code-intelligence**: Read the tooling API version from the Linux build alone
  ([`63068f9`](https://github.com/bkuberek/coding-study/commit/63068f935731507442aeda31a68b993093f0c40f))

- **problems**: List 0310 among the related versions of 0278, 0305 and 0306
  ([`6349a6a`](https://github.com/bkuberek/coding-study/commit/6349a6ab19ccc83f0fe6b73f5033a420caff17c8))

- **runners**: Give Go and Rust runners a generous wait to say hello
  ([`24d7bf8`](https://github.com/bkuberek/coding-study/commit/24d7bf8e84b1d0383a23aa471bd7f2e1708a60ba))

### Documentation

- Catalog at 325 with 0311 hash-chaining ledger
  ([`dba6c62`](https://github.com/bkuberek/coding-study/commit/dba6c623299b1a3bf2371f79ce1ad24d9c0f1ba6))

- Catalog at 331 with 0310 to 0316, P13 problems on the roadmap
  ([`c63606f`](https://github.com/bkuberek/coding-study/commit/c63606f3a499a97363a6b14cbb0aeba25b3d5366))

- Name the docker_go marker beside docker_jvm
  ([`8e72aa6`](https://github.com/bkuberek/coding-study/commit/8e72aa6d396d3fd960e1e66b97c28a941ff6a144))

- P13 built, with GOPROXY=off and the module cache settled
  ([`d04d81c`](https://github.com/bkuberek/coding-study/commit/d04d81cffd211da8c0ae9fcd19cdcb766e92a8f2))

### Features

- **code-intelligence**: A route table for every kind of problem in every language
  ([`687b22e`](https://github.com/bkuberek/coding-study/commit/687b22e140c033420e8c8c48b62c3ddfaeed4f4d))

- **code-intelligence**: Gopls in a Go service project's sidecar
  ([`14ef62d`](https://github.com/bkuberek/coding-study/commit/14ef62dce95b73bc7da4c8f30a0b4181fc8efd97))

- **code-intelligence**: JDT LS in a Java service project's sidecar
  ([`b666c68`](https://github.com/bkuberek/coding-study/commit/b666c685478ac354838c6de659d1d5390ab8f5ce))

- **code-intelligence**: The Kotlin LSP's Linux build in a Kotlin service project's sidecar
  ([`485d258`](https://github.com/bkuberek/coding-study/commit/485d258791e38f46e59e21665f35372184b1c878))

- **code-intelligence**: Warm the default language's server up in cstudy serve
  ([`b450131`](https://github.com/bkuberek/coding-study/commit/b45013119c0aa141930e180d6bf1073d14af1c7d))

- **problems**: Add 0311 tamper-evident ledger
  ([`c055498`](https://github.com/bkuberek/coding-study/commit/c055498b731ab4e3a9b992b24cce95b2df5c927d))

- **problems**: Add 0312 feed-ingest-python service project
  ([`1afccfe`](https://github.com/bkuberek/coding-study/commit/1afccfe16d2d2bd945e97cd1be2bf4f8af427482))

- **problems**: Add 0313 org-chart-outline progressive problem
  ([`21be234`](https://github.com/bkuberek/coding-study/commit/21be234946ab8cb44800f46c7e54721921f052ef))

- **problems**: Add 0314 referral-rewards progressive problem
  ([`5123e3f`](https://github.com/bkuberek/coding-study/commit/5123e3faad1ef8782c3664f202954ebca296daf5))

- **problems**: Add 0315 safe-redaction-python project
  ([`242eae0`](https://github.com/bkuberek/coding-study/commit/242eae0bef129a0344465865a0ead36b98315b6d))

- **problems**: Add 0316 water-on-terrain progressive problem
  ([`2d0d5ac`](https://github.com/bkuberek/coding-study/commit/2d0d5aceb3891193e0c07ec62b292762082aa89d))

- **problems**: Coworking availability in Go
  ([`e4d23e0`](https://github.com/bkuberek/coding-study/commit/e4d23e091c524d42c687d456f8cf2c25e0fcf228))

- **project**: Go service template
  ([`553778b`](https://github.com/bkuberek/coding-study/commit/553778b37f38323397f0ee6aae35a2100d927a2a))

- **sandbox**: Go modules from the install cache, offline outside install
  ([`fc6b72b`](https://github.com/bkuberek/coding-study/commit/fc6b72b578f4bfdb1b25a694ece89c1bcc1309f6))

### Testing

- A Go service fixture on a real engine
  ([`412d58b`](https://github.com/bkuberek/coding-study/commit/412d58b39de6f201361853e4af594ba6045bd85f))

- Browser labs opt into the warm-up, and one test in each engine proves it
  ([`208bc1f`](https://github.com/bkuberek/coding-study/commit/208bc1fe1be1c394d50ed6c21f14c3b4d15f6931))

- Give every language's runners the generous wait to start
  ([`7611640`](https://github.com/bkuberek/coding-study/commit/76116400819c0d39c3f2735647d2b53436d4ff11))

- Give the crash-without-bye case a generous hang guard
  ([`e8eb0b3`](https://github.com/bkuberek/coding-study/commit/e8eb0b3f58a83124d302e28b8af5ee66602bd420))


## v0.39.0 (2026-11-10)

### Continuous Integration

- Keep the real-engine JVM tests out of the sandbox job
  ([`2478eef`](https://github.com/bkuberek/coding-study/commit/2478eef10487b68cc2f77a19e7544641255e53c6))

- Run the browser job when the shared test waits change
  ([`df94395`](https://github.com/bkuberek/coding-study/commit/df94395cd77364c0ecefe3af42d118d2b36f5443))

### Documentation

- Catalog at 324 with 0305 to 0309, P12 and PP14 ticked, cstudy new target noted
  ([`496d52c`](https://github.com/bkuberek/coding-study/commit/496d52ce784279ed24b1e4363626cd270f4d86c0))

- P12 built, with Gradle's --offline settled and measured
  ([`a9ec367`](https://github.com/bkuberek/coding-study/commit/a9ec367f07777d12deea05420a65dcace9a9f53e))

### Features

- **problems**: Add 0307 fix the flaws, a security-fix round on a notes service
  ([`2584583`](https://github.com/bkuberek/coding-study/commit/25845836ef300a3af6b6ed3ab5638585b1d3d3ff))

- **problems**: Add 0308 all-grid-paths, listing every right-and-down route in order
  ([`5c27bda`](https://github.com/bkuberek/coding-study/commit/5c27bda3aff9bfe90aa9873f3f2dc9c9e08aeada))

- **problems**: Add 0309 find-missing-and-duplicates with cyclic sort
  ([`30b28a2`](https://github.com/bkuberek/coding-study/commit/30b28a2dd119bc47317e5c9e661f75e71f3316fa))

- **problems**: Coworking availability in Java and Kotlin
  ([`8eec5d5`](https://github.com/bkuberek/coding-study/commit/8eec5d553422f570334829d14ffbcbf51379b1bd))

- **project**: Java and Kotlin service templates
  ([`a7d41c7`](https://github.com/bkuberek/coding-study/commit/a7d41c76c4b8ddf225510257cc839206826d4609))

- **project**: Size the Kotlin service template as measured
  ([`7a835ca`](https://github.com/bkuberek/coding-study/commit/7a835caaa58beea4d97bd14dcaada52de68620c4))

- **sandbox**: Gradle's install cache and lock for JVM service projects
  ([`8dce9a9`](https://github.com/bkuberek/coding-study/commit/8dce9a9152c5e6b13b6efd2892e09932337f8ae1))

### Testing

- A Java service fixture on a real engine
  ([`62f5619`](https://github.com/bkuberek/coding-study/commit/62f5619493b92645393b2083a08a58a63f1deb0e))

- Keep the coworking drift guard's docstring within the line limit
  ([`5442323`](https://github.com/bkuberek/coding-study/commit/5442323f5afac0bc5e30bc3aee761449e23ade9d))

- Run the sandbox job when devcontainer.json's code changes
  ([`3d701bf`](https://github.com/bkuberek/coding-study/commit/3d701bfe476506656c92cf70771731921aa0b4f6))


## v0.38.0 (2026-11-10)

### Continuous Integration

- Run the service-step test in the sandbox job with the fixture's Redis pulled first
  ([`8091af7`](https://github.com/bkuberek/coding-study/commit/8091af7ebb7627806f344d762f254a1b4b219b84))

### Documentation

- Catalog at 319 with 0304, P9 leftovers and engine gaps ticked on the roadmap
  ([`86dfa80`](https://github.com/bkuberek/coding-study/commit/86dfa8084947b174266c063bc50ef706d1e7e5df))

- Describe service projects in the web ui guide
  ([`0e248de`](https://github.com/bkuberek/coding-study/commit/0e248de05ab449ae19320cee2c1aa29f0dde3018))

- Mark P11's AI problems built in ADR 0019's status
  ([`cc4d71b`](https://github.com/bkuberek/coding-study/commit/cc4d71b1eb4981f928d7be2ae3de5535e7af4fa4))

- Plan frontend problems graded in a headless browser on the roadmap
  ([`31e11e1`](https://github.com/bkuberek/coding-study/commit/31e11e11dfb346494a727b72a5b61f12d895d366))

### Features

- **cli**: Add cstudy dev's --no-run, --debug, --reset-data and --exec, and a devcontainer.json
  ([`7512391`](https://github.com/bkuberek/coding-study/commit/75123913144bbbdfbd72448c1880ba80c219ac13))

- **grader**: Pause, stop and start a backing service mid-case
  ([`9743f02`](https://github.com/bkuberek/coding-study/commit/9743f02780265df05aa62643690a70be1b3441d7))

- **grader**: Restart only the app between cases with restart: app
  ([`4ce8579`](https://github.com/bkuberek/coding-study/commit/4ce8579b580a86114b07d563c2f075334a80ef30))

- **grader**: Send a binary request body written as base64
  ([`f6a1171`](https://github.com/bkuberek/coding-study/commit/f6a1171356e18c3adf5a4d65e5bc90a01176f983))

- **grader**: Wait inside a multi-step case with a sleep step
  ([`1ca5589`](https://github.com/bkuberek/coding-study/commit/1ca558906690baf363170f9d74de273b2e472c96))

- **problems**: Add 0304 search box with keyboard navigation
  ([`de8b66f`](https://github.com/bkuberek/coding-study/commit/de8b66f383a02003afb5f4b0374f5515dd02d09a))

- **project**: Set basedpyright's standard mode in Python service starters
  ([`1809000`](https://github.com/bkuberek/coding-study/commit/1809000339f1b107956bbee6c37d41f0b033c54f))

- **sandbox**: Pause, unpause, stop and start one backing service of a stack
  ([`3a642bd`](https://github.com/bkuberek/coding-study/commit/3a642bda5e4d4e504880629a067a180533afa84e))

### Refactoring

- **grader**: Name the stack step type without a forward reference
  ([`e38eb33`](https://github.com/bkuberek/coding-study/commit/e38eb33e2aa7ef0c796a893969c63bbd610b3d21))

### Testing

- Wait generously for host version checks and stream frames
  ([`d5e8ac0`](https://github.com/bkuberek/coding-study/commit/d5e8ac05527be3dc53721c81df1404ad6fa74d9b))

- Wait generously for the dev stack panel under load
  ([`2f08ca0`](https://github.com/bkuberek/coding-study/commit/2f08ca0a92d492008b5e396d89cc6dde2a9ea841))


## v0.37.0 (2026-11-10)

### Bug Fixes

- **problems**: Keep the 0300 and 0303 summaries within the 200-character header cap
  ([`dfd85a4`](https://github.com/bkuberek/coding-study/commit/dfd85a49a807418d49719a07bf9847f668425549))

- **web**: Keep the dev stack panel's heading on one line
  ([`2ac693e`](https://github.com/bkuberek/coding-study/commit/2ac693e6a9872777781fd9b2078faff25946a22e))

### Code Style

- **problems**: Wrap long lines in the 0299 and 0301 references
  ([`81c3a94`](https://github.com/bkuberek/coding-study/commit/81c3a94284ac43d2d0a8fae9b798f5e8db06c43e))

### Continuous Integration

- Run the browser job on the sandbox fakes and the sandbox job on the dev stack and sidecar modules
  ([`a80ac5a`](https://github.com/bkuberek/coding-study/commit/a80ac5ac149641d34199f66e9325f27345760eeb))

### Documentation

- Catalog at 318 with 0293 to 0303, P9 ticked, and P12 to P14 next
  ([`47e01bf`](https://github.com/bkuberek/coding-study/commit/47e01bfc40396b51bf376321c917e9c13c456230))

- Code intelligence for service projects runs in a sidecar, built in P9
  ([`e88a4c0`](https://github.com/bkuberek/coding-study/commit/e88a4c0171a87255bdf3ba7ed74267670fd697be))

- Mark P9 built, with its code intelligence and Web UI in ADR 0019 and the spec
  ([`e001550`](https://github.com/bkuberek/coding-study/commit/e00155035d1d552bfbef85879937d9066e094243))

- Name cstudy dev's --events flag in its synopsis and flag table
  ([`5736930`](https://github.com/bkuberek/coding-study/commit/57369307f7161d529e9770d8e02c126b27d1edb2))

### Features

- **cli**: Stream a service project's cstudy test as events and JSON
  ([`20307ba`](https://github.com/bkuberek/coding-study/commit/20307ba69397dffa33fb8b6f82fa0eb64edb91db))

- **code-intelligence**: Judge a service project's servers as its sidecar runs them
  ([`68bbd15`](https://github.com/bkuberek/coding-study/commit/68bbd153395cc513c6b32fe51f05a7681ed98566))

- **code-intelligence**: Run a service project's TypeScript and Python servers in a sidecar
  ([`9834de5`](https://github.com/bkuberek/coding-study/commit/9834de580fa3edebb9940616ad2258891a899cfa))

- **code-intelligence**: Show a service project's waiting server calmly in the editor
  ([`f2ffe6c`](https://github.com/bkuberek/coding-study/commit/f2ffe6cac731d04277c642040e52ecfa6d8861cf))

- **problems**: Add 0293 memory store, a four-level progressive practice set
  ([`a4b8efb`](https://github.com/bkuberek/coding-study/commit/a4b8efb380ca8608bef3732b37b11ec1df62fb87))

- **problems**: Add 0294 chat history index, a four-level progressive practice set
  ([`951969e`](https://github.com/bkuberek/coding-study/commit/951969e0e25cc5895a84610d6a9208bfe04b0f65))

- **problems**: Add 0295 context packer, a four-level progressive practice set
  ([`95f4950`](https://github.com/bkuberek/coding-study/commit/95f49500cbf5bf6aa4192daf829e668b9acbb9ad))

- **problems**: Add 0296 memory facts with merge, a four-level progressive store
  ([`3c708f3`](https://github.com/bkuberek/coding-study/commit/3c708f3cbd7cae12b2f31d0328ffab9d98f72599))

- **problems**: Add 0297 forgettable inverted index with BM25 over live statistics
  ([`a6668c9`](https://github.com/bkuberek/coding-study/commit/a6668c92dc56c9f228048d6719026884655191ef))

- **problems**: Add 0298 memory write sanitizer, a defensive step before storing
  ([`6294a62`](https://github.com/bkuberek/coding-study/commit/6294a62cf881fc053941f33e93109ec86939cba7))

- **problems**: Add 0299 cosine top k with a bounded heap, oracle and ladder
  ([`a71857f`](https://github.com/bkuberek/coding-study/commit/a71857f1375a24992840b63f97259da1064c2c39))

- **problems**: Add 0300 chunking with overlap and sentence-aware cuts
  ([`87bd951`](https://github.com/bkuberek/coding-study/commit/87bd951ccbddf361ca5728980b742400d73af952))

- **problems**: Add 0301 retrieval metrics with recall, MRR and graded nDCG
  ([`f2f8dc6`](https://github.com/bkuberek/coding-study/commit/f2f8dc64458afb2b948eb6ce6c9c8bc55f2ea064))

- **problems**: Add 0302 freshness reranker with half-life decay and copy removal
  ([`b308b43`](https://github.com/bkuberek/coding-study/commit/b308b438804bdfa63e97c8c23b45ab120832e5b0))

- **problems**: Add 0303 versioned memory store with compare-and-set writes
  ([`7dff0c5`](https://github.com/bkuberek/coding-study/commit/7dff0c59a7e65758242da328fe709598917c8224))

- **web**: List what a service project needs and say when Docker cannot run it
  ([`91e6142`](https://github.com/bkuberek/coding-study/commit/91e6142cfe8fc0b1e39c598a5ea840d645f0a188))

- **web**: Run a service project's dev stack from the page
  ([`9aa88e5`](https://github.com/bkuberek/coding-study/commit/9aa88e58a42818cf14a1edaacdff7daa9eecf55d))

- **web**: Run tests and submit service projects from the page
  ([`6f9fdae`](https://github.com/bkuberek/coding-study/commit/6f9fdae4277615df81749b6155da34e36a576441))

### Testing

- A definition from the sidecar leads into the project's installed dependencies
  ([`4c7b3f3`](https://github.com/bkuberek/coding-study/commit/4c7b3f35a644b9676f282935a6a446ed27f82052))

- A service project's server answers from inside its sidecar on a real engine
  ([`fefd34e`](https://github.com/bkuberek/coding-study/commit/fefd34e4e841c653de1928b2daf5b8d8ba89251c))

- Check the dev stack's API documents against the web API schema
  ([`8ad92c6`](https://github.com/bkuberek/coding-study/commit/8ad92c6cf337ea3a3e284e2babcc5ea8a29c8131))

- Keep the real sidecar tests where the sandbox CI job runs them
  ([`803ff8c`](https://github.com/bkuberek/coding-study/commit/803ff8cf79cd59cdeb5b26783340996e5566a90f))

- Keep the schema test's dev stack lines within the line length
  ([`842ef67`](https://github.com/bkuberek/coding-study/commit/842ef6715f57ca3cf5a74a02a0bfa2c998eb7b03))

- Stream a real service project's cstudy test as events
  ([`887d437`](https://github.com/bkuberek/coding-study/commit/887d437954a1e9911bf458c87bda4299849d072c))


## v0.36.0 (2026-11-10)

### Documentation

- Bring the README's practical count, ADR 0020's catalog link and Phase 12 status up to date
  ([`424cdee`](https://github.com/bkuberek/coding-study/commit/424cdee799f5bf0669ad7e50da4db66b96cfdc93))

- Catalog at 307 with 0289 to 0292, P11 built, PP11 to PP13 and PP15 ticked, and service-project
  known limits
  ([`6c9fa86`](https://github.com/bkuberek/coding-study/commit/6c9fa86a755674befa5752b523f02ee6b9f1b4de))

### Features

- **grader**: Assert on what a logged request's JSON body carried
  ([`6dc3e43`](https://github.com/bkuberek/coding-study/commit/6dc3e434ae1c0b54d16700cd7f57678e3ec8bdf5))

- **grader**: Limit the time to a response's first body byte
  ([`f3ff656`](https://github.com/bkuberek/coding-study/commit/f3ff656b4a323843b2766572b81f0d30874e1670))

- **mock-server**: Fill in run-time values in mock responses
  ([`9b8f457`](https://github.com/bkuberek/coding-study/commit/9b8f457427106b99b05e5d89838846be0311d220))

- **mock-server**: Match routes on JSON request bodies
  ([`cae6505`](https://github.com/bkuberek/coding-study/commit/cae65052ea9400a537487820260bdae96de551d2))

- **mock-server**: Ship an example mock LLM provider config
  ([`42c052d`](https://github.com/bkuberek/coding-study/commit/42c052dc5bbd9aff434395368e4acc98d87c53f6))

- **mock-server**: Stream server-sent events with drop and stall scenarios
  ([`46d6ed8`](https://github.com/bkuberek/coding-study/commit/46d6ed88c0c2fa71cd75709d0bd10d587577eabd))

- **problems**: Add 0289 secure file upload, a TypeScript service project
  ([`859a133`](https://github.com/bkuberek/coding-study/commit/859a133b4780b01c27404d091e9cbc7b7fe678d0))

- **problems**: Add 0290 LLM gateway in TypeScript (PP11)
  ([`5647e68`](https://github.com/bkuberek/coding-study/commit/5647e6882114376d93b3a2d46521e1deb5d444dd))

- **problems**: Add 0291 rag service with citations in TypeScript
  ([`8ae07d0`](https://github.com/bkuberek/coding-study/commit/8ae07d0290f3b6862bcb466a08b6194cbdf19d30))

- **problems**: Add tool-calling agent loop project 0292
  ([`60171bc`](https://github.com/bkuberek/coding-study/commit/60171bcac3b329dcf7ab1922a4e7076efc12513d))

- **problems**: Time the first byte of 0290's slow stream
  ([`6f02cdb`](https://github.com/bkuberek/coding-study/commit/6f02cdb5d2e673fbad126a7593ecb774bb5734fd))

### Testing

- Give Rust runners the generous wait to start
  ([`1872f5b`](https://github.com/bkuberek/coding-study/commit/1872f5b0afad29597617f98413cfb7f8caf26788))


## v0.35.0 (2026-11-10)

### Documentation

- Catalog at 303 with 0283 to 0287, PP6 to PP10 ticked, and service-project known limits and Valkey
  note
  ([`7ff3ac0`](https://github.com/bkuberek/coding-study/commit/7ff3ac013e88ae091768348a550a062d706fb982))

### Features

- **problems**: Add 0283 job queue on Postgres (PP6)
  ([`3aae480`](https://github.com/bkuberek/coding-study/commit/3aae480d5676b17e371140f4a2138acfeaa8a916))

- **problems**: Add 0284 CSV upload ingestion on S3, SQS and Postgres (PP7)
  ([`2851bc9`](https://github.com/bkuberek/coding-study/commit/2851bc942996e3587b9af252f96e37484eded842))

- **problems**: Add 0285 price cache and rate limits on Valkey (PP9)
  ([`c9304b4`](https://github.com/bkuberek/coding-study/commit/c9304b4e5ea62ca7aad2a7e76bc85f3d3776cbfd))

- **problems**: Add 0286 multi-tenant API on Postgres with row-level security (PP8)
  ([`95f7a74`](https://github.com/bkuberek/coding-study/commit/95f7a74792dbe28dcf3dada01d2eed3736befab5))

- **problems**: Add 0287 event-sourced ledger on Postgres (PP10)
  ([`a098b12`](https://github.com/bkuberek/coding-study/commit/a098b12f0971b0b9adb8d567134e2d79211050e6))


## v0.34.0 (2026-11-10)

### Documentation

- Backing services are built, with measured numbers
  ([`0535ccd`](https://github.com/bkuberek/coding-study/commit/0535ccde3ac7215857adeabc0bac1c2a7fee664c))

- Catalog at 298 with 0280 and 0282, PP3 and PP5 ticked, and Keycloak, stateless-service and
  Liquibase notes
  ([`7508e7f`](https://github.com/bkuberek/coding-study/commit/7508e7f74b6580433619c9c41bee7c93b16f3fb1))

- Mark R34 and P11's grader part built in ADR 0019
  ([`3e1da04`](https://github.com/bkuberek/coding-study/commit/3e1da04b7e1d5f74d8e06e4fbad9ee92de363647))

- P10 and P11 meet through grader_reach, and P10 is ticked
  ([`a23b44c`](https://github.com/bkuberek/coding-study/commit/a23b44c790bc6f75ad00fa38a480a4b76b75be26))

### Features

- **grader**: Check what the app prints during a case
  ([`fe02819`](https://github.com/bkuberek/coding-study/commit/fe02819d76f5ebb53bca251b82be667ee96bac7e))

- **grader**: Let a parallel burst take several requests in turn
  ([`6a8050d`](https://github.com/bkuberek/coding-study/commit/6a8050d945635561b079e50c51516215ecad269a))

- **grader**: Multi-step HTTP cases with captures, cookie jars, flows and cleanup
  ([`ba92407`](https://github.com/bkuberek/coding-study/commit/ba92407d4d2706c40f6b063cdb821f3567875dca))

- **grader**: Parallel cases that send a burst at once and count its statuses
  ([`828a268`](https://github.com/bkuberek/coding-study/commit/828a268f73caeae306235cf7a3e78d58e61cdd19))

- **grader**: Reach the origins grader_reach publishes, and declare only those
  ([`cecdd1c`](https://github.com/bkuberek/coding-study/commit/cecdd1c2afe1294564a2988f8156ef4ad178a0b2))

- **grader**: Show a parallel case's expected counts as its report shows them
  ([`4dcaf77`](https://github.com/bkuberek/coding-study/commit/4dcaf77328d1d7bb92e31082f0bb61aad919c8aa))

- **mock-server**: Pass requests through to an upstream and spoil a JWT in flight
  ([`3d25dee`](https://github.com/bkuberek/coding-study/commit/3d25dee3375277e8f49f7617eb15458014d5190e))

- **problems**: Add 0280 oauth-pkce-client-typescript, graded against Keycloak
  ([`603db83`](https://github.com/bkuberek/coding-study/commit/603db837e4c404af354f21b4fd41bd17d516d6d3))

- **problems**: Add 0282 inventory reservations on Postgres (PP5)
  ([`dc8f86f`](https://github.com/bkuberek/coding-study/commit/dc8f86f2c833527ceaaeae8840f2b892a1f2c226))

- **sandbox**: A fresh start removes the dev stack's data
  ([`0024c22`](https://github.com/bkuberek/coding-study/commit/0024c2278dc560f3177b1f194603c967e4744f12))

- **sandbox**: A mock server's upstream names a service of the compose file
  ([`73304c4`](https://github.com/bkuberek/coding-study/commit/73304c402c76103c72e4d0ad4528bafa733250f8))

- **sandbox**: Finish S21 and S22 so a services file stays in the sandbox
  ([`75e7012`](https://github.com/bkuberek/coding-study/commit/75e70123a2df9bee48f99b6f725cd70816978689))

- **sandbox**: Merge a problem's backing services into its stack
  ([`b506fce`](https://github.com/bkuberek/coding-study/commit/b506fced18f53afc1ebab55a8541e66480657fb4))

### Refactoring

- **grader**: Say plainly when a step has no expectation to fill in
  ([`f69fc08`](https://github.com/bkuberek/coding-study/commit/f69fc0812f69a7bd10175b8ee0a315c4f789e210))

- **sandbox**: Say why a pass-through's upstream is a backing service
  ([`24a211d`](https://github.com/bkuberek/coding-study/commit/24a211d0931e1fdb2e5e436439a07f865e9c686b))

### Testing

- A service project fixture with Postgres and Redis on a real engine
  ([`40374e8`](https://github.com/bkuberek/coding-study/commit/40374e89ecd1cca72e4cc3e5d0abff596211bb1d))

- Grade a case through grader_reach, a pass-through and the app's output on a real engine
  ([`53bb438`](https://github.com/bkuberek/coding-study/commit/53bb43863fb95e4a7df539cf93b9d1a13876d6c6))

- Grade a login flow end to end on loopback with tampering and an output check
  ([`ea3904a`](https://github.com/bkuberek/coding-study/commit/ea3904a23efc93c020b5c0907a0da49eccc4c315))

- Read the app's output in the real Docker tests the CI job runs
  ([`99aa94f`](https://github.com/bkuberek/coding-study/commit/99aa94fa653ef1e1b7397a130a61c59645e01d92))


## v0.33.0 (2026-11-09)

### Bug Fixes

- **web**: Exit 130, not by SIGINT, when Cancel lands while a run starts
  ([`a4b4c4c`](https://github.com/bkuberek/coding-study/commit/a4b4c4c19b617b913dd1756ce1f4fd5d431e8932))

### Documentation

- List 0279 and 0281, move PP3 and set the catalog at 296
  ([`1084f22`](https://github.com/bkuberek/coding-study/commit/1084f22eaa9503aecb904e4abb398c4845066ae7))

### Features

- **problems**: Add a payment webhook receiver in TypeScript
  ([`67b0c47`](https://github.com/bkuberek/coding-study/commit/67b0c47af8aba2578f3a19d495c57b065eff0baa))

- **problems**: Add an SSRF-safe webhook dispatcher in TypeScript
  ([`1560065`](https://github.com/bkuberek/coding-study/commit/1560065bdb35fec01cf29aa7df01e32f4b68c88e))

### Testing

- Wait for the idle toolbar after each run in the diagnostics browser test
  ([`4115cc7`](https://github.com/bkuberek/coding-study/commit/4115cc7999d9d33ee701965c4c0383b155146b88))

- Wait until the button reads Run again before the next run in the browser tests
  ([`75018d4`](https://github.com/bkuberek/coding-study/commit/75018d4f9ba45c7cbeb7b22291054f73caf3bf3f))


## v0.32.0 (2026-11-09)

### Chores

- **showcase**: Take a Kotlin hover shot and Settings with Kotlin ready, for cstudy 0.31
  ([`1aef8bd`](https://github.com/bkuberek/coding-study/commit/1aef8bd87e9ed3b117d20926856962a6a9b40f4e))

### Documentation

- Say doctor --fix renews an expired Kotlin LSP build in the web UI spec
  ([`680293d`](https://github.com/bkuberek/coding-study/commit/680293d29097074ba5cae6826d884506523c347d))

### Features

- **problems**: Add coworking availability in Python, completing P8
  ([`db588b1`](https://github.com/bkuberek/coding-study/commit/db588b170f1e14db219cbdcfa3640efc7e70694a))

### Testing

- Read doctor's help without the styles a forced terminal adds
  ([`6dec3ff`](https://github.com/bkuberek/coding-study/commit/6dec3ffcc9d0ad0d88f922f4321ac8d0bdb8e379))


## v0.31.0 (2026-11-09)

### Documentation

- Measure doctor --fix fetching the newest Kotlin LSP build
  ([`e29ba71`](https://github.com/bkuberek/coding-study/commit/e29ba71296929c420481701d3fe0218b67251e72))

- Measure the Kotlin LSP offline, in a project folder and past its expiry
  ([`1955407`](https://github.com/bkuberek/coding-study/commit/1955407ebe102ff65a54168cc8c3745f913af28f))

- Record the Kotlin servers spiked for ADR 0018 and the choice of the Kotlin LSP
  ([`f796c05`](https://github.com/bkuberek/coding-study/commit/f796c05e24f4857458095f1ad76cb37724147ce6))

### Features

- **code-intelligence**: Fetch JetBrains' newest Kotlin LSP build, checked by its published SHA-256
  ([`f322e12`](https://github.com/bkuberek/coding-study/commit/f322e12aaae044bb37e5885dc6227887477a1d61))

- **code-intelligence**: Kotlin through JetBrains' Kotlin LSP, behind a license you accept
  ([`6ddab5c`](https://github.com/bkuberek/coding-study/commit/6ddab5cf7a78779f500cd2d3fd1a05691985e54b))

- **code-intelligence**: Say plainly when the pinned Kotlin LSP build has expired
  ([`51361d3`](https://github.com/bkuberek/coding-study/commit/51361d3de9de891f834c2dcffff01ae999b8c506))

### Refactoring

- **code-intelligence**: Word the expired Kotlin state for fetched builds
  ([`dd696a6`](https://github.com/bkuberek/coding-study/commit/dd696a63fc132f8ba3e59b38c764f85b949aefd5))

### Testing

- Drive Kotlin code intelligence in Chromium and against the real Kotlin LSP
  ([`2b7aa1d`](https://github.com/bkuberek/coding-study/commit/2b7aa1dccc9ba2714616d784eed72cb35538791f))

- Expect Kotlin's license state in the browser tests
  ([`662589e`](https://github.com/bkuberek/coding-study/commit/662589ec57b2fa23bc12fcbcacdc00d9614f1b9d))

- Import the practice workspace's Gradle build in the real Kotlin LSP test
  ([`7e4f1cf`](https://github.com/bkuberek/coding-study/commit/7e4f1cfd6e56594b2ea6bc2854f323c813059256))


## v0.30.2 (2026-11-08)

### Bug Fixes

- **sandbox**: Read the engine as running only when docker info prints a version
  ([`dbcbf97`](https://github.com/bkuberek/coding-study/commit/dbcbf97d01fdb8ff0ed1e909dacd11f765ee9eda))

- **sandbox**: Wait for a version, not exit 0, after starting the engine
  ([`6a9467e`](https://github.com/bkuberek/coding-study/commit/6a9467ecf28d9625af1dfcbfa1355fd874730e8b))

### Documentation

- Add CI, release, license and Homebrew badges to the README
  ([`df66256`](https://github.com/bkuberek/coding-study/commit/df6625694c5ae89dcb5f265f1f1ec259b48a0176))


## v0.30.1 (2026-11-08)

### Bug Fixes

- **sandbox**: Start rootless Docker, and say sudo only for an engine that needs it
  ([`0d41369`](https://github.com/bkuberek/coding-study/commit/0d41369d36a4ce2605b30968b0711a7a883559c3))

- **sandbox**: Tell a docker group member to log in again, not to join with sudo
  ([`c04a300`](https://github.com/bkuberek/coding-study/commit/c04a300ddc84595ab0084c11ed6b137a056499d0))

### Chores

- **showcase**: Take Go and Rust hover shots, and stop only the daemons this run started
  ([`9b92f07`](https://github.com/bkuberek/coding-study/commit/9b92f07ea7a936f39062ff39d2cbc461f9ef822c))

### Documentation

- Plan fifteen project problems on the roadmap, and tick what has shipped
  ([`38ef478`](https://github.com/bkuberek/coding-study/commit/38ef478394eee63cf0333575c23e6752757ca07b))

- Use Moto for AWS services in service projects, with LocalStack 4.14.0 as the fallback
  ([`ff6a240`](https://github.com/bkuberek/coding-study/commit/ff6a2409f43a49747496f274a376d2d437e47a92))


## v0.30.0 (2026-11-08)

### Bug Fixes

- **code-intelligence**: Ask again for pulls rust-analyzer cancels while it loads
  ([`aa92b2a`](https://github.com/bkuberek/coding-study/commit/aa92b2a0fe8a5e4d020d6d8fd9f9dce5d54e7fb2))

- **code-intelligence**: Give rust-analyzer the standard library through links
  ([`adeed7f`](https://github.com/bkuberek/coding-study/commit/adeed7f6111f7448927cb86abc72c6261b815c20))

### Documentation

- **adr**: Close the standard-library gap of rust-analyzer in ADR 0018
  ([`942bdd1`](https://github.com/bkuberek/coding-study/commit/942bdd1fc87b268e94ff13051fcdbf7723d22deb))

- **adr**: Record phase 3 of ADR 0018 as built, with gopls measured
  ([`d2b2968`](https://github.com/bkuberek/coding-study/commit/d2b2968c3c9b865abbfdfd8e250aaff8198ba8cd))

- **adr**: Record rust-analyzer 1.92.0 as measured in phase 3
  ([`ba4d94d`](https://github.com/bkuberek/coding-study/commit/ba4d94d79f6f525d6ba3494fcea287c53e3c3bee))

### Features

- **code-intelligence**: Go through gopls and Rust through rust-analyzer
  ([`7121e8c`](https://github.com/bkuberek/coding-study/commit/7121e8c580e8d9f4e09369b1348d43781d8b6542))

- **code-intelligence**: Pull diagnostics and documentation links that open library sources
  ([`9d72e70`](https://github.com/bkuberek/coding-study/commit/9d72e7087dbb16ecf6da43f4cd9dda7aee6cd218))

### Testing

- Drive the real rust-analyzer as the page does
  ([`e4cf60e`](https://github.com/bkuberek/coding-study/commit/e4cf60effe5b471123790619261f96a1e442ccc0))


## v0.29.2 (2026-11-08)

### Bug Fixes

- **sandbox**: Turn IPv6 off on the sandbox network and probe for an IPv6 address
  ([`b61af09`](https://github.com/bkuberek/coding-study/commit/b61af09bdb706b8dbb19fea9896add64dd59f22b))

### Documentation

- Describe the IPv6 enforcement and measurement on the sandbox network
  ([`57d0c58`](https://github.com/bkuberek/coding-study/commit/57d0c5855c9f568a0aff1b0056155f9be56c91b3))


## v0.29.1 (2026-11-08)

### Bug Fixes

- **sandbox**: Give the sandbox network's bridge no address of this machine
  ([`47a9df1`](https://github.com/bkuberek/coding-study/commit/47a9df1949a8c8e995b6182e06ac54b1109cd5c4))

- **sandbox**: Send a status line with every mock server error
  ([`a0ee196`](https://github.com/bkuberek/coding-study/commit/a0ee1964e330bc99123c75fa9680703cb642785d))

### Chores

- **showcase**: Take a Java hover shot and Settings with Java ready, for cstudy 0.29
  ([`826715f`](https://github.com/bkuberek/coding-study/commit/826715f0114308e7bce66ead0f9f0a83ff2b48e5))

### Documentation

- Say what the sandbox is measured to do on Linux and what stays unproven
  ([`05458ff`](https://github.com/bkuberek/coding-study/commit/05458ff11ef1d63b809bb39a4d77665c075ab277))


## v0.29.0 (2026-11-08)

### Chores

- **showcase**: Retake the media of cstudy 0.28, with dark animations
  ([`6809b6a`](https://github.com/bkuberek/coding-study/commit/6809b6a05bb3b1c19edcedb85c4281268a064047))

### Documentation

- **adr**: Record the phase 2 spikes of JDT LS and Kotlin LSP
  ([`42f5e07`](https://github.com/bkuberek/coding-study/commit/42f5e07fd2f2e6164b34896f7952399d6ca28c9b))

### Features

- **code-intelligence**: Java through Eclipse JDT LS on JDK 25 and 26
  ([`c8863cb`](https://github.com/bkuberek/coding-study/commit/c8863cb19902446d533fecde7194aac8c193b153))


## v0.28.1 (2026-11-08)

### Bug Fixes

- **web**: Give the run shortcuts 4.5:1 contrast on the Run tests button
  ([`6f5bb5e`](https://github.com/bkuberek/coding-study/commit/6f5bb5e27d2c3eb467aa508807eeda73cb66c783))

- **web**: Mark an edit made while the file's language still loads
  ([`f6e9461`](https://github.com/bkuberek/coding-study/commit/f6e9461b176794f36426a30896c5130e1d1d9ef2))

- **web**: Name the terminal commands of a service project instead of runs
  ([`b6e8946`](https://github.com/bkuberek/coding-study/commit/b6e8946169f1a28437f165bf8d499785cf58170a))

- **web**: Scroll the focus clear of the status bar
  ([`3e2f82a`](https://github.com/bkuberek/coding-study/commit/3e2f82a3c949345673441e846212078a96194d25))

### Documentation

- Say the run-saves browser test edits before the language loads
  ([`82beaba`](https://github.com/bkuberek/coding-study/commit/82beaba576ab90fe9f354bd0b7015757f49e6b6e))

### Testing

- Leave out of axe a target only the top bar covers as the view rests
  ([`f7626bb`](https://github.com/bkuberek/coding-study/commit/f7626bbbd80394ef612c3b58b6a81d1b4808280b))

- Let the completion list take arrows before pressing ArrowDown
  ([`402b64f`](https://github.com/bkuberek/coding-study/commit/402b64f9969898f86ea980c890aecaa2dfecf494))

- Open the lint panel with the M a keyboard sends under Shift
  ([`6a0e7cc`](https://github.com/bkuberek/coding-study/commit/6a0e7cc3e1c5915296d6241ea45d4114aff50d20))


## v0.28.0 (2026-11-07)

### Bug Fixes

- **cli**: Name cstudy dev and cstudy test as a service project's next step
  ([`3e63cc6`](https://github.com/bkuberek/coding-study/commit/3e63cc63edcddf3d28767b9aaa4049668a53feac))

- **grader**: Run D9's test command with the control interface
  ([`79de5d2`](https://github.com/bkuberek/coding-study/commit/79de5d2295c4162db9c16bda3759153ae69a443b))

- **sandbox**: Count the helper image at the 43 MB it measures
  ([`67df405`](https://github.com/bkuberek/coding-study/commit/67df40550d16ceba1a6b253a6d78ebd9e30d4f99))

- **verify**: Refuse a .env in any project starter
  ([`a33f92b`](https://github.com/bkuberek/coding-study/commit/a33f92b39c6e25d908d650614479fc5b86977a5f))

- **web**: Say code intelligence for a service project comes later
  ([`3b2f296`](https://github.com/bkuberek/coding-study/commit/3b2f29631bd41f5dac26b766e50f233fda1673ba))

### Code Style

- **grader**: Sort the imports of verify_service
  ([`3deafb1`](https://github.com/bkuberek/coding-study/commit/3deafb1895410d6fd21e9917665528aa7d9850b3))

### Documentation

- List the browser and sandbox CI jobs and where .env comes from
  ([`91b7a88`](https://github.com/bkuberek/coding-study/commit/91b7a88edc24497f0c873913ac03b9e5bbb704ee))

- **versioning**: List the browser and sandbox jobs of the CI workflow
  ([`aaf6503`](https://github.com/bkuberek/coding-study/commit/aaf650312b589814275ac97069f7c32546d665b3))

### Features

- **problems**: Add coworking availability, the first catalog service project
  ([`d7984d4`](https://github.com/bkuberek/coding-study/commit/d7984d4bf5a3c459113ed04e296a4e3e2233c534))

- **project**: Write a service project's .env from its manifest
  ([`154aa33`](https://github.com/bkuberek/coding-study/commit/154aa33eebe5df6f97a8c569d52ad0ffff3b65b0))

### Refactoring

- **sandbox**: Drop the unused stack kind letters
  ([`b9f9302`](https://github.com/bkuberek/coding-study/commit/b9f9302fc877716309ef98bb42399ab6ff55a7ca))


## v0.27.0 (2026-11-07)

### Features

- **web**: Say who created cstudy on the About view
  ([`9796df7`](https://github.com/bkuberek/coding-study/commit/9796df78250e83db18f0462dbbc8105171846551))

- **web**: Widen the About text so the sponsor line stays on one line
  ([`e1a96f6`](https://github.com/bkuberek/coding-study/commit/e1a96f6b40aeb2ba6531b618758c3b137b32493e))


## v0.26.0 (2026-11-07)

### Features

- **web**: Credit the author at the top of About
  ([`b6bfd8a`](https://github.com/bkuberek/coding-study/commit/b6bfd8af0f6e360e460707b00a82104da3716a93))


## v0.25.0 (2026-11-07)

### Features

- **cli**: Add cstudy about with the version, license, links and credits
  ([`cfcc626`](https://github.com/bkuberek/coding-study/commit/cfcc6264248117fb3c2230810d646d52b6ac9f41))

- **web**: Add an About view opened by the status bar's version
  ([`c097405`](https://github.com/bkuberek/coding-study/commit/c09740544630947e146ba9cc7f315e07eca47441))

- **web**: Describe the About endpoints in the API schema
  ([`2cf9ca5`](https://github.com/bkuberek/coding-study/commit/2cf9ca5ec13a00df5f00a5221224d9e19efa079e))

- **web**: Read ABOUT in the status bar, as the other views do
  ([`7361ca2`](https://github.com/bkuberek/coding-study/commit/7361ca291a947999d695b3127eea0fa6915f589d))

### Refactoring

- Move the installed-packages reader from entrypoints to adapters
  ([`2662e54`](https://github.com/bkuberek/coding-study/commit/2662e54c1c676d01bb844972397ceaf825660f77))


## v0.24.0 (2026-11-07)

### Bug Fixes

- **web**: Let the Sets view fill the page
  ([`a495e14`](https://github.com/bkuberek/coding-study/commit/a495e1480e17b897b6d9d9c12db515994655954e))

### Features

- **web**: Give every config key a friendly label and a section
  ([`930f5a3`](https://github.com/bkuberek/coding-study/commit/930f5a317a668da7cbaeb4dd5adef3922f9aaa69))

- **web**: Lay Settings out in two columns, with the path and a red reset
  ([`bc5b1bc`](https://github.com/bkuberek/coding-study/commit/bc5b1bcb909ccf8d457ebcf53216039bb2c0e41f))

- **web**: Stage every Settings change until one Save
  ([`a1e293c`](https://github.com/bkuberek/coding-study/commit/a1e293c2fc04c5dd28c84359082a56e473bf531e))

### Testing

- Keep a served cstudy off the config file the shell names
  ([`19e79b2`](https://github.com/bkuberek/coding-study/commit/19e79b2ab2f20fa82b9e2b74d4b9657d61a91486))

- Tell the TypeScript starters that run from the bare ones
  ([`86b7b2c`](https://github.com/bkuberek/coding-study/commit/86b7b2c8b79c39a4847057e50d4d1b4fa51f9451))


## v0.23.0 (2026-11-07)

### Continuous Integration

- Run the Chromium browser tests in a path-gated job
  ([`80cd8bb`](https://github.com/bkuberek/coding-study/commit/80cd8bb939ed9ebb2ca13fcc9ff2090ecc0a1d85))

### Features

- **runners**: Give user code an allowlisted environment
  ([`27ffdc2`](https://github.com/bkuberek/coding-study/commit/27ffdc2d7625a9e12ec832b7ac54e0f9a13ad348))


## v0.22.0 (2026-11-07)

### Bug Fixes

- **web**: Keep room for a title where the Problems table scrolls in its own box
  ([`924a57b`](https://github.com/bkuberek/coding-study/commit/924a57b0952faa71748e554d1ba844636a3370e8))

- **web**: Keep the Problems rows on one line and the filter row compact in narrow windows
  ([`83d7a4b`](https://github.com/bkuberek/coding-study/commit/83d7a4b994e1d7b86abf2bc44f93b400bee8ce97))

- **web**: List each set once in the Set filter after a row leaves its set
  ([`f95d212`](https://github.com/bkuberek/coding-study/commit/f95d2127543c3660eb22d1edabc29a49f7ea2e43))

- **web**: Meet the axe checks with the filter chips, and keep hidden row text from widening a
  narrow page
  ([`d5d460d`](https://github.com/bkuberek/coding-study/commit/d5d460dc619f55764cfe872c5e4e4ab79d348d33))

- **web**: Type the columns preference for pyright
  ([`8e5edbd`](https://github.com/bkuberek/coding-study/commit/8e5edbdf3e1efea7d5181504f0fd53c13e6ea26d))

### Documentation

- Add --search to the cstudy list spec
  ([`d0a66c3`](https://github.com/bkuberek/coding-study/commit/d0a66c3cdbbf4b161a3082226148d59ccba4bc7c))

- Name the slash key among the page's shortcuts
  ([`7501d86`](https://github.com/bkuberek/coding-study/commit/7501d8612e9cf56174970dc163c85d6108ab631e))

### Features

- **web**: Choose the Problems table's columns in a menu stored in the preferences
  ([`87cdc1d`](https://github.com/bkuberek/coding-study/commit/87cdc1dcbe32c44157855c8edf8cb41420a0341d))

- **web**: Give the Next panel a real Start or Resume button and shrink it to two lines
  ([`b3f9d69`](https://github.com/bkuberek/coding-study/commit/b3f9d69ce6ef091363eb7ff789b51c6187ee082c))

- **web**: Hide the attempts menu in the top bar while nothing is open
  ([`ffee13c`](https://github.com/bkuberek/coding-study/commit/ffee13c572e08b7f3b9f80f85decb3b3b7968d4b))

- **web**: Lead each row with its title, merge In Progress into Status, and open a row on a click
  ([`76463f9`](https://github.com/bkuberek/coding-study/commit/76463f9fb5830ad0cb36598c3cf0a51e131a5422))

- **web**: Put the filters in one slim row with More, removable chips, a count and Clear
  ([`e350d49`](https://github.com/bkuberek/coding-study/commit/e350d49ec253b3cf100e3809abc9bd2d0ef9216c))

- **web**: Search the Problems view by title and slug as you type, and add cstudy list --search
  ([`b62a602`](https://github.com/bkuberek/coding-study/commit/b62a602adf4b0b44d09f927151e75b64a2c2abea))

- **web**: Show the Sets column in the Problems table by default
  ([`0148ce3`](https://github.com/bkuberek/coding-study/commit/0148ce3554744a8f3c2d883581931df65775fb0c))

### Refactoring

- **web**: Fetch the Problems and Problem views' styles and the landing view as chunks
  ([`04a0da9`](https://github.com/bkuberek/coding-study/commit/04a0da98fba13c736ddd949ff8fd2fa0dbd25c72))

### Testing

- **web**: Bring each header cell into view before reading what is on top of it
  ([`0bba7e8`](https://github.com/bkuberek/coding-study/commit/0bba7e85a4033d3b55f9145cf46f0b2534ea8dbf))

- **web**: Check the slash key on another view, and read the columns preference in one place
  ([`c28ad68`](https://github.com/bkuberek/coding-study/commit/c28ad68b16b86242755a28661ed405dc751f8cdd))

- **web**: Pin the columns in the document preferences save
  ([`b3753eb`](https://github.com/bkuberek/coding-study/commit/b3753eb289407a43d1073730151ff76bac37d77b))

- **web**: Pin what the preferences route says of the columns
  ([`df85e31`](https://github.com/bkuberek/coding-study/commit/df85e31431d2f5b59e94dde4f0a964dc779e62f7))

- **web**: Publish the live diagnostics on the starter file's current lines
  ([`0df3127`](https://github.com/bkuberek/coding-study/commit/0df3127922ae6438fc0f10a5e98186fce8f458ee))

- **web**: Wait on the run toolbar's current marker in the run on save test
  ([`f951754`](https://github.com/bkuberek/coding-study/commit/f951754495a1163e96ca73526fa84bde9d6b3b03))


## v0.21.0 (2026-11-07)

### Documentation

- Decide problem sets in ADR 0023, with their spec rows
  ([`d0a504b`](https://github.com/bkuberek/coding-study/commit/d0a504b4720d04db14e160022c4a0b6031912155))

- Tick the problem sets phase on the roadmap
  ([`2623c4b`](https://github.com/bkuberek/coding-study/commit/2623c4b1d79b373a0d9d9b8eda5bc127a92af088))

### Features

- **sets**: Add cstudy set, and --set on cstudy list and cstudy next
  ([`c8c5476`](https://github.com/bkuberek/coding-study/commit/c8c547645c244444f62a9e8b3d3300d4b4c00eee))

- **sets**: Add the problem set model and the sets.yaml store that keeps hand edits
  ([`1d8a348`](https://github.com/bkuberek/coding-study/commit/1d8a348dd353ad2e04505eac969bd40ff754d15a))

- **sets**: Add the Sets view, the Set filter and the add-to-set control
  ([`36a7a25`](https://github.com/bkuberek/coding-study/commit/36a7a25cf9db79835289420b0993ddc0032c513a))

- **sets**: Refuse a sets.yaml that can't be read, and pin the new command group
  ([`d940217`](https://github.com/bkuberek/coding-study/commit/d9402178ea0c4e6c06b0cf1dfe32f3c5cdb21b01))

- **sets**: Say that cstudy reset keeps sets, and add sets to the guide and the README
  ([`6858082`](https://github.com/bkuberek/coding-study/commit/68580829ff0f3eb3e45df17dbf178b409ab47183))

- **sets**: Serve the sets on the web API under the page's write rules
  ([`b5384ba`](https://github.com/bkuberek/coding-study/commit/b5384baa53b068d790705c3cdc17e023d635e678))


## v0.20.0 (2026-11-07)

### Documentation

- Add the backend depth problems to the catalog, counts and roadmap
  ([`21d5827`](https://github.com/bkuberek/coding-study/commit/21d58278df767b69f0d3a432a4bc4454f708a801))

### Features

- **catalog**: Add Idempotent Document Consumer (TypeScript)
  ([`a017ca2`](https://github.com/bkuberek/coding-study/commit/a017ca2446d71b6a0666f39c0e48713f7e4c1373))

- **catalog**: Add Loan Extraction Review (TypeScript)
  ([`a88f3b3`](https://github.com/bkuberek/coding-study/commit/a88f3b3bb55be1ac097968b153289236150f9b72))

- **catalog**: Add Supplier Records with Optimistic Locking (TypeScript)
  ([`d6caedc`](https://github.com/bkuberek/coding-study/commit/d6caedcec2f01045462fa83beb20b0e0f816866d))

- **catalog**: Add Transactional Outbox (TypeScript)
  ([`ba86d37`](https://github.com/bkuberek/coding-study/commit/ba86d37c05c5b29b0fff2fdf2b47e544d447401a))

- **catalog**: Add Vendor Retry Client (TypeScript)
  ([`6e1f683`](https://github.com/bkuberek/coding-study/commit/6e1f6836b826445c76d2a0d35756eb8816996e7c))


## v0.19.0 (2026-11-07)

### Documentation

- Describe the starter's new header and what cstudy next resumes
  ([`81e296b`](https://github.com/bkuberek/coding-study/commit/81e296bc341f3573e35d5a61a874e53fa9fc8586))

- State the starter header's real wrapping in the runners spec
  ([`6b1b62b`](https://github.com/bkuberek/coding-study/commit/6b1b62b2c44a8d23ea322a4079a9b97a5e453cf3))

### Features

- **catalog**: Give 151 problems a hand-written starter summary
  ([`32a2bab`](https://github.com/bkuberek/coding-study/commit/32a2babac3e30f3330d086753849c7156ff0056b))

- **cli**: Add cstudy abort, which ends an attempt as abandoned
  ([`9a34036`](https://github.com/bkuberek/coding-study/commit/9a340362d5f285f05d3fc53478e54cc312c32704))

- **cli**: Resume the attempt in progress first in cstudy next
  ([`05e9400`](https://github.com/bkuberek/coding-study/commit/05e9400e2ebb488823c6c8442dccaacad9c07a85))

- **cli**: Wrap the starter header and add a short summary of the problem
  ([`78e6d64`](https://github.com/bkuberek/coding-study/commit/78e6d64aeca029404240fb365b6f2161e1d0ed2b))

- **cli**: Write in progress in words and accept in-progress as a status
  ([`5cc9fcd`](https://github.com/bkuberek/coding-study/commit/5cc9fcdac234084961dec19b76e0aa7fa883c67d))

- **web**: Add Abort to the Attempt view
  ([`dd04fa2`](https://github.com/bkuberek/coding-study/commit/dd04fa2317ecf8fcc320a65006b38f7de138f9f9))

- **web**: Resume the attempt in progress first in the Next card
  ([`203d873`](https://github.com/bkuberek/coding-study/commit/203d873a66de2d06fad07d910f257c40ac28da87))

- **web**: Show commands as code text, not as buttons
  ([`0354696`](https://github.com/bkuberek/coding-study/commit/035469663cef7e286290fe7632355409236f5ec8))

- **web**: Turn Run tests and Submit into Cancel while their run is active
  ([`2038b11`](https://github.com/bkuberek/coding-study/commit/2038b116826ee1186165e4cdb2593517934b6819))

- **web**: Write in progress in words in the Problems view
  ([`7db2f8c`](https://github.com/bkuberek/coding-study/commit/7db2f8c4d03c5b74cbdd5ba881206e4f27fac480))


## v0.18.0 (2026-11-06)

### Documentation

- Update the front end's size table for Settings
  ([`661e9d7`](https://github.com/bkuberek/coding-study/commit/661e9d7cb1969ed8e39def883aeed53810854d2e))

### Features

- **cli**: Add cstudy config edit and path
  ([`2798c0c`](https://github.com/bkuberek/coding-study/commit/2798c0ceefd660877757bf3b913a609283323850))

- **cli**: Add cstudy reset, with a preview and a typed word
  ([`af11b60`](https://github.com/bkuberek/coding-study/commit/af11b60261679527dbbafc15b8df63c45903b284))

- **config**: Let Settings edit every key of config.toml, keeping comments
  ([`6a09677`](https://github.com/bkuberek/coding-study/commit/6a096771d1416d247ccc57433ed69aca83413cbb))

- **config**: Review intervals and the mastered threshold under [schedule]
  ([`1ed0a00`](https://github.com/bkuberek/coding-study/commit/1ed0a0038e2b67b1e1f89130e0842c2cafaf7ece))

- **config**: Say a new progress_db moves no data, and ask first
  ([`19707c3`](https://github.com/bkuberek/coding-study/commit/19707c30cbca94431deb6e04834a308db07abb4b))

- **web**: Add a Danger section to Settings that resets progress
  ([`0c6fb2e`](https://github.com/bkuberek/coding-study/commit/0c6fb2e24d15547b376c223c275766d7a69e0bc9))

### Testing

- List cstudy reset and the config group among the commands
  ([`9900cd4`](https://github.com/bkuberek/coding-study/commit/9900cd4e15d1fcf27cbb3c7e0dfddd27b0e05e49))


## v0.17.1 (2026-11-06)

### Bug Fixes

- **web**: Indent each language by its own unit
  ([`4f6c4b3`](https://github.com/bkuberek/coding-study/commit/4f6c4b3c8d54890390018b7740203d4d05d27df0))

- **web**: Keep column header styles off the row headers of a table
  ([`38c815e`](https://github.com/bkuberek/coding-study/commit/38c815effdfb3f6c816ab1a1cb132457b7b92b24))

- **web**: Let Tab accept the selected completion
  ([`3c0c40c`](https://github.com/bkuberek/coding-study/commit/3c0c40c035a2a8b2b977f706ef5d90ebb0a7201b))

- **web**: Make the save hint a real button
  ([`9b66db6`](https://github.com/bkuberek/coding-study/commit/9b66db65279b6b026364239461b9a0d1534d57d7))

- **web**: Reword where a past attempt's current files come from
  ([`c746980`](https://github.com/bkuberek/coding-study/commit/c7469804e34b82f396fbe793f5fcc3d43310c934))

- **web**: Save every open tab before a run
  ([`4746bab`](https://github.com/bkuberek/coding-study/commit/4746bab1466bb4aac778bec8adc776087c91bb2b))

- **web**: Show a selection on the cursor's line
  ([`a89f0d4`](https://github.com/bkuberek/coding-study/commit/a89f0d4f94be983f27cd88e59526d2d275260087))

### Documentation

- Update the front end's size table for the editor fixes
  ([`319c552`](https://github.com/bkuberek/coding-study/commit/319c5528d9df0d8835e8b663a8b0aac47b3a6845))

### Refactoring

- **web**: Fetch the Problem view when it first opens
  ([`0a8e1c6`](https://github.com/bkuberek/coding-study/commit/0a8e1c6467a6357ee95df8135433291713601a1e))

- **web**: Fold the dialogs into one chunk and one stylesheet
  ([`9cd9a70`](https://github.com/bkuberek/coding-study/commit/9cd9a701bd025d4167586040c0d394be33223e95))


## v0.17.0 (2026-11-06)

### Bug Fixes

- **web**: Leave an empty fix hint of a Health row empty
  ([`7839ceb`](https://github.com/bkuberek/coding-study/commit/7839ceb9477eac818a0950f593f266f620bb36ae))

### Documentation

- Update the front end's size table for the sticky bar, headers and Fix buttons
  ([`13d383c`](https://github.com/bkuberek/coding-study/commit/13d383c6cea18a02ff09cfea0296e0fbd1f231f7))

### Features

- **cli**: Say when doctor --fix skips the language servers
  ([`253e1a8`](https://github.com/bkuberek/coding-study/commit/253e1a81347bb6ae0dbed049c33f1e7c05b15259))

- **cli**: Show a problem with an attempt in progress as in_progress
  ([`6047a3b`](https://github.com/bkuberek/coding-study/commit/6047a3b8cd437a8ef3191c0c8999e96d145570d5))

- **web**: Give each Health row whose fix is cstudy doctor --fix a Fix button
  ([`ef80242`](https://github.com/bkuberek/coding-study/commit/ef802429d56c462aaf18ae9111d1c663de78b053))

- **web**: Keep the top bar and the table headers in view while scrolling
  ([`9f54d49`](https://github.com/bkuberek/coding-study/commit/9f54d4998c356b03c31c669f0f04510d4585fc7c))


## v0.16.0 (2026-11-06)

### Documentation

- List the TypeScript backend problems with their labels, and update counts, the PRD and the roadmap
  ([`c741c42`](https://github.com/bkuberek/coding-study/commit/c741c42d7edd928365cfe3d57e5dfa5bcb8af7aa))

- Remove a later level's hint and a framework's name from two problem texts
  ([`dc89659`](https://github.com/bkuberek/coding-study/commit/dc896594e17144e673d597287ed4b369194ab358))

### Features

- **catalog**: Add Debug: Async Batch (TypeScript)
  ([`a705092`](https://github.com/bkuberek/coding-study/commit/a705092ebb50eb94cea15ccf3c1e3acd3fa64cb7))

- **catalog**: Add Debug: Falsy Plan Update
  ([`de4ca34`](https://github.com/bkuberek/coding-study/commit/de4ca342378591b7fcf17f889c3cd6bb59014e8e))

- **catalog**: Add Debug: Invoice Total Cents
  ([`69320f8`](https://github.com/bkuberek/coding-study/commit/69320f8e296946dc04721044f7ec7bbd13b41175))

- **catalog**: Add Debug: Local Day Boundaries
  ([`11f1f29`](https://github.com/bkuberek/coding-study/commit/11f1f294848e3576ae32f3f53e8b7cb229c18141))

- **catalog**: Add Debug: Pagination Query Strings
  ([`f6ff343`](https://github.com/bkuberek/coding-study/commit/f6ff3430c4029dd9bef2a26ff408c5929fbe1f0f))

- **catalog**: Add Debug: Shared Default Config
  ([`ff8635e`](https://github.com/bkuberek/coding-study/commit/ff8635ea401eef2a5fd2326290d8c29aeba70e20))

- **catalog**: Add Debug: Sorted Report Rows
  ([`d128404`](https://github.com/bkuberek/coding-study/commit/d1284049ccdc3242119f8f07a6cd7d5c5103459f))

- **catalog**: Add Debug: Stale Closure Callbacks
  ([`a78987d`](https://github.com/bkuberek/coding-study/commit/a78987defedf6d92c22ef7a48a5eac1a5f9335d3))

- **catalog**: Add Loan Pipeline Service (TypeScript)
  ([`6e2c813`](https://github.com/bkuberek/coding-study/commit/6e2c813ae6644d0ae4728aab54243ffdd7c117fd))

- **catalog**: Add Warehouse Work Orders (TypeScript)
  ([`4212317`](https://github.com/bkuberek/coding-study/commit/42123176d5bcab1a17d2ce1574c4d7eae1729e62))


## v0.15.0 (2026-11-06)

### Documentation

- Describe cstudy as a study tool for engineers and note the domain language rule
  ([`337bcc2`](https://github.com/bkuberek/coding-study/commit/337bcc226ebe8a2c15d2ea2a01a7ad1f1f9a161f))

- List the first wave with its labels, and update counts, the PRD and ADR 0020
  ([`a52914b`](https://github.com/bkuberek/coding-study/commit/a52914b20321e579fb5a32a4ebd35c3bb31b2390))

### Features

- **catalog**: Add Authorization Policy Engine
  ([`64fb64d`](https://github.com/bkuberek/coding-study/commit/64fb64d55e5ce6303ed2a78f8698fa1d77f23ee8))

- **catalog**: Add BM25 Hybrid Ranker
  ([`1b13bcb`](https://github.com/bkuberek/coding-study/commit/1b13bcbe130e2388d9d02db184f32c658822206c))

- **catalog**: Add Calibration Metrics
  ([`0ab912f`](https://github.com/bkuberek/coding-study/commit/0ab912fcaa973123914482128b6fe595e75c4fa3))

- **catalog**: Add Refresh Token Rotation
  ([`1e813b6`](https://github.com/bkuberek/coding-study/commit/1e813b620a83f127acc7f0cea99d9b0f8ec8b59e))

- **catalog**: Add Stream Reassembler
  ([`fe44b3a`](https://github.com/bkuberek/coding-study/commit/fe44b3adfc74016413937bf4964393ba84f4757a))

- **catalog**: Add Token Claim Validator
  ([`e4b44d2`](https://github.com/bkuberek/coding-study/commit/e4b44d24a744a6a081e3a1bded29722be7651f61))

- **catalog**: Add Token Cost Reconciler
  ([`4d0b12e`](https://github.com/bkuberek/coding-study/commit/4d0b12eac2e568d76b1afdf46798f75138681cd4))

- **catalog**: Let the security, identity and AI domains list a language subset
  ([`ee5a82b`](https://github.com/bkuberek/coding-study/commit/ee5a82bfe3ebcfad14d9fbbee59a3bd8225c8990))


## v0.14.0 (2026-11-06)

### Documentation

- Configure AI review keys in Settings or the configuration file (ADR 0021)
  ([`41e7b94`](https://github.com/bkuberek/coding-study/commit/41e7b94dcf7e6d904302b5f0fc86a15c5ff2c6fb))

- Describe the catalog labels, their filters and check S24 as current
  ([`094db98`](https://github.com/bkuberek/coding-study/commit/094db98d4e5edce4676c88a47051863f009908aa))

- Keep AI review keys in a credentials file of their own (ADR 0021)
  ([`881fe4a`](https://github.com/bkuberek/coding-study/commit/881fe4ad0262b6927c4cc53fa0d41d53e32978aa))

- Mark ADR 0020 phase 1 implemented and describe the Problems view filters
  ([`700ceb4`](https://github.com/bkuberek/coding-study/commit/700ceb43b0ab66243c884cc0ebaaa942378632a7))

- Plan service projects with mock servers, Docker services and HTTP grading (ADR 0019)
  ([`2ce25e8`](https://github.com/bkuberek/coding-study/commit/2ce25e884a68c372b3af5c88a73e6f0117a853f3))

- Run service projects in Docker and plan catalog labels and AI review (ADR 0019, 0020, 0021)
  ([`644b61b`](https://github.com/bkuberek/coding-study/commit/644b61b8ceaf93dbda43aacc18c9534e151e02cf))

### Features

- **catalog**: Add the domain, job role and scope vocabularies to the schemas and the model
  ([`007bab1`](https://github.com/bkuberek/coding-study/commit/007bab145d40ecb74823faba54e4c0f286afaa26))

- **catalog**: Cstudy new writes the labels of its template
  ([`0ddfd1e`](https://github.com/bkuberek/coding-study/commit/0ddfd1ec6468ec06a9a0fc0ac3390d14ef11b463))

- **catalog**: Filter cstudy list and cstudy next by domain, role and scope
  ([`3151669`](https://github.com/bkuberek/coding-study/commit/315166946a6674a92fdf80c49b9db85387d49935))

- **catalog**: Filter the Problems view by domain, role and scope
  ([`3ea1c97`](https://github.com/bkuberek/coding-study/commit/3ea1c97c11444154ee256b019de624338d31e17b))

- **catalog**: Filter the web API's problem list and next pick by domain, role and scope
  ([`37050a8`](https://github.com/bkuberek/coding-study/commit/37050a86810999f48d69f49d7cb7e9e4d11310b5))

- **catalog**: Label all 270 entries with their domains, job roles and scope
  ([`2325531`](https://github.com/bkuberek/coding-study/commit/23255311a1c88e904d5c81c65fb704ecb82735ad))

- **catalog**: Require the labels of a catalog entry in check S24
  ([`efb7f91`](https://github.com/bkuberek/coding-study/commit/efb7f91b65fd1f3b00d549395ccf8f15321db89c))

### Testing

- Strip the color codes that CI forces from the doctor help before reading it
  ([`0003ff0`](https://github.com/bkuberek/coding-study/commit/0003ff02b8a1295d958dd7b990730f3d370f645c))


## v0.13.3 (2026-11-04)

### Bug Fixes

- **doctor**: Say in --fix's help that it installs the language servers for code intelligence
  ([`6a712eb`](https://github.com/bkuberek/coding-study/commit/6a712eb1f562309e70152595f9f2bcbffbb45640))

### Documentation

- Match the doctor's real output, size the web ui assets at 1.2 MB and note basedpyright's
  type-checking mode in 0.13.1
  ([`4f3098d`](https://github.com/bkuberek/coding-study/commit/4f3098d14f41b5e54011a6f1351eff7cd72c6051))

### Testing

- Give the bench budget test a budget far above a cold runtime's first call
  ([`91d7815`](https://github.com/bkuberek/coding-study/commit/91d7815ff978f6647d9ed944a43bf4e85f8e8479))


## v0.13.2 (2026-11-04)

### Bug Fixes

- **test**: Read only complete lines of the fake language server's logs
  ([`5f18790`](https://github.com/bkuberek/coding-study/commit/5f18790c2a3c649f6e5b1bc43f8b80586876f51a))

### Documentation

- Retake the autocomplete media on 0.13.1
  ([`6e78dfc`](https://github.com/bkuberek/coding-study/commit/6e78dfc8f72185241901591a823cc46734eeec9b))

### Testing

- Keep the slow tests' Gradle daemons for ten minutes and ignore the warm-up notice
  ([`ef8b166`](https://github.com/bkuberek/coding-study/commit/ef8b16614072a4503c7ce6efc5c451781cb20db8))


## v0.13.1 (2026-11-04)

### Bug Fixes

- **web**: Offer no auto-import completions, as autocomplete promises
  ([`d868b4a`](https://github.com/bkuberek/coding-study/commit/d868b4a8fef085861711ba44c334784aa677faea))

- **web**: Apply basedpyright's configured type-checking mode (`standard`). Before this release the
  server never read its settings key, so neither `autoImportCompletions` nor `typeCheckingMode`
  applied.

### Documentation

- Showcase code intelligence and autocomplete on 0.13.0
  ([`bddce83`](https://github.com/bkuberek/coding-study/commit/bddce83e4d935ad84c8a4fcd01ab8f55363f0a24))


## v0.13.0 (2026-11-04)

### Bug Fixes

- **web**: Bound the stop of a language server, its frames and its queues
  ([`d14d57f`](https://github.com/bkuberek/coding-study/commit/d14d57f70485712cd34895ef002d8b28632c9a71))

- **web**: Keep cases and run data out of definition answers and the library
  ([`010ec79`](https://github.com/bkuberek/coding-study/commit/010ec7993a1fc2e629066345076644c301fcaeae))

- **web**: Keep the reference directories from the language server's reach
  ([`c500b18`](https://github.com/bkuberek/coding-study/commit/c500b18c0d7c9520eab219d3bc3c21fb9ed9682a))

- **web**: Refuse reused request ids and forged resolve data in the code intelligence broker
  ([`85a4946`](https://github.com/bkuberek/coding-study/commit/85a49466a8ed65b7349e9d599d83649700b92b54))

### Documentation

- Guide to code intelligence and autocomplete
  ([`af72767`](https://github.com/bkuberek/coding-study/commit/af7276798d65e1b0b4001fe6913650fd453e47db))

- Hidden directories and the release order of code intelligence
  ([`cd0bb52`](https://github.com/bkuberek/coding-study/commit/cd0bb52c706b695811268438150b91c5bb282592))

- The language servers take 46 MB in .cs/lsp/, as measured
  ([`19c61bc`](https://github.com/bkuberek/coding-study/commit/19c61bc363cbe1467e9b45bd778570e28c2e5290))

- **adr**: Accept 0018, editor code intelligence
  ([`d9d6395`](https://github.com/bkuberek/coding-study/commit/d9d639501494f44e8681228e79ebdeb06141300b))

- **specs**: Code intelligence and autocomplete for slice 1
  ([`1df0e62`](https://github.com/bkuberek/coding-study/commit/1df0e62ff001bdfe42f31174b925f9549c069ab2))

### Features

- **doctor**: Install and check the language servers for code intelligence
  ([`73f32d4`](https://github.com/bkuberek/coding-study/commit/73f32d43aac218f0cfdcf8bc2d3c42edb6ccbea7))

- **web**: Alt-Shift-click adds a cursor, and autocomplete governs all completion
  ([`92c884e`](https://github.com/bkuberek/coding-study/commit/92c884eb0960c157c2e4ec294910bd5a29c11cb6))

- **web**: Broker between a code intelligence session and its language server
  ([`9b91af4`](https://github.com/bkuberek/coding-study/commit/9b91af48cf97db6494261d2e9efbd799a478440b))

- **web**: Code intelligence and autocomplete preferences with their Settings checkboxes
  ([`b73e448`](https://github.com/bkuberek/coding-study/commit/b73e448423e6aaba91587812084500c4536ac5a1))

- **web**: Code intelligence client with sessions, status bar and the languages in Settings
  ([`3503fe7`](https://github.com/bkuberek/coding-study/commit/3503fe706c6e8c14848bb2b919baee64e6b596cb))

- **web**: Code intelligence session route with its security checks and server lifecycle
  ([`00b9318`](https://github.com/bkuberek/coding-study/commit/00b931887f88e32a21700bfc9be038c8de93dd30))

- **web**: Completion and signature help from the language server, behind the autocomplete setting
  ([`4bfbd3d`](https://github.com/bkuberek/coding-study/commit/4bfbd3dc6412fe459ba66b6324de4ceec4c542aa))

- **web**: Go to definition by click and key, and read-only library tabs
  ([`1cbb3cc`](https://github.com/bkuberek/coding-study/commit/1cbb3cc34120cf44602af6e85d7b7924eaa10b9c))

- **web**: Hover documentation by pointer and keyboard, read out by a live region
  ([`cbcc75c`](https://github.com/bkuberek/coding-study/commit/cbcc75ce60b726b999778f5355793e6a1351b7eb))

- **web**: Live diagnostics from the language server beside the last run's
  ([`631a817`](https://github.com/bkuberek/coding-study/commit/631a8172b4425dc6f657ca1ca961341d5782b121))

### Testing

- Leave the installs row of the host out of the upgrade test's workspace check
  ([`95cdffe`](https://github.com/bkuberek/coding-study/commit/95cdffee5463a0e978caa2cf5d80ad47a77c1a33))

- Let the slow tests' Gradle daemons idle out after a minute
  ([`1ea12a3`](https://github.com/bkuberek/coding-study/commit/1ea12a343b995ac5ae1cc27ebfcbef29f3228475))

- **web**: The status bar names the broker's new close reasons
  ([`cf8fe09`](https://github.com/bkuberek/coding-study/commit/cf8fe09c4f3d107ebc2cdbf78f8f7961b6c57e13))


## v0.12.0 (2026-11-03)

### Bug Fixes

- **ide**: Stop passing --keep-going to rust-analyzer twice
  ([`42fa839`](https://github.com/bkuberek/coding-study/commit/42fa8395f33f2b4d25fbb6eadd1bf8a56e740a90))

- **start**: Wrap the starter header comment at 100 columns
  ([`6ce14b9`](https://github.com/bkuberek/coding-study/commit/6ce14b98974bd4e30873a27b06b5075397461000))

- **web**: Say that a review start deletes nothing
  ([`9cbf73c`](https://github.com/bkuberek/coding-study/commit/9cbf73cf7031b2f7fc165f63251aca0283d36ccc))

### Documentation

- **web-ui**: Refresh the bundle size table and add the past-code chunk
  ([`6e57eba`](https://github.com/bkuberek/coding-study/commit/6e57ebaab2b6dbc33e1b794c82a348f5bd677e5b))

### Features

- **doctor**: Report more than one cstudy install and name the running one in the reinstall fix
  ([`6a9251f`](https://github.com/bkuberek/coding-study/commit/6a9251f28082e43efe55419f8333aed9a8606c58))

- **serve**: Name the running install in the reinstall hint
  ([`498e78d`](https://github.com/bkuberek/coding-study/commit/498e78d0f03e41d18a6142cc54d2bf86a55db13d))

- **web**: Read the files of a past attempt through the API
  ([`b772858`](https://github.com/bkuberek/coding-study/commit/b772858a560e285802c006bb9a880d886ae9b62d))

- **web**: Show a past attempt's code read-only in History
  ([`8680a3b`](https://github.com/bkuberek/coding-study/commit/8680a3bd0149ae19c4bbcc1c0c20c49fc093eed0))


## v0.11.1 (2026-11-03)

### Bug Fixes

- **jdk**: Name the problem's own JDK range in the fix line
  ([`34b2478`](https://github.com/bkuberek/coding-study/commit/34b247800e95be6c4c321f3a6e9edf9327c2b17d))

- **web**: Scroll the status bar instead of squeezing its segments in a narrow window
  ([`836c0ca`](https://github.com/bkuberek/coding-study/commit/836c0ca9a7ca58ce60b75a5089f0170063fd4f01))

### Documentation

- List Linux among the supported platforms in the PRD
  ([`4ee4eeb`](https://github.com/bkuberek/coding-study/commit/4ee4eeb1d998f00e9c097c4f4426463882e74913))

- Retake the web UI screenshots on 0.11.0
  ([`b54f308`](https://github.com/bkuberek/coding-study/commit/b54f308a0bec15b7f3f19f370759cbad3346d496))

- Say which commands refresh the runner runtime
  ([`19ba2ca`](https://github.com/bkuberek/coding-study/commit/19ba2ca8fa753acbb1a645308eb56a1de146e930))

- State the Java --virtual-clock refusal text exactly
  ([`732c0fa`](https://github.com/bkuberek/coding-study/commit/732c0fa7882c360157f1b4ab7e8ee32bc4176930))


## v0.11.0 (2026-11-03)

### Bug Fixes

- **content**: Accept earlier virtual-clock helper digests in TypeScript starters
  ([`af65037`](https://github.com/bkuberek/coding-study/commit/af65037d0b1d85897433b4f81e8080f801651fb1))

- **rust**: Measure a lone list item's room from its line
  ([`05c2929`](https://github.com/bkuberek/coding-study/commit/05c2929ffb3d6c135ee9c212678ea158e3c159be))

### Build System

- **jvm**: Cache kotlinx-coroutines for Kotlin clock projects
  ([`73def1d`](https://github.com/bkuberek/coding-study/commit/73def1d9426bb54e89a3568e1c523cbf7f56df6b))

- **rust**: Vendor tokio for Rust clock projects
  ([`02d45bc`](https://github.com/bkuberek/coding-study/commit/02d45bc2e75fea6a32b6a828caa7cc1814d6f6ac))

### Chores

- **go**: Remove the runner file for Go before 1.23
  ([`3c24328`](https://github.com/bkuberek/coding-study/commit/3c24328be833170a351ac82fd89ba2c82d2f4c37))

### Documentation

- Accept ADR 0017 and specify async and concurrent project problems
  ([`fab6401`](https://github.com/bkuberek/coding-study/commit/fab640198ad37b025b873e5fb5ce590d4d2078f6))

- Answer PRD Q5 with ADR 0017
  ([`3f5375b`](https://github.com/bkuberek/coding-study/commit/3f5375b5d84bcc1d1c5ffec9c15525f19224d899))

- Name the coroutine bridge among the JVM runner's parts
  ([`46bf3f1`](https://github.com/bkuberek/coding-study/commit/46bf3f1f734a61b3bbb2273aad759350db7b37cf))

- Note that tokio's select! picks among ready branches at random
  ([`b2ba6c2`](https://github.com/bkuberek/coding-study/commit/b2ba6c2fdf9c54d2fcd41bd67c5d42f6e9f949f9))

- Note the TypeScript clock's wait helper in ADR 0017
  ([`27389f0`](https://github.com/bkuberek/coding-study/commit/27389f0529664acae488f1c6ad44634bf74ff309))

- Record the async project tooling in the roadmap and ADR 0017
  ([`284df1f`](https://github.com/bkuberek/coding-study/commit/284df1f124711e2af376190f08df8ad27a97158f))

- Record the Kotlin coroutines spike in ADR 0017
  ([`3d1ed96`](https://github.com/bkuberek/coding-study/commit/3d1ed96b81275e34b598c7f29b8ce014483b16a6))

- **new**: Describe the stress project scaffold
  ([`459d4d7`](https://github.com/bkuberek/coding-study/commit/459d4d714a3513441957df394c042901067d8cfd))

### Features

- **go**: Generate synctest level tests and render harness operations
  ([`45fb5f3`](https://github.com/bkuberek/coding-study/commit/45fb5f3dd04eab89a7ecb3011a546c804dc20514))

- **go**: Grade virtual-clock projects in a synctest test binary
  ([`16cd441`](https://github.com/bkuberek/coding-study/commit/16cd4415d927aaedbfef8380ad9de527ef326682))

- **go**: Require Go 1.25 and add the virtual-clock project template
  ([`4ff231f`](https://github.com/bkuberek/coding-study/commit/4ff231f6fff46e5499eb9cce83b741fca52b29c7))

- **kotlin**: Generate virtual-clock level tests and the clock starter
  ([`19823e7`](https://github.com/bkuberek/coding-study/commit/19823e7d7c2cfc6d6f95ece5277acc40990027e2))

- **kotlin**: Grade virtual-clock and suspend projects
  ([`6eb0226`](https://github.com/bkuberek/coding-study/commit/6eb02268d99ba273ef400e142b003f851f50f1a7))

- **kotlin**: Run suspend stress workers
  ([`9b5ee69`](https://github.com/bkuberek/coding-study/commit/9b5ee69a84ef57ae4e424b546cdc671b86ab6ec4))

- **new**: Scaffold stress project problems
  ([`c72785e`](https://github.com/bkuberek/coding-study/commit/c72785e8de2b654b99688e591dfd0db0acc20c46))

- **projects**: Allow stress cases and broken references in project problems
  ([`5c0dd48`](https://github.com/bkuberek/coding-study/commit/5c0dd48436ee91074c1b9570f9d7ebb34ebf036a))

- **projects**: Declare async methods, the virtual clock and harness operations
  ([`4101a4f`](https://github.com/bkuberek/coding-study/commit/4101a4f41a36117f0af7a53d0a2ef49d163abb00))

- **python**: Generate virtual-clock level tests and the clock starter
  ([`ddbaaa7`](https://github.com/bkuberek/coding-study/commit/ddbaaa781e6e5cbc7f036ca138540c92146d044d))

- **python**: Grade virtual-clock and async projects
  ([`321461c`](https://github.com/bkuberek/coding-study/commit/321461c9016628aef69ce75d9fd7e7d6b855acd7))

- **runners**: Run project stress cases in every runner
  ([`4c3550a`](https://github.com/bkuberek/coding-study/commit/4c3550a55999d2b60977ff1673fe6485104b631a))

- **rust**: Generate virtual-clock level tests and the clock starter
  ([`c04f7e2`](https://github.com/bkuberek/coding-study/commit/c04f7e2365abf5ce2222bf424ecc4dcd778a8eb8))

- **rust**: Grade virtual-clock and async projects
  ([`b409799`](https://github.com/bkuberek/coding-study/commit/b409799793b615b596a79fa8dd5dfb9c832d05e1))

- **submit**: Judge stalled project cases
  ([`d31b207`](https://github.com/bkuberek/coding-study/commit/d31b2079603254a5f6a36a0fd57ea0e4aa9738cd))

- **submit**: Report stress verdicts per level
  ([`5f9ea5b`](https://github.com/bkuberek/coding-study/commit/5f9ea5b7aa52c30bcfe1c2220cc8c443e7afeebc))

- **typescript**: Generate virtual-clock level tests and the clock starter
  ([`dd38e13`](https://github.com/bkuberek/coding-study/commit/dd38e13857728b5f9a0560eaa5ef1b00123d10b2))

- **typescript**: Grade virtual-clock and async projects
  ([`889b9b5`](https://github.com/bkuberek/coding-study/commit/889b9b5e4903b51027d6a727526791a3fb3f988a))

- **verify**: Check virtual-clock determinism (D10)
  ([`f2291b6`](https://github.com/bkuberek/coding-study/commit/f2291b670502befb80ab499cb5f25621f98715cb))

- **verify**: Prove project stress cases catch their broken references (D6/D7)
  ([`98e54ec`](https://github.com/bkuberek/coding-study/commit/98e54ecf93ef97e165605d1047957419bf26596e))

### Testing

- **jvm**: Read the sources from disk in the release-level builds
  ([`265ccd6`](https://github.com/bkuberek/coding-study/commit/265ccd6a18a80d2718cb0493c6e0b45b0a73666d))

- **rust**: Grade stress workers that block on an async method
  ([`d5f554b`](https://github.com/bkuberek/coding-study/commit/d5f554b1080d01d4a98e740c430cc7f8045838a7))


## v0.10.1 (2026-11-02)

### Bug Fixes

- **jvm**: Read the sources from disk on every Gradle build
  ([`b9a310d`](https://github.com/bkuberek/coding-study/commit/b9a310d6c8daafa44177df4033e72e46d1102793))

### Documentation

- Link the README to coding-study.com
  ([`a071fc0`](https://github.com/bkuberek/coding-study/commit/a071fc0a0ba99e9fdded38cf5192fa03e1cb8c39))


## v0.10.0 (2026-11-02)

### Bug Fixes

- **web**: Listen before printing the URL so the first request is never refused
  ([`807346b`](https://github.com/bkuberek/coding-study/commit/807346bc0389c8fda9f9843b9d88bde224a9e658))

- **web**: Wrap long fix hints in the health view
  ([`0af140e`](https://github.com/bkuberek/coding-study/commit/0af140e503fb3f1980439bf4f83fa4c5a7e872a2))

### Continuous Integration

- Run the Java and Kotlin tests on JDK 21 and JDK 26
  ([`a69f579`](https://github.com/bkuberek/coding-study/commit/a69f579ed6ffd0593e65c133b136b59b7c32e2cb))

- Show why a JVM test is skipped and shorten the job limit
  ([`9f5822a`](https://github.com/bkuberek/coding-study/commit/9f5822a241f98fc6c002ffafc8d709540d1efa54))

### Documentation

- Accept ADR 0016 and specify the supported JDK range
  ([`66461bf`](https://github.com/bkuberek/coding-study/commit/66461bfe832a82e9ac726705826e9a7d6253ac35))

- List ADR 0016 in the docs index
  ([`10ce6e1`](https://github.com/bkuberek/coding-study/commit/10ce6e1f521d27d91963c2a00a62cff71afe2525))

- Note that Kotlin reference builds fail on JDK 22.0.0
  ([`9d0b7c3`](https://github.com/bkuberek/coding-study/commit/9d0b7c345effcdb36fdfd283967189bb1a8d5c16))

- Retake the web UI screenshots on 0.9.1
  ([`d0a96ba`](https://github.com/bkuberek/coding-study/commit/d0a96bac6b8bdca65529951556a5b15fc4a56137))

- **cli**: List the jvm test selection
  ([`814db78`](https://github.com/bkuberek/coding-study/commit/814db78fe3a6c86ca8a9789ddc00f92427f2f3a5))

- **content**: Note where virtual-thread behaviour differs from JDK 24
  ([`6b59ae1`](https://github.com/bkuberek/coding-study/commit/6b59ae170d63c6fe082e076b1558cc23f1ae0dfe))

### Features

- Refuse Java and Kotlin problems outside the selected JDK's range
  ([`9391860`](https://github.com/bkuberek/coding-study/commit/9391860eac042dd7fad09a318f004b1dc9bf8027))

- **cli**: Show which problems the selected JDK can run
  ([`a890c32`](https://github.com/bkuberek/coding-study/commit/a890c32dd069ea3b63c8d89f2d529b6dfdb6bcac))

- **content**: Let a problem declare the JDK range it needs
  ([`09a3fa0`](https://github.com/bkuberek/coding-study/commit/09a3fa0233406260665e7ad4c16583c0f37bae76))

- **doctor**: Accept JDK 21 to 26 and say when a JDK is not supported yet
  ([`292f4a3`](https://github.com/bkuberek/coding-study/commit/292f4a3738ee8e88bb7c5990f8e940240dd251fe))

- **ide**: Name the IntelliJ project JDK after the selected JDK
  ([`5538996`](https://github.com/bkuberek/coding-study/commit/5538996e9584a778675a4ecf6556340a08d831c9))

- **runners**: Build Java and Kotlin with the selected JDK at one release level
  ([`fdb87f5`](https://github.com/bkuberek/coding-study/commit/fdb87f56f5023c87e97c7a3d76e611bf9567233a))

- **web**: Show which languages the selected JDK can run
  ([`861c9f4`](https://github.com/bkuberek/coding-study/commit/861c9f4fdd4566f0e2161396fc18599359790fbc))

### Refactoring

- **content**: Drop the JDK version from the starter build comment
  ([`435dd0e`](https://github.com/bkuberek/coding-study/commit/435dd0ec0d560ad543774f44da5aaaecf6ae6b07))

### Testing

- Keep the wall-clock Gradle test out of the CI selection
  ([`95bfe2a`](https://github.com/bkuberek/coding-study/commit/95bfe2ad7b6ef7e6bcf32f28390a320ae9ace2e2))

- Wait for the server to listen before the first request
  ([`9e74f18`](https://github.com/bkuberek/coding-study/commit/9e74f189c9aee1496c3e5b15bcb3c9077517890f))


## v0.9.1 (2026-11-01)

### Bug Fixes

- **web**: Give the page the cstudy mark as its icon so browsers stop asking for /favicon.ico
  ([`58ad584`](https://github.com/bkuberek/coding-study/commit/58ad58419cf01465557a28b96a5079ac39157140))

### Documentation

- Add the cstudy header to the README
  ([`ae7ca04`](https://github.com/bkuberek/coding-study/commit/ae7ca04a11b1bd0d45bc4c285f8b3100ddf44fd4))

### Testing

- **cli**: Read usage errors without the colours Rich adds in CI
  ([`971f406`](https://github.com/bkuberek/coding-study/commit/971f406962ff32e1dd602fd1f06466759c0ea30b))


## v0.9.0 (2026-11-01)

### Bug Fixes

- **cli**: Answer 412 when a page move or delete finds its file deleted on the way
  ([`6b3f2c0`](https://github.com/bkuberek/coding-study/commit/6b3f2c001b1a7420ae07536bad461df884f45a97))

- **cli**: End a run's processes when cstudy is killed
  ([`9f745c4`](https://github.com/bkuberek/coding-study/commit/9f745c4fe98eab61c53608d4a787e8ca7aa071a9))

- **cli**: Let cstudy doctor --fix upgrade a workspace from v0.7.0
  ([`c688fb8`](https://github.com/bkuberek/coding-study/commit/c688fb88f854ccc6db6bdd3fd3ab593ca9274f31))

- **cli**: Open the web ui's event streams at once in Firefox
  ([`22a5d50`](https://github.com/bkuberek/coding-study/commit/22a5d50c7cf69150cfd32186c54e195d15bb727c))

- **cli**: Pass cstudy serve's --content to the commands it runs
  ([`b76766f`](https://github.com/bkuberek/coding-study/commit/b76766f7d629e671e2d6039db69203be3d4b0651))

- **cli**: Read compiler diagnostics on cstudy submit
  ([`825b34b`](https://github.com/bkuberek/coding-study/commit/825b34b95aed94eba36b08821ee151690c8a4742))

- **cli**: Refresh compiled runners' runtime copies under their build locks
  ([`ec91d63`](https://github.com/bkuberek/coding-study/commit/ec91d633c975a2001b68f2b596f739360d73a75b))

- **cli**: Show the web ui rows in cstudy doctor
  ([`7feeedc`](https://github.com/bkuberek/coding-study/commit/7feeedc04ffe4c6dbdfd5b64124b2ee5a7233aa4))

- **cli**: Start the workspace watch again after any failure or early end
  ([`282321b`](https://github.com/bkuberek/coding-study/commit/282321b076a57264f86be04b6bb20ef3d2f63570))

- **doctor**: Skip the Gradle warm-up when no working java is on PATH
  ([`9397bc9`](https://github.com/bkuberek/coding-study/commit/9397bc9de65d6cd118e1162c7b8a5257fdf8b036))

- **packaging**: Depend on gcc in the Homebrew formula on Linux
  ([`87fc673`](https://github.com/bkuberek/coding-study/commit/87fc673a02e864a71831bbaea3b6ff7a264fd6e2))

- **runners**: Fail the Go and Rust leak fixture only once its spinner runs
  ([`1eef800`](https://github.com/bkuberek/coding-study/commit/1eef800cfbb78e7a667ae301e1caf703affca1f6))

- **runners**: Give up the CPU at Python stress yields instead of spinning
  ([`54a8efa`](https://github.com/bkuberek/coding-study/commit/54a8efa45b3082d3264244114fc804216a2468fe))

- **runners**: Hand the GIL over at Python stress yields on a busy machine
  ([`5b7c7c7`](https://github.com/bkuberek/coding-study/commit/5b7c7c7287b8639e16293d45df4911a61317fadf))

- **runners**: Keep Python stress yields short on a busy CPU
  ([`d102db9`](https://github.com/bkuberek/coding-study/commit/d102db984c2372cfbd88ad5f428582604a1f0802))

- **runners**: Run 1000 racy increments per worker in conformance 9014
  ([`fc88d49`](https://github.com/bkuberek/coding-study/commit/fc88d49dbc8cd270cd62553095b972e530e30e94))

- **runners**: Show Delve's refusal of an older Go as an environment error in a Go project debug run
  ([`4efb027`](https://github.com/bkuberek/coding-study/commit/4efb02737ef7b3b7b69da1c7ee6df86342568555))

- **runners**: Stop hung Go, Rust, Gradle and tsc builds and keep user build settings out
  ([`648b368`](https://github.com/bkuberek/coding-study/commit/648b368a5a39f8505a99e09f8cb603f38d4b3f26))

- **runners**: Treat a zombie process as dead when waiting for cleanup
  ([`55db3ff`](https://github.com/bkuberek/coding-study/commit/55db3ff92d1eaf597038970f1a11e50ac64cc6f4))

- **runners**: Widen the race window of conformance 9014 on compiled runtimes
  ([`e70be57`](https://github.com/bkuberek/coding-study/commit/e70be5725247cb0f2be2e537ccffa83f5403ae25))

- **rust**: Touch sources replaced by older copies so Cargo rebuilds them
  ([`108c542`](https://github.com/bkuberek/coding-study/commit/108c5429fa953097dd1d543ead22d18d3479d276))

- **web-ui**: Ask before a run's cancel and doctor --fix in the page's own dialog
  ([`ac3d666`](https://github.com/bkuberek/coding-study/commit/ac3d666fd42427031ad3cdb3c2eb3211b320f3cd))

- **web-ui**: Draw the list and the attempt header at their final size
  ([`d20f5b7`](https://github.com/bkuberek/coding-study/commit/d20f5b7db6acea02ee4fdc50122ea75be00915ba))

- **web-ui**: Free the run controls when the server no longer keeps a streamed run
  ([`ebe7f56`](https://github.com/bkuberek/coding-study/commit/ebe7f56d8cf4ed3663936febb2fda09126585705))

- **web-ui**: Keep the page one window wide on a phone
  ([`1d7c0e4`](https://github.com/bkuberek/coding-study/commit/1d7c0e45c5136c26222ae76d8a2ae0b966817826))

- **web-ui**: Log in with a page that moves on, so --open keeps the cookie
  ([`4192fe4`](https://github.com/bkuberek/coding-study/commit/4192fe46238dc3c96f1bc4368e7ffbd66d2edc2b))

- **web-ui**: Pass axe-core and a keyboard-only pass on every view
  ([`93f8efa`](https://github.com/bkuberek/coding-study/commit/93f8efa4a3c29d938f25ffa36acf9be3286987df))

### Build System

- **cli**: Add the web server libraries and python -m coding_study
  ([`9d42a11`](https://github.com/bkuberek/coding-study/commit/9d42a11db51656904d3033eee068c05d3a273cd9))

- **cli**: Declare markdown-it-py and Pygments, which the web ui imports
  ([`347e338`](https://github.com/bkuberek/coding-study/commit/347e33850754b7fce8fe121a4eb337b4bbc48c5a))

### Chores

- **conformance**: Drop the six-language lists that repeat the default
  ([`f9af95f`](https://github.com/bkuberek/coding-study/commit/f9af95fefa6730d32dac809c9d6daae6ab0bee9d))

### Continuous Integration

- Run the fast checks on Linux on every push and pull request
  ([`82e3d76`](https://github.com/bkuberek/coding-study/commit/82e3d76008dc6fc809ee9e16b0b55202a6aefa49))

### Documentation

- Accept the local web UI (ADR 0015) and specify it
  ([`afb2bdf`](https://github.com/bkuberek/coding-study/commit/afb2bdf67674e53c5f69e8b5c416dd607bb1ac8a))

- Add the Linux install notes a Linux container verified
  ([`779fb8d`](https://github.com/bkuberek/coding-study/commit/779fb8d1c25199fbd9791c3ff0e27ec1bab61b2a))

- Budget verify throughput for six languages and note the workspace-problem languages
  ([`b4ab94b`](https://github.com/bkuberek/coding-study/commit/b4ab94bcd7a4fb4803ed3a07f96fa97be1633ffb))

- List Workspace.locked_with_deadline among the web adapter's port methods
  ([`daf2647`](https://github.com/bkuberek/coding-study/commit/daf2647a64d472ca87af6ef0f045cfd3caadc04f))

- Record 405, the stop line, exit 143, httpx2 and the page template
  ([`5f004d7`](https://github.com/bkuberek/coding-study/commit/5f004d78a6bde9312930ca9ee30a03b8b1be629e))

- Set the Go project test target to 2 s from 0.8.0 and 0.9.0 measurements
  ([`29d050d`](https://github.com/bkuberek/coding-study/commit/29d050d8c4a4b661068722195cfe9132e087e826))

- **roadmap**: Record the release measurements and the open Go target
  ([`73e0147`](https://github.com/bkuberek/coding-study/commit/73e0147e04c92dc2a0def72f7556084847d524e0))

- **specs**: Build the web UI assets with pnpm
  ([`3a44ecb`](https://github.com/bkuberek/coding-study/commit/3a44ecb1cca271c74ea5313e1c256dd18d83afe4))

- **specs**: Describe the Python stress yield as it now works
  ([`78fd46b`](https://github.com/bkuberek/coding-study/commit/78fd46b7a96b954533974473f7dfdc72343f7b39))

- **specs**: Note the Delve and Go check, the Java-less doctor fix and Linux gcc
  ([`30cab03`](https://github.com/bkuberek/coding-study/commit/30cab03ad3fb1060ec9856fa8d74db1eb430f7f9))

- **specs**: Propose a local web UI
  ([`645ff49`](https://github.com/bkuberek/coding-study/commit/645ff49ad7f8735332d7f9d4d737a2dd08b032f1))

- **specs**: Say which web API documents the schema covers
  ([`d5356f9`](https://github.com/bkuberek/coding-study/commit/d5356f9df465a4598ca02a61f3c63f8581ec2554))

- **web-ui**: Add the cstudy serve guide, its README section and screenshots
  ([`2f099ea`](https://github.com/bkuberek/coding-study/commit/2f099ea5f8369e47125f990ce04246aefaf256bd))

- **web-ui**: Record NFR-11 timings and tick what U11 verified in Phase 9
  ([`7e72bc3`](https://github.com/bkuberek/coding-study/commit/7e72bc3a326a4fca8ddb0b11cb3ee5cdd50d9743))

- **web-ui**: Tick the parity criterion and the diagnostic marker in Phase 9
  ([`7048b9e`](https://github.com/bkuberek/coding-study/commit/7048b9e1f360d4998ec11d084cad2e8639b4597e))

### Features

- **cli**: Add cstudy doctor --json
  ([`9f24f80`](https://github.com/bkuberek/coding-study/commit/9f24f803fb5214a1bd9aae55b5724e8699e60fbf))

- **cli**: Add cstudy history
  ([`6fcf525`](https://github.com/bkuberek/coding-study/commit/6fcf525069cef69aeb5227cca443798a454aaa41))

- **cli**: Add cstudy list --kind and --json
  ([`a249625`](https://github.com/bkuberek/coding-study/commit/a249625cdb0bd3966e4fbbd2baba1d962be13e4e))

- **cli**: Add cstudy next --json
  ([`639adf4`](https://github.com/bkuberek/coding-study/commit/639adf41f935621277db97883be37f688fceb96e))

- **cli**: Add cstudy serve, the local web UI server and its security layer
  ([`59e17eb`](https://github.com/bkuberek/coding-study/commit/59e17eb22751d365c382e27f77f00cd7579663e8))

- **cli**: Add diagnostic parsers for javac, kotlinc, go and rustc reports
  ([`94bf9a3`](https://github.com/bkuberek/coding-study/commit/94bf9a359fd3f1a4972093a3f9e897c14b79c649))

- **cli**: Check the web UI assets and server libraries for cstudy doctor
  ([`d650d4e`](https://github.com/bkuberek/coding-study/commit/d650d4efcac968a13bb1c7958179fee7a7dd3afd))

- **cli**: Download the progress export from the web ui
  ([`e76f9ce`](https://github.com/bkuberek/coding-study/commit/e76f9ceeb07428604766a6610c8dd907413f9f17))

- **cli**: End an --events run on SIGTERM with exit code 143
  ([`54fbd9c`](https://github.com/bkuberek/coding-study/commit/54fbd9cd0ed3b02d222cf32c4c7c048cdf662914))

- **cli**: Keep the web UI preferences in .cs/serve/preferences.json
  ([`b411dcf`](https://github.com/bkuberek/coding-study/commit/b411dcf9e51f4b559b91b73fe326b3edaa20e3d8))

- **cli**: Keep the web ui's theme in its preferences
  ([`32e4490`](https://github.com/bkuberek/coding-study/commit/32e4490cc90105733dbb772806d020972fe28fb6))

- **cli**: Move, delete and restore an attempt's files from the web ui
  ([`d43d187`](https://github.com/bkuberek/coding-study/commit/d43d1872e5b1c9bba7988fbbf7202a637c72685b))

- **cli**: Notify every tab of file, attempt, progress, run and job changes
  ([`6da421b`](https://github.com/bkuberek/coding-study/commit/6da421be172c7048f13fed487e96bc664b2ce3c7))

- **cli**: Read compiler reports of single files and projects into diagnostics
  ([`e2dd1a8`](https://github.com/bkuberek/coding-study/commit/e2dd1a8b1b51cb2fc8bffde91593fb57fc9cee6a))

- **cli**: Reveal reference solutions in the web ui behind the cli's question
  ([`626783a`](https://github.com/bkuberek/coding-study/commit/626783a7978233232362a83b3721eede6f1ad053))

- **cli**: Run tests, submissions and jobs from the web ui as streamed child commands
  ([`6d32aff`](https://github.com/bkuberek/coding-study/commit/6d32aff3a3b270e9845a2cca31f349369cff2e93))

- **cli**: Save and create an attempt's files from the web ui
  ([`aa7d844`](https://github.com/bkuberek/coding-study/commit/aa7d844dd16859c8f2efd20f66c2ce902fd47554))

- **cli**: Serve progress stats and import an export in the web ui
  ([`3b45e5d`](https://github.com/bkuberek/coding-study/commit/3b45e5df1cab98aa006521746cfb0b98851f7141))

- **cli**: Serve the web ui's reads: problems, statements, history, next, status, files and doctor
  ([`e4b0011`](https://github.com/bkuberek/coding-study/commit/e4b00117b4be81c2dc5245570248a82a3053ca21))

- **cli**: Show cstudy status for every kind of problem and item
  ([`6009a9d`](https://github.com/bkuberek/coding-study/commit/6009a9d199d6201000639b0d6607a4f99657577b))

- **cli**: Start and show mock interviews from the web ui
  ([`02188bd`](https://github.com/bkuberek/coding-study/commit/02188bdf2f540c1863bf99725880ab6c9b76986f))

- **cli**: Start attempts, reveal hints and finish attempts from the web ui
  ([`8822a0d`](https://github.com/bkuberek/coding-study/commit/8822a0d87becefe0bce17991dbb8a3355ffe8d74))

- **cli**: Stream cstudy test --events on every problem kind
  ([`2ee9382`](https://github.com/bkuberek/coding-study/commit/2ee9382b3823ef47e77601f0f11240002db532c1))

- **cli**: Warn on a busy machine and measure a contradicted ladder again
  ([`6bb6622`](https://github.com/bkuberek/coding-study/commit/6bb662223aef9400e0ecfb280c94a5e4ebd69860))

- **cli**: Write, move and delete files within a folder atomically and without following links
  ([`354b587`](https://github.com/bkuberek/coding-study/commit/354b5871cf0b775109bbce701bcb392f14c423bf))

- **doctor**: Warn when the installed Delve refuses the installed Go
  ([`12db9a7`](https://github.com/bkuberek/coding-study/commit/12db9a7f183613b07108ef127c6bd98f4aed6c8b))

- **rust**: Report the real outcome of a test debugged under lldb-server from libtest's log
  ([`91b8987`](https://github.com/bkuberek/coding-study/commit/91b8987dbabf0482244c0dcc2e5f65f5582717b4))

- **web-ui**: Add the page shell: problems, problem, attempt, health and settings views
  ([`714c172`](https://github.com/bkuberek/coding-study/commit/714c1728adab980176d30784b8f1f972978b5f43))

- **web-ui**: Build the CodeMirror 6 editor into the package
  ([`5550298`](https://github.com/bkuberek/coding-study/commit/5550298bdb23d081b68f90f0f7189599a6e7d8d4))

- **web-ui**: Create, rename, move, delete and restore files from the file tree
  ([`8f1ffcf`](https://github.com/bkuberek/coding-study/commit/8f1ffcf68cfa673711d9cb904616c204076bd2d6))

- **web-ui**: Follow changes from elsewhere through the notification stream
  ([`e85976a`](https://github.com/bkuberek/coding-study/commit/e85976af3f8b3573278ffb8550212f699b04a65d))

- **web-ui**: Save files from the editor, with unsaved marks and a conflict banner
  ([`f85e7ad`](https://github.com/bkuberek/coding-study/commit/f85e7ad51d4e574ac87896ec0600fb5b1edc4704))

- **web-ui**: Start, hint, finish, reveal solutions, run mocks and see progress from the page
  ([`283aeaf`](https://github.com/bkuberek/coding-study/commit/283aeaf6d9a25dde056d358ea3587d3bc13d17a7))

- **web-ui**: Stream runs and jobs in the page, with cancel, editor diagnostics and run on save
  ([`ad65afe`](https://github.com/bkuberek/coding-study/commit/ad65afecdab55a60d10976a927fec24d9f77b5ac))

### Performance Improvements

- **cli**: Check each problem schema once per process
  ([`af988f1`](https://github.com/bkuberek/coding-study/commit/af988f1a27e9359b0854594daf8dcf50d01a2e47))

- **cli**: Sync verify's project builds instead of rebuilding them
  ([`cd38b0c`](https://github.com/bkuberek/coding-study/commit/cd38b0c91d780845829c35165915ee80d0c1815a))

- **web-ui**: Fetch the run session, the tree actions and the off-path views on first use
  ([`3744b56`](https://github.com/bkuberek/coding-study/commit/3744b56175fb5add4b0151d019d23408e0faffff))

- **web-ui**: Fetch the start, done, solution and file dialogs when first used
  ([`c725729`](https://github.com/bkuberek/coding-study/commit/c725729013b3b341acdc3646c8fe8dec12acf513))

- **web-ui**: Link each chunk's stylesheet as it loads, out of app.css
  ([`425be17`](https://github.com/bkuberek/coding-study/commit/425be1763bfc96001c5143312377efd15b7ff46d))

### Refactoring

- **cli**: Address the web ui's done request by its attempt
  ([`5ea82dd`](https://github.com/bkuberek/coding-study/commit/5ea82dd3d622976e3fe00e2598bc98dd75d50b47))

- **cli**: Give the run events a module of their own
  ([`cf88485`](https://github.com/bkuberek/coding-study/commit/cf88485e47cbf50702be58291373aeb65d2f7d46))

- **cli**: Let list_items leave items out for a kind of problem
  ([`c341dd4`](https://github.com/bkuberek/coding-study/commit/c341dd445cd607dadfaf16c043c4ca640a4e3ce9))

- **cli**: One rule for a test run that passed every case
  ([`c339637`](https://github.com/bkuberek/coding-study/commit/c3396375c2e228e9aff138531b0b017526e5380f))

- **cli**: Share the stats document and since parser, and drop duplicate next and list checks
  ([`28100d0`](https://github.com/bkuberek/coding-study/commit/28100d0bbaa95a5d711c3bb8e160eaf1a05384e6))

- **web-ui**: One dialog module for the file tree, solutions and imports
  ([`937578b`](https://github.com/bkuberek/coding-study/commit/937578b3f2451f5272f1b60d190f38259195b402))

### Testing

- Leave zombies out of the leftover-process checks
  ([`c9f3162`](https://github.com/bkuberek/coding-study/commit/c9f31623271e2f0768451a46c16a3059c0576c60))

- Skip the rustfmt tests when rustfmt fails to run, as rustup's stub does
  ([`56cf4b1`](https://github.com/bkuberek/coding-study/commit/56cf4b1dcbf0d090bb1e449ea45581247c5820d8))

- **cli**: Check every read endpoint of a real cstudy serve, and the page in Chromium
  ([`9bb02f3`](https://github.com/bkuberek/coding-study/commit/9bb02f3ef08f82aaea988a527dc61a306cfa2d32))

- **cli**: Check verify's kept JVM builds by recompiles and Gradle time
  ([`ee1dfd7`](https://github.com/bkuberek/coding-study/commit/ee1dfd75ddd6230a0b1eb46a3279fcbe9171614d))

- **cli**: Fit the kept-builds Gradle share to a quiet machine
  ([`d71df96`](https://github.com/bkuberek/coding-study/commit/d71df968d46beebd38acc277a17e6c2ecc3615a0))

- **cli**: Play a compile error of each compiled language through cstudy test --events
  ([`4104b15`](https://github.com/bkuberek/coding-study/commit/4104b15f8117fd557ada270435ca647ce8be48da))

- **cli**: Save and restore a project file through a real cstudy serve and in Chromium
  ([`874eb2e`](https://github.com/bkuberek/coding-study/commit/874eb2e98fdd6b4c0622a36dde7662a5906289e9))

- **cli**: Type-check without the optional browser group
  ([`d98962a`](https://github.com/bkuberek/coding-study/commit/d98962a3d90ef0f6e4e42ac1afd051d856574feb))

- **rust**: Expect lldb-server's unknown outcome for a debugged project test on Linux
  ([`373aa7b`](https://github.com/bkuberek/coding-study/commit/373aa7b15cfa967ee41888a4e5c66f9892318e2f))

- **web-ui**: Check a diagnostic marker, its jump and its clearing in each engine
  ([`f3384a2`](https://github.com/bkuberek/coding-study/commit/f3384a26313168739129c683cfd3d3ee71f6f65a))

- **web-ui**: Describe the API's own documents in web-api.schema.json
  ([`9a95caa`](https://github.com/bkuberek/coding-study/commit/9a95caa33515479ccba5a1aa135b355605b5817b))

- **web-ui**: Run the browser tests in chromium, firefox and webkit
  ([`f9bb84b`](https://github.com/bkuberek/coding-study/commit/f9bb84bd36b084a3024e934338e3ed92dc4497a3))

- **web-ui**: See a save start a run when Run on save is on, in a real browser
  ([`d27a1db`](https://github.com/bkuberek/coding-study/commit/d27a1db56ae65ff0a17c3b08e176e31a6fa90664))

- **web-ui**: Walk start, test and done from the page for every kind and language
  ([`c678037`](https://github.com/bkuberek/coding-study/commit/c67803730297d00d99367d33e4c65930751983b5))


## v0.8.0 (2026-10-31)

### Bug Fixes

- **cli**: Cache the JVM runtime classpath in the doctor's warm-up
  ([`0263cb8`](https://github.com/bkuberek/coding-study/commit/0263cb8a7b39c5410b3edbffc41ad1206e142123))

- **cli**: Clear a project's stale bytecode before each project run
  ([`15f6000`](https://github.com/bkuberek/coding-study/commit/15f6000bd2ac0cc2ad755c87660d1a9a644f7af3))

- **cli**: Exit 2 from cstudy test when a project's code does not build or load
  ([`b52adaa`](https://github.com/bkuberek/coding-study/commit/b52adaabe82108d3b1b1efb0e621a68f5bd5122e))

- **cli**: Point cstudy test to cstudy done once every level is done
  ([`55a7f58`](https://github.com/bkuberek/coding-study/commit/55a7f587ccc8bf310db95bb065efb8256ceb99f3))

- **cli**: Report a project whose builds cannot be written
  ([`e5ddf30`](https://github.com/bkuberek/coding-study/commit/e5ddf30b13eed6e4b842ade526f51c8bf21c7ce8))

- **cli**: Start each project build from an empty folder
  ([`a145e5f`](https://github.com/bkuberek/coding-study/commit/a145e5f88c522a52f4000cae08020d9a5337abd2))

- **cli**: Tag Rust unit tests by the file their module path names
  ([`27bb6be`](https://github.com/bkuberek/coding-study/commit/27bb6beea7cb3cef53a51c44c89d4736b3e602eb))

- **progress**: Migrate a new progress database safely from concurrent processes
  ([`3b4577a`](https://github.com/bkuberek/coding-study/commit/3b4577a3bb1d778ae2b9da740f4af6790236e2b2))

### Chores

- **problems**: Link bank-project-python from scheduled-transfers-bank
  ([`8a7ff5e`](https://github.com/bkuberek/coding-study/commit/8a7ff5e545c3be615de915080651acb27f5f7280))

### Code Style

- **cli**: Import UserError on one line in the test command
  ([`6f1d922`](https://github.com/bkuberek/coding-study/commit/6f1d922da8691ac0e8cb9090118127df9405ef73))

### Documentation

- Accept project problems (ADR 0014) and specify the format
  ([`93148bf`](https://github.com/bkuberek/coding-study/commit/93148bf130b40527973f69a42a3a5ca1ceaadf53))

- Bring project-problem counts, Phase 8 exit criteria and TypeScript test rules up to date
  ([`858a152`](https://github.com/bkuberek/coding-study/commit/858a1525b6afabddad0bdd2db45dd60e12e26076))

- Count the six project problems and tick the Phase 8 pilots
  ([`51c667e`](https://github.com/bkuberek/coding-study/commit/51c667e4052e05d6401c07baa48852e05c7a4897))

- Note the Go suite's first build and the compile error trace
  ([`b10e6d6`](https://github.com/bkuberek/coding-study/commit/b10e6d6a6a2ab5a7f6c6043ccd408d2bb884fb31))

- Print the doctor's JVM warm-up commands as they run
  ([`f1f2248`](https://github.com/bkuberek/coding-study/commit/f1f22485378d83c3d9122658e8b7dc98cd2ed8b6))

- Say which replace lines cstudy doctor checks in a Go folder
  ([`fccbc08`](https://github.com/bkuberek/coding-study/commit/fccbc08ce50051feb86d33c121c2676b46066c0f))

- Specify Go project problems after spike K5
  ([`5ac7ec4`](https://github.com/bkuberek/coding-study/commit/5ac7ec4459ed09530be327dbda0e7efab1597dfa))

- Specify Java and Kotlin project problems from spike K4
  ([`59406e7`](https://github.com/bkuberek/coding-study/commit/59406e7c1c36fd14aeba2e6ecb96b6101ddf439b))

- **architecture**: Name the events schema among the schemas
  ([`8d41c42`](https://github.com/bkuberek/coding-study/commit/8d41c42ccf362de9f12ae5f044c8e51390c4637e))

- **cli**: Name Rust among the runners of project jobs
  ([`9b80a6f`](https://github.com/bkuberek/coding-study/commit/9b80a6f7e10dcda3cc904ab315894e052a097418))

- **specs**: Exclude uv.lock from project hashes and refuse an existing archive
  ([`bf1a22c`](https://github.com/bkuberek/coding-study/commit/bf1a22c60a70124f30ab753ba93eab557b7eaf33))

- **specs**: Map project hints to levels and fix the done example
  ([`4882635`](https://github.com/bkuberek/coding-study/commit/48826357b95fd5d4a2cf5003329301e16c538d37))

- **specs**: Propose project problems
  ([`6a52eff`](https://github.com/bkuberek/coding-study/commit/6a52eff309959aec2f44b69c3090e632b2140214))

- **specs**: Settle generated pytest edge cases
  ([`69b5720`](https://github.com/bkuberek/coding-study/commit/69b57200f63e3c899c49f2f5b3fa352a6ce8fb87))

- **specs**: Settle suite job edge cases and stale bytecode
  ([`d97708e`](https://github.com/bkuberek/coding-study/commit/d97708e686a565a4a33290e8091180d15890f32d))

- **specs**: Settle TypeScript project types and test selection
  ([`a993f75`](https://github.com/bkuberek/coding-study/commit/a993f759f1d902c9f07c4b125be0da8a75daa7d4))

- **specs**: Specify Rust project problems
  ([`d1a7144`](https://github.com/bkuberek/coding-study/commit/d1a71449dc422d8c141741b6160135d806f5732b))

### Features

- **application**: Write the generated test file of a project level
  ([`f812b4a`](https://github.com/bkuberek/coding-study/commit/f812b4ab7f10e5f1d3c0e31cea551396c68e1352))

- **cli**: Accept Go project problems in the domain and check their starters
  ([`82c7374`](https://github.com/bkuberek/coding-study/commit/82c73747b373c20537944bb40d70820763d01246))

- **cli**: Accept Java and Kotlin project problems
  ([`44f554e`](https://github.com/bkuberek/coding-study/commit/44f554e52f8269d9e2fb7060251494926abd1701))

- **cli**: Accept Rust project problems and seed their folders
  ([`dca247a`](https://github.com/bkuberek/coding-study/commit/dca247ac5b338f5cb062130bb6486d1f574f2dd0))

- **cli**: Add the project-go template to cstudy new
  ([`9c6278e`](https://github.com/bkuberek/coding-study/commit/9c6278e52eebc55766f9f1fd06946c99f70621e9))

- **cli**: Add the project-java and project-kotlin templates
  ([`be60dea`](https://github.com/bkuberek/coding-study/commit/be60dea3e62a167b1544a8ffafd594434f356288))

- **cli**: Add the project-rust problem template
  ([`0625c3d`](https://github.com/bkuberek/coding-study/commit/0625c3d40bdae6782d4270632c0ef3b31691707a))

- **cli**: Apply the project rules to bench, next and mock
  ([`0986f07`](https://github.com/bkuberek/coding-study/commit/0986f07976af6ce11dbf23b57a8296de0d0fb9fd))

- **cli**: Build, test and grade Java and Kotlin project folders
  ([`075ba06`](https://github.com/bkuberek/coding-study/commit/075ba063d12772babe330bc0b394337b92dd6b1a))

- **cli**: Check Go project folders in cstudy doctor
  ([`4108401`](https://github.com/bkuberek/coding-study/commit/4108401cc1548ff625a6c250ed7b8c6b262975bc))

- **cli**: Count a project's overlay as its reference
  ([`ff0d6da`](https://github.com/bkuberek/coding-study/commit/ff0d6da8e7ec65cf29603c541cd1d05c368640de))

- **cli**: Doctor checks project folders, their venv links and pytest
  ([`4fe4e17`](https://github.com/bkuberek/coding-study/commit/4fe4e170784b0be88ed74e526ae26a79bee544f7))

- **cli**: Generate Go testing level files for project problems
  ([`cb7ef39`](https://github.com/bkuberek/coding-study/commit/cb7ef39c55f858d33627aa12bbbf3f2fef90ebf5))

- **cli**: Generate JUnit 5 and kotlin.test level tests
  ([`ff12a52`](https://github.com/bkuberek/coding-study/commit/ff12a528c09fdf09e2348993ae3bba0ac22487a3))

- **cli**: Generate libtest level files for Rust projects
  ([`103ef23`](https://github.com/bkuberek/coding-study/commit/103ef23a58aaf8ed00df5011c3bab3bc3670061a))

- **cli**: Generate node:test level files for TypeScript projects
  ([`1b194b3`](https://github.com/bkuberek/coding-study/commit/1b194b30e058e8801c25d6289c7f2e13b817ff10))

- **cli**: Give a Go project folder a go.work of its own
  ([`051ba8e`](https://github.com/bkuberek/coding-study/commit/051ba8e26b0a54e91ad359e34f898c8122f19067))

- **cli**: Give project load errors structured diagnostics
  ([`c72a49c`](https://github.com/bkuberek/coding-study/commit/c72a49c8f1a57d163a837382fb29f1245cbe871a))

- **cli**: Grade and test Go project folders through their own go.work
  ([`41bebae`](https://github.com/bkuberek/coding-study/commit/41bebae99d2bb48271a839d15614b5aabead4455))

- **cli**: Grade project attempts by the levels finished
  ([`09f7d19`](https://github.com/bkuberek/coding-study/commit/09f7d1999f328acb1c9702a3a225b263eb8e6c04))

- **cli**: Grade project folders through the runner
  ([`4993ee1`](https://github.com/bkuberek/coding-study/commit/4993ee1269298122a889caa8a4c7f9fe16c07cfc))

- **cli**: Grade project problems with cstudy submit
  ([`07c7a51`](https://github.com/bkuberek/coding-study/commit/07c7a512d9d67b4da83054659f3a4ac06873c7d8))

- **cli**: Grade Rust projects and run their suites one process per test
  ([`96d447f`](https://github.com/bkuberek/coding-study/commit/96d447f177769222f9945afc13ffe32a7dbca533))

- **cli**: Launch python project jobs and expose project run seams
  ([`07801fb`](https://github.com/bkuberek/coding-study/commit/07801fbd4edcc1c0affb654f2e05c9c90c3a53c4))

- **cli**: Launch TypeScript project jobs and type-check project folders
  ([`edfbbc9`](https://github.com/bkuberek/coding-study/commit/edfbbc95fc4be072b729d371d05df65b466f550a))

- **cli**: Link a new Rust project folder in VS Code's settings on cstudy start
  ([`de744db`](https://github.com/bkuberek/coding-study/commit/de744dbd78b84bc6c8def5d23beac01eff1a7c01))

- **cli**: Link and check Rust project folders in ide and doctor
  ([`eca48ae`](https://github.com/bkuberek/coding-study/commit/eca48ae24a666e7a3e20b3ecca6e16b167dc7216))

- **cli**: List a project folder's tracked files through the Workspace port
  ([`fefd177`](https://github.com/bkuberek/coding-study/commit/fefd177da82736498732915b0b3d9025d767da41))

- **cli**: List diagnostics in the project JSON documents
  ([`d3a936f`](https://github.com/bkuberek/coding-study/commit/d3a936f23006cd44ebad98b9e28fc118457b65a9))

- **cli**: Lock a project while cstudy writes its tests and unlocks
  ([`7641ce6`](https://github.com/bkuberek/coding-study/commit/7641ce6b3f5792c0a66719841ada84125af19a86))

- **cli**: Name the first compiler line when a project does not compile in verify
  ([`0d9a91e`](https://github.com/bkuberek/coding-study/commit/0d9a91e649b93752198c788679fff1786cfb8d1a))

- **cli**: Project-python template for cstudy new
  ([`3ca75bd`](https://github.com/bkuberek/coding-study/commit/3ca75bd7a421f86a6a9e0977dcf47c649e36daf5))

- **cli**: Reach the project test generator and name cstudy submit for project levels
  ([`9585a13`](https://github.com/bkuberek/coding-study/commit/9585a130a73888f86069068912cc9beca9a2fac7))

- **cli**: Read diagnostics from a suite the framework refused
  ([`0154d05`](https://github.com/bkuberek/coding-study/commit/0154d05b2c8d456057f887b7667a6dbc8dce7e0f))

- **cli**: Record a starter manifest for each project folder
  ([`bf2ff04`](https://github.com/bkuberek/coding-study/commit/bf2ff041b2c9a29cbf078dffe2a0d3a1b376c835))

- **cli**: Resolve file targets inside project folders
  ([`d64023a`](https://github.com/bkuberek/coding-study/commit/d64023ac003611171bdc869f83b691456b76988e))

- **cli**: Restore one project file with cstudy start --restore
  ([`ae3a25f`](https://github.com/bkuberek/coding-study/commit/ae3a25f918730fac50f997328504f90876fe38c7))

- **cli**: Run a project's native tests with cstudy test
  ([`c53a77a`](https://github.com/bkuberek/coding-study/commit/c53a77a89a29f5c893328a64f9e250d563b4c0f0))

- **cli**: Run project suites through the runner protocol
  ([`b299d0a`](https://github.com/bkuberek/coding-study/commit/b299d0aadf3794b16810909634bdbc3273ad9dd7))

- **cli**: Run the Python project fixtures in the conformance suite
  ([`af2aca8`](https://github.com/bkuberek/coding-study/commit/af2aca86d23cef9794b16373134fb466d88dc8bb))

- **cli**: Say when the latest cstudy test predates an open level in cstudy status
  ([`95433c6`](https://github.com/bkuberek/coding-study/commit/95433c69d0a9bca4cb3ebb3dc902a94597f42b46))

- **cli**: Say why a project suite stopped early in its JSON
  ([`42e112e`](https://github.com/bkuberek/coding-study/commit/42e112ef50cd23b064ff167037b9201d2b81dcba))

- **cli**: Select the project-typescript template in cstudy new
  ([`4afa23c`](https://github.com/bkuberek/coding-study/commit/4afa23c244187dd05d5c4c612e6ad5d8202b31dd))

- **cli**: Ship the project-typescript template files
  ([`44e54ec`](https://github.com/bkuberek/coding-study/commit/44e54ecc4a5ff638e41ff6a3e47d344913d01e82))

- **cli**: Show a project attempt with cstudy status
  ([`3f367b2`](https://github.com/bkuberek/coding-study/commit/3f367b253fa6ffc7bd371be6c49fd6bebc315b5f))

- **cli**: Show a project's reference as an overlay on its starter
  ([`8bc62c9`](https://github.com/bkuberek/coding-study/commit/8bc62c985468e978ee3743fbb6175b3ad3100680))

- **cli**: Show only the hints of a project's unlocked levels
  ([`e0d87c1`](https://github.com/bkuberek/coding-study/commit/e0d87c1ce112461037bfd5a97926b1d2a6509cf0))

- **cli**: Show the state of each project file in cstudy status
  ([`7128bb0`](https://github.com/bkuberek/coding-study/commit/7128bb088dd43e5cbc41651606db2b2fdeea08da))

- **cli**: Start project problems in their folder
  ([`a15651a`](https://github.com/bkuberek/coding-study/commit/a15651a2652ee5f3f61d3deff6e082399dadf0e2))

- **cli**: Store project submissions and level unlocks
  ([`410751e`](https://github.com/bkuberek/coding-study/commit/410751ecaa6796b9bac9d9371a6e1feac9d164c4))

- **cli**: Stream each project test and graded case as it runs
  ([`aacfb91`](https://github.com/bkuberek/coding-study/commit/aacfb91a281d11c042558f7eac3865ebfd173123))

- **cli**: Stream project test and submit runs as events
  ([`6d509ce`](https://github.com/bkuberek/coding-study/commit/6d509ce02c7adff74f3ec80edce3440cdf799bdf))

- **cli**: Type-check a project folder with cstudy test --typecheck
  ([`43369b8`](https://github.com/bkuberek/coding-study/commit/43369b82c767bf84b813bec4d698a34ddbd56bba))

- **cli**: Verify project problems through their starter and reference builds
  ([`ae39de4`](https://github.com/bkuberek/coding-study/commit/ae39de4c088566546e77c3030bd37b403929103f))

- **domain**: Add the project problem kind
  ([`c084a2e`](https://github.com/bkuberek/coding-study/commit/c084a2ea611cc096cd14dc8e81f5fa942b14f974))

- **domain**: Load the starter and reference trees of project problems
  ([`2226e1b`](https://github.com/bkuberek/coding-study/commit/2226e1bfd36d5549849973f95a179cbd929bafb7))

- **domain**: Plan the generated test file of a project level
  ([`a0d98b5`](https://github.com/bkuberek/coding-study/commit/a0d98b5fd99d06862a6ec3dba74d999e7236a58b))

- **problems**: Add bank-project-go
  ([`d8b63df`](https://github.com/bkuberek/coding-study/commit/d8b63df23b7e9349241140d756ec1760b11b456e))

- **problems**: Add bank-project-java
  ([`d4b5956`](https://github.com/bkuberek/coding-study/commit/d4b5956d6352ff54290848cb67e7e5e823ca1eff))

- **problems**: Add bank-project-kotlin
  ([`ba1e6a3`](https://github.com/bkuberek/coding-study/commit/ba1e6a3b18a26a7e7e7e16fc52a495c776179d35))

- **problems**: Add bank-project-python
  ([`7eaadc1`](https://github.com/bkuberek/coding-study/commit/7eaadc1a06757125e62cb1ec58dffd42b9688dc9))

- **problems**: Add bank-project-rust
  ([`31d4414`](https://github.com/bkuberek/coding-study/commit/31d441474fa8d5e4931d5e751c0263648cf8260d))

- **problems**: Add bank-project-typescript as a draft
  ([`8c8a163`](https://github.com/bkuberek/coding-study/commit/8c8a163305dfce01b522d3433bdbda1df30cd9c6))

- **problems**: Link every bank pilot to its Rust sibling and to scheduled-transfers-bank
  ([`9a79d79`](https://github.com/bkuberek/coding-study/commit/9a79d792f004c757ce23270cbada60671312793d))

- **problems**: Mark bank-project-go ready
  ([`1ed50f0`](https://github.com/bkuberek/coding-study/commit/1ed50f0eb01fd5d6fa8d5b5a4b736a693ab4a58d))

- **problems**: Mark bank-project-java ready
  ([`9c156c4`](https://github.com/bkuberek/coding-study/commit/9c156c4e3aed2c390a4f0d2493280e53a6774d54))

- **problems**: Mark bank-project-kotlin ready
  ([`7b3aef4`](https://github.com/bkuberek/coding-study/commit/7b3aef44487a68086b82b9b1482c5b0c15325663))

- **problems**: Mark bank-project-python ready
  ([`5e859e0`](https://github.com/bkuberek/coding-study/commit/5e859e0394a67a307969cb1c69780214d24a1fd0))

- **problems**: Mark bank-project-rust ready
  ([`023ba8b`](https://github.com/bkuberek/coding-study/commit/023ba8bae16a8a13c18ea355b460b41b399cb99a))

- **problems**: Mark bank-project-typescript ready
  ([`a3031c7`](https://github.com/bkuberek/coding-study/commit/a3031c77827a2b6b5dfd8cabe45c13538bd604b9))

- **python**: Generate the pytest file of a project level
  ([`eff3278`](https://github.com/bkuberek/coding-study/commit/eff3278ee999982cf13df641733787b21c6fff9e))

- **runners**: Add the TypeScript project and node:test conformance fixtures
  ([`dd6ca3d`](https://github.com/bkuberek/coding-study/commit/dd6ca3de9a12551d6f476700f2f000ce640610ee))

- **runners**: Report a Go project that does not compile as a load error
  ([`dec5484`](https://github.com/bkuberek/coding-study/commit/dec54847e8535f995f9c632f588ae8f3ed90aef8))

- **runners**: Report a test that ends its Go test binary and run its package again
  ([`e3e4a4d`](https://github.com/bkuberek/coding-study/commit/e3e4a4d0bdd4fb6b74d9dedfedaba1f41e97a2d6))

- **runners**: Run a Go project's suite through go test -json
  ([`ab4a8a6`](https://github.com/bkuberek/coding-study/commit/ab4a8a6d60bd52e0b0590967ea19a86164679817))

- **runners**: Run node:test suite jobs in the TypeScript runner
  ([`3936f03`](https://github.com/bkuberek/coding-study/commit/3936f0301a6ca3f9207464b3bf5f77be46d2dc9c))

- **runners**: Run python project grading and pytest suite jobs
  ([`ce71816`](https://github.com/bkuberek/coding-study/commit/ce718160289bca32b5651c964b99c0e1d2bbec76))

- **statement**: Render project statements in their language
  ([`c43e023`](https://github.com/bkuberek/coding-study/commit/c43e0235de0d71ce9f64cf7a71844524a366b50d))

- **static**: Check project problems
  ([`143f4f3`](https://github.com/bkuberek/coding-study/commit/143f4f3994604f96161f6684ffaa5d55da910100))

- **workspace**: Add projects/ and pytest to the workspace template
  ([`d044add`](https://github.com/bkuberek/coding-study/commit/d044add2761ce2c01fb4ff5dd9aa0596617e900e))

- **workspace**: Seed, link, archive, hash and watch project folders
  ([`7b9ae8d`](https://github.com/bkuberek/coding-study/commit/7b9ae8d65fbf8c511f3024a8d857cdd9802649f9))

### Refactoring

- **cli**: Check Go project folders through the generic doctor seam
  ([`802b2eb`](https://github.com/bkuberek/coding-study/commit/802b2eb7d892f4264cca9b67cc05d46eedd245b9))

- **cli**: Drop the unsupported-language paths now that every language has project problems
  ([`7f2f1ad`](https://github.com/bkuberek/coding-study/commit/7f2f1adfa6086b950cc4f1fb85c2de8f201ee97a))

- **cli**: Give the project test exit code one home
  ([`710135f`](https://github.com/bkuberek/coding-study/commit/710135f23205075d62af534c8b36dbd74b0f6cd1))

- **cli**: Give the pytest install command one home
  ([`6b9d663`](https://github.com/bkuberek/coding-study/commit/6b9d6635c27ca1c858e84acb511b6c202c5ed7f0))

- **cli**: Share one test file printer between generators
  ([`b784e47`](https://github.com/bkuberek/coding-study/commit/b784e4731f18480360d379a975f73bde7c14834f))

- **cli**: Share the case report lines of cstudy test
  ([`503f324`](https://github.com/bkuberek/coding-study/commit/503f324af14e197fb75d1b1046cfe4f618c0261c))

- **cli**: Verify through Toolchains.project_test_generator
  ([`fcf3ab4`](https://github.com/bkuberek/coding-study/commit/fcf3ab4ee280027e52ef545b0894e21a04fed9b2))

### Testing

- **cli**: Build Java and Kotlin project folders offline after the warm-up
  ([`d4130ea`](https://github.com/bkuberek/coding-study/commit/d4130ea3f406891c57a818ce78754da7f7e77f1e))

- **cli**: Count project-go among the one-language templates
  ([`bc8c53c`](https://github.com/bkuberek/coding-study/commit/bc8c53cb461e91cebef93cb7d1920d9d98653125))

- **cli**: Count the pilot's new tie case in the grading test
  ([`5f7b8c4`](https://github.com/bkuberek/coding-study/commit/5f7b8c4b5ea210d8afd807f8c9a251b28389ed62))

- **cli**: Debug a Go project through Delve end to end
  ([`5e5761b`](https://github.com/bkuberek/coding-study/commit/5e5761b33f9e25232c0b0bd329ecb4d5cc9cf0be))

- **cli**: Export carries a project attempt's level unlocks
  ([`e7b4843`](https://github.com/bkuberek/coding-study/commit/e7b48433265684947a0ea4ba857bb5da5b871130))

- **cli**: List the files of the JVM project templates
  ([`36f409b`](https://github.com/bkuberek/coding-study/commit/36f409b9577c67fea541fbaa63c1f566784aa5cc))

- **cli**: Play a Go project problem end to end through the Go toolchain
  ([`f382d2e`](https://github.com/bkuberek/coding-study/commit/f382d2ebd917430c3508611f20862108b2c3c9a1))

- **cli**: Play the pilot project from start to done
  ([`6d94111`](https://github.com/bkuberek/coding-study/commit/6d94111a3afd7f7be832b7b87b5e261312ecca61))

- **cli**: Run Rust project problems end to end through cargo
  ([`ce850f0`](https://github.com/bkuberek/coding-study/commit/ce850f0d8fcdcb33bf635f4319fc364c7595060a))

- **cli**: Stop at breakpoints in a debugged TypeScript project suite
  ([`0537f6f`](https://github.com/bkuberek/coding-study/commit/0537f6f175494627c5cb056323215192f5676e11))

- **conformance**: Add the Java and Kotlin project fixtures 9026 to 9029
  ([`11bd847`](https://github.com/bkuberek/coding-study/commit/11bd84773000f4ea2e1fb341dc3f569ee3ff465d))

- **problems**: Add a three-way tie to bank-project-python
  ([`6ad2829`](https://github.com/bkuberek/coding-study/commit/6ad2829eab1156d70e39e203aae9e36802229f5d))

- **problems**: Add hidden case h22 to the Python, TypeScript, Kotlin and Go bank pilots
  ([`0eaae50`](https://github.com/bkuberek/coding-study/commit/0eaae5076d146a212aa5a7963ede9ba053311038))

- **runners**: Add Go project and go test suite conformance fixtures
  ([`fb7a4d3`](https://github.com/bkuberek/coding-study/commit/fb7a4d3768652a3a93cee38d6aaba937770435f4))

- **runners**: Add Rust project and cargo suite conformance fixtures
  ([`39b415a`](https://github.com/bkuberek/coding-study/commit/39b415a6edda3ca2ad47a8993b0622850be8b656))


## v0.7.0 (2026-10-30)

### Documentation

- **readme**: Count the new practical problem
  ([`2d5c077`](https://github.com/bkuberek/coding-study/commit/2d5c077a336f3ebaa1bcb357d015087ba6c48d1f))

### Features

- **problems**: Add scheduled-transfers-bank
  ([`6afbc0c`](https://github.com/bkuberek/coding-study/commit/6afbc0c9af793c7bff7e6cb138a1b7f19bbdbc6a))


## v0.6.0 (2026-10-30)

### Bug Fixes

- **cli**: Keep jvm runs off runner jars that a build rewrites
  ([`9c5045c`](https://github.com/bkuberek/coding-study/commit/9c5045c44c840bc4dab1d5e7f2598316f8ea5750))

- **cli**: Run each language's stress cases alone in verify
  ([`7dddb58`](https://github.com/bkuberek/coding-study/commit/7dddb58a61124d77ec8fb7f2848860afbb73316e))

- **content**: Let workspace problems list any subset of the languages
  ([`fd08d5c`](https://github.com/bkuberek/coding-study/commit/fd08d5c81778b8fe0819a5a44c911291bde229d2))

- **debug**: List leftover processes from /proc on Linux, where BusyBox ps rejects -x
  ([`6a73a93`](https://github.com/bkuberek/coding-study/commit/6a73a937ea164bfb069a5a8ae2cbea24a023a0c0))

- **debug**: Stop the rust runner left behind by a detached debugger
  ([`b86db33`](https://github.com/bkuberek/coding-study/commit/b86db338acda76ebb6f92023d032171d062bc56a))

- **doctor**: Warn about missing optional-language workspace files
  ([`630c4dc`](https://github.com/bkuberek/coding-study/commit/630c4dc830abc65f25fea238420eeda9e5ba9308))

- **go**: Never name a Go file with a GOOS, GOARCH or _test suffix
  ([`7995a14`](https://github.com/bkuberek/coding-study/commit/7995a14aa5c4f35b8e1ee64193200c3290f00a14))

- **go**: Pin GOFLAGS so a user's go env cannot break builds
  ([`859ee2a`](https://github.com/bkuberek/coding-study/commit/859ee2a601a54adcd20cb62f33e8059c0937f58a))

- **go-runner**: Reset decimal settings before decoding arguments, in bench and stress runs
  ([`daa5545`](https://github.com/bkuberek/coding-study/commit/daa55454eabfada005509f50545591a44e545233))

- **ide**: Kill the rust debuggee when the debug session ends
  ([`9d75774`](https://github.com/bkuberek/coding-study/commit/9d75774a9b3c0fd677fd8adbf181b55cb8c1f1c2))

- **ide**: Stop CodeLLDB printing 'Process must be launched' after a finished Rust debug run
  ([`5f74f52`](https://github.com/bkuberek/coding-study/commit/5f74f523f3dd8a4be2db220d66ecd870e0116f53))

- **problems**: Give valid-anagram one input family at every ladder size
  ([`4fcd58a`](https://github.com/bkuberek/coding-study/commit/4fcd58a2c2c551114b245d0f8967b0e127c6a67c))

- **problems**: Make the go no-lock lru cache fail in nearly every run
  ([`1911cca`](https://github.com/bkuberek/coding-study/commit/1911ccaeea588fbd20928c9888a053bba11f4107))

- **runner**: Kill the debuggee's leftover processes even when the group kill fails
  ([`1abb89e`](https://github.com/bkuberek/coding-study/commit/1abb89e987636b3b65d87527447183c31dd3a8b2))

- **runners**: Remove the Go and Rust private binary copy when the run ends
  ([`5241472`](https://github.com/bkuberek/coding-study/commit/5241472c258620eafa9ed40abd099b9262f81592))

- **rust**: Keep symbols and debug info when a user config strips them
  ([`f307a68`](https://github.com/bkuberek/coding-study/commit/f307a68b611f30f61a73092452dd427bf90a0381))

- **rust**: Keep the similar-name hint of a misnamed method
  ([`46a9262`](https://github.com/bkuberek/coding-study/commit/46a926290cc610e7f26e377323c1a8fe10a3bbcd))

- **rust**: Write keyword names as raw identifiers
  ([`6d4d34f`](https://github.com/bkuberek/coding-study/commit/6d4d34f591d18a9c49330172dbb62f1b743ee9e6))

- **verify**: Reject decimal values with more than 28 digits after the point
  ([`a882093`](https://github.com/bkuberek/coding-study/commit/a882093335aed20e6bd0e1ce9cfcaabee0b72cf0))

### Build System

- **rust**: Declare rust-version 1.80 in the runner crates, harness packages and practice project
  ([`11bc210`](https://github.com/bkuberek/coding-study/commit/11bc2102b9809a057b15d36d70e4aa21aaeed59e))

### Documentation

- Describe the go and rust doctor checks and shared compiled builds
  ([`532954b`](https://github.com/bkuberek/coding-study/commit/532954b1c6a8523c04b9063ba0c61649f5b7e664))

- Describe the go- and rust-native debugging problems
  ([`2067620`](https://github.com/bkuberek/coding-study/commit/206762071cb1fc018dad63d514c03c1bd9390d39))

- Record ladder decisions for adaptive sorts and early-exit searches
  ([`5a95c69`](https://github.com/bkuberek/coding-study/commit/5a95c69a5475f48a68940f8d5ee53b10b32691d0))

- Record stress turns and runtime jar copies in ADR 0012
  ([`c7544d8`](https://github.com/bkuberek/coding-study/commit/c7544d8fdc2385fb467ef03dfe603cc4d6e160e3))

- **adr**: 0012 go and rust
  ([`296687e`](https://github.com/bkuberek/coding-study/commit/296687e29987c657262344a0f92540444dd4cb29))

- **adr**: Drop the sentence that called the references planned
  ([`8fc8857`](https://github.com/bkuberek/coding-study/commit/8fc88573b310aabf326f36676b216316b97d2287))

- **architecture**: Drop the stale go debug example
  ([`8bec9a5`](https://github.com/bkuberek/coding-study/commit/8bec9a5bb285882008185004bd3ab37d382a8db4))

- **catalog**: List the 263 items with counts per track
  ([`176c04a`](https://github.com/bkuberek/coding-study/commit/176c04a1dfb6408460c1dfab25a9da4eb7350d98))

- **concurrency**: Record how go and rust broken references race
  ([`23ec673`](https://github.com/bkuberek/coding-study/commit/23ec673f215787085c4fc96ea9e38bf5d6362d2a))

- **conformance**: Describe the go and rust decimal and date references
  ([`61545db`](https://github.com/bkuberek/coding-study/commit/61545db3fae2f59fe26b8ea4bfe0517b6e7fb8dd))

- **debug**: Describe the go and rust debuggers
  ([`1973fd0`](https://github.com/bkuberek/coding-study/commit/1973fd015604121c9c13ba5f77d32ee1eee86225))

- **guides**: Install go and rust
  ([`3e19707`](https://github.com/bkuberek/coding-study/commit/3e1970710396f495c5924680baacb56515e779c0))

- **homebrew**: Mention optional go and rust in the caveats
  ([`e2896e5`](https://github.com/bkuberek/coding-study/commit/e2896e5956e84b1b3e0c7ac8facb374780fb8a02))

- **ide**: Describe the go and rust vs code settings
  ([`e1cc294`](https://github.com/bkuberek/coding-study/commit/e1cc2942a9b51bbda952f38004832c3c775c68f3))

- **readme**: Practice in all six languages
  ([`52f7a97`](https://github.com/bkuberek/coding-study/commit/52f7a978e1db1d1c12af749b081631722c3f0bbc))

- **specs**: Describe the go runner, stubs and build
  ([`fa6fa88`](https://github.com/bkuberek/coding-study/commit/fa6fa885e52ec4abb796b959ba4c81a4ae2506cd))

- **specs**: Describe the rust runner, bridge and build
  ([`68492d7`](https://github.com/bkuberek/coding-study/commit/68492d7600313680e263091684a0dbe75c9b721a))

- **specs**: List the go and rust doctor checks
  ([`fe8f57d`](https://github.com/bkuberek/coding-study/commit/fe8f57d2f175bdc25619235fcc7d1e1bb8cfe6cb))

- **specs**: List the vendored decimal and date wiring of the go and rust projects
  ([`1c82d50`](https://github.com/bkuberek/coding-study/commit/1c82d502a1561a6b528ee9a01eeb940a3d5d0516))

- **specs**: Say an interrupted debug run also stops the detached runner
  ([`b4579a5`](https://github.com/bkuberek/coding-study/commit/b4579a548fcdb0d3eb0bbf7c8f3ee3929dde606b))

### Features

- **cli**: Name a busy machine when stress checks fail in verify
  ([`f31a1da`](https://github.com/bkuberek/coding-study/commit/f31a1da8c010114827b1e3c4b8cb8f4db8d3fe57))

- **content**: Name the languages of an approach with fewer references
  ([`e9069ac`](https://github.com/bkuberek/coding-study/commit/e9069accf618af07d7316ea1a5489c3ae1b0e20c))

- **content**: Require go and rust references
  ([`2b31271`](https://github.com/bkuberek/coding-study/commit/2b312718c99ea71ce12cbb41eec0bfa05bd0dd7f))

- **debug**: Attach delve to go runs
  ([`fcd698f`](https://github.com/bkuberek/coding-study/commit/fcd698fa572efda0562e2a08508bdb9f79c7c706))

- **debug**: Attach lldb to rust runs
  ([`e0c732d`](https://github.com/bkuberek/coding-study/commit/e0c732d7fb309cdce6ce263ece88a2091bb18161))

- **doctor**: Check the go and rust debuggers
  ([`3d8280a`](https://github.com/bkuberek/coding-study/commit/3d8280afa32c692048eafe995561611368e6a012))

- **doctor**: Check the go and rust toolchains
  ([`0a113ed`](https://github.com/bkuberek/coding-study/commit/0a113ed4332f33881f69685c625f714a27722c40))

- **domain**: Add go and rust as optional languages
  ([`2b5c272`](https://github.com/bkuberek/coding-study/commit/2b5c272ca07c92d9e8abb86c9b5ccc6f57e31233))

- **go**: Run concurrent stress jobs
  ([`5585053`](https://github.com/bkuberek/coding-study/commit/5585053fce059f8814dc96ded642bc1cd13e3ba5))

- **go**: Support decimal and date with a vendored shopspring/decimal
  ([`34fd2ec`](https://github.com/bkuberek/coding-study/commit/34fd2ece28dbc5b61623684d5d4d28f90ab687be))

- **ide**: Add go and rust debug configurations
  ([`aa93372`](https://github.com/bkuberek/coding-study/commit/aa9337235ea079a7c9cc1989f65ef885e7d0c912))

- **ide**: Set up vs code for go and rust
  ([`0134bc7`](https://github.com/bkuberek/coding-study/commit/0134bc73f98ff58d7f87b8ede0673806357c62db))

- **languages**: Build and run go solutions
  ([`db85a2a`](https://github.com/bkuberek/coding-study/commit/db85a2a387d94d30b740d944d58a81fa02bacb1e))

- **languages**: Build and run rust solutions
  ([`58ec5e6`](https://github.com/bkuberek/coding-study/commit/58ec5e641551d0eb2dba8787f41db8d244c68c45))

- **naming**: Name members by role for go and rust
  ([`671a192`](https://github.com/bkuberek/coding-study/commit/671a19259c3d4450ebdbff0f7f32606180ed3256))

- **problems**: Add debug-append-aliasing
  ([`899522a`](https://github.com/bkuberek/coding-study/commit/899522a62ad6d5f4e665e3d95d71ab86c2441095))

- **problems**: Add debug-char-boundary
  ([`42c417c`](https://github.com/bkuberek/coding-study/commit/42c417c767d9c42759ff519dc4cae3b2d66b82f8))

- **problems**: Add debug-clone-mutation
  ([`367813d`](https://github.com/bkuberek/coding-study/commit/367813d7990983f85a81c1aae952b97ab0b28ce8))

- **problems**: Add debug-float-ordering
  ([`80e340f`](https://github.com/bkuberek/coding-study/commit/80e340ffeefa0302b8cb09c2e3354510e8aa9e41))

- **problems**: Add debug-nil-map-write
  ([`3e1d8df`](https://github.com/bkuberek/coding-study/commit/3e1d8df95d68fb24af4859c03d9a62966a0ee17a))

- **problems**: Add debug-range-value-copy
  ([`093c8fd`](https://github.com/bkuberek/coding-study/commit/093c8fd1b874824340322bc33bbd3016761b529b))

- **problems**: Add debug-shadowed-variable
  ([`2223d71`](https://github.com/bkuberek/coding-study/commit/2223d712479101d6ef8e318756bc99b77eafc7e8))

- **problems**: Add debug-unsigned-underflow
  ([`7d5dce9`](https://github.com/bkuberek/coding-study/commit/7d5dce9b577101fe226ccb7e5fdc6ed8914f7503))

- **problems**: Add go and rust references to accounts-merge
  ([`805e350`](https://github.com/bkuberek/coding-study/commit/805e3500aff1d491a640ace1ed8593f702fc6c85))

- **problems**: Add go and rust references to add-two-numbers
  ([`e480e1b`](https://github.com/bkuberek/coding-study/commit/e480e1b5c64f75e1943315a5be7e4ee8e29ccb9a))

- **problems**: Add go and rust references to alien-dictionary
  ([`042dbba`](https://github.com/bkuberek/coding-study/commit/042dbba79343fa0d83b2bc8af945319f0b0fa304))

- **problems**: Add go and rust references to all-possible-recipes
  ([`e47cece`](https://github.com/bkuberek/coding-study/commit/e47ceceaff71b6053188a76b08239b968692668b))

- **problems**: Add go and rust references to almost-palindrome
  ([`7111737`](https://github.com/bkuberek/coding-study/commit/711173773b2ed171b1de729d874bda14b3648bec))

- **problems**: Add go and rust references to api-gateway
  ([`89e3260`](https://github.com/bkuberek/coding-study/commit/89e32607a071a87c4ebe86b5bc8998f1e38b8f16))

- **problems**: Add go and rust references to balanced-binary-tree
  ([`e46be33`](https://github.com/bkuberek/coding-study/commit/e46be332deedf92f56e13c68a89a8e9a82e299cb))

- **problems**: Add go and rust references to banking-system
  ([`2f402c9`](https://github.com/bkuberek/coding-study/commit/2f402c9994ba49863ec31b1eb0429ca449e415bd))

- **problems**: Add go and rust references to basic-calculator
  ([`5f4242c`](https://github.com/bkuberek/coding-study/commit/5f4242cc8bbf843dbfdedfb45520ddae74faab02))

- **problems**: Add go and rust references to best-time-to-buy-sell-stock
  ([`4d654be`](https://github.com/bkuberek/coding-study/commit/4d654beba9c91ef15ae1c697b13ec27db0c60903))

- **problems**: Add go and rust references to binary-search
  ([`c5b6891`](https://github.com/bkuberek/coding-study/commit/c5b6891a7e0c58c4cbae2394af9348737f7dbca9))

- **problems**: Add go and rust references to bipartite-graph
  ([`e6defb0`](https://github.com/bkuberek/coding-study/commit/e6defb02ac383120eb2073edc83899f1c8e46ac2))

- **problems**: Add go and rust references to bst-iterator
  ([`bf75c8d`](https://github.com/bkuberek/coding-study/commit/bf75c8d83296c75869c3ec0c23350ebd647344d7))

- **problems**: Add go and rust references to burst-balloons
  ([`6e62816`](https://github.com/bkuberek/coding-study/commit/6e628168d0d36abcf4b08b1215be1ddb5493458b))

- **problems**: Add go and rust references to cache-service
  ([`994b3ba`](https://github.com/bkuberek/coding-study/commit/994b3ba5924d3937461f12c31becc2dcfe422af1))

- **problems**: Add go and rust references to can-attend-meetings
  ([`5a06582`](https://github.com/bkuberek/coding-study/commit/5a065823b60a71f6b5a06c1d8349da9d41faf0f3))

- **problems**: Add go and rust references to candy-distribution
  ([`93bdf32`](https://github.com/bkuberek/coding-study/commit/93bdf32d7320e236fe0a096dfcddf264b9eaf8de))

- **problems**: Add go and rust references to car-fleet
  ([`2bea091`](https://github.com/bkuberek/coding-study/commit/2bea0915f20988db881e8caa7e9a395cab817832))

- **problems**: Add go and rust references to car-pooling
  ([`e6c73be`](https://github.com/bkuberek/coding-study/commit/e6c73be053e52879dd01e57b382f295dc945d312))

- **problems**: Add go and rust references to certificate-expiry-alerts
  ([`79c1272`](https://github.com/bkuberek/coding-study/commit/79c127286d75d137112c66c602eabf123eda3471))

- **problems**: Add go and rust references to cheapest-flights-k-stops
  ([`d6e94fe`](https://github.com/bkuberek/coding-study/commit/d6e94fe001b755178fd7b68bd104a057b8792073))

- **problems**: Add go and rust references to city-fewest-neighbors
  ([`1bb2ad8`](https://github.com/bkuberek/coding-study/commit/1bb2ad8d97503fe7a319702054c776b283ce8160))

- **problems**: Add go and rust references to climbing-stairs
  ([`ef652fb`](https://github.com/bkuberek/coding-study/commit/ef652fbab954f0b55ea1932482016305e54d4aca))

- **problems**: Add go and rust references to clone-graph
  ([`4c0bdef`](https://github.com/bkuberek/coding-study/commit/4c0bdefd2906172e1433c352f594878c4575d9be))

- **problems**: Add go and rust references to cloud-file-storage
  ([`cc992b2`](https://github.com/bkuberek/coding-study/commit/cc992b2cc5e93dd8cef36898e9ebde512fbf6122))

- **problems**: Add go and rust references to coin-change
  ([`51c5f33`](https://github.com/bkuberek/coding-study/commit/51c5f33fc333c15b70e7a14d9cfc3f5b2a578bd5))

- **problems**: Add go and rust references to coin-change-ways
  ([`2a9a11b`](https://github.com/bkuberek/coding-study/commit/2a9a11b3a959b41b03e98c9d9e12c0342b76f189))

- **problems**: Add go and rust references to combination-sum
  ([`acfaa19`](https://github.com/bkuberek/coding-study/commit/acfaa19a9c74a243c62b36401fa0aabf75b9a696))

- **problems**: Add go and rust references to combination-sum-no-reuse
  ([`3eee1d4`](https://github.com/bkuberek/coding-study/commit/3eee1d4e566a717529f1ed067f7288d1b8350d86))

- **problems**: Add go and rust references to container-with-most-water
  ([`0982930`](https://github.com/bkuberek/coding-study/commit/09829302b041bb1e6bd32a94db5a692a99900f6e))

- **problems**: Add go and rust references to contains-duplicate
  ([`b47cc41`](https://github.com/bkuberek/coding-study/commit/b47cc41ec26467ca10faa327be99a32fe6bc9288))

- **problems**: Add go and rust references to continuous-subarray-sum
  ([`c2b11cc`](https://github.com/bkuberek/coding-study/commit/c2b11cced07c61497e23b4cae063f978a0268cb5))

- **problems**: Add go and rust references to contractor-exposure-rollup
  ([`8150f42`](https://github.com/bkuberek/coding-study/commit/8150f42adb2f24ab40ef0232dc3fbc8580f3a638))

- **problems**: Add go and rust references to count-connected-components
  ([`56d9b68`](https://github.com/bkuberek/coding-study/commit/56d9b68e5e9cea1732f8da3a9320edf52c23e20f))

- **problems**: Add go and rust references to count-set-bits
  ([`613e92d`](https://github.com/bkuberek/coding-study/commit/613e92d3148da6d0d5a2bb604725c202c8d67e63))

- **problems**: Add go and rust references to count-smaller-after-self
  ([`8a0f5dd`](https://github.com/bkuberek/coding-study/commit/8a0f5dd05a1e1ff79cd0a45dedbcc3978cc3e53f))

- **problems**: Add go and rust references to counting-bits
  ([`0c53767`](https://github.com/bkuberek/coding-study/commit/0c53767f3b8d8d261e7c079036c88df163a45095))

- **problems**: Add go and rust references to course-schedule
  ([`8a28f65`](https://github.com/bkuberek/coding-study/commit/8a28f65a45966ca3951f6d7013cbea6444f5f0ce))

- **problems**: Add go and rust references to course-schedule-ii
  ([`39bd986`](https://github.com/bkuberek/coding-study/commit/39bd9863e1c2ab89a206bc4ac8c046ff6423d919))

- **problems**: Add go and rust references to coverage-gaps
  ([`faa14d0`](https://github.com/bkuberek/coding-study/commit/faa14d0c24c9a0f4a86a11dcb4b0c2ead873e00d))

- **problems**: Add go and rust references to critical-connections
  ([`db847ee`](https://github.com/bkuberek/coding-study/commit/db847ee971bc0f7e6ad65838da5f6d99a15c408a))

- **problems**: Add go and rust references to daily-temperatures
  ([`fae24c2`](https://github.com/bkuberek/coding-study/commit/fae24c2748eae71920b1f335acb8cc41261bc813))

- **problems**: Add go and rust references to decode-string
  ([`3c5b862`](https://github.com/bkuberek/coding-study/commit/3c5b8626a3e1be5212c648c024e8633af4d1f3ba))

- **problems**: Add go and rust references to decode-ways
  ([`1b67429`](https://github.com/bkuberek/coding-study/commit/1b6742972501ee7bc7ee0ef4d3a3b98b318f5f91))

- **problems**: Add go and rust references to design-twitter
  ([`c7b3140`](https://github.com/bkuberek/coding-study/commit/c7b3140d741d236285fdd4f096a2042ec93d4e3d))

- **problems**: Add go and rust references to diameter-binary-tree
  ([`166eb21`](https://github.com/bkuberek/coding-study/commit/166eb215fbc722fd247e24b28cf9910cca9370ce))

- **problems**: Add go and rust references to distinct-subsequences
  ([`62026f5`](https://github.com/bkuberek/coding-study/commit/62026f5ef358b53c422a14516d4e24d7805def29))

- **problems**: Add go and rust references to duplicate-contractor-records
  ([`f3b9624`](https://github.com/bkuberek/coding-study/commit/f3b962495f52cead5e45ddc88a3419c1f7b56b72))

- **problems**: Add go and rust references to earned-premium-as-of
  ([`e161e7b`](https://github.com/bkuberek/coding-study/commit/e161e7b7896f1cf994dfa9b408a80f37ec599965))

- **problems**: Add go and rust references to edit-distance
  ([`b92e18b`](https://github.com/bkuberek/coding-study/commit/b92e18bd09b407cfe20883e1755b290649323473))

- **problems**: Add go and rust references to effective-dated-history
  ([`c8e822a`](https://github.com/bkuberek/coding-study/commit/c8e822a8d4a5be077d506a2d35c9696ccfd998f1))

- **problems**: Add go and rust references to elevator-system
  ([`65f6693`](https://github.com/bkuberek/coding-study/commit/65f66936404b3aa4c3ad029e1404a6a65df92a3d))

- **problems**: Add go and rust references to employee-free-time
  ([`abbda4e`](https://github.com/bkuberek/coding-study/commit/abbda4e9148353751c3f47feb1ef669cbb4b7358))

- **problems**: Add go and rust references to employee-importance
  ([`34ea347`](https://github.com/bkuberek/coding-study/commit/34ea347271d40a658ba505a3d7cff4b933662210))

- **problems**: Add go and rust references to encode-decode-strings
  ([`aad05bd`](https://github.com/bkuberek/coding-study/commit/aad05bde1bc8bf5a18f8b602cbab6a7a9eec5da0))

- **problems**: Add go and rust references to endorsement-replay
  ([`08dafb9`](https://github.com/bkuberek/coding-study/commit/08dafb908c81ecd05753ea50f53a283c1b2ee485))

- **problems**: Add go and rust references to evaluate-division
  ([`e6d13a5`](https://github.com/bkuberek/coding-study/commit/e6d13a5189a8fd7181255957b0a11dedae905c9c))

- **problems**: Add go and rust references to evaluate-rpn
  ([`6f68b2f`](https://github.com/bkuberek/coding-study/commit/6f68b2f1a3d5a11f696d8758b14eb8cf27172d5f))

- **problems**: Add go and rust references to event-bus
  ([`61c4c81`](https://github.com/bkuberek/coding-study/commit/61c4c81dbd3fa27197d7483622f9e781a8714689))

- **problems**: Add go and rust references to fast-power
  ([`c2833ae`](https://github.com/bkuberek/coding-study/commit/c2833aeee4c0cb0c31a3ceaf0fec0146cc07e05c))

- **problems**: Add go and rust references to find-peak-element
  ([`79af63f`](https://github.com/bkuberek/coding-study/commit/79af63ffcf84e2b48d9959988f86b7c7e4ea77d0))

- **problems**: Add go and rust references to first-last-position
  ([`c9812e5`](https://github.com/bkuberek/coding-study/commit/c9812e5b3beac5d90f893b2c0c6387fb53a37e7e))

- **problems**: Add go and rust references to first-missing-positive
  ([`f1f24c9`](https://github.com/bkuberek/coding-study/commit/f1f24c9f75f5ba85d2a5f1b3a912ea87f166624a))

- **problems**: Add go and rust references to fruit-into-baskets
  ([`6ce5330`](https://github.com/bkuberek/coding-study/commit/6ce53302dabb6ac7306187d9339bc8673bc5aa06))

- **problems**: Add go and rust references to gas-station
  ([`9e5c6d2`](https://github.com/bkuberek/coding-study/commit/9e5c6d229ae0708eee77b61b5196c90288a84299))

- **problems**: Add go and rust references to generate-parentheses
  ([`fcbfc3f`](https://github.com/bkuberek/coding-study/commit/fcbfc3f34ba6f7ffb4dc386bc2b47290d7473de1))

- **problems**: Add go and rust references to group-anagrams
  ([`1243d0c`](https://github.com/bkuberek/coding-study/commit/1243d0c1b9fb529e0ed8b1a29a6b6db8465a38c0))

- **problems**: Add go and rust references to hand-of-straights
  ([`7d0f277`](https://github.com/bkuberek/coding-study/commit/7d0f277e1033959a0236841de450248b176aafe1))

- **problems**: Add go and rust references to house-robber
  ([`a92b522`](https://github.com/bkuberek/coding-study/commit/a92b522af628863dda6e21f96b27bec158f7cb59))

- **problems**: Add go and rust references to implement-trie
  ([`a4ba3b7`](https://github.com/bkuberek/coding-study/commit/a4ba3b7e9589fb1e7c1abba4f1126b6514d552f7))

- **problems**: Add go and rust references to in-memory-database
  ([`a2cff54`](https://github.com/bkuberek/coding-study/commit/a2cff5448ff9f63d872f13ceaa284bf204f10a39))

- **problems**: Add go and rust references to insert-interval
  ([`f16d4ea`](https://github.com/bkuberek/coding-study/commit/f16d4eae5b3a99f644a9546c9e101b5829b19566))

- **problems**: Add go and rust references to installment-schedule
  ([`0740490`](https://github.com/bkuberek/coding-study/commit/0740490c3a3027902fcaa253a511aaeef704e3d6))

- **problems**: Add go and rust references to interleaving-string
  ([`44887e2`](https://github.com/bkuberek/coding-study/commit/44887e263d1f77663ccbe1a2bae59237e0edad89))

- **problems**: Add go and rust references to interval-list-intersections
  ([`621eb3a`](https://github.com/bkuberek/coding-study/commit/621eb3a55fecbb36ea8b93ff83f732cecbf14263))

- **problems**: Add go and rust references to job-scheduler
  ([`210e2b9`](https://github.com/bkuberek/coding-study/commit/210e2b958951e59e315b18e898bf59e01ab2b7d3))

- **problems**: Add go and rust references to job-scheduling-max-profit
  ([`75edbb6`](https://github.com/bkuberek/coding-study/commit/75edbb6a4ca64d7f5be5ef5d64209d784a9d60d7))

- **problems**: Add go and rust references to jump-game
  ([`3fa0be7`](https://github.com/bkuberek/coding-study/commit/3fa0be7f81a6ee8747d316df11c1b2b4bafb89ae))

- **problems**: Add go and rust references to k-closest-points
  ([`ef85ba2`](https://github.com/bkuberek/coding-study/commit/ef85ba2314d6a761faad1c00822867b10e5053be))

- **problems**: Add go and rust references to koko-eating-bananas
  ([`e7ab34a`](https://github.com/bkuberek/coding-study/commit/e7ab34ac1f308e50701b8425fa6ebb479f548be4))

- **problems**: Add go and rust references to kth-largest-element
  ([`5c97a8c`](https://github.com/bkuberek/coding-study/commit/5c97a8c18cd00e657e4b183a2c48a685ac82bd6e))

- **problems**: Add go and rust references to kth-smallest-in-bst
  ([`7200950`](https://github.com/bkuberek/coding-study/commit/7200950b7e6ba1a90f1e4095a649bc72080bcd22))

- **problems**: Add go and rust references to largest-rectangle-histogram
  ([`643f1e1`](https://github.com/bkuberek/coding-study/commit/643f1e16b1d6d610659361914edae69e27c1bedc))

- **problems**: Add go and rust references to last-stone-weight
  ([`73612e7`](https://github.com/bkuberek/coding-study/commit/73612e732d5888223b6e1589a4fcce3590ccd4f8))

- **problems**: Add go and rust references to level-order-traversal
  ([`4df61d8`](https://github.com/bkuberek/coding-study/commit/4df61d87b48effa2934f6c164c8de3e1a7bbfc8d))

- **problems**: Add go and rust references to library-management
  ([`1222195`](https://github.com/bkuberek/coding-study/commit/12221954a17b387a3a9c7d53869d38f0567f17c8))

- **problems**: Add go and rust references to longest-common-subsequence
  ([`f49db85`](https://github.com/bkuberek/coding-study/commit/f49db85252f083a5acd4236980f0438fc50ec397))

- **problems**: Add go and rust references to longest-consecutive-sequence
  ([`c6eafaf`](https://github.com/bkuberek/coding-study/commit/c6eafafc4d80d49fdaa413a18408df4cabf966fc))

- **problems**: Add go and rust references to longest-increasing-path-matrix
  ([`e045ed8`](https://github.com/bkuberek/coding-study/commit/e045ed8256ecb69f5d78a76ea8cca96877896b2e))

- **problems**: Add go and rust references to longest-increasing-subsequence
  ([`d27cb4c`](https://github.com/bkuberek/coding-study/commit/d27cb4c7b90ce4226c33796594cf127f75cdad45))

- **problems**: Add go and rust references to longest-palindromic-substring
  ([`3077847`](https://github.com/bkuberek/coding-study/commit/30778471f45b13b5191e97f4f0b6b1e151752576))

- **problems**: Add go and rust references to longest-repeating-replacement
  ([`e2ce149`](https://github.com/bkuberek/coding-study/commit/e2ce1498698981bd0650241510b9555e1a3b57fb))

- **problems**: Add go and rust references to longest-substring-without-repeats
  ([`48f474c`](https://github.com/bkuberek/coding-study/commit/48f474ced21508bc1495f62be17284291b38e6c5))

- **problems**: Add go and rust references to loss-ratio-by-period
  ([`2ee3fe9`](https://github.com/bkuberek/coding-study/commit/2ee3fe96febc0715c746b002c99779efe36a6dad))

- **problems**: Add go and rust references to lowest-common-ancestor
  ([`88be913`](https://github.com/bkuberek/coding-study/commit/88be9138235fa80ad66d7c4702ec04339609af24))

- **problems**: Add go and rust references to majority-element
  ([`7628f1b`](https://github.com/bkuberek/coding-study/commit/7628f1b86ef682d8f15ca795da57be0ee2ace00c))

- **problems**: Add go and rust references to max-area-of-island
  ([`47a6851`](https://github.com/bkuberek/coding-study/commit/47a6851ce6a4638cbd73f2bbf98e083e5b526bfc))

- **problems**: Add go and rust references to max-depth-binary-tree
  ([`c213587`](https://github.com/bkuberek/coding-study/commit/c2135879e50ab0bd53eaae7d25e646a84f017a05))

- **problems**: Add go and rust references to max-ones-with-flips
  ([`dba52f9`](https://github.com/bkuberek/coding-study/commit/dba52f96c46ebe69551826362c62e0909afe56a1))

- **problems**: Add go and rust references to max-path-sum
  ([`5ef40f9`](https://github.com/bkuberek/coding-study/commit/5ef40f96783c669848fe9748a160ddc5e127bc27))

- **problems**: Add go and rust references to max-points-on-line
  ([`37d314f`](https://github.com/bkuberek/coding-study/commit/37d314f47309a76e107448bf70591af4b06b91e3))

- **problems**: Add go and rust references to max-product-subarray
  ([`7bcf50c`](https://github.com/bkuberek/coding-study/commit/7bcf50c10317950be061f5cfb64966fab09c9bf2))

- **problems**: Add go and rust references to maximal-rectangle
  ([`86db8ad`](https://github.com/bkuberek/coding-study/commit/86db8ada86498a796f50b1edcb8cb3026c0f3271))

- **problems**: Add go and rust references to maximal-square
  ([`1d8114e`](https://github.com/bkuberek/coding-study/commit/1d8114eb3388a37b8631500085e1da8f8c70ba73))

- **problems**: Add go and rust references to maximize-capital
  ([`d5424c1`](https://github.com/bkuberek/coding-study/commit/d5424c1b8a71d07c5f235893e1a329316daf3fc8))

- **problems**: Add go and rust references to maximum-subarray
  ([`92947b3`](https://github.com/bkuberek/coding-study/commit/92947b3d6857addabd18cd9f0e253234bb4b77eb))

- **problems**: Add go and rust references to median-data-stream
  ([`9369b8a`](https://github.com/bkuberek/coding-study/commit/9369b8a48e2f97b52ce1712f8415c9c2069516c2))

- **problems**: Add go and rust references to median-of-two-sorted-arrays
  ([`8893684`](https://github.com/bkuberek/coding-study/commit/8893684217421a57b402a9bf33b9ac7f05e225f9))

- **problems**: Add go and rust references to merge-intervals
  ([`9a370cf`](https://github.com/bkuberek/coding-study/commit/9a370cf721ed3af144d9236f5daea983aeac0cba))

- **problems**: Add go and rust references to merge-k-sorted-lists
  ([`fba0693`](https://github.com/bkuberek/coding-study/commit/fba0693d92297289fee92929078cc5761495d736))

- **problems**: Add go and rust references to merge-two-sorted-lists
  ([`ce249a3`](https://github.com/bkuberek/coding-study/commit/ce249a3193468ac3588c5b24beb24e6547e59f38))

- **problems**: Add go and rust references to min-cost-connect-points
  ([`96f84d5`](https://github.com/bkuberek/coding-study/commit/96f84d54fed4e46e89548e8ad67fcf8db5086fc5))

- **problems**: Add go and rust references to min-cost-tickets
  ([`0cddd22`](https://github.com/bkuberek/coding-study/commit/0cddd22d4076dc6032758e24b08d1868e47dd5ed))

- **problems**: Add go and rust references to min-in-rotated-array
  ([`1aa5903`](https://github.com/bkuberek/coding-study/commit/1aa59038c927d0b4c7b66a344cfdf75aaf2ec958))

- **problems**: Add go and rust references to min-interval-per-query
  ([`23c28fa`](https://github.com/bkuberek/coding-study/commit/23c28faa7091296f7399b6c624d55729681f784f))

- **problems**: Add go and rust references to min-meeting-rooms
  ([`a05ccb2`](https://github.com/bkuberek/coding-study/commit/a05ccb254d6d8778f22aa6253d53e5a1e0fea533))

- **problems**: Add go and rust references to min-obstacle-removal
  ([`e0d6b2c`](https://github.com/bkuberek/coding-study/commit/e0d6b2c28ce8881e82146d0ecebca7794f2d9cac))

- **problems**: Add go and rust references to min-remove-to-balance
  ([`ef89919`](https://github.com/bkuberek/coding-study/commit/ef89919462fde140a214ba358202b85a6e4e4e09))

- **problems**: Add go and rust references to min-size-subarray-sum
  ([`69517ef`](https://github.com/bkuberek/coding-study/commit/69517ef004403e6368d974be3d69be8bc344af7d))

- **problems**: Add go and rust references to min-stack
  ([`579e9b4`](https://github.com/bkuberek/coding-study/commit/579e9b41f12058b87a3004d3572a3ac939a27a58))

- **problems**: Add go and rust references to minimum-window-substring
  ([`35b0f2f`](https://github.com/bkuberek/coding-study/commit/35b0f2fa6e042eaa67a8d6685ddbda4b4dc9ca3a))

- **problems**: Add go and rust references to missing-number
  ([`38c7bfc`](https://github.com/bkuberek/coding-study/commit/38c7bfcc09d5386d767d55cf4d7bf64720e1e0a4))

- **problems**: Add go and rust references to move-zeroes
  ([`222e835`](https://github.com/bkuberek/coding-study/commit/222e83531c02bd54e54b39a70b1494467e69211c))

- **problems**: Add go and rust references to multiply-strings
  ([`ae42091`](https://github.com/bkuberek/coding-study/commit/ae4209156e7aafb84b3a37be503588130bf2df48))

- **problems**: Add go and rust references to n-queens
  ([`c44cd7f`](https://github.com/bkuberek/coding-study/commit/c44cd7fd84999fa1b9379e4232e8439f452ef3b9))

- **problems**: Add go and rust references to network-delay-time
  ([`eb504a4`](https://github.com/bkuberek/coding-study/commit/eb504a445332aced744b69bdcc8d2f3189bd8925))

- **problems**: Add go and rust references to non-overlapping-intervals
  ([`5d56cc8`](https://github.com/bkuberek/coding-study/commit/5d56cc821eed2cfe160c56933f375d19ead992c4))

- **problems**: Add go and rust references to notification-service
  ([`6e974ef`](https://github.com/bkuberek/coding-study/commit/6e974eff1eece8954769e93d8f2468f909aa7f92))

- **problems**: Add go and rust references to number-of-islands
  ([`0f78067`](https://github.com/bkuberek/coding-study/commit/0f780673e57235450234064ca57ac4c16d1b8ef5))

- **problems**: Add go and rust references to number-of-islands-ii
  ([`05e65da`](https://github.com/bkuberek/coding-study/commit/05e65da9214cc2ce7f9f5ab6b6ae73ebcdf78501))

- **problems**: Add go and rust references to open-the-lock
  ([`ff014ec`](https://github.com/bkuberek/coding-study/commit/ff014ec75f634fc747648e543cc9f203556eced8))

- **problems**: Add go and rust references to pacific-atlantic-water-flow
  ([`77a65d7`](https://github.com/bkuberek/coding-study/commit/77a65d7fc4a4458fd511f4afb3aa4867f7428b15))

- **problems**: Add go and rust references to palindrome-partitioning
  ([`cff91de`](https://github.com/bkuberek/coding-study/commit/cff91dec17bd299cc8ba14a4daf6f9ed117609ed))

- **problems**: Add go and rust references to parallel-courses
  ([`c007608`](https://github.com/bkuberek/coding-study/commit/c007608f1afb9ad78060143d09a3b9d9fd559327))

- **problems**: Add go and rust references to parking-lot
  ([`654b258`](https://github.com/bkuberek/coding-study/commit/654b258ca08044b2e79d3049a512974f6c74b934))

- **problems**: Add go and rust references to partition-equal-subset-sum
  ([`1857050`](https://github.com/bkuberek/coding-study/commit/18570504c7cdc6c8e529021053513e0ddfeb22fe))

- **problems**: Add go and rust references to partition-labels
  ([`6fa7c27`](https://github.com/bkuberek/coding-study/commit/6fa7c27e913ca2fc030099df4f594ca71a33d3aa))

- **problems**: Add go and rust references to payroll-report-validation
  ([`07b099e`](https://github.com/bkuberek/coding-study/commit/07b099e5bfb4fcceed4ad316219c89b354a6152f))

- **problems**: Add go and rust references to permutation-in-string
  ([`b287ca2`](https://github.com/bkuberek/coding-study/commit/b287ca2972672b72ce5d9c2ff66a07ea12b9b7f2))

- **problems**: Add go and rust references to permutations
  ([`a3bf73d`](https://github.com/bkuberek/coding-study/commit/a3bf73dfce5824b13e2daa4f55466f4ca94d8674))

- **problems**: Add go and rust references to phone-letter-combinations
  ([`83b44d7`](https://github.com/bkuberek/coding-study/commit/83b44d73fea4ad79bb8175d0e34f99d665b4cc2d))

- **problems**: Add go and rust references to premium-rating-breakdown
  ([`7e76d60`](https://github.com/bkuberek/coding-study/commit/7e76d60d5ae62be26dcfdae1727d9acaed26cb9e))

- **problems**: Add go and rust references to pro-rata-unearned-premium
  ([`bc4171a`](https://github.com/bkuberek/coding-study/commit/bc4171ad5e0a7ea14cb2d266a67cf075e058e60a))

- **problems**: Add go and rust references to product-except-self
  ([`fc7a607`](https://github.com/bkuberek/coding-study/commit/fc7a6072d32ef197d4fd45d8818a529e67adfb41))

- **problems**: Add go and rust references to randomized-set
  ([`98b537b`](https://github.com/bkuberek/coding-study/commit/98b537b7f4d17e2d0084d5ee26cef3d29cc72c8b))

- **problems**: Add go and rust references to range-module
  ([`4d62ea2`](https://github.com/bkuberek/coding-study/commit/4d62ea26167384f3cbb7ac619a91d6149412d76f))

- **problems**: Add go and rust references to range-sum-2d
  ([`7416e91`](https://github.com/bkuberek/coding-study/commit/7416e911692aedd5ff96f5b2ac8392180bd6907a))

- **problems**: Add go and rust references to range-sum-immutable
  ([`dc7f134`](https://github.com/bkuberek/coding-study/commit/dc7f134935d14c9fda67301f79af7ff4b6ba8d9c))

- **problems**: Add go and rust references to range-sum-mutable
  ([`51cf1b1`](https://github.com/bkuberek/coding-study/commit/51cf1b16419aebaeb65258281eff2a6ebe5df81f))

- **problems**: Add go and rust references to rate-change-impact
  ([`c9428e9`](https://github.com/bkuberek/coding-study/commit/c9428e905df47df4052091151fdaaa767628b74f))

- **problems**: Add go and rust references to reconstruct-itinerary
  ([`0c1c566`](https://github.com/bkuberek/coding-study/commit/0c1c56677773c04adfe5d519a7a5fdcaf83301bb))

- **problems**: Add go and rust references to redundant-connection
  ([`da26859`](https://github.com/bkuberek/coding-study/commit/da2685999622dc3cc00d82fb9e8eed6ff4dbd314))

- **problems**: Add go and rust references to regex-matching
  ([`cefb74b`](https://github.com/bkuberek/coding-study/commit/cefb74b5f4495dff67cf96b143e7aba9f1214b61))

- **problems**: Add go and rust references to remove-covered-intervals
  ([`e398d39`](https://github.com/bkuberek/coding-study/commit/e398d39010ac8e999b996834618dee2efd6ca250))

- **problems**: Add go and rust references to remove-k-digits
  ([`9ea664e`](https://github.com/bkuberek/coding-study/commit/9ea664ebd4f795dd9553db3c81300ebb3934690f))

- **problems**: Add go and rust references to remove-nth-from-end
  ([`7a6212a`](https://github.com/bkuberek/coding-study/commit/7a6212a09a58d9696506ff8114a2f43c4f9891ff))

- **problems**: Add go and rust references to reorder-list
  ([`1c058bb`](https://github.com/bkuberek/coding-study/commit/1c058bb49a75fc5ad69d618165e24f5a8f91a1f6))

- **problems**: Add go and rust references to replace-words
  ([`60caf2f`](https://github.com/bkuberek/coding-study/commit/60caf2ff19d918e6f0ba81bd617f73d49dfe0b00))

- **problems**: Add go and rust references to reverse-linked-list
  ([`268587b`](https://github.com/bkuberek/coding-study/commit/268587b13e7463163a40b9811798d0a746dec7ac))

- **problems**: Add go and rust references to reverse-nodes-in-k-group
  ([`5439c43`](https://github.com/bkuberek/coding-study/commit/5439c438cf25ca81769a6953220a6edaa9bf893e))

- **problems**: Add go and rust references to right-side-view
  ([`4e9ba2d`](https://github.com/bkuberek/coding-study/commit/4e9ba2d87b4265dfdac65427b990c5b28f097278))

- **problems**: Add go and rust references to rotate-image
  ([`776811e`](https://github.com/bkuberek/coding-study/commit/776811eff6dcb1634e07900e38b6d35e47088868))

- **problems**: Add go and rust references to rotting-oranges
  ([`dea35d5`](https://github.com/bkuberek/coding-study/commit/dea35d5973919c090db22bfcfad50dee3d50f288))

- **problems**: Add go and rust references to same-tree
  ([`82697ea`](https://github.com/bkuberek/coding-study/commit/82697ea0512c198536a19cd66799d998ea80040f))

- **problems**: Add go and rust references to search-2d-matrix
  ([`d5d2689`](https://github.com/bkuberek/coding-study/commit/d5d26890d9f9b7b68ac28dc1346d7f83c2f7eecc))

- **problems**: Add go and rust references to search-insert-position
  ([`1ecbfb9`](https://github.com/bkuberek/coding-study/commit/1ecbfb9c1f3bbc159a7a2ebd4de96548f80766e3))

- **problems**: Add go and rust references to search-rotated-array
  ([`ebda6e4`](https://github.com/bkuberek/coding-study/commit/ebda6e4cf22ad876346929bac54586520331de30))

- **problems**: Add go and rust references to search-suggestions
  ([`5419d3a`](https://github.com/bkuberek/coding-study/commit/5419d3aa79a8c761dd0f288020b373403700406a))

- **problems**: Add go and rust references to serialize-binary-tree
  ([`757409d`](https://github.com/bkuberek/coding-study/commit/757409d9c69053d2e8229a819b645d5e9c2de4ed))

- **problems**: Add go and rust references to set-matrix-zeroes
  ([`8a1ebb3`](https://github.com/bkuberek/coding-study/commit/8a1ebb3fb7807fd9bd84a6b7ff223b4a2060da95))

- **problems**: Add go and rust references to shortest-path-binary-matrix
  ([`5a2e9a7`](https://github.com/bkuberek/coding-study/commit/5a2e9a7de84ddaf6c81bae10fe778c62fd5a3600))

- **problems**: Add go and rust references to shortest-path-with-removals
  ([`8698a27`](https://github.com/bkuberek/coding-study/commit/8698a273d531921312e7fe722b53245a7ecf2e98))

- **problems**: Add go and rust references to single-number
  ([`724f225`](https://github.com/bkuberek/coding-study/commit/724f22553b4656f72b93998b58f313185c8673d2))

- **problems**: Add go and rust references to single-threaded-cpu
  ([`45f352c`](https://github.com/bkuberek/coding-study/commit/45f352ccd419cd1223f3194d014db1323e024ecc))

- **problems**: Add go and rust references to sliding-window-maximum
  ([`ee1044e`](https://github.com/bkuberek/coding-study/commit/ee1044e38af907d7ae777af3a1aebd2495e772d2))

- **problems**: Add go and rust references to smallest-string-with-swaps
  ([`55befbb`](https://github.com/bkuberek/coding-study/commit/55befbbf6db38a2f4d63eb41ce1b4191eda71832))

- **problems**: Add go and rust references to snapshot-array
  ([`7a0800e`](https://github.com/bkuberek/coding-study/commit/7a0800ecc327a8929886d19335eb5be50a8b53fe))

- **problems**: Add go and rust references to sort-colors
  ([`6336a33`](https://github.com/bkuberek/coding-study/commit/6336a3318cb9597010d85e02d94f1e4f0d11f0c2))

- **problems**: Add go and rust references to sort-linked-list
  ([`248bf6f`](https://github.com/bkuberek/coding-study/commit/248bf6f31d6f2264dc516e0f5a5a77110f21775a))

- **problems**: Add go and rust references to sorted-insertion-cost
  ([`bb6f4bb`](https://github.com/bkuberek/coding-study/commit/bb6f4bbca3fe7808bb694b3ab1dc153f5bce3e13))

- **problems**: Add go and rust references to spiral-matrix
  ([`22c9c9c`](https://github.com/bkuberek/coding-study/commit/22c9c9c89b008387637a18b5eebac949480faa42))

- **problems**: Add go and rust references to split-array-largest-sum
  ([`46843b7`](https://github.com/bkuberek/coding-study/commit/46843b772dceacf6de3ca3eb069422b1bbcd29da))

- **problems**: Add go and rust references to stock-span
  ([`8978157`](https://github.com/bkuberek/coding-study/commit/8978157d1feaaae343dec12b991fc91f390fac4c))

- **problems**: Add go and rust references to stock-with-cooldown
  ([`63b69e1`](https://github.com/bkuberek/coding-study/commit/63b69e1191d10f7eb5820cd86466324f80de784b))

- **problems**: Add go and rust references to subarray-sum-equals-k
  ([`93e1262`](https://github.com/bkuberek/coding-study/commit/93e12620dcdb7ca3d2ef0d305e75ab5771f9cb12))

- **problems**: Add go and rust references to subsets
  ([`972a2bc`](https://github.com/bkuberek/coding-study/commit/972a2bcce1b82bba395acdd86042a28d8ebdcbdd))

- **problems**: Add go and rust references to subsets-with-duplicates
  ([`ab36087`](https://github.com/bkuberek/coding-study/commit/ab3608781fb6ab45282a23a1451fa6525d00f06b))

- **problems**: Add go and rust references to subtree-of-another-tree
  ([`50ee858`](https://github.com/bkuberek/coding-study/commit/50ee858980ff84b6e2c19b0d3aaa5237da31caa7))

- **problems**: Add go and rust references to sum-of-subarray-minimums
  ([`e4ec921`](https://github.com/bkuberek/coding-study/commit/e4ec9217b6caf9dcc56ba96f812c67b16b9b13f8))

- **problems**: Add go and rust references to sum-without-plus
  ([`592fe8f`](https://github.com/bkuberek/coding-study/commit/592fe8fd29fff3fdca32978c240e690394e0061e))

- **problems**: Add go and rust references to surrounded-regions
  ([`6270f33`](https://github.com/bkuberek/coding-study/commit/6270f3326320517af3d4b1b7768c432c274e0211))

- **problems**: Add go and rust references to swim-rising-water
  ([`2d31aea`](https://github.com/bkuberek/coding-study/commit/2d31aea206ea4f6a8472a255206e08076689575d))

- **problems**: Add go and rust references to target-sum
  ([`95ed808`](https://github.com/bkuberek/coding-study/commit/95ed8080089ba5ed512c23d03733cbb876ab491e))

- **problems**: Add go and rust references to task-scheduler
  ([`42beaae`](https://github.com/bkuberek/coding-study/commit/42beaae7ed99317d965acdd9749a38e208c35838))

- **problems**: Add go and rust references to tax-brackets
  ([`bec2a63`](https://github.com/bkuberek/coding-study/commit/bec2a63d28df08eb19c53f4de340850ea9930165))

- **problems**: Add go and rust references to three-sum
  ([`d2c78c7`](https://github.com/bkuberek/coding-study/commit/d2c78c7af7e86cb4b45b6f28d8a50305fc69d2fd))

- **problems**: Add go and rust references to tiered-bond-premium
  ([`a06ca06`](https://github.com/bkuberek/coding-study/commit/a06ca0697a242440549c1c57e0dc7b790cdbf1d3))

- **problems**: Add go and rust references to time-based-kv-store
  ([`ed406c2`](https://github.com/bkuberek/coding-study/commit/ed406c251cd1892a7e93748ec6f028545079fe12))

- **problems**: Add go and rust references to time-to-inform-employees
  ([`36ff3ce`](https://github.com/bkuberek/coding-study/commit/36ff3ce8875c9c0b91f07c74acd60f54bc8a8c1d))

- **problems**: Add go and rust references to top-k-frequent-elements
  ([`f0d3a5c`](https://github.com/bkuberek/coding-study/commit/f0d3a5c238e625068b69d40a2ffc0508b957d000))

- **problems**: Add go and rust references to transactional-kv-store
  ([`c51400c`](https://github.com/bkuberek/coding-study/commit/c51400c309ecc214e09b743d1b4c40431a0a500e))

- **problems**: Add go and rust references to trapping-rain-water
  ([`248f5e3`](https://github.com/bkuberek/coding-study/commit/248f5e3887e90440d72058068436c0cdce791e0d))

- **problems**: Add go and rust references to tree-from-preorder-inorder
  ([`dcbddc9`](https://github.com/bkuberek/coding-study/commit/dcbddc90a8e7725245e4725e0391ca78b2fba8f8))

- **problems**: Add go and rust references to tree-path-sum-count
  ([`98fe9a2`](https://github.com/bkuberek/coding-study/commit/98fe9a2669d8978a89f1afcf083e3017c64e664d))

- **problems**: Add go and rust references to two-sum-sorted
  ([`da6b295`](https://github.com/bkuberek/coding-study/commit/da6b295a0617e48a7b44e96045786cf672a6af5a))

- **problems**: Add go and rust references to unique-paths
  ([`db331e2`](https://github.com/bkuberek/coding-study/commit/db331e286afd8ee0f8e4b0bd4e65a048f50e8877))

- **problems**: Add go and rust references to valid-anagram
  ([`bad4725`](https://github.com/bkuberek/coding-study/commit/bad4725d7e8211a7f1d6887ccc28c4480c31fc6b))

- **problems**: Add go and rust references to valid-palindrome
  ([`e701194`](https://github.com/bkuberek/coding-study/commit/e701194e867c3bf3d19cc3674721b778dfc00d3f))

- **problems**: Add go and rust references to valid-parentheses
  ([`57810cc`](https://github.com/bkuberek/coding-study/commit/57810cc2510a4e982b65b4f7877a905c618986a9))

- **problems**: Add go and rust references to valid-parenthesis-string
  ([`5b96667`](https://github.com/bkuberek/coding-study/commit/5b96667778516d1170679f3a08cac6a8fe23fcc8))

- **problems**: Add go and rust references to valid-sudoku
  ([`556f85e`](https://github.com/bkuberek/coding-study/commit/556f85e333bf975b1a77400236d949f5a94f21ab))

- **problems**: Add go and rust references to validate-bst
  ([`a7ded6d`](https://github.com/bkuberek/coding-study/commit/a7ded6d5e89a2da3c833f25ddafbfe37911b8d21))

- **problems**: Add go and rust references to vending-machine
  ([`f9af02c`](https://github.com/bkuberek/coding-study/commit/f9af02c66e3b44866abc2cb75242ab2af2203390))

- **problems**: Add go and rust references to versioned-rate-table
  ([`d11543f`](https://github.com/bkuberek/coding-study/commit/d11543f1cc99ea2de0610e90ed9ab51101b0136e))

- **problems**: Add go and rust references to vertical-order-traversal
  ([`4ec7ee7`](https://github.com/bkuberek/coding-study/commit/4ec7ee7173e0c8cff7577be03e92665fe2d4ce6d))

- **problems**: Add go and rust references to wildcard-word-dictionary
  ([`739a4b8`](https://github.com/bkuberek/coding-study/commit/739a4b8698fecbb92449f444869c673fd3a85be6))

- **problems**: Add go and rust references to word-break
  ([`5ad98b1`](https://github.com/bkuberek/coding-study/commit/5ad98b1a3db48c9fa34994955d9c14f871388032))

- **problems**: Add go and rust references to word-ladder
  ([`8639368`](https://github.com/bkuberek/coding-study/commit/8639368c4084be3f084d0837e7791b29181367b8))

- **problems**: Add go and rust references to word-search
  ([`2b36baf`](https://github.com/bkuberek/coding-study/commit/2b36baf71e87098347ea7406eab481d7704cf33c))

- **problems**: Add go and rust references to word-search-ii
  ([`82cd46c`](https://github.com/bkuberek/coding-study/commit/82cd46c9dac357a1f726cb448d46475474b6672a))

- **problems**: Add go and rust to bank-transfers
  ([`a29b28a`](https://github.com/bkuberek/coding-study/commit/a29b28a8b5e61da8248eadbd3dcce8f9a64e7cc3))

- **problems**: Add go and rust to bounded-blocking-queue
  ([`bece4aa`](https://github.com/bkuberek/coding-study/commit/bece4aac8bc9ddf4fab38406a1ade3058a814add))

- **problems**: Add go and rust to concurrency-limiter
  ([`5b71a8f`](https://github.com/bkuberek/coding-study/commit/5b71a8f26fe06f6459ee79ccea424c46c7343821))

- **problems**: Add go and rust to read-write-lock
  ([`b75fa4d`](https://github.com/bkuberek/coding-study/commit/b75fa4d8e35e93d0b31c5cf21c63888344152aaa))

- **problems**: Add go and rust to thread-safe-lru-cache
  ([`9fe835e`](https://github.com/bkuberek/coding-study/commit/9fe835e5d74a40bad31cadf929e5549b79c30d3b))

- **problems**: Add go and rust to token-bucket-limiter
  ([`1e633e9`](https://github.com/bkuberek/coding-study/commit/1e633e9d3744d02134b50c60e413d55f83ad013a))

- **problems**: Add go references to 0001 two sum
  ([`f8532d1`](https://github.com/bkuberek/coding-study/commit/f8532d1f2bd6a05f981ee8a14436b181fbac1e94))

- **problems**: Add go references to 0002 lru cache
  ([`39ea4d6`](https://github.com/bkuberek/coding-study/commit/39ea4d613db9220189bf209e95d7021224c87763))

- **problems**: Add go references to 0003 invert binary tree
  ([`9665e52`](https://github.com/bkuberek/coding-study/commit/9665e523a3d25a076273c095437244d53d7647be))

- **problems**: Add go references to chess-move-validator
  ([`75b6619`](https://github.com/bkuberek/coding-study/commit/75b6619cdff2f536ac98db15142ff62e88819d2e))

- **problems**: Add go references to linked-list-cycle
  ([`105f0a4`](https://github.com/bkuberek/coding-study/commit/105f0a4229e15528464a8d76ac6cab8e95e47468))

- **problems**: Add rust references to 0001 two sum
  ([`6d566f4`](https://github.com/bkuberek/coding-study/commit/6d566f4277fb17fbef5502cc9acfa8f8afcb7dc3))

- **problems**: Add rust references to 0002 lru cache
  ([`8397f44`](https://github.com/bkuberek/coding-study/commit/8397f442c5836fa37e6c08ee9f4021345145e987))

- **problems**: Add rust references to 0003 invert binary tree
  ([`8cc7f49`](https://github.com/bkuberek/coding-study/commit/8cc7f4943b4a82501d81aafe34d0df196ae89e9e))

- **problems**: Add rust references to chess-move-validator
  ([`d7f0912`](https://github.com/bkuberek/coding-study/commit/d7f091242bf5911ae978343344058ea7e4a58ff0))

- **runners**: Add the go runner
  ([`7b38c81`](https://github.com/bkuberek/coding-study/commit/7b38c81da5fe0eb0a17a2513846d2fbb81add74d))

- **runners**: Add the rust runner
  ([`70f2e2d`](https://github.com/bkuberek/coding-study/commit/70f2e2dfd566c8ad80a0db42874ac24aac632d88))

- **rust**: Run concurrent stress jobs
  ([`eb58666`](https://github.com/bkuberek/coding-study/commit/eb58666ab7e98b243f458542c8dfcb7a63c712ee))

- **rust**: Support decimal and date with vendored rust_decimal and chrono
  ([`f587b3f`](https://github.com/bkuberek/coding-study/commit/f587b3fa846a4fc8e2bb9ebed1cf624def5c4d24))

- **schemas**: Accept go and rust in languages
  ([`f152c4f`](https://github.com/bkuberek/coding-study/commit/f152c4f44f3a30d70f5069f05920edf62925e9e3))

- **stubs**: Generate go stubs
  ([`ea1b395`](https://github.com/bkuberek/coding-study/commit/ea1b3952f1d8b6d445a6c62599d2910622e6271f))

- **stubs**: Generate rust stubs
  ([`13651d1`](https://github.com/bkuberek/coding-study/commit/13651d1a92677d033294aba96635f8ec9eaf5911))

- **verify**: Check go and rust names against the decimal and date imports
  ([`9449149`](https://github.com/bkuberek/coding-study/commit/944914962f89da315333c4d7049ec05ca29e90c1))

- **workspace**: Add the go project
  ([`4fd4511`](https://github.com/bkuberek/coding-study/commit/4fd45115f96cce3e30628db6f57e94d76cc435e3))

- **workspace**: Add the rust project
  ([`2a2e24b`](https://github.com/bkuberek/coding-study/commit/2a2e24bafb466519dfb36dec2dc90cb1fe73008a))

### Performance Improvements

- **go**: Call design-problem methods through generated typed thunks
  ([`8c299f0`](https://github.com/bkuberek/coding-study/commit/8c299f04781778e09170b5c150166c410077d78f))

### Refactoring

- **layout**: Make language matches exhaustive
  ([`cee7a5b`](https://github.com/bkuberek/coding-study/commit/cee7a5b4871c71dba321ddb4183dca48c5e1033a))

- **problems**: Drop languages lists equal to the default
  ([`c2ddf60`](https://github.com/bkuberek/coding-study/commit/c2ddf60283cec06f9c2e55d33ae219e56fd55792))

- **runners**: Take the Go and Rust build lock from file_lock
  ([`bccce00`](https://github.com/bkuberek/coding-study/commit/bccce00554f86b90a695450ae3cd2d7e0183c7a0))

### Testing

- Use the go and rust projects every test workspace now has
  ([`49f7e7b`](https://github.com/bkuberek/coding-study/commit/49f7e7b0323c884834d966e38b4bea9df7a5345f))

- **conformance**: Move the decimal and date round trips to their own fixture
  ([`c58348b`](https://github.com/bkuberek/coding-study/commit/c58348b2459d8974976c0a6ca14231122c02a5f4))

- **conformance**: Run fixtures 9001 to 9013 in go
  ([`1eac258`](https://github.com/bkuberek/coding-study/commit/1eac258d2b7e8c878776b5654012f0f68bd9fc02))

- **conformance**: Run fixtures in rust
  ([`40c7b72`](https://github.com/bkuberek/coding-study/commit/40c7b727727b6870f3a84bae3012ea0f9e3351a4))

- **progress**: Sort migration scripts by name
  ([`ce8a0d2`](https://github.com/bkuberek/coding-study/commit/ce8a0d2637bc4a42053a11744c07f8b8b1aa1275))

- **runners**: Order the go fixture's decimal setting writes
  ([`deb400c`](https://github.com/bkuberek/coding-study/commit/deb400cd6443ac18ba8b8ec35b68d38b726aa245))


## v0.5.0 (2026-10-29)

### Bug Fixes

- **jvm**: Lock the shared build and run from a private class copy
  ([`b3712e9`](https://github.com/bkuberek/coding-study/commit/b3712e9966e62f579acaca90c90f9ddbb0af894d))

### Documentation

- **install**: Explain trusting the Homebrew tap
  ([`103e158`](https://github.com/bkuberek/coding-study/commit/103e15879f3767d888dd1cf205c3e4a7ce85504e))

- **runners**: Document the JVM build lock and the per-run class copy
  ([`fbfb5ba`](https://github.com/bkuberek/coding-study/commit/fbfb5ba2ab4e065ee040488a1d7d81b8b197329b))

### Features

- **runners**: Remove a launch's scratch directory when the run ends
  ([`635beb2`](https://github.com/bkuberek/coding-study/commit/635beb2aaf2a432a4255ff9b3e797dd55c16d843))


## v0.4.1 (2026-10-29)

### Bug Fixes

- **doctor**: Link each toolchain fix to its install guide
  ([`23ceb49`](https://github.com/bkuberek/coding-study/commit/23ceb496a7782c532ff09e178f23ae67a698e53c))

### Continuous Integration

- **release**: Publish each release to GitHub and the Homebrew tap
  ([`c56038e`](https://github.com/bkuberek/coding-study/commit/c56038efe6b6c64d02fcd1a0a308d3db164b4712))

### Documentation

- **install**: Install with Homebrew and a toolchains guide
  ([`539aefb`](https://github.com/bkuberek/coding-study/commit/539aefb002d087e8d7eab4b9981d402cc8396ca1))


## v0.4.0 (2026-10-29)

### Bug Fixes

- **problems**: Treat year 0000 as an invalid date in 0226 payroll-report-validation
  ([`ae217f5`](https://github.com/bkuberek/coding-study/commit/ae217f5df9eea9533203cfc898b5b303cf5e0f17))

### Features

- **problems**: Add 0219 installment-schedule
  ([`7988091`](https://github.com/bkuberek/coding-study/commit/7988091c1f878db3cf3fcb8e53156e7c2ffb8bf7))

- **problems**: Add 0220 tiered-bond-premium
  ([`94f8915`](https://github.com/bkuberek/coding-study/commit/94f8915bd16347d0e3fdac9e9674a8d644abdc53))

- **problems**: Add 0221 earned-premium-as-of
  ([`2230980`](https://github.com/bkuberek/coding-study/commit/2230980496c8c2d9102741124ed8c5ee5f26bf23))

- **problems**: Add 0222 endorsement-replay
  ([`eeeb544`](https://github.com/bkuberek/coding-study/commit/eeeb544ce2479efb39da19ddf9afff1a10f44f40))

- **problems**: Add 0223 certificate-expiry-alerts
  ([`ba3ba43`](https://github.com/bkuberek/coding-study/commit/ba3ba43762990c36e7d67a9533335d83709267f9))

- **problems**: Add 0224 loss-ratio-by-period
  ([`836786e`](https://github.com/bkuberek/coding-study/commit/836786e0e96814ce50dedacbc663d77d8a77abae))

- **problems**: Add 0225 rate-change-impact
  ([`87a237b`](https://github.com/bkuberek/coding-study/commit/87a237b5540bd43b1fe42a8cb2646349bb2556a6))

- **problems**: Add 0226 payroll-report-validation
  ([`6401c09`](https://github.com/bkuberek/coding-study/commit/6401c09d81547ac60f3e5b104eae46c73430c83d))

- **problems**: Add 0227 duplicate-contractor-records
  ([`9d98b0e`](https://github.com/bkuberek/coding-study/commit/9d98b0ea4781ece6e4ec9a9f8d8835f5f5e372df))

- **problems**: Add 0228 effective-dated-history
  ([`a5a13ca`](https://github.com/bkuberek/coding-study/commit/a5a13cae0cddbe6d6580014ee1744603b574a31f))

- **problems**: Add 0229 can-attend-meetings
  ([`3153dfb`](https://github.com/bkuberek/coding-study/commit/3153dfb24a65c9616a5b0a489970b056361200ee))

- **problems**: Add 0230 employee-free-time
  ([`4344f13`](https://github.com/bkuberek/coding-study/commit/4344f134931c59101a07d39baf6fd22587f397b4))

- **problems**: Add 0231 remove-covered-intervals
  ([`6523b3b`](https://github.com/bkuberek/coding-study/commit/6523b3b75ee2baca91728be01ca61f849e84586d))

- **problems**: Add 0232 snapshot-array
  ([`a27a8a6`](https://github.com/bkuberek/coding-study/commit/a27a8a664c9a15447269cd34ea7c3292dec27aa5))

- **problems**: Add 0233 employee-importance
  ([`f263d50`](https://github.com/bkuberek/coding-study/commit/f263d506b6e1cc2d755e2eef116e025ba602509e))

- **problems**: Add 0234 course-schedule-ii
  ([`d2644fa`](https://github.com/bkuberek/coding-study/commit/d2644fa6a45be1e689e5b5aacf95d3ac4fa5853b))

- **problems**: Add 0235 time-to-inform-employees
  ([`7364e53`](https://github.com/bkuberek/coding-study/commit/7364e531218ca73c58f1218571441315d1e485b7))

- **problems**: Add 0236 search-insert-position
  ([`4205cdb`](https://github.com/bkuberek/coding-study/commit/4205cdb3ac45614e5c39733d502b0e53e1cc1a04))

- **problems**: Add 0237 tax-brackets
  ([`8e78293`](https://github.com/bkuberek/coding-study/commit/8e782934487269929679cdb3d5e7e7c5afce3579))

- **problems**: Add 0238 replace-words
  ([`baea147`](https://github.com/bkuberek/coding-study/commit/baea1474912d1d0a23781aa5c9d7cf1a24afc4b3))

- **problems**: Add 0239 sorted-insertion-cost
  ([`9d22421`](https://github.com/bkuberek/coding-study/commit/9d224214eef9420f536f756f923e70e82cf4c9d9))

### Refactoring

- **stubs**: Reuse the domain type helpers in the Python and JVM stub generators
  ([`164e81d`](https://github.com/bkuberek/coding-study/commit/164e81d25165c81be03ca8e810b4e370063e2725))


## v0.3.0 (2026-10-28)

### Documentation

- **adr**: 0011 decimal and date types
  ([`4d79892`](https://github.com/bkuberek/coding-study/commit/4d798924d5d69a9a008054715f27659be3287afb))

- **problems**: Drop the quoted-strings notes from the 0214-0218 statements
  ([`996565d`](https://github.com/bkuberek/coding-study/commit/996565d5c4ad0ab167b4ff0f3074280ccd387b0f))

### Features

- **dsl**: Add decimal and date scalar types
  ([`6cb2c91`](https://github.com/bkuberek/coding-study/commit/6cb2c91c3782f466e8d84ccc9d12aabab0660275))

- **problems**: Add 0214 premium-rating-breakdown
  ([`3f52ba2`](https://github.com/bkuberek/coding-study/commit/3f52ba2f096c45b95eb4843fb5f2dc51d8b3152b))

- **problems**: Add 0215 versioned-rate-table
  ([`851adac`](https://github.com/bkuberek/coding-study/commit/851adacae209e89d90590d89e76cbbb4b98f38d9))

- **problems**: Add 0216 pro-rata-unearned-premium
  ([`28e9f4d`](https://github.com/bkuberek/coding-study/commit/28e9f4d900ed2967538fcb652e50cd91caabb2cc))

- **problems**: Add 0217 coverage-gaps
  ([`f954195`](https://github.com/bkuberek/coding-study/commit/f95419533cb28fcc2ae6c5d65d67c8dcf610e4c1))

- **problems**: Add 0218 contractor-exposure-rollup
  ([`75a3f91`](https://github.com/bkuberek/coding-study/commit/75a3f91d42c9fc38b2c3e9d3689cb9f681838449))

- **runners**: Decode and encode decimal and date
  ([`517dc86`](https://github.com/bkuberek/coding-study/commit/517dc869636281607e92ee84459e5845a86ef31f))

- **runners**: Move the point and round in every mode in the TypeScript Decimal
  ([`d558071`](https://github.com/bkuberek/coding-study/commit/d558071499a2ed52325173f45c204bd89df1b967))

- **statement**: Show decimal and date example values unquoted
  ([`b710e57`](https://github.com/bkuberek/coding-study/commit/b710e575624dba29d1dff6a8162eec6cd5faf747))

- **stubs**: Map decimal and date in all four languages
  ([`d796407`](https://github.com/bkuberek/coding-study/commit/d796407929d1741bac647b42b97fd5af043736b3))

- **stubs**: Type TypeScript dates as IsoDate from #support
  ([`d8698ce`](https://github.com/bkuberek/coding-study/commit/d8698ce3688c079ee6de092708075d4755c00093))

- **verify**: Reject the float comparator where only decimals are compared
  ([`c15a230`](https://github.com/bkuberek/coding-study/commit/c15a2302f9a487537066fda3c81a93aa495c364c))

- **verify**: Warn when a Python name shadows the imported date or Decimal
  ([`1a696a0`](https://github.com/bkuberek/coding-study/commit/1a696a0a53210ccfac556b46c6c92c10767fe8aa))

### Refactoring

- **problems**: Declare dates as IsoDate in the 0215-0217 TypeScript references
  ([`f716c62`](https://github.com/bkuberek/coding-study/commit/f716c62dade07426ff24b6f5a98e96f305e74ce3))

- **problems**: Divide by 1000 with movePointLeft in the 0214 TypeScript reference
  ([`4b44f74`](https://github.com/bkuberek/coding-study/commit/4b44f749bf68b0aafadb578a9df7cdf7861ea190))


## v0.2.0 (2026-10-26)

### Build System

- **ide**: Add the IntelliJ open-file launcher
  ([`c732828`](https://github.com/bkuberek/coding-study/commit/c732828fcd8e5375979297753d52b6d190f8f7bc))

- **workspace**: Add debugpy to the python template
  ([`f270ddd`](https://github.com/bkuberek/coding-study/commit/f270ddd1dee960b0ea4312ad40cecb15c809e267))

### Features

- **cli**: Accept solution file paths as command targets
  ([`3ff7566`](https://github.com/bkuberek/coding-study/commit/3ff7566649bcee475403d52d54f04eb10f7817c9))

- **cli**: Add test --debug to attach an IDE debugger to the runner
  ([`c4e7271`](https://github.com/bkuberek/coding-study/commit/c4e72714c515b1fcf170cd977227e6e8c901af49))

- **cli**: Ask for a solution file when the target is a directory
  ([`e1b666e`](https://github.com/bkuberek/coding-study/commit/e1b666e86b17efbf6ed92398faeb55005e3cf5d6))

- **ide**: Generate VS Code and IntelliJ project files in workspaces
  ([`6003172`](https://github.com/bkuberek/coding-study/commit/6003172da0512c2dcbcd4d3c8069db8ff2d08333))

### Refactoring

- **ide**: Parse debug command lines and share debug ports after merge
  ([`5f081de`](https://github.com/bkuberek/coding-study/commit/5f081de1585c0a4ddae0d635ca830b4d8a771aad))

- **ide**: Use the shared debug host in VS Code launch configs
  ([`d6ce82b`](https://github.com/bkuberek/coding-study/commit/d6ce82b8483f14023df3d9bbb8a58c027ed55959))

### Testing

- **ide**: Pin user.home so the launcher tests ignore an installed cstudy
  ([`0b325f4`](https://github.com/bkuberek/coding-study/commit/0b325f4bbc7835c80bef501700512a5eec337dab))


## v0.1.0 (2026-10-26)

- Initial Release
