// Conformance: every DSL type round-trips. Statement: .statements/conformance-types.md. Run: cstudy test conformance-types
import { ListNode, TreeNode, GraphNode, Decimal } from "#support";

export class TypeEcho {
  constructor(label: string) {}

  echoInt(value: number): number {
    throw new Error("Not implemented");
  }

  echoLong(value: number): number {
    throw new Error("Not implemented");
  }

  echoDouble(value: number): number {
    throw new Error("Not implemented");
  }

  echoBool(value: boolean): boolean {
    throw new Error("Not implemented");
  }

  echoString(value: string): string {
    throw new Error("Not implemented");
  }

  echoChar(value: string): string {
    throw new Error("Not implemented");
  }

  echoIntArray(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoLongArray(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoDoubleArray(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoBoolArray(value: boolean[]): boolean[] {
    throw new Error("Not implemented");
  }

  echoCharArray(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  echoStringArray(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  echoIntMatrix(value: number[][]): number[][] {
    throw new Error("Not implemented");
  }

  echoLongMatrix(value: number[][]): number[][] {
    throw new Error("Not implemented");
  }

  echoDoubleMatrix(value: number[][]): number[][] {
    throw new Error("Not implemented");
  }

  echoBoolMatrix(value: boolean[][]): boolean[][] {
    throw new Error("Not implemented");
  }

  echoCharMatrix(value: string[][]): string[][] {
    throw new Error("Not implemented");
  }

  echoStringMatrix(value: string[][]): string[][] {
    throw new Error("Not implemented");
  }

  echoIntList(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoLongList(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoDoubleList(value: number[]): number[] {
    throw new Error("Not implemented");
  }

  echoBoolList(value: boolean[]): boolean[] {
    throw new Error("Not implemented");
  }

  echoCharList(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  echoStringList(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  echoIntArrayList(value: number[][]): number[][] {
    throw new Error("Not implemented");
  }

  echoIntListList(value: number[][]): number[][] {
    throw new Error("Not implemented");
  }

  echoStringListList(value: string[][]): string[][] {
    throw new Error("Not implemented");
  }

  echoIntListListList(value: number[][][]): number[][][] {
    throw new Error("Not implemented");
  }

  echoListNode(value: ListNode | null): ListNode | null {
    throw new Error("Not implemented");
  }

  echoTreeNode(value: TreeNode | null): TreeNode | null {
    throw new Error("Not implemented");
  }

  echoGraphNode(value: GraphNode | null): GraphNode | null {
    throw new Error("Not implemented");
  }

  echoListNodeArray(value: (ListNode | null)[]): (ListNode | null)[] {
    throw new Error("Not implemented");
  }

  echoTreeNodeList(value: (TreeNode | null)[]): (TreeNode | null)[] {
    throw new Error("Not implemented");
  }

  echoDecimal(value: Decimal): Decimal {
    throw new Error("Not implemented");
  }

  echoDate(value: string): string {
    throw new Error("Not implemented");
  }

  echoDecimalArray(value: Decimal[]): Decimal[] {
    throw new Error("Not implemented");
  }

  echoDateArray(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  echoDecimalMatrix(value: Decimal[][]): Decimal[][] {
    throw new Error("Not implemented");
  }

  echoDateMatrix(value: string[][]): string[][] {
    throw new Error("Not implemented");
  }

  echoDecimalList(value: Decimal[]): Decimal[] {
    throw new Error("Not implemented");
  }

  echoDateList(value: string[]): string[] {
    throw new Error("Not implemented");
  }

  noop(value: number): void {
    throw new Error("Not implemented");
  }
}
