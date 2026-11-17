# Classic step trace with pass-through Orders: Weeks 1-10 worked by hand

Independent check (2026-11-17): agrees. No human is in the loop, so a separate reviewer
worked Weeks 1-10 by hand from the story, addendum §B and the spec's rules, without seeing
this table or the engine, and then compared its result with `classic-step-pass-through.json`:
0 mismatches in every field, the Orders and the totals.

This table is the source of `classic-step-pass-through.json`. It was worked by hand from the
Week sequence (PRD FR-26, addendum §B), not produced by the engine under test.

## Set-up

- Classic settings: 4 Roles, starting inventory 12, 4 in every slot, order, shipping and
  production delay 2, holding 0.50 and backorder 1.00 per unit per Week.
- Customer demand 4 in Weeks 1-4, 8 from Week 5.
- Orders: the Retailer orders customer demand; every other Seat orders its own incoming order.
- The chain starts with 80 units: 48 in inventory, 24 in shipping slots, 8 in production slots.

## How each Week is worked

1. Receive `goods_slots[0]` into inventory.
2. Amount to ship = incoming order + backlog; ship the smaller of inventory and that amount;
   the rest is backlog.
3. Goods pipelines move up one slot and take the upstream Seat's shipment this Week; the
   Factory's production pipeline takes the Order entering production (`production_orders[0]`).
4. Cost = 0.50 × inventory + 1.00 × backlog on those balances.
5. Orders: each order pipeline drops index 0 and appends the downstream Seat's Order; the
   Factory's `production_orders` appends its own Order.

Slots below are the state after the Week opened (step 3), "arrives soonest" first. Order slots
index 0 is the Order received this Week; production orders index 0 entered production this
Week. Timing: an Order placed in Week t is received in t+2, a shipment sent in t arrives in
t+2, and a Factory Order placed in t enters production in t+2 and reaches Factory inventory in
t+4.

Derived by hand: the Wholesaler's incoming order in Week t is the Retailer's Order of t-2, so
the step reaches the Wholesaler in Week 7, the Distributor in Week 9 and the Factory in Week 11
(outside this table). The Retailer gets 8 delivered first in Week 9, from the Wholesaler's
Week 7 shipment.

## Weeks

### Week 1

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 6.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 6.00 | (4, 4) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 6.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 6.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 80 on hand and in transit = 80 + 4 entered production − 4 delivered.

### Week 2

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 12.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 12.00 | (4, 4) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 12.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 12.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 80 on hand and in transit = 80 + 8 entered production − 8 delivered.

### Week 3

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 18.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 18.00 | (4, 4) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 18.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 18.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 80 on hand and in transit = 80 + 12 entered production − 12 delivered.

### Week 4

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 24.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 24.00 | (4, 4) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 24.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 24.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 80 on hand and in transit = 80 + 16 entered production − 16 delivered.

### Week 5

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 8 | 8 | 0 | 8 | 4.00 | 28.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 30.00 | (4, 4) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 30.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 30.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 76 on hand and in transit = 80 + 20 entered production − 24 delivered.

### Week 6

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 8 | 4 | 0 | 8 | 2.00 | 30.00 | — | (4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 36.00 | (4, 8) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 36.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 36.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 72 on hand and in transit = 80 + 24 entered production − 32 delivered.

### Week 7

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 8 | 0 | 0 | 8 | 0.00 | 30.00 | — | (4, 8) | — |
| Wholesaler | 8 | 4 | 8 | 8 | 0 | 8 | 4.00 | 40.00 | (8, 8) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 42.00 | (4, 4) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 42.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 68 on hand and in transit = 80 + 28 entered production − 40 delivered.

### Week 8

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 4 | 0 | 4 | 8 | 4.00 | 34.00 | — | (8, 8) | — |
| Wholesaler | 8 | 4 | 8 | 4 | 0 | 8 | 2.00 | 42.00 | (8, 8) | (4, 4) | — |
| Distributor | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 48.00 | (4, 8) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 48.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 68 on hand and in transit = 80 + 32 entered production − 44 delivered.

### Week 9

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 8 | 8 | 0 | 4 | 8 | 4.00 | 38.00 | — | (8, 8) | — |
| Wholesaler | 8 | 4 | 8 | 0 | 0 | 8 | 0.00 | 42.00 | (8, 8) | (4, 8) | — |
| Distributor | 8 | 4 | 8 | 8 | 0 | 8 | 4.00 | 52.00 | (8, 8) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 54.00 | (4, 4) | (4, 4) | (4, 4) |

Unit check: 64 on hand and in transit = 80 + 36 entered production − 52 delivered.

### Week 10

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 8 | 8 | 0 | 4 | 8 | 4.00 | 42.00 | — | (8, 4) | — |
| Wholesaler | 8 | 4 | 4 | 0 | 4 | 8 | 4.00 | 46.00 | (8, 8) | (8, 8) | — |
| Distributor | 8 | 4 | 8 | 4 | 0 | 8 | 2.00 | 54.00 | (8, 8) | (4, 4) | — |
| Factory | 4 | 4 | 4 | 12 | 0 | 4 | 6.00 | 60.00 | (4, 8) | (4, 4) | (4, 4) |

Unit check: 60 on hand and in transit = 80 + 40 entered production − 60 delivered.

## Totals after Week 10

| Role | Total cost |
|---|---:|
| Retailer | 42.00 |
| Wholesaler | 46.00 |
| Distributor | 54.00 |
| Factory | 60.00 |
