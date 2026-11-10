// The documents of the visible cases, to put from your own tests. Their texts are exactly what
// the cases send, so the embeddings service knows the chunks they cut into.

export const DOCUMENTS: Record<string, string> = {
  refunds:
    "Customer refunds. Support agents may refund a customer who asks within 30 days of " +
    "purchase. The customer must give the order number from the confirmation email. " +
    "Refunds go back to the original payment method and take up to 5 business days to " +
    "appear. A purchase older than 30 days gets store credit instead, once a team lead " +
    "approves it. Never refund in cash, and never refund a gift card.",
  expenses:
    "Expense claims. Submit each expense within 60 days, with a photo of the receipt. " +
    "Meals while travelling are covered up to 40 euros a day. Your manager approves " +
    "claims under 500 euros, and claims above that need the finance team as well. " +
    "Approved claims are paid with the next monthly salary. Personal items, fines and " +
    "alcohol are never reimbursed.",
  leave:
    "Time off. Everyone gets 25 vacation days a year, and unused days carry over until " +
    "the end of March. Ask your manager at least two weeks ahead, through the leave " +
    "calendar, before you book a trip. Sick days need no approval: tell your team before " +
    "10 in the morning, and send a note from a doctor after three sick days in a row.",
  oncall:
    "On-call runbook. The on-call engineer answers a page within 15 minutes, day or " +
    "night. Acknowledge the alert first, then open an incident channel and post what you " +
    "see. If customers are affected, page the incident commander and update the status " +
    "page every 30 minutes. Hand over open incidents at the end of your shift, in the " +
    "on-call notes.",
  deploys:
    "Deploy runbook. Deploys run from the main branch through the pipeline, never from a " +
    "laptop. Nobody deploys on a Friday afternoon or during an open incident. Watch the " +
    "error dashboard for 20 minutes after each release. If errors rise, roll back at once " +
    "with the rollback button and tell the on-call engineer. Investigate after the " +
    "rollback, not before.",
  access:
    "Accounts and access. To reset your password, use the self-service portal; the help " +
    "desk never asks for your password. Report a lost laptop to security within one hour, " +
    "so the device can be locked. New joiners get a laptop and a badge on their first " +
    "day. Access to production needs a request approved by your team lead.",
};

// The refund policy as level 4 updates it.
export const UPDATED_REFUNDS =
  "Customer refunds. From 1 June, support agents may refund a customer who asks within " +
  "14 days of purchase. The customer must give the order number. Refunds go back to the " +
  "original payment method. After 14 days, offer store credit instead.";

// Questions the services know, by the cases that ask them.
export const QUESTIONS = {
  refundWindow: "How long do customers have to ask for a refund?",
  expenseApproval: "Who approves an expense claim over 500 euros?",
  sellVacation: "How many vacation days can I sell back?",
  offsite: "When is the next team offsite?",
};
