# CHANGELOG

<!-- version list -->

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
