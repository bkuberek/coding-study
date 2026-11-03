/**
 * The code-intelligence chunk (docs/specs/web-ui.md#front-end-assets): `@codemirror/lsp-client`
 * and the page's sessions over it. The page imports it dynamically, only while the
 * `code_intelligence` preference is on and a file of a language with an installed server opens,
 * after the editor is editable, so NFR-12's budget before the first editable file is unchanged.
 */

export { type Attachment, type AttachRequest, codeIntelligence, type PageHooks } from "./code-intelligence/manager.ts";
export { type LibraryFile, type Navigator } from "./code-intelligence/definition.ts";
export { libraryNavigation } from "./code-intelligence/extension.ts";
