import { TreeNode } from "#support";

const MISSING = "#";
const SEPARATOR = ",";

export function serializeDeserialize(root: TreeNode | null): TreeNode | null {
  return deserialize(serialize(root));
}

function serialize(root: TreeNode | null): string {
  const tokens: string[] = [];
  const write = (node: TreeNode | null): void => {
    if (node === null) {
      tokens.push(MISSING);
      return;
    }
    tokens.push(String(node.val));
    write(node.left);
    write(node.right);
  };
  write(root);
  return tokens.join(SEPARATOR);
}

function deserialize(data: string): TreeNode | null {
  const tokens = data.split(SEPARATOR);
  let next = 0;
  const read = (): TreeNode | null => {
    const token = tokens[next++];
    if (token === MISSING) return null;
    const node = new TreeNode(Number(token));
    node.left = read();
    node.right = read();
    return node;
  };
  return read();
}
