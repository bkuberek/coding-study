import { Decimal, GraphNode, ListNode, TreeNode, type IsoDate } from "#support";

export class TypeEcho {
  constructor(label: string) {}

  echoInt(value: number): number {
    return value;
  }

  echoLong(value: number): number {
    return value;
  }

  echoDouble(value: number): number {
    return value;
  }

  echoBool(value: boolean): boolean {
    return value;
  }

  echoString(value: string): string {
    return value;
  }

  echoChar(value: string): string {
    return value;
  }

  echoIntArray(value: number[]): number[] {
    return value;
  }

  echoLongArray(value: number[]): number[] {
    return value;
  }

  echoDoubleArray(value: number[]): number[] {
    return value;
  }

  echoBoolArray(value: boolean[]): boolean[] {
    return value;
  }

  echoCharArray(value: string[]): string[] {
    return value;
  }

  echoStringArray(value: string[]): string[] {
    return value;
  }

  echoIntMatrix(value: number[][]): number[][] {
    return value;
  }

  echoLongMatrix(value: number[][]): number[][] {
    return value;
  }

  echoDoubleMatrix(value: number[][]): number[][] {
    return value;
  }

  echoBoolMatrix(value: boolean[][]): boolean[][] {
    return value;
  }

  echoCharMatrix(value: string[][]): string[][] {
    return value;
  }

  echoStringMatrix(value: string[][]): string[][] {
    return value;
  }

  echoIntList(value: number[]): number[] {
    return value;
  }

  echoLongList(value: number[]): number[] {
    return value;
  }

  echoDoubleList(value: number[]): number[] {
    return value;
  }

  echoBoolList(value: boolean[]): boolean[] {
    return value;
  }

  echoCharList(value: string[]): string[] {
    return value;
  }

  echoStringList(value: string[]): string[] {
    return value;
  }

  echoIntArrayList(value: number[][]): number[][] {
    return value;
  }

  echoIntListList(value: number[][]): number[][] {
    return value;
  }

  echoStringListList(value: string[][]): string[][] {
    return value;
  }

  echoIntListListList(value: number[][][]): number[][][] {
    return value;
  }

  echoListNode(value: ListNode | null): ListNode | null {
    return value;
  }

  echoTreeNode(value: TreeNode | null): TreeNode | null {
    return value;
  }

  echoGraphNode(value: GraphNode | null): GraphNode | null {
    return value;
  }

  echoListNodeArray(value: (ListNode | null)[]): (ListNode | null)[] {
    return value;
  }

  echoTreeNodeList(value: (TreeNode | null)[]): (TreeNode | null)[] {
    return value;
  }

  echoDecimal(value: Decimal): Decimal {
    return value;
  }

  echoDate(value: IsoDate): IsoDate {
    return value;
  }

  echoDecimalArray(value: Decimal[]): Decimal[] {
    return value;
  }

  echoDateArray(value: IsoDate[]): IsoDate[] {
    return value;
  }

  echoDecimalMatrix(value: Decimal[][]): Decimal[][] {
    return value;
  }

  echoDateMatrix(value: IsoDate[][]): IsoDate[][] {
    return value;
  }

  echoDecimalList(value: Decimal[]): Decimal[] {
    return value;
  }

  echoDateList(value: IsoDate[]): IsoDate[] {
    return value;
  }

  noop(value: number): void {}
}
