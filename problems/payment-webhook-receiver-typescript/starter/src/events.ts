// What the provider sends: one payment event per delivery, as vendors/payment-provider/API.md
// describes it.

export type PaymentEvent = {
  id: string;
  type: string;
  order: string;
  sequence: number;
  amount: number;
  currency: string;
  created: number;
};
