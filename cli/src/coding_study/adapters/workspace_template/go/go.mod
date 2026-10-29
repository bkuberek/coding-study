// The Go practice module: one package per problem in practice/<snake_slug>/, written by
// `cstudy start --lang go`. cstudy/support (ListNode, TreeNode, GraphNode) and the vendored
// copy of github.com/shopspring/decimal come from the workspace's runner runtime, which
// `cstudy doctor --fix` restores; nothing is downloaded.
module workspace

go 1.24

require (
	cstudy v0.0.0
	github.com/shopspring/decimal v1.5.0
)

replace (
	cstudy => ../.cs/runtime/runners/go
	github.com/shopspring/decimal => ../.cs/runtime/runners/go/third_party/github.com/shopspring/decimal
)
