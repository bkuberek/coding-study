// The Go practice module: one package per problem in practice/<snake_slug>/, written by
// `cstudy start --lang go`. cstudy/support (ListNode, TreeNode, GraphNode) comes from the
// workspace's runner runtime, which `cstudy doctor --fix` restores.
module workspace

go 1.24

require cstudy v0.0.0

replace cstudy => ../.cs/runtime/runners/go
