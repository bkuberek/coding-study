# CHANGELOG

<!-- version list -->

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
