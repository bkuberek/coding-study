package cs.runner;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import cs.support.GraphNode;
import cs.support.ListNode;
import cs.support.TreeNode;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Set;

/**
 * Encodings of linked structures
 * (docs/specs/problem-format.md#serialization-of-linked-structures).
 */
final class Nodes {
    static final int MAX_LIST_NODES = 100_000;

    private Nodes() {
    }

    static ListNode decodeList(JsonElement json) {
        if (json.isJsonObject()) {
            return decodeCyclicList(json.getAsJsonObject());
        }
        List<ListNode> nodes = listNodes(Json.asArray(json, "ListNode"));
        return nodes.isEmpty() ? null : nodes.get(0);
    }

    static TreeNode decodeTree(JsonElement json) {
        JsonArray values = Json.asArray(json, "TreeNode");
        if (values.isEmpty() || values.get(0).isJsonNull()) {
            return null;
        }
        TreeNode root = new TreeNode(Values.decodeInt(values.get(0)));
        List<TreeNode> parents = new ArrayList<>(List.of(root));
        int index = 1;
        for (int parent = 0; parent < parents.size() && index < values.size(); parent++) {
            TreeNode node = parents.get(parent);
            node.left = treeChild(values, index++, parents);
            node.right = treeChild(values, index++, parents);
        }
        return root;
    }

    static GraphNode decodeGraph(JsonElement json) {
        JsonArray adjacency = Json.asArray(json, "GraphNode");
        List<GraphNode> nodes = new ArrayList<>();
        for (int val = 1; val <= adjacency.size(); val++) {
            nodes.add(new GraphNode(val));
        }
        for (int index = 0; index < adjacency.size(); index++) {
            for (JsonElement neighbor : Json.asArray(adjacency.get(index), "GraphNode")) {
                int val = Values.decodeInt(neighbor);
                if (val < 1 || val > nodes.size()) {
                    throw new BadRequestException("graph neighbor " + val + " is out of range");
                }
                nodes.get(index).neighbors.add(nodes.get(val - 1));
            }
        }
        return nodes.isEmpty() ? null : nodes.get(0);
    }

    static JsonArray encodeList(ListNode head) throws InvalidOutputException {
        JsonArray encoded = new JsonArray();
        for (ListNode node = head; node != null; node = node.next) {
            if (encoded.size() == MAX_LIST_NODES) {
                throw new InvalidOutputException("list too long or cyclic");
            }
            encoded.add(node.val);
        }
        return encoded;
    }

    static JsonArray encodeTree(TreeNode root) throws InvalidOutputException {
        JsonArray encoded = new JsonArray();
        if (root == null) {
            return encoded;
        }
        Set<TreeNode> seen = identitySet();
        List<TreeNode> levelOrder = new ArrayList<>();
        levelOrder.add(root);
        seen.add(root);
        for (int index = 0; index < levelOrder.size(); index++) {
            TreeNode node = levelOrder.get(index);
            if (node == null) {
                encoded.add(JsonNull.INSTANCE);
                continue;
            }
            encoded.add(node.val);
            for (TreeNode child : new TreeNode[] {node.left, node.right}) {
                if (child != null && !seen.add(child)) {
                    throw new InvalidOutputException("tree is cyclic or shares a node");
                }
                levelOrder.add(child);
            }
        }
        while (encoded.get(encoded.size() - 1).isJsonNull()) {
            encoded.remove(encoded.size() - 1);
        }
        return encoded;
    }

    static JsonArray encodeGraph(GraphNode start) throws InvalidOutputException {
        if (start == null) {
            return new JsonArray();
        }
        List<GraphNode> reachable = graphNodes(start);
        GraphNode[] byVal = new GraphNode[reachable.size()];
        for (GraphNode node : reachable) {
            if (node.val < 1 || node.val > byVal.length || byVal[node.val - 1] != null) {
                throw new InvalidOutputException(
                        "graph node values must be exactly 1.." + byVal.length);
            }
            byVal[node.val - 1] = node;
        }
        JsonArray adjacency = new JsonArray();
        for (GraphNode node : byVal) {
            JsonArray neighbors = new JsonArray();
            for (GraphNode neighbor : node.neighbors) {
                neighbors.add(neighbor.val);
            }
            adjacency.add(neighbors);
        }
        return adjacency;
    }

    /** Every node reachable from {@code root} in traversal order, each once. */
    static List<Object> traverse(Object root) throws InvalidOutputException {
        return switch (root) {
            case null -> List.of();
            case ListNode head -> List.copyOf(listOrder(head));
            case TreeNode tree -> List.copyOf(treeOrder(tree));
            case GraphNode graph -> List.copyOf(graphNodes(graph));
            default -> throw new InvalidOutputException(
                    "expected a node, got " + root.getClass().getName());
        };
    }

    static int val(Object node) {
        return switch (node) {
            case ListNode list -> list.val;
            case TreeNode tree -> tree.val;
            case GraphNode graph -> graph.val;
            default -> throw new IllegalArgumentException("not a node: " + node);
        };
    }

    static <T> Set<T> identitySet() {
        return Collections.newSetFromMap(new IdentityHashMap<>());
    }

    private static ListNode decodeCyclicList(JsonObject cyclic) {
        List<ListNode> nodes = listNodes(Json.array(cyclic, "values"));
        int cycleAt = Json.integer(cyclic, "cycle_at");
        if (cycleAt < 0 || cycleAt >= nodes.size()) {
            throw new BadRequestException("cycle_at " + cycleAt + " is out of range");
        }
        nodes.get(nodes.size() - 1).next = nodes.get(cycleAt);
        return nodes.get(0);
    }

    private static List<ListNode> listNodes(JsonArray values) {
        List<ListNode> nodes = new ArrayList<>();
        for (JsonElement value : values) {
            ListNode node = new ListNode(Values.decodeInt(value));
            if (!nodes.isEmpty()) {
                nodes.get(nodes.size() - 1).next = node;
            }
            nodes.add(node);
        }
        return nodes;
    }

    private static TreeNode treeChild(JsonArray values, int index, List<TreeNode> parents) {
        if (index >= values.size() || values.get(index).isJsonNull()) {
            return null;
        }
        TreeNode child = new TreeNode(Values.decodeInt(values.get(index)));
        parents.add(child);
        return child;
    }

    private static List<ListNode> listOrder(ListNode head) {
        Set<ListNode> seen = identitySet();
        List<ListNode> order = new ArrayList<>();
        for (ListNode node = head; node != null && seen.add(node); node = node.next) {
            order.add(node);
        }
        return order;
    }

    private static List<TreeNode> treeOrder(TreeNode root) {
        Set<TreeNode> seen = identitySet();
        List<TreeNode> order = new ArrayList<>(List.of(root));
        seen.add(root);
        for (int index = 0; index < order.size(); index++) {
            TreeNode node = order.get(index);
            for (TreeNode child : new TreeNode[] {node.left, node.right}) {
                if (child != null && seen.add(child)) {
                    order.add(child);
                }
            }
        }
        return order;
    }

    private static List<GraphNode> graphNodes(GraphNode start) throws InvalidOutputException {
        Set<GraphNode> seen = identitySet();
        List<GraphNode> order = new ArrayList<>(List.of(start));
        seen.add(start);
        for (int index = 0; index < order.size(); index++) {
            List<GraphNode> neighbors = order.get(index).neighbors;
            if (neighbors == null) {
                throw new InvalidOutputException("graph node neighbors must not be null");
            }
            for (GraphNode neighbor : neighbors) {
                if (neighbor == null) {
                    throw new InvalidOutputException("graph node neighbors must not hold null");
                }
                if (seen.add(neighbor)) {
                    order.add(neighbor);
                }
            }
        }
        return order;
    }
}
