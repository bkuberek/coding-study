// Conformance reference: every echo method returns its argument unchanged.

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
	return value
}

func (e *TypeEcho) EchoLong(value int64) int64 {
	return value
}

func (e *TypeEcho) EchoDouble(value float64) float64 {
	return value
}

func (e *TypeEcho) EchoBool(value bool) bool {
	return value
}

func (e *TypeEcho) EchoString(value string) string {
	return value
}

func (e *TypeEcho) EchoChar(value rune) rune {
	return value
}

func (e *TypeEcho) EchoIntArray(value []int) []int {
	return value
}

func (e *TypeEcho) EchoLongArray(value []int64) []int64 {
	return value
}

func (e *TypeEcho) EchoDoubleArray(value []float64) []float64 {
	return value
}

func (e *TypeEcho) EchoBoolArray(value []bool) []bool {
	return value
}

func (e *TypeEcho) EchoCharArray(value []rune) []rune {
	return value
}

func (e *TypeEcho) EchoStringArray(value []string) []string {
	return value
}

func (e *TypeEcho) EchoIntMatrix(value [][]int) [][]int {
	return value
}

func (e *TypeEcho) EchoLongMatrix(value [][]int64) [][]int64 {
	return value
}

func (e *TypeEcho) EchoDoubleMatrix(value [][]float64) [][]float64 {
	return value
}

func (e *TypeEcho) EchoBoolMatrix(value [][]bool) [][]bool {
	return value
}

func (e *TypeEcho) EchoCharMatrix(value [][]rune) [][]rune {
	return value
}

func (e *TypeEcho) EchoStringMatrix(value [][]string) [][]string {
	return value
}

func (e *TypeEcho) EchoIntList(value []int) []int {
	return value
}

func (e *TypeEcho) EchoLongList(value []int64) []int64 {
	return value
}

func (e *TypeEcho) EchoDoubleList(value []float64) []float64 {
	return value
}

func (e *TypeEcho) EchoBoolList(value []bool) []bool {
	return value
}

func (e *TypeEcho) EchoCharList(value []rune) []rune {
	return value
}

func (e *TypeEcho) EchoStringList(value []string) []string {
	return value
}

func (e *TypeEcho) EchoIntArrayList(value [][]int) [][]int {
	return value
}

func (e *TypeEcho) EchoIntListList(value [][]int) [][]int {
	return value
}

func (e *TypeEcho) EchoStringListList(value [][]string) [][]string {
	return value
}

func (e *TypeEcho) EchoIntListListList(value [][][]int) [][][]int {
	return value
}

func (e *TypeEcho) EchoListNode(value *ListNode) *ListNode {
	return value
}

func (e *TypeEcho) EchoTreeNode(value *TreeNode) *TreeNode {
	return value
}

func (e *TypeEcho) EchoGraphNode(value *GraphNode) *GraphNode {
	return value
}

func (e *TypeEcho) EchoListNodeArray(value []*ListNode) []*ListNode {
	return value
}

func (e *TypeEcho) EchoTreeNodeList(value []*TreeNode) []*TreeNode {
	return value
}

func (e *TypeEcho) Noop(value int) {}
