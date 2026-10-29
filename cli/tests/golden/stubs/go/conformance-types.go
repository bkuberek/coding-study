// Conformance: every DSL type round-trips. Statement: .statements/conformance-types.md. Run: cstudy test conformance-types

package conformance_types

import "cstudy/support"

type ListNode = support.ListNode
type TreeNode = support.TreeNode
type GraphNode = support.GraphNode

type TypeEcho struct{}

func NewTypeEcho(label string) *TypeEcho {
	return &TypeEcho{}
}

func (e *TypeEcho) EchoInt(value int) int {
	panic("not implemented")
}

func (e *TypeEcho) EchoLong(value int64) int64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoDouble(value float64) float64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoBool(value bool) bool {
	panic("not implemented")
}

func (e *TypeEcho) EchoString(value string) string {
	panic("not implemented")
}

func (e *TypeEcho) EchoChar(value rune) rune {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntArray(value []int) []int {
	panic("not implemented")
}

func (e *TypeEcho) EchoLongArray(value []int64) []int64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoDoubleArray(value []float64) []float64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoBoolArray(value []bool) []bool {
	panic("not implemented")
}

func (e *TypeEcho) EchoCharArray(value []rune) []rune {
	panic("not implemented")
}

func (e *TypeEcho) EchoStringArray(value []string) []string {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntMatrix(value [][]int) [][]int {
	panic("not implemented")
}

func (e *TypeEcho) EchoLongMatrix(value [][]int64) [][]int64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoDoubleMatrix(value [][]float64) [][]float64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoBoolMatrix(value [][]bool) [][]bool {
	panic("not implemented")
}

func (e *TypeEcho) EchoCharMatrix(value [][]rune) [][]rune {
	panic("not implemented")
}

func (e *TypeEcho) EchoStringMatrix(value [][]string) [][]string {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntList(value []int) []int {
	panic("not implemented")
}

func (e *TypeEcho) EchoLongList(value []int64) []int64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoDoubleList(value []float64) []float64 {
	panic("not implemented")
}

func (e *TypeEcho) EchoBoolList(value []bool) []bool {
	panic("not implemented")
}

func (e *TypeEcho) EchoCharList(value []rune) []rune {
	panic("not implemented")
}

func (e *TypeEcho) EchoStringList(value []string) []string {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntArrayList(value [][]int) [][]int {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntListList(value [][]int) [][]int {
	panic("not implemented")
}

func (e *TypeEcho) EchoStringListList(value [][]string) [][]string {
	panic("not implemented")
}

func (e *TypeEcho) EchoIntListListList(value [][][]int) [][][]int {
	panic("not implemented")
}

func (e *TypeEcho) EchoListNode(value *ListNode) *ListNode {
	panic("not implemented")
}

func (e *TypeEcho) EchoTreeNode(value *TreeNode) *TreeNode {
	panic("not implemented")
}

func (e *TypeEcho) EchoGraphNode(value *GraphNode) *GraphNode {
	panic("not implemented")
}

func (e *TypeEcho) EchoListNodeArray(value []*ListNode) []*ListNode {
	panic("not implemented")
}

func (e *TypeEcho) EchoTreeNodeList(value []*TreeNode) []*TreeNode {
	panic("not implemented")
}

func (e *TypeEcho) Noop(value int) {
	panic("not implemented")
}
