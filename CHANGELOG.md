# CHANGELOG

<!-- version list -->

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
