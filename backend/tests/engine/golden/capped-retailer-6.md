# Classic step trace with capacity 6 on the Retailer: Weeks 1-10 worked by hand

This table is the source of `capped-retailer-6.json`. It was worked by hand from the Week
sequence (PRD FR-26, addendum §B: "ship the smaller of inventory and amount to ship (and
capacity)"), not produced by the engine under test.

## Set-up

- Classic settings (as in `classic-step-pass-through.md`), plus capacity 6 on the Retailer
  only: the Retailer ships at most 6 units a Week. No other Seat is capped.
- Customer demand 4 in Weeks 1-4, 8 from Week 5.
- Orders: the same as `classic-step-pass-through.json`. The Retailer orders customer demand;
  every other Seat orders its own incoming order.

## Why only the Retailer's rows change

The Retailer ships to the customer, so its shipments never enter another Seat. Its Orders are
customer demand, as in the uncapped trace. Every other Seat therefore receives the same orders
and deliveries as in `classic-step-pass-through.md`, and its rows (and the Retailer's incoming
delivery and goods slots) are copied from that hand-worked table unchanged.

## Retailer, Weeks 1-10

Each Week: on hand = previous inventory + delivery; owed = previous backlog + incoming order;
shipped = the smallest of on hand, owed and 6; inventory = on hand − shipped; backlog = owed −
shipped; cost = 0.50 × inventory + 1.00 × backlog. Deliveries are the Wholesaler's shipments of
two Weeks earlier (from the uncapped table).

| Week | Incoming order | Delivery | On hand | Owed | Shipped | Inventory | Backlog | Cost | Total incl. Week |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 4 | 16 | 4 | 4 | 12 | 0 | 6.00 | 6.00 |
| 2 | 4 | 4 | 16 | 4 | 4 | 12 | 0 | 6.00 | 12.00 |
| 3 | 4 | 4 | 16 | 4 | 4 | 12 | 0 | 6.00 | 18.00 |
| 4 | 4 | 4 | 16 | 4 | 4 | 12 | 0 | 6.00 | 24.00 |
| 5 | 8 | 4 | 16 | 8 | 6 | 10 | 2 | 7.00 | 31.00 |
| 6 | 8 | 4 | 14 | 10 | 6 | 8 | 4 | 8.00 | 39.00 |
| 7 | 8 | 4 | 12 | 12 | 6 | 6 | 6 | 9.00 | 48.00 |
| 8 | 8 | 4 | 10 | 14 | 6 | 4 | 8 | 10.00 | 58.00 |
| 9 | 8 | 8 | 12 | 16 | 6 | 6 | 10 | 13.00 | 71.00 |
| 10 | 8 | 8 | 14 | 18 | 6 | 8 | 12 | 16.00 | 87.00 |

From Week 5 the Retailer has at least 6 on hand every Week, so it ships its full capacity and
its backlog grows by 2 a Week (demand 8 − capacity 6), as addendum §B says. Inventory and
backlog are both positive from Week 5: allowed on a capped Seat only (FR-29).

Total cost after Week 10 (the state that opens Week 11): Retailer 87.00; Wholesaler 46.00,
Distributor 54.00 and Factory 60.00 as in the uncapped trace.

Unit check: in Weeks 5-10 the Retailer delivers 36 units to the customer (6 a Week) against
44 in the uncapped trace (8, 8, 8, 4, 8, 8). The 8 units not delivered are exactly the
difference in its Week 10 inventory (8 against 0), so units on hand and in transit still equal
80 + units entered production − units delivered.
