export class StockSpanner {
  private readonly prices: number[] = [];

  span(price: number): number {
    this.prices.push(price);
    let day = this.prices.length - 1;
    while (day > 0 && this.prices[day - 1] <= price) {
      day--;
    }
    return this.prices.length - day;
  }
}
