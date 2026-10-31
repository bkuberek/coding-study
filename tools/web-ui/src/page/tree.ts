/** An attempt's files as nested folders for the file tree (docs/specs/web-ui.md#file-scope). */

export interface FolderNode<File> {
  readonly kind: "folder";
  readonly name: string;
  readonly path: string;
  readonly children: readonly TreeNode<File>[];
}

export interface FileNode<File> {
  readonly kind: "file";
  readonly name: string;
  readonly path: string;
  readonly file: File;
}

export type TreeNode<File> = FolderNode<File> | FileNode<File>;

interface Building<File> {
  readonly folders: Map<string, Building<File>>;
  readonly files: FileNode<File>[];
}

/** The files by folder: in each folder its folders first, then its files, each by name. */
export function fileTree<File extends { readonly path: string }>(files: readonly File[]): TreeNode<File>[] {
  const root: Building<File> = { folders: new Map(), files: [] };
  for (const file of files) {
    const segments = file.path.split("/");
    const name = segments.pop() ?? file.path;
    let folder = root;
    for (const segment of segments) {
      let next = folder.folders.get(segment);
      if (next === undefined) {
        next = { folders: new Map(), files: [] };
        folder.folders.set(segment, next);
      }
      folder = next;
    }
    folder.files.push({ kind: "file", name, path: file.path, file });
  }
  return nodes(root, "");
}

function nodes<File>(folder: Building<File>, prefix: string): TreeNode<File>[] {
  const folders = [...folder.folders.entries()]
    .sort(([a], [b]) => byName(a, b))
    .map(([name, child]): FolderNode<File> => {
      const path = `${prefix}${name}`;
      return { kind: "folder", name, path, children: nodes(child, `${path}/`) };
    });
  const files = [...folder.files].sort((a, b) => byName(a.name, b.name));
  return [...folders, ...files];
}

function byName(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}
