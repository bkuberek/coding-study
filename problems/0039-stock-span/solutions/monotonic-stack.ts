export class StockSpanner {
  // prices[i] and spans[i] form entry i; prices strictly decrease from bottom to top.
  private readonly prices: number[] = [];
  private readonly spans: number[] = [];

  span(price: number): number {
    let span = 1;
    while (this.prices.length > 0 && this.prices[this.prices.length - 1] <= price) {
      this.prices.pop();
      span += this.spans.pop()!;
    }
    this.prices.push(price);
    this.spans.push(span);
    return span;
  }
}
