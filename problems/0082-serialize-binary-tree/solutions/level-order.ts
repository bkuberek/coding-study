import { TreeNode } from "#support";

const MISSING = "#";
const SEPARATOR = ",";

export function serializeDeserialize(root: TreeNode | null): TreeNode | null {
  return deserialize(serialize(root));
}

function serialize(root: TreeNode | null): string {
  const tokens: string[] = [];
  const queue: (TreeNode | null)[] = [root];
  for (let head = 0; head < queue.length; head++) {
    const node = queue[head];
    if (node === null) {
      tokens.push(MISSING);
      continue;
    }
    tokens.push(String(node.val));
    queue.push(node.left, node.right);
  }
  return tokens.join(SEPARATOR);
}

function deserialize(data: string): TreeNode | null {
  const tokens = data.split(SEPARATOR);
  if (tokens[0] === MISSING) return null;
  const root = new TreeNode(Number(tokens[0]));
  const queue: TreeNode[] = [root];
  let position = 1;
  // Every node was written with exactly two child tokens, in queue order.
  for (let head = 0; head < queue.length; head++) {
    const node = queue[head];
    const left = tokens[position++];
    const right = tokens[position++];
    if (left !== MISSING) {
      node.left = new TreeNode(Number(left));
      queue.push(node.left);
    }
    if (right !== MISSING) {
      node.right = new TreeNode(Number(right));
      queue.push(node.right);
    }
  }
  return root;
}
